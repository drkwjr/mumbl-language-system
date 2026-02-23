"""
Policy gates: quality thresholds and content filtering.
"""

from typing import List, Optional, Union

from mumbl_data_contracts.scores import SegmentScore
from mumbl_data_contracts.segments import AudioSegment, TextSegment


class PolicyGate:
    """
    Apply quality thresholds and content filters.
    """

    def __init__(self, min_training_score: float = 70.0, min_learner_score: float = 90.0):
        """
        Initialize policy gate.

        Args:
            min_training_score: Minimum score for TTS training (≥70)
            min_learner_score: Minimum score for learner/Premium datasets (≥90)
        """
        self.min_training_score = min_training_score
        self.min_learner_score = min_learner_score

        # Content filter keywords (basic, can be expanded)
        self.blocked_keywords = [
            # Add content filtering keywords here if needed
        ]

    def apply_thresholds(
        self, segments_with_scores: List[tuple], min_score: Optional[float] = None
    ) -> List[tuple]:
        """
        Filter segments by quality threshold.

        Args:
            segments_with_scores: List of (segment, score) tuples
            min_score: Minimum score threshold (uses self.min_training_score if None)

        Returns:
            Filtered list of (segment, score) tuples
        """
        threshold = min_score if min_score is not None else self.min_training_score

        filtered = []
        for segment, score in segments_with_scores:
            if score.total >= threshold:
                filtered.append((segment, score))

        return filtered

    def apply_content_filters(
        self, segments: List[Union[TextSegment, AudioSegment]]
    ) -> List[Union[TextSegment, AudioSegment]]:
        """
        Filter segments by content (remove inappropriate content).

        Args:
            segments: List of segments to filter

        Returns:
            Filtered list of segments
        """
        if not self.blocked_keywords:
            return segments  # No filtering if no keywords

        filtered = []
        for segment in segments:
            text = None
            if isinstance(segment, TextSegment):
                text = segment.text
            elif isinstance(segment, AudioSegment):
                text = segment.transcript_text

            if text:
                # Check if text contains blocked keywords (case-insensitive)
                text_lower = text.lower()
                if any(keyword.lower() in text_lower for keyword in self.blocked_keywords):
                    continue  # Skip this segment

            filtered.append(segment)

        return filtered

    def get_eligible_segments(
        self, segments_with_scores: List[tuple], target: str = "training"  # "training" or "learner"
    ) -> List[tuple]:
        """
        Get segments eligible for a specific target dataset.

        Args:
            segments_with_scores: List of (segment, score) tuples
            target: "training" or "learner"

        Returns:
            List of eligible (segment, score) tuples
        """
        min_score = self.min_learner_score if target == "learner" else self.min_training_score

        # Apply thresholds
        eligible = self.apply_thresholds(segments_with_scores, min_score)

        # Apply content filters
        segments_only = [seg for seg, score in eligible]
        filtered_segments = self.apply_content_filters(segments_only)

        # Rebuild list with scores
        filtered = []
        for seg, score in eligible:
            if seg in filtered_segments:
                filtered.append((seg, score))

        return filtered
