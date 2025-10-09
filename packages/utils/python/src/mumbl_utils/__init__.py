"""Mumbl Utils Package - Character handling and text utilities"""

from mumbl_utils.text_utils import (
    clean_ocr_artifacts,
    normalize_unicode,
    is_valid_ipa,
    extract_phonemes,
)

__all__ = [
    "clean_ocr_artifacts",
    "normalize_unicode",
    "is_valid_ipa",
    "extract_phonemes",
]

