#!/usr/bin/env python3
"""The full lyric haul — walk the 54-artist seed, crawl each artist's songs, ingest the Twi.

Wires crawl_artist.js (artist page -> song URLs) to the lyric ingestion, and — per the meaning
discipline — keeps the two axes separate:
  - ATTESTATION: language_id says the word is real Twi (+ it's genuinely new vs the morphology check).
  - MEANING: we do NOT guess. A captured word's meaning is sourced from the bank (self/root gloss) if
    possible; otherwise it goes to the UNKNOWN-MEANING queue (data/aka/lyric-unknowns.jsonl) WITH its
    line context, for native review / dictionary lookup. Never a model guess as truth.

  set -a; source ../mumbl-server/.env; set +a   # (not needed — no LLM; meanings are sourced or unknown)
  python3 bank/ingest/lyrics_catalog.py [--per-artist 6] [--max-artists 54]
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ING = Path(__file__).resolve().parent
sys.path.insert(0, str(ING.parents[0]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402
import morphophon as mp  # noqa: E402
import lyrics_ingest as L  # noqa: E402  reuse fetch_lyrics + norm + TOK + LABEL

DATA = ING.parents[0] / "data" / "aka"
STAGED = DATA / "discovered.jsonl"
UNKNOWNS = DATA / "lyric-unknowns.jsonl"  # the explicit "real Twi, meaning unknown" queue
NODE_PATH = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True).stdout.strip()


def slug(name):
    s = name.lower().replace("'", "").replace("(asakaa)", "").strip()
    return "".join(c if c.isalnum() or c == " " else "" for c in s).strip().replace(" ", "-")


def song_urls(artist, cap):
    url = f"https://afrikalyrics.com/artist/{slug(artist)}"
    r = subprocess.run(["node", str(ING / "crawl_artist.js"), url, str(cap)],
                       capture_output=True, text=True, timeout=120, env={**os.environ, "NODE_PATH": NODE_PATH})
    return [u for u in r.stdout.splitlines() if u.strip().startswith("http")]


def sourced_meaning(bank, word):
    """A SOURCED gloss for the word or its morphological root — or None (then it's unknown-meaning)."""
    g = bank.gloss(word)
    if g:
        return g
    d = mp.decompose(word, lambda w: bank.is_known(w)["known"])
    return bank.gloss(d[0]) if d else None


def main():
    bank = Bank()
    per = int(sys.argv[sys.argv.index("--per-artist") + 1]) if "--per-artist" in sys.argv else 6
    mx = int(sys.argv[sys.argv.index("--max-artists") + 1]) if "--max-artists" in sys.argv else 54
    artists = [json.loads(line) for line in (DATA / "twi-artists.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()][:mx]

    have = {json.loads(line)["word"] for line in (STAGED.read_text(encoding="utf-8").splitlines() if STAGED.exists() else []) if line.strip()}
    seen_unknown = set()
    staged = sourced = unknown = songs = 0
    uf = UNKNOWNS.open("a", encoding="utf-8")
    sf = STAGED.open("a", encoding="utf-8")

    for a in artists:
        urls = song_urls(a["name"], per)
        words_here = 0
        for url in urls:
            try:
                lines = L.fetch_lyrics(url)
            except Exception:
                continue
            songs += 1
            for line in lines:
                for raw in L.TOK.findall(L.norm(line).lower()):
                    tok = raw.strip("'’")
                    if len(tok) < 2 or "aka" not in lid.membership(tok, bank):
                        continue
                    if mp.is_known_morph(bank, tok, bank.pkey_index)["known"]:
                        continue  # already attested (incl. inflections)
                    meaning = sourced_meaning(bank, tok)
                    if tok not in have:
                        have.add(tok)
                        sf.write(json.dumps({"word": tok, "freq": 1, "gloss_proposed": meaning,
                                             "gloss_status": "sourced" if meaning else "unknown",
                                             "method": "lyric", "verification": "unverified",
                                             "use": "staged-for-review"}, ensure_ascii=False) + "\n")
                        staged += 1
                        words_here += 1
                        if meaning:
                            sourced += 1
                        elif tok not in seen_unknown:  # the explicit unknown-meaning queue, with context
                            seen_unknown.add(tok)
                            uf.write(json.dumps({"word": tok, "artist": a["name"], "song": url.split("/")[-1],
                                                 "context": line[:120], "status": "meaning-unknown"}, ensure_ascii=False) + "\n")
                            unknown += 1
        print(f"  {a['name'][:26]:26} {len(urls)} songs · {words_here} new Twi", flush=True)

    uf.close(); sf.close()
    print(f"\n{songs} songs · {staged} new Twi words staged · {sourced} meaning-sourced · {unknown} meaning-UNKNOWN (-> {UNKNOWNS.name})")


if __name__ == "__main__":
    main()
