"""Unit tests for language identification module"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from radio_ingestion.lid.aggregator import StationAggregator, create_aggregator
from radio_ingestion.lid.fusion import LIDFusion, create_fusion
from radio_ingestion.lid.llm_verifier import LLMVerifier, create_llm_verifier


class TestLIDFusion:
    """Test LID fusion logic"""

    def test_init(self):
        """Test fusion initialization"""
        fusion = LIDFusion(audio_weight=0.5, text_weight=0.4, context_weight=0.1)
        assert fusion.audio_weight == 0.5
        assert fusion.text_weight == 0.4
        assert fusion.context_weight == 0.1

    def test_init_normalizes_weights(self):
        """Test that weights are normalized if they don't sum to 1.0"""
        fusion = LIDFusion(audio_weight=1.0, text_weight=1.0, context_weight=1.0)
        total = fusion.audio_weight + fusion.text_weight + fusion.context_weight
        assert abs(total - 1.0) < 0.01

    def test_normalize_probabilities(self):
        """Test probability normalization"""
        fusion = LIDFusion()

        predictions = [("en", 0.8), ("fr", 0.5), ("de", 0.3)]
        probs = fusion.normalize_probabilities(predictions)

        assert "en" in probs
        assert "fr" in probs
        assert "de" in probs
        assert abs(sum(probs.values()) - 1.0) < 0.01
        assert probs["en"] > probs["fr"] > probs["de"]

    def test_fuse_predictions_audio_only(self):
        """Test fusion with only audio predictions"""
        fusion = LIDFusion()

        audio_preds = [("so", 0.9), ("en", 0.05), ("ar", 0.05)]

        fused = fusion.fuse_predictions(audio_predictions=audio_preds)

        assert "so" in fused
        assert fused["so"] > 0.5  # Should be highest

    def test_fuse_predictions_audio_and_text(self):
        """Test fusion with audio and text predictions"""
        fusion = LIDFusion(audio_weight=0.6, text_weight=0.4, context_weight=0.0)

        audio_preds = [("so", 0.8), ("en", 0.2)]
        text_preds = [("en", 0.7), ("so", 0.3)]

        fused = fusion.fuse_predictions(audio_predictions=audio_preds, text_predictions=text_preds)

        # Should combine both signals
        assert "so" in fused
        assert "en" in fused

    def test_fuse_predictions_with_context(self):
        """Test fusion with context prior"""
        fusion = LIDFusion(audio_weight=0.5, text_weight=0.4, context_weight=0.1)

        audio_preds = [("so", 0.9), ("en", 0.1)]
        context_prior = {"so": 0.8, "en": 0.2}

        fused = fusion.fuse_predictions(audio_predictions=audio_preds, context_prior=context_prior)

        # Context should boost "so"
        assert "so" in fused

    def test_get_primary_language(self):
        """Test getting primary language"""
        fusion = LIDFusion()

        fused_probs = {"so": 0.6, "en": 0.3, "ar": 0.1}
        primary, confidence = fusion.get_primary_language(fused_probs)

        assert primary == "so"
        assert confidence == 0.6

    def test_get_primary_language_empty(self):
        """Test getting primary language from empty distribution"""
        fusion = LIDFusion()
        primary, confidence = fusion.get_primary_language({})

        assert primary is None
        assert confidence == 0.0


