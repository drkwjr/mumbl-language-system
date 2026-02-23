#!/usr/bin/env python3
"""Validate recent radio ingestion outputs in the database."""

import os
import sys
from datetime import timedelta
from typing import Optional

from mumbl_storage.db import get_connection
from psycopg.rows import dict_row


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def validate_recent(minutes: int) -> int:
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS shards
                FROM radio_shards
                WHERE start_ts >= NOW() - (%s || ' minutes')::interval
                """,
                (minutes,),
            )
            shards = cur.fetchone()["shards"]
            cur.execute(
                """
                SELECT COUNT(*) AS segments
                FROM radio_segments
                WHERE created_at >= NOW() - (%s || ' minutes')::interval
                """,
                (minutes,),
            )
            segments = cur.fetchone()["segments"]
            cur.execute(
                """
                SELECT COUNT(*) AS verifications
                FROM segment_language_verifications
                WHERE created_at >= NOW() - (%s || ' minutes')::interval
                """,
                (minutes,),
            )
            verifications = cur.fetchone()["verifications"]

    print(f"Recent window: last {minutes} minutes")
    print(f"radio_shards: {shards}")
    print(f"radio_segments: {segments}")
    print(f"segment_language_verifications: {verifications}")

    if shards == 0 or segments == 0:
        print("Validation failed: no recent shards/segments.")
        return 1
    print("Validation passed.")
    return 0


def main() -> int:
    minutes = get_int_env("INGEST_VALIDATE_MINUTES", 30)
    return validate_recent(minutes)


if __name__ == "__main__":
    sys.exit(main())
