#!/usr/bin/env python3
"""Build the TTS bake-off eval set FROM THE BANK — the fixed sentences every candidate voice speaks.

The bank designs its own pronunciation test: pick short, bank-verified conversational sentences that
together exercise every tricky Twi phoneme/cluster (ɛ ɔ ŋ, the tw/dw/kw/ky/gy/hy/nw/ny clusters, long
vowels). Each candidate TTS (Orpheus / CosyVoice / Chatterbox / the mms-tts-aka baseline) synthesizes
this same set; the eval then scores naturalness (MOS predictors), intelligibility (ASR-WER relative to
the WAXAL real-audio floor — which cancels the ASR's own Twi weakness), and latency.

  python3 bank/eval/build_tts_eval.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import Bank  # noqa: E402

# phoneme/grapheme contrasts a Twi voice must get right (the test must exercise these)
TARGETS = ["ɛ", "ɔ", "ŋ", "ny", "tw", "dw", "kw", "ky", "gy", "hy", "nw", "aa", "ee", "ii", "oo", "uu", "ɛɛ", "ɔɔ", "'"]
TOK = re.compile(r"[a-zɛɔŋ']+", re.I)


def covers(s):
    sl = s.lower()
    return [t for t in TARGETS if t in sl]


def attest(bank, s):
    ws = [w.strip("'") for w in TOK.findall(s.lower()) if len(w.strip("'")) >= 2]
    return (sum(1 for w in ws if bank.is_known(w)["known"]) / len(ws) if ws else 0)


def main():
    bank = Bank()
    seen, pool = set(), []
    for p in bank.pairs:
        s = p["twi"].strip()
        if 2 <= len(s.split()) <= 9 and p.get("en") and attest(bank, s) >= 0.8 and s.lower() not in seen:
            seen.add(s.lower())
            pool.append((s, p["en"], p["source"]))

    # greedy phoneme coverage, then top up with short conversational lines
    need, chosen = set(TARGETS), []
    pool.sort(key=lambda x: -len(covers(x[0])))
    for s, en, src in pool:
        if set(covers(s)) & need:
            chosen.append((s, en, src))
            need -= set(covers(s))
        if not need:
            break
    for s, en, src in pool:
        if len(chosen) >= 28:
            break
        if all(s != c[0] for c in chosen) and 3 <= len(s.split()) <= 7:
            chosen.append((s, en, src))

    out = [{"sentence": s, "gloss": en, "phonemes": covers(s), "source": src} for s, en, src in chosen[:28]]
    p = Path(__file__).resolve().parent / "twi-tts-eval.jsonl"
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    covered = set(t for r in out for t in r["phonemes"])
    print(f"eval set: {len(out)} sentences -> {p.name} · phoneme coverage {len(covered)}/{len(TARGETS)}")


if __name__ == "__main__":
    main()
