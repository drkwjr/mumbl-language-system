#!/usr/bin/env python3
"""Verify a channel's Twi-purity properly — sample SEVERAL videos and look at the spread, not one clip.

A single sample lies: a mixed/multilingual channel can score high on one Twi video. So for each named
channel we find it, pull its recent uploads, transcribe a short clip from M of them, and report
min/mean/max purity. Consistently-high = genuinely Twi; high variance = mixed (e.g. Anansi Masters).

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/verify_channels.py "SVTV Africa" "Akomapa TV" --vids 4 --secs 50
"""
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import media_discover as md  # noqa: E402
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402

YTDLP = "/tmp/ytenv/bin/yt-dlp"
TWITOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)


def resolve(arg):
    """arg may be an exact @handle, a channel URL, a UC… channel-id, or (fallback) a search name.
    Prefer exact — fuzzy search resolves to the wrong channel (Khemical TV != KMTV)."""
    if arg.startswith("http"):
        url = arg.split("/videos")[0].rstrip("/")
    elif arg.startswith("@"):
        url = f"https://www.youtube.com/{arg}"
    elif arg.startswith("UC") and len(arg) > 20:
        url = f"https://www.youtube.com/channel/{arg}"
    else:
        cid = subprocess.run([YTDLP, f"ytsearch1:{arg}", "--flat-playlist", "--print", "%(channel_id)s"],
                             capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
        url = f"https://www.youtube.com/channel/{cid[0]}" if cid and cid[0] else None
    if not url:
        return None, arg
    name = subprocess.run([YTDLP, f"{url}/videos", "--flat-playlist", "--playlist-end", "1", "--print", "%(channel,uploader)s"],
                          capture_output=True, text=True, timeout=60).stdout.strip().splitlines()
    return url, (name[0] if name and name[0] not in ("NA", "") else arg.lstrip("@"))


def channel_videos(url, m):
    out = subprocess.run([YTDLP, f"{url}/videos", "--flat-playlist", "--playlist-end", str(m), "--print", "%(id)s"],
                         capture_output=True, text=True, timeout=90).stdout
    return out.split()


def purity(bank, text):
    c = {"T": 0, "E": 0, "u": 0}
    for tok in set(t.strip("'’") for t in TWITOK.findall(text.lower())):
        if len(tok) < 2:
            continue
        mem = lid.membership(tok, bank)
        c["T" if "aka" in mem else "E" if "eng" in mem else "u"] += 1
    tot = sum(c.values()) or 1
    return round(100 * c["T"] / tot)


def main():
    bank = Bank()
    vids = int(sys.argv[sys.argv.index("--vids") + 1]) if "--vids" in sys.argv else 4
    secs = int(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 50
    skip = {"--vids", str(vids), "--secs", str(secs)}
    names, a = [], sys.argv[1:]
    i = 0
    while i < len(a):
        if a[i] in ("--vids", "--secs"):
            i += 2
            continue
        names.append(a[i]); i += 1

    def sample(vid):
        mp3 = md.audio(vid, secs)
        if not mp3:
            return None
        try:
            return purity(bank, md.transcribe(mp3))
        except Exception:
            return None

    print(f"verifying {len(names)} channels, {vids} videos each ({secs}s)\n", flush=True)
    for name in names:
        url, cname = resolve(name)
        if not url:
            print(f"  {name}: not found"); continue
        vlist = channel_videos(url, vids)
        with ThreadPoolExecutor(max_workers=vids) as ex:
            scores = [s for s in ex.map(sample, vlist) if s is not None]
        if not scores:
            print(f"  {cname[:34]:34} no samples"); continue
        mn, mx = min(scores), max(scores)
        mean = round(sum(scores) / len(scores))
        verdict = "GENUINELY TWI" if mn >= 70 else ("MIXED" if mx - mn > 30 else "low/English")
        print(f"  {cname[:32]:32} mean {mean:3}%  (range {mn}-{mx}% over {len(scores)})  -> {verdict}", flush=True)
    cost = md.USAGE["in"] * 0.30 / 1e6 + md.USAGE["out"] * 2.50 / 1e6
    print(f"\nCOST: ~${cost:.4f}")


if __name__ == "__main__":
    main()
