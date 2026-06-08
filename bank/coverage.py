#!/usr/bin/env python3
"""Generated coverage map — what the bank HAS, and (via the overlay) what it's MISSING, per variety.

A bank that only shows what it contains lies by omission. This computes, per dialect view, how much of
each layer exists. A view includes records tagged for that dialect PLUS shared/unspecified ones (when we
don't know a dialect, we treat it as shared). Dialect-specific records of OTHER varieties are excluded —
which is how Akuapem-sourced phonemes correctly show up as MISSING for the Asante view.

Counts come from the data (always honest). bank/data/coverage-overlay.json adds the known-gap notes and
the graded audio-readiness states that record counts can't express. Generated presence always wins; the
overlay annotates intent and the things data can't see.

  python3 bank/coverage.py            # print the matrix
  python3 bank/coverage.py --json     # also write bank/data/coverage.json
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "aka"
ROOT = Path(__file__).resolve().parent / "data"

# layer -> (file, dialect source). "record" = read each record's own dialect tag; otherwise a fixed
# dialect inherited from the layer's source (until those layers carry per-record tags).
LAYERS = {
    "lexicon": ("lexicon.jsonl", "shared"),
    "wordforms": ("wordforms.jsonl", "aka-asante"),
    "phrases": ("phrases.jsonl", "unspecified"),
    "phonemes": ("phonemes*.jsonl", "record"),  # glob: Akuapem + Asante phoneme files
    "grammar": ("grammar.jsonl", "record"),
}
THRESH = {"lexicon": 2000, "wordforms": 10000, "phrases": 200, "phonemes": 30, "grammar": 5}
VIEWS = ["aka-asante", "aka-akuapem", "aka-fante"]
SHAREDISH = {"shared", "unspecified"}
# text states + the graded audio-readiness states (audio is its own axis, not a count)
GLYPH = {"missing": ".", "partial": "~", "sufficient": "#",
         "none": ".", "synthetic": "s", "sourced-rough": "r", "sourced-good": "g",
         "native-verified": "v", "native-recorded": "N"}


def load(name):
    # name may be a glob (e.g. phonemes*.jsonl) to merge per-dialect files
    rows = []
    for p in sorted(DATA.glob(name)) if any(c in name for c in "*?[") else ([DATA / name] if (DATA / name).exists() else []):
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


def state(layer, n):
    if n == 0:
        return "missing"
    return "sufficient" if n >= THRESH.get(layer, 1) else "partial"


def build():
    counts = {}  # layer -> {dialect: n}
    for layer, (f, src) in LAYERS.items():
        d = {}
        for r in load(f):
            dia = r.get("dialect", "unspecified") if src == "record" else src
            d[dia] = d.get(dia, 0) + 1
        counts[layer] = d

    overlay = json.loads((ROOT / "coverage-overlay.json").read_text(encoding="utf-8"))
    notes = {}
    for nt in overlay["notes"]:
        notes.setdefault(nt["variety"], {})[nt["layer"]] = nt["note"]

    matrix = {}
    for v in VIEWS:
        row = {}
        for layer in LAYERS:
            n = sum(c for dia, c in counts[layer].items() if dia == v or dia in SHAREDISH)
            row[layer] = {"count": n, "state": state(layer, n)}
        anote = notes.get(v, {}).get("audio")
        # audio readiness comes from the overlay (graded), not from a count
        astate = next((x["state"] for x in overlay["notes"] if x["variety"] == v and x["layer"] == "audio"), "none")
        row["audio"] = {"count": 0, "state": astate}
        matrix[v] = row
    backbone = {"concepts": len(load("concepts.jsonl")), "relations": len(load("relations.jsonl")), "variants": len(load("variants.jsonl"))}
    return matrix, backbone, notes


def main():
    matrix, backbone, notes = build()
    cols = list(LAYERS) + ["audio"]
    print("\nBANK COVERAGE  (text: #=sufficient ~=partial .=missing | audio: s=synthetic r=rough g=good v/N=native)\n")
    print(f"  {'view':14} " + "  ".join(f"{c[:9]:>9}" for c in cols))
    for v, row in matrix.items():
        cells = "  ".join(f"{GLYPH[row[c]['state']]}{row[c]['count']:>8}" for c in cols)
        print(f"  {v:14} {cells}")
    print(f"\n  shared backbone: {backbone['concepts']} concepts · {backbone['relations']} relations · {backbone['variants']} variants (dialect-agnostic)")

    print("\nKNOWN GAPS (overlay):")
    for v in matrix:
        for layer, note in notes.get(v, {}).items():
            if matrix[v].get(layer, {}).get("state") in ("missing", "partial", None) or layer == "audio":
                print(f"  [{v} · {layer}] {note}")

    if "--json" in sys.argv:
        out = ROOT / "coverage.json"
        out.write_text(json.dumps({"matrix": matrix, "backbone": backbone}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
