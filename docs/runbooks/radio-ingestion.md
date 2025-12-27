# Radio Ingestion Runbook

This runbook covers the capture → prefilter → LID → segment flow for radio streams.

## Prereqs

- `DATABASE_URL` is set and points to Supabase Postgres.
- `ffmpeg` is installed and on the PATH.
- Optional (recommended): `HUGGINGFACE_TOKEN` for faster SpeechBrain model downloads.

## Config

Set capture scope and timing via env:

```bash
CAPTURE_COUNTRIES=GHA,SOM
CAPTURE_DURATION=60
MAX_CONCURRENT_CAPTURES=5
CAPTURE_DIR=/path/to/radio_shards
LISTENING_TIMEZONE_STRATEGY=station
LISTENING_TIMEZONE=America/New_York
```

## Run the capture cycle

The service runs capture cycles on a schedule, but you can trigger a one-off
cycle by running the service and waiting for the scheduler to fire.

```bash
python -m radio_ingestion.service
```

## What to expect

- `radio_sources` is read for active stations in `CAPTURE_COUNTRIES`.
- `radio_shards` rows are created for each successful capture.
- `radio_segments` rows are created after prefilter + LID.
- `radio_station_hourly` aggregates update per station/hour.
- `radio_station_daypart` aggregates update per station/daypart.
- `pipeline_events` logs stage transitions and failures.

## Troubleshooting

- If SpeechBrain downloads repeat, set `HF_HOME` and `TORCH_HOME` to a stable path.
- If `WindowExtractor` fails, check `librosa`/`soundfile` availability.
- If connections fail, verify `DATABASE_URL` and ensure `sslmode=require` for Supabase.
