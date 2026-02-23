"""Repository classes for radio ingestion database operations"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import psycopg
import structlog
from mumbl_storage.repositories import PipelineEventRepository
from psycopg.rows import dict_row

logger = structlog.get_logger(__name__)

FREQUENCY_SOURCE_PRIORITY = {
    "manual": 5,
    "regulator": 4,
    "wikidata": 3,
    "llm": 2,
    "heuristic": 1,
}


def _extract_frequency(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    match = re.search(r"(?P<freq>\d{2,3}(?:\.\d)?)\s*(?:mhz|fm)?", text, re.IGNORECASE)
    if not match:
        return None
    try:
        value = float(match.group("freq"))
    except ValueError:
        return None
    if value < 60 or value > 110:
        return None
    label = match.group(0).strip()
    return {"frequency_mhz": value, "frequency_label": label}


def _emit_event(
    conn: psycopg.Connection,
    stage: str,
    event_type: str,
    status: str,
    source_id: Optional[int] = None,
    shard_id: Optional[int] = None,
    segment_id: Optional[int] = None,
    count: Optional[int] = None,
    duration_seconds: Optional[float] = None,
    message: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        PipelineEventRepository(conn).insert(
            stage=stage,
            event_type=event_type,
            status=status,
            source_id=source_id,
            shard_id=shard_id,
            segment_id=segment_id,
            count=count,
            duration_seconds=duration_seconds,
            message=message,
            payload=payload,
        )
    except Exception as exc:
        logger.warning("Failed to emit pipeline event", error=str(exc), event_type=event_type)


class RadioSourceRepository:
    """Repository for radio_sources table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, source_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a radio source, returns ID or None if duplicate.

        Args:
            source_data: Dictionary with source fields

        Returns:
            Source ID if inserted, None if duplicate
        """
        insert_query = """
            INSERT INTO radio_sources (
                name, stream_url, country, timezone, lang_hint,
                bitrate, codec, station_uuid, homepage, tags,
                status, last_check
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (stream_url) DO UPDATE SET
                name = EXCLUDED.name,
                country = EXCLUDED.country,
                timezone = EXCLUDED.timezone,
                lang_hint = EXCLUDED.lang_hint,
                bitrate = EXCLUDED.bitrate,
                codec = EXCLUDED.codec,
                homepage = EXCLUDED.homepage,
                tags = EXCLUDED.tags,
                last_check = EXCLUDED.last_check,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
        """
        params = (
            source_data["name"],
            source_data["stream_url"],
            source_data.get("country"),
            source_data.get("timezone"),
            source_data.get("lang_hint"),
            source_data.get("bitrate"),
            source_data.get("codec"),
            source_data.get("station_uuid"),
            source_data.get("homepage"),
            json.dumps(source_data.get("tags", [])),
            "active",
            datetime.now(timezone.utc),
        )
        update_query = """
            UPDATE radio_sources
            SET
                name = %s,
                stream_url = %s,
                country = %s,
                timezone = %s,
                lang_hint = %s,
                bitrate = %s,
                codec = %s,
                homepage = %s,
                tags = %s,
                last_check = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE station_uuid = %s
            RETURNING id
        """

        with self.conn.cursor() as cur:
            try:
                cur.execute(insert_query, params)
                result = cur.fetchone()
                source_id = result[0] if result else None
                if source_id:
                    self._record_heuristic_frequency(source_id, source_data)
                    _emit_event(
                        self.conn,
                        stage="discovery",
                        event_type="source_upserted",
                        status="success",
                        source_id=source_id,
                        count=1,
                        message="Radio source upserted",
                        payload={
                            "station_uuid": source_data.get("station_uuid"),
                            "stream_url": source_data.get("stream_url"),
                            "country": source_data.get("country"),
                            "lang_hint": source_data.get("lang_hint"),
                        },
                    )
                return source_id
            except psycopg.errors.UniqueViolation:
                self.conn.rollback()
                station_uuid = source_data.get("station_uuid")
                if not station_uuid:
                    return None
                cur.execute(
                    update_query,
                    (
                        source_data["name"],
                        source_data["stream_url"],
                        source_data.get("country"),
                        source_data.get("timezone"),
                        source_data.get("lang_hint"),
                        source_data.get("bitrate"),
                        source_data.get("codec"),
                        source_data.get("homepage"),
                        json.dumps(source_data.get("tags", [])),
                        datetime.now(timezone.utc),
                        station_uuid,
                    ),
                )
                result = cur.fetchone()
                source_id = result[0] if result else None
                if source_id:
                    self._record_heuristic_frequency(source_id, source_data)
                    _emit_event(
                        self.conn,
                        stage="discovery",
                        event_type="source_upserted",
                        status="success",
                        source_id=source_id,
                        count=1,
                        message="Radio source updated",
                        payload={
                            "station_uuid": station_uuid,
                            "stream_url": source_data.get("stream_url"),
                            "country": source_data.get("country"),
                            "lang_hint": source_data.get("lang_hint"),
                        },
                    )
                return source_id

    def _record_heuristic_frequency(self, source_id: int, source_data: Dict[str, Any]) -> None:
        text_bits = [source_data.get("name", "")]
        tags = source_data.get("tags") or []
        if isinstance(tags, list):
            text_bits.extend(tags)
        text = " ".join([bit for bit in text_bits if bit])
        candidate = _extract_frequency(text)
        if not candidate:
            return
        RadioFrequencyCandidateRepository(self.conn).insert(
            source_id=source_id,
            frequency_mhz=candidate["frequency_mhz"],
            frequency_label=candidate["frequency_label"],
            source="heuristic",
            confidence=0.35,
            evidence_text=text[:200],
        )
        RadioFrequencyCandidateRepository(self.conn).resolve_best_for_source(source_id)

    def update_frequency(
        self,
        source_id: int,
        frequency_mhz: Optional[float],
        frequency_label: Optional[str],
        frequency_source: Optional[str],
        frequency_confidence: Optional[float],
    ) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE radio_sources
                SET
                    frequency_mhz = %s,
                    frequency_label = %s,
                    frequency_source = %s,
                    frequency_confidence = %s,
                    frequency_updated_at = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    frequency_mhz,
                    frequency_label,
                    frequency_source,
                    frequency_confidence,
                    datetime.now(timezone.utc),
                    source_id,
                ),
            )

    def insert_many(self, sources: List[Dict[str, Any]]) -> List[Optional[int]]:
        """Insert multiple sources, returns list of IDs"""
        ids = []
        for source in sources:
            source_id = self.insert(source)
            ids.append(source_id)
        return ids

    def get_by_id(self, source_id: int) -> Optional[Dict[str, Any]]:
        """Get source by ID"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT * FROM radio_sources WHERE id = %s", (source_id,))
            row = cur.fetchone()
            if row:
                # Parse JSONB tags
                if isinstance(row["tags"], str):
                    row["tags"] = json.loads(row["tags"])
                elif row["tags"] is None:
                    row["tags"] = []
            return dict(row) if row else None

    def list_active(
        self, country: Optional[str] = None, lang_hint: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List active sources with optional filters"""
        query = "SELECT * FROM radio_sources WHERE status = 'active'"
        params = []

        if country:
            query += " AND country = %s"
            params.append(country)

        if lang_hint:
            query += " AND lang_hint = %s"
            params.append(lang_hint)

        query += " ORDER BY name"

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

            # Parse JSONB tags
            for row in rows:
                if isinstance(row["tags"], str):
                    row["tags"] = json.loads(row["tags"])
                elif row["tags"] is None:
                    row["tags"] = []

            return [dict(row) for row in rows]

    def update_health(
        self,
        source_id: int,
        successful: bool,
        error_message: Optional[str] = None,
        max_consecutive_failures: int = 3,
    ):
        """Update capture health metadata for a source."""
        now = datetime.now(timezone.utc)
        with self.conn.cursor() as cur:
            if successful:
                cur.execute(
                    """
                    UPDATE radio_sources
                    SET last_check = %s,
                        last_successful_capture = %s,
                        health_last_success_at = %s,
                        health_last_error = NULL,
                        health_consecutive_failures = 0,
                        health_status = 'healthy'
                    WHERE id = %s
                    """,
                    (now, now, now, source_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE radio_sources
                    SET last_check = %s,
                        health_last_failure_at = %s,
                        health_last_error = %s,
                        health_consecutive_failures = health_consecutive_failures + 1,
                        health_status = CASE
                            WHEN health_consecutive_failures + 1 >= %s THEN 'down'
                            ELSE 'degraded'
                        END
                    WHERE id = %s
                    """,
                    (now, now, error_message, max_consecutive_failures, source_id),
                )

    def mark_inactive(self, source_id: int, reason: str):
        """Mark a source inactive with a reason."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE radio_sources
                SET status = 'inactive',
                    health_last_error = %s,
                    last_check = %s
                WHERE id = %s
                """,
                (reason, datetime.now(timezone.utc), source_id),
            )


