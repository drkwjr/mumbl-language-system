"""FastAPI dashboard for radio ingestion monitoring"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import PipelineEventRepository
from psycopg.rows import dict_row
from pydantic import BaseModel
from radio_ingestion.discovery.coverage import (
    build_coverage_report,
)
from radio_ingestion.discovery.coverage import fetch_sources as fetch_coverage_sources
from radio_ingestion.discovery.coverage import (
    fetch_target_countries,
    store_coverage_report,
)
from radio_ingestion.service import RadioIngestionService
from radio_ingestion.storage.radio_repositories import (
    CaptureTargetRepository,
    RadioSegmentRepository,
    RadioShardRepository,
    RadioSourceRepository,
    RadioStationDaypartRepository,
    RadioStationHourlyRepository,
)

app = FastAPI(title="Radio Ingestion Dashboard", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_json_field(value: Optional[Any]) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return value


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: str
    components: Dict[str, Any]


class StationSummary(BaseModel):
    """Station summary"""

    id: int
    name: str
    country: str
    lang_hint: Optional[str]
    status: str
    last_check: Optional[str]
    last_successful_capture: Optional[str]
    health_status: Optional[str] = None
    health_last_error: Optional[str] = None
    health_last_failure_at: Optional[str] = None
    health_consecutive_failures: Optional[int] = None
    health_last_success_at: Optional[str] = None
    frequency_mhz: Optional[float] = None
    frequency_label: Optional[str] = None
    frequency_source: Optional[str] = None
    frequency_confidence: Optional[float] = None


class StationQualityResponse(BaseModel):
    window_hours: int
    shard_count: int
    avg_bitrate_kbps: Optional[float] = None
    bitrate_stddev_kbps: Optional[float] = None
    avg_silence_ratio: Optional[float] = None
    avg_duration_ratio: Optional[float] = None
    dropout_count: int
    capture_failures: int
    ffmpeg_errors: int
    last_shard_at: Optional[str] = None


class DiscoveryRunRow(BaseModel):
    id: int
    source_name: str
    source_type: str
    country: Optional[str]
    status: str
    stats: Dict[str, Any]
    started_at: Optional[str]
    finished_at: Optional[str]
    error_message: Optional[str]


class DiscoverySummaryRow(BaseModel):
    source_name: str
    source_type: str
    runs: int
    total_discovered: int
    total_inserted: int
    last_finished: Optional[str]


class DiscoveryCoverageSource(BaseModel):
    source_id: int
    source_name: str
    source_type: str
    discovered: int
    inserted: int
    provenance_count: int
    canonical_count: int
    status: Optional[str]
    last_finished: Optional[str]


class DiscoveryCoverageAudioQuality(BaseModel):
    window_hours: int
    shard_count: int
    avg_bitrate_kbps: Optional[float] = None
    bitrate_stddev_kbps: Optional[float] = None
    avg_silence_ratio: Optional[float] = None
    avg_duration_ratio: Optional[float] = None
    dropout_count: int
    capture_failures: Optional[int] = None
    ffmpeg_errors: Optional[int] = None


class DiscoveryCoverageLanguageMapping(BaseModel):
    window_hours: int
    total_segments: int
    mapped_segments: int
    unmapped_segments: int


class DiscoveryCoverageCountry(BaseModel):
    country: Optional[str]
    total_discovered: int
    total_inserted: int
    provenance_count: int
    canonical_station_count: int
    audio_quality: Optional[DiscoveryCoverageAudioQuality] = None
    language_mapping: Optional[DiscoveryCoverageLanguageMapping] = None
    sources: List[DiscoveryCoverageSource]


class DiscoveryCoverageReport(BaseModel):
    generated_at: str
    countries: List[DiscoveryCoverageCountry]


class UnmappedLanguageLabel(BaseModel):
    label: str
    count: int


class LanguageTaxonomyRow(BaseModel):
    iso639_3: str
    iso639_1: Optional[str]
    name: str


class LanguageLabelMapRow(BaseModel):
    observed_label: str
    canonical_iso639_3: Optional[str]
    source: Optional[str]
    confidence: Optional[float]
    notes: Optional[str]


class LanguageLabelMapRequest(BaseModel):
    observed_label: str
    canonical_iso639_3: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None


class PipelineErrorRow(BaseModel):
    stage: str
    event_type: str
    status: str
    message: Optional[str]
    error_kind: Optional[str]
    error_detail: Optional[str]
    source_id: Optional[int]
    station_name: Optional[str]
    created_at: str


# Global service instance (will be set by startup)
service_instance: Optional[RadioIngestionService] = None


@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    # Service will be passed in or initialized here
    # For now, we'll initialize it lazily if needed
    pass


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status of database, queue, scheduler
    """
    if not service_instance:
        # Quick health check without service
        health = {
            "status": "degraded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {"database": "unknown", "service": "not_initialized"},
        }

        # Check database
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
            health["components"]["database"] = "healthy"
        except Exception as e:
            health["status"] = "unhealthy"
            health["components"]["database"] = f"unhealthy: {str(e)}"

        return health

    # Full health check with service
    health = await service_instance.health_check()
    return health


