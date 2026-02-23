#!/usr/bin/env python3
"""Backfill canonical station mappings from existing provenance rows."""

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))

from mumbl_storage.db import get_connection

from scripts.discovery.run_discovery import link_canonical_station, upsert_canonical_station


def main() -> None:
    batch_size = int(os.getenv("BACKFILL_BATCH_SIZE", "200"))
    limit = int(os.getenv("BACKFILL_LIMIT", "0"))
    offset = 0
    total = 0

    with get_connection() as conn:
        while True:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, source_id, station_name, stream_url, homepage, country, confidence
                    FROM station_provenance
                    ORDER BY id
                    LIMIT %s OFFSET %s
                    """,
                    (batch_size, offset),
                )
                rows = cur.fetchall()

            if not rows:
                break

            for row in rows:
                provenance_id = row[0]
                source_id = row[1]
                station_name = row[2]
                stream_url = row[3]
                homepage = row[4]
                country = row[5]
                confidence = row[6]

                canonical_id = upsert_canonical_station(
                    conn,
                    station_name,
                    stream_url,
                    homepage,
                )
                link_canonical_station(
                    conn,
                    canonical_id,
                    source_id,
                    provenance_id,
                    country,
                    confidence,
                )

            conn.commit()
            total += len(rows)
            offset += batch_size
            print(f"Backfilled {total} provenance rows", flush=True)
            if limit and total >= limit:
                break


if __name__ == "__main__":
    main()
