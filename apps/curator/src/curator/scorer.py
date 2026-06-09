"""
Scoring rubric implementation for text and audio segments.

`validity` is bank-backed: the bank's verifier decides whether the text is real target-language
content (the judgment heuristics can't make), and the conversational labels (dialogue / topic /
register) add learner-value on top. Falls back to the metadata heuristic if the bank is unavailable.
"""

from typing import Optional

from mumbl_data_contracts.scores import SegmentScore
from mumbl_data_contracts.segments import AudioSegment, TextSegment

from .language_validity import BankValidator


class SegmentScorer:
    """
    Score segments across 6 dimensions: clarity, alignment, diarization,
    transcript_accuracy, validity, shape.
    """

    def __init__(self, validator: Optional[BankValidator] = None):
        """Initialize scorer with default weights and a bank-backed language validator."""
        # Equal weights for all dimensions
        self.weights = {
            "clarity": 1.0,
            "alignment": 1.0,
            "diarization": 1.0,
            "transcript_accuracy": 1.0,
            "validity": 1.0,
            "shape": 1.0,
        }
        # The bank is the language-truth half of the system; wired in by default (lazy + graceful).
        self.validator = validator if validator is not None else BankValidator()

    def score_text_segment(self, segment: TextSegment) -> SegmentScore:
        """
        Score a text segment (clarity, validity, shape only).

        Args:
            segment: TextSegment to score

        Returns:
            SegmentScore with filled dimensions
        """
        # Clarity: Text readability (based on length, punctuation, etc.)
        clarity = self._score_text_clarity(segment.text)

        # Validity: bank language-attestation (the spine) + conversational labels on top
        lang = self.validator.validity(segment.text) if self.validator else None
        validity = self._score_text_validity(segment, lang)

        # Shape: Length, structure appropriateness
        shape = self._score_text_shape(segment.text)

        # Text segments don't have alignment, diarization, transcript_accuracy
        # Use 0.0 as default (not applicable) rather than None
        alignment = 0.0
        diarization = 0.0
        transcript_accuracy = 0.0

        # Calculate total (only count applicable dimensions for text)
        applicable_dims = [clarity, validity, shape]
        total = sum(applicable_dims) / len(applicable_dims) if applicable_dims else 0.0

        return SegmentScore(
            clarity=clarity,
            alignment=alignment,
            diarization=diarization,
            transcript_accuracy=transcript_accuracy,
            validity=validity,
            shape=shape,
            total=total,
            eligible_learner=total >= 90,
            eligible_training=total >= 70,
            notes=self._segment_notes(segment.labels, lang),
        )

    def score_audio_segment(self, segment: AudioSegment) -> SegmentScore:
        """
        Score an audio segment (all 6 dimensions).

        Args:
            segment: AudioSegment to score

        Returns:
            SegmentScore with all dimensions filled
        """
        # Clarity: Audio quality (SNR approximation via confidence scores)
        clarity = self._score_audio_clarity(segment)

        # Alignment: ASR confidence, word timing accuracy
        alignment = self._score_alignment(segment.alignment_confidence)

        # Diarization: Speaker separation quality
        diarization = self._score_diarization(segment.diarization_confidence)

        # Transcript accuracy: Transcription quality
        transcript_accuracy = self._score_transcript_accuracy(segment)

        # Validity: bank-attested transcript is the spine; falls back to metadata heuristic
        lang = (
            self.validator.validity(segment.transcript_text)
            if self.validator and segment.transcript_text
            else None
        )
        validity = self._score_audio_validity(segment, lang)

        # Shape: Length, structure appropriateness
        shape = self._score_audio_shape(segment)

        # Calculate total (weighted average)
        dims = [
            clarity * self.weights["clarity"],
            alignment * self.weights["alignment"],
            diarization * self.weights["diarization"],
            transcript_accuracy * self.weights["transcript_accuracy"],
            validity * self.weights["validity"],
            shape * self.weights["shape"],
        ]
        total_weight = sum(self.weights.values())
        total = sum(dims) / total_weight if total_weight > 0 else 0.0

        notes = self._segment_notes(None, lang) if lang is not None else None
        return SegmentScore(
            clarity=clarity,
            alignment=alignment,
            diarization=diarization,
            transcript_accuracy=transcript_accuracy,
            validity=validity,
            shape=shape,
            total=total,
            eligible_learner=total >= 90,
            eligible_training=total >= 70,
            notes=notes,
        )

    def _score_text_clarity(self, text: str) -> float:
        """Score text clarity (0-100)."""
        if not text or len(text.strip()) == 0:
            return 0.0

        score = 70.0  # Base score

        # Longer text tends to be clearer
        if len(text) > 50:
            score += 10

        # Has punctuation (indicates structure)
        if any(c in text for c in ".!?;,"):
            score += 10

        # Has capitalization (indicates structure)
        if any(c.isupper() for c in text):
            score += 5

        # Has whitespace (readable)
        if " " in text:
            score += 5

        return min(100.0, score)

    def _score_text_validity(self, segment: TextSegment, lang=None) -> float:
        """Score text validity (0-100).

        Bank-backed: language attestation is the spine (real target-language text scores high,
        English or noise scores low), and the conversational labels add learner-value ON TOP of
        valid content; they no longer rescue non-target text. Falls back to the heuristic if absent.
        """
        if lang is None:
            score = 80.0  # Base score (no bank — metadata-only fallback)
            if segment.labels.topic:
                score += 10
            if segment.labels.register_type:
                score += 10
            return min(100.0, score)

        pct, _unknown = lang
        score = pct
        # Reward the conversational labels only once the content is plausibly real target language,
        # so a well-labeled English segment stays correctly invalid.
        if pct >= 50:
            if segment.labels.is_dialogue:
                score += 3
            if segment.labels.topic:
                score += 4
            if segment.labels.register_type:
                score += 3
        return min(100.0, score)

    @staticmethod
    def _segment_notes(labels, lang) -> Optional[str]:
        """Keep the conversational labels visible downstream, and surface what the bank couldn't
        attest (those unknown words are exactly the discovery/promotion-loop candidates)."""
        parts = []
        if labels is not None:
            tags = [
                t
                for t in [
                    ("dialogue" if labels.is_dialogue else None),
                    labels.topic,
                    labels.register_type,
                ]
                if t
            ]
            if tags:
                parts.append("labels: " + " · ".join(tags))
        if lang is not None:
            pct, unknown = lang
            parts.append(f"bank-validity {pct:.0f}%")
            if unknown:
                parts.append("unattested: " + ", ".join(unknown[:8]))
        return "; ".join(parts) or None

    def _score_text_shape(self, text: str) -> float:
        """Score text shape (0-100)."""
        if not text:
            return 0.0

        length = len(text)

        # Ideal length: 50-500 characters
        if 50 <= length <= 500:
            return 100.0
        elif 20 <= length < 50:
            return 80.0
        elif 500 < length <= 1000:
            return 80.0
        elif length < 20:
            return 50.0
        else:
            return 60.0

    def _score_audio_clarity(self, segment: AudioSegment) -> float:
        """Score audio clarity (0-100)."""
        # Use alignment confidence as proxy for audio quality
        if segment.alignment_confidence is not None:
            return segment.alignment_confidence * 100
        return 70.0  # Default if no confidence available

    def _score_alignment(self, alignment_confidence: Optional[float]) -> float:
        """Score alignment quality (0-100)."""
        if alignment_confidence is None:
            return 50.0  # Unknown alignment
        return alignment_confidence * 100

    def _score_diarization(self, diarization_confidence: Optional[float]) -> float:
        """Score diarization quality (0-100)."""
        if diarization_confidence is None:
            # If no diarization, check if speaker_id exists
            # For now, assume single speaker if no diarization
            return 75.0
        return diarization_confidence * 100

    def _score_transcript_accuracy(self, segment: AudioSegment) -> float:
        """Score transcript accuracy (0-100)."""
        # Use alignment confidence as proxy
        if segment.alignment_confidence is not None:
            return segment.alignment_confidence * 100

        # Has transcript text
        if segment.transcript_text and len(segment.transcript_text.strip()) > 0:
            return 70.0

        return 0.0

    def _score_audio_validity(self, segment: AudioSegment, lang=None) -> float:
        """Score audio validity (0-100). Bank-attested transcript is the spine when available;
        otherwise the metadata heuristic."""
        if lang is not None:
            pct, _unknown = lang
            score = pct
            if pct >= 50:  # plausibly real target-language transcript
                if segment.lang:
                    score += 5
                if segment.speaker_id:
                    score += 5
            return min(100.0, score)

        score = 70.0  # Base score (no bank — metadata-only fallback)
        if segment.lang:
            score += 10
        if segment.transcript_text:
            score += 10
        if segment.speaker_id:
            score += 10
        return min(100.0, score)

    def _score_audio_shape(self, segment: AudioSegment) -> float:
        """Score audio shape (0-100)."""
        duration = segment.end - segment.start

        # Ideal duration: 2-12 seconds
        if 2.0 <= duration <= 12.0:
            return 100.0
        elif 1.0 <= duration < 2.0:
            return 80.0
        elif 12.0 < duration <= 15.0:
            return 80.0
        elif duration < 1.0:
            return 50.0
        else:
            return 60.0