@app.get("/stations", response_model=List[StationSummary])
async def list_stations(
    country: Optional[str] = None, lang_hint: Optional[str] = None, status: str = "active"
):
    """
    List radio stations.

    Args:
        country: Filter by country code
        lang_hint: Filter by language hint
        status: Filter by status (default: active)

    Returns:
        List of station summaries
    """
    try:
        with get_connection() as conn:
            source_repo = RadioSourceRepository(conn)

            if status == "active":
                sources = source_repo.list_active(country=country, lang_hint=lang_hint)
            else:
                # Would need to add method for other statuses
                sources = source_repo.list_active(country=country, lang_hint=lang_hint)

            return [
                StationSummary(
                    id=s["id"],
                    name=s["name"],
                    country=s["country"] or "",
                    lang_hint=s.get("lang_hint"),
                    status=s["status"],
                    last_check=s["last_check"].isoformat() if s.get("last_check") else None,
                    last_successful_capture=(
                        s["last_successful_capture"].isoformat()
                        if s.get("last_successful_capture")
                        else None
                    ),
                    health_status=s.get("health_status"),
                    health_last_error=s.get("health_last_error"),
                    health_last_failure_at=(
                        s["health_last_failure_at"].isoformat()
                        if s.get("health_last_failure_at")
                        else None
                    ),
                    health_consecutive_failures=s.get("health_consecutive_failures"),
                    health_last_success_at=(
                        s["health_last_success_at"].isoformat()
                        if s.get("health_last_success_at")
                        else None
                    ),
                    frequency_mhz=s.get("frequency_mhz"),
                    frequency_label=s.get("frequency_label"),
                    frequency_source=s.get("frequency_source"),
                    frequency_confidence=s.get("frequency_confidence"),
                )
                for s in sources
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list stations: {str(e)}")


@app.get("/api/discovery/runs", response_model=List[DiscoveryRunRow])
async def get_discovery_runs(limit: int = 20):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        dr.id,
                        ds.name AS source_name,
                        ds.source_type,
                        dr.country,
                        dr.status,
                        dr.stats,
                        dr.started_at,
                        dr.finished_at,
                        dr.error_message
                    FROM discovery_runs dr
                    JOIN discovery_sources ds ON ds.id = dr.source_id
                    ORDER BY dr.id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        results = []
        for row in rows:
            results.append(
                DiscoveryRunRow(
                    id=row["id"],
                    source_name=row["source_name"],
                    source_type=row["source_type"],
                    country=row["country"],
                    status=row["status"],
                    stats=_parse_json_field(row["stats"]) or {},
                    started_at=row["started_at"].isoformat() if row.get("started_at") else None,
                    finished_at=row["finished_at"].isoformat() if row.get("finished_at") else None,
                    error_message=row.get("error_message"),
                )
            )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch discovery runs: {str(exc)}")


@app.get("/api/discovery/summary", response_model=List[DiscoverySummaryRow])
async def get_discovery_summary():
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        ds.name AS source_name,
                        ds.source_type,
                        COUNT(*) AS runs,
                        COALESCE(SUM((dr.stats->>'discovered')::int), 0) AS total_discovered,
                        COALESCE(SUM((dr.stats->>'inserted')::int), 0) AS total_inserted,
                        MAX(dr.finished_at) AS last_finished
                    FROM discovery_runs dr
                    JOIN discovery_sources ds ON ds.id = dr.source_id
                    GROUP BY ds.name, ds.source_type
                    ORDER BY total_discovered DESC
                    """
                )
                rows = cur.fetchall()
        results = []
        for row in rows:
            results.append(
                DiscoverySummaryRow(
                    source_name=row["source_name"],
                    source_type=row["source_type"],
                    runs=int(row["runs"]),
                    total_discovered=int(row["total_discovered"]),
                    total_inserted=int(row["total_inserted"]),
                    last_finished=(
                        row["last_finished"].isoformat() if row.get("last_finished") else None
                    ),
                )
            )
        return results
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch discovery summary: {str(exc)}"
        )


@app.get("/api/discovery/coverage", response_model=DiscoveryCoverageReport)
async def get_discovery_coverage():
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT report
                    FROM discovery_coverage_reports
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
        report = _parse_json_field(row["report"]) if row else None
        if not report:
            report = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "countries": [],
            }
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch discovery coverage: {str(exc)}"
        )


@app.post("/api/discovery/coverage/refresh", response_model=DiscoveryCoverageReport)
async def refresh_discovery_coverage():
    try:
        with get_connection() as conn:
            sources = fetch_coverage_sources(conn)
            target_countries = fetch_target_countries(sources)
            report = build_coverage_report(conn, target_countries)
            store_coverage_report(conn, target_countries, report)
            conn.commit()
        return report
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Failed to refresh discovery coverage: {str(exc)}"
        )


@app.get("/api/languages/unmapped", response_model=List[UnmappedLanguageLabel])
async def get_unmapped_language_labels(limit: int = 20):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT primary_lang_raw AS label, COUNT(*) AS count
                    FROM radio_segments
                    WHERE primary_lang_raw IS NOT NULL
                      AND primary_lang_iso639_3 IS NULL
                    GROUP BY primary_lang_raw
                    ORDER BY count DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        return [
            UnmappedLanguageLabel(label=row["label"], count=int(row["count"] or 0)) for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch unmapped labels: {str(exc)}")


@app.get("/api/languages/taxonomy", response_model=List[LanguageTaxonomyRow])
async def get_language_taxonomy():
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT iso639_3, iso639_1, name
                    FROM language_taxonomy
                    ORDER BY name
                    """
                )
                rows = cur.fetchall()
        return [
            LanguageTaxonomyRow(
                iso639_3=row["iso639_3"],
                iso639_1=row.get("iso639_1"),
                name=row["name"],
            )
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch taxonomy: {str(exc)}")


@app.get("/api/languages/label-map", response_model=List[LanguageLabelMapRow])
async def list_language_label_map(limit: int = 200):
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT observed_label, canonical_iso639_3, source, confidence, notes
                    FROM language_label_map
                    ORDER BY observed_label
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        return [
            LanguageLabelMapRow(
                observed_label=row["observed_label"],
                canonical_iso639_3=row.get("canonical_iso639_3"),
                source=row.get("source"),
                confidence=row.get("confidence"),
                notes=row.get("notes"),
            )
            for row in rows
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch label map: {str(exc)}")


@app.post("/api/languages/label-map", response_model=LanguageLabelMapRow)
async def upsert_language_label_map(payload: LanguageLabelMapRequest):
    if not payload.observed_label:
        raise HTTPException(status_code=400, detail="observed_label is required")

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if payload.canonical_iso639_3:
                cur.execute(
                    """
                    SELECT 1
                    FROM language_taxonomy
                    WHERE iso639_3 = %s
                    """,
                    (payload.canonical_iso639_3,),
                )
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown ISO-639-3 code: {payload.canonical_iso639_3}",
                    )

            cur.execute(
                """
                INSERT INTO language_label_map (
                    observed_label, canonical_iso639_3, source, confidence, notes
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (observed_label) DO UPDATE
                SET canonical_iso639_3 = EXCLUDED.canonical_iso639_3,
                    source = EXCLUDED.source,
                    confidence = EXCLUDED.confidence,
                    notes = EXCLUDED.notes
                RETURNING observed_label, canonical_iso639_3, source, confidence, notes
                """,
                (
                    payload.observed_label,
                    payload.canonical_iso639_3,
                    payload.source,
                    payload.confidence,
                    payload.notes,
                ),
            )
            row = cur.fetchone()

        pipeline_repo = PipelineEventRepository(conn)
        pipeline_repo.insert(
            stage="lid",
            event_type="label_map_updated",
            status="success",
            message="Language label mapping updated",
            payload={
                "observed_label": payload.observed_label,
                "canonical_iso639_3": payload.canonical_iso639_3,
                "source": payload.source,
                "confidence": payload.confidence,
            },
        )
        conn.commit()

    return LanguageLabelMapRow(
        observed_label=row["observed_label"],
        canonical_iso639_3=row.get("canonical_iso639_3"),
        source=row.get("source"),
        confidence=row.get("confidence"),
        notes=row.get("notes"),
    )


@app.get("/api/pipeline/errors", response_model=List[PipelineErrorRow])
async def get_pipeline_errors(limit: int = 20, hours: int = 24):
    try:
        window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        ev.stage,
                        ev.event_type,
                        ev.status,
                        ev.message,
                        ev.payload,
                        ev.source_id,
                        src.name AS station_name,
                        ev.created_at
                    FROM pipeline_events ev
                    LEFT JOIN radio_sources src ON src.id = ev.source_id
                    WHERE ev.created_at >= %s
                      AND ev.status IN ('error', 'warn')
                    ORDER BY ev.created_at DESC
                    LIMIT %s
                    """,
                    (window_start, limit),
                )
                rows = cur.fetchall()

        results = []
        for row in rows:
            payload = _parse_json_field(row.get("payload")) or {}
            results.append(
                PipelineErrorRow(
                    stage=row.get("stage"),
                    event_type=row.get("event_type"),
                    status=row.get("status"),
                    message=row.get("message"),
                    error_kind=payload.get("error_kind"),
                    error_detail=payload.get("error_detail"),
                    source_id=row.get("source_id"),
                    station_name=row.get("station_name"),
                    created_at=(
                        row.get("created_at").isoformat()
                        if row.get("created_at")
                        else datetime.now(timezone.utc).isoformat()
                    ),
                )
            )
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch errors: {str(exc)}")


@app.get("/api/summary/today")
async def get_summary_today(hours: int = 24):
    """Summary for the last N hours"""
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        with get_connection() as conn:
            source_repo = RadioSourceRepository(conn)

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        DATE_TRUNC('hour', start_ts) AS hour,
                        SUM(duration) / 60.0 AS captured_minutes,
                        SUM(duration * COALESCE(speech_ratio, 0)) / 60.0 AS speech_minutes
                    FROM radio_shards
                    WHERE start_ts >= %s
                    GROUP BY 1
                    ORDER BY 1
                    """,
                    (window_start,),
                )
                timeseries = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT DATE_TRUNC('hour', created_at) AS hour, COUNT(*) AS segments
                    FROM radio_segments
                    WHERE created_at >= %s
                    GROUP BY 1
                    ORDER BY 1
                    """,
                    (window_start,),
                )
                segment_series = {row["hour"]: int(row["segments"]) for row in cur.fetchall()}

                cur.execute(
                    """
                    SELECT COUNT(*) AS segments_created
                    FROM radio_segments
                    WHERE created_at >= %s
                    """,
                    (window_start,),
                )
                segment_row = cur.fetchone()
                segments_created = int(segment_row["segments_created"]) if segment_row else 0

                cur.execute(
                    """
                    SELECT
                        primary_lang,
                        SUM(duration) / 60.0 AS minutes,
                        COUNT(*) AS segments
                    FROM radio_segments
                    WHERE created_at >= %s
                    GROUP BY 1
                    ORDER BY minutes DESC
                    LIMIT 6
                    """,
                    (window_start,),
                )
                top_languages = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT
                        SUM(duration) / 3600.0 AS hours_recorded,
                        SUM(duration * COALESCE(speech_ratio, 0)) / 3600.0 AS speech_hours
                    FROM radio_shards
                    WHERE start_ts >= %s
                    """,
                    (window_start,),
                )
                hours_row = cur.fetchone() or {}

                cur.execute(
                    """
                    SELECT language, COUNT(*) AS total
                    FROM segment_language_verifications
                    WHERE created_at >= %s
                    GROUP BY 1
                    ORDER BY total DESC
                    LIMIT 6
                    """,
                    (window_start,),
                )
                verification_languages = [dict(row) for row in cur.fetchall()]

                cur.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM segment_language_verifications
                    WHERE created_at >= %s
                    """,
                    (window_start,),
                )
                verification_total_row = cur.fetchone() or {}

            sources_active = len(source_repo.list_active())

            return {
                "window_hours": hours,
                "counts": {
                    "sources_active": sources_active,
                    "hours_recorded": float(hours_row.get("hours_recorded") or 0),
                    "speech_hours": float(hours_row.get("speech_hours") or 0),
                    "segments_created": segments_created,
                    "learner_ready_pct": None,
                },
                "timeseries": [
                    {
                        "ts": row["hour"].isoformat(),
                        "captured_minutes": float(row["captured_minutes"] or 0),
                        "speech_minutes": float(row["speech_minutes"] or 0),
                        "segments": segment_series.get(row["hour"], 0),
                    }
                    for row in timeseries
                ],
                "top_languages": [
                    {
                        "lang": row["primary_lang"] or "unknown",
                        "minutes": float(row["minutes"] or 0),
                        "segments": int(row["segments"] or 0),
                    }
                    for row in top_languages
                ],
                "verification_summary": {
                    "total": int(verification_total_row.get("total") or 0),
                    "top_languages": [
                        {
                            "lang": row.get("language") or "unknown",
                            "count": int(row.get("total") or 0),
                        }
                        for row in verification_languages
                    ],
                },
                "errors_by_stage": [
                    {"stage": "capture", "count": 0},
                    {"stage": "lid", "count": 0},
                    {"stage": "segments", "count": 0},
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load summary: {str(e)}")


@app.get("/api/stations")
async def list_station_summaries():
    """List stations with most recent hourly stats"""
    try:
        with get_connection() as conn:
            source_repo = RadioSourceRepository(conn)
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        src.*,
                        hourly.primary_lang AS primary_lang,
                        hourly.lang_mix AS lang_mix,
                        hourly.switch_rate AS switch_rate,
                        hourly.speech_ratio AS speech_ratio
                    FROM radio_sources src
                    LEFT JOIN LATERAL (
                        SELECT primary_lang, lang_mix, switch_rate, speech_ratio
                        FROM radio_station_hourly
                        WHERE source_id = src.id
                        ORDER BY hour DESC
                        LIMIT 1
                    ) AS hourly ON TRUE
                    WHERE src.status = 'active'
                    ORDER BY src.name
                    """
                )
                rows = cur.fetchall()
                results = []
                for row in rows:
                    lang_mix = _parse_json_field(row.get("lang_mix"))
                    tags = _parse_json_field(row.get("tags"))
                    results.append(
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "stream_url": row.get("stream_url"),
                            "homepage": row.get("homepage"),
                            "bitrate": row.get("bitrate"),
                            "codec": row.get("codec"),
                            "frequency_mhz": row.get("frequency_mhz"),
                            "frequency_label": row.get("frequency_label"),
                            "frequency_source": row.get("frequency_source"),
                            "frequency_confidence": row.get("frequency_confidence"),
                            "country": row.get("country"),
                            "lang_hint": row.get("lang_hint"),
                            "status": row.get("status"),
                            "last_check": (
                                row.get("last_check").isoformat() if row.get("last_check") else None
                            ),
                            "last_successful_capture": (
                                row.get("last_successful_capture").isoformat()
                                if row.get("last_successful_capture")
                                else None
                            ),
                            "health_status": row.get("health_status"),
                            "health_last_error": row.get("health_last_error"),
                            "health_last_failure_at": (
                                row.get("health_last_failure_at").isoformat()
                                if row.get("health_last_failure_at")
                                else None
                            ),
                            "health_consecutive_failures": row.get("health_consecutive_failures"),
                            "health_last_success_at": (
                                row.get("health_last_success_at").isoformat()
                                if row.get("health_last_success_at")
                                else None
                            ),
                            "primary_lang": row.get("primary_lang"),
                            "speech_ratio": row.get("speech_ratio"),
                            "lang_mix": lang_mix if isinstance(lang_mix, dict) else None,
                            "switch_rate": row.get("switch_rate"),
                            "tags": tags if isinstance(tags, list) else [],
                            "station_uuid": row.get("station_uuid"),
                            "votes": row.get("votes"),
                            "clickcount": row.get("clickcount"),
                        }
                    )
                return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list stations: {str(e)}")


