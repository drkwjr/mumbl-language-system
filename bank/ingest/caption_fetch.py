#!/usr/bin/env python3
"""Captions-first fetch — pull Akan caption tracks where they exist: free, accurate, no audio, no ASR.

Tier 1 of the YouTube-fetch plan. For channels that caption in Akan (a minority — mostly educational/news),
yt-dlp can download the subtitle track with --skip-download: no audio bandwidth, no Gemini call, and the
text is human-authored (higher trust than ASR). We prioritize channels discovery already flagged as having
manual captions. Routes through HARVEST_PROXY (caption endpoints are bot-walled on datacenter IPs too).

Output: _media/<vid>.cap.txt (caption-sourced text, kept distinct from .twi.txt ASR so trust is traceable)
+ a yield report. Akan-caption yield is expected to be low; this harvests the gold where it exists and
confirms where it doesn't.

  set -a; source /tmp/harvest_proxy.env; set +a
  python3 bank/ingest/caption_fetch.py [--per 6] [--max-channels 50] [--manual-only]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ING = Path(__file__).resolve().parent
DATA = ING.parents[0] / "data" / "aka"
MEDIA = ING.parents[0] / "corpus" / "aka-asante" / "_media"
POOL = DATA / "channels.jsonl"
YTDLP = "/tmp/ytenv/bin/yt-dlp"
SUB_LANGS = "ak,tw,aka"  # Akan/Twi caption tracks; skip English (we want the language, not a translation)


def proxy_args():
    p = os.environ.get("HARVEST_PROXY", "").strip()
    return ["--proxy", p] if p else []


def channel_videos(cid, n):
    base = f"https://www.youtube.com/channel/{cid}" if cid.startswith("UC") else f"https://www.youtube.com/{cid}"
    try:
        out = subprocess.run([YTDLP, f"{base}/videos", "--flat-playlist", "--playlist-end", str(n),
                              "--print", "%(id)s"] + proxy_args(), capture_output=True, text=True, timeout=120).stdout
        return out.split()[:n]
    except Exception:
        return []


def vtt_to_text(vtt):
    """Strip WEBVTT timestamps/markup -> deduped plain lines."""
    lines, seen = [], set()
    for ln in vtt.splitlines():
        ln = ln.strip()
        if not ln or ln == "WEBVTT" or "-->" in ln or ln.isdigit() or ln.startswith(("Kind:", "Language:", "NOTE")):
            continue
        ln = re.sub(r"<[^>]+>", "", ln)  # inline timing tags
        if ln and ln not in seen:
            seen.add(ln)
            lines.append(ln)
    return "\n".join(lines)


def fetch_caption(vid):
    """Try to pull an Akan caption track for one video. Returns text or None."""
    out = MEDIA / f"{vid}.cap.txt"
    if out.exists():
        return "cached"
    tmp = MEDIA / f"_cap_{vid}"
    subprocess.run([YTDLP, "--skip-download", "--write-subs", "--write-auto-subs",
                    "--sub-langs", SUB_LANGS, "--sub-format", "vtt",
                    "-o", str(tmp), f"https://www.youtube.com/watch?v={vid}"] + proxy_args(),
                   capture_output=True, timeout=90)
    vtts = list(MEDIA.glob(f"_cap_{vid}*.vtt"))
    if not vtts:
        return None
    text = vtt_to_text(vtts[0].read_text(encoding="utf-8", errors="ignore"))
    for v in vtts:
        v.unlink(missing_ok=True)
    if len(text) < 40:
        return None
    out.write_text(text, encoding="utf-8")
    return text


def main():
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 6
    mx = int(sys.argv[sys.argv.index("--max-channels") + 1]) if "--max-channels" in sys.argv else 60
    manual_only = "--manual-only" in sys.argv
    if not os.environ.get("HARVEST_PROXY"):
        print("warning: HARVEST_PROXY not set — caption endpoints are bot-walled on datacenter/raw IPs")

    chans = []
    for line in POOL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if manual_only and not r.get("manual_subs"):
                continue
            cid = r.get("channel_id")
            if cid:
                chans.append(cid)
    chans = chans[:mx]
    print(f"caption sweep: {len(chans)} channels × {per} videos, langs={SUB_LANGS}\n", flush=True)

    hits = vids = 0
    for i, cid in enumerate(chans, 1):
        for vid in channel_videos(cid, per):
            vids += 1
            r = fetch_caption(vid)
            if r:
                hits += 1
                if hits <= 12 and r != "cached":
                    print(f"  ✓ {vid}: {len(r.split())} words of Akan captions", flush=True)
        if i % 20 == 0:
            print(f"  [{i}/{len(chans)}] {hits} caption hits / {vids} videos", flush=True)

    print(f"\nCAPTION YIELD: {hits} Akan-caption tracks from {vids} videos ({100*hits//max(vids,1)}%)")
    print("low yield is expected (Akan captioning is rare); these are the free, accurate ones.")


if __name__ == "__main__":
    main()
