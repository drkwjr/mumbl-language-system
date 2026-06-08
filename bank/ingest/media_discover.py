#!/usr/bin/env python3
"""Media discovery — the self-growing engine on spoken Twi. Pull N clips from a YouTube search, transcribe
Asante Twi with Gemini, and aggregate unknown words by DOCUMENT FREQUENCY across clips. Corroboration is
the filter: a real word recurs across clips; an ASR mis-hearing or proper noun appears once. Cheap
(~$0.002/min). Verify-not-trust: corroborated words are staged with a gloss, never auto-added.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/media_discover.py "GhanaWeb news Twi Asemsebe" --clips 6 --secs 120
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402
import morphophon as mp  # noqa: E402

YTDLP = "/tmp/ytenv/bin/yt-dlp"
CACHE = Path(__file__).resolve().parents[1] / "corpus" / "aka-asante" / "_media"
TWITOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)
USAGE = {"in": 0, "out": 0}


def search_ids(query, n):
    out = subprocess.run([YTDLP, f"ytsearch{n}:{query}", "--flat-playlist", "--print", "%(id)s"],
                         capture_output=True, text=True, timeout=120).stdout.split()
    return out[:n]


def audio(vid, secs):
    f = CACHE / f"{vid}.mp3"
    if not f.exists():
        subprocess.run([YTDLP, "-x", "--audio-format", "mp3", "--audio-quality", "5",
                        "--download-sections", f"*0-{secs}", "-o", str(CACHE / f"{vid}.%(ext)s"),
                        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, timeout=300)
    return f if f.exists() else None


def transcribe(mp3):
    txt = mp3.with_suffix(".twi.txt")
    if txt.exists():
        return txt.read_text(encoding="utf-8")
    key = os.environ["GEMINI_API_KEY"]
    b64 = base64.b64encode(mp3.read_bytes()).decode()
    p = "This is spoken Asante Twi news. Transcribe the Twi verbatim, preserving ɛ ɔ ŋ. Output only the Twi."
    body = json.dumps({"contents": [{"parts": [{"text": p}, {"inline_data": {"mime_type": "audio/mp3", "data": b64}}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 3000}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=180).read())
    t = r["candidates"][0]["content"]["parts"][0]["text"]
    u = r.get("usageMetadata", {})
    USAGE["in"] += u.get("promptTokenCount", 0)
    USAGE["out"] += u.get("candidatesTokenCount", 0)
    txt.write_text(t, encoding="utf-8")
    return t


def gloss(words):
    if not words:
        return {}
    key = os.environ["GEMINI_API_KEY"]
    p = ('Give a short English meaning for each Asante Twi word. Use "?" if unsure. '
         'JSON {"word":"meaning"} only.\n' + "\n".join(words))
    body = json.dumps({"contents": [{"parts": [{"text": p}]}],
                       "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=60).read())
        return json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
    except Exception:
        return {}


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    query = sys.argv[1]
    clips = int(sys.argv[sys.argv.index("--clips") + 1]) if "--clips" in sys.argv else 6
    secs = int(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 120
    bank = Bank()

    ids = search_ids(query, clips)
    print(f"clips: {len(ids)}  ({secs}s each)")
    df = defaultdict(set)   # unknown word -> set of clip ids (document frequency = corroboration)
    purity = Counter()
    for i, vid in enumerate(ids, 1):
        mp3 = audio(vid, secs)
        if not mp3:
            print(f"  [{i}/{len(ids)}] {vid}: download failed")
            continue
        text = transcribe(mp3)
        for tok in set(t.strip("'’") for t in TWITOK.findall(text.lower())):
            if len(tok) < 2:
                continue
            m = lid.membership(tok, bank)
            if "aka" in m:
                purity["Twi"] += 1
            elif "eng" in m:
                purity["English"] += 1
            else:
                purity["unknown"] += 1
            if not mp.is_known_morph(bank, tok, bank.pkey_index)["known"] and not ("eng" in m and "aka" not in m):
                df[tok].add(vid)
        print(f"  [{i}/{len(ids)}] {vid}: {len(text)} chars")

    corroborated = sorted(((w, len(c)) for w, c in df.items() if len(c) >= 2), key=lambda x: -x[1])
    oneoff = [w for w, c in df.items() if len(c) == 1]
    glosses = gloss([w for w, _ in corroborated[:20]])

    tot = sum(purity.values()) or 1
    print(f"\nPURITY across {len(ids)} clips: Twi {100*purity['Twi']//tot}% · English {100*purity['English']//tot}% · unknown {100*purity['unknown']//tot}%")
    print(f"\nCORROBORATED unknowns (in >=2 clips -> likely real): {len(corroborated)}   |   one-offs (likely noise): {len(oneoff)}")
    for w, n in corroborated[:18]:
        g = glosses.get(w)
        print(f"  {w:14} in {n} clips   {'~ ' + g if g and g != '?' else ''}")
    cost = USAGE["in"] * 0.30 / 1e6 + USAGE["out"] * 2.50 / 1e6
    print(f"\nCOST: in={USAGE['in']:,} out={USAGE['out']:,} tokens · ~${cost:.4f} (gemini-2.5-flash; rates drift)")


if __name__ == "__main__":
    main()
