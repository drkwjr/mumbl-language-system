#!/usr/bin/env python3
"""Ingest the kasahorow English-Akan wordlist into the data-as-code language bank.

Produces OntoLex-ish JSONL under bank/data/aka/:
  - lexicon.jsonl   : lexical entries (lemma / pos / forms / senses / bilingual examples + provenance)
  - concepts.jsonl  : the concept layer (senses sharing an English gloss share a concept)
  - relations.jsonl : typed edges (synonyms via shared concept)

The concept layer here is FIRST-PASS, gloss-derived: two Akan words mapped to the same English
gloss are treated as sharing a concept (hence candidate synonyms). That is a heuristic, so concepts
and synonym edges are tagged verification 'auto-gloss' / entries 'unverified' — candidates for the
verify-not-trust pipeline, not ground truth. Idempotent: rewrites outputs from source each run.

Usage:  python3 bank/ingest/kasahorow_to_lexicon.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .../bank
SRC = ROOT / "sources" / "kasahorow-akan.tsv"
OUT = ROOT / "data" / "aka"
LANG = "aka"
SOURCE_ID = "kasahorow-akan"
LICENSE = "BSD-2-Clause"
AS_OF = "2026-06-07"


def slug(s: str) -> str:
    s = re.sub(r"[^\w'-]+", "-", s.strip().lower(), flags=re.UNICODE)
    return re.sub(r"-{2,}", "-", s).strip("-") or "x"


def norm_gloss(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def write_jsonl(path: Path, rows) -> int:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def main() -> None:
    entries = []
    concepts: dict[str, dict] = {}
    seen = defaultdict(int)
    sense_lemma: dict[str, str] = {}

    for line in SRC.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        akan = cols[0].strip() if len(cols) > 0 else ""
        english = cols[1].strip() if len(cols) > 1 else ""
        pos = cols[2].strip() if len(cols) > 2 else ""
        akan_ex = cols[5].strip() if len(cols) > 5 else ""
        en_ex = cols[6].strip() if len(cols) > 6 else ""
        if not akan or not english or akan == "_":
            continue

        base = f"{LANG}:{slug(akan)}"
        eid = f"{base}:{seen[base]}"
        seen[base] += 1

        cid = f"concept:{slug(norm_gloss(english))}"
        concepts.setdefault(cid, {"id": cid, "label_en": norm_gloss(english), "senses": []})
        sid = f"{eid}#s1"
        concepts[cid]["senses"].append(sid)
        sense_lemma[sid] = akan

        examples = [{"aka": akan_ex, "en": en_ex}] if akan_ex and en_ex else []
        entries.append(
            {
                "id": eid,
                "lang": LANG,
                "lemma": akan,
                "pos": pos or None,
                "forms": [{"writtenRep": akan}],
                "senses": [{"id": sid, "gloss_en": english, "concept": cid, "examples": examples}],
                "provenance": {"source": SOURCE_ID, "license": LICENSE, "verification": "unverified", "as_of": AS_OF},
            }
        )

    # Synonyms: senses sharing a concept (gloss-derived → 'auto-gloss' tier).
    relations = []
    for c in concepts.values():
        ss = c["senses"]
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                if sense_lemma.get(ss[i]) == sense_lemma.get(ss[j]):
                    continue  # same spelling isn't its own synonym
                relations.append(
                    {
                        "type": "synonym",
                        "a": ss[i],
                        "b": ss[j],
                        "via": c["id"],
                        "provenance": {"source": SOURCE_ID, "method": "shared-gloss", "verification": "auto-gloss", "as_of": AS_OF},
                    }
                )

    OUT.mkdir(parents=True, exist_ok=True)
    n_lex = write_jsonl(OUT / "lexicon.jsonl", entries)
    n_con = write_jsonl(OUT / "concepts.jsonl", list(concepts.values()))
    n_rel = write_jsonl(OUT / "relations.jsonl", relations)

    multi = sum(1 for c in concepts.values() if len(c["senses"]) >= 2)
    with_ex = sum(1 for e in entries if e["senses"][0]["examples"])
    print(f"entries        {n_lex}")
    print(f"concepts       {n_con}   ({multi} with >=2 realizations = synonym sets)")
    print(f"synonym edges  {n_rel}")
    print(f"with examples  {with_ex}/{n_lex}")


if __name__ == "__main__":
    main()
