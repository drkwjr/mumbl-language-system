#!/usr/bin/env python3
"""Seed language_label_map using safe ISO-639 matches."""

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
            cur.execute(
                """
                SELECT DISTINCT primary_lang_raw
                FROM radio_segments
                WHERE primary_lang_raw IS NOT NULL
                """
            )
            raw_labels = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT iso639_3, iso639_1 FROM language_taxonomy")
            rows = cur.fetchall()

        iso3 = {row[0] for row in rows if row[0]}
        iso1_to_iso3 = {row[1]: row[0] for row in rows if row[1] and row[0]}

        inserted = 0
        for label in raw_labels:
            if not label:
                continue
            prefix = label.split(":", 1)[0].strip()
            canonical = None
            if len(prefix) == 3 and prefix in iso3:
                canonical = prefix
            elif len(prefix) == 2 and prefix in iso1_to_iso3:
                canonical = iso1_to_iso3[prefix]

            if not canonical:
                continue

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO language_label_map (
                        observed_label, canonical_iso639_3, source, confidence, notes
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (observed_label) DO NOTHING
                    """,
                    (label, canonical, "seed", 0.8, "iso prefix match"),
                )
                if cur.rowcount:
                    inserted += 1

        conn.commit()

    print(f"Seeded {inserted} label mappings")


if __name__ == "__main__":
    main()
