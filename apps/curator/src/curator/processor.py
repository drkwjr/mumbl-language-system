"""
Main Curator processor orchestrating scoring, deduplication, and dataset creation.
"""

from typing import Any, Dict, List, Optional

from mumbl_data_contracts.scores import SegmentScore
from mumbl_data_contracts.segments import AudioSegment, TextSegment

from .deduplicator import Deduplicator
from .policy_gates import PolicyGate
from .scorer import SegmentScorer
from .snapshot import DatasetSnapshot


class CuratorProcessor:
    """
    Main processor for Curator pipeline.

    Orchestrates: Score → Dedupe → Policy Gates → Snapshot → Register
    """

    def __init__(self):
        """Initialize processor with all components."""
        self.scorer = SegmentScorer()
        self.deduplicator = Deduplicator()
        self.policy_gate = PolicyGate()
        self.snapshot = DatasetSnapshot()

    def process_segments(
        self,
        text_segments: List[TextSegment] = None,
        audio_segments: List[Dict[str, Any]] = None,
        batch_id: Optional[str] = None,
        language: str = "",
        dialect: str = "",
        target: str = "training",  # "training" or "learner"
    ) -> Dict[str, Any]:
        """
        Process segments through full curator pipeline.

        Args:
            text_segments: List of TextSegment objects (optional)
            audio_segments: List of dicts with 'segment' and 'audio_hash' keys (optional)
            batch_id: Optional batch ID for tracking
            language: Language code
            dialect: Dialect code
            target: Target dataset type ("training" or "learner")

        Returns:
            Dict with curated dataset info
        """
        # Step 1: Score segments
        text_scores = []
        audio_scores = []

        if text_segments:
            for segment in text_segments:
                score = self.scorer.score_text_segment(segment)
                text_scores.append((segment, score))

        if audio_segments:
            for item in audio_segments:
                segment = item.get("segment")
                if segment:
                    score = self.scorer.score_audio_segment(segment)
                    audio_scores.append((segment, score))

        # Step 2: Deduplication
        dedup_report = self.deduplicator.get_deduplication_report(
            text_segments=text_segments, audio_segments=audio_segments
        )

        # Remove duplicates from scored segments
        text_dups = dedup_report.get("exact_duplicates", {}).get("text_duplicates", [])
        audio_dups = dedup_report.get("exact_duplicates", {}).get("audio_duplicates", [])

        text_scores_filtered = self._remove_duplicates_from_scores(text_scores, text_dups)
        audio_scores_filtered = self._remove_duplicates_from_scores(audio_scores, audio_dups)

        # Step 3: Apply policy gates
        eligible_text = self.policy_gate.get_eligible_segments(text_scores_filtered, target=target)
        eligible_audio = self.policy_gate.get_eligible_segments(
            audio_scores_filtered, target=target
        )

        # Step 4: Create dataset snapshot
        # Extract segment IDs (assuming segments have IDs from database)
        segment_ids = []
        for seg, score in eligible_text:
            # Text segments would need ID from database
            # For now, use hash or index
            segment_ids.append(id(seg))

        for seg, score in eligible_audio:
            segment_ids.append(id(seg))

        snapshot = self.snapshot.create_snapshot(
            segment_ids=segment_ids,
            language=language,
            dialect=dialect,
            metadata={
                "batch_id": batch_id,
                "target": target,
                "text_count": len(eligible_text),
                "audio_count": len(eligible_audio),
            },
        )

        return {
            "snapshot": snapshot,
            "stats": {
                "text_segments_scored": len(text_scores),
                "audio_segments_scored": len(audio_scores),
                "text_segments_eligible": len(eligible_text),
                "audio_segments_eligible": len(eligible_audio),
                "exact_duplicates_removed": (len(text_dups) + len(audio_dups)),
                "near_duplicates_found": len(
                    dedup_report.get("near_duplicates", {}).get("pairs", [])
                ),
            },
            "deduplication_report": dedup_report,
        }

    def _remove_duplicates_from_scores(
        self, scores: List[tuple], duplicate_pairs: List[tuple]
    ) -> List[tuple]:
        """Remove duplicate segments from scored list."""
        if not duplicate_pairs:
            return scores

        # Build set of duplicate indices
        duplicate_indices = set()
        for keep_idx, dup_idx in duplicate_pairs:
            duplicate_indices.add(dup_idx)

        # Filter out duplicates
        filtered = []
        for idx, (seg, score) in enumerate(scores):
            if idx not in duplicate_indices:
                filtered.append((seg, score))

        return filtered
