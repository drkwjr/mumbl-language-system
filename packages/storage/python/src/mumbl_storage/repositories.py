"""Repository classes for database operations"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import psycopg
from psycopg.rows import dict_row

# Import data contracts - these should already be installed
try:
    from mumbl_data_contracts.profiles import LanguageProfileV1
    from mumbl_data_contracts.scores import SegmentScore
    from mumbl_data_contracts.segments import AudioSegment, Labels, SourceRef, TextSegment
except ImportError:
    print(
        "Warning: mumbl_data_contracts not found. Install with: pip install -e packages/data-contracts/python"
    )
    raise


class TextSegmentRepository:
    """Repository for text_segments table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, segment: TextSegment, batch_id: Optional[str] = None) -> int:
        """Insert a text segment, returns the ID"""
        text_hash = hashlib.sha256(segment.text.encode("utf-8")).hexdigest()

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO text_segments (
                    doc_id, start_offset, end_offset, text, text_hash, lang,
                    is_dialogue, topic, register_type, code_switch_spans, batch_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (text_hash) DO NOTHING
                RETURNING id
            """,
                (
                    segment.source_ref.doc_id,
                    segment.source_ref.start,
                    segment.source_ref.end,
                    segment.text,
                    text_hash,
                    segment.lang,
                    segment.labels.is_dialogue,
                    segment.labels.topic,
                    segment.labels.register_type,
                    json.dumps(segment.labels.code_switch_spans),
                    batch_id,
                ),
            )
            result = cur.fetchone()
            return result[0] if result else None

    def insert_many(self, segments: List[TextSegment], batch_id: Optional[str] = None) -> List[int]:
        """Insert multiple segments, returns list of IDs (None for duplicates)"""
        ids = []
        for segment in segments:
            segment_id = self.insert(segment, batch_id)
            ids.append(segment_id)
        return ids

    def get_by_id(self, segment_id: int) -> Optional[TextSegment]:
        """Retrieve a text segment by ID"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM text_segments WHERE id = %s
            """,
                (segment_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            # Note: psycopg automatically deserializes JSONB columns
            return TextSegment(
                text=row["text"],
                lang=row["lang"],
                labels=Labels(
                    is_dialogue=row["is_dialogue"],
                    topic=row["topic"],
                    register_type=row["register_type"],
                    code_switch_spans=(
                        row["code_switch_spans"]
                        if isinstance(row["code_switch_spans"], list)
                        else json.loads(row["code_switch_spans"])
                    ),
                ),
                source_ref=SourceRef(
                    doc_id=row["doc_id"],
                    start=row["start_offset"],
                    end=row["end_offset"],
                ),
            )

    def get_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all segments for a batch"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM text_segments WHERE batch_id = %s ORDER BY id
            """,
                (batch_id,),
            )
            return cur.fetchall()

    def count_by_language(self, lang: str) -> int:
        """Count segments for a language"""
        with self.conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM text_segments WHERE lang = %s", (lang,))
            return cur.fetchone()[0]


