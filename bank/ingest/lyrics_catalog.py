#!/usr/bin/env python3
"""The full lyric haul — batched. Run harvest_lyrics.js once (one warm browser crawls + renders the
whole 54-artist catalog), then capture the Twi keeping ATTESTATION and MEANING separate:
  - ATTESTATION: language_id + morphology = real, genuinely-new Twi.
  - MEANING: SOURCED from the bank (self/root gloss) or marked UNKNOWN. Unknowns go to
    lyric-unknowns.jsonl WITH line context (artist/song/line) for native review / dictionary lookup.
    Never a model guess as truth — no LLM in the loop.

  python3 bank/ingest/lyrics_catalog.py [--per-artist 6] [--max-artists 54]
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ING = Path(__file__).resolve().parent
sys.path.insert(0, str(ING.parents[0]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402
import morphophon as mp  # noqa: E402
import lyrics_ingest as L  # noqa: E402  reuse norm + TOK

DATA = ING.parents[0] / "data" / "aka"
STAGED = DATA / "discovered.jsonl"
UNKNOWNS = DATA / "lyric-unknowns.jsonl"
NODE_PATH = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()


def sourced_meaning(bank, word):
    """A SOURCED gloss for the word or its morphological root — or None (then meaning is unknown)."""
    g = bank.gloss(word)
    if g:
        return g
    d = mp.decompose(word, lambda w: bank.is_known(w)["known"])
    return bank.gloss(d[0]) if d else None


def main():
    bank = Bank()
    per = sys.argv[sys.argv.index("--per-artist") + 1] if "--per-artist" in sys.argv else "6"
    mx = sys.argv[sys.argv.index("--max-artists") + 1] if "--max-artists" in sys.argv else "54"

    # one warm browser does the whole catalog (crawl + render)
    lyr = Path(tempfile.gettempdir()) / "lyric_haul.jsonl"
    print(f"harvesting lyrics (batched, one browser) -> {lyr.name} ...", flush=True)
    subprocess.run(["node", str(ING / "harvest_lyrics.js"), str(DATA / "twi-artists.jsonl"), str(lyr), per, mx],
                   env={**os.environ, "NODE_PATH": NODE_PATH}, timeout=3600)
    if not lyr.exists():
        print("no lyrics harvested"); return

    have = {json.loads(line)["word"] for line in (STAGED.read_text(encoding="utf-8").splitlines() if STAGED.exists() else []) if line.strip()}
    seen_unknown = set()
    songs = staged = sourced = unknown = 0
    with STAGED.open("a", encoding="utf-8") as sf, UNKNOWNS.open("a", encoding="utf-8") as uf:
        for raw_line in lyr.read_text(encoding="utf-8").splitlines():
            if not raw_line.strip():
                continue
            song = json.loads(raw_line)
            songs += 1
            for line in song["text"].splitlines():
                for raw in L.TOK.findall(L.norm(line).lower()):
                    tok = raw.strip("'’")
                    if len(tok) < 2 or "aka" not in lid.membership(tok, bank):
                        continue
                    if mp.is_known_morph(bank, tok, bank.pkey_index)["known"] or tok in have:
                        continue
                    have.add(tok)
                    meaning = sourced_meaning(bank, tok)
                    sf.write(json.dumps({"word": tok, "freq": 1, "gloss_proposed": meaning,
                                         "gloss_status": "sourced" if meaning else "unknown",
                                         "method": "lyric", "verification": "unverified",
                                         "use": "staged-for-review"}, ensure_ascii=False) + "\n")
                    staged += 1
                    if meaning:
                        sourced += 1
                    elif tok not in seen_unknown:
                        seen_unknown.add(tok)
                        uf.write(json.dumps({"word": tok, "artist": song["artist"], "song": song["url"].split("/")[-1],
                                             "context": line[:120], "status": "meaning-unknown"}, ensure_ascii=False) + "\n")
                        unknown += 1

    print(f"\n{songs} songs · {staged} new Twi words · {sourced} meaning-sourced · {unknown} meaning-UNKNOWN (-> {UNKNOWNS.name})")


if __name__ == "__main__":
    main()
