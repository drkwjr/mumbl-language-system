"""Text-based language identification using fastText"""

from typing import List, Tuple, Optional, Dict
import structlog

logger = structlog.get_logger(__name__)

try:
    import fasttext
    FASTTEXT_AVAILABLE = True
except ImportError:
    FASTTEXT_AVAILABLE = False
    logger.warning(
        "fastText not available. Install with: pip install fasttext. "
        "Text-based LID will be disabled."
    )


class TextLID:
    """
    Text-based language identification using fastText.
    
    Model: lid.176.bin (176 languages)
    """
    
    MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
    MODEL_PATH = "lid.176.bin"
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize text LID model.
        
        Args:
            model_path: Path to fastText model file (downloads if not provided)
        """
        if not FASTTEXT_AVAILABLE:
            raise ImportError(
                "fastText is not installed. Install with: pip install fasttext"
            )
        
        self.model_path = model_path or self.MODEL_PATH
        
        # Load model (downloads if needed)
        try:
            logger.info("Loading fastText LID model", model_path=self.model_path)
            self.model = fasttext.load_model(self.model_path)
            logger.info("Text LID model loaded successfully")
        except Exception as e:
            logger.error(
                "Failed to load fastText model",
                model_path=self.model_path,
                error=str(e)
            )
            # Model will download automatically on first use
            # If it fails, user needs to download manually
            raise
    
    def predict_language(
        self,
        text: str,
        top_k: int = 3
    ) -> List[Tuple[str, float]]:
        """
        Predict language from text.
        
        Args:
            text: Text string (minimum 2 characters for fastText)
            top_k: Number of top predictions to return
        
        Returns:
            List of (language_code, probability) tuples
        """
        if not FASTTEXT_AVAILABLE:
            return []
        
        if len(text.strip()) < 2:
            logger.warning("Text too short for LID prediction", text_length=len(text))
            return []
        
        try:
            # fastText predict returns label with __label__ prefix
            # Format: [('__label__en', 0.95)]
            predictions = self.model.predict(text, k=top_k)
            
            labels, scores = predictions
            
            results = []
            for label, score in zip(labels, scores):
                # Remove __label__ prefix and convert to language code
                lang_code = label.replace("__label__", "")
                prob = float(score)
                results.append((lang_code, prob))
            
            logger.debug(
                "Text LID prediction complete",
                text_length=len(text),
                top_lang=results[0][0] if results else None,
                top_prob=results[0][1] if results else None
            )
            
            return results
            
        except Exception as e:
            logger.error(
                "Text LID prediction failed",
                text_length=len(text),
                error=str(e)
            )
            return []


def create_text_lid(model_path: Optional[str] = None) -> Optional[TextLID]:
    """
    Factory function to create text LID model.
    
    Args:
        model_path: Path to fastText model (optional)
    
    Returns:
        TextLID instance or None if fastText not available
    """
    if not FASTTEXT_AVAILABLE:
        return None
    
    try:
        return TextLID(model_path=model_path)
    except Exception as e:
        logger.warning(
            "Text LID model creation failed",
            error=str(e),
            note="Text LID will be disabled"
        )
        return None

