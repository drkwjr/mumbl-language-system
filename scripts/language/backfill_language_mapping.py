#!/usr/bin/env python3
"""Backfill canonical language codes for radio segments using label map."""

import os
from pathlib import Path

from mumbl_storage.db import get_connection

REPO_ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def main() -> None:
    ensure_database_url()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE radio_segments
                SET primary_lang_raw = COALESCE(primary_lang_raw, primary_lang)
                WHERE primary_lang_raw IS NULL
                  AND primary_lang IS NOT NULL
                """)
            cur.execute("""
                UPDATE radio_segments seg
                SET primary_lang_iso639_3 = map.canonical_iso639_3,
                    primary_lang = map.canonical_iso639_3
                FROM language_label_map map
                WHERE seg.primary_lang_raw = map.observed_label
                  AND map.canonical_iso639_3 IS NOT NULL
                  AND (seg.primary_lang_iso639_3 IS NULL
                       OR seg.primary_lang_iso639_3 <> map.canonical_iso639_3)
                """)
            updated = cur.rowcount
        conn.commit()
    print(f"Updated {updated} segments")


if __name__ == "__main__":
    main()
