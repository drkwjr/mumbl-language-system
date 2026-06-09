#!/usr/bin/env python3
"""Dialect discernment (heuristic, reviewable) — can we tell which Akan dialect a transcript is?

Akan is a dialect continuum. In TEXT, the cleanly separable split is Fante (Mfantse) vs the Twi cluster
(Asante + Akuapem); Asante-vs-Akuapem differences are mostly phonetic and don't survive ASR, so we MERGE
them as "twi" and say so. Bono/Kwawu get weak markers — flagged low-confidence.

Method: high-precision marker words per dialect (characteristic forms a dialect uses where the others use
something else — e.g. Fante 'dze' where Twi says 'de', Fante 'hom' for 2pl where Twi says 'mo', Fante
'nyim' vs Twi 'nim'). Score a transcript by which dialect's markers dominate. This is a HEURISTIC that
SURFACES the dialect signal for review and routing — not an authority. Markers want native review before
any are trusted as ground truth; that's a first-class contributor task, not a model assertion.

Runs over the _media transcript cache and reports the corpus dialect mix + the strongest non-Asante clips
(the interesting ones — Fante/Bono that the wide net pulled in, which want dialect-appropriate handling).

  python3 bank/ingest/dialect_tag.py [--show 15]
"""
import re
import sys
from collections import Counter
from pathlib import Path

MEDIA = Path(__file__).resolve().parents[1] / "corpus" / "aka-asante" / "_media"
TOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)

# High-precision markers: a form one dialect uses where the OTHERS use something else. Conservative on
# purpose — better to tag "und" than to mislabel. (Heuristic; pending native review.)
MARKERS = {
    "fante": {"dze", "hom", "homu", "nyim", "mbofra", "mbɔfra", "dɛm", "ekyir", "ngyae", "osi", "ɔkyer",
              "rdo", "obu", "ɔbɔr", "kakraba", "mbusua", "nzu", "edziban", "ndze"},
    "twi": {"de", "mo", "nim", "mmɔfra", "firi", "saa", "deɛ", "ɛno", "wɔn", "yɛn", "ɛyɛ", "aane"},
    "bono": {"aane", "kraman", "ankasa", "yie"},  # weak — low confidence
}
# words too common to discriminate (appear in all dialects) get no weight even if listed above
NEUTRAL = {"de", "saa", "yɛn", "ɛyɛ", "wɔn", "aane"}


def score(text):
    toks = Counter(t.strip("'’").lower() for t in TOK.findall(text) if len(t.strip("'’")) >= 2)
    hits = {d: 0 for d in MARKERS}
    seen = {d: [] for d in MARKERS}
    for d, mk in MARKERS.items():
        for w in mk - NEUTRAL:
            if toks.get(w):
                hits[d] += toks[w]
                seen[d].append(w)
    return hits, seen


def classify(hits):
    """Fante only when its markers clearly out-vote the Twi cluster (it's the marked case); else Twi if any
    Twi signal; else undetermined. Bono is advisory only."""
    f, t = hits["fante"], hits["twi"]
    if f >= 2 and f > t:
        return "fante"
    if t >= 2:
        return "twi"
    if f >= 1 and f > t:
        return "fante?"
    return "und"


def main():
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 12
    files = sorted(MEDIA.glob("*.twi.txt"))
    if not files:
        print("no transcripts in the _media cache yet — run harvest_pool first")
        return
    dist = Counter()
    flagged = []  # (fante_score, vid, markers)
    for f in files:
        text = f.read_text(encoding="utf-8")
        if len(text) < 40:
            continue
        hits, seen = score(text)
        tag = classify(hits)
        dist[tag] += 1
        if tag in ("fante", "fante?") and hits["fante"]:
            flagged.append((hits["fante"], f.stem.replace(".twi", ""), seen["fante"]))

    total = sum(dist.values()) or 1
    print(f"corpus: {total} transcripts\n")
    print("dialect mix (heuristic):")
    for tag in ("twi", "fante", "fante?", "und"):
        n = dist.get(tag, 0)
        label = {"twi": "Twi (Asante/Akuapem — merged)", "fante": "Fante (Mfantse)",
                 "fante?": "Fante (low confidence)", "und": "undetermined"}[tag]
        print(f"  {100 * n // total:3d}%  {label:34} {n}")

    flagged.sort(reverse=True)
    print(f"\nstrongest non-Asante (Fante-leaning) clips — the ones wanting dialect-aware handling:")
    for sc, vid, mk in flagged[:show]:
        print(f"  fante={sc:2d}  {vid:14} markers: {', '.join(sorted(set(mk)))}")
    if not flagged:
        print("  (none — corpus is currently Twi-cluster, as expected from Asante-biased seeds)")
    print("\nNOTE: heuristic. Asante vs Akuapem is NOT separated here (phonetic, lost in ASR).")
    print("Markers are a starting point for native review, not ground truth.")


if __name__ == "__main__":
    main()