def _fetch_pipeline_activity(conn, window_start: datetime, source_id: Optional[int] = None):
    params = [window_start]
    source_clause = ""
    if source_id is not None:
        source_clause = " AND source_id = %s"
        params.append(source_id)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                DATE_TRUNC('hour', created_at) AS hour,
                stage,
                COALESCE(SUM(count), 0) AS count,
                COALESCE(SUM(duration_seconds), 0) AS duration_seconds
            FROM pipeline_events
            WHERE created_at >= %s{source_clause}
            GROUP BY 1, 2
            ORDER BY 1, 2
            """,
            params,
        )
        series = [dict(row) for row in cur.fetchall()]

        cur.execute(
            f"""
            SELECT
                stage,
                MAX(created_at) AS last_seen,
                COALESCE(SUM(count), 0) AS total_count
            FROM pipeline_events
            WHERE created_at >= %s{source_clause}
            GROUP BY 1
            ORDER BY total_count DESC
            """,
            params,
        )
        stages = [dict(row) for row in cur.fetchall()]

    return series, stages


def _fetch_capture_health(conn, window_start: datetime):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN event_type = 'shard_captured' THEN 1 ELSE 0 END), 0) AS captures,
                COALESCE(SUM(CASE WHEN event_type = 'capture_failed' THEN 1 ELSE 0 END), 0) AS failures
            FROM pipeline_events
            WHERE created_at >= %s AND stage = 'capture'
            """,
            (window_start,),
        )
        summary = cur.fetchone() or {}

        cur.execute(
            """
            SELECT COUNT(*) AS shard_count,
                   COUNT(DISTINCT source_id) AS station_count
            FROM radio_shards
            WHERE created_at >= %s
            """,
            (window_start,),
        )
        shard_counts = cur.fetchone() or {}

        cur.execute(
            """
            SELECT
                shard.id,
                shard.source_id,
                src.name AS station_name,
                shard.start_ts,
                shard.duration,
                shard.capture_status
            FROM radio_shards shard
            JOIN radio_sources src ON src.id = shard.source_id
            ORDER BY shard.start_ts DESC
            LIMIT 6
            """
        )
        recent = [dict(row) for row in cur.fetchall()]

    return {
        "captures": int(summary.get("captures") or 0),
        "failures": int(summary.get("failures") or 0),
        "shard_count": int(shard_counts.get("shard_count") or 0),
        "station_count": int(shard_counts.get("station_count") or 0),
        "recent_shards": [
            {
                "id": row["id"],
                "source_id": row["source_id"],
                "station_name": row["station_name"],
                "start_ts": row["start_ts"].isoformat() if row.get("start_ts") else None,
                "duration": float(row.get("duration") or 0),
                "capture_status": row.get("capture_status"),
            }
            for row in recent
        ],
    }


