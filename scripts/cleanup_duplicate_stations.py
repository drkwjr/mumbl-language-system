#!/usr/bin/env python3
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STORAGE_SRC = REPO_ROOT / "packages" / "storage" / "python" / "src"

sys.path.insert(0, str(STORAGE_SRC))

from mumbl_storage.db import get_connection  # noqa: E402


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def main() -> None:
    ensure_database_url()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH duplicates AS (
                  SELECT id,
                         COALESCE(station_uuid, stream_url) AS dedupe_key,
                         ROW_NUMBER() OVER (PARTITION BY COALESCE(station_uuid, stream_url) ORDER BY id) AS rn
                  FROM radio_sources
                )
                DELETE FROM radio_sources
                WHERE id IN (SELECT id FROM duplicates WHERE rn > 1)
                """
            )
            deleted = cur.rowcount

    print(f"Removed {deleted} duplicate stations.")


if __name__ == "__main__":
    main()
