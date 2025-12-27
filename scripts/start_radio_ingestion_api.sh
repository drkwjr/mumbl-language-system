#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn is required (pip install -e apps/radio-ingestion)" >&2
  exit 1
fi

cd "$(dirname "${BASH_SOURCE[0]}")/../apps/radio-ingestion"

exec uvicorn radio_ingestion.api.dashboard:app --host 127.0.0.1 --port 8001 --reload
