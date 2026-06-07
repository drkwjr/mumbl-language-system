#!/usr/bin/env python3
"""Ingest the Wikivoyage Twi phrasebook into the bank's phrase layer.

Parses the ';' definition-list lines (English : Twi) from the cached raw wikitext, tags each phrase
with the section it sits under (Basics / Numbers / Eating / Shopping / ...) as a topic, and pulls
out pronunciation hints and formal/informal register. CC-BY-SA source → 'unverified' tier (candidate
phrases for the verify-not-trust pipeline). Idempotent.

Usage:  python3 bank/ingest/wikivoyage_to_phrases.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../bank
SRC = ROOT / "sources" / "wikivoyage-twi.wikitext"
OUT = ROOT / "data" / "aka"
SOURCE_ID = "wikivoyage-twi"
LICENSE = "CC-BY-SA-4.0"
AS_OF = "2026-06-07"
REGISTER = {"formal", "informal", "polite", "casual"}


def strip_markup(s: str) -> str:
    s = re.sub(r"'''?", "", s)  # bold / italic
    s = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", s)  # [[link|text]] -> text
    s = s.replace("{{", "").replace("}}", "")
    return re.sub(r"\s+", " ", s).strip()


def extract_notes(s: str):
    """Pull (''note'') parentheticals out; return (clean_text, [notes])."""
    notes = re.findall(r"\(''([^']+)''[^)]*\)", s)
    s = re.sub(r"\(''[^']+''[^)]*\)", "", s)
    return s, [n.strip() for n in notes]


def main() -> None:
    section = None
    phrases = []
    for line in SRC.read_text(encoding="utf-8").splitlines():
        h = re.match(r"^==+\s*(.+?)\s*==+\s*$", line)
        if h:
            section = strip_markup(h.group(1))
            continue
        m = re.match(r"^;\s*(.+?)\s*:\s*(.+)$", line)
        if not m:
            continue
        eng, eng_notes = extract_notes(m.group(1))
        twi, twi_notes = extract_notes(m.group(2))
        eng, twi = strip_markup(eng), strip_markup(twi)
        if not eng or not twi:
            continue
        notes = eng_notes + twi_notes
        register = next((n.lower() for n in notes if n.lower() in REGISTER), None)
        pron = next((n for n in twi_notes if n.lower() not in REGISTER), None)
        phrases.append(
            {
                "id": f"aka:phrase:{len(phrases) + 1:04d}",
                "lang": "aka",
                "text_aka": twi,
                "text_en": eng,
                "topic": section,
                "register": register,
                "pronunciation_hint": pron,
                "provenance": {"source": SOURCE_ID, "license": LICENSE, "verification": "unverified", "as_of": AS_OF},
            }
        )

    with (OUT / "phrases.jsonl").open("w", encoding="utf-8") as f:
        for r in phrases:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    topics: dict[str, int] = {}
    for r in phrases:
        topics[r["topic"] or "(none)"] = topics.get(r["topic"] or "(none)", 0) + 1
    print(f"phrases  {len(phrases)}")
    print(f"with pronunciation hint  {sum(1 for r in phrases if r['pronunciation_hint'])}")
    print("by topic:", dict(sorted(topics.items(), key=lambda x: -x[1])[:12]))


if __name__ == "__main__":
    main()