class LanguageLabelMapRepository:
    """Repository for language_label_map table."""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def get_canonical(self, observed_label: str) -> Optional[str]:
        if not observed_label:
            return None
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT canonical_iso639_3
                FROM language_label_map
                WHERE observed_label = %s
                """,
                (observed_label,),
            )
            row = cur.fetchone()
        return row["canonical_iso639_3"] if row else None

    def list_map(self) -> Dict[str, str]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT observed_label, canonical_iso639_3
                FROM language_label_map
                WHERE canonical_iso639_3 IS NOT NULL
                """
            )
            rows = cur.fetchall()
        return {row["observed_label"]: row["canonical_iso639_3"] for row in rows}


class RadioShardRepository:
    """Repository for radio_shards table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, shard_data: Dict[str, Any]) -> int:
        """
        Insert a radio shard, returns ID.

        Args:
            shard_data: Dictionary with shard fields

        Returns:
            Shard ID
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO radio_shards (
                    source_id, start_ts, end_ts, duration,
                    path, s3_url, file_size_bytes,
                    bitrate, codec, sample_rate, channels,
                    actual_duration, duration_ratio,
                    capture_status, speech_ratio, total_segments, speech_segments
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    shard_data["source_id"],
                    shard_data["start_ts"],
                    shard_data["end_ts"],
                    shard_data["duration"],
                    shard_data["path"],
                    shard_data.get("s3_url"),
                    shard_data.get("file_size_bytes"),
                    shard_data.get("bitrate"),
                    shard_data.get("codec"),
                    shard_data.get("sample_rate", 22050),
                    shard_data.get("channels", 1),
                    shard_data.get("actual_duration"),
                    shard_data.get("duration_ratio"),
                    shard_data.get("capture_status", "captured"),
                    shard_data.get("speech_ratio"),
                    shard_data.get("total_segments"),
                    shard_data.get("speech_segments"),
                ),
            )
            shard_id = cur.fetchone()[0]
            _emit_event(
                self.conn,
                stage="capture",
                event_type="shard_captured",
                status="success",
                source_id=shard_data.get("source_id"),
                shard_id=shard_id,
                duration_seconds=shard_data.get("duration"),
                message="Shard captured",
            )
            return shard_id

    def update_status(
        self,
        shard_id: int,
        status: str,
        speech_ratio: Optional[float] = None,
        silence_ratio: Optional[float] = None,
        total_segments: Optional[int] = None,
        speech_segments: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update shard processing status"""
        updates = ["capture_status = %s", "updated_at = CURRENT_TIMESTAMP"]
        params = [status]

        if speech_ratio is not None:
            updates.append("speech_ratio = %s")
            params.append(speech_ratio)

        if silence_ratio is not None:
            updates.append("silence_ratio = %s")
            params.append(silence_ratio)

        if total_segments is not None:
            updates.append("total_segments = %s")
            params.append(total_segments)

        if speech_segments is not None:
            updates.append("speech_segments = %s")
            params.append(speech_segments)

        if error_message is not None:
            updates.append("error_message = %s")
            params.append(error_message)

        query = f"UPDATE radio_shards SET {', '.join(updates)} WHERE id = %s"
        params.append(shard_id)

        with self.conn.cursor() as cur:
            cur.execute(query, params)

        stage_map = {
            "captured": "capture",
            "prefiltered": "prefilter",
            "lid_done": "lid",
            "error": "error",
        }
        stage = stage_map.get(status, "capture")
        _emit_event(
            self.conn,
            stage=stage,
            event_type="shard_status_updated",
            status="success" if status != "error" else "error",
            shard_id=shard_id,
            count=1,
            message=f"Shard status updated to {status}",
            payload={
                "status": status,
                "speech_ratio": speech_ratio,
                "silence_ratio": silence_ratio,
                "total_segments": total_segments,
                "speech_segments": speech_segments,
                "error_message": error_message,
            },
        )

    def update_s3_url(self, shard_id: int, s3_url: str):
        """Update shard with S3 URL"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE radio_shards
                SET s3_url = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """,
                (s3_url, shard_id),
            )

    def get_by_source(self, source_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent shards for a source"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM radio_shards
                WHERE source_id = %s
                ORDER BY start_ts DESC
                LIMIT %s
            """,
                (source_id, limit),
            )
            return [dict(row) for row in cur.fetchall()]


