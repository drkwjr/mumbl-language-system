#!/usr/bin/env python3
"""Channel discovery — find Asante Twi creators and rank them by Twi-purity.

Casts a wide net across content types (not just news — vlogs, podcasts, storytelling, comedy surface the
small, entirely-Twi creators that are gold for natural register), then for each channel samples a clip,
transcribes it, and scores membership purity. Flags channels with real (manual) captions — those skip ASR
entirely. Output: a ranked channel catalog to feed media_discover.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/discover_channels.py [--per 3] [--max 14] [--secs 60]
"""
import json
import re
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import media_discover as md  # reuse audio() + transcribe() + USAGE  # noqa: E402
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402

YTDLP = "/tmp/ytenv/bin/yt-dlp"
OUT = Path(__file__).resolve().parents[1] / "data" / "aka" / "channels.jsonl"
TWITOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)

QUERIES = [
    "Asante Twi vlog", "Twi podcast Ghana", "Twi storytelling Anansesem", "Asante Twi conversation full",
    "Twi comedy Ghana", "Twi motivation advice Akan", "Akan Twi interview", "Kumawood Twi movie scene",
]


def search_channels(per):
    chans = OrderedDict()  # channel_id -> {name, vid, views}
    for q in QUERIES:
        try:
            out = subprocess.run([YTDLP, f"ytsearch{per}:{q}", "--flat-playlist",
                                  "--print", "%(channel_id)s\t%(channel)s\t%(id)s\t%(view_count)s"],
                                 capture_output=True, text=True, timeout=90).stdout
        except Exception:
            continue
        for line in out.splitlines():
            p = line.split("\t")
            if len(p) >= 3 and p[0] and p[0] not in chans:
                chans[p[0]] = {"name": p[1], "vid": p[2], "views": p[3] if len(p) > 3 else "?"}
    return chans


def has_manual_subs(vid):
    try:
        out = subprocess.run([YTDLP, "--skip-download", "--list-subs", f"https://www.youtube.com/watch?v={vid}"],
                             capture_output=True, text=True, timeout=25).stdout
    except Exception:
        return False
    # the "Available subtitles" section = manual (auto-translate lives under "automatic captions")
    m = re.search(r"Available subtitles for .*?:(.*)", out, re.S)
    return bool(m and re.search(r"\b(ak|tw|en)\b", m.group(1)))


def purity(bank, text):
    c = {"Twi": 0, "English": 0, "unknown": 0}
    for tok in set(t.strip("'’") for t in TWITOK.findall(text.lower())):
        if len(tok) < 2:
            continue
        mem = lid.membership(tok, bank)
        c["Twi" if "aka" in mem else "English" if "eng" in mem else "unknown"] += 1
    tot = sum(c.values()) or 1
    return round(100 * c["Twi"] / tot), tot


def main():
    bank = Bank()
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 3
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 14
    secs = int(sys.argv[sys.argv.index("--secs") + 1]) if "--secs" in sys.argv else 60

    from concurrent.futures import ThreadPoolExecutor

    chans = search_channels(per)
    print(f"found {len(chans)} candidate channels; sampling up to {mx} ({secs}s each), parallel", flush=True)

    def process(item):
        cid, info = item
        mp3 = md.audio(info["vid"], secs)
        if not mp3:
            return None
        try:
            text = md.transcribe(mp3)
        except Exception:
            return None
        pct, ntok = purity(bank, text)
        return {"channel_id": cid, "name": info["name"], "twi_pct": pct, "tokens": ntok,
                "manual_subs": has_manual_subs(info["vid"]), "sample_vid": info["vid"], "views": info["views"]}

    rows = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(process, list(chans.items())[:mx]):
            if r:
                rows.append(r)
                print(f"  {r['name'][:30]:30} Twi {r['twi_pct']:3}%  {'[captions]' if r['manual_subs'] else ''}", flush=True)

    rows.sort(key=lambda r: -r["twi_pct"])
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    cost = md.USAGE["in"] * 0.30 / 1e6 + md.USAGE["out"] * 2.50 / 1e6
    print(f"\nRANKED Asante-Twi channels (by purity) -> {OUT}")
    for r in rows:
        print(f"  {r['twi_pct']:3}% Twi  {'📝' if r['manual_subs'] else '  '}  {r['name'][:38]}")
    print(f"\nCOST: ~${cost:.4f} (gemini-2.5-flash)")


if __name__ == "__main__":
    main()
