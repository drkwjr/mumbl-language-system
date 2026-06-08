#!/usr/bin/env python3
"""Promotion loop — graduate corroborated discoveries into the bank. Closes the flywheel.

harvest.py STAGES corroborated unknowns to discovered.jsonl; nothing used them yet. This promotes the
ones that clear a bar (corroborated in >= N clips, survives the English/filler/proper-noun screen, has a
proposed gloss) into data/aka/discovered-promoted.jsonl at verification tier `auto` — real enough to
verify against and ground generation on, NOT `native-verified` (a human still signs off later). Additive
+ reversible: promoted rows carry provenance (clips, method) and a tier; nothing is overwritten.

  python3 bank/ingest/promote.py [--min-clips 3] [--dry-run]
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402
import morphophon as mp  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "aka"
STAGED = DATA / "discovered.jsonl"
PROMOTED = DATA / "discovered-promoted.jsonl"
VOWELS = set("aeiouɛɔ")

# English contraction bases (it's, i'm, don't) — but KEEP Twi elision (n'adwuma, m'ayɛ, w'akɔ): the base
# of a Twi elision is a syllabic consonant (m/n/w/y), not an English pronoun/aux.
EN_CONTRACTION_BASE = {"it", "i", "don", "can", "won", "didn", "that", "what", "let", "we", "you", "they",
                       "he", "she", "there", "here", "isn", "aren", "wasn", "weren", "doesn", "ain", "y"}
FILLER = re.compile(r"^(.)\1+h?$|^[aeiou]+h$|^(ah|eh|oh|mm+|hm+|aa+|oo+|ee+|uu+)$", re.I)
# letters foreign to Twi orthography — a token using them is English/abbreviation/noise (e.g. "tv", "vim").
NON_TWI_LETTERS = set("cjqvxz")


def is_noise(word, bank):
    w = word.strip().lower()
    if len(w) < 2:
        return True
    if NON_TWI_LETTERS & set(w):               # c/j/q/v/x/z aren't Twi letters
        return True
    if not (VOWELS & set(w)):                   # no vowel -> acronym/abbreviation (npp, fm, ndc, mm)
        return True
    m = lid.membership(w, bank)
    if "eng" in m and "aka" not in m:          # plain English word
        return True
    if ("'" in w or "’" in w):                  # contraction vs Twi elision
        base = re.split(r"['’]", w)[0]
        if base in EN_CONTRACTION_BASE:
            return True
    if FILLER.match(w):                          # aaa, aah, ooo, mm, interjections
        return True
    return False


def proper_nouns(words):
    """Gemini NER — flag tokens that are proper nouns (person/place/org/brand/acronym), not vocabulary.
    Catches what the orthographic screen can't: politician names (Addo), places (Kumasi), brands. Cheap;
    skipped gracefully if no key. Default-keep on failure (the deterministic screen is the floor)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key or not words:
        return set()
    prompt = ("These tokens are from Asante Twi radio/video transcripts. For EACH, classify it as a "
              "PROPER NOUN (person, place, organization, political party, brand, or acronym) or a COMMON "
              "word/phrase.\n" + "\n".join(words))
    schema = {"type": "array", "items": {"type": "object", "properties": {
        "token": {"type": "string"}, "kind": {"type": "string", "enum": ["proper", "common"]}},
        "required": ["token", "kind"]}}
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": schema}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=60).read())
        verdict = json.loads(r["candidates"][0]["content"]["parts"][0]["text"])
        return {row["token"] for row in verdict if str(row.get("kind", "")).lower() == "proper"}
    except Exception:
        return set()


def main():
    bank = Bank()
    min_clips = int(sys.argv[sys.argv.index("--min-clips") + 1]) if "--min-clips" in sys.argv else 3
    dry = "--dry-run" in sys.argv

    staged = [json.loads(l) for l in STAGED.read_text(encoding="utf-8").splitlines() if l.strip()]
    already = {json.loads(l)["word"] for l in (PROMOTED.read_text(encoding="utf-8").splitlines() if PROMOTED.exists() else []) if l.strip()}

    promote, rejected, skipped = [], [], 0
    for r in staged:
        w = r["word"]
        if w in already:
            skipped += 1
            continue
        freq = r.get("freq", 0)
        if freq < min_clips:
            continue
        if bank.is_known(w)["known"]:            # already in the bank by some other layer
            skipped += 1
            continue
        if is_noise(w, bank):
            rejected.append(w)
            continue
        if not r.get("gloss_proposed"):          # need a candidate meaning to be useful
            continue
        promote.append({
            "word": w, "gloss_en": r["gloss_proposed"], "freq": freq,
            "tier": "auto", "dialect": "aka-asante", "method": r.get("method", "media-corroborated"),
            "provenance": f"corroborated in {freq} clips", "gloss_status": "proposed-unverified",
        })

    # NER pass — drop proper nouns the deterministic screen can't catch (names, places, parties)
    propers = proper_nouns([p["word"] for p in promote])
    if propers:
        rejected += [w for w in propers]
        promote = [p for p in promote if p["word"] not in propers]

    print(f"staged {len(staged)} · promote {len(promote)} (>= {min_clips} clips, screened) · "
          f"rejected {len(rejected)} noise · skipped {skipped} (already known/promoted)")
    if rejected:
        print("  screened out:", ", ".join(sorted(set(rejected))[:24]))
    if propers:
        print("  NER dropped (proper nouns):", ", ".join(sorted(propers)))
    print("  promoting:")
    for p in promote[:24]:
        print(f"    {p['word']:14} ({p['freq']:2} clips)  ~ {p['gloss_en'][:34]}")

    if dry:
        print("\n(dry run — nothing written)")
        return
    with PROMOTED.open("a", encoding="utf-8") as f:
        for p in promote:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"\n-> appended {len(promote)} to {PROMOTED.name} (tier=auto). serve.py loads it into known + glosses + grounding.")


if __name__ == "__main__":
    main()
