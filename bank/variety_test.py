#!/usr/bin/env python3
"""Variety probe — can grounded (construct-and-verify) Twi conversation come out VARIED rather than
canned, while staying verified? That is the whole tension: variety usually comes from letting the
model freelance, which is exactly what hallucinates on Twi. So we measure both at once.

  samples  : one scene + learner line, generated K times -> lexical variety AND verify rate, grounded
             vs. freelance side by side (does grounding cost us variety? does freelance cost us truth?)
  dialogue : a short multi-turn market exchange -> turn-to-turn variety inside one conversation

Run:  set -a; source ../mumbl-server/.env; set +a ; /tmp/ytenv/bin/python bank/variety_test.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brain import chat, freelance_reply, grounded_reply, verify  # noqa: E402
from serve import Bank  # noqa: E402

WORDS = re.compile(r"[a-zA-Zɛɔŋ'’-]+")


def toks(s):
    return [t for t in WORDS.findall(s.lower()) if t]


def measure(bank, replies):
    """Variety = distinct replies + type/token ratio over the pooled tokens; truth = mean verify rate."""
    distinct = len({r.strip().lower() for r in replies})
    pooled = [t for r in replies for t in toks(r)]
    ttr = round(len(set(pooled)) / len(pooled), 2) if pooled else 0.0
    vr = [verify(bank, r)["rate_pct"] for r in replies]
    return distinct, ttr, round(sum(vr) / len(vr)) if vr else 0


def samples_probe(bank, persona, topics, learner, k=4):
    print(f"scene: {persona}\nlearner: {learner}\n")
    grounded = [grounded_reply(bank, persona, topics, learner)["twi"] for _ in range(k)]
    free = [freelance_reply(persona, learner)["twi"] for _ in range(k)]

    gd, gt, gv = measure(bank, grounded)
    fd, ft, fv = measure(bank, free)

    print(f"GROUNDED  ({k} samples): {gd}/{k} distinct · type-token {gt} · verified {gv}%")
    for r in grounded:
        print(f"    {r}")
    print(f"FREELANCE ({k} samples): {fd}/{k} distinct · type-token {ft} · verified {fv}%")
    for r in free:
        print(f"    {r}")
    print()


def varied_grounded_probe(bank, persona, topics, learner, k=4):
    """The variety lever: same over-constrained scene, but hand the model a WIDER verified candidate set
    (synonyms + ways-to-say from the bank's relation graph) and ask it to vary phrasing each time.
    If distinct rises while verified stays high, the bank's relation layer is what buys variety-with-truth."""
    phrases = [p for t in topics for p in bank.phrases(t)]
    menu = "\n".join(f"- {p['text_aka']}  ({p['text_en']})" for p in phrases[:30])
    # pull verified synonyms for the scene's core concepts so the model has real room to vary
    syn_lines = []
    for en in ("water", "want", "have", "good", "money", "thanks"):
        ways = bank.ways_to_say(en)
        if ways:
            syn_lines.append(f"  {en}: {', '.join(dict.fromkeys(ways))}")
    syns = "\n".join(syn_lines)
    system = (
        f"You are {persona}, speaking Twi (Akan) with a beginner. Reply IN TWI, ONE short sentence, using "
        "ONLY real attested Twi from the verified material below. Each time, deliberately VARY your phrasing "
        '(different verified words/synonyms); do not repeat a previous reply. Output JSON: {"twi":"...","gloss_en":"..."}.'
    )
    seen = []
    replies = []
    for _ in range(k):
        avoid = (" Do NOT reuse: " + " / ".join(seen)) if seen else ""
        user = f"Verified phrases:\n{menu}\n\nVerified synonyms:\n{syns}\n\nLearner said: {learner}.{avoid}\nReply now, phrased differently."
        r = chat(system, user)["twi"]
        replies.append(r)
        seen.append(r)
    d, t, vr = measure(bank, replies)
    print(f"scene: {persona}\nlearner: {learner}\n")
    print(f"VARIED-GROUNDED ({k} samples): {d}/{k} distinct · type-token {t} · verified {vr}%")
    for r in replies:
        print(f"    {r}")
    print()


def dialogue_probe(bank, persona, topics, learner_lines):
    """One conversation: learner lines are fixed, the grounded vendor responds each turn. Show that the
    vendor's turns vary and stay verified across the exchange."""
    print(f"dialogue: {persona}\n")
    vendor = []
    for line in learner_lines:
        r = grounded_reply(bank, persona, topics, line)
        vendor.append(r["twi"])
        v = verify(bank, r["twi"])
        print(f"  learner: {line}")
        print(f"  vendor : {r['twi']}   ({r.get('gloss_en','')})  [{v['rate_pct']}% verified]")
    d, t, vr = measure(bank, vendor)
    print(f"\n  -> vendor turns: {d}/{len(vendor)} distinct · type-token {t} · verified {vr}%\n")


def main():
    bank = Bank()
    print("=" * 72)
    samples_probe(bank, "Akua, a friendly market vendor", ["Shopping", "Money", "Numbers", "Basics"], "Mepɛ nsuo. (I want water.)")
    print("=" * 72)
    varied_grounded_probe(bank, "Akua, a friendly market vendor", ["Shopping", "Money", "Numbers", "Basics"], "Mepɛ nsuo. (I want water.)")
    print("=" * 72)
    dialogue_probe(
        bank,
        "Akua, a friendly market vendor",
        ["Shopping", "Money", "Numbers", "Basics"],
        ["Maakye. (Good morning.)", "Mepɛ nsuo. (I want water.)", "Ɛyɛ sɛn? (How much?)", "Medaase. (Thank you.)"],
    )


if __name__ == "__main__":
    main()
