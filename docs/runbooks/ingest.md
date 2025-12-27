# Radio Ingestion Runbook

**Date verified:** 2025-12-26

## Goal

Run a short radio ingestion batch and validate that shards, segments, and LLM verification records are written.

## Prereqs

- `.env` includes `DATABASE_URL` and `OPENAI_API_KEY`.
- Dependencies installed (see `scripts/check_ingest_deps.py`).
- Radio stations already discovered (`scripts/discovery/run_discovery.py`).
- Optional tuning: `FAILURE_COOLDOWN_MINUTES`, `MAX_CONSECUTIVE_FAILURES`.

## Steps

1) Check dependencies

```bash
python scripts/check_ingest_deps.py
```

2) Start the radio ingestion API

```bash
./scripts/start_radio_ingestion_api.sh
```

3) Run a short ingestion pass

```bash
python scripts/run_radio_ingest_once.py
```

Optional: run the continuous scheduler (daemon mode)

```bash
python scripts/run_radio_ingest_daemon.py
```

4) Validate ingestion outputs (last 30 minutes)

```bash
python scripts/validate_radio_ingest.py
```

## Expected results

- `radio_shards` > 0 for the last 30 minutes.
- `radio_segments` > 0 for the last 30 minutes.
- `segment_language_verifications` present when `OPENAI_API_KEY` is set.

## Troubleshooting

- `ffmpeg` missing: install via brew and re-run dependency check.
- SpeechBrain model downloads fail: retry once; first run downloads are slow.
- No shards/segments: confirm stations exist and stream URLs are reachable.
