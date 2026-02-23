"""Mumbl Utils Package - Character handling and text utilities"""

from mumbl_utils.text_utils import (
    clean_ocr_artifacts,
    extract_phonemes,
    is_valid_ipa,
    normalize_unicode,
)

__all__ = [
    "clean_ocr_artifacts",
    "normalize_unicode",
    "is_valid_ipa",
    "extract_phonemes",
]
