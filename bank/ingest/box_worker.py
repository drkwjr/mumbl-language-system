#!/usr/bin/env python3
"""Runs ON a Vultr worker box — download + ASR a shard of channels, write transcripts to ./out/.

Deliberately self-contained: needs only yt-dlp + ffmpeg on PATH and GEMINI_API_KEY in env. No bank, no
pip packages beyond yt-dlp. The orchestrator (fleet_harvest.py) ships this file + a shard.txt to each
box, runs it, and pulls back ./out/*.twi.txt. Audio is deleted after transcription to keep disk tiny —
only the (KB-sized) transcripts travel back.

  GEMINI_API_KEY=... WORKERS=6 PER_CHANNEL=8 CLIP_SECS=180 python3 box_worker.py
"""
import base64
import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

OUT = Path("out")
YTDLP = "yt-dlp"


def channel_videos(cid, n):
    base = f"https://www.youtube.com/channel/{cid}" if cid.startswith("UC") else f"https://www.youtube.com/{cid}"
    try:
        out = subprocess.run([YTDLP, f"{base}/videos", "--flat-playlist", "--playlist-end", str(n),
                              "--print", "%(id)s"], capture_output=True, text=True, timeout=120).stdout
        return out.split()[:n]
    except Exception:
        return []


def audio(vid, secs):
    f = OUT / f"{vid}.mp3"
    if not f.exists():
        subprocess.run([YTDLP, "-x", "--audio-format", "mp3", "--audio-quality", "5",
                        "--download-sections", f"*0-{secs}", "-o", str(OUT / f"{vid}.%(ext)s"),
                        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, timeout=300)
    return f if f.exists() else None


def transcribe(vid, mp3):
    txt = OUT / f"{vid}.twi.txt"
    if txt.exists():
        return
    key = os.environ["GEMINI_API_KEY"]
    b64 = base64.b64encode(mp3.read_bytes()).decode()
    p = "This is spoken Asante Twi. Transcribe the Twi verbatim, preserving ɛ ɔ ŋ. Output only the Twi."
    body = json.dumps({"contents": [{"parts": [{"text": p}, {"inline_data": {"mime_type": "audio/mp3", "data": b64}}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 3000}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=180).read())
        cands = r.get("candidates", [])
        parts = cands[0].get("content", {}).get("parts") if cands else None
        txt.write_text(parts[0].get("text", "") if parts else "", encoding="utf-8")
    except Exception:
        pass
    finally:
        mp3.unlink(missing_ok=True)  # free disk — only the transcript travels back


def main():
    OUT.mkdir(exist_ok=True)
    secs = int(os.environ.get("CLIP_SECS", "180"))
    per = int(os.environ.get("PER_CHANNEL", "8"))
    workers = int(os.environ.get("WORKERS", "6"))
    shard = [l.strip() for l in Path("shard.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"shard: {len(shard)} channels · {per}/ch × {secs}s · {workers} workers", flush=True)

    jobs = []
    for cid in shard:
        for vid in channel_videos(cid, per):
            if not (OUT / f"{vid}.twi.txt").exists():
                jobs.append(vid)
    print(f"queued {len(jobs)} fresh clips", flush=True)

    def pull(vid):
        m = audio(vid, secs)
        if m:
            transcribe(vid, m)
        return vid

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for _ in as_completed([ex.submit(pull, v) for v in jobs]):
            done += 1
            if done % 20 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)
    print(f"DONE {done} pulled -> {len(list(OUT.glob('*.twi.txt')))} transcripts", flush=True)


if __name__ == "__main__":
    main()
