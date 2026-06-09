"""Morphophonology — make the verifier robust to Twi's agglutination + spelling variety.

Two mechanisms, both grounding the construct-and-verify check:
  decompose(word) : strip recognized subject + TAM prefixes (surface) -> root; verify the root.
                    e.g. yɛbɛma -> yɛ + bɛ + ma ("we will give"), root `ma` is known.
  pkey(word)      : a normalized phoneme key via GhanaNLP/twi-g2p (sourced phone set, Cho et al.) —
                    collapses spelling variants by sound (nsuo~nsu, medaase~medase). Optional: if
                    twi-g2p isn't importable the module still decomposes.

The affix inventory is now SOURCED to Christaller §54 (subject prefixes) + the verb-tense formation
section (TAM prefixes), recovered via IIIF vision re-OCR — see bank/data/aka/grammar.jsonl.
"""
import re

# Subject prefixes + TAM markers, SOURCED from Christaller §54 (subject prefixes, leaf 72) and the
# verb-tense formation section (TAM prefixes). See bank/data/aka/grammar.jsonl.
# §54 prefixed nominative forms: me- wo- ɔ- ɛ- yɛ- mo- wɔ-, with i/u-stem variants mi- wu- mu- and the
# ɔ/ɛ ASCII variants o-/e-. (Earlier hand-list wrongly included ne [possessive §55], wɔn [object/
# independent], na, obi — and was MISSING wɔ, the real 3pl subject prefix.)
SUBJECTS = ["me", "mɛ", "wo", "ɔ", "ɛ", "yɛ", "mo", "wɔ", "o", "e", "mi", "wu", "mu"]
# mɛ = the contracted 1sg future (me + bɛ -> mɛ), e.g. mɛtena = "I will stay".
# TAM: progressive re-, future bɛ- (his 'be'), proximate-future rebɛ-, perfect a-, Fante neg-future kɔ-.
TAM = ["bɛ", "re", "a", "kɔ", "be", "ko"]
# Negative marker: a homorganic nasal that precedes the (unchanged) root, e.g. ɔ-re-n-gyaw, mo-n-pɛ.
NEG = ["nn", "mm", "n", "m"]

_g2p = None


def _g2p_fn():
    global _g2p
    if _g2p is False:
        return None
    if _g2p is None:
        try:
            from twi_g2p import TwiG2P

            _g2p = TwiG2P()
        except Exception:
            _g2p = False
            return None
    return _g2p


def pkey(word: str):
    """Normalized phoneme key for variant clustering (None if twi-g2p unavailable)."""
    g = _g2p_fn()
    if not g:
        return None
    try:
        ph = g.convert(word)
    except Exception:
        return None
    s = re.sub(r"[{}\s]", "", ph)
    s = re.sub(r"[̀-̘̙̩͈̰ͯ]", "", s)  # drop ATR/tone diacritics
    s = re.sub(r"(.)\1+", r"\1", s)  # collapse doubled vowels (aa -> a)
    return s.lower()


VOWELS = set("aeiouɛɔ")
_ATR_FLIP = {"e": "ɛ", "ɛ": "e", "o": "ɔ", "ɔ": "o"}
# elided subject/possessive before a vowel-initial stem: m'abusua, n'adwuma, w'akɔ, y'ahunu
_ELIDED = {"m": "me", "n": "ne", "w": "wo", "y": "yɛ"}


def _surface_variants(stem: str):
    """Surface forms of a stem that map to the same root: past-tense / emphatic final-vowel
    lengthening (kɔ~kɔɔ), word-final ATR vowel-harmony alternation (aduane~aduanɛ), and the sh~hw
    consonant alternation lyric/Fante spellings use (shwɛ~hwɛ)."""
    forms = [stem]
    if "sh" in stem:
        forms.append(stem.replace("sh", "hw"))  # shwɛ -> hwɛ
    if len(stem) >= 2 and stem[-1] == stem[-2] and stem[-1] in VOWELS:
        forms.append(stem[:-1])  # de-lengthen a doubled final vowel (past tense)
    for f in list(forms):
        if f and f[-1] in _ATR_FLIP:
            forms.append(f[:-1] + _ATR_FLIP[f[-1]])  # flip the final vowel's ATR value
    return forms


def _root_known(stem: str, is_known):
    return any(is_known(f) for f in _surface_variants(stem) if f)


def _strip_neg(stem: str, is_known):
    """The root itself, or the root after a negative nasal (n-/m-/nn-/mm-); None if neither is known."""
    if _root_known(stem, is_known):
        return stem
    for n in NEG:
        if stem.startswith(n) and len(stem) > len(n) + 1 and _root_known(stem[len(n):], is_known):
            return stem[len(n):]
    return None


def decompose(word: str, is_known):
    """Strip subject (+TAM) prefixes / elision; return (root, [affixes]) if a known root is reached.

    Robust to past-tense final-vowel lengthening and ATR spelling variants via _surface_variants, so
    inflected forms like mekɔɔ (me+kɔ+past) and yɛbɔɔ (yɛ+bɔ+past) resolve to their known roots.
    """
    w = word.lower()
    # elided subject/possessive: m'abusua -> abusua, n'adwuma -> adwuma
    m = re.match(r"^([mnwy])['’](.+)$", w)
    if m and _root_known(m.group(2), is_known):
        return (m.group(2), [_ELIDED[m.group(1)] + "'"])

    fallback = None
    for s in SUBJECTS:
        if not w.startswith(s):
            continue
        r1 = w[len(s):]
        if r1:
            nr = _strip_neg(r1, is_known)  # subject (+ optional negative nasal) -> root
            if nr:
                fallback = fallback or (nr, [s] + (["NEG"] if nr != r1 else []))
        for t in TAM:
            if not r1.startswith(t):
                continue
            r2 = r1[len(t):]
            if r2:
                nr2 = _strip_neg(r2, is_known)  # subject + TAM (+ optional negative) -> root
                if nr2:
                    return (nr2, [s, t] + (["NEG"] if nr2 != r2 else []))
    return fallback


def is_known_morph(bank, word: str, pkey_index=None) -> dict:
    """Verifier: a word is real if it is known directly, decomposes to a known root, or matches a
    known word by phoneme key."""
    if bank.is_known(word)["known"]:
        return {"known": True, "how": "direct"}
    d = decompose(word, lambda w: bank.is_known(w)["known"])
    if d:
        return {"known": True, "how": "morph", "root": d[0], "affixes": d[1]}
    # whole-word surface variant (ATR harmony / lengthening) with no affix to strip: aduanɛ ~ aduane
    for v in _surface_variants(word.lower()):
        if v != word.lower() and bank.is_known(v)["known"]:
            return {"known": True, "how": "variant", "of": [v]}
    if pkey_index is not None:
        k = pkey(word)
        if k and k in pkey_index:
            return {"known": True, "how": "variant", "of": pkey_index[k][:3]}
    return {"known": False, "how": None}
