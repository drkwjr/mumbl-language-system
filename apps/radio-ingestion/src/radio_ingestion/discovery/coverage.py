"""Discovery coverage report helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


def _parse_stats(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def fetch_sources(conn) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, name, source_type, base_url, countries
            FROM discovery_sources
            WHERE active = true
            ORDER BY id
            """)
        rows = cur.fetchall()
    sources = []
    for row in rows:
        source = {
            "id": row[0],
            "name": row[1],
            "source_type": row[2],
            "base_url": row[3],
            "countries": row[4] or [],
        }
        if isinstance(source["countries"], str):
            source["countries"] = json.loads(source["countries"])
        sources.append(source)
    return sources


def fetch_target_countries(sources: List[Dict[str, Any]]) -> List[str]:
    target_countries: List[str] = []
    for source in sources:
        for country in source.get("countries") or []:
            if country not in target_countries:
                target_countries.append(country)
    return target_countries


def _fetch_audio_quality(conn, window_hours: int = 24) -> Dict[Optional[str], Dict[str, Any]]:
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    quality_map: Dict[Optional[str], Dict[str, Any]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                src.country,
                COUNT(*) AS shard_count,
                AVG(shard.bitrate) AS avg_bitrate,
                STDDEV_POP(shard.bitrate) AS bitrate_stddev,
                AVG(shard.silence_ratio) AS avg_silence_ratio,
                AVG(shard.duration_ratio) AS avg_duration_ratio,
                SUM(
                    CASE
                        WHEN shard.duration_ratio IS NOT NULL
                             AND shard.duration_ratio < 0.9 THEN 1
                        ELSE 0
                    END
                ) AS dropout_count
            FROM radio_shards shard
            JOIN radio_sources src ON src.id = shard.source_id
            WHERE shard.created_at >= %s
            GROUP BY src.country
            """,
            (window_start,),
        )
        for row in cur.fetchall():
            quality_map[row[0]] = {
                "window_hours": window_hours,
                "shard_count": int(row[1] or 0),
                "avg_bitrate_kbps": float(row[2]) if row[2] is not None else None,
                "bitrate_stddev_kbps": float(row[3]) if row[3] is not None else None,
                "avg_silence_ratio": float(row[4]) if row[4] is not None else None,
                "avg_duration_ratio": float(row[5]) if row[5] is not None else None,
                "dropout_count": int(row[6] or 0),
            }

        cur.execute(
            """
            SELECT
                src.country,
                COUNT(*) AS capture_failures,
                SUM(
                    CASE
                        WHEN payload->>'error_kind' = 'ffmpeg_error' THEN 1
                        ELSE 0
                    END
                ) AS ffmpeg_errors
            FROM pipeline_events pe
            JOIN radio_sources src ON src.id = pe.source_id
            WHERE pe.created_at >= %s
              AND pe.stage = 'capture'
              AND pe.event_type = 'capture_failed'
            GROUP BY src.country
            """,
            (window_start,),
        )
        for row in cur.fetchall():
            quality = quality_map.setdefault(
                row[0],
                {
                    "window_hours": window_hours,
                    "shard_count": 0,
                    "avg_bitrate_kbps": None,
                    "bitrate_stddev_kbps": None,
                    "avg_silence_ratio": None,
                    "avg_duration_ratio": None,
                    "dropout_count": 0,
                },
            )
            quality["capture_failures"] = int(row[1] or 0)
            quality["ffmpeg_errors"] = int(row[2] or 0)

    return quality_map


def _fetch_language_mapping(conn, window_hours: int = 24) -> Dict[Optional[str], Dict[str, Any]]:
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    mapping_map: Dict[Optional[str], Dict[str, Any]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                src.country,
                COUNT(*) AS total_segments,
                SUM(CASE WHEN seg.primary_lang_iso639_3 IS NOT NULL THEN 1 ELSE 0 END)
                    AS mapped_segments,
                SUM(CASE WHEN seg.primary_lang_iso639_3 IS NULL THEN 1 ELSE 0 END)
                    AS unmapped_segments
            FROM radio_segments seg
            JOIN radio_shards shard ON shard.id = seg.shard_id
            JOIN radio_sources src ON src.id = shard.source_id
            WHERE seg.created_at >= %s
              AND seg.primary_lang_raw IS NOT NULL
            GROUP BY src.country
            """,
            (window_start,),
        )
        for row in cur.fetchall():
            mapping_map[row[0]] = {
                "window_hours": window_hours,
                "total_segments": int(row[1] or 0),
                "mapped_segments": int(row[2] or 0),
                "unmapped_segments": int(row[3] or 0),
            }
    return mapping_map