class AudioSegmentRepository:
    """Repository for audio_segments table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(
        self, segment: AudioSegment, batch_id: Optional[str] = None, **kwargs
    ) -> Optional[int]:
        """Insert an audio segment, returns ID or None if duplicate"""
        audio_hash = kwargs.get("audio_hash")

        with self.conn.cursor() as cur:
            # Handle NULL audio_hash case (no deduplication) vs non-NULL (deduplication)
            if audio_hash:
                cur.execute(
                    """
                    INSERT INTO audio_segments (
                        audio_file, audio_hash, start_time, end_time,
                        speaker_id, transcript_text, lang, dialect,
                        dialect_probs, alignment_confidence, diarization_confidence,
                        granularity, sample_rate, batch_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (audio_hash) DO NOTHING
                    RETURNING id
                """,
                    (
                        segment.audio_file,
                        audio_hash,
                        segment.start,
                        segment.end,
                        segment.speaker_id,
                        segment.transcript_text,
                        segment.lang,
                        kwargs.get("dialect"),
                        json.dumps(segment.dialect_probs) if segment.dialect_probs else None,
                        segment.alignment_confidence,
                        segment.diarization_confidence,
                        kwargs.get("granularity"),
                        kwargs.get("sample_rate"),
                        batch_id,
                    ),
                )
            else:
                # No hash provided, insert without deduplication check
                cur.execute(
                    """
                    INSERT INTO audio_segments (
                        audio_file, audio_hash, start_time, end_time,
                        speaker_id, transcript_text, lang, dialect,
                        dialect_probs, alignment_confidence, diarization_confidence,
                        granularity, sample_rate, batch_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        segment.audio_file,
                        None,
                        segment.start,
                        segment.end,
                        segment.speaker_id,
                        segment.transcript_text,
                        segment.lang,
                        kwargs.get("dialect"),
                        json.dumps(segment.dialect_probs) if segment.dialect_probs else None,
                        segment.alignment_confidence,
                        segment.diarization_confidence,
                        kwargs.get("granularity"),
                        kwargs.get("sample_rate"),
                        batch_id,
                    ),
                )
            result = cur.fetchone()
            return result[0] if result else None

    def insert_many(
        self, segments: List[Dict[str, Any]], batch_id: Optional[str] = None
    ) -> List[Optional[int]]:
        """Insert multiple audio segments, returns list of IDs"""
        ids = []
        for item in segments:
            segment = item.get("segment")
            kwargs = {k: v for k, v in item.items() if k != "segment"}
            if segment:
                segment_id = self.insert(segment, batch_id, **kwargs)
                ids.append(segment_id)
            else:
                ids.append(None)
        return ids

    def get_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all audio segments for a batch"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM audio_segments WHERE batch_id = %s ORDER BY id
            """,
                (batch_id,),
            )
            return cur.fetchall()

    def export_to_csv(
        self, output_path: str, batch_id: Optional[str] = None, lang: Optional[str] = None
    ) -> int:
        """
        Export audio segments to CSV file (paired_speech_corpus.csv format).

        Args:
            output_path: Path to write CSV file
            batch_id: Optional batch filter
            lang: Optional language filter

        Returns:
            Number of segments exported
        """
        import csv

        # Build query
        query = "SELECT * FROM audio_segments WHERE 1=1"
        params = []

        if batch_id:
            query += " AND batch_id = %s"
            params.append(batch_id)

        if lang:
            query += " AND lang = %s"
            params.append(lang)

        query += " ORDER BY id"

        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        # Write CSV
        if not rows:
            return 0

        fieldnames = [
            "audio_file",
            "start_time",
            "end_time",
            "speaker_id",
            "transcript_text",
            "lang",
            "dialect",
            "dialect_probs",
            "alignment_confidence",
            "diarization_confidence",
            "granularity",
            "sample_rate",
            "batch_id",
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for row in rows:
                # Convert JSONB fields to strings
                csv_row = {
                    "audio_file": row["audio_file"],
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "speaker_id": row["speaker_id"],
                    "transcript_text": row["transcript_text"],
                    "lang": row["lang"],
                    "dialect": row.get("dialect"),
                    "dialect_probs": (
                        json.dumps(row["dialect_probs"]) if row.get("dialect_probs") else None
                    ),
                    "alignment_confidence": row.get("alignment_confidence"),
                    "diarization_confidence": row.get("diarization_confidence"),
                    "granularity": row.get("granularity"),
                    "sample_rate": row.get("sample_rate"),
                    "batch_id": row.get("batch_id"),
                }
                writer.writerow(csv_row)

        return len(rows)


class SegmentScoreRepository:
    """Repository for segment_scores table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, score: SegmentScore, segment_type: str, segment_id: int) -> int:
        """Insert a segment score"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO segment_scores (
                    segment_type, segment_id,
                    clarity, alignment, diarization, transcript_accuracy,
                    validity, shape, total,
                    eligible_learner, eligible_training, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (segment_type, segment_id) DO UPDATE SET
                    clarity = EXCLUDED.clarity,
                    alignment = EXCLUDED.alignment,
                    diarization = EXCLUDED.diarization,
                    transcript_accuracy = EXCLUDED.transcript_accuracy,
                    validity = EXCLUDED.validity,
                    shape = EXCLUDED.shape,
                    total = EXCLUDED.total,
                    eligible_learner = EXCLUDED.eligible_learner,
                    eligible_training = EXCLUDED.eligible_training,
                    notes = EXCLUDED.notes
                RETURNING id
            """,
                (
                    segment_type,
                    segment_id,
                    score.clarity,
                    score.alignment,
                    score.diarization,
                    score.transcript_accuracy,
                    score.validity,
                    score.shape,
                    score.total,
                    score.eligible_learner,
                    score.eligible_training,
                    score.notes,
                ),
            )
            return cur.fetchone()[0]

    def get_high_quality_count(
        self, segment_type: str, lang: Optional[str] = None, min_score: float = 90
    ) -> int:
        """Count high-quality segments"""
        with self.conn.cursor() as cur:
            if lang:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM segment_scores ss
                    JOIN text_segments ts ON ss.segment_id = ts.id
                    WHERE ss.segment_type = %s AND ss.total >= %s AND ts.lang = %s
                """,
                    (segment_type, min_score, lang),
                )
            else:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM segment_scores
                    WHERE segment_type = %s AND total >= %s
                """,
                    (segment_type, min_score),
                )
            return cur.fetchone()[0]


