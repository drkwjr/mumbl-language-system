"""
Deduplication: exact and near-duplicate detection.
"""

import hashlib
import logging
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _require_sentence_transformers():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for text deduplication. "
            "Install with: pip install sentence-transformers"
        ) from exc
    return SentenceTransformer


from mumbl_data_contracts.segments import AudioSegment, TextSegment


class Deduplicator:
    """
    Find exact and near-duplicate segments.
    """

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize deduplicator.

        Args:
            embedding_model: Sentence transformer model name
        """
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self._text_cache = {}  # Cache embeddings

    def _get_embedding_model(self):
        if self.embedding_model is not None:
            return self.embedding_model
        try:
            SentenceTransformer = _require_sentence_transformers()
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            return self.embedding_model
        except ImportError as exc:
            logger.warning(
                "SentenceTransformer unavailable; skipping near-duplicate checks: %s", exc
            )
            return None

    def find_exact_duplicates(
        self, text_segments: List[TextSegment] = None, audio_segments: List[Dict[str, Any]] = None
    ) -> Dict[str, List[Tuple[int, int]]]:
        """
        Find exact duplicates by hash/fingerprint.

        Args:
            text_segments: List of TextSegment objects
            audio_segments: List of dicts with 'segment' and 'audio_hash' keys

        Returns:
            Dict with keys: 'text_duplicates', 'audio_duplicates'
            Values are lists of (segment_id, duplicate_id) tuples
        """
        text_duplicates = []
        audio_duplicates = []

        # Text duplicates by hash
        if text_segments:
            text_hash_map = defaultdict(list)
            for idx, segment in enumerate(text_segments):
                text_hash = hashlib.sha256(segment.text.encode("utf-8")).hexdigest()
                text_hash_map[text_hash].append(idx)

            # Find groups with multiple segments
            for hash_val, indices in text_hash_map.items():
                if len(indices) > 1:
                    # First segment is kept, others are duplicates
                    for dup_idx in indices[1:]:
                        text_duplicates.append((indices[0], dup_idx))

        # Audio duplicates by fingerprint
        if audio_segments:
            audio_hash_map = defaultdict(list)
            for idx, item in enumerate(audio_segments):
                audio_hash = item.get("audio_hash")
                if audio_hash:
                    audio_hash_map[audio_hash].append(idx)

            # Find groups with multiple segments
            for hash_val, indices in audio_hash_map.items():
                if len(indices) > 1:
                    # First segment is kept, others are duplicates
                    for dup_idx in indices[1:]:
                        audio_duplicates.append((indices[0], dup_idx))

        return {
            "text_duplicates": text_duplicates,
            "audio_duplicates": audio_duplicates,
        }

    def find_near_duplicates(
        self, text_segments: List[TextSegment] = None, threshold: float = 0.95
    ) -> List[Tuple[int, int, float]]:
        """
        Find near-duplicate text segments using embedding similarity.

        Args:
            text_segments: List of TextSegment objects
            threshold: Cosine similarity threshold (0-1)

        Returns:
            List of (segment_idx1, segment_idx2, similarity) tuples
        """
        if not text_segments or len(text_segments) < 2:
            return []

        embedding_model = self._get_embedding_model()
        if embedding_model is None:
            return []

        # Compute embeddings
        texts = [seg.text for seg in text_segments]
        embeddings = embedding_model.encode(texts, show_progress_bar=False)

        # Compute pairwise cosine similarities
        similarities = []
        for i in range(len(text_segments)):
            for j in range(i + 1, len(text_segments)):
                similarity = np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                )
                if similarity >= threshold:
                    similarities.append((i, j, float(similarity)))

        return similarities

    def get_deduplication_report(
        self,
        text_segments: List[TextSegment] = None,
        audio_segments: List[Dict[str, Any]] = None,
        near_dup_threshold: float = 0.95,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive deduplication report.

        Returns:
            Dict with duplicate counts and groups
        """
        exact_dups = self.find_exact_duplicates(text_segments, audio_segments)
        near_dups = []

        if text_segments:
            near_dups = self.find_near_duplicates(text_segments, near_dup_threshold)

        return {
            "exact_duplicates": {
                "text": len(exact_dups["text_duplicates"]),
                "audio": len(exact_dups["audio_duplicates"]),
                "pairs": exact_dups,
            },
            "near_duplicates": {
                "count": len(near_dups),
                "pairs": near_dups,
            },
            "total_text_segments": len(text_segments) if text_segments else 0,
            "total_audio_segments": len(audio_segments) if audio_segments else 0,
        }
