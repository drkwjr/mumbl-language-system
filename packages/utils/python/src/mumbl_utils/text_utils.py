"""
Text and character utilities for linguistic data processing.

Handles Unicode normalization, OCR artifact removal, and IPA validation.
"""

import unicodedata
from typing import List, Set

# OCR artifacts to remove (not linguistic symbols)
OCR_GARBAGE = {
    "¢",  # Cent sign (OCR artifact)
    "®",  # Registered trademark
    "©",  # Copyright
    "™",  # Trademark
    "€",  # Euro sign
    "§",  # Section sign
    "¶",  # Pilcrow
    "†",  # Dagger
    "‡",  # Double dagger
}

# Valid linguistic symbols to PRESERVE
LINGUISTIC_SYMBOLS = {
    # IPA vowels
    "ɛ",
    "ɔ",
    "ə",
    "ɨ",
    "ʉ",
    "ɯ",
    "ɪ",
    "ʏ",
    "ʊ",
    "œ",
    "ø",
    "ɞ",
    "ɤ",
    "ɐ",
    "ɑ",
    "ɒ",
    # IPA consonants
    "ŋ",
    "ɲ",
    "ʃ",
    "ʒ",
    "θ",
    "ð",
    "ɣ",
    "χ",
    "ʁ",
    "ħ",
    "ʕ",
    "ʔ",
    "ɾ",
    "ɹ",
    "ɻ",
    "ʙ",
    "ʀ",
    "ɢ",
    "ɡ",
    "ɟ",
    "ʄ",
    "ɓ",
    "ɗ",
    "ʛ",
    "ʈ",
    "ɖ",
    "ɳ",
    "ɽ",
    "ʂ",
    "ʐ",
    "ɕ",
    "ʑ",
    "ç",
    "ʝ",
    "ɥ",
    "ʋ",
    "ɰ",
    "ʎ",
    "ʟ",
    "ɬ",
    "ɮ",
    # Diacritics and combining marks
    "\u0301",  # Combining acute accent
    "\u0300",  # Combining grave accent
    "\u0302",  # Combining circumflex
    "\u0303",  # Combining tilde
    "\u0304",  # Combining macron
    "\u0308",  # Combining diaeresis
    "\u030c",  # Combining caron
    "\u0361",  # Combining double inverted breve (tie bar)
    # Latin extended (tone marks for Twi, etc.)
    "á",
    "à",
    "â",
    "ã",
    "ä",
    "å",
    "ā",
    "é",
    "è",
    "ê",
    "ë",
    "ē",
    "í",
    "ì",
    "î",
    "ï",
    "ī",
    "ó",
    "ò",
    "ô",
    "õ",
    "ö",
    "ō",
    "ú",
    "ù",
    "û",
    "ü",
    "ū",
    "ñ",
    "č",
    "š",
    "ž",
}


def clean_ocr_artifacts(text: str, preserve_linguistic: bool = True) -> str:
    """
    Remove OCR artifacts while preserving linguistic symbols.

    Args:
        text: Text to clean
        preserve_linguistic: If True, keeps IPA and tone marks

    Returns:
        Cleaned text
    """
    if not preserve_linguistic:
        # Aggressive cleaning (remove all non-ASCII)
        return text.encode("ascii", errors="ignore").decode("ascii")

    # Smart cleaning: Remove garbage, keep linguistic symbols
    cleaned = []
    for char in text:
        if char in OCR_GARBAGE:
            continue  # Skip garbage
        elif char in LINGUISTIC_SYMBOLS:
            cleaned.append(char)  # Keep linguistic symbols
        elif ord(char) < 128:
            cleaned.append(char)  # Keep ASCII
        elif unicodedata.category(char).startswith("L"):
            cleaned.append(char)  # Keep all letters
        elif unicodedata.category(char).startswith("M"):
            cleaned.append(char)  # Keep combining marks
        elif char in {" ", "\n", "\t", ".", ",", "!", "?", ";", ":", "-", "'", '"'}:
            cleaned.append(char)  # Keep basic punctuation
        # Everything else is dropped

    return "".join(cleaned)


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """
    Normalize Unicode text to standard form.

    Args:
        text: Text to normalize
        form: Normalization form (NFC, NFD, NFKC, NFKD)
            - NFC: Canonical composition (RECOMMENDED for storage)
            - NFD: Canonical decomposition (RECOMMENDED for processing)

    Returns:
        Normalized text
    """
    return unicodedata.normalize(form, text)


def is_valid_ipa(text: str) -> bool:
    """
    Check if text contains only valid IPA symbols.

    Returns:
        True if all characters are valid IPA or basic punctuation
    """
    valid_chars = LINGUISTIC_SYMBOLS | set(" .,-!?'\"\n\t")

    for char in text:
        if ord(char) < 128:  # ASCII is always valid
            continue
        if char not in valid_chars:
            return False

    return True


def extract_phonemes(ipa_text: str) -> List[str]:
    """
    Extract individual phonemes from IPA text.

    Handles combining diacritics (e.g., 'a' + combining accent = 'á')

    Args:
        ipa_text: IPA notation string

    Returns:
        List of phoneme strings
    """
    # Normalize to NFD (decomposed) so we can see combining marks
    decomposed = unicodedata.normalize("NFD", ipa_text)

    phonemes = []
    current = []

    for char in decomposed:
        category = unicodedata.category(char)

        if category.startswith("M"):  # Combining mark
            current.append(char)
        else:
            if current:
                # Finish previous phoneme
                phonemes.append("".join(current))
                current = []
            if char.strip():  # Not whitespace
                current.append(char)

    if current:
        phonemes.append("".join(current))

    # Normalize back to NFC (composed)
    return [unicodedata.normalize("NFC", p) for p in phonemes if p.strip()]


# Example usage and tests
if __name__ == "__main__":
    # Test cleaning
    dirty = "This costs ¢5.00 and is © trademarked™"
    clean = clean_ocr_artifacts(dirty)
    print(f"Cleaned: {clean}")

    # Test IPA preservation
    ipa = "asasé ɛbɛ ŋ ɲ"
    cleaned_ipa = clean_ocr_artifacts(ipa)
    print(f"IPA preserved: {cleaned_ipa}")

    # Test phoneme extraction
    phonemes = extract_phonemes("asasé")
    print(f"Phonemes: {phonemes}")
