# Architecture Overview

## High-level flow

Intake → Text lane → Audio lane → Curator → Profiles → TTS training → Runtime

- **Intake**: fetch artifacts and metadata. YouTube links and file uploads supported.
- **Text lane**: LangExtract labels dialogue turns, topic, register, code-switch spans with grounded offsets. Emits `text_dialogue_corpus.jsonl`.
- **Audio lane**: ASR + diarization + normalization + alignment. Emits clips and `paired_speech_corpus.csv`.
- **Curator**: scores, dedupes, applies policy gates. Produces dataset snapshots.
- **Profiles**: LanguageProfile guides G2P, defaults, and thresholds.
- **TTS training**: multi-speaker VITS per language or group. Model registry holds metrics and versions.
- **Runtime**: ASR → LLM → G2P → TTS. Minimal API for tests and Admin UI.

## Service boundaries (apps/*)

- `intake-worker`: source fetchers, YouTube, file uploads.
- `text-lane`: LangExtract schemas and validators.
- `audio-lane`: ASR, diarization, alignment, normalization.
- `curator`: scoring, dedupe, policy filters, snapshots.
- `profile-builder`: profile validation, inheritance, G2P generation and overrides.
- `tts-trainer`: training and eval harness.
- `synth-gen`: synthetic dialogue generation (optional for V1).
- `runtime`: simple synthesis API and conversation harness.
- `admin-ui`: dashboard, seekers, preflight, link ingestion.

## Storage and DB

- Object storage: raw audio (cold), clips (hot), JSONL and CSV, dataset snapshots.
- Postgres: segments, scores, profiles, voices, datasets, model registry.

## Language tree

Group → Language → Dialect → Voice → Dataset → Clip

Profiles live at Dialect with inheritance. Voices attach to Dialect and reference model_id.