def build_coverage_report(conn, target_countries: Optional[List[str]] = None) -> Dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (dr.source_id, dr.country)
                dr.source_id,
                dr.country,
                dr.status,
                dr.stats,
                dr.finished_at,
                ds.name,
                ds.source_type
            FROM discovery_runs dr
            JOIN discovery_sources ds ON ds.id = dr.source_id
            WHERE dr.finished_at IS NOT NULL
            ORDER BY dr.source_id, dr.country, dr.finished_at DESC
            """)
        latest_runs = cur.fetchall()

        cur.execute("""
            SELECT source_id, country, COUNT(*) AS count
            FROM station_provenance
            GROUP BY source_id, country
            """)
        provenance_rows = cur.fetchall()

        cur.execute("""
            SELECT source_id, country, COUNT(DISTINCT canonical_id) AS count
            FROM station_source_links
            GROUP BY source_id, country
            """)
        canonical_rows = cur.fetchall()

        cur.execute("""
            SELECT country, COUNT(DISTINCT canonical_id) AS count
            FROM station_source_links
            GROUP BY country
            """)
        canonical_country_rows = cur.fetchall()

    provenance_map: Dict[Tuple[int, Optional[str]], int] = {}
    for row in provenance_rows:
        provenance_map[(row[0], row[1])] = int(row[2] or 0)

    canonical_map: Dict[Tuple[int, Optional[str]], int] = {}
    for row in canonical_rows:
        canonical_map[(row[0], row[1])] = int(row[2] or 0)

    canonical_country_map: Dict[Optional[str], int] = {}
    for row in canonical_country_rows:
        canonical_country_map[row[0]] = int(row[1] or 0)

    countries = set(target_countries or [])
    for row in latest_runs:
        countries.add(row[1])
    for row in provenance_rows:
        countries.add(row[1])

    countries_list = [c for c in countries if c] or [None]
    audio_quality = _fetch_audio_quality(conn)
    language_mapping = _fetch_language_mapping(conn)
    report_countries = []

    for country in sorted(countries_list, key=lambda x: x or ""):
        sources = []
        total_discovered = 0
        total_inserted = 0
        total_provenance = 0

        for row in latest_runs:
            source_id, run_country, status, stats_value, finished_at, name, source_type = row
            if run_country != country:
                continue

            stats = _parse_stats(stats_value)
            discovered = int(stats.get("discovered") or 0)
            inserted = int(stats.get("inserted") or 0)
            provenance = provenance_map.get((source_id, run_country), 0)
            canonical_count = canonical_map.get((source_id, run_country), 0)

            sources.append(
                {
                    "source_id": source_id,
                    "source_name": name,
                    "source_type": source_type,
                    "discovered": discovered,
                    "inserted": inserted,
                    "provenance_count": provenance,
                    "canonical_count": canonical_count,
                    "status": status,
                    "last_finished": finished_at.isoformat() if finished_at else None,
                }
            )

            total_discovered += discovered
            total_inserted += inserted
            total_provenance += provenance
        canonical_total = canonical_country_map.get(country, 0)

        report_countries.append(
            {
                "country": country,
                "total_discovered": total_discovered,
                "total_inserted": total_inserted,
                "provenance_count": total_provenance,
                "canonical_station_count": canonical_total,
                "audio_quality": audio_quality.get(country),
                "language_mapping": language_mapping.get(country),
                "sources": sources,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "countries": report_countries,
    }


def store_coverage_report(conn, countries: List[Optional[str]], report: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO discovery_coverage_reports (target_countries, report)
            VALUES (%s, %s)
            """,
            (json.dumps([c for c in countries if c]), json.dumps(report)),
        )
