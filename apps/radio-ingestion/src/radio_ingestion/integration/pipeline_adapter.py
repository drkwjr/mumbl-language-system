"""Adapter to convert radio segments to Mumbl pipeline contracts"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from mumbl_data_contracts.segments import AudioSegment
from radio_ingestion.storage.radio_repositories import (
    RadioSegmentRepository,
    RadioShardRepository,
    RadioSourceRepository,
)

logger = structlog.get_logger(__name__)


class RadioPipelineAdapter:
    """
    Adapter to convert radio segments to AudioSegment contracts
    and integrate with Mumbl pipeline.
    """

    def __init__(
        self,
        min_speech_ratio: float = 0.7,
        min_confidence: float = 0.8,
        min_duration: float = 2.0,
        max_duration: float = 12.0,
    ):
        """
        Initialize adapter.

        Args:
            min_speech_ratio: Minimum speech ratio for export (default: 0.7)
            min_confidence: Minimum LID confidence for export (default: 0.8)
            min_duration: Minimum segment duration (default: 2.0 seconds)
            max_duration: Maximum segment duration (default: 12.0 seconds)
        """
        self.min_speech_ratio = min_speech_ratio
        self.min_confidence = min_confidence
        self.min_duration = min_duration
        self.max_duration = max_duration

        logger.info(
            "Pipeline adapter initialized",
            min_speech_ratio=min_speech_ratio,
            min_confidence=min_confidence,
            duration_range=(min_duration, max_duration),
        )

    def convert_segment_to_audiosegment(
        self, radio_segment: Dict[str, Any], shard_data: Dict[str, Any], source_data: Dict[str, Any]
    ) -> AudioSegment:
        """
        Convert a radio segment to AudioSegment contract.

        Args:
            radio_segment: Radio segment from database
            shard_data: Shard data containing audio file path
            source_data: Source data for metadata

        Returns:
            AudioSegment contract instance
        """
        # Extract audio file path (prefer S3 URL, fallback to local path)
        audio_file = shard_data.get("s3_url") or shard_data.get("path", "")

        # Calculate absolute start/end times within the audio file
        # radio_segment.start/end are relative to shard, but we need them relative to the full audio
        # For now, assume segments are already extracted or shard is the audio file
        start_time = radio_segment.get("start", 0.0)
        end_time = radio_segment.get("end", 0.0)

        # If segment has a separate path, use that
        if radio_segment.get("path"):
            audio_file = radio_segment["path"]
            # Reset times to 0 since it's the segment file itself
            start_time = 0.0
            end_time = radio_segment.get("duration", 0.0)

        # Get language and dialect probabilities
        lang_probs = radio_segment.get("lang_probs", {})
        primary_lang = radio_segment.get("primary_lang_iso639_3") or radio_segment.get(
            "primary_lang"
        )

        # Convert lang_probs to dialect_probs format
        # For radio, we use language probabilities as dialect_probs
        # (radio stations often broadcast in a single dialect per language)
        dialect_probs = lang_probs if lang_probs else None

        # Extract confidence
        confidence = radio_segment.get("confidence", 0.0)

        # Create AudioSegment
        audio_segment = AudioSegment(
            audio_file=audio_file,
            start=start_time,
            end=end_time,
            speaker_id=None,  # Radio segments typically don't have speaker IDs
            transcript_text=None,  # Will be filled by ASR later
            lang=primary_lang,
            dialect_probs=dialect_probs,
            alignment_confidence=confidence if confidence > 0 else None,
            diarization_confidence=None,  # Radio segments typically don't have diarization
        )

        return audio_segment

    def filter_high_quality_segments(
        self, segments: List[Dict[str, Any]], shard_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter segments that meet quality thresholds.

        Args:
            segments: List of radio segment dictionaries
            shard_data: Shard data for speech ratio check

        Returns:
            Filtered list of segments
        """
        shard_speech_ratio = shard_data.get("speech_ratio", 0.0)

        # Filter segments
        filtered = []
        for segment in segments:
            # Check speech flag
            if not segment.get("is_speech", True):
                continue

            # Check music probability
            music_prob = segment.get("music_prob", 0.0)
            if music_prob > 0.6:
                continue

            # Check duration
            duration = segment.get("duration", 0.0)
            if duration < self.min_duration or duration > self.max_duration:
                continue

            # Check confidence
            confidence = segment.get("confidence", 0.0)
            if confidence < self.min_confidence:
                continue

            # Check shard-level speech ratio (optional, if available)
            if shard_speech_ratio > 0 and shard_speech_ratio < self.min_speech_ratio:
                # Skip if entire shard has low speech ratio
                continue

            filtered.append(segment)

        logger.info(
            "Filtered high-quality segments",
            total=len(segments),
            filtered=len(filtered),
            min_confidence=self.min_confidence,
            min_duration=self.min_duration,
        )

        return filtered

    def export_segments_for_asr(self, shard_id: int, db_conn) -> List[AudioSegment]:
        """
        Export high-quality segments from a shard for ASR processing.

        Args:
            shard_id: Shard database ID
            db_conn: Database connection

        Returns:
            List of AudioSegment contracts
        """
        segment_repo = RadioSegmentRepository(db_conn)
        shard_repo = RadioShardRepository(db_conn)
        source_repo = RadioSourceRepository(db_conn)

        # Get shard data
        shards = shard_repo.get_by_source(0, limit=1000)  # Get all, then filter
        shard_data = None
        for s in shards:
            if s["id"] == shard_id:
                shard_data = s
                break

        if not shard_data:
            logger.warning("Shard not found", shard_id=shard_id)
            return []

        # Get source data
        source_data = source_repo.get_by_id(shard_data["source_id"])
        if not source_data:
            logger.warning("Source not found", source_id=shard_data["source_id"])
            return []

        # Get segments
        segments = segment_repo.get_by_shard(shard_id)

        # Filter high-quality segments
        filtered = self.filter_high_quality_segments(segments, shard_data)

        # Convert to AudioSegment contracts (with metadata dict format)
        audio_segments = []
        for segment in filtered:
            try:
                audio_seg = self.convert_segment_to_audiosegment(segment, shard_data, source_data)

                # Compute audio hash if file exists (for deduplication)
                audio_hash = None
                try:
                    from audio_lane.fingerprint import compute_fingerprint

                    if audio_seg.audio_file and Path(audio_seg.audio_file).exists():
                        audio_hash = compute_fingerprint(audio_seg.audio_file)
                except Exception as e:
                    logger.debug(
                        "Could not compute audio hash",
                        audio_file=audio_seg.audio_file,
                        error=str(e),
                    )

                # Format matches AudioLaneProcessor output
                audio_segments.append(
                    {
                        "segment": audio_seg,
                        "audio_hash": audio_hash,
                        "granularity": "sentence",  # Radio segments are sentence-level
                        "sample_rate": 22050,
                        "dialect": None,  # Will be extracted from dialect_probs if needed
                    }
                )
            except Exception as e:
                logger.warning(
                    "Failed to convert segment", segment_id=segment.get("id"), error=str(e)
                )
                continue

        logger.info(
            "Exported segments for ASR",
            shard_id=shard_id,
            total_segments=len(segments),
            exported=len(audio_segments),
        )

        return audio_segments

    def batch_export_for_asr(
        self,
        db_conn,
        source_id: Optional[int] = None,
        min_confidence: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Batch export high-quality segments for ASR processing.

        Args:
            db_conn: Database connection
            source_id: Optional source filter
            min_confidence: Override min_confidence if provided
            limit: Maximum number of segments to export

        Returns:
            List of dictionaries with 'segment' (AudioSegment) and metadata
        """
        segment_repo = RadioSegmentRepository(db_conn)
        shard_repo = RadioShardRepository(db_conn)
        source_repo = RadioSourceRepository(db_conn)

        # Use override confidence if provided
        confidence_threshold = min_confidence if min_confidence is not None else self.min_confidence

        # Get shards
        if source_id:
            shards = shard_repo.get_by_source(source_id, limit=100)
        else:
            # Get from all active sources
            source_repo_instance = source_repo
            sources = source_repo_instance.list_active()
            shards = []
            for source in sources[:20]:  # Limit to first 20 sources
                source_shards = shard_repo.get_by_source(source["id"], limit=10)
                shards.extend(source_shards)

        all_segments = []

        for shard in shards:
            # Get shard data (already have it)
            source_data = source_repo.get_by_id(shard["source_id"])
            if not source_data:
                continue

            # Get segments
            segments = segment_repo.get_by_shard(shard["id"])

            # Filter
            filtered = self.filter_high_quality_segments(segments, shard)

            # Additional confidence filter if override provided
            if confidence_threshold > self.min_confidence:
                filtered = [s for s in filtered if s.get("confidence", 0.0) >= confidence_threshold]

            # Convert (format matches AudioLaneProcessor output)
            for segment in filtered:
                try:
                    audio_seg = self.convert_segment_to_audiosegment(segment, shard, source_data)

                    # Compute audio hash for deduplication
                    audio_hash = None
                    try:
                        from audio_lane.fingerprint import compute_fingerprint

                        if audio_seg.audio_file and Path(audio_seg.audio_file).exists():
                            audio_hash = compute_fingerprint(audio_seg.audio_file)
                    except Exception:
                        pass  # Hash computation is optional

                    all_segments.append(
                        {
                            "segment": audio_seg,
                            "audio_hash": audio_hash,
                            "granularity": "sentence",
                            "sample_rate": 22050,
                            "dialect": None,
                            # Radio-specific metadata
                            "radio_segment_id": segment.get("id"),
                            "shard_id": shard["id"],
                            "source_id": shard["source_id"],
                            "source_type": "radio",
                            "batch_id": f"radio_{shard['source_id']}_{shard['id']}",
                        }
                    )

                    if limit and len(all_segments) >= limit:
                        break

                except Exception as e:
                    logger.warning("Failed to convert segment in batch", error=str(e))
                    continue

            if limit and len(all_segments) >= limit:
                break

        logger.info(
            "Batch export complete",
            total_exported=len(all_segments),
            source_id=source_id,
            min_confidence=confidence_threshold,
        )

        return all_segments


def create_adapter(
    min_speech_ratio: float = 0.7, min_confidence: float = 0.8
) -> RadioPipelineAdapter:
    """Factory function to create adapter"""
    return RadioPipelineAdapter(min_speech_ratio=min_speech_ratio, min_confidence=min_confidence)
