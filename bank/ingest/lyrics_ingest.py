#!/usr/bin/env python3
"""Song-lyric ingestion — the colloquial/slang register the dictionaries + courses lack.

The TEXT version of media_discover: scrape Twi song lyrics from Ghanaian music blogs (static HTML —
the lyric APPS like AfrikaLyrics/Genius are JS-walled; the blogs aren't), normalize the ASCII-Twi
conventions (3->ɛ), let language_id keep only the Twi words (Ghanaian lyrics code-switch Twi/English/
Pidgin heavily), corroborate across songs, and stage the survivors for promotion.

Copyrighted -> verifier/vocab-reference only, gitignored. Verify-not-trust: corroborated, never auto-added.

  python3 bank/ingest/lyrics_ingest.py <notjustok-lyric-url> [more urls...]
"""
import html as H
import re
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402

STAGED = Path(__file__).resolve().parents[1] / "data" / "aka" / "discovered.jsonl"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
TOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)
LABEL = re.compile(r"^(verse|chorus|bridge|hook|intro|outro|refrain|pre-?chorus)\b", re.I)


def fetch_lyrics(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    # blog lyric body lives in <p> tags; keep the ones that are actual lyric lines
    ps = [H.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in re.findall(r"<p[^>]*>(.*?)</p>", raw, re.S)]
    return [p for p in ps if len(p) > 8 and not LABEL.match(p) and "Notjustok" not in p and "LISTEN" not in p]


def norm(s):
    """ASCII-Twi conventions used by lyric sites: 3->ɛ, and bare o/e stay (we can't always recover ɔ)."""
    return s.replace("3", "ɛ").replace("ε", "ɛ")


def main():
    bank = Bank()
    urls = [a for a in sys.argv[1:] if a.startswith("http")]
    df = defaultdict(set)   # twi word -> set of song urls (corroboration)
    counts = {"twi": 0, "eng": 0, "unk": 0}
    for url in urls:
        try:
            lines = fetch_lyrics(url)
        except Exception as e:
            print(f"  {url[:50]}: fetch failed ({e})")
            continue
        song_words = set()
        for line in lines:
            for tok in TOK.findall(norm(line).lower()):
                tok = tok.strip("'’")
                if len(tok) < 2:
                    continue
                m = lid.membership(tok, bank)
                counts["twi" if "aka" in m else "eng" if "eng" in m else "unk"] += 1
                if "aka" in m and not bank.is_known(tok)["known"]:
                    song_words.add(tok)  # Twi word the bank doesn't have yet
        for w in song_words:
            df[w].add(url)
        print(f"  {url.split('/')[-2][:46]:46} {len(lines)} lines · {len(song_words)} new-Twi candidates")

    tot = sum(counts.values()) or 1
    corroborated = sorted(((w, len(c)) for w, c in df.items() if len(c) >= 2), key=lambda x: -x[1])
    oneoff = [w for w, c in df.items() if len(c) == 1]
    print(f"\nlyric language mix: Twi {100*counts['twi']//tot}% · English {100*counts['eng']//tot}% · unknown {100*counts['unk']//tot}%")
    print(f"NEW Twi words: {len(df)} total · {len(corroborated)} corroborated (>=2 songs) · {len(oneoff)} one-offs")
    for w, n in corroborated[:24]:
        print(f"  {w:16} in {n} songs")


if __name__ == "__main__":
    main()
