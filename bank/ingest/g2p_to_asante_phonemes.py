#!/usr/bin/env python3
"""Asante-Twi sound key (phonemes-asante.jsonl) from the GhanaNLP twi-g2p phone tables.

Closes the Asante phoneme gap with an Asante-ATTESTED, permissive source: twi-g2p is MIT-licensed and
explicitly an "Asante-Twi Grapheme-to-Phoneme Converter", grounded in the primary paper
  Cho et al., "A phone set of Asante-Twi defined in IPA and X-SAMPA" (Microsoft LDC / University of Ghana).
It also encodes the ATR vowel-harmony pairs (i/ɩ, e/ɛ, æ/a, o/ɔ, u/ʊ), so this doubles as the §17 layer.

Distinct from phonemes.jsonl, which is the Akuapem (Christaller) sound key in 19th-c. Lepsius orthography.
This one is modern Akan Unified Orthography — what the app actually renders.

  /tmp/ytenv/bin/python bank/ingest/g2p_to_asante_phonemes.py   (needs twi-g2p installed)
"""
import json
from pathlib import Path

import twi_g2p.phoneme_rules as pr

OUT = Path(__file__).resolve().parents[1] / "data" / "aka" / "phonemes-asante.jsonl"
ATR_MARK = "̘"  # combining advanced tongue root (+ATR)
HARMONY = {"i": "ɩ", "e": "ɛ", "æ": "a", "o": "ɔ", "u": "ʊ"}
PAIR = {**HARMONY, **{v: k for k, v in HARMONY.items()}}


def prov():
    return {
        "source": "twi-g2p",
        "citation": "Cho et al., 'A phone set of Asante-Twi defined in IPA and X-SAMPA' (Microsoft LDC / University of Ghana)",
        "repo": "https://github.com/GhanaNLP/twi-g2p",
        "license": "MIT",
        "method": "phone-table-extract",
        "verification": "sourced",
    }


def main():
    recs = []
    for g, ipa in pr.VOWEL_IPA.items():
        atr = "+ATR" if ATR_MARK in ipa else "-ATR"
        recs.append({"id": f"phon:aka-asante:V-{g}", "type": "vowel", "grapheme": g, "ipa": ipa,
                     "xsampa": pr.VOWEL_XSAMPA.get(g), "atr": atr, "harmony_pair": PAIR.get(g),
                     "modern_twi": g, **{"provenance": prov()}})
    for g, ipa in pr.CONSONANT_IPA.items():
        recs.append({"id": f"phon:aka-asante:C-{g}", "type": "consonant", "grapheme": g, "ipa": ipa,
                     "xsampa": pr.CONSONANT_XSAMPA.get(g), "modern_twi": g, "provenance": prov()})
    for g, ipa in pr.DIGRAPH_IPA.items():
        kind = "palatalized" if "ʲ" in ipa else "labialized" if "ʷ" in ipa else "nasal-cluster"
        recs.append({"id": f"phon:aka-asante:D-{g}", "type": "digraph", "subtype": kind, "grapheme": g,
                     "ipa": ipa, "xsampa": pr.DIGRAPH_XSAMPA.get(g), "modern_twi": g, "provenance": prov()})
    tone_name = {"_H": "high", "_L": "low", "_R": "rising"}
    for mark, tag in pr.TONE_MARKS_IPA.items():
        recs.append({"id": f"phon:aka-asante:T-{tone_name[tag]}", "type": "tone", "tone": tone_name[tag],
                     "combining": f"U+{ord(mark):04X}", "provenance": prov()})

    for r in recs:
        r["dialect"] = "aka-asante"
        r["dialect_status"] = "attested"

    with OUT.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    nv = sum(1 for r in recs if r["type"] == "vowel")
    print(f"wrote {len(recs)} Asante phoneme records ({nv} vowels w/ ATR, "
          f"{sum(1 for r in recs if r['type']=='consonant')} consonants, "
          f"{sum(1 for r in recs if r['type']=='digraph')} digraphs, "
          f"{sum(1 for r in recs if r['type']=='tone')} tones)")


if __name__ == "__main__":
    main()
