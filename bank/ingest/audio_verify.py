#!/usr/bin/env python3
"""Verify the audio<->text pairing: does each track actually SPEAK the text we paired it with?

Sample tracks from the audio-corpus manifest, ASR the audio (Gemini), and measure how much of the
section's expected Twi appears in the transcript. High overlap = the pairing is real; low = a mis-key
to chase. Verify-not-trust, applied to the audio layer. Cheap (~$0.001/min); transcripts cached.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/audio_verify.py [--n 8]
"""
import base64
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "aka" / "_restricted" / "audio-corpus.jsonl"
AUDIO = ROOT / "sources" / "learnakan"
TOK = re.compile(r"[a-zɛɔŋ']+", re.I)
USAGE = {"in": 0, "out": 0}


def toks(text):
    return {t.strip("'") for t in TOK.findall(text.lower()) if len(t.strip("'")) >= 2}


def asr(mp3):
    cache = mp3.with_suffix(".asr.txt")
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    key = os.environ["GEMINI_API_KEY"]
    b64 = base64.b64encode(mp3.read_bytes()).decode()
    p = "This is a studio recording from a Twi (Akan) phrasebook. Transcribe ALL the Twi spoken, preserving ɛ ɔ ŋ. Output only the Twi."
    body = json.dumps({"contents": [{"parts": [{"text": p}, {"inline_data": {"mime_type": "audio/mp3", "data": b64}}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 4000}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=180).read())
    cands = r.get("candidates", [])
    parts = cands[0].get("content", {}).get("parts") if cands else None
    t = parts[0].get("text", "") if parts else ""
    u = r.get("usageMetadata", {})
    USAGE["in"] += u.get("promptTokenCount", 0); USAGE["out"] += u.get("candidatesTokenCount", 0)
    cache.write_text(t, encoding="utf-8")
    return t


def main():
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 8
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    present = [r for r in rows if r.get("audio_exists") and r.get("phrases")]
    # spread the sample across both corpora and the track range (deterministic stride, no RNG)
    stride = max(1, len(present) // n)
    sample = present[::stride][:n]
    print(f"verifying {len(sample)} of {len(present)} paired tracks\n", flush=True)

    overlaps = []
    for r in sample:
        mp3 = AUDIO / r["audio_path"]
        expected = set()
        for ph in r["phrases"]:
            expected |= toks(ph["twi"])
        if not expected:
            continue
        heard = toks(asr(mp3))
        hit = expected & heard
        ov = round(100 * len(hit) / len(expected))
        overlaps.append(ov)
        print(f"  track {r['track']:>2} [{r['corpus'][:6]}] {r['section'][:34]:34} expected {len(expected):>3} Twi words · audio matches {ov:>3}%", flush=True)

    avg = round(sum(overlaps) / len(overlaps)) if overlaps else 0
    cost = USAGE["in"] * 0.30 / 1e6 + USAGE["out"] * 2.50 / 1e6
    print(f"\nMEAN overlap (expected Twi heard in the audio): {avg}%  ·  ~${cost:.4f}")
    print("high overlap => the pairing is real; the audio speaks the paired text.")


if __name__ == "__main__":
    main()