class PipelineEventRepository:
    """Repository for pipeline_events table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
        self.log_path = os.getenv("PIPELINE_EVENT_LOG_PATH", "logs/pipeline_events.jsonl")

    def insert(
        self,
        stage: str,
        event_type: str,
        status: Optional[str] = None,
        source_id: Optional[int] = None,
        shard_id: Optional[int] = None,
        segment_id: Optional[int] = None,
        count: Optional[int] = None,
        duration_seconds: Optional[float] = None,
        message: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a pipeline event and append a raw log line"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO pipeline_events (
                    stage, event_type, status,
                    source_id, shard_id, segment_id,
                    count, duration_seconds,
                    message, payload
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at
                """,
                (
                    stage,
                    event_type,
                    status,
                    source_id,
                    shard_id,
                    segment_id,
                    count,
                    duration_seconds,
                    message,
                    json.dumps(payload) if payload else None,
                ),
            )
            row = cur.fetchone()
            event_id = row["id"]
            created_at = row["created_at"]

        self._write_event_log(
            {
                "id": event_id,
                "stage": stage,
                "event_type": event_type,
                "status": status,
                "source_id": source_id,
                "shard_id": shard_id,
                "segment_id": segment_id,
                "count": count,
                "duration_seconds": duration_seconds,
                "message": message,
                "payload": payload,
                "created_at": created_at.isoformat() if created_at else None,
            }
        )
        return event_id

    def _write_event_log(self, event: Dict[str, Any]) -> None:
        if not self.log_path:
            return
        path = Path(self.log_path)
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")


class SegmentLanguageVerificationRepository:
    """Repository for segment_language_verifications table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(
        self,
        segment_type: str,
        segment_id: int,
        source: str = "llm",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        candidates: Optional[List[str]] = None,
        language: Optional[str] = None,
        dialect: Optional[str] = None,
        confidence: Optional[float] = None,
        rationale: Optional[str] = None,
    ) -> int:
        """Insert a language verification record"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO segment_language_verifications (
                    segment_type, segment_id, source,
                    provider, model, candidates,
                    language, dialect, confidence, rationale
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    segment_type,
                    segment_id,
                    source,
                    provider,
                    model,
                    json.dumps(candidates) if candidates else None,
                    language,
                    dialect,
                    confidence,
                    rationale,
                ),
            )
            verification_id = cur.fetchone()[0]

        PipelineEventRepository(self.conn).insert(
            stage="verification",
            event_type="verification_recorded",
            status="success",
            segment_id=segment_id,
            count=1,
            message=f"{segment_type} segment verification recorded",
            payload={
                "segment_type": segment_type,
                "source": source,
                "provider": provider,
                "model": model,
                "candidates": candidates,
                "language": language,
                "dialect": dialect,
                "confidence": confidence,
                "rationale": rationale,
            },
        )
        return verification_id


