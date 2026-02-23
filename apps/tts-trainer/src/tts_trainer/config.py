"""
Training configuration for TTS models.
"""

import json
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """
    Training configuration for VITS TTS model.
    """

    # Model type
    model_type: str = "vits"

    # Hyperparameters
    learning_rate: float = Field(default=2e-4, description="Learning rate")
    batch_size: int = Field(default=16, description="Batch size")
    epochs: int = Field(default=100, description="Number of epochs")
    warmup_steps: int = Field(default=4000, description="Warmup steps")

    # VITS-specific hyperparameters
    segment_size: int = Field(default=8192, description="Segment size for VITS")
    n_speakers: int = Field(default=1, description="Number of speakers")
    speaker_dim: int = Field(default=256, description="Speaker embedding dimension")

    # Audio configuration
    sample_rate: int = Field(default=22050, description="Audio sample rate")
    hop_length: int = Field(default=256, description="Hop length for mel spectrogram")
    n_mel_channels: int = Field(default=80, description="Number of mel channels")

    # Dataset configuration
    dataset_path: str = Field(description="Path to dataset manifest")
    language: str = Field(description="Language code")
    dialect: Optional[str] = Field(default=None, description="Dialect code")

    # Speaker configuration
    speaker_config: Optional[Dict[str, Any]] = Field(
        default=None, description="Speaker-specific config"
    )

    # Checkpoint configuration
    checkpoint_dir: str = Field(default="checkpoints", description="Checkpoint directory")
    save_interval: int = Field(default=10, description="Save checkpoint every N epochs")

    # Logging
    log_dir: str = Field(default="logs", description="Log directory")

    @classmethod
    def from_file(cls, config_path: str) -> "TrainingConfig":
        """Load configuration from YAML or JSON file."""
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.endswith(".yaml") or config_path.endswith(".yml"):
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        return cls(**data)

    def to_file(self, config_path: str):
        """Save configuration to file."""
        data = self.model_dump()

        with open(config_path, "w", encoding="utf-8") as f:
            if config_path.endswith(".yaml") or config_path.endswith(".yml"):
                yaml.dump(data, f, default_flow_style=False)
            else:
                json.dump(data, f, indent=2)