class TestStationAggregator:
    """Test station aggregator"""

    def test_init(self):
        """Test aggregator initialization"""
        agg = StationAggregator()
        assert agg is not None

    def test_empty_aggregate(self):
        """Test aggregation with no segments"""
        agg = StationAggregator()
        result = agg.aggregate_hourly([])

        assert result["primary_lang"] is None
        assert result["lang_mix"] == {}
        assert result["total_segments"] == 0
        assert result["switch_rate"] == 0.0

    def test_aggregate_single_language(self):
        """Test aggregation with single language"""
        agg = StationAggregator()

        segments = [
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 10.0,
                "is_speech": True,
            },
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.8},
                "confidence": 0.8,
                "duration": 15.0,
                "is_speech": True,
            },
        ]

        result = agg.aggregate_hourly(segments)

        assert result["primary_lang"] == "so"
        assert "so" in result["lang_mix"]
        assert result["lang_mix"]["so"] > 0.8
        assert result["switch_rate"] == 0.0  # No switches
        assert result["total_segments"] == 2

    def test_aggregate_multiple_languages(self):
        """Test aggregation with multiple languages"""
        agg = StationAggregator()

        segments = [
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9, "en": 0.1},
                "confidence": 0.9,
                "duration": 10.0,
                "is_speech": True,
            },
            {
                "primary_lang": "en",
                "lang_probs": {"en": 0.8, "so": 0.2},
                "confidence": 0.8,
                "duration": 15.0,
                "is_speech": True,
            },
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.7, "ar": 0.3},
                "confidence": 0.7,
                "duration": 20.0,
                "is_speech": True,
            },
        ]

        result = agg.aggregate_hourly(segments)

        assert result["primary_lang"] in ["so", "en"]  # Should be most common
        assert "so" in result["lang_mix"]
        assert "en" in result["lang_mix"]
        assert result["switch_rate"] > 0.0  # Has switches
        assert result["total_segments"] == 3

    def test_aggregate_switch_rate(self):
        """Test switch rate calculation"""
        agg = StationAggregator()

        # 3 segments, 2 switches (so->en->so), 45 seconds total = 1.5 minutes
        segments = [
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 15.0,
                "is_speech": True,
            },
            {
                "primary_lang": "en",
                "lang_probs": {"en": 0.9},
                "confidence": 0.9,
                "duration": 15.0,
                "is_speech": True,
            },
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 15.0,
                "is_speech": True,
            },
        ]

        result = agg.aggregate_hourly(segments)

        # 2 switches / 0.75 minutes = 2.67 switches per minute
        expected_rate = 2.0 / (45.0 / 60.0)
        assert abs(result["switch_rate"] - expected_rate) < 0.1

    def test_aggregate_speech_ratio(self):
        """Test speech ratio calculation"""
        agg = StationAggregator()

        segments = [
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 10.0,
                "is_speech": True,
            },
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 10.0,
                "is_speech": False,
            },  # Not speech
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 10.0,
                "is_speech": True,
            },
        ]

        result = agg.aggregate_hourly(segments)

        # 20 seconds speech / 30 seconds total = 0.67
        assert abs(result["speech_ratio"] - 0.67) < 0.1

    def test_aggregate_confidence_stats(self):
        """Test confidence statistics"""
        agg = StationAggregator()

        segments = [
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.9},
                "confidence": 0.9,
                "duration": 10.0,
                "is_speech": True,
            },
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.8},
                "confidence": 0.8,
                "duration": 10.0,
                "is_speech": True,
            },
            {
                "primary_lang": "so",
                "lang_probs": {"so": 0.7},
                "confidence": 0.7,
                "duration": 10.0,
                "is_speech": True,
            },
        ]

        result = agg.aggregate_hourly(segments)

        assert result["min_confidence"] == 0.7
        assert result["max_confidence"] == 0.9
        assert 0.7 <= result["avg_confidence"] <= 0.9


class TestLLMVerifier:
    """Test LLM verifier"""

    def test_init(self):
        """Test verifier initialization"""
        verifier = LLMVerifier(enabled=False)
        assert verifier.enabled is False

    def test_should_verify_agreement(self):
        """Test verification check when languages agree"""
        verifier = LLMVerifier()

        should_verify = verifier.should_verify(
            audio_lang="so", audio_confidence=0.9, text_lang="so", text_confidence=0.8
        )

        assert should_verify is False  # No disagreement

    def test_should_verify_disagreement_high_confidence(self):
        """Test verification check when languages disagree with high confidence"""
        verifier = LLMVerifier()

        should_verify = verifier.should_verify(
            audio_lang="so", audio_confidence=0.9, text_lang="en", text_confidence=0.85
        )

        assert should_verify is True  # Both confident but disagree

    def test_verify_disagreement_stub(self):
        """Test verification stub returns higher confidence"""
        verifier = LLMVerifier(enabled=False)

        verified_lang, confidence, reason = verifier.verify_disagreement(
            audio_lang="so",
            audio_confidence=0.9,
            text_lang="en",
            text_confidence=0.7,
            transcript="Test transcript",
        )

        assert verified_lang == "so"  # Higher confidence
        assert confidence == 0.9
        assert "audio" in reason.lower()


class TestFactoryFunctions:
    """Test factory functions"""

    def test_create_fusion(self):
        """Test fusion factory"""
        fusion = create_fusion(0.6, 0.3, 0.1)
        assert fusion.audio_weight == 0.6
        assert fusion.text_weight == 0.3
        assert fusion.context_weight == 0.1

    def test_create_aggregator(self):
        """Test aggregator factory"""
        agg = create_aggregator()
        assert isinstance(agg, StationAggregator)

    def test_create_llm_verifier(self):
        """Test verifier factory"""
        verifier = create_llm_verifier(enabled=False)
        assert isinstance(verifier, LLMVerifier)
        assert verifier.enabled is False
