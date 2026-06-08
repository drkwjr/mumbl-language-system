#!/usr/bin/env python3
"""Language identification by EVIDENCE, not by string.

A form's language is not a property of its spelling — it's membership backed by evidence. And membership
is a SET, not a single value: words are routinely multilingual (loanwords, cognates, proper nouns). So
`membership(token)` returns every language that has evidence for the token, each with the evidence types
and a tier. This replaces the crude "is it in the English dictionary" filter with something principled
and extensible — adding Somali or Spanish later is just adding their lexicon + orthographic signals.

Evidence, strongest first:
  lexicon      the token is attested in that language's verified words (our bank, or the English dict)
  orthography  it carries letters essentially unique to that language (Akan ɛ ɔ ŋ)
  morphology   it decomposes via that language's grammar (an inflection of a known stem)

  python3 bank/language_id.py nsuo asopiti set Kofi the   # show membership for tokens
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import morphophon as mp  # noqa: E402

# Per-language config. Extend this dict to add a language (Somali 'som', Spanish 'spa', ...).
ORTHO_SIGNAL = {"aka": set("ɛɔŋɪʊ")}  # letters that essentially never occur in English

_ENGLISH = None


def _english():
    global _ENGLISH
    if _ENGLISH is None:
        try:
            _ENGLISH = {w.strip().lower() for w in open("/usr/share/dict/words", encoding="utf-8", errors="replace")}
        except OSError:
            _ENGLISH = set()
    return _ENGLISH


def _tier(ev):
    if "lexicon" in ev or "orthography" in ev:
        return "attested"
    if "morphology" in ev:
        return "derived"
    return "weak"


def membership(token, bank):
    """-> {lang: {'evidence': [...], 'tier': ...}}. A set; multilingual tokens get multiple langs."""
    tok = token.lower().strip("'’")
    out = {}

    # Akan / Twi (aka): orthography + bank lexicon + morphology
    ev = []
    if ORTHO_SIGNAL["aka"] & set(tok):
        ev.append("orthography")
    if tok in bank.known:
        ev.append("lexicon")
    elif mp.is_known_morph(bank, tok, bank.pkey_index).get("how") == "morph":
        ev.append("morphology")
    if ev:
        out["aka"] = {"evidence": ev, "tier": _tier(ev)}

    # English (eng): the contrast language, from the system dictionary (incl. simple plurals)
    eng = _english()
    if len(tok) > 1 and (tok in eng or tok.rstrip("s") in eng):
        out["eng"] = {"evidence": ["lexicon"], "tier": "attested"}

    return out


def primary(token, bank, context_lang=None):
    """Best single-language guess. In a known-language context (e.g. a Twi corpus), that language wins
    ties; otherwise the strongest evidence does."""
    m = membership(token, bank)
    if not m:
        return None
    if context_lang and context_lang in m:
        return context_lang
    order = {"attested": 2, "derived": 1, "weak": 0}
    return max(m, key=lambda lang: order[m[lang]["tier"]])


def looks_like(token, bank, lang):
    """Does the token have evidence for `lang` (orthography/morphology), even if not yet in the lexicon?
    Used by discovery to keep plausible new words of a language without needing them pre-attested."""
    m = membership(token, bank).get(lang, {})
    return bool(m) and ("lexicon" not in m["evidence"])  # plausible but not yet known


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from serve import Bank
    bank = Bank()
    for tok in sys.argv[1:] or ["nsuo", "asopiti", "ɔdɔfo", "set", "Kofi", "the", "wɔbɛba"]:
        m = membership(tok, bank)
        tags = ", ".join(f"{lang} ({'/'.join(v['evidence'])}, {v['tier']})" for lang, v in m.items()) or "unknown"
        print(f"  {tok:12} -> {tags}")


if __name__ == "__main__":
    main()
