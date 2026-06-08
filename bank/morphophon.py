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
SUBJECTS = ["me", "wo", "ɔ", "ɛ", "yɛ", "mo", "wɔ", "o", "e", "mi", "wu", "mu"]
# TAM: progressive re-, future bɛ- (his 'be'), proximate-future rebɛ-, perfect a-, Fante neg-future kɔ-.
TAM = ["bɛ", "re", "a", "kɔ", "be", "ko"]

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


def decompose(word: str, is_known):
    """Strip subject (+TAM) prefixes; return (root, [affixes]) if the root is known, else None."""
    w = word.lower()
    fallback = None
    for s in SUBJECTS:
        if not w.startswith(s):
            continue
        r1 = w[len(s):]
        if r1 and is_known(r1):
            fallback = fallback or (r1, [s])
        for t in TAM:
            if not r1.startswith(t):
                continue
            r2 = r1[len(t):]
            if r2 and is_known(r2):
                return (r2, [s, t])  # subject + TAM is the strongest decomposition
    return fallback


def is_known_morph(bank, word: str, pkey_index=None) -> dict:
    """Verifier: a word is real if it is known directly, decomposes to a known root, or matches a
    known word by phoneme key."""
    if bank.is_known(word)["known"]:
        return {"known": True, "how": "direct"}
    d = decompose(word, lambda w: bank.is_known(w)["known"])
    if d:
        return {"known": True, "how": "morph", "root": d[0], "affixes": d[1]}
    if pkey_index is not None:
        k = pkey(word)
        if k and k in pkey_index:
            return {"known": True, "how": "variant", "of": pkey_index[k][:3]}
    return {"known": False, "how": None}
