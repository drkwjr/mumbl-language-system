#!/usr/bin/env python3
"""Wide channel discovery — cast a BIG net for Akan-speaking YouTube channels, cheaply.

Decoupled from verification on purpose: this only reads YouTube SEARCH METADATA (channel id + name +
one sample video), never downloads or transcribes. That sidesteps the per-IP download throttle, so one
run can surface hundreds of channels for a few seconds of search calls. Purity scoring happens later at
harvest time (verify_channels / harvest.py do it through the proxy).

The query bank is dialect x genre: every Akan dialect (Asante, Akuapem, Fante, Bono/Brong, Kwawu) crossed
with the genres where natural speech lives (vlog, podcast, interview, sermon, drama, storytelling, radio
call-ins, cooking, football commentary...). The dialect a query targets is recorded as a weak hint on
each channel it surfaces — refined later by dialect_tag.py against the actual transcript.

Merges (dedup by channel_id) into channels.jsonl — the candidate pool harvest.py reads.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/discover_wide.py [--per 8]
"""
import json
import subprocess
import sys
from collections import OrderedDict
from pathlib import Path

YTDLP = "/tmp/ytenv/bin/yt-dlp"
POOL = Path(__file__).resolve().parents[1] / "data" / "aka" / "channels.jsonl"

# Each Akan dialect, with the search terms that bias toward it. Asante is the default/largest; the others
# are where dialect discernment gets interesting. "Akan" stays dialect-neutral.
DIALECTS = {
    "asante": ["Asante Twi", "Kumasi Twi", "Ashanti Twi"],
    "akuapem": ["Akuapem Twi", "Akwapim Twi"],
    "fante": ["Fante", "Mfantse", "Cape Coast Fante"],
    "bono": ["Bono Twi", "Brong Twi", "Sunyani"],
    "kwawu": ["Kwawu Twi", "Kwahu Twi"],
    "akan": ["Akan", "Twi Ghana"],
}
# Genres where natural, conversational speech lives (not just news read from a script).
GENRES = [
    "vlog", "podcast full episode", "interview", "kasa nkɔmmɔ conversation", "storytelling Anansesem",
    "comedy skit", "Kumawood movie", "drama series", "sermon preaching", "gospel testimony",
    "radio call-in show", "market street interview", "cooking recipe", "football commentary",
    "history proverbs", "motivation advice", "news Asemsebe", "documentary", "vox pop",
]


def search_channels(query, per):
    """Channel id + name + one sample video from search metadata only — no download."""
    try:
        out = subprocess.run(
            [YTDLP, f"ytsearch{per}:{query}", "--flat-playlist",
             "--print", "%(channel_id)s\t%(channel)s\t%(id)s\t%(view_count)s"],
            capture_output=True, text=True, timeout=90).stdout
    except Exception:
        return []
    rows = []
    for line in out.splitlines():
        p = line.split("\t")
        if len(p) >= 3 and p[0]:
            rows.append({"channel_id": p[0], "name": p[1], "sample_vid": p[2],
                         "views": p[3] if len(p) > 3 else "?"})
    return rows


def load_pool():
    if not POOL.exists():
        return OrderedDict()
    pool = OrderedDict()
    for line in POOL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            cid = r.get("channel_id")
            if cid:
                pool[cid] = r
    return pool


def main():
    per = int(sys.argv[sys.argv.index("--per") + 1]) if "--per" in sys.argv else 8
    pool = load_pool()
    before = len(pool)
    queries = [(d, f"{term} {g}") for d, terms in DIALECTS.items() for term in terms for g in GENRES]
    print(f"pool: {before} channels · sweeping {len(queries)} dialect×genre queries (×{per} results)\n", flush=True)

    new = 0
    by_dialect = {d: 0 for d in DIALECTS}
    for i, (dialect, q) in enumerate(queries, 1):
        for r in search_channels(q, per):
            cid = r["channel_id"]
            if cid in pool:
                pool[cid].setdefault("dialect_hints", [])
                if dialect not in pool[cid]["dialect_hints"]:
                    pool[cid]["dialect_hints"].append(dialect)  # surfaced by another dialect's query too
                continue
            r["dialect_hints"] = [dialect]
            r["src"] = q
            pool[cid] = r
            new += 1
            by_dialect[dialect] += 1
        if i % 20 == 0:
            print(f"  [{i}/{len(queries)}] pool now {len(pool)} (+{new} new)", flush=True)

    POOL.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in pool.values()) + "\n", encoding="utf-8")
    print(f"\nDISCOVERED +{new} new channels -> pool {before} -> {len(pool)}  ({POOL.name})")
    print("new by dialect-hint: " + " · ".join(f"{d} {n}" for d, n in by_dialect.items() if n))
    print("(hints are weak priors from the surfacing query; dialect_tag.py refines against transcripts)")


if __name__ == "__main__":
    main()
