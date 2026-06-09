#!/usr/bin/env python3
"""Export the bank as JSON the app (mumbl-server, TS) loads at startup — the serving bridge.

The bank is data-as-code (Python + JSONL); the app is Node/TS. Until the Postgres+pgvector serving
layer (ANO-1699) lands, this is the interim sync: flatten the three things the app's brain needs —
sourced glosses (tap-to-understand), the known-word set (verify the character's Twi), and the
bilingual grounding pool (ground the reply) — into JSON. Regenerable; a build artifact, not source.

Writes to mumbl-server/data/bank/ (gitignored there — it carries restricted-derived glosses, which
we USE but do not redistribute).

  python3 bank/export_for_app.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serve import Bank  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "mumbl-server" / "data" / "bank"


def main():
    b = Bank()
    OUT.mkdir(parents=True, exist_ok=True)

    # sourced glosses: twi(lower) -> english meaning (from the bank, never a model guess)
    (OUT / "glosses.json").write_text(json.dumps(b.glosses, ensure_ascii=False), encoding="utf-8")

    # verifier set: every word the bank knows is real Twi
    (OUT / "known.json").write_text(json.dumps(sorted(b.known), ensure_ascii=False), encoding="utf-8")

    # grounding pool: bilingual pairs the brain composes a reply from
    pairs = [{"twi": p["twi"], "en": p["en"], "source": p["source"]} for p in b.pairs]
    (OUT / "grounding.json").write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")

    # construction layer: how Twi chains words (for syntax grounding + structural verification)
    cpath = Path(__file__).resolve().parent / "data" / "aka" / "constructions.jsonl"
    cons = [json.loads(line) for line in cpath.read_text(encoding="utf-8").splitlines() if line.strip()] if cpath.exists() else []
    cons = [{"chunk": c["chunk"], "freq": c["freq"], "n": c["n"]} for c in cons]
    (OUT / "constructions.json").write_text(json.dumps(cons, ensure_ascii=False), encoding="utf-8")

    meta = {"glosses": len(b.glosses), "known": len(b.known), "grounding": len(pairs),
            "constructions": len(cons), "lang": "aka", "langName": "Twi"}
    (OUT / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"exported -> {OUT}")
    print(f"  glosses {meta['glosses']:,} · known {meta['known']:,} · grounding {meta['grounding']:,}")


if __name__ == "__main__":
    main()
