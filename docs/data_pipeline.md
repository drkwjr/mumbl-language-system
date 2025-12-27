# Data Pipeline Overview

**Date verified:** 2025-12-26

## Purpose

This document describes the end-to-end data flow across discovery, ingestion, labeling, curation, and dataset preparation. It is the canonical pipeline map and should be kept in sync with `docs/CURRENT_STATUS.md`.

## Pipeline stages (current)

1) **Discovery (radio sources)**
   - Sources: Radio Browser + Wikipedia lists.
   - Output: `radio_sources`, `station_provenance`, `discovery_runs`.
   - Runbook: `docs/station-discovery.md`.

2) **Radio ingestion (capture + segmentation)**
   - Capture streams into shards, run VAD + LID, create segments.
   - Output: `radio_shards`, `radio_segments`, `pipeline_events`.
   - Runbook: `docs/runbooks/ingest.md`.

3) **Language verification (LLM)**
   - LLM classifier normalizes LID results against taxonomy.
   - Output: `segment_language_verifications`.
   - Strategy: `docs/llm-strategy.md`.

4) **Curator (quality + dedupe)**
   - Scores and policy gates applied; dedupe for exact/near duplicates.
   - Output: curated snapshots and dataset manifests.

5) **Dataset builder / TTS training**
   - Dataset manifests validated and prepared for training.

## Pipeline stages (text lane)

- Text ingestion → chunking → labeling → validation → curator → dataset snapshot.

## Sources of truth

- **Current status:** `docs/CURRENT_STATUS.md`
- **Discovery details:** `docs/station-discovery.md`
- **Ingest operations:** `docs/runbooks/ingest.md`
- **LLM usage:** `docs/llm-strategy.md` and `docs/llm-prompts/`
