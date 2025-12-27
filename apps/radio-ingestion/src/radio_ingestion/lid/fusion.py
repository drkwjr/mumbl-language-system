"""Fusion logic for combining audio, text, and context LID predictions"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import structlog

logger = structlog.get_logger(__name__)


class LIDFusion:
    """
    Fuse multiple LID signals using weighted log-probability fusion.
    
    Formula:
        fused = softmax(
            w_a * log(audio_lid + eps)
          + w_t * log(text_lid + eps)
          + w_c * log(context_prior + eps)
        )
    
    Default weights: w_a=0.5, w_t=0.4, w_c=0.1
    """
    
    EPSILON = 1e-10  # Small value to avoid log(0)
    
    def __init__(
        self,
        audio_weight: float = 0.5,
        text_weight: float = 0.4,
        context_weight: float = 0.1
    ):
        """
        Initialize fusion with weights.
        
        Args:
            audio_weight: Weight for audio LID (default: 0.5)
            text_weight: Weight for text LID (default: 0.4)
            context_weight: Weight for context prior (default: 0.1)
        
        Note: Weights should sum to 1.0 (will be normalized if not)
        """
        total_weight = audio_weight + text_weight + context_weight
        
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(
                "LID fusion weights don't sum to 1.0, normalizing",
                original_weights=(audio_weight, text_weight, context_weight),
                total=total_weight
            )
            # Normalize
            audio_weight /= total_weight
            text_weight /= total_weight
            context_weight /= total_weight
        
        self.audio_weight = audio_weight
        self.text_weight = text_weight
        self.context_weight = context_weight
        
        logger.info(
            "LID fusion initialized",
            audio_weight=audio_weight,
            text_weight=text_weight,
            context_weight=context_weight
        )
    
    def normalize_probabilities(
        self,
        predictions: List[Tuple[str, float]]
    ) -> Dict[str, float]:
        """
        Normalize predictions to probability distribution.
        
        Args:
            predictions: List of (lang_code, score) tuples
        
        Returns:
            Dictionary mapping language codes to probabilities
        """
        if not predictions:
            return {}
        
        # Extract scores
        scores = np.array([score for _, score in predictions])
        
        # Normalize to probabilities (softmax)
        exp_scores = np.exp(scores - np.max(scores))  # Subtract max for numerical stability
        probs = exp_scores / np.sum(exp_scores)
        
        # Build dictionary
        result = {
            lang_code: float(prob)
            for (lang_code, _), prob in zip(predictions, probs)
        }
        
        return result
    
    def fuse_predictions(
        self,
        audio_predictions: Optional[List[Tuple[str, float]]] = None,
        text_predictions: Optional[List[Tuple[str, float]]] = None,
        context_prior: Optional[Dict[str, float]] = None,
        min_confidence: float = 0.1
    ) -> Dict[str, float]:
        """
        Fuse multiple LID predictions.
        
        Args:
            audio_predictions: Audio LID predictions (lang_code, prob)
            text_predictions: Text LID predictions (lang_code, prob)
            context_prior: Context prior probabilities (e.g., from station history)
            min_confidence: Minimum probability to include (default: 0.1)
        
        Returns:
            Fused probability distribution as dictionary
        """
        # Collect all languages
        all_langs = set()
        
        if audio_predictions:
            all_langs.update(lang for lang, _ in audio_predictions)
        
        if text_predictions:
            all_langs.update(lang for lang, _ in text_predictions)
        
        if context_prior:
            all_langs.update(context_prior.keys())
        
        if not all_langs:
            logger.warning("No language predictions to fuse")
            return {}
        
        # Convert predictions to normalized distributions
        audio_probs = {}
        if audio_predictions:
            audio_probs = self.normalize_probabilities(audio_predictions)
        
        text_probs = {}
        if text_predictions:
            text_probs = self.normalize_probabilities(text_predictions)
        
        context_probs = context_prior or {}
        
        # Compute weighted log-probabilities
        fused_log_probs = {}
        
        for lang in all_langs:
            audio_prob = audio_probs.get(lang, 0.0)
            text_prob = text_probs.get(lang, 0.0)
            context_prob = context_probs.get(lang, 0.0)
            
            # Weighted log-probability sum
            log_sum = (
                self.audio_weight * np.log(audio_prob + self.EPSILON)
                + self.text_weight * np.log(text_prob + self.EPSILON)
                + self.context_weight * np.log(context_prob + self.EPSILON)
            )
            
            fused_log_probs[lang] = log_sum
        
        # Convert back to probabilities (softmax)
        if not fused_log_probs:
            return {}
        
        log_probs_array = np.array(list(fused_log_probs.values()))
        exp_log_probs = np.exp(log_probs_array - np.max(log_probs_array))
        fused_probs = exp_log_probs / np.sum(exp_log_probs)
        
        # Build result dictionary
        result = {
            lang: float(prob)
            for lang, prob in zip(all_langs, fused_probs)
            if prob >= min_confidence
        }
        
        # Sort by probability (descending)
        result = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        
        return result
    
    def get_primary_language(
        self,
        fused_probs: Dict[str, float]
    ) -> Tuple[Optional[str], float]:
        """
        Get primary language from fused probabilities.
        
        Args:
            fused_probs: Fused probability distribution
        
        Returns:
            Tuple of (primary_lang_code, confidence) or (None, 0.0) if empty
        """
        if not fused_probs:
            return None, 0.0
        
        primary_lang = max(fused_probs.items(), key=lambda x: x[1])
        return primary_lang[0], primary_lang[1]


def create_fusion(
    audio_weight: float = 0.5,
    text_weight: float = 0.4,
    context_weight: float = 0.1
) -> LIDFusion:
    """
    Factory function to create LID fusion instance.
    
    Args:
        audio_weight: Weight for audio LID
        text_weight: Weight for text LID
        context_weight: Weight for context prior
    
    Returns:
        LIDFusion instance
    """
    return LIDFusion(
        audio_weight=audio_weight,
        text_weight=text_weight,
        context_weight=context_weight
    )

