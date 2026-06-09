"""Language validity from the bank — the judgment the heuristic scorer can't make: is this real Twi?

Fuses the bank (the right half of the system) into the curator (the left half) so labeling isn't
blind to language. The bank's verifier is the spine of the `validity` dimension; the conversational
labels (dialogue / topic / register) add learner-value ON TOP of real target-language content,
instead of rescuing non-target text the way the old metadata-only heuristic did.

Lazily loads the bank and degrades gracefully (returns None) if it isn't available, so the curator
still runs standalone in the funnel.
"""

import re
import sys
from pathlib import Path

_WORD = re.compile(r"[a-zɛɔŋ'’-]+", re.I)
_bank = None
_tried = False


def _load():
    global _bank, _tried
    if _tried:
        return _bank
    _tried = True
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "bank"))
        from serve import Bank  # noqa: E402

        _bank = Bank()
    except Exception:
        _bank = None
    return _bank


class BankValidator:
    """Scores what fraction of a text's words are attested in the bank, and names the ones that aren't."""  # noqa: E501

    def available(self) -> bool:
        return _load() is not None

    def validity(self, text: str):
        """(pct of tokens attested in the bank, [unattested words]); None if the bank is absent."""
        bank = _load()
        if bank is None:
            return None
        toks = [t.strip("'’.,!?¿¡") for t in _WORD.findall(text.lower())]
        toks = [t for t in toks if len(t) >= 2]
        if not toks:
            return (0.0, [])
        unknown = [t for t in toks if not bank.is_known(t)["known"]]
        pct = 100.0 * (len(toks) - len(unknown)) / len(toks)
        return (pct, sorted(set(unknown)))
