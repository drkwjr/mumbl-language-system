# Scaling the engine to other languages

The bank is built for Twi first, but almost none of it is *about* Twi. This is the note on what
transfers, what doesn't, and what it actually costs to add a language.

## The thesis (why this scales at all)

The hard problem in low-resource language tech: LLMs hallucinate fluently in languages they barely
know, and there isn't enough clean data to fine-tune the hallucination out. The usual answers — collect
a giant parallel corpus, train a model — are slow, expensive, and still leave you trusting the model.

We sidestep the ML problem entirely. **We don't trust the model to *know* the language; we make it
*retrieve* from a verified bank and *verify* its output against it** (`brain.py`). That turns the
bottleneck from "train a model" into "build a verified bank" — a **data-acquisition** problem, not a
research problem. And data acquisition is exactly what we've industrialized into cheap, repeatable
pipelines (Gemini Flash OCR/ASR at roughly $0.50 per book or per harvest run).

So the bank's **size becomes the product**, and the acquisition pipelines make growing it cheap. That
is the whole game, and it is language-agnostic.

## The flywheel

```
more sources ─▶ bigger verified bank ─▶ better grounding for generation
     ▲                                            │
     │                                            ▼
target acquisition ◀─ catch-unknowns surfaces ◀─ run it on real speech
   where it's thin      what the bank is missing
```

The verifier is what lets the loop tolerate **noisy** sources. We can point ASR at YouTube and keep
only what corroborates across clips (`harvest.py` / `media_discover.py`), because the known-word set +
document-frequency filter throw out the mishearings. That is what makes it possible to grow into a
language whose only real "corpus" is people talking on video.

## What transfers vs. what you swap

**Language-agnostic — the engine (~90% of the value, already built):**

| Piece | File(s) |
|---|---|
| Data model: lexicon / concept / relation / phrase / wordform / phoneme / variant layers | `data/<iso>/`, `schema/` |
| Query + verifier layer (known-set + frequency + sourced gloss) | `serve.py` |
| Morphophonology decomposer (accept agglutinated/variant forms) | `morphophon.py` |
| Evidence-based, **multilingual** language ID (a token can belong to a *set* of languages) | `language_id.py` |
| Vision re-OCR of scanned sources (faithful to any orthography you describe) | `iiif_page.py`, `pdf_ocr.py`, `vision_ocr.py` |
| Structured glossed-pair extraction from bilingual books (Gemini `responseSchema`) | `structured_extract.py` |
| Media discovery → ASR → corroboration; multi-sample channel verification | `discover_channels.py`, `verify_channels.py`, `harvest.py` |
| Catch-unknowns → propose gloss → stage for review | `discover.py` |
| Construct-and-verify generation loop | `brain.py` |
| Coverage map (variety × layer), verification tiers, licensing discipline | `coverage.py`, README |

**Language-specific — what you actually swap in (~10%):**

- **Seed lexicon**: one public-domain dictionary (the Christaller-equivalent — vision re-OCR it) plus a
  modern bilingual wordlist.
- **Orthographic signals** for `language_id`: the characters/tones that mark the language
  (Twi = `ɛ ɔ ŋ`; Yoruba = `ẹ ọ ṣ` + tone; etc.). One dict entry.
- **A sound key**: a G2P model (the `twi-g2p` equivalent) or a grammar that describes the phonology.
- **Dialect registry**: the varieties that matter and how they share.
- **Media channels**: the genuine native-speaker creators (the pipeline finds and verifies them).
- **Morphology rules**: the one genuinely bespoke piece — see limits.

## Honest limits (what does *not* auto-scale)

- **Morphology is real linguistic work.** Twi's prefix-heavy agglutinating verb won't transfer to an
  isolating tonal language or a Semitic root-and-pattern system. The decomposer needs per-language
  affix paradigms. Budget for this on every new language.
- **Orthography depth.** No standardized orthography (common in African languages) or a non-Latin
  script (Amharic, Tigrinya) adds OCR + normalization cost.
- **Native verification is a human bottleneck.** The engine gets you to `auto`/`sourced` cheaply, but
  the gold `native-verified` tier always needs speakers. That scales with people you recruit, not with
  compute.
- **Source availability varies.** Twi is lucky: a 19th-c. scholarly dictionary, an FSI course, an
  active YouTube. A truly tiny language may have none — then the engine is the storage/verification
  layer, not an acquisition accelerator, and you're doing fieldwork.

## Next-language playbook

1. Stand up `data/<iso>/` with the same layers; copy the schema.
2. Find seed sources: 1 public-domain dictionary (re-OCR), 1 modern bilingual wordlist, a phrasebook
   (Wikivoyage), a frequency list if one exists.
3. Add the orthographic signals to `language_id`.
4. Get a G2P or grammar for the sound key.
5. Point `discover_channels` → `verify_channels` → `harvest` at the language's creators.
6. Write the morphology decomposer for the language's structure. **(the real per-language cost)**
7. Run the selftest equivalent; ship the variety when coverage crosses the bar, preview below it.

Steps 1–5 are *run the pipeline*, not *build*. Step 6 is where the linguistics lives. That ratio —
mostly run, a little build — is the reason this scales.
