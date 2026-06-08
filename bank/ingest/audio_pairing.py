#!/usr/bin/env python3
"""Pair the LearnAkan native audio to its text — the foundation of the audio layer.

Each guide is keyed to its audio: "SECTION TITLE – track N" maps 1:1 to Track N.mp3 (79 conversational
+ 45 vocab-companion = 124 native-recorded tracks). So segment each guide by its track markers, pull the
Twi<->English phrases per section (Gemini structured output), attach the audio file + its duration, and
emit a track-level manifest. That gives, per track: the audio, the phrases it speaks, and the meaning —
the raw material for pronunciation playback, forced alignment, and a Twi TTS trained on real native audio.

Restricted (copyrighted guide text + paid audio) -> _restricted/, gitignored. Verify-not-trust: a later
pass ASR-checks that each track actually speaks its section text (audio_verify.py).

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/audio_pairing.py
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BOOKS = Path(__file__).resolve().parents[1] / "corpus" / "aka-asante" / "_books"
AUDIO = Path(__file__).resolve().parents[1] / "sources" / "learnakan" / "audio"
OUT = Path(__file__).resolve().parents[1] / "data" / "aka" / "_restricted" / "audio-corpus.jsonl"
USAGE = {"in": 0, "out": 0, "lock": __import__("threading").Lock()}

# guide book name -> (audio subfolder, number of tracks)
CORPORA = {
    "learnakan-conversational": ("conversational", 79),
    "learnakan-vocab-companion": ("vocabulary-companion", 45),
}
SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "twi": {"type": "string"}, "english": {"type": "string"}}, "required": ["twi", "english"]}}


def sections(book):
    """Split a guide into (track_num, title, text) by its 'TITLE - track N' markers."""
    full = "\n".join(json.loads(l)["text"] for l in (BOOKS / f"{book}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    marks = list(re.finditer(r'([A-Z][^\n]{0,60}?)\s*[–\-]?\s*track\s*(\d+)\b', full, re.I))
    out = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(full)
        out.append((int(m.group(2)), m.group(1).strip(), full[start:end].strip()))
    # keep the first occurrence of each track number, in order
    seen, uniq = set(), []
    for n, title, text in out:
        if n not in seen:
            seen.add(n); uniq.append((n, title, text))
    return sorted(uniq)


def extract_pairs(text):
    key = os.environ["GEMINI_API_KEY"]
    prompt = ("Extract every Twi<->English phrase pair from this section of a Twi phrasebook. One row per "
              "pair (twi = the Twi word/phrase, english = its meaning). Keep register notes out of the twi "
              "field. Preserve ɛ ɔ ŋ exactly. Skip headers, 'track N', and English-only instructions.\n\n" + text)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    for t in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=90).read())
            cands = r.get("candidates", [])
            parts = cands[0].get("content", {}).get("parts") if cands else None
            u = r.get("usageMetadata", {})
            with USAGE["lock"]:
                USAGE["in"] += u.get("promptTokenCount", 0); USAGE["out"] += u.get("candidatesTokenCount", 0)
            return json.loads(parts[0]["text"]) if parts else []
        except Exception:
            __import__("time").sleep(2 * (t + 1))
    return []


def duration(path):
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                              "default=nw=1:nk=1", str(path)], capture_output=True, text=True, timeout=30).stdout.strip()
        return round(float(out), 1) if out else None
    except Exception:
        return None


def main():
    rows = []
    for book, (subdir, ntracks) in CORPORA.items():
        secs = sections(book)
        print(f"{book}: {len(secs)} sections (audio files: {ntracks})", flush=True)

        def build(item):
            n, title, text = item
            audio = AUDIO / subdir / f"Track {n}.mp3"
            pairs = [{"twi": p["twi"].strip(), "english": p["english"].strip()}
                     for p in extract_pairs(text) if p.get("twi") and p.get("english")]
            return {"track": n, "corpus": subdir, "section": title,
                    "audio_path": f"audio/{subdir}/Track {n}.mp3", "audio_exists": audio.exists(),
                    "duration_s": duration(audio), "n_phrases": len(pairs), "phrases": pairs}

        with ThreadPoolExecutor(max_workers=6) as ex:
            built = list(ex.map(build, secs))
        rows += built
        got = sum(1 for b in built if b["audio_exists"])
        secs_total = sum(b["duration_s"] or 0 for b in built)
        print(f"  {len(built)} tracks paired · {got} audio files present · {secs_total/60:.0f} min of audio · "
              f"{sum(b['n_phrases'] for b in built)} phrases", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in sorted(rows, key=lambda r: (r["corpus"], r["track"])):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cost = USAGE["in"] * 0.30 / 1e6 + USAGE["out"] * 2.50 / 1e6
    print(f"\n{len(rows)} tracks -> {OUT.name} · {sum(r['n_phrases'] for r in rows)} phrases · ~${cost:.4f}", flush=True)


if __name__ == "__main__":
    main()
