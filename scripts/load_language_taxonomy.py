#!/usr/bin/env python3
import json
from pathlib import Path

from mumbl_storage.db import get_connection


def load_taxonomy(path: Path) -> dict:
    return json.loads(path.read_text())


def upsert_families(cur, families):
    for family in families:
        cur.execute(
            """
            INSERT INTO language_families (family_code, name, notes)
            VALUES (%s, %s, %s)
            ON CONFLICT (family_code) DO UPDATE SET
                name = EXCLUDED.name,
                notes = EXCLUDED.notes
            """,
            (family["family_code"], family["name"], family.get("notes")),
        )


def upsert_languages(cur, languages):
    for lang in languages:
        cur.execute(
            """
            INSERT INTO language_taxonomy (
                iso639_3, iso639_1, name, family_code, countries, notes
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (iso639_3) DO UPDATE SET
                iso639_1 = EXCLUDED.iso639_1,
                name = EXCLUDED.name,
                family_code = EXCLUDED.family_code,
                countries = EXCLUDED.countries,
                notes = EXCLUDED.notes
            """,
            (
                lang["iso639_3"],
                lang.get("iso639_1"),
                lang["name"],
                lang.get("family_code"),
                json.dumps(lang.get("countries", [])),
                lang.get("notes"),
            ),
        )


def upsert_dialects(cur, dialects):
    for dialect in dialects:
        cur.execute(
            """
            INSERT INTO language_dialects (
                language_iso639_3, dialect_code, name, region, notes
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (language_iso639_3, dialect_code) DO UPDATE SET
                name = EXCLUDED.name,
                region = EXCLUDED.region,
                notes = EXCLUDED.notes
            """,
            (
                dialect["language_iso639_3"],
                dialect["dialect_code"],
                dialect["name"],
                dialect.get("region"),
                dialect.get("notes"),
            ),
        )


def main():
    taxonomy_path = Path("data/language_taxonomy/ghana_somalia.json")
    if not taxonomy_path.exists():
        raise SystemExit(f"Missing taxonomy file: {taxonomy_path}")

    payload = load_taxonomy(taxonomy_path)
    families = payload.get("families", [])
    languages = payload.get("languages", [])
    dialects = payload.get("dialects", [])

    with get_connection() as conn:
        with conn.cursor() as cur:
            upsert_families(cur, families)
            upsert_languages(cur, languages)
            upsert_dialects(cur, dialects)
        conn.commit()

    print("Taxonomy loaded:", taxonomy_path)


if __name__ == "__main__":
    main()
