# Language Bank (data-as-code)

The **right half** of `mumbl-language-system`: the structured, queryable knowledge bank the
construct-and-verify brain pulls from — lexicon + concept layer + relation graph + (later) phrase
bank + grammar rules. The left half (acquisition / curation / training: `text_segments`,
`audio_segments`, `segment_scores`, `datasets`, `model_registry`) already lives in `infra/db` +
`apps/`. The two connect at the corpus: scored, learner-eligible segments feed this bank.

Design docs (vault): `Reference/SideProjects/Mumbl/language-build-pipeline.md` (acquisition) and
`language-bank-architecture.md` (storage / verification / serving + the relation taxonomy). For how
this engine scales to other languages (what transfers vs. what you swap), see [`SCALING.md`](SCALING.md).

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
│   ├── relations.jsonl   typed edges (synonym, ... )
│   ├── phrases.jsonl     verified scenario phrases
│   ├── wordforms.jsonl   frequency-ranked verifier coverage set
│   ├── variants.jsonl    spelling-variant groups clustered by phoneme key
│   └── phonemes.jsonl    grapheme -> sound key (orthography -> phoneme map)
└── schema/           JSON-Schema contracts for the records
```

## Data model (OntoLex-Lemon-ish)

- **Lexical entry** → `forms` (written/inflected) → `senses` (gloss + examples), each sense points to a **concept**.
- **Concept** = a language-agnostic meaning. Two senses on the same concept = **synonyms** (within a language) or **translations** (across languages). The cross-language backbone (§10 of the architecture spec covers the full relation taxonomy).
- **Relation** = a typed edge (synonym, antonym, hypernym, derivation, dialect-variant, collocation, ...).
- **Provenance + verification tier** on every record: `unverified` (raw ingest) → `auto` (heuristic / cross-source) → `native-verified` (the gold). Generation only voices `auto`/`native-verified`.

## Varieties (dialects) and coverage

Two independent axes live on every surface record:

- **content verification** — is it correct? `unverified → auto → sourced → native-verified`
- **dialect attribution** — which variety, and how sure? `attested` (the source marks it) · `attributed` (inferred from the source's general dialect) · `unspecified` (unknown → treated as shared)

**One Akan store, dialect-tagged.** The concept layer is meaning, so it carries no dialect — it's the shared backbone across Asante Twi, Akuapem Twi, and Fante. Surface layers (lexicon, phonemes, grammar, wordforms) carry a `dialect` tag (`bank/data/varieties.jsonl` is the registry). A **dialect view** = records tagged for that variety **plus** shared/unspecified ones; other varieties' dialect-specific records are excluded. That's why our Christaller-sourced (Akuapem) phonemes correctly read as MISSING for the Asante view.

**Know what we don't have.** `bank/coverage.py` generates the variety × layer matrix from the data (presence is always honest); `bank/data/coverage-overlay.json` adds the known-gap notes and the graded **audio-readiness** scale (`none → synthetic → sourced-rough → sourced-good → native-verified → native-recorded`) — audio readiness is tracked separately from text readiness, since a variety can be solid in text and silent in audio. A variety becomes a first-class product choice when its coverage crosses the bar; below it, it shows as preview.

```
python3 bank/coverage.py --json    # print the matrix + known gaps, write coverage.json
```

Current state: the sound/grammar layers are **Akuapem** (Christaller); the vocabulary leans **Asante**. The open gap is an Asante-attested phoneme + grammar source.

## Current state (2026-06-08) — the engine, end to end

A self-growing construct-and-verify engine for Asante Twi, built end to end.

**Vocabulary / meaning**
- Glossed dictionary entries: kasahorow 3.2k + Christaller dictionary 4.6k (vision OCR, Akuapem) + Kotey modern dictionary 2.1k (bilingual).
- **Glossed PAIRS from the courses** (structured-output extraction, the meaning side not bare words): FSI 1,996 (public-domain, committed) + Denteh 1,096 + Yeboa 1,366 (restricted, verifier-only). Conversational register — `Wo ho te sɛn? = How are you?`.
- **10,465 words carry a sourced gloss** — `serve.gloss()` glosses from the bank, not a model guess.
- **~68,800 words** in the verifier (wordforms + dictionaries + FSI + restricted learner books).
- 2,904 concepts — the shared, language-agnostic meaning backbone.

**Sound / grammar** — Asante phonemes (twi-g2p, ATR harmony) + Akuapem (Christaller); grammar paradigms + the `morphophon` decomposer; 6 dialect-tagged varieties.

**Pipeline** (catch → gloss → corroborate → grow): `serve.py` verifier · `morphophon.py` · `language_id.py` (evidence-based, multilingual membership) · `discover.py` (catch unknowns → gloss → stage) · `media_discover.py` (YouTube/radio → Gemini ASR → corroboration) · `discover_channels.py` + `verify_channels.py` (find + **multi-sample**-rank channels) · `pdf_ocr.py`/`iiif_page.py`/`vision_ocr.py` (vision re-OCR) · `structured_extract.py` (Gemini responseSchema → glossed PAIRS) · `coverage.py` · `selftest.py` (25/25).

**Sources:** Christaller grammar+dictionary, kasahorow, twi_words, Wikivoyage, twi-g2p, Kotey dictionary, FSI Twi Basic Course (public-domain), Denteh/Tie-Ma-Mense-Wo/1973-guide (restricted), Rattray folk-tales (cataloged).

**Verified-clean Asante channels** (multi-sampled): KMTV 84%, Mogyabi 94%, Akomapa 82%, SVTV 80%.

**Model / cost doctrine:** Gemini 2.5 Flash for OCR + ASR — ~30× cheaper than gpt-4o, faithful on special characters; ~$0.0003/page, ~$0.0013/min of audio; always `max_tokens`-capped + retry + graceful-skip on blocked responses.

**Licensing:** public-domain (FSI, Christaller, Rattray) may feed generation; copyrighted (Kotey, learner books) are verifier/gloss-reference only, local + gitignored.

## Status — Phase 1 (Akan/Twi, text-only)

**Lexicon** — kasahorow English-Akan wordlist (BSD-2): **3,231 entries · 2,904 concepts · 349 synonym sets · 3,209 with bilingual examples.** The concept layer is **first-pass, gloss-derived** (two Akan words sharing an English gloss → shared concept), so concepts + synonym edges are tagged `auto-gloss` — candidates for the verify-not-trust pipeline, not ground truth.

**Phrase bank** — Wikivoyage Twi phrasebook (CC-BY-SA): **308 phrases** tagged by topic/scenario (Eating, Basics, Numbers, Shopping, Directions, Money, ...) with register + pronunciation hints, `unverified` tier.

**Wordforms** — michsethowusu/twi_words: **59,563 frequency-ranked words** — the verifier's "is this a real Twi word" coverage set + curriculum sequencing (distinct from the glossed lexicon).

```
python3 bank/ingest/kasahorow_to_lexicon.py     # lexicon + concepts + relations
python3 bank/ingest/wikivoyage_to_phrases.py    # phrase bank
python3 bank/ingest/twi_words_to_wordforms.py   # 59k verifier wordlist + frequency
python3 bank/serve.py demo                       # query the bank: lookup / ways_to_say / synonyms / is_known / phrases
```

`serve.py` is the file-based query layer — the construct-and-verify brain's interface to the bank
(translate a meaning, surface synonyms, verify a word is real Twi, retrieve scenario phrases). The
same queries move to Postgres + pgvector later; the API stays the same.

**Phonemes / sound key** — Christaller's *Grammar of the Asante and Fante Language* (1875, public domain): the 10-vowel inventory + nasal/length diacritics + ŋ, with sound descriptions and a reconciled IPA / modern-orthography mapping (`phonemes.jsonl`, `sourced`). This is the orthography→phoneme foundation — **the characters are the sound**, so getting them right is prerequisite to any G2P/pronunciation/TTS.

### Scanned sources: vision re-OCR, not djvu.txt (cross-language doctrine)

archive.org's `<id>_djvu.txt` is OCR'd by an engine with no model for phonetic orthography, so for any low-resource-language source it **silently flattens the special characters that carry the sound** (`ɛ→e`, `ɔ→o`, drops `ŋ`, removes nasal/length/tone diacritics). Verified on Christaller: the alphabet line `a (ạ) b d e̱ e (ẹ) f g h i k (l) m n ṅ o̱ o (ọ) p r s t u w w̃ y` came through djvu as bare ASCII. **Never trust djvu.txt for orthography or sound** — use it for English prose and section structure only.

The fix (reusable for every scanned source, every language): pull the page image via IIIF and re-read it with a vision model that is told the orthography. `bank/ingest/iiif_page.py` is the image side; transcription is done by a vision pass (Claude in-session for high-value pages, or a vision-OCR call at scale). Leaf↔page mapping via `<id>_scandata.xml`.

```
python3 bank/ingest/iiif_page.py <archive_id> <leaf|range> [x,y,w,h]   # fetch page / zoom a line
```

## Next

The books are done — all four (FSI, Kotey, Denteh, Yeboa) mined for glossed PAIRS. Open workstreams (Linear, Mumbl project):

- **Scale + clean the harvest** (ANO-1696 / ANO-1697): more clips/channels; a NER filter (proper-noun leakage like NPP/SVTV still corroborates).
- **Promotion loop** (ANO-1695): a corroborated word with a stable gloss graduates into the bank with a verification tier.
- **New source veins** (ANO-1698): song lyrics (rich but figurative register), more verified channels.
- **Serving + verification** (ANO-1699 / ANO-1700): build/sync into Postgres + pgvector; native verification of the `auto`/`unverified` tiers.