class RadioSegmentRepository:
    """Repository for radio_segments table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, segment_data: Dict[str, Any]) -> int:
        """Insert a radio segment, returns ID"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO radio_segments (
                    shard_id, start_sec, end_sec,
                    is_speech, music_prob,
                    lang_probs, primary_lang, primary_lang_raw, primary_lang_iso639_3, confidence,
                    text_lang, text_confidence,
                    llm_verified_lang, llm_verification_confidence,
                    mfcc_features, path
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    segment_data["shard_id"],
                    segment_data["start"],
                    segment_data["end"],
                    segment_data.get("is_speech", True),
                    segment_data.get("music_prob"),
                    json.dumps(segment_data["lang_probs"]),
                    segment_data.get("primary_lang"),
                    segment_data.get("primary_lang_raw"),
                    segment_data.get("primary_lang_iso639_3"),
                    segment_data.get("confidence"),
                    segment_data.get("text_lang"),
                    segment_data.get("text_confidence"),
                    segment_data.get("llm_verified_lang"),
                    segment_data.get("llm_verification_confidence"),
                    (
                        json.dumps(segment_data.get("mfcc_features"))
                        if segment_data.get("mfcc_features")
                        else None
                    ),
                    segment_data.get("path"),
                ),
            )
            segment_id = cur.fetchone()[0]
            _emit_event(
                self.conn,
                stage="segments",
                event_type="radio_segment_inserted",
                status="success",
                shard_id=segment_data.get("shard_id"),
                segment_id=segment_id,
                count=1,
                message="Radio segment inserted",
                payload={
                    "primary_lang": segment_data.get("primary_lang"),
                    "primary_lang_raw": segment_data.get("primary_lang_raw"),
                    "primary_lang_iso639_3": segment_data.get("primary_lang_iso639_3"),
                    "confidence": segment_data.get("confidence"),
                    "is_speech": segment_data.get("is_speech", True),
                },
            )
            return segment_id

    def insert_many(self, segments: List[Dict[str, Any]]) -> List[int]:
        """Insert multiple segments, returns list of IDs"""
        ids = []
        for segment in segments:
            segment_id = self.insert(segment)
            ids.append(segment_id)
        return ids

    def get_by_shard(self, shard_id: int) -> List[Dict[str, Any]]:
        """Get all segments for a shard"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM radio_segments
                WHERE shard_id = %s
                ORDER BY start_sec
            """,
                (shard_id,),
            )
            rows = cur.fetchall()

            # Parse JSONB fields
            for row in rows:
                row["start"] = row.get("start_sec")
                row["end"] = row.get("end_sec")
                if isinstance(row.get("lang_probs"), str):
                    row["lang_probs"] = json.loads(row["lang_probs"])
                if isinstance(row.get("mfcc_features"), str):
                    row["mfcc_features"] = json.loads(row["mfcc_features"])

            return [dict(row) for row in rows]

    def search(
        self,
        lang: Optional[str] = None,
        confidence_min: Optional[float] = None,
        station_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search segments with optional filters"""
        query = """
            SELECT
                seg.*,
                seg.start_sec AS start,
                seg.end_sec AS end,
                shard.start_ts AS shard_start_ts,
                shard.path AS shard_path,
                shard.s3_url AS shard_s3_url,
                src.id AS source_id,
                src.name AS station_name
            FROM radio_segments seg
            JOIN radio_shards shard ON seg.shard_id = shard.id
            JOIN radio_sources src ON shard.source_id = src.id
        """
        params = []
        filters = []

        if lang:
            filters.append("COALESCE(seg.primary_lang_iso639_3, seg.primary_lang) = %s")
            params.append(lang)
        if confidence_min is not None:
            filters.append("seg.confidence >= %s")
            params.append(confidence_min)
        if station_id is not None:
            filters.append("src.id = %s")
            params.append(station_id)
        if date_from is not None:
            filters.append("seg.created_at >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("seg.created_at <= %s")
            params.append(date_to)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY seg.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

            for row in rows:
                if isinstance(row.get("lang_probs"), str):
                    row["lang_probs"] = json.loads(row["lang_probs"])
                if isinstance(row.get("mfcc_features"), str):
                    row["mfcc_features"] = json.loads(row["mfcc_features"])

            return [dict(row) for row in rows]

    def count(
        self,
        lang: Optional[str] = None,
        confidence_min: Optional[float] = None,
        station_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> int:
        """Count segments matching filters"""
        query = """
            SELECT COUNT(*) AS total
            FROM radio_segments seg
            JOIN radio_shards shard ON seg.shard_id = shard.id
            JOIN radio_sources src ON shard.source_id = src.id
        """
        params = []
        filters = []

        if lang:
            filters.append("COALESCE(seg.primary_lang_iso639_3, seg.primary_lang) = %s")
            params.append(lang)
        if confidence_min is not None:
            filters.append("seg.confidence >= %s")
            params.append(confidence_min)
        if station_id is not None:
            filters.append("src.id = %s")
            params.append(station_id)
        if date_from is not None:
            filters.append("seg.created_at >= %s")
            params.append(date_from)
        if date_to is not None:
            filters.append("seg.created_at <= %s")
            params.append(date_to)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return int(row["total"]) if row else 0

    def get_by_id(self, segment_id: int) -> Optional[Dict[str, Any]]:
        """Get a segment by ID with station context"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    seg.*,
                    seg.start_sec AS start,
                    seg.end_sec AS end,
                    shard.start_ts AS shard_start_ts,
                    shard.path AS shard_path,
                    shard.s3_url AS shard_s3_url,
                    src.id AS source_id,
                    src.name AS station_name
                FROM radio_segments seg
                JOIN radio_shards shard ON seg.shard_id = shard.id
                JOIN radio_sources src ON shard.source_id = src.id
                WHERE seg.id = %s
                """,
                (segment_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            if isinstance(row.get("lang_probs"), str):
                row["lang_probs"] = json.loads(row["lang_probs"])
            if isinstance(row.get("mfcc_features"), str):
                row["mfcc_features"] = json.loads(row["mfcc_features"])
            return dict(row)


class RadioStationHourlyRepository:
    """Repository for radio_station_hourly table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def upsert(self, hourly_data: Dict[str, Any]) -> int:
        """Insert or update hourly aggregate"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO radio_station_hourly (
                    source_id, hour, primary_lang, lang_mix, switch_rate,
                    total_segments, speech_segments, speech_ratio,
                    dialect_notes, dialect_token_counts,
                    avg_confidence, min_confidence, max_confidence
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id, hour) DO UPDATE SET
                    primary_lang = EXCLUDED.primary_lang,
                    lang_mix = EXCLUDED.lang_mix,
                    switch_rate = EXCLUDED.switch_rate,
                    total_segments = EXCLUDED.total_segments,
                    speech_segments = EXCLUDED.speech_segments,
                    speech_ratio = EXCLUDED.speech_ratio,
                    dialect_notes = EXCLUDED.dialect_notes,
                    dialect_token_counts = EXCLUDED.dialect_token_counts,
                    avg_confidence = EXCLUDED.avg_confidence,
                    min_confidence = EXCLUDED.min_confidence,
                    max_confidence = EXCLUDED.max_confidence,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """,
                (
                    hourly_data["source_id"],
                    hourly_data["hour"],
                    hourly_data.get("primary_lang"),
                    json.dumps(hourly_data["lang_mix"]),
                    hourly_data.get("switch_rate"),
                    hourly_data.get("total_segments", 0),
                    hourly_data.get("speech_segments", 0),
                    hourly_data.get("speech_ratio"),
                    hourly_data.get("dialect_notes"),
                    (
                        json.dumps(hourly_data.get("dialect_token_counts"))
                        if hourly_data.get("dialect_token_counts")
                        else None
                    ),
                    hourly_data.get("avg_confidence"),
                    hourly_data.get("min_confidence"),
                    hourly_data.get("max_confidence"),
                ),
            )
            return cur.fetchone()[0]

    def list_for_source(self, source_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """List hourly aggregates for a station"""
        window_start = datetime.now(timezone.utc) - timedelta(hours=hours)
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT hour, primary_lang, lang_mix, switch_rate, speech_ratio
                FROM radio_station_hourly
                WHERE source_id = %s AND hour >= %s
                ORDER BY hour ASC
            """,
                (source_id, window_start),
            )
            rows = cur.fetchall()
            for row in rows:
                if isinstance(row.get("lang_mix"), str):
                    row["lang_mix"] = json.loads(row["lang_mix"])
            return [dict(row) for row in rows]

    def get_latest_for_sources(self, source_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Fetch latest hourly aggregate for multiple sources."""
        if not source_ids:
            return {}
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (source_id)
                    source_id,
                    hour,
                    primary_lang,
                    speech_ratio,
                    switch_rate,
                    avg_confidence
                FROM radio_station_hourly
                WHERE source_id = ANY(%s)
                ORDER BY source_id, hour DESC
                """,
                (source_ids,),
            )
            rows = cur.fetchall()
        return {row["source_id"]: dict(row) for row in rows}


class RadioStationDaypartRepository:
    """Repository for radio_station_daypart table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def upsert(self, daypart_data: Dict[str, Any]) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO radio_station_daypart (
                    source_id, day, daypart, timezone_used,
                    total_seconds, speech_seconds, shard_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id, day, daypart) DO UPDATE SET
                    timezone_used = EXCLUDED.timezone_used,
                    total_seconds = radio_station_daypart.total_seconds + EXCLUDED.total_seconds,
                    speech_seconds = radio_station_daypart.speech_seconds + EXCLUDED.speech_seconds,
                    shard_count = radio_station_daypart.shard_count + EXCLUDED.shard_count,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    daypart_data["source_id"],
                    daypart_data["day"],
                    daypart_data["daypart"],
                    daypart_data.get("timezone_used"),
                    daypart_data.get("total_seconds", 0),
                    daypart_data.get("speech_seconds", 0),
                    daypart_data.get("shard_count", 0),
                ),
            )
            return cur.fetchone()[0]

    def list_for_source(self, source_id: int, days: int = 7) -> List[Dict[str, Any]]:
        window_start = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT day, daypart, timezone_used, total_seconds, speech_seconds, shard_count
                FROM radio_station_daypart
                WHERE source_id = %s AND day >= %s
                ORDER BY day DESC, daypart ASC
                """,
                (source_id, window_start),
            )
            rows = cur.fetchall()
            return [dict(row) for row in rows]


class CaptureTargetRepository:
    """Repository for capture_targets table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def get_active(self) -> Optional[Dict[str, Any]]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM capture_targets
                WHERE active = true
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if not row:
                return None
            if isinstance(row.get("countries"), str):
                row["countries"] = json.loads(row["countries"])
            if isinstance(row.get("languages"), str):
                row["languages"] = json.loads(row["languages"])
            return dict(row)

    def upsert(
        self, countries: List[str], languages: List[str], notes: Optional[str] = None
    ) -> int:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO capture_targets (countries, languages, notes, active)
                VALUES (%s, %s, %s, true)
                RETURNING id
                """,
                (json.dumps(countries), json.dumps(languages), notes),
            )
            return cur.fetchone()[0]


class RadioFrequencyCandidateRepository:
    """Repository for station_frequency_candidates table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(
        self,
        source_id: int,
        frequency_mhz: Optional[float],
        frequency_label: Optional[str],
        source: str,
        confidence: Optional[float] = None,
        evidence_url: Optional[str] = None,
        evidence_text: Optional[str] = None,
    ) -> Optional[int]:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id FROM station_frequency_candidates
                WHERE source_id = %s AND frequency_mhz = %s AND source = %s
                LIMIT 1
                """,
                (source_id, frequency_mhz, source),
            )
            existing = cur.fetchone()
            if existing:
                return existing["id"]
            cur.execute(
                """
                INSERT INTO station_frequency_candidates (
                    source_id, frequency_mhz, frequency_label,
                    source, confidence, evidence_url, evidence_text
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    source_id,
                    frequency_mhz,
                    frequency_label,
                    source,
                    confidence,
                    evidence_url,
                    evidence_text,
                ),
            )
            candidate_id = cur.fetchone()["id"]

        _emit_event(
            self.conn,
            stage="discovery",
            event_type="frequency_candidate_added",
            status="success",
            source_id=source_id,
            count=1,
            message="Frequency candidate added",
            payload={
                "frequency_mhz": frequency_mhz,
                "frequency_label": frequency_label,
                "source": source,
                "confidence": confidence,
                "evidence_url": evidence_url,
            },
        )
        return candidate_id

    def resolve_best_for_source(self, source_id: int) -> None:
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM station_frequency_candidates
                WHERE source_id = %s AND frequency_mhz IS NOT NULL
                """,
                (source_id,),
            )
            candidates = cur.fetchall()

        if not candidates:
            return

        def score(row: Dict[str, Any]) -> tuple:
            priority = FREQUENCY_SOURCE_PRIORITY.get(row["source"], 0)
            confidence = row.get("confidence") or 0
            created_at = row.get("created_at") or datetime.min
            return (priority, confidence, created_at)

        best = max(candidates, key=score)
        RadioSourceRepository(self.conn).update_frequency(
            source_id=source_id,
            frequency_mhz=best.get("frequency_mhz"),
            frequency_label=best.get("frequency_label"),
            frequency_source=best.get("source"),
            frequency_confidence=best.get("confidence"),
        )
