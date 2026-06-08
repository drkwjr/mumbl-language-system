#!/usr/bin/env python3
"""Proof that the language bank works — exercises every layer with assertions and prints evidence.

Offline (no API): meaning/translation, the verifier, morphophonology, the sound key, dialect views.
The construct-and-verify *generation* proof is separate (bank/brain.py demo, needs OPENAI_API_KEY),
since only generation calls a model — everything the bank itself does is deterministic and testable here.

  /tmp/ytenv/bin/python bank/selftest.py     (needs twi-g2p for morphology/pronunciation)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serve import Bank  # noqa: E402
import morphophon as mp  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, evidence=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  →  {evidence}" if evidence else ""))


def main():
    b = Bank()

    print("\n1. LAYERS LOADED")
    check("lexicon", len(b.entries) > 3000, f"{len(b.entries)} entries")
    check("wordforms (verifier set)", len(b.known) > 50000, f"{len(b.known)} known words")
    check("concepts (meaning backbone)", len(b.concepts) > 2000, f"{len(b.concepts)} concepts")
    check("phonemes (both dialects)", len(b.phonemes) > 80, f"{len(b.phonemes)} ({sum(1 for p in b.phonemes if p.get('dialect')=='aka-asante')} Asante / {sum(1 for p in b.phonemes if p.get('dialect')=='aka-akuapem')} Akuapem)")
    check("grammar paradigms", len(b.grammar) >= 5, f"{len(b.grammar)} sourced")
    check("variety registry", len(b.varieties) >= 5, ", ".join(v["code"] for v in b.varieties))

    print("\n2. MEANING → FORM (translation backbone)")
    water = b.ways_to_say("water")
    check("ways_to_say('water')", any("nsu" in w for w in water), str(water))
    buy = b.ways_to_say("buy")
    check("ways_to_say('buy')", len(buy) > 0, str(buy[:5]))

    print("\n3. VERIFIER (is this real Twi?)")
    check("real word 'nsu' passes", b.is_known("nsu")["known"], "known=True")
    check("real word 'medaase' passes", b.is_known("medaase")["known"])
    check("nonsense 'xqzfake' rejected", not b.is_known("xqzfake")["known"], "known=False")
    check("Spanish 'manzana' rejected", not b.is_known("manzana")["known"])
    check("Ewe 'akpe' rejected (not Twi)", not b.is_known("akpe")["known"], "the leak the brain caught earlier")

    print("\n4. MORPHOPHONOLOGY (agglutinated forms decompose to known roots)")
    for w, exp in [("yɛbɛma", "ma"), ("wɔbɛba", "ba"), ("ɔrekɔ", "kɔ"), ("metɔ", "tɔ")]:
        r = mp.is_known_morph(b, w, b.pkey_index)
        # verifies if it decomposes to the expected root OR is now directly attested (a real word)
        ok = r["known"] and (r.get("root") == exp or r.get("how") == "direct")
        check(f"verify {w}", ok, f"{r.get('how')}: {'+'.join(r.get('affixes',[]))}+{r.get('root')}" if r.get("root") else r.get("how"))
    rf = mp.is_known_morph(b, "xbɛfake", b.pkey_index)
    check("fake agglutination rejected", not rf["known"], "xbɛfake → unknown")

    print("\n5. SOUND KEY (Asante grapheme → IPA, with ATR)")
    asante_v = {p["grapheme"]: p for p in b.phonemes if p.get("dialect") == "aka-asante" and p.get("type") == "vowel"}
    check("ɛ is -ATR", asante_v.get("ɛ", {}).get("atr") == "-ATR", asante_v.get("ɛ", {}).get("ipa"))
    check("e is +ATR (harmony pair of ɛ)", asante_v.get("e", {}).get("atr") == "+ATR", f"pair={asante_v.get('e',{}).get('harmony_pair')}")
    try:
        from twi_g2p import TwiG2P
        g = TwiG2P()
        check("pronounce 'nsuo'", bool(g.convert("nsuo")), g.convert("nsuo"))
        check("pronounce 'medaase'", bool(g.convert("medaase")), g.convert("medaase"))
    except Exception as e:
        check("twi-g2p pronunciation", False, f"twi-g2p not available: {e}")

    print("\n6. DIALECT VIEWS (Asante vs Akuapem are distinct)")
    asante_phon = [p for p in b.phonemes if p.get("dialect") == "aka-asante"]
    akuapem_phon = [p for p in b.phonemes if p.get("dialect") == "aka-akuapem"]
    check("Asante has its own phoneme layer", len(asante_phon) > 30, f"{len(asante_phon)} records (twi-g2p)")
    check("Akuapem has its own (Christaller)", len(akuapem_phon) > 30, f"{len(akuapem_phon)} records")
    check("grammar is shared (serves both)", all(g.get("dialect") == "shared" for g in b.grammar), "pan-Twi paradigm")

    n = len(PASS) + len(FAIL)
    print(f"\n{'='*60}\nRESULT: {len(PASS)}/{n} passed" + (f"  — FAILURES: {FAIL}" if FAIL else "  — ALL PASS ✓"))
    print("(generation proof: set OPENAI_API_KEY and run bank/brain.py demo + bank/variety_test.py)")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
