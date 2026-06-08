#!/usr/bin/env python3
"""Ingest the frequency-ranked Twi wordlist into the bank's wordforms layer.

These are bare words + frequency (no glosses) — the construct-and-verify "is this a real Twi word"
coverage set, plus a frequency rank for curriculum / conversational-utility sequencing. Distinct
from the glossed lexicon. Source TSV is frequency-sorted desc, so line order = rank. Idempotent.

Usage:  python3 bank/ingest/twi_words_to_wordforms.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../bank
SRC = ROOT / "sources" / "twi_words.tsv"
OUT = ROOT / "data" / "aka"
SOURCE_ID = "michsethowusu-twi-words"
AS_OF = "2026-06-07"


def main() -> None:
    rows = []
    for rank, line in enumerate(SRC.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        word = parts[0].strip()
        if not word:
            continue
        try:
            freq = int(parts[1]) if len(parts) > 1 and parts[1].strip() else None
        except ValueError:
            freq = None
        rows.append(
            {
                "id": f"aka:wf:{rank}",
                "lang": "aka",
                "word": word,
                "frequency": freq,
                "rank": rank,
                "provenance": {"source": SOURCE_ID, "verification": "unverified", "as_of": AS_OF},
            }
        )

    with (OUT / "wordforms.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wordforms  {len(rows)}")
    print(f"top 10     {[r['word'] for r in rows[:10]]}")


if __name__ == "__main__":
    main()
