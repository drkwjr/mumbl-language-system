"""Audio-based language identification using SpeechBrain"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)

try:
    from speechbrain.inference.classifiers import EncoderClassifier

    SPEECHBRAIN_AVAILABLE = True
except ImportError:
    SPEECHBRAIN_AVAILABLE = False
    logger.warning(
        "SpeechBrain not available. Install with: pip install speechbrain. "
        "For LID, you can also use: pip install speechbrain[lang-id]"
    )

try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Install with: pip install torch")


class AudioLID:
    """
    Audio-based language identification using SpeechBrain VoxLingua107.

    Model: speechbrain/lang-id-voxlingua107-ecapa
    Supports 107 languages including Somali, Arabic, English, etc.
    """

    def __init__(
        self,
        model_name: str = "speechbrain/lang-id-voxlingua107-ecapa",
        device: Optional[str] = None,
    ):
        """
        Initialize audio LID model.

        Args:
            model_name: SpeechBrain model identifier
            device: Device to use ('cpu', 'cuda', or None for auto)
        """
        if not SPEECHBRAIN_AVAILABLE:
            raise ImportError("SpeechBrain is not installed. Install with: pip install speechbrain")

        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is not installed. Install with: pip install torch")

        self.model_name = model_name

        # Auto-detect device if not specified
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        # Load model (will download on first use)
        try:
            logger.info("Loading SpeechBrain LID model", model=model_name, device=device)
            self.classifier = EncoderClassifier.from_hparams(
                source=model_name, run_opts={"device": device}
            )
            self.label_encoder = getattr(self.classifier.hparams, "label_encoder", None)
            logger.info("LID model loaded successfully", device=device)
        except Exception as e:
            logger.error("Failed to load LID model", model=model_name, error=str(e))
            raise

    def _resolve_label(self, index: int, fallback: str) -> str:
        if not self.label_encoder:
            return fallback
        try:
            ind2lab = getattr(self.label_encoder, "ind2lab", None)
            if isinstance(ind2lab, dict):
                return ind2lab.get(index, fallback)
            if isinstance(ind2lab, list) and index < len(ind2lab):
                return ind2lab[index]
            if hasattr(self.label_encoder, "decode_ndim"):
                decoded = self.label_encoder.decode_ndim([index])
                if decoded:
                    return decoded[0]
        except Exception as exc:
            logger.debug("Failed to resolve label", error=str(exc), index=index)
        return fallback

    def predict_language(self, audio_path: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """
        Predict language from audio file.

        Args:
            audio_path: Path to audio file
            top_k: Number of top predictions to return

        Returns:
            List of (language_code, probability) tuples, sorted by probability
        """
        try:
            # SpeechBrain expects file path
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Get predictions
            out_prob, score, index, text_lab = self.classifier.classify_file(audio_path)

            # Extract probabilities and labels
            # out_prob is a tensor, index contains indices, text_lab contains labels
            probabilities = out_prob[0].cpu().numpy()  # Convert to numpy

            # Get top-k predictions
            top_indices = np.argsort(probabilities)[::-1][:top_k]

            results = []
            for idx in top_indices:
                fallback = text_lab[idx] if idx < len(text_lab) else f"lang_{idx}"
                lang_code = self._resolve_label(idx, fallback)
                prob = float(probabilities[idx])
                results.append((lang_code.lower(), prob))

            logger.debug(
                "LID prediction complete",
                audio_path=audio_path,
                top_lang=results[0][0] if results else None,
                top_prob=results[0][1] if results else None,
            )

            return results

        except Exception as e:
            logger.error("LID prediction failed", audio_path=audio_path, error=str(e))
            return []

    def predict_language_from_array(
        self, audio_data: np.ndarray, sample_rate: int = 22050, top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Predict language from audio array.

        Args:
            audio_data: Audio samples as numpy array
            sample_rate: Sample rate of audio
            top_k: Number of top predictions to return

        Returns:
            List of (language_code, probability) tuples
        """
        try:
            import tempfile

            import soundfile as sf

            # Save to temporary file for SpeechBrain
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                sf.write(tmp_file.name, audio_data, sample_rate)
                tmp_path = tmp_file.name

            try:
                results = self.predict_language(tmp_path, top_k=top_k)
            finally:
                # Clean up temp file
                Path(tmp_path).unlink()

            return results

        except Exception as e:
            logger.error("LID prediction from array failed", error=str(e))
            return []

    def predict_segment(
        self, audio_path: str, start_time: float, end_time: float, top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Predict language for a specific segment of audio.

        Args:
            audio_path: Path to full audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            top_k: Number of top predictions

        Returns:
            List of (language_code, probability) tuples
        """
        try:
            import tempfile

            import librosa
            import soundfile as sf

            # Load audio segment
            audio_data, sr = librosa.load(
                audio_path, sr=None, offset=start_time, duration=end_time - start_time, mono=True
            )

            # Predict using array method
            return self.predict_language_from_array(audio_data, sample_rate=sr, top_k=top_k)

        except Exception as e:
            logger.warning(
                "Segment LID prediction failed",
                audio_path=audio_path,
                start_time=start_time,
                end_time=end_time,
                error=str(e),
            )
            return []


def create_lid_model(model_name: Optional[str] = None, device: Optional[str] = None) -> AudioLID:
    """
    Factory function to create LID model.

    Args:
        model_name: Model identifier (default: voxlingua107)
        device: 'cpu' or 'cuda' (None for auto)

    Returns:
        AudioLID instance
    """
    if model_name is None:
        model_name = "speechbrain/lang-id-voxlingua107-ecapa"

    return AudioLID(model_name=model_name, device=device)
