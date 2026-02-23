#!/usr/bin/env python3
"""Apply SQL migrations idempotently using DATABASE_URL."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

from mumbl_storage.db import get_connection

REPO_ROOT = Path(__file__).resolve().parents[1]

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

MIGRATIONS_DIR = REPO_ROOT / "infra" / "db" / "migrations"

BOOTSTRAP_TABLES = {
    "001_initial_schema.sql": "text_segments",
    "002_radio_ingestion_schema.sql": "radio_sources",
    "003_segment_language_verifications.sql": "segment_language_verifications",
    "004_pipeline_events.sql": "pipeline_events",
    "005_station_frequency_candidates.sql": "station_frequency_candidates",
}


def iter_migrations() -> Iterable[Path]:
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name.endswith("_down.sql"):
            continue
        yield path


def ensure_schema_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            """)


def is_applied(conn, filename: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM schema_migrations WHERE filename = %s LIMIT 1",
            (filename,),
        )
        return cur.fetchone() is not None


def mark_applied(conn, filename: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO schema_migrations (filename)
            VALUES (%s)
            ON CONFLICT DO NOTHING
            """,
            (filename,),
        )


def table_exists(conn, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
        row = cur.fetchone()
    return bool(row and row[0] == table_name)


def bootstrap_if_present(conn, filename: str, table_name: Optional[str]) -> bool:
    if not table_name:
        return False
    if not table_exists(conn, table_name):
        return False
    mark_applied(conn, filename)
    return True


def apply_migration(conn, path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        sql = handle.read()
    with conn.cursor() as cur:
        cur.execute(sql)


def main() -> None:
    if not MIGRATIONS_DIR.exists():
        raise SystemExit(f"Migrations directory not found: {MIGRATIONS_DIR}")
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required to apply migrations")

    with get_connection() as conn:
        ensure_schema_table(conn)

        for migration in iter_migrations():
            name = migration.name
            if is_applied(conn, name):
                print(f"Skipping {name} (already applied)")
                continue

            if bootstrap_if_present(conn, name, BOOTSTRAP_TABLES.get(name)):
                print(f"Skipping {name} (existing schema detected)")
                continue

            print(f"Applying {name}")
            apply_migration(conn, migration)
            mark_applied(conn, name)
            conn.commit()

    print("Migrations complete.")


if __name__ == "__main__":
    main()
