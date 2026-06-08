#!/usr/bin/env python3
"""Extract Asante-Twi WORDS from two copyrighted learner books for VERIFIER COVERAGE only.

Licensing posture (Sam's call): these books are in copyright (Anna's Archive). We extract only the
vocabulary — word facts, not copyrightable — to expand the "is this a real Asante word" verifier, and we
keep it LOCAL + GITIGNORED so nothing copyrighted is ever published or voiced. NOT a generation source.

Books (in ~/Downloads, extracted to /tmp/twibooks):
  - "Tie Ma Mense Wo" (Adu-Amankwah, 2017): English – Twi vocabulary + examples
  - "Language guide (Asante Twi)" (Bureau of Ghana Languages, 1973): bilingual guide text

  /tmp/ytenv/bin/python bank/ingest/asante_books_to_verifier.py
"""
import glob
import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "aka" / "_restricted" / "asante-books.jsonl"
TWITOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)
# English leakage to drop (POS tags, abbreviations, common words that ride along on the Twi side)
DROP = set("e g i ob sb v n adj adv prep pl sing lit cf eg ie etc the a to of and or is are no not "
           "my your his her our the we you they he she it him them this that note also".split())
# the system English dictionary — drop English homographs (a verifier that accepts English as Twi is broken)
ENGLISH = set()
for _p in ("/usr/share/dict/words",):
    try:
        ENGLISH = {w.strip().lower() for w in open(_p, encoding="utf-8", errors="replace")}
    except OSError:
        pass


def twi_words(s):
    """Tokens from the Twi side of a 'English – Twi' entry — Twi by position, so keep all (minus the
    English-leakage DROP set + stray ascii single letters)."""
    s = re.sub(r"\[[^\]]*\]", " ", s)  # strip [English POS/notes]
    out = []
    for t in TWITOK.findall(s.lower()):
        t = t.strip("'’")
        twiish = any(c in t for c in "ɛɔŋ")
        if len(t) > 1 and t not in DROP and (twiish or t not in ENGLISH):
            out.append(t)
    return out


def from_epub():
    words = set()
    for f in glob.glob("/tmp/twibooks/epub/OEBPS/*.xhtml"):
        t = Path(f).read_text(encoding="utf-8", errors="replace")
        for p in re.findall(r"<p[^>]*>(.*?)</p>", t, re.S):
            txt = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", p)).strip()
            parts = re.split(r"\s[–-]\s", txt, maxsplit=1)
            if len(parts) == 2:  # English – Twi: the right side is Twi
                words.update(twi_words(parts[1]))
    return words


def from_guide():
    words = set()
    for f in glob.glob("/tmp/twibooks/zip/**/*.txt", recursive=True):
        t = Path(f).read_text(encoding="utf-8", errors="replace")
        for tok in TWITOK.findall(t.lower()):
            tok = tok.strip("'’")
            if len(tok) > 1 and any(c in tok for c in "ɛɔŋ") and tok not in DROP:  # only clearly-Twi tokens
                words.add(tok)
    return words


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    epub = from_epub()
    guide = from_guide()
    words = epub | guide
    with OUT.open("w", encoding="utf-8") as f:
        for w in sorted(words):
            f.write(json.dumps({"word": w, "dialect": "aka-asante", "source": "asante-learner-books",
                                "license": "copyright-restricted", "use": "verifier-reference-only"},
                               ensure_ascii=False) + "\n")
    print(f"epub words: {len(epub)} · guide words: {len(guide)} · total unique: {len(words)} -> {OUT}")
    print("samples:", sorted(words)[100:115])


if __name__ == "__main__":
    main()
