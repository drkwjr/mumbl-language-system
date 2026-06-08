#!/usr/bin/env python3
"""Construct-and-verify brain (text prototype).

The whole low-resource thesis in one file: an LLM that can't reliably speak Twi produces a believable
Twi reply *because it is grounded in the bank and verified against it* — not trusted to freelance.

  retrieve : pull verified phrases for the scene from the bank (serve.py)
  generate : an LLM composes a short reply, told to use the verified phrases/words
  verify   : every Twi token is checked against the bank's known-word set; unknown tokens are flagged
             (a real system repairs/regenerates; here we report so the contrast is visible)

`demo` runs one market turn TWO ways — grounded vs. unconstrained freelance — and shows the
verification gap. Needs OPENAI_API_KEY in the environment.

  set -a; source ../mumbl-server/.env; set +a   # or export OPENAI_API_KEY
  python3 bank/brain.py demo
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from serve import Bank  # noqa: E402

MODEL = os.environ.get("BRAIN_MODEL", "gpt-4o-mini")
WORD_RE = re.compile(r"[a-zA-Zɛɔŋæ'’-]+", re.UNICODE)


def chat(system: str, user: str) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY not set (source ../mumbl-server/.env)")
    body = json.dumps(
        {
            "model": MODEL,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.5,
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    res = json.loads(urllib.request.urlopen(req, timeout=40).read())
    return json.loads(res["choices"][0]["message"]["content"])


def verify(bank: Bank, twi: str) -> dict:
    import morphophon as mp  # morphophonology-aware: decomposes agglutinated forms before rejecting

    toks = [t for t in WORD_RE.findall(twi.lower()) if t]
    res = [(t, mp.is_known_morph(bank, t, bank.pkey_index)) for t in toks]
    known = [t for t, r in res if r["known"]]
    unknown = [t for t, r in res if not r["known"]]
    via_morph = [t for t, r in res if r.get("how") == "morph"]
    rate = round(100 * len(known) / len(toks)) if toks else 0
    return {"tokens": len(toks), "verified": len(known), "unknown": unknown, "via_morph": via_morph, "rate_pct": rate}


def grounded_reply(bank: Bank, persona: str, topics, learner: str) -> dict:
    # ground on the WHOLE bank (phrases + course gloss-pairs + dictionaries), retrieved by relevance to
    # this turn — not just topic-filtered phrases. More sourced material = more the model can say safely.
    pool = bank.grounding(learner + " " + " ".join(topics), k=40)
    menu = "\n".join(f"- {p['twi']}  ({p['en']})" for p in pool)
    system = (
        f"You are {persona}, speaking Twi (Akan) with a beginner learner. Reply IN TWI, ONE short "
        "sentence. Use ONLY real, attested Twi — prefer the sourced words/phrases below; do not invent "
        'words. Output JSON: {"twi": "...", "gloss_en": "..."}.'
    )
    user = f"Sourced Twi material you may use:\n{menu}\n\nThe learner said: {learner}\nReply now."
    return chat(system, user)


def freelance_reply(persona: str, learner: str) -> dict:
    system = (
        f"You are {persona}, speaking Twi (Akan) with a learner. Reply IN TWI, one short sentence. "
        'Output JSON: {"twi": "...", "gloss_en": "..."}.'
    )
    return chat(system, f"The learner said: {learner}\nReply now.")


def demo() -> None:
    bank = Bank()
    persona = "Akua, a friendly market vendor"
    topics = ["Shopping", "Money", "Numbers", "Basics"]
    learner = "Mepɛ nsuo. (I want water.)"

    print(f"scene: market · {persona}\nlearner: {learner}\n")

    g = grounded_reply(bank, persona, topics, learner)
    gv = verify(bank, g["twi"])
    print("GROUNDED (construct-and-verify):")
    print(f'  twi : {g["twi"]}')
    print(f'  en  : {g["gloss_en"]}')
    print(f'  verify: {gv["verified"]}/{gv["tokens"]} words known ({gv["rate_pct"]}%)  unknown={gv["unknown"]}\n')

    f = freelance_reply(persona, learner)
    fv = verify(bank, f["twi"])
    print("FREELANCE (unconstrained LLM Twi):")
    print(f'  twi : {f["twi"]}')
    print(f'  en  : {f["gloss_en"]}')
    print(f'  verify: {fv["verified"]}/{fv["tokens"]} words known ({fv["rate_pct"]}%)  unknown={fv["unknown"]}')


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "demo":
        demo()
    else:
        print(__doc__)
