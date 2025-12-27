# Storage Layout (Project-wide)

**Date verified:** 2025-12-26

This document defines the canonical storage layout across all lanes (text, audio, radio ingestion, curator, and training). It is a stub until object storage is fully wired.

## Goals

- Keep raw inputs and derived artifacts clearly separated.
- Ensure paths are stable across environments (local/dev/prod).
- Support lifecycle rules (raw retention vs curated keep-forever).

## Storage domains

### 1) Raw Inputs

- `raw/text/` — source documents, scraped text
- `raw/audio/` — long-form audio (YouTube or uploads)
- `raw/radio/` — captured stream shards (radio ingestion)

### 2) Processed Artifacts

- `processed/text/` — labeled JSONL outputs
- `processed/audio/` — normalized clips + manifests
- `processed/radio/` — segmented speech windows

### 3) Curated Datasets

- `datasets/` — curated snapshots and dataset cards
- `datasets/manifests/` — training manifests

### 4) Models and Eval

- `models/` — trained model artifacts
- `models/evals/` — evaluation reports

## Notes

- Local paths typically live under `data/`.
- Object storage paths should mirror the same layout when S3/MinIO is wired.
- Retention targets:
  - raw audio/shards: short-lived (days)
  - processed clips + curated datasets: retained

## Local defaults

These are the default local directories used today:

- `data/radio_shards/` — radio capture shards
- `data/audio/` — audio lane outputs (raw/normalized/clips)
- `data/` — shared scratch outputs and intermediate artifacts

## Related docs

- `docs/runbooks/ingest.md`
- `docs/data_pipeline.md`
- `docs/database_structure.md`
