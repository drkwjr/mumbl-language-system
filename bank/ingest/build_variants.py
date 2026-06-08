#!/usr/bin/env python3
"""Cluster lexicon lemmas into spelling-variant groups by phoneme key (GhanaNLP/twi-g2p).

Lemmas that map to the same normalized phoneme key are variant spellings of one word (e.g. nsuo~nsu,
medaase~medase) — the variant edge of the relation taxonomy, constructed from sound. Tier 'auto'
(verify-not-trust): G2P-derived candidates. Needs twi-g2p installed. Idempotent.

Usage:  /tmp/ytenv/bin/python bank/ingest/build_variants.py   (any python with twi-g2p)
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import morphophon as mp  # noqa: E402

LEX = ROOT / "data" / "aka" / "lexicon.jsonl"
OUT = ROOT / "data" / "aka" / "variants.jsonl"


def main() -> None:
    if mp._g2p_fn() is None:
        raise SystemExit("twi-g2p not importable — pip install git+https://github.com/GhanaNLP/twi-g2p")
    entries = [json.loads(l) for l in LEX.read_text(encoding="utf-8").splitlines()]
    groups = defaultdict(set)
    for e in entries:
        k = mp.pkey(e["lemma"])
        if k:
            groups[k].add(e["lemma"])

    variants = []
    for k, lemmas in groups.items():
        if len(lemmas) >= 2:
            variants.append(
                {
                    "id": f"variant:{len(variants) + 1:04d}",
                    "pkey": k,
                    "spellings": sorted(lemmas),
                    "provenance": {"source": "twi-g2p", "method": "phoneme-key", "verification": "auto", "as_of": "2026-06-07"},
                }
            )

    with OUT.open("w", encoding="utf-8") as f:
        for v in variants:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    print(f"variant groups (>=2 spellings): {len(variants)}")
    for v in variants[:8]:
        print("  ", v["spellings"])


if __name__ == "__main__":
    main()
