# Mumbl Language System — Roadmap (V1)

This roadmap is the execution guide for the scaffolded repo. Tasks are grouped by milestone and include acceptance checks. Mark items with `[x]` when complete.

## Final State (V1) — definition of done

- [ ] **Contracts frozen and validated**: `TextSegment`, `AudioSegment`, `SegmentScore`, `LanguageProfile` with a validator CLI and JSON Schemas.
- [ ] **Text lane live**: LangExtract schemas produce grounded `text_dialogue_corpus.jsonl` at scale with HTML spot-checks.
- [ ] **Audio lane live**: YouTube and file uploads, ASR + diarization, sentence or word alignment, normalized clips, `paired_speech_corpus.csv`.
- [ ] **Curator live**: scoring rubric, dedupe (exact + near), policy gates, thresholds for learner (≥90) and training (≥70), dataset snapshots with cards.
- [ ] **Profiles live**: LanguageProfile for 2 launch languages, one dialect each, with G2P rules and overrides.
- [ ] **TTS training live**: multi-speaker VITS per language or per group, model registry with evals, at least one production voice per launch language.
- [ ] **Runtime path live**: ASR → LLM → G2P → TTS with an API. Admin can trigger a short test conversation.
- [ ] **Admin UI useful**: Language Completeness dashboard, Seek-More panels, preflight cost estimate, YouTube link ingestion, discovery/ingest visibility.
- [ ] **Ops in place**: Postgres schema, object storage, dataset and model registries, CI checks, basic dashboards, promotion gates.

---

## Milestone A — Contracts and Validators

**Goal:** Freeze data contracts and prevent drift.

**Status:** ✅ Foundations in place; CI drift checks deferred.

**Tasks**
- [x] Add JSON Schemas for all contracts and export to `packages/data-contracts/` (scripts exist).
- [x] Implement `profile-validate` CLI (reads a LanguageProfile JSON, validates with pydantic, prints errors).
- [ ] Add CI job to fail on schema or contract drift. (deferred)

**Acceptance**
- [ ] Running `profile-validate examples/ak-GH.language-profile.json` passes.
- [ ] Sample fixtures validate for all contracts.

---

## Milestone B — Minimal Data Plane

**Goal:** Storage + DB are ready for lanes.

**Status:** ✅ Core tables + migrations exist; object storage + lifecycle rules pending.

**Tasks**
- [x] Postgres tables: `raw_artifacts`, `text_segments`, `audio_segments`, `segment_scores`, `language_profiles`, `voices`, `datasets`, `model_registry`.
- [ ] S3-compatible buckets and path layout for raw audio, normalized clips, JSONL, CSV, and dataset snapshots.
- [ ] Lifecycle rules: keep clips, optionally delete raw audio after N days.

**Acceptance**
- [ ] `infra/db/migrations` applied locally.
- [ ] Writing and reading small fixtures works.

---

## Milestone C — Text Lane MVP

**Goal:** Produce grounded dialogue JSONL at scale.

**Tasks**
- [x] LangExtract integrated with Google's library (real, not mock)
- [x] Chunking with overlap implemented and tested
- [x] Multi-format document parser (EPUB, PDF, TXT, HTML)
- [x] OCR support for scanned PDFs (Tesseract)
- [ ] HTML spot-check artifacts for N samples per batch
- [x] Contract validation on output (format guardians working)

**Acceptance**
- [x] `text_dialogue_corpus.jsonl` emitted and validated on a sample corpus
- [ ] Spot-check HTML renders and shows offsets aligned to source

**Status Update (Oct 9, 2025):**
- ✅ Text Lane MVP functional with database integration
- ✅ Tested end-to-end: document → segments → DB → JSONL
- ✅ OCR extraction: Somali Grammar (128k chars, 466 sentences)
- ✅ Dictionary mining: Twi pronunciations (2,327 entries)
- ⏸️ Real LangExtract API testing pending (needs API key)

---

