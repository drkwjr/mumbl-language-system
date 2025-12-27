"""Aggregate language statistics per station and hour"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class StationAggregator:
    """
    Aggregate language statistics per station and hour.
    
    Computes:
    - primary_lang: Most common language
    - lang_mix: Language distribution
    - switch_rate: Rate of language switches per minute
    - speech_ratio: Ratio of speech segments
    """
    
    def __init__(self):
        """Initialize aggregator"""
        self.logger = logger
    
    def aggregate_hourly(
        self,
        segments: List[Dict[str, Any]],
        hour: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Aggregate segments for an hour.
        
        Args:
            segments: List of segment dictionaries with:
                - primary_lang: Language code
                - confidence: Confidence score
                - lang_probs: Language probability distribution (dict)
                - start: Start time
                - end: End time
                - is_speech: Boolean
            hour: Hour bucket (defaults to current hour)
        
        Returns:
            Dictionary with aggregated statistics
        """
        if not segments:
            logger.warning("No segments to aggregate")
            return self._empty_aggregate(hour)
        
        # Use provided hour or round to nearest hour
        if hour is None:
            hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        else:
            hour = hour.replace(minute=0, second=0, microsecond=0)
        
        # Aggregate language distributions
        lang_counts = defaultdict(float)
        lang_confidences = defaultdict(list)
        total_duration = 0.0
        speech_duration = 0.0
        language_switches = 0
        
        prev_lang = None
        
        for segment in segments:
            primary_lang = segment.get("primary_lang")
            lang_probs = segment.get("lang_probs", {})
            confidence = segment.get("confidence", 0.0)
            duration = segment.get("duration", 0.0)
            is_speech = segment.get("is_speech", True)
            
            # Skip if no language info
            if not primary_lang and not lang_probs:
                continue
            
            # Aggregate by language probabilities (weighted by duration)
            if lang_probs:
                for lang, prob in lang_probs.items():
                    lang_counts[lang] += prob * duration
                    if confidence > 0:
                        lang_confidences[lang].append(confidence)
            elif primary_lang:
                lang_counts[primary_lang] += duration
                if confidence > 0:
                    lang_confidences[primary_lang].append(confidence)
            
            total_duration += duration
            
            if is_speech:
                speech_duration += duration
            
            # Count language switches
            if prev_lang is not None and primary_lang != prev_lang:
                language_switches += 1
            
            prev_lang = primary_lang
        
        # Normalize language distribution
        if total_duration > 0:
            lang_mix = {
                lang: count / total_duration
                for lang, count in lang_counts.items()
            }
        else:
            lang_mix = {}
        
        # Get primary language
        if lang_mix:
            primary_lang = max(lang_mix.items(), key=lambda x: x[1])[0]
        else:
            primary_lang = None
        
        # Compute confidence statistics
        all_confidences = [
            conf for confs in lang_confidences.values() for conf in confs
        ]
        
        avg_confidence = float(np.mean(all_confidences)) if all_confidences else 0.0
        min_confidence = float(np.min(all_confidences)) if all_confidences else 0.0
        max_confidence = float(np.max(all_confidences)) if all_confidences else 0.0
        
        # Compute switch rate (switches per minute)
        duration_minutes = total_duration / 60.0
        switch_rate = language_switches / duration_minutes if duration_minutes > 0 else 0.0
        
        # Compute speech ratio
        speech_ratio = speech_duration / total_duration if total_duration > 0 else 0.0
        
        # Count segments
        speech_segments = sum(1 for s in segments if s.get("is_speech", True))
        total_segments = len(segments)
        
        result = {
            "hour": hour,
            "primary_lang": primary_lang,
            "lang_mix": lang_mix,
            "switch_rate": switch_rate,
            "total_segments": total_segments,
            "speech_segments": speech_segments,
            "speech_ratio": speech_ratio,
            "avg_confidence": avg_confidence,
            "min_confidence": min_confidence,
            "max_confidence": max_confidence,
        }
        
        logger.info(
            "Hourly aggregation complete",
            hour=hour.isoformat(),
            primary_lang=primary_lang,
            total_segments=total_segments,
            switch_rate=switch_rate
        )
        
        return result
    
    def _empty_aggregate(self, hour: Optional[datetime]) -> Dict[str, Any]:
        """Return empty aggregate for no segments"""
        if hour is None:
            hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        else:
            hour = hour.replace(minute=0, second=0, microsecond=0)
        
        return {
            "hour": hour,
            "primary_lang": None,
            "lang_mix": {},
            "switch_rate": 0.0,
            "total_segments": 0,
            "speech_segments": 0,
            "speech_ratio": 0.0,
            "avg_confidence": 0.0,
            "min_confidence": 0.0,
            "max_confidence": 0.0,
        }


def create_aggregator() -> StationAggregator:
    """Factory function to create aggregator"""
    return StationAggregator()

