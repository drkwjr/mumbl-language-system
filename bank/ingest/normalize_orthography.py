#!/usr/bin/env python3
"""Normalize a reduced Twi orthography (e/o, as Rattray prints) to modern Akan (ɛ/ɔ).

Rattray 1930 omits ɛ/ɔ; our bank is modern. This restores them by matching each token's reduced form
against modern words that DO carry ɛ/ɔ. Unambiguous matches are restored; ambiguous (e.g. se -> se|sɛ)
and unknown tokens are left as-is and counted. Coverage is bounded by how much modern-orthography
vocabulary we have — so it rises as we ingest more (Christaller's 1881 dictionary is the big lever).

  /tmp/ytenv/bin/python bank/ingest/normalize_orthography.py "Kwaku Ananse na okoo Nyankonpon ho se"
  /tmp/ytenv/bin/python bank/ingest/normalize_orthography.py --corpus   # normalize the folk-tales corpus
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "aka"
CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "aka-asante" / "rattray-folktales.jsonl"
WORD = re.compile(r"[A-Za-zɛɔŋ'’-]+")


ENG_STOP = set("the and he she they was were said that with from you have this our had not".split())


def reduced(w):
    return w.lower().replace("ɛ", "e").replace("ɔ", "o").replace("-", "")


def _is_english(line):
    toks = re.findall(r"[a-z']+", line.lower())
    return bool(toks) and sum(t in ENG_STOP for t in toks) / len(toks) > 0.2


def extract_twi(text):
    """Pull the Twi out of a vision-OCR page using its [TWI]/[ENG] section labels (reliable);
    if a page has no labels, fall back to dropping English-looking lines."""
    lines = text.splitlines()
    labeled = any(l.strip() in ("[TWI]", "[ENG]") for l in lines)
    mode, out = None, []
    for ln in lines:
        s = ln.strip()
        if s in ("[TWI]", "[ENG]"):
            mode = s
            continue
        if labeled:
            if mode == "[TWI]":
                out.append(ln)
        elif s and not _is_english(ln):
            out.append(ln)
    return "\n".join(out).strip()


def build_map():
    """reduced-form -> set of modern forms that carry ɛ/ɔ (built from the modern lexicon, the Christaller
    dictionary, and phrases)."""
    m = defaultdict(set)
    for fn in ("lexicon.jsonl", "lexicon-christaller.jsonl", "phrases.jsonl"):
        p = DATA / fn
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            forms = [r["lemma"]] if "lemma" in r else re.findall(r"[A-Za-zɛɔŋ'’]+", r.get("text_aka", ""))
            for w in forms:
                w = w.replace("-", "")
                if any(c in w for c in "ɛɔ"):
                    m[reduced(w)].add(w.lower())
    return m


def normalize(text, m):
    stats = Counter()

    def repl(mt):
        tok = mt.group(0)
        cands = m.get(reduced(tok))
        if not cands:
            stats["unmatched"] += 1
            return tok
        if len(cands) == 1:
            stats["restored"] += 1
            modern = next(iter(cands))
            return modern.capitalize() if tok[:1].isupper() else modern
        stats["ambiguous"] += 1
        return tok

    return WORD.sub(repl, text), stats


def main():
    m = build_map()
    print(f"(normalization map: {len(m)} reduced->modern keys from the modern lexicon)\n", file=sys.stderr)
    if "--corpus" in sys.argv:
        if not CORPUS.exists():
            raise SystemExit("no corpus yet — run rattray_folktales.py first")
        out = CORPUS.with_name("rattray-folktales.normalized.jsonl")
        total = Counter()
        with out.open("w", encoding="utf-8") as f:
            for line in CORPUS.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                twi = extract_twi(rec.get("text", ""))  # re-extract cleanly from raw OCR by label
                if not twi:
                    continue  # English-only page (detection false positive) — skip
                norm, st = normalize(twi, m)
                total.update(st)
                rec["twi"] = twi
                rec["twi_modern"] = norm
                rec["norm_stats"] = dict(st)
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tot = sum(total.values()) or 1
        print(f"normalized corpus -> {out}")
        print(f"  restored {total['restored']} ({100*total['restored']//tot}%) · ambiguous {total['ambiguous']} · unmatched {total['unmatched']}")
    else:
        text = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
        norm, st = normalize(text, m)
        print("reduced :", text)
        print("modern  :", norm)
        print("stats   :", dict(st))


if __name__ == "__main__":
    main()
