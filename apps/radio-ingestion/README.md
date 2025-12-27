# radio-ingestion

Automated radio stream ingestion service that discovers stations, captures live audio, detects speech, identifies languages, and feeds labeled segments into the Mumbl pipeline.

## Architecture

Modular packages:
- `discovery/`: Radio Browser API integration and station management
- `capture/`: ffmpeg-based audio recording
- `prefilter/`: VAD and music/speech classification
- `lid/`: Language identification (audio + text fusion)
- `storage/`: Database repositories and S3 upload
- `orchestration/`: Task queues and scheduling
- `api/`: FastAPI dashboard endpoints

## Configuration

Environment variables (`.env`):
- `RADIO_BROWSER_API`: API endpoint URL (default: https://de1.api.radio-browser.info/json)
- `CAPTURE_DIR`: Local storage path (default: /data/radio_shards)
- `DATABASE_URL`: PostgreSQL connection string
- `S3_BUCKET`: S3 bucket name (optional for MVP)
- `S3_ENABLED`: Enable S3 uploads (default: false)
- `CAPTURE_DURATION`: Seconds per capture (default: 180)
- `WINDOW_SIZE`: Seconds per language window (default: 30)
- `VAD_AGGRESSIVENESS`: WebRTC VAD mode 0-3 (default: 2)
- `MUSIC_THRESHOLD`: Music filter cutoff 0-1 (default: 0.6)

## Quick Start

```bash
# Install dependencies
pip install -e .

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/mumbl_lang_system
export CAPTURE_DIR=/data/radio_shards

# Run discovery for Somali stations
python -m radio_ingestion.discovery.radio_browser --country SO --limit 5
```

## Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests (requires DB)
pytest tests/integration/

# Run full pipeline E2E test
pytest tests/e2e/test_full_pipeline.py
```