def _fetch_station_listening(conn, station_id: int, days: int):
    repo = RadioStationDaypartRepository(conn)
    rows = repo.list_for_source(station_id, days=days)
    totals = {"total_seconds": 0.0, "speech_seconds": 0.0, "shard_count": 0}
    dayparts: Dict[str, Dict[str, float]] = {}

    for row in rows:
        totals["total_seconds"] += float(row.get("total_seconds") or 0)
        totals["speech_seconds"] += float(row.get("speech_seconds") or 0)
        totals["shard_count"] += int(row.get("shard_count") or 0)
        daypart = row.get("daypart") or "unknown"
        bucket = dayparts.setdefault(
            daypart,
            {"total_seconds": 0.0, "speech_seconds": 0.0, "shard_count": 0},
        )
        bucket["total_seconds"] += float(row.get("total_seconds") or 0)
        bucket["speech_seconds"] += float(row.get("speech_seconds") or 0)
        bucket["shard_count"] += int(row.get("shard_count") or 0)

    return {
        "days": days,
        "totals": totals,
        "dayparts": dayparts,
    }


@app.get("/api/pipeline/activity")
async def get_pipeline_activity(hours: int = 24):
    """Get pipeline activity for the last N hours"""
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        with get_connection() as conn:
            series, stages = _fetch_pipeline_activity(conn, window_start)
            capture_health = _fetch_capture_health(conn, window_start)

        return {
            "window_hours": hours,
            "series": [
                {
                    "hour": row["hour"].isoformat(),
                    "stage": row["stage"],
                    "count": int(row["count"] or 0),
                    "duration_seconds": float(row["duration_seconds"] or 0),
                }
                for row in series
            ],
            "stages": [
                {
                    "stage": row["stage"],
                    "last_seen": row["last_seen"].isoformat() if row.get("last_seen") else None,
                    "total_count": int(row["total_count"] or 0),
                }
                for row in stages
            ],
            "capture_health": capture_health,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load pipeline activity: {str(e)}")


@app.get("/api/stations/{station_id}/activity")
async def get_station_activity(station_id: int, hours: int = 24):
    """Get pipeline activity for a specific station"""
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        with get_connection() as conn:
            series, stages = _fetch_pipeline_activity(conn, window_start, source_id=station_id)

        return {
            "window_hours": hours,
            "series": [
                {
                    "hour": row["hour"].isoformat(),
                    "stage": row["stage"],
                    "count": int(row["count"] or 0),
                    "duration_seconds": float(row["duration_seconds"] or 0),
                }
                for row in series
            ],
            "stages": [
                {
                    "stage": row["stage"],
                    "last_seen": row["last_seen"].isoformat() if row.get("last_seen") else None,
                    "total_count": int(row["total_count"] or 0),
                }
                for row in stages
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load station activity: {str(e)}")


@app.get("/api/stations/{station_id}/quality", response_model=StationQualityResponse)
async def get_station_quality(station_id: int, hours: int = 24):
    """Get audio quality rollups for a station."""
    window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
    try:
        with get_connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS shard_count,
                        AVG(bitrate) AS avg_bitrate,
                        STDDEV_POP(bitrate) AS bitrate_stddev,
                        AVG(silence_ratio) AS avg_silence_ratio,
                        AVG(duration_ratio) AS avg_duration_ratio,
                        SUM(
                            CASE
                                WHEN duration_ratio IS NOT NULL
                                     AND duration_ratio < 0.9 THEN 1
                                ELSE 0
                            END
                        ) AS dropout_count,
                        MAX(created_at) AS last_shard_at
                    FROM radio_shards
                    WHERE source_id = %s
                      AND created_at >= %s
                    """,
                    (station_id, window_start),
                )
                shard_row = cur.fetchone() or {}
                cur.execute(
                    """
                    SELECT
                        COUNT(*) AS capture_failures,
                        SUM(
                            CASE
                                WHEN payload->>'error_kind' = 'ffmpeg_error' THEN 1
                                ELSE 0
                            END
                        ) AS ffmpeg_errors
                    FROM pipeline_events
                    WHERE source_id = %s
                      AND created_at >= %s
                      AND stage = 'capture'
                      AND event_type = 'capture_failed'
                    """,
                    (station_id, window_start),
                )
                error_row = cur.fetchone() or {}

        return StationQualityResponse(
            window_hours=hours,
            shard_count=int(shard_row.get("shard_count") or 0),
            avg_bitrate_kbps=(
                float(shard_row["avg_bitrate"])
                if shard_row.get("avg_bitrate") is not None
                else None
            ),
            bitrate_stddev_kbps=(
                float(shard_row["bitrate_stddev"])
                if shard_row.get("bitrate_stddev") is not None
                else None
            ),
            avg_silence_ratio=(
                float(shard_row["avg_silence_ratio"])
                if shard_row.get("avg_silence_ratio") is not None
                else None
            ),
            avg_duration_ratio=(
                float(shard_row["avg_duration_ratio"])
                if shard_row.get("avg_duration_ratio") is not None
                else None
            ),
            dropout_count=int(shard_row.get("dropout_count") or 0),
            capture_failures=int(error_row.get("capture_failures") or 0),
            ffmpeg_errors=int(error_row.get("ffmpeg_errors") or 0),
            last_shard_at=(
                shard_row.get("last_shard_at").isoformat()
                if shard_row.get("last_shard_at")
                else None
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load station quality: {str(e)}")


@app.get("/api/stations/{station_id}/listening")
async def get_station_listening(station_id: int, days: int = 7):
    """Get listening totals and daypart aggregates for a station"""
    try:
        with get_connection() as conn:
            listening = _fetch_station_listening(conn, station_id, days)
        return {"station_id": station_id, **listening}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load listening stats: {str(e)}")


@app.get("/api/capture-targets")
async def get_capture_targets():
    try:
        with get_connection() as conn:
            repo = CaptureTargetRepository(conn)
            target = repo.get_active()
        return target or {"countries": [], "languages": [], "active": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load capture targets: {str(e)}")


@app.put("/api/capture-targets")
async def update_capture_targets(payload: Dict[str, Any]):
    try:
        countries = [c.strip().upper() for c in payload.get("countries", []) if c.strip()]
        languages = [l.strip().lower() for l in payload.get("languages", []) if l.strip()]
        notes = payload.get("notes")
        with get_connection() as conn:
            repo = CaptureTargetRepository(conn)
            target_id = repo.upsert(countries=countries, languages=languages, notes=notes)
        return {"id": target_id, "countries": countries, "languages": languages, "active": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update capture targets: {str(e)}")


@app.get("/stations/{station_id}/shards")
async def get_station_shards(station_id: int, limit: int = 10):
    """Get shards for a station"""
    try:
        with get_connection() as conn:
            shard_repo = RadioShardRepository(conn)
            shards = shard_repo.get_by_source(station_id, limit=limit)

            return {"station_id": station_id, "shards": shards}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get shards: {str(e)}")


@app.get("/stations/{station_id}/segments")
async def get_station_segments(station_id: int, limit: int = 100):
    """Get segments for a station (via shards)"""
    try:
        with get_connection() as conn:
            shard_repo = RadioShardRepository(conn)
            segment_repo = RadioSegmentRepository(conn)

            # Get recent shards
            shards = shard_repo.get_by_source(station_id, limit=10)

            all_segments = []
            for shard in shards[:5]:  # Limit to 5 most recent shards
                segments = segment_repo.get_by_shard(shard["id"])
                all_segments.extend(segments)

            # Sort by created_at and limit
            all_segments.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)

            return {"station_id": station_id, "segments": all_segments[:limit]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get segments: {str(e)}")


@app.get("/stations/{station_id}/hourly")
async def get_station_hourly(station_id: int, hours: int = 24):
    """Get hourly language aggregates for a station"""
    try:
        with get_connection() as conn:
            hourly_repo = RadioStationHourlyRepository(conn)

            # Would need to add method to get hourly data
            # For now, return placeholder
            return {
                "station_id": station_id,
                "hours": hours,
                "note": "Hourly aggregation endpoint - implementation pending",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hourly stats: {str(e)}")


@app.get("/api/stations/{station_id}/hours")
async def get_station_hours_api(station_id: int, hours: int = 24):
    """Get hourly language aggregates for a station"""
    try:
        with get_connection() as conn:
            hourly_repo = RadioStationHourlyRepository(conn)
            rows = hourly_repo.list_for_source(station_id, hours=hours)
            for row in rows:
                if isinstance(row.get("lang_mix"), str):
                    row["lang_mix"] = json.loads(row["lang_mix"])
            return {
                "station_id": station_id,
                "hours": hours,
                "rows": [
                    {
                        "hour": row["hour"].isoformat(),
                        "primary_lang": row.get("primary_lang"),
                        "lang_mix": row.get("lang_mix") or {},
                        "switch_rate": row.get("switch_rate"),
                        "speech_ratio": row.get("speech_ratio"),
                    }
                    for row in rows
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get hourly stats: {str(e)}")


@app.get("/api/segments/search")
async def search_segments(
    lang: Optional[str] = None,
    confidence_min: Optional[float] = None,
    station_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Search segments with filters"""
    try:
        parsed_date_from = datetime.fromisoformat(date_from) if date_from else None
        parsed_date_to = datetime.fromisoformat(date_to) if date_to else None
        with get_connection() as conn:
            segment_repo = RadioSegmentRepository(conn)
            rows = segment_repo.search(
                lang=lang,
                confidence_min=confidence_min,
                station_id=station_id,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
                limit=limit,
                offset=offset,
            )
            total = segment_repo.count(
                lang=lang,
                confidence_min=confidence_min,
                station_id=station_id,
                date_from=parsed_date_from,
                date_to=parsed_date_to,
            )

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "rows": [
                    {
                        "id": row["id"],
                        "shard_id": row["shard_id"],
                        "source_id": row["source_id"],
                        "station_name": row["station_name"],
                        "shard_start_ts": row["shard_start_ts"].isoformat(),
                        "segment_start": row["start"],
                        "segment_end": row["end"],
                        "duration": row.get("duration"),
                        "primary_lang": row.get("primary_lang"),
                        "confidence": row.get("confidence"),
                        "is_speech": row.get("is_speech"),
                        "music_prob": row.get("music_prob"),
                        "lang_probs": row.get("lang_probs"),
                        "created_at": (
                            row.get("created_at").isoformat() if row.get("created_at") else None
                        ),
                        "shard_path": row.get("shard_path"),
                        "shard_s3_url": row.get("shard_s3_url"),
                        "segment_path": row.get("path"),
                    }
                    for row in rows
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search segments: {str(e)}")


@app.get("/api/segments/{segment_id}")
async def get_segment_detail(segment_id: int):
    """Get detailed segment information"""
    try:
        with get_connection() as conn:
            segment_repo = RadioSegmentRepository(conn)
            source_repo = RadioSourceRepository(conn)
            segment = segment_repo.get_by_id(segment_id)
            if not segment:
                raise HTTPException(status_code=404, detail="Segment not found")

            source = source_repo.get_by_id(segment["source_id"])
            if source:
                source["lang_mix"] = _parse_json_field(source.get("lang_mix"))

            return {
                "segment": {
                    "id": segment["id"],
                    "shard_id": segment["shard_id"],
                    "source_id": segment["source_id"],
                    "station_name": segment["station_name"],
                    "shard_start_ts": segment["shard_start_ts"].isoformat(),
                    "segment_start": segment["start"],
                    "segment_end": segment["end"],
                    "duration": segment.get("duration"),
                    "primary_lang": segment.get("primary_lang"),
                    "confidence": segment.get("confidence"),
                    "is_speech": segment.get("is_speech"),
                    "music_prob": segment.get("music_prob"),
                    "lang_probs": segment.get("lang_probs"),
                    "created_at": (
                        segment.get("created_at").isoformat() if segment.get("created_at") else None
                    ),
                    "shard_path": segment.get("shard_path"),
                    "shard_s3_url": segment.get("shard_s3_url"),
                    "segment_path": segment.get("path"),
                },
                "source": (
                    {
                        "id": source["id"],
                        "name": source["name"],
                        "country": source.get("country"),
                        "lang_hint": source.get("lang_hint"),
                        "status": source.get("status"),
                        "last_check": (
                            source.get("last_check").isoformat()
                            if source.get("last_check")
                            else None
                        ),
                        "last_successful_capture": (
                            source.get("last_successful_capture").isoformat()
                            if source.get("last_successful_capture")
                            else None
                        ),
                        "primary_lang": None,
                        "speech_ratio": None,
                        "lang_mix": None,
                        "switch_rate": None,
                    }
                    if source
                    else None
                ),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get segment: {str(e)}")


@app.get("/stats")
async def get_service_stats():
    """Get service statistics"""
    try:
        stats = {}

        if service_instance:
            if service_instance.task_queue:
                stats["task_queue"] = service_instance.task_queue.get_queue_stats()

            if service_instance.scheduler:
                stats["scheduler"] = service_instance.scheduler.get_stats()

            if service_instance.backpressure:
                stats["backpressure"] = service_instance.backpressure.get_status()

        # Database stats
        with get_connection() as conn:
            source_repo = RadioSourceRepository(conn)
            shard_repo = RadioShardRepository(conn)

            sources = source_repo.list_active()

            total_shards = 0
            for source in sources[:10]:  # Sample first 10
                shards = shard_repo.get_by_source(source["id"], limit=1000)
                total_shards += len(shards)

            stats["database"] = {
                "active_sources": len(sources),
                "total_shards_sample": total_shards,
            }

        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


def create_app(service: Optional[RadioIngestionService] = None) -> FastAPI:
    """Factory function to create app with service"""
    global service_instance
    service_instance = service
    return app
