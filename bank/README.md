# Language Bank (data-as-code)

The **right half** of `mumbl-language-system`: the structured, queryable knowledge bank the
construct-and-verify brain pulls from — lexicon + concept layer + relation graph + (later) phrase
bank + grammar rules. The left half (acquisition / curation / training: `text_segments`,
`audio_segments`, `segment_scores`, `datasets`, `model_registry`) already lives in `infra/db` +
`apps/`. The two connect at the corpus: scored, learner-eligible segments feed this bank.

Design docs (vault): `Reference/SideProjects/Mumbl/language-build-pipeline.md` (acquisition) and
`language-bank-architecture.md` (storage / verification / serving + the relation taxonomy).

## Why data-as-code

The curated layers are the moat and are small enough to version in git — diffable, provenance-in-
history, reproducible. They build/sync into Postgres + pgvector (this repo's DB) for runtime
structured lookup + RAG retrieval. Git = source of truth; Postgres = serving copy.

## Layout

```
bank/
├── sources/          raw downloaded sources + <id>.source.json provenance records
├── ingest/           reusable, idempotent ingest scripts (raw → data-as-code)
├── data/<lang>/       the curated bank, one dir per language (ISO 639-3, e.g. aka = Akan/Twi)
│   ├── lexicon.jsonl     lexical entries (lemma / pos / forms / senses / bilingual examples)
│   ├── concepts.jsonl    the concept layer (language-agnostic meanings)
│   └── relations.jsonl   typed edges (synonym, ... )
└── schema/           JSON-Schema contracts for the records
```

## Data model (OntoLex-Lemon-ish)

- **Lexical entry** → `forms` (written/inflected) → `senses` (gloss + examples), each sense points to a **concept**.
- **Concept** = a language-agnostic meaning. Two senses on the same concept = **synonyms** (within a language) or **translations** (across languages). The cross-language backbone (§10 of the architecture spec covers the full relation taxonomy).
- **Relation** = a typed edge (synonym, antonym, hypernym, derivation, dialect-variant, collocation, ...).
- **Provenance + verification tier** on every record: `unverified` (raw ingest) → `auto` (heuristic / cross-source) → `native-verified` (the gold). Generation only voices `auto`/`native-verified`.

## Status — Phase 1 (Akan/Twi, text-only)

**Lexicon** — kasahorow English-Akan wordlist (BSD-2): **3,231 entries · 2,904 concepts · 349 synonym sets · 3,209 with bilingual examples.** The concept layer is **first-pass, gloss-derived** (two Akan words sharing an English gloss → shared concept), so concepts + synonym edges are tagged `auto-gloss` — candidates for the verify-not-trust pipeline, not ground truth.

**Phrase bank** — Wikivoyage Twi phrasebook (CC-BY-SA): **308 phrases** tagged by topic/scenario (Eating, Basics, Numbers, Shopping, Directions, Money, ...) with register + pronunciation hints, `unverified` tier.

```
python3 bank/ingest/kasahorow_to_lexicon.py     # lexicon + concepts + relations
python3 bank/ingest/wikivoyage_to_phrases.py    # phrase bank
```

## Next

Grammar rules (from a sourced reference — not hand-written from memory); more phrase/corpus sources; native verification of the `auto`/`unverified` tiers; then the build/sync into Postgres + pgvector and the construct-and-verify brain that queries it.
