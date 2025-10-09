"""Repository classes for database operations"""

import hashlib
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
import psycopg
from psycopg.rows import dict_row

# Import data contracts - these should already be installed
try:
    from mumbl_data_contracts.segments import TextSegment, AudioSegment, SourceRef, Labels
    from mumbl_data_contracts.scores import SegmentScore
    from mumbl_data_contracts.profiles import LanguageProfileV1
except ImportError:
    print("Warning: mumbl_data_contracts not found. Install with: pip install -e packages/data-contracts/python")
    raise


class TextSegmentRepository:
    """Repository for text_segments table"""
    
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
    
    def insert(self, segment: TextSegment, batch_id: Optional[str] = None) -> int:
        """Insert a text segment, returns the ID"""
        text_hash = hashlib.sha256(segment.text.encode('utf-8')).hexdigest()
        
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO text_segments (
                    doc_id, start_offset, end_offset, text, text_hash, lang,
                    is_dialogue, topic, register_type, code_switch_spans, batch_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (text_hash) DO NOTHING
                RETURNING id
            """, (
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
            ))
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
            cur.execute("""
                SELECT * FROM text_segments WHERE id = %s
            """, (segment_id,))
            row = cur.fetchone()
            if not row:
                return None
            
            # Note: psycopg automatically deserializes JSONB columns
            return TextSegment(
                text=row['text'],
                lang=row['lang'],
                labels=Labels(
                    is_dialogue=row['is_dialogue'],
                    topic=row['topic'],
                    register_type=row['register_type'],
                    code_switch_spans=row['code_switch_spans'] if isinstance(row['code_switch_spans'], list) else json.loads(row['code_switch_spans']),
                ),
                source_ref=SourceRef(
                    doc_id=row['doc_id'],
                    start=row['start_offset'],
                    end=row['end_offset'],
                )
            )
    
    def get_by_batch(self, batch_id: str) -> List[Dict[str, Any]]:
        """Get all segments for a batch"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT * FROM text_segments WHERE batch_id = %s ORDER BY id
            """, (batch_id,))
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
    
    def insert(self, segment: AudioSegment, batch_id: Optional[str] = None, **kwargs) -> int:
        """Insert an audio segment"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO audio_segments (
                    audio_file, audio_hash, start_time, end_time,
                    speaker_id, transcript_text, lang, dialect,
                    dialect_probs, alignment_confidence, diarization_confidence,
                    granularity, sample_rate, batch_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (audio_hash) DO NOTHING
                RETURNING id
            """, (
                segment.audio_file,
                kwargs.get('audio_hash'),
                segment.start,
                segment.end,
                segment.speaker_id,
                segment.transcript_text,
                segment.lang,
                kwargs.get('dialect'),
                json.dumps(segment.dialect_probs) if segment.dialect_probs else None,
                segment.alignment_confidence,
                segment.diarization_confidence,
                kwargs.get('granularity'),
                kwargs.get('sample_rate'),
                batch_id,
            ))
            result = cur.fetchone()
            return result[0] if result else None


class SegmentScoreRepository:
    """Repository for segment_scores table"""
    
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
    
    def insert(self, score: SegmentScore, segment_type: str, segment_id: int) -> int:
        """Insert a segment score"""
        with self.conn.cursor() as cur:
            cur.execute("""
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
            """, (
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
            ))
            return cur.fetchone()[0]
    
    def get_high_quality_count(self, segment_type: str, lang: Optional[str] = None, min_score: float = 90) -> int:
        """Count high-quality segments"""
        with self.conn.cursor() as cur:
            if lang:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM segment_scores ss
                    JOIN text_segments ts ON ss.segment_id = ts.id
                    WHERE ss.segment_type = %s AND ss.total >= %s AND ts.lang = %s
                """, (segment_type, min_score, lang))
            else:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM segment_scores
                    WHERE segment_type = %s AND total >= %s
                """, (segment_type, min_score))
            return cur.fetchone()[0]


class LanguageProfileRepository:
    """Repository for language_profiles table"""
    
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
    
    def insert(self, profile: LanguageProfileV1) -> int:
        """Insert or update a language profile"""
        profile_json = profile.model_dump(mode='json')
        
        with self.conn.cursor() as cur:
            cur.execute("""
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
            """, (
                profile.language,
                profile.dialect,
                profile.script,
                profile.version,
                json.dumps(profile_json),
                profile.tts_strategy,
                len(profile.phoneme_inventory),
            ))
            return cur.fetchone()[0]
    
    def get_by_dialect(self, dialect: str) -> Optional[LanguageProfileV1]:
        """Retrieve profile by dialect"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT profile_json FROM language_profiles WHERE dialect = %s
            """, (dialect,))
            row = cur.fetchone()
            if not row:
                return None
            return LanguageProfileV1(**row['profile_json'])
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all profiles"""
        with self.conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT language, dialect, version, tts_strategy, phoneme_count, created_at
                FROM language_profiles
                ORDER BY language, dialect
            """)
            return cur.fetchall()

