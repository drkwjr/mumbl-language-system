#!/usr/bin/env python3
"""Mine HOW Twi actually builds sentences — the syntax/construction layer, not the vocabulary.

The bank knows words + phrases, but generation can still calque English word order. This learns the
real Twi chunks from everything we've ingested (curated phrase pairs + conversational guides + lyric
lines + media transcripts): the frequent ATTESTED n-grams (the natural multi-word building blocks),
the sentence-opening and -closing frames, and the workhorse function words. Generation grounds on
these so it chains words the Twi way — "Me pɛ sɛ..." not a word-for-word English mapping.

Output: bank/data/aka/constructions.jsonl (ranked chunks) + a printed "how they talk" summary.

  python3 bank/ingest/construction_miner.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ING = Path(__file__).resolve().parent
sys.path.insert(0, str(ING.parents[0]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402
import morphophon as mp  # noqa: E402

DATA = ING.parents[0] / "data" / "aka"
MEDIA = ING.parents[0] / "corpus" / "aka-asante" / "_media"
OUT = DATA / "constructions.jsonl"
WORD = re.compile(r"[a-zɛɔŋ'’]+", re.I)
# Twi grammatical function words — the glue whose PLACEMENT is the syntax (focus na, complementiser sɛ,
# clausal a, the postposed definite no, relativiser deɛ, the negative/serial connectors).
FUNCTION = {"na", "sɛ", "a", "no", "deɛ", "nti", "ne", "wɔ", "mu", "so", "ho", "ma", "ara", "koraa", "bi", "yi", "saa"}


def sentences():
    """Every Twi sentence/line we have, from curated -> colloquial -> spoken."""
    bank = Bank()
    out = []
    for p in bank.pairs:  # curated phrase pairs (wikivoyage/fsi/learnakan/dictionaries)
        if p.get("twi"):
            out.append(p["twi"])
    haul = Path("/tmp/claude-501/lyric_haul.jsonl")  # lyric lines (colloquial)
    if haul.exists():
        for line in haul.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out += json.loads(line)["text"].splitlines()
    for f in MEDIA.glob("*.twi.txt"):  # media transcripts (spoken)
        out += f.read_text(encoding="utf-8").splitlines()
    return bank, out


def main():
    bank, lines = sentences()
    lines = list(dict.fromkeys(l.strip() for l in lines if l.strip()))  # dedup (songs/transcripts repeat)
    print(f"corpus: {len(lines):,} unique Twi lines\n", flush=True)

    grams = {2: Counter(), 3: Counter()}
    cls_grams = Counter()  # class-bigrams (f:<func> / C / U) — the dense backoff for the smoothed metric
    opens, closes = Counter(), Counter()
    func = Counter()
    cls_cache = {}

    def wclass(t):
        """Grammatical class of a kept token: each function word is its OWN class (its placement IS the
        syntax), known content -> C, name/unknown -> U. Class bigrams are dense, so they credit a
        grammatical-but-unseen pair while still rejecting misplaced glue."""
        if t in FUNCTION:
            return "f:" + t
        return "C" if classify(t) == "twi" else "U"

    def classify(t):
        """twi (real Twi, INCLUDING words that also exist in English: wo/me/ho/de) · eng (English-ONLY:
        the/of/ghana) · other (names/unknowns). The Twi grammatical core collides with English, so we
        must NOT drop it per-token — we gate Twi-ness at the line level instead."""
        if t not in cls_cache:
            m = lid.membership(t, bank)
            if "aka" in m:
                cls_cache[t] = "twi"
            elif "eng" in m:
                cls_cache[t] = "eng"
            else:
                cls_cache[t] = "other"
        return cls_cache[t]

    for line in lines:
        raw = [t.strip("'’").lower() for t in WORD.findall(line) if len(t.strip("'’")) >= 2]
        tags = [classify(t) for t in raw]
        ntwi, neng = tags.count("twi"), tags.count("eng")
        if ntwi < 2 or ntwi <= neng:
            continue  # line-level gate: keep only Twi-dominant lines (drops English/nav lines wholesale)
        toks = [t for t, g in zip(raw, tags) if g != "eng"]  # keep Twi + names/unknowns; drop English-only
        if len(toks) < 2:
            continue
        for w in toks:
            if w in FUNCTION:
                func[w] += 1
        wc = [wclass(w) for w in toks]
        for i in range(len(toks) - 1):
            cls_grams[f"{wc[i]} {wc[i + 1]}"] += 1
        for n in (2, 3):
            for i in range(len(toks) - n + 1):
                gram = toks[i:i + n]
                if len(set(gram)) < n:
                    continue  # skip adjacent repeats (kɔ kɔ — song/ASR artifacts)
                grams[n][" ".join(gram)] += 1
        opens[" ".join(toks[:2])] += 1
        closes[" ".join(toks[-2:])] += 1

    # the dense class-bigram backoff: which grammatical-class transitions actually occur in Twi
    cls_rows = [{"pair": p, "freq": c} for p, c in cls_grams.most_common() if c >= 3]
    (DATA / "class_bigrams.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in cls_rows) + "\n", encoding="utf-8")

    # Export ALL attested bigrams (freq>=2) for the structural-naturalness check, plus the top trigrams.
    # The full bigram set makes "is this assembled like Twi" meaningful; the top entries (file is freq-
    # sorted) are what generation grounds on.
    rows = []
    for n in (2, 3):
        thresh, cap = (2, None) if n == 2 else (3, 250)
        for chunk, c in grams[n].most_common(cap):
            if c < thresh:
                continue
            rev = " ".join(reversed(chunk.split()))  # X Y and Y X both high = a repeated song line
            if grams[n].get(rev, 0) >= 0.7 * c:
                continue
            rows.append({"chunk": chunk, "n": n, "freq": c})
    rows.sort(key=lambda r: -r["freq"])
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    print(f"=== HOW TWI TALKS — mined from {len(lines):,} lines -> {OUT.name} ({len(rows)} constructions) ===\n")
    print("top building-block bigrams (the natural chunks):")
    for chunk, c in grams[2].most_common(16):
        print(f"   {chunk:22} {c}")
    print("\ntop sentence OPENINGS (how a Twi sentence starts):")
    for chunk, c in opens.most_common(10):
        print(f"   {chunk:22} {c}")
    print("\ntop sentence CLOSINGS:")
    for chunk, c in closes.most_common(8):
        print(f"   {chunk:22} {c}")
    print("\nworkhorse function words (the glue whose placement IS the grammar):")
    for w, c in func.most_common(12):
        print(f"   {w:8} {c}")


if __name__ == "__main__":
    main()
