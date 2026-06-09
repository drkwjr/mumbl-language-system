#!/usr/bin/env python3
"""Language readiness map — for each language, what do we HAVE vs LACK to bring it online?

Onboarding a language is the repeatable business motion, so it needs a portfolio view, not guesswork.
This inventories every language we have any data for and scores it against the component stack a language
needs to go from "captured audio" to "speaks naturally in the app":

  seed audio -> lexicon -> dictionary -> phonemes/G2P -> morphology -> grammar -> constructions -> TTS

High-resource ("famous") languages arrive with most of the middle of that stack for free (public
dictionaries, G2P, TTS) — their real gap is usually the construction/naturalness layer. Low-resource
languages start at "seed audio" and need the whole pipeline. This map shows, per language, exactly which
rungs are filled and which are the next thing to build.

  python3 bank/ingest/language_readiness.py
"""
import json
from pathlib import Path

ING = Path(__file__).resolve().parent
DATA = ING.parents[0] / "data"
CORPUS = ING.parents[0] / "corpus"
TTS = ING.parents[2] / "mumbl-server" / "services"
SEEDS = DATA / "aka" / "_captured_languages.jsonl"

# component -> (filename glob under data/<code>/, label). Order = the dependency stack.
STACK = [
    ("seed_audio", None, "seed audio (spoken)"),
    ("lexicon", "lexicon*.jsonl", "lexicon (words)"),
    ("dictionary", "glosses*.jsonl", "dictionary (meanings)"),
    ("phonemes", "phonemes*.jsonl", "phonemes / G2P"),
    ("morphology", "wordforms*.jsonl", "morphology (forms)"),
    ("grammar", "grammar.jsonl", "grammar"),
    ("constructions", "constructions.jsonl", "constructions (syntax)"),
    ("tts", None, "TTS voice"),
]
CODE_NAME = {"aka": "Twi (Akan)"}
CODE_TTS = {"aka": "twi"}  # the TTS sidecar is named by language, not ISO code


def count_lines(p):
    return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())


def assess_coded(code):
    d = DATA / code
    have = {}
    # corpus transcripts (live under corpus/<code>-*/_media/)
    cdirs = list(CORPUS.glob(f"{code}*"))
    n_corpus = sum(len(list(cd.rglob("*.twi.txt"))) for cd in cdirs)
    have["seed_audio"] = (n_corpus, f"{n_corpus} clips") if n_corpus else (0, "")
    for key, glob, _ in STACK:
        if key in ("seed_audio", "tts"):
            continue
        files = list(d.glob(glob)) if glob else []
        total = sum(count_lines(f) for f in files)
        have[key] = (total, f"{total:,}") if total else (0, "")
    tts = TTS / f"{CODE_TTS.get(code, code)}_tts.py"
    have["tts"] = (1, "sidecar") if tts.exists() else (0, "")
    return have


def assess_seed(lang, clips, minutes):
    have = {k: (0, "") for k, _, _ in STACK}
    have["seed_audio"] = (clips, f"{clips} clips ~{minutes:.0f}min")
    return have


def main():
    langs = {}  # display name -> have-dict

    # coded bank languages (anything with a data/<code>/ dir that has bank files)
    for d in sorted(DATA.iterdir()):
        if d.is_dir() and not d.name.startswith("_") and (list(d.glob("lexicon*.jsonl")) or list(d.glob("phrases.jsonl"))):
            langs[CODE_NAME.get(d.name, d.name)] = assess_coded(d.name)

    # captured-seed languages (audio only, awaiting the stack)
    if SEEDS.exists():
        from collections import Counter
        c = Counter()
        for line in SEEDS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r["lang"] not in ("Akan", "English", "unknown") and not r["lang"].startswith("unknown"):
                    c[r["lang"]] += 1
        for lang, clips in c.most_common():
            if lang not in langs:
                langs[lang] = assess_seed(lang, clips, clips * 3)

    # render
    labels = [lbl for _, _, lbl in STACK]
    print("LANGUAGE READINESS MAP\n")
    print(f"{'language':22} " + "  ".join(f"{l.split(' (')[0][:11]:11}" for l in labels) + "   ready")
    print("-" * 130)
    for name, have in langs.items():
        cells, filled = [], 0
        for key, _, _ in STACK:
            n, detail = have[key]
            if n:
                filled += 1
                cells.append(f"{('✓ ' + detail)[:11]:11}")
            else:
                cells.append(f"{'·':11}")
        pct = 100 * filled // len(STACK)
        print(f"{name[:22]:22} " + "  ".join(cells) + f"   {pct:3d}%")

    print("\ngaps (what to build next per language):")
    for name, have in langs.items():
        missing = [lbl for key, _, lbl in STACK if not have[key][0]]
        if missing:
            print(f"  {name}: needs {', '.join(missing)}")
        else:
            print(f"  {name}: complete ✓")


if __name__ == "__main__":
    main()