## Milestone C2 — Radio Discovery + Ingest Reliability

**Goal:** Reliable station coverage, long-running capture, and visibility.

**Tasks**
- [x] Expand discovery sources (multi-country directories + wiki + other public lists).
- [x] Discovery coverage metrics: per-country station counts, source coverage stats.
- [x] Canonical station dedupe + provenance linking.
- [x] Long-running ingest scheduler with retries + backoff + per-station health.
- [x] Station auto-quarantine for repeated hard failures.
- [ ] Audio quality signals: bitrate stability, dropouts, silence ratio, codec failures. (silence ratio + codec/bitrate partially tracked; dropouts pending)
- [x] Admin visibility: per-station ingest health + global pipeline status.
- [x] Label mapping workflow (raw LID → ISO-639-3) with admin controls + backfill script.

**Acceptance**
- [ ] 24h run completes with automatic retries and visible health in admin.
- [x] Coverage report shows source totals + deltas for targeted countries.
- [ ] Coverage report includes auto-quarantine counts and audio quality rollups.

## Milestone D — Audio Lane MVP

**Goal:** Turn long audio into training-ready clips.

**Status:** ✅ MVP implemented; heavy dependencies and model downloads still required.

**Tasks**
- [x] Ingestion for YouTube link and file upload. Preflight duration and cost estimate.
- [x] ASR + diarization. Sentence-level alignment first; word-level when feasible.
- [x] Normalization: mono, 22.05 or 24 kHz, conservative trims. Clip length target 2–12 seconds.
- [x] Emit `paired_speech_corpus.csv` with confidences and granularity noted.

**Acceptance**
- [ ] A long sample link produces clips, CSV, and artifacts within projected cost.
- [ ] Alignment level recorded honestly (sentence vs word).

---

## Milestone E — Curator MVP

**Goal:** Score, dedupe, gate, and snapshot.

**Status:** ✅ Core logic implemented; needs production tuning.

**Tasks**
- [x] Scoring rubric with subscores: clarity, alignment, diarization, transcript accuracy, validity, shape.
- [x] Exact dupes: text hash and audio fingerprint. Near-dupes: embeddings cosine.
- [x] Policy gates for sensitive content.
- [x] Dataset snapshots with cards and audit trail.

**Acceptance**
- [ ] Curated minutes ≥90 and ≥70 computed. Duplicates suppressed. Policy gates applied.

---

## Milestone F — LanguageProfile and G2P

**Goal:** Rules and overrides guide pronunciation and defaults.

**Tasks**
- [ ] Inheritance: Group → Language → Dialect.
- [ ] Seed G2P rules, build override lexicon. Add `fallback_chain`.
- [ ] Targets in profile: min minutes ≥90, phoneme coverage, topic/register distribution.

**Acceptance**
- [ ] Two initial profiles pass validation. G2P overrides resolve correctly.

---

## Milestone G — Seeker Agents and Metrics

**Goal:** Fill gaps with automation.

**Tasks**
- [ ] Compute Language Completeness and the submetrics defined in `docs/architecture/metrics-and-completeness.md`.
- [ ] Seek-More panels for text and audio with preflight budget and storage estimates.
- [ ] Daily schedules and per-language caps.

**Acceptance**
- [ ] Dashboard shows green/yellow/red status and suggests sources to ingest.

---

## Milestone H — TTS Training Harness

**Goal:** Train and evaluate multi-speaker VITS.

**Tasks**
- [ ] Training scripts with dataset manifests and reproducible configs.
- [ ] Eval harness: MOS-lite, pronunciation error rate, stability.
- [ ] Model registry entries with semantic versions.

**Acceptance**
- [ ] One voice per launch language meets thresholds and is promoted.

---

## Milestone I — Runtime Service

**Goal:** Wire ASR → LLM → G2P → TTS for simple tests.

**Tasks**
- [ ] Minimal API to synthesize a reply with selected voice, style, dialect.
- [ ] Conversation harness for short back-and-forth tests.
- [ ] Request and error logging.

