"""
Integration tests for TTS Trainer components.
Tests actual functionality to identify issues.
"""

import json
import os
import tempfile

import pytest


def test_tts_trainer_imports():
    """Test that all TTS trainer modules can be imported."""
    try:
        from tts_trainer.config import TrainingConfig
        from tts_trainer.dataset_loader import load_dataset, validate_dataset_format
        from tts_trainer.evaluator import ModelEvaluator
        from tts_trainer.registry import ModelRegistry
        from tts_trainer.trainer import TTSTrainer

        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import TTS trainer modules: {e}")


def test_training_config():
    """Test TrainingConfig class."""
    try:
        from tts_trainer.config import TrainingConfig

        config = TrainingConfig(dataset_path="/path/to/dataset", language="en", dialect="en-US")

        assert config.model_type == "vits"
        assert config.learning_rate > 0
        assert config.batch_size > 0
        assert config.epochs > 0
        assert config.dataset_path == "/path/to/dataset"
        assert config.language == "en"

        # Test config file save/load
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            config.to_file(config_path)

            assert os.path.exists(config_path)

            # Load config
            loaded_config = TrainingConfig.from_file(config_path)
            assert loaded_config.language == config.language
            assert loaded_config.model_type == config.model_type

    except Exception as e:
        pytest.fail(f"TrainingConfig test failed: {e}")


def test_dataset_loader():
    """Test dataset loader functionality."""
    try:
        from tts_trainer.dataset_loader import load_dataset, validate_dataset_format

        # Create test manifest
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "manifest.jsonl")

            # Write test entries
            entries = [
                {"audio_file": "/path/to/audio1.wav", "transcript_text": "Hello world"},
                {"audio_file": "/path/to/audio2.wav", "transcript_text": "Test transcript"},
            ]

            with open(manifest_path, "w", encoding="utf-8") as f:
                for entry in entries:
                    f.write(json.dumps(entry) + "\n")

            # Load dataset
            loaded = load_dataset(manifest_path)

            assert len(loaded) == 2
            assert loaded[0]["transcript_text"] == "Hello world"

            # Validate format
            validation = validate_dataset_format(loaded)

            assert validation["total_entries"] == 2
            # Note: validation will show errors because audio files don't exist
            # This is expected in tests

    except Exception as e:
        pytest.fail(f"Dataset loader test failed: {e}")


def test_trainer_initialization():
    """Test TTSTrainer initialization."""
    try:
        from tts_trainer.config import TrainingConfig
        from tts_trainer.trainer import TTSTrainer

        with tempfile.TemporaryDirectory() as tmpdir:
            config = TrainingConfig(
                dataset_path="/fake/path",
                language="en",
                checkpoint_dir=os.path.join(tmpdir, "checkpoints"),
            )

            trainer = TTSTrainer(config)

            assert trainer.config == config
            assert trainer.current_epoch == 0
            assert trainer.current_step == 0

    except Exception as e:
        pytest.fail(f"TTSTrainer initialization test failed: {e}")


def test_evaluator():
    """Test ModelEvaluator."""
    try:
        from tts_trainer.evaluator import ModelEvaluator

        evaluator = ModelEvaluator()

        # Test MOS-lite (stubbed)
        samples = [
            {"audio": None, "transcript": "Test 1"},
            {"audio": None, "transcript": "Test 2"},
        ]

        mos_result = evaluator.mos_lite(samples)
        assert "overall" in mos_result
        assert "sample_count" in mos_result

        # Test pronunciation error rate
        predictions = ["hello", "world"]
        ground_truth = ["hello", "world"]

        pronunciation_result = evaluator.pronunciation_error_rate(predictions, ground_truth)
        assert "error_rate" in pronunciation_result
        assert "accuracy" in pronunciation_result

        # Test stability
        stability_result = evaluator.stability(samples)
        assert "stability_score" in stability_result

    except Exception as e:
        pytest.fail(f"Evaluator test failed: {e}")


def test_model_registry():
    """Test ModelRegistry (requires database connection)."""
    try:
        from tts_trainer.registry import ModelRegistry

        registry = ModelRegistry()
        assert registry is not None

        # Note: Actual registration requires database connection
        # This test just verifies the class can be instantiated

    except Exception as e:
        pytest.fail(f"ModelRegistry test failed: {e}")
