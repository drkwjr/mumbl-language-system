# Language Construction — Status & What's Left

Snapshot of the construct-and-verify language bank: where it stands and the open work. See `LANGUAGES.md`
(how to add a language), `YOUTUBE_FETCH.md` (fetch doctrine), `SCALING.md` (engine transfer).

## Where it stands (working)

- **Bank**: ~77.9k known words · ~20.6k sourced glosses · dictionaries (Christaller, kasahorow, FSI,
  LearnAkan) · phonemes/G2P (Akuapem + Asante) · morphology decomposer · grammar paradigm.
- **Construction / syntax layer** (new): ~11.7k attested word-bigrams + ~240 grammatical-class transitions.
  Generation grounds on it (assembles the Twi way, not calqued English) and the reply is verified on two
  axes — words attested (`bankVerify`) and assembled-like-Twi (`bankStructural`, smoothed).
- **Harvest pipeline**: wide discovery (996 channels, dialect-tagged) → residential-proxy audio+ASR
  (checkpointed, resumable) → corroboration → construction mining. Corpus ~1,000 spoken clips and counting.
- **Portfolio tooling**: dialect tagger, multi-language seed capture, and a per-language **readiness map**
  (Twi = 100%).
- **App**: bank wired into `mumbl-server` (sourced glosses, grounded+verified replies, mms-tts-aka voice).

## What's left (prioritized)

1. **Finish the full corpus pull — PINNED.** Blocked: the IPRoyal proxy ran out of credit (402) mid-run;
   Vultr datacenter IPs are bot-walled (confirmed, all yt-dlp clients). Resume needs an IPRoyal top-up or
   another residential route. Unlocks: dialect diversity (Fante/Bono channels weren't reached), more
   mid-range construction coverage, and clean multi-language seeds. → *ticket: resume full harvest.*

2. **Structural metric → hard gate.** Today it's a reported signal (class-backoff is too coarse to catch
   scrambling). It sharpens two ways: more corpus (watch `exactPct` climb) and/or a smarter model
   (trigrams / function-word placement). The product payoff is a **verify-and-repair loop** — regenerate
   the reply when the word OR structure axis is low, instead of just reporting it.

3. **Meaning sourcing for discoveries (the rule reconciliation).** `promote.py` currently graduates words
   with a *Gemini-proposed* gloss — which conflicts with the hard rule "never invent a definition." Fix:
   graduate **attestation** (corroborated = real Twi) but route **meaning** to a native-review queue, not
   an LLM guess. This is the honest unblock for vocabulary growth.

4. **Native-review contributor experience.** The platform feature where native speakers verify/gloss the
   unknown queue (slang, new forms). It's the *source* of meaning for everything dictionaries lack. Not
   built — and it's the dependency for #3.

5. **Second-language onboarding.** The readiness map + `LANGUAGES.md` recipe make this a process: pick a
   language, seed the stack (lexicon, language_id, morphology, queries, TTS), run the pipeline. This is the
   repeatable business motion. (Somali spike on the backlog.)

6. **Custom TTS voice.** mms-tts-aka is the demo voice; the real one is a bake-off (Orpheus/CosyVoice/
   Chatterbox) on rights-clean data — post-sprint, needs a GPU.

7. **Serving layer.** Postgres + pgvector eventually; the JSON export bridge works for now.

## The shape of the work

Construction (#2) and meaning-via-native-review (#3/#4) are the highest-leverage *quality* work — they make
the Twi sound native and keep meaning honest. The full pull (#1) is *quantity* — pinned, resumes on one
command once a proxy is funded. Onboarding (#5) is where this becomes a repeatable product line.
