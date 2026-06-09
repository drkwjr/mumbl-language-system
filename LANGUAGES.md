# Adding a Language

This system is a **construct-and-verify language bank**: it learns a low-resource language from real
attested material (dictionaries, phrasebooks, lyrics, and — at scale — spoken transcripts), then grounds
and verifies generation against that material so the app never hallucinates words or word order. Twi
(Akan) is the first language; the loop is deliberately language-agnostic.

This doc is the recipe for pointing it at a new language (Somali, Yoruba, Ga, …).

---

## What generalizes for free (the engine)

These need **no per-language code** — they operate on whatever the bank contains:

| Stage | File | What it does |
|---|---|---|
| Wide discovery | `bank/ingest/discover_wide.py` | Finds creators via search metadata (no downloads → no throttle) |
| Background harvest | `bank/ingest/harvest_pool.py` | Checkpointed, resumable, proxy-aware download+ASR at scale |
| ASR | `media_discover.transcribe` | Gemini speech→text (cheap, ~$0.001/clip) |
| Corroboration | `media_discover` | A real word recurs across clips; ASR noise appears once |
| Construction mining | `bank/ingest/construction_miner.py` | Learns word order: exact bigrams + grammatical-class transitions |
| Structural metric | `mumbl-server bank.ts` `bankStructural` | "Is this assembled like the language?" (exact + class backoff) |
| Word verification | `bank.ts` `bankVerify` | "Is every word attested?" (with morphology) |
| App serving | `bank/export_for_app.py` → `bank.ts` | Flattens the bank to JSON the brain loads |

So: discovery, harvesting, transcription, corroboration, syntax mining, both verification axes, and the
serving bridge are reusable as-is.

---

## What is language-specific (the swap list)

Seven things carry language knowledge. To add language `X`:

1. **A starter lexicon** → `bank/data/<X>/` and `bank/corpus/<X>/`.
   The cold-start seed: a dictionary, a phrasebook (Wikivoyage/FSI), anything attested. This is what
   `language_id` checks membership against and what generation grounds on. Bigger seed = fewer
   false "unknowns" early. (Twi used Christaller/kasahorow dictionaries + Wikivoyage + FSI.)

2. **Language ID** → `bank/language_id.py`.
   `membership(token)` must know `X`'s lexicon + orthography (special characters). This is how the
   harvest tells `X` from English from noise. Orthography rules catch words the lexicon hasn't seen yet.

3. **Morphology** → `bank/morphophon.py` (+ the port in `bank.ts`).
   The decomposer: subject/TAM prefixes, elision, vowel harmony, negation — whatever `X` does. This is
   what lets inflected forms count as attested instead of flagged unknown. The single most impactful
   per-language file for verification quality. Conservative by design (root must be known → no false
   positives), so a partial ruleset is safe.

4. **Dialect markers** → `bank/ingest/dialect_tag.py` `MARKERS`.
   High-precision forms that separate `X`'s dialects in text. Optional; only if `X` has a dialect
   continuum worth routing. Heuristic, pending native review — never asserted as ground truth.

5. **Discovery queries** → `discover_wide.py` `DIALECTS` / `GENRES`.
   The search terms that surface `X` creators, crossed with conversational genres. Genres mostly carry
   over; the dialect/language terms are what you swap.

6. **The ASR prompt** → `media_discover.transcribe`.
   "This is spoken `X`. Transcribe verbatim, preserving <special chars>." Tells Gemini which language and
   which orthography to honor.

7. **TTS voice** → `mumbl-server services/*_tts.py` + `tts.ts` routing.
   A rights-clean voice for `X`. Twi uses Meta `mms-tts-aka` (MMS covers ~1100 languages, so many `X`
   start here). Custom-voice training is a separate, optional upgrade. `bank.ts` `bankActiveFor` routes
   the language by name.

Plus the small morphology constants in `bank.ts` (`SUBJECTS`, `TAM`, `NEG`, `FUNCTION`) — the TS mirror of
`morphophon.py` for in-app verification.

---

## The order of operations

```
1. Seed     drop a dictionary/phrasebook into bank/data/<X>/ ; wire language_id membership
2. Discover python3 bank/ingest/discover_wide.py            # build the channel pool
3. Harvest  python3 bank/ingest/harvest_pool.py             # fill the transcript corpus (background)
4. Mine     python3 bank/ingest/construction_miner.py       # learn the words + the word order
5. Export   python3 bank/export_for_app.py                  # ship it to the app
6. Verify   (app) bankVerify + bankStructural now light up for <X>
7. Voice    wire an mms-tts-<X> sidecar + tts.ts routing
8. Dialect  (optional) add dialect_tag.py markers if <X> has dialects
```

Steps 2–6 are the reusable engine. Steps 1, 7, and the markers in 3/4/8 are the per-language work — a
seed lexicon, a voice, and (if relevant) dialect markers. Everything else is free.

---

## The honest constraints (same for every language)

- **Download is the wall, not ASR.** YouTube throttles per IP. Scale needs multiple IPs — a rotating
  residential proxy (`HARVEST_PROXY`) now, a Vultr fleet (cheaper bandwidth) for truly massive volume.
- **ASR is noisy.** Corroboration (freq ≥ 2) is the noise filter; it needs *volume* to work, which is
  why the corpus has to be large. More transcript is the highest-leverage lever for a new language.
- **Never invent meaning.** A word is sourced (from a dictionary/root-gloss) or it's an honest unknown
  queued for native review. Attestation (is it real?) and meaning (what does it mean?) are separate axes.
- **Dialects split cleanly only sometimes.** Where the difference is lexical (Fante vs Twi) text can tell;
  where it's phonetic (Asante vs Akuapem) ASR text cannot. Be explicit about which.
