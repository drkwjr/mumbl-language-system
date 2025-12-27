# LLM Strategy (Project-wide)

**Date verified:** 2025-12-26  
**Source of truth:** OpenAI `/v1/models` list from the configured `OPENAI_API_KEY`.

This project uses LLMs **throughout** the pipeline (discovery, labeling, QA,
summarization, and review). The goal is to place the right model at the right
point in the workflow, keeping cost and latency predictable.

## Model inventory (from `/v1/models`)

The current inventory includes families across:

- **Large reasoning models** (e.g., `gpt-5`, `gpt-5-pro`, `o1`, `o3`)
- **Mid-size general models** (e.g., `gpt-4.1`, `gpt-4o`)
- **Small/fast models** (e.g., `gpt-5-mini`, `gpt-4o-mini`)
- **Search + research variants** (e.g., `o3-deep-research`, `gpt-5-search-api`)
- **Audio + transcription** (e.g., `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `whisper-1`)
- **Realtime + audio** (e.g., `gpt-realtime`, `gpt-audio`)
- **Embeddings** (e.g., `text-embedding-3-small`, `text-embedding-3-large`)
- **TTS** (e.g., `gpt-4o-mini-tts`, `tts-1`, `tts-1-hd`)
- **Images** (e.g., `gpt-image-1`, `dall-e-3`)

## Placement guidance

**Discovery (multi-source ingestion)**
- Use small/fast models for parsing directory pages, cleaning station names, and
  extracting stream URLs.
- Use mid-size models for ambiguous entity resolution (stations with similar names).
- Prompt spec for wiki parsing: `docs/llm-prompts/wiki-station-extraction.md`.

**Language labeling / verification**
- Audio LID first (SpeechBrain), then **always-on** LLM verification using the
  language taxonomy to normalize labels and capture dialect hints.

**Curation / scoring**
- Mid-size or large reasoning models for policy checks, semantic quality review,
  and issue classification.

**Search and research**
- Use search/research variants when external facts are required, with citations.

**Embeddings**
- Use embeddings for dedupe, clustering, and similarity search across stations
  and transcripts.

## Operational guardrails

- Prefer **small/fast** models for high-volume tasks.
- Escalate to **large models** only for ambiguous or high‑impact decisions.
- Log model + prompt version with each LLM-assisted decision.
- Use the language taxonomy as the authoritative label set.

## Next steps

We can add a config table for model routing rules (task → model), so that the
admin can adjust model choices without code changes.
