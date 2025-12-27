#!/usr/bin/env python3
import json

from mumbl_storage.db import get_connection


SOURCES = [
    {
        "name": "Radio Browser",
        "source_type": "directory",
        "base_url": "https://www.radio-browser.info/",
        "countries": ["GH", "SO"],
        "notes": "Primary open directory of online radio streams.",
    },
    {
        "name": "Wikipedia Ghana Stations",
        "source_type": "wiki",
        "base_url": "https://en.wikipedia.org/wiki/Lists_of_radio_stations_in_Ghana",
        "countries": ["GH"],
        "notes": "Station list index; requires extraction + validation.",
    },
    {
        "name": "Wikipedia Somalia Media",
        "source_type": "wiki",
        "base_url": "https://en.wikipedia.org/wiki/Mass_media_in_Somalia",
        "countries": ["SO"],
        "notes": "Media list; includes radio stations.",
    },
]


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            for source in SOURCES:
                cur.execute(
                    """
                    INSERT INTO discovery_sources (name, source_type, base_url, countries, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        source_type = EXCLUDED.source_type,
                        base_url = EXCLUDED.base_url,
                        countries = EXCLUDED.countries,
                        notes = EXCLUDED.notes,
                        active = true,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        source["name"],
                        source["source_type"],
                        source["base_url"],
                        json.dumps(source.get("countries", [])),
                        source.get("notes"),
                    ),
                )
    print("Discovery sources seeded.")


if __name__ == "__main__":
    main()