class DatasetRepository:
    """Repository for datasets table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def create_snapshot(
        self,
        name: str,
        language: str,
        dialect: str,
        dataset_type: str,
        manifest_json: Dict[str, Any],
        version: Optional[str] = None,
        description: Optional[str] = None,
        artifact_uri: Optional[str] = None,
    ) -> int:
        """Create a dataset snapshot"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO datasets (
                    name, description, language, dialect, dataset_type,
                    manifest_json, segment_count, version, artifact_uri
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """,
                (
                    name,
                    description,
                    language,
                    dialect,
                    dataset_type,
                    json.dumps(manifest_json),
                    manifest_json.get("segment_count", 0),
                    version,
                    artifact_uri,
                ),
            )
            return cur.fetchone()[0]

    def get_by_id(self, dataset_id: int) -> Optional[Dict[str, Any]]:
        """Get dataset by ID"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM datasets WHERE id = %s
            """,
                (dataset_id,),
            )
            return cur.fetchone()

    def list_by_language(
        self, language: str, dataset_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List datasets by language"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            if dataset_type:
                cur.execute(
                    """
                    SELECT * FROM datasets 
                    WHERE language = %s AND dataset_type = %s
                    ORDER BY created_at DESC
                """,
                    (language, dataset_type),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM datasets 
                    WHERE language = %s
                    ORDER BY created_at DESC
                """,
                    (language,),
                )
            return cur.fetchall()


class ModelRegistryRepository:
    """Repository for model_registry table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def register(
        self,
        kind: str,
        language: str,
        dialect: Optional[str],
        model_name: str,
        version: str,
        artifact_uri: str,
        training_dataset_id: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        status: str = "dev",
    ) -> int:
        """Register a model in the registry"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_registry (
                    kind, language, dialect, model_name, version,
                    training_dataset_id, training_config, metrics_json,
                    artifact_uri, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (kind, language, dialect, version) DO UPDATE SET
                    training_dataset_id = EXCLUDED.training_dataset_id,
                    training_config = EXCLUDED.training_config,
                    metrics_json = EXCLUDED.metrics_json,
                    artifact_uri = EXCLUDED.artifact_uri,
                    status = EXCLUDED.status
                RETURNING id
            """,
                (
                    kind,
                    language,
                    dialect,
                    model_name,
                    version,
                    training_dataset_id,
                    json.dumps(training_config) if training_config else None,
                    json.dumps(metrics) if metrics else None,
                    artifact_uri,
                    status,
                ),
            )
            return cur.fetchone()[0]

    def get_by_id(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get model by ID"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT * FROM model_registry WHERE id = %s
            """,
                (model_id,),
            )
            return cur.fetchone()

    def list_by_language(self, language: str, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        """List models by language"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            if kind:
                cur.execute(
                    """
                    SELECT * FROM model_registry 
                    WHERE language = %s AND kind = %s
                    ORDER BY created_at DESC
                """,
                    (language, kind),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM model_registry 
                    WHERE language = %s
                    ORDER BY created_at DESC
                """,
                    (language,),
                )
            return cur.fetchall()


class LanguageProfileRepository:
    """Repository for language_profiles table"""

    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def insert(self, profile: LanguageProfileV1) -> int:
        """Insert or update a language profile"""
        profile_json = profile.model_dump(mode="json")

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO language_profiles (
                    language, dialect, script, version,
                    profile_json, tts_strategy, phoneme_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (dialect) DO UPDATE SET
                    profile_json = EXCLUDED.profile_json,
                    version = EXCLUDED.version,
                    tts_strategy = EXCLUDED.tts_strategy,
                    phoneme_count = EXCLUDED.phoneme_count,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """,
                (
                    profile.language,
                    profile.dialect,
                    profile.script,
                    profile.version,
                    json.dumps(profile_json),
                    profile.tts_strategy,
                    len(profile.phoneme_inventory),
                ),
            )
            return cur.fetchone()[0]

    def get_by_dialect(self, dialect: str) -> Optional[LanguageProfileV1]:
        """Retrieve profile by dialect"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT profile_json FROM language_profiles WHERE dialect = %s
            """,
                (dialect,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return LanguageProfileV1(**row["profile_json"])

    def list_all(self) -> List[Dict[str, Any]]:
        """List all profiles"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT language, dialect, version, tts_strategy, phoneme_count, created_at
                FROM language_profiles
                ORDER BY language, dialect
            """
            )
            return cur.fetchall()
