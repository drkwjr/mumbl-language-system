#!/usr/bin/env python3
"""Generate the Twi sound key (phonemes.jsonl) from Christaller's Grammar (1875), recovered via IIIF
vision re-OCR — NOT from the lossy djvu.txt.

This is the auditable source of the phoneme layer: every record is transcribed from a specific page
image (leaf) of the public-domain grammar and cites it. Sound descriptions + Christaller's orthography
are `sourced`; the IPA and modern-Twi-orthography columns are my `reconciled` linguistic mapping.

Sections: §1-4 vowels + nasal/length (leaf 34) · §13 System of Consonants (leaf 39) · §15 w̃ (leaf 40)
· §25 Of Tone and Accent (leaf 47). Re-run to rebuild phonemes.jsonl (idempotent).

  /tmp/ytenv/bin/python bank/ingest/christaller_to_phonemes.py   (any python; no deps)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "aka" / "phonemes.jsonl"
IIIF = "https://iiif.archive.org/iiif/grammarofasantef00chriuoft"


def prov(section, leaf, evidence, tier="sourced"):
    return {
        "source": "christaller-grammar",
        "section": section,
        "leaf": leaf,
        "image": f"{IIIF}${leaf}/full/full/0/default.jpg",
        "method": "iiif-vision-reocr",
        "evidence": evidence,
        "verification": tier,
    }


# (christaller, grade, class, sound_desc, ipa, modern) — §1-4, leaf 34
VOWELS = [
    ("a", "full", "guttural", "a in 'far'", "a", "a"),
    ("ạ", "thin", "guttural", "a in 'fat'", "æ", "a"),
    ("e̱", "narrow", "palatal", "between e and i", "ɪ", "e"),
    ("e", "broad", "palatal", "e in 'very', 'there'", "ɛ", "ɛ"),
    ("ẹ", "full", "palatal", "e in 'heel', a in 'fate'", "e", "e"),
    ("i", "close", "palatal", "i in 'fill', 'ravine'", "i", "i"),
    ("o̱", "narrow", "labial", "between o and u", "ʊ", "o"),
    ("o", "broad", "labial", "o in 'not', 'nor'", "ɔ", "ɔ"),
    ("ọ", "full", "labial", "o in 'tobacco', 'note'", "o", "o"),
    ("u", "close", "labial", "u in 'full', 'rule'", "u", "u"),
]
VOWEL_EVID = "§3 'ten principal vowels: a ạ (guttural) | e̱ e ẹ i (palatal) | o̱ o ọ u (labial)' with pronunciation table; djvu.txt flattens every diacritic"

# (christaller, family, manner, sound_desc, ipa, modern, tier) — §13 System of Consonants, leaf 39
CONSONANTS = [
    ("p", "labial", "mute-hard", "p", "p", "p", "sourced"),
    ("b", "labial", "mute-soft", "b", "b", "b", "sourced"),
    ("f", "labial", "fricative-sharp", "f", "f", "f", "sourced"),
    ("m", "labial", "nasal", "m", "m", "m", "sourced"),
    ("w", "labial", "semivowel", "gentle vocalic breathing between nearly closed lips", "w", "w", "sourced"),
    ("t", "dental", "mute-hard", "t", "t", "t", "sourced"),
    ("d", "dental", "mute-soft", "d", "d", "d", "sourced"),
    ("s", "dental", "fricative-sharp", "s", "s", "s", "sourced"),
    ("r", "dental", "semivowel", "r", "r", "r", "sourced"),
    ("k", "guttural", "mute-hard", "k", "k", "k", "sourced"),
    ("g", "guttural", "mute-soft", "g", "ɡ", "g", "sourced"),
    ("h", "guttural", "fricative-sharp", "h", "h", "h", "sourced"),
    ("ṅ", "guttural", "nasal", "velar nasal", "ŋ", "ŋ", "sourced"),
    ("ky", "palatal", "mute-hard", "palatal k", "tɕ", "ky", "reconciled"),
    ("gy", "palatal", "mute-soft", "palatal g", "dʑ", "gy", "reconciled"),
    ("hy", "palatal", "fricative-sharp", "palatal h", "ɕ", "hy", "reconciled"),
    ("ny", "palatal", "nasal", "palatal n", "ɲ", "ny", "sourced"),
    ("y", "palatal", "semivowel", "gentle vocalic breathing between tongue and palate", "j", "y", "sourced"),
    ("kw", "guttural-labial", "mute-hard", "labialized k", "kʷ", "kw", "reconciled"),
    ("gw", "guttural-labial", "mute-soft", "labialized g", "ɡʷ", "gw", "reconciled"),
    ("hw", "guttural-labial", "fricative-sharp", "labialized h", "hʷ", "hw", "reconciled"),
    ("ṅw", "guttural-labial", "nasal", "labialized velar nasal", "ŋʷ", "nw", "reconciled"),
    ("tw", "palato-labial", "mute-hard", "labio-palatal t", "tɕʷ", "tw", "reconciled"),
    ("dw", "palato-labial", "mute-soft", "labio-palatal d", "dʑʷ", "dw", "reconciled"),
    ("fw", "palato-labial", "fricative-sharp", "labio-palatal f", "fʷ", "fw", "reconciled"),
    ("w̃", "palato-labial", "semivowel", "gentle vocalic breathing from both passages (lips + tongue-palate); §15", "ɥ", "w (hw)", "reconciled"),
]
CONS_EVID = "§13 'System of Consonants': families Labials/Dentals/Gutturals/Palatals/Guttural-labials/Palato-labials across mutes (hard,soft), fricatives (sharp,flat), semi-vowels (nasal,pure)"

# marginal / Fante / foreign (bracketed in §13, or §14) — kept for completeness, tier marginal
MARGINAL = [
    ("ts", "dental", "Fante affricate (t before e, i)", "ts", "ts", "§14 'in some Fante dialects t and d are changed into ts and dz before e, i'"),
    ("dz", "dental", "Fante affricate (d before e, i)", "dz", "dz", "§14 Fante t/d -> ts/dz before e, i"),
    ("v", "labial", "foreign/flat fricative [v]", "v", "v", "§13 bracketed [v]; §15.2 'foreign letters v z sound as in English'"),
    ("z", "dental", "foreign/flat fricative [z]", "z", "z", "§13 bracketed [z]; §15.2 foreign"),
]

# tone — §25 Of Tone and Accent, leaf 47
TONES = [
    ("low", "à (grave); unmarked before the first high tone", 1, "low tone relative to neighbouring syllables", "Rule 1 'low-toned syllables preceding the first high tone are left unmarked: aberewà'; Rule 4 'low tone after/between high tones marked with grave: òba he comes'"),
    ("middle", "á (acute; a downstepped high)", 2, "high tone abating by one or more steps (automatic/terraced downstep)", "Rule 3 'subsequent middle tones, i.e. high tones abating by one step, marked with the acute: obóntó (132)'"),
    ("high", "á (acute)", 3, "high tone relative to neighbouring syllables", "Rule 2 'the first high tone in a word/sentence is marked with the acute accent: óba child'"),
]
CONTOURS = [
    ("rising", "ǎ (caron)", "low-high on a long vowel/diphthong", "§25.6c 'low, high: kǎ ring; ṅkáé remnant'"),
    ("falling", "â (circumflex)", "high-middle on a long vowel/diphthong", "§25.6d 'high, middle: nàdâ deceit; têtê asthma'"),
]


def main():
    recs = []
    for ch, grade, cls, desc, ipa, modern in VOWELS:
        recs.append({"id": f"phon:aka:V-{grade}-{cls[:3]}", "type": "vowel", "christaller": ch, "grade": grade,
                     "class": cls, "sound_desc": desc, "ipa": ipa, "modern_twi": modern, "mapping_tier": "reconciled",
                     "provenance": prov("Part I ch.1 §1-4", 34, VOWEL_EVID)})
    recs.append({"id": "phon:aka:nasal", "type": "diacritic", "function": "nasalization", "christaller": "◌̃",
                 "sound_desc": "nasal vowels marked ã ẽ ĩ õ ũ; mark often dropped next to nasal consonants. Minimal pair ka 'bite' vs kã 'touch/speak'",
                 "modern_twi": "(usually unmarked/contextual)", "mapping_tier": "reconciled",
                 "provenance": prov("Part I ch.1 §3", 34, "§3 'Nasal vowels are marked thus: ã ẽ ĩ õ ũ'")})
    recs.append({"id": "phon:aka:length", "type": "diacritic", "function": "length", "christaller": "◌̄",
                 "sound_desc": "long vowels marked with a macron, or by doubling. Minimal pair ka 'bite' vs kā 'touch'",
                 "modern_twi": "(vowel doubling, e.g. aa)", "mapping_tier": "reconciled",
                 "provenance": prov("Part I ch.1 §4", 34, "§4 'Long vowels are marked thus [macron]. In certain cases the vowel is doubled'")})
    for ch, fam, manner, desc, ipa, modern, tier in CONSONANTS:
        cid = "".join(c for c in modern if c.isalnum()) or "x"  # alnum-fold keeps w (plain) vs w̃ ('w (hw)') distinct
        recs.append({"id": f"phon:aka:C-{cid}", "type": "consonant", "christaller": ch, "family": fam,
                     "manner": manner, "sound_desc": desc, "ipa": ipa, "modern_twi": modern, "mapping_tier": "reconciled",
                     "provenance": prov("Part I ch.1 §13" + (", §15" if ch == "w̃" else ""), 39 if ch != "w̃" else 40, CONS_EVID, tier)})
    for ch, fam, desc, ipa, modern, ev in MARGINAL:
        recs.append({"id": f"phon:aka:M-{ch}", "type": "consonant-marginal", "christaller": ch, "family": fam,
                     "sound_desc": desc, "ipa": ipa, "modern_twi": modern, "mapping_tier": "reconciled",
                     "provenance": prov("Part I ch.1 §13-15", 39, ev, "sourced")})
    for name, mark, figure, desc, ev in TONES:
        recs.append({"id": f"phon:aka:T-{name}", "type": "tone", "tone": name, "mark": mark, "figure": figure,
                     "sound_desc": desc, "mapping_tier": "sourced",
                     "provenance": prov("Part I ch.2 §25", 47, ev)})
    for name, mark, desc, ev in CONTOURS:
        recs.append({"id": f"phon:aka:T-{name}", "type": "tone-contour", "tone": name, "mark": mark,
                     "sound_desc": desc, "mapping_tier": "sourced",
                     "provenance": prov("Part I ch.2 §25.6", 47, ev)})

    with OUT.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    n = lambda t: sum(1 for r in recs if r["type"] == t)
    print(f"wrote {len(recs)} records: {n('vowel')} vowels, {n('consonant')} consonants, "
          f"{n('consonant-marginal')} marginal, {n('tone')} tones, {n('tone-contour')} contours, {n('diacritic')} diacritics")


if __name__ == "__main__":
    main()
