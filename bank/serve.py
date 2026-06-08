#!/usr/bin/env python3
"""File-based query layer over the data-as-code language bank.

Makes the bank a usable knowledge base for the construct-and-verify brain — without Postgres yet
(the same queries move to Postgres + pgvector later). Loads the JSONL layers and answers the
questions generation/verification actually need:

    lookup(word)        -> entries (gloss, pos, examples)
    ways_to_say(en)     -> Twi words for an English meaning (synonyms surface here)
    synonyms(word)      -> other words sharing a concept
    phrases(topic)      -> verified phrases for a scenario
    is_known(word)      -> the verifier check (in the 59k wordforms / lexicon) + frequency rank

    python3 bank/serve.py demo            # illustrative queries against the loaded bank
    python3 bank/serve.py lookup me       # ad-hoc
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "aka"


def _load(name):
    p = DATA / name
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


class Bank:
    def __init__(self) -> None:
        self.entries = _load("lexicon.jsonl")
        self.concepts = {c["id"]: c for c in _load("concepts.jsonl")}
        self.phrases_all = _load("phrases.jsonl")
        wf = _load("wordforms.jsonl")

        # phoneme-key -> spelling variants (built by ingest/build_variants.py); lets the verifier
        # accept a known word's variant spelling (nsuo for nsu) without re-running G2P at query time.
        self.pkey_index = {v["pkey"]: v["spellings"] for v in _load("variants.jsonl")}

        # grapheme -> sound key (Christaller §1-4, vision-recovered): the orthography->phoneme map.
        self.phonemes = _load("phonemes.jsonl")

        # sourced grammar paradigms (Christaller §54-56, §90-91): pronoun + TAM affix tables.
        self.grammar = _load("grammar.jsonl")

        self.by_lemma = defaultdict(list)
        self.by_gloss = defaultdict(list)
        for e in self.entries:
            self.by_lemma[e["lemma"].lower()].append(e)
            for s in e["senses"]:
                self.by_gloss[s["gloss_en"].strip().lower()].append((e, s))

        # sense_id -> entry, and concept -> entries
        self.entry_of_sense = {s["id"]: e for e in self.entries for s in e["senses"]}
        self.concept_entries = defaultdict(list)
        for e in self.entries:
            for s in e["senses"]:
                self.concept_entries[s["concept"]].append(e)

        self.known = {e["lemma"].lower() for e in self.entries} | {w["word"].lower() for w in wf}
        self.freq_rank = {w["word"].lower(): w["rank"] for w in wf}

    def lookup(self, word):
        return self.by_lemma.get(word.strip().lower(), [])

    def ways_to_say(self, english):
        return [e["lemma"] for e, _ in self.by_gloss.get(english.strip().lower(), [])]

    def synonyms(self, word):
        out, seen = [], {word.lower()}
        for e in self.lookup(word):
            for s in e["senses"]:
                for other in self.concept_entries.get(s["concept"], []):
                    if other["lemma"].lower() not in seen:
                        seen.add(other["lemma"].lower())
                        out.append((other["lemma"], s["concept"].replace("concept:", "")))
        return out

    def phrases(self, topic):
        t = topic.strip().lower()
        return [p for p in self.phrases_all if (p.get("topic") or "").lower() == t]

    def is_known(self, word):
        w = word.strip().lower()
        return {"known": w in self.known, "freq_rank": self.freq_rank.get(w)}


def demo(b: Bank) -> None:
    print(f"loaded: {len(b.entries)} entries · {len(b.concepts)} concepts · {len(b.phrases_all)} phrases · {len(b.known)} known words\n")

    print('ways_to_say("water"):', b.ways_to_say("water"))
    print('ways_to_say("buy"):  ', b.ways_to_say("buy"))
    print()

    # pick a word that has synonyms to show the relation graph working
    sample = next((e["lemma"] for e in b.entries if len(b.synonyms(e["lemma"])) >= 2), b.entries[0]["lemma"])
    print(f'synonyms("{sample}"):', b.synonyms(sample)[:6])
    print()

    e = b.lookup(sample)[0]
    g = e["senses"][0]
    print(f'lookup("{sample}"): {g["gloss_en"]} [{e["pos"]}]  e.g. "{(g["examples"] or [{}])[0].get("aka","")}" = "{(g["examples"] or [{}])[0].get("en","")}"')
    print()

    print("verifier — is_known:")
    for w in ["nsu", "me", "xqz-not-a-word", "manzana"]:
        print(f'  {w:18} {b.is_known(w)}')
    print()

    print('phrases(topic="Shopping") [first 4]:')
    for p in b.phrases("Shopping")[:4]:
        print(f'  {p["text_en"]}  ->  {p["text_aka"]}')


def main() -> None:
    b = Bank()
    if len(sys.argv) >= 2 and sys.argv[1] == "demo":
        demo(b)
    elif len(sys.argv) >= 3 and sys.argv[1] == "lookup":
        for e in b.lookup(sys.argv[2]):
            print(json.dumps(e, ensure_ascii=False, indent=2))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
