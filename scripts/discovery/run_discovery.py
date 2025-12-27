#!/usr/bin/env python3
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import re

import requests
import structlog

from mumbl_storage.db import get_connection
from radio_ingestion.discovery.coverage import (
    build_coverage_report,
    fetch_sources as fetch_coverage_sources,
    fetch_target_countries,
    store_coverage_report,
)
from radio_ingestion.discovery.radio_browser import RadioBrowserClient
from radio_ingestion.discovery.wiki_parser import parse_wiki_page
from radio_ingestion.storage.radio_repositories import RadioSourceRepository

WIKI_HEADERS = {
    "User-Agent": "MumblLanguageSystem/0.1.0 (educational/research)",
}

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def create_run(conn, source_id: int, country: Optional[str]) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO discovery_runs (source_id, country, status)
            VALUES (%s, %s, 'running')
            RETURNING id
            """,
            (source_id, country),
        )
        return cur.fetchone()[0]


def finalize_run(conn, run_id: int, status: str, stats: Dict[str, Any], error: Optional[str] = None):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE discovery_runs
            SET status = %s,
                finished_at = CURRENT_TIMESTAMP,
                stats = %s,
                error_message = %s
            WHERE id = %s
            """,
            (status, json.dumps(stats), error, run_id),
        )


def insert_provenance(
    conn,
    source_id: int,
    station_uuid: Optional[str],
    stream_url: Optional[str],
    homepage: Optional[str],
    station_name: Optional[str],
    country: Optional[str],
    tags: Optional[List[str]],
    evidence_url: Optional[str],
    confidence: Optional[float],
    raw_payload: Dict[str, Any],
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO station_provenance (
                source_id, station_uuid, stream_url, homepage,
                station_name, country, tags, evidence_url, confidence, raw_payload
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (
                source_id,
                station_uuid,
                stream_url,
                homepage,
                station_name,
                country,
                json.dumps(tags or []),
                evidence_url,
                confidence,
                json.dumps(raw_payload),
            ),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        if station_uuid:
            cur.execute(
                """
                SELECT id FROM station_provenance
                WHERE source_id = %s AND station_uuid = %s
                """,
                (source_id, station_uuid),
            )
            existing = cur.fetchone()
            if existing:
                return existing[0]

        if stream_url:
            cur.execute(
                """
                SELECT id FROM station_provenance
                WHERE source_id = %s AND stream_url = %s
                """,
                (source_id, stream_url),
            )
            existing = cur.fetchone()
            if existing:
                return existing[0]

    return None


def _normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    cleaned = re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def _normalize_stream_url(stream_url: Optional[str]) -> Optional[str]:
    if not stream_url:
        return None
    try:
        parsed = urlparse(stream_url)
    except Exception:
        return stream_url
    base = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    return base.rstrip("/")


def _homepage_domain(homepage: Optional[str]) -> Optional[str]:
    if not homepage:
        return None
    try:
        parsed = urlparse(homepage)
    except Exception:
        return None
    return parsed.netloc.lower() if parsed.netloc else None


def upsert_canonical_station(
    conn,
    station_name: Optional[str],
    stream_url: Optional[str],
    homepage: Optional[str],
):
    normalized_name = _normalize_name(station_name)
    normalized_stream = _normalize_stream_url(stream_url)
    homepage_domain = _homepage_domain(homepage)
    if normalized_stream:
        canonical_key = f"stream:{normalized_stream}"
    else:
        canonical_key = f"site:{homepage_domain or 'unknown'}|name:{normalized_name}"
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO canonical_stations (canonical_key, normalized_name, homepage_domain, stream_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (canonical_key) DO UPDATE
            SET normalized_name = COALESCE(EXCLUDED.normalized_name, canonical_stations.normalized_name),
                homepage_domain = COALESCE(EXCLUDED.homepage_domain, canonical_stations.homepage_domain),
                stream_url = COALESCE(EXCLUDED.stream_url, canonical_stations.stream_url)
            RETURNING id
            """,
            (canonical_key, normalized_name or None, homepage_domain, normalized_stream),
        )
        return cur.fetchone()[0]


def link_canonical_station(
    conn,
    canonical_id: int,
    source_id: int,
    provenance_id: int,
    country: Optional[str],
    confidence: Optional[float],
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO station_source_links (
                canonical_id, source_id, station_provenance_id, country, confidence
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (station_provenance_id) DO NOTHING
            """,
            (canonical_id, source_id, provenance_id, country, confidence),
        )


def write_report_file(report: Dict[str, Any]):
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    output_path = logs_dir / "discovery_coverage_latest.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def run_radio_browser(conn, source, country: str, limit: int = 200):
    client = RadioBrowserClient()
    repo = RadioSourceRepository(conn)
    stations = client.search_stations(country_code=country, limit=limit, order="votes", reverse=True)
    parsed = []
    for station in stations:
        parsed_station = client.parse_station(station)
        if parsed_station.get("stream_url"):
            parsed.append(parsed_station)

    inserted_ids = repo.insert_many(parsed)
    inserted = len([sid for sid in inserted_ids if sid is not None])

    for station in parsed:
        provenance_id = insert_provenance(
            conn,
            source["id"],
            station.get("station_uuid"),
            station.get("stream_url"),
            station.get("homepage"),
            station.get("name"),
            station.get("country"),
            station.get("tags"),
            source.get("base_url"),
            confidence=0.7,
            raw_payload=station,
        )
        if provenance_id:
            canonical_id = upsert_canonical_station(
                conn,
                station.get("name"),
                station.get("stream_url"),
                station.get("homepage"),
            )
            link_canonical_station(
                conn,
                canonical_id,
                source["id"],
                provenance_id,
                station.get("country"),
                0.7,
            )

    return {"discovered": len(parsed), "inserted": inserted}


def run_wiki(conn, source):
    url = source.get("base_url")
    if not url:
        return {"discovered": 0, "inserted": 0}

    resp = requests.get(url, timeout=30, headers=WIKI_HEADERS)
    resp.raise_for_status()

    candidates = parse_wiki_page(resp.text, source, allow_llm=True)

    discovered = 0
    for candidate in candidates:
        provenance_id = insert_provenance(
            conn,
            source["id"],
            station_uuid=None,
            stream_url=candidate.stream_url,
            homepage=candidate.homepage,
            station_name=candidate.name,
            country=(source.get("countries") or [None])[0],
            tags=candidate.tags,
            evidence_url=url,
            confidence=candidate.confidence or 0.3,
            raw_payload={
                "raw": candidate.name,
                "stream_url": candidate.stream_url,
                "homepage": candidate.homepage,
                "languages": candidate.languages,
                "tags": candidate.tags,
                "confidence": candidate.confidence,
            },
        )
        if provenance_id:
            canonical_id = upsert_canonical_station(
                conn,
                candidate.name,
                candidate.stream_url,
                candidate.homepage,
            )
            link_canonical_station(
                conn,
                canonical_id,
                source["id"],
                provenance_id,
                (source.get("countries") or [None])[0],
                candidate.confidence or 0.3,
            )
        discovered += 1

    return {"discovered": discovered, "inserted": 0}

def _run_task(source: Dict[str, Any], country: Optional[str]) -> Tuple[int, str]:
    start_time = time.time()
    logger.info("Discovery run started", source=source.get("name"), country=country)
    with get_connection() as conn:
        run_id = create_run(conn, source["id"], country)
        conn.commit()

    stats = {"discovered": 0, "inserted": 0}
    status = "completed"
    error = None
    try:
        with get_connection() as conn:
            if source["source_type"] == "directory" and source["name"] == "Radio Browser":
                result = run_radio_browser(conn, source, country)
            elif source["source_type"] == "wiki":
                result = run_wiki(conn, source)
            else:
                result = {"discovered": 0, "inserted": 0}
            stats.update(result)
            conn.commit()
    except Exception as exc:
        status = "failed"
        error = str(exc)

    with get_connection() as conn:
        finalize_run(conn, run_id, status, stats, error)
        conn.commit()

    elapsed = time.time() - start_time
    logger.info(
        "Discovery run completed",
        run_id=run_id,
        source=source.get("name"),
        country=country,
        status=status,
        stats=stats,
        elapsed_seconds=round(elapsed, 2),
        error=error,
    )
    return run_id, status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run station discovery and coverage report.")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Skip discovery runs and only refresh coverage report from existing data.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    ensure_database_url()
    with get_connection() as conn:
        sources = fetch_coverage_sources(conn)

    if not args.report_only:
        tasks: List[Tuple[Dict[str, Any], Optional[str]]] = []
        for source in sources:
            countries = source.get("countries") or [None]
            for country in countries:
                tasks.append((source, country))

        max_workers = int(os.getenv("DISCOVERY_MAX_WORKERS", "4"))
        logger.info("Starting discovery", tasks=len(tasks), max_workers=max_workers)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_run_task, source, country): (source.get("name"), country)
                for source, country in tasks
            }
            for future in as_completed(futures):
                source_name, country = futures[future]
                try:
                    future.result()
                except Exception as exc:
                    logger.error(
                        "Discovery task failed",
                        source=source_name,
                        country=country,
                        error=str(exc),
                    )

    target_countries = fetch_target_countries(sources)

    with get_connection() as conn:
        report = build_coverage_report(conn, target_countries)
        store_coverage_report(conn, target_countries, report)
        conn.commit()

    write_report_file(report)
    logger.info(
        "Coverage report generated",
        countries=len(report.get("countries") or []),
    )


if __name__ == "__main__":
    main()