**Acceptance**
- [ ] Admin triggers a short test conversation and hears audio.

---

## Milestone J — Observability and Promotion Gates

**Goal:** Safe deploys and basic dashboards.

**Tasks**
- [ ] Dashboards: lane throughput, curator acceptance, cost per processed hour.
- [ ] Promotion checklist and rollback plan for datasets and models.

**Acceptance**
- [ ] A dataset and a TTS model pass gates and are promoted to "prod".

---

## Implementation TODOs (Format Guardians & Orchestration)

**Recent Implementation**: Added Format Guardians, Dataset Builder, Orchestration, and Runtime API packages.

**Next Priority Tasks:**
- [ ] **Wire real LangExtract** in text lane flows (replace stubs in `mumbl_orchestration.flows_text`)
- [x] **Integrate audio processing providers** in audio lane flows (replace stubs in `mumbl_orchestration.flows_audio`)
- [ ] **Call validators from flows** - integrate format guardians into orchestration validation steps
- [x] **Implement curator scoring/dedupe** logic in curator flows (replace stubs in `mumbl_orchestration.flows_curator`)
- [ ] **Replace stub S3 paths** with real storage integration in all flows
- [ ] **Add LUFS check** when audio library is introduced for audio validation
- [ ] **Connect runtime API** to real Prefect deployment for production orchestration
- [ ] **Define minimal production run profile** (station sampling, quotas, cost caps, success criteria)
- [ ] **Add discovery/ingest cost profile** (compute/storage/LLM budget assumptions)

## Infrastructure and Cost Notes

**Goal:** Keep heavy dependencies optional and off local laptops when needed.

**Options**
- Run heavy audio deps (torch/speechbrain/pyannote) on a VM or Docker host.
- Store model caches on a shared volume or object storage to avoid re-downloads.
- Use a small always-on worker for ingest while admin/UI run locally.

**Acceptance**
- [ ] Document runtime cost assumptions and storage growth per hour of capture.

## Recent Delivery Notes (Radio)

- ✅ Added an idempotent migration runner (`scripts/apply_migrations.py`) for Supabase.
- ✅ Continuous ingestion runner available (`scripts/run_radio_ingest_daemon.py`).

**New Commands Available:**
- `profile-validate` - Profile validation CLI
- `validate-text-jsonl` - Text validation CLI  
- `validate-audio-dataset` - Audio validation CLI
- `validate-scores` - Scores validation CLI
- `dataset-build tts ...` - Dataset building CLI
- `make run-api` - Runtime API server

## Risks and Controls

- LangExtract drift: grounding required, HTML spot-checks, contract tests fail builds.
- Noisy or scarce audio: sentence alignment allowed, honesty about granularity, Seek-More targets clean sources.
- Dupes: hash, fingerprint, near-dup filter.
- Model sprawl: model and dataset registries, semantic versions, promote gates.
- Cost: preflight estimates, caps, storage lifecycle rules.

---

## Future Enhancements (Post-V1)

### OCR Quality Improvements
- [ ] **Google Cloud Vision API integration** for higher OCR accuracy (95-98% vs 85-90%)
  - Cost: $1.50 per 1000 pages
  - Use case: Critical documents, poor scan quality, complex layouts
  - Implementation: Add as optional OCR provider alongside Tesseract
  - Selector: Auto-detect quality threshold, fallback to Vision API if Tesseract < 80%

### Multi-Language OCR
- [ ] Language-specific OCR models for better accuracy
- [ ] Post-OCR spell checking and correction
- [ ] OCR confidence scores per word/line
- [ ] Human-in-the-loop OCR correction workflow


### Radio Thing
- [ ] Hook it up so that the audio isnt stored locally, but rather elsewhere

---

## Out of Scope (V1)

- One giant multilingual TTS for all languages.
- Full cross-lingual same-voice without anchor data.
- Rich agentic enrichment beyond core labels (defer to V1.x).
