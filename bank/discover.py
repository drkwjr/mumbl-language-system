#!/usr/bin/env python3
"""Vocabulary-discovery loop — the growth mechanism. Catch unknown words in any corpus, figure out what
they mean, stage them for the bank. Scales to any language that has a verifier + a corpus.

  CATCH   the verifier flags tokens the bank doesn't know (already excludes inflections that decompose).
  GLOSS   tiered, cheapest/most-trusted first:
            · morph-hint   — strips known affixes to surface a probable stem (sourced rule)
            · llm-propose  — a model proposes a meaning (Gemini Flash, cheap), tagged UNVERIFIED
          (a real run would also use bilingual alignment / native confirmation before promotion)
  STAGE   ranked candidates with method + verification tier -> discovered.jsonl. NOT auto-added to the
          bank; verify-not-trust, promote on review. This is how the concept map + lexicon grow.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/discover.py <corpus.txt | dir/> [--gloss N]   # propose glosses for the top N unknowns
"""
import json
import os
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "ingest"))
from serve import Bank  # noqa: E402
import morphophon as mp  # noqa: E402

TWITOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)
OUT = Path(__file__).resolve().parent / "data" / "aka" / "discovered.jsonl"
# bilingual corpora leak English; drop English homographs (keep ɛ/ɔ words always)
ENGLISH = set()
try:
    ENGLISH = {w.strip().lower() for w in open("/usr/share/dict/words", encoding="utf-8", errors="replace")}
except OSError:
    pass


def read_corpus(path):
    p = Path(path)
    files = sorted(p.rglob("*.txt")) if p.is_dir() else [p]
    return "\n".join(f.read_text(encoding="utf-8", errors="replace") for f in files)


def catch_unknowns(bank, text):
    """Tokens the bank can't verify (not known, don't decompose, no variant) — ranked by frequency."""
    unk = Counter()
    for tok in TWITOK.findall(text.lower()):
        tok = tok.strip("'’")
        twiish = any(c in tok for c in "ɛɔŋ")
        base = tok.split("'")[0]  # contractions/possessives: i'll, chief's
        is_eng = not twiish and (tok in ENGLISH or base in ENGLISH or tok.rstrip("s") in ENGLISH)
        if len(tok) < 2 or is_eng:  # drop English homographs/plurals in bilingual text
            continue
        if not mp.is_known_morph(bank, tok, bank.pkey_index)["known"]:
            unk[tok] += 1
    return unk


def morph_hint(bank, w):
    """Strip a known subject/TAM prefix to surface a probable stem, even if the stem isn't known yet."""
    for s in mp.SUBJECTS:
        if w.startswith(s) and len(w) > len(s) + 1:
            return {"prefix": s, "stem": w[len(s):]}
    return None


def gemini_gloss(words):
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not words:
        return {}
    prompt = ("For each Asante Twi word below, give a short English meaning. If you are not confident, "
              'use "?". Reply as JSON {"word": "meaning"} only.\n' + "\n".join(words))
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}).encode()
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=60).read())
        return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as e:
        print(f"  (gemini gloss failed: {str(e)[:80]})", file=sys.stderr)
        return {}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    n_gloss = int(sys.argv[sys.argv.index("--gloss") + 1]) if "--gloss" in sys.argv else 0
    bank = Bank()
    unk = catch_unknowns(bank, read_corpus(sys.argv[1]))
    top = unk.most_common()
    hinted = sum(1 for w, _ in top if morph_hint(bank, w))
    print(f"CAUGHT {len(unk)} unknown word-types ({sum(unk.values())} tokens) · {hinted} have a morph-hint")

    glosses = gemini_gloss([w for w, _ in top[:n_gloss]]) if n_gloss else {}
    cands = []
    for w, f in top:
        h = morph_hint(bank, w)
        g = glosses.get(w)
        cands.append({"word": w, "freq": f, "morph_hint": h,
                      "gloss_proposed": g if g and g != "?" else None,
                      "method": "llm-propose" if g and g != "?" else ("morph-hint" if h else "uncategorized"),
                      "verification": "unverified", "use": "staged-for-review"})
    OUT.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in cands) + "\n", encoding="utf-8")
    print(f"STAGED {len(cands)} candidates -> {OUT}  (review + promote; not auto-added)")
    print("\ntop unknowns" + (" with proposed gloss" if n_gloss else "") + ":")
    for c in cands[:14]:
        extra = f"  ~ {c['gloss_proposed']}" if c["gloss_proposed"] else (f"  (stem? {c['morph_hint']['stem']})" if c["morph_hint"] else "")
        print(f"  {c['word']:16} x{c['freq']:<3}{extra}")


if __name__ == "__main__":
    main()
