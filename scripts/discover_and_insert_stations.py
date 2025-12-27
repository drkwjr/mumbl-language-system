#!/usr/bin/env python3
import argparse
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RADIO_SRC = REPO_ROOT / "apps" / "radio-ingestion" / "src"
STORAGE_SRC = REPO_ROOT / "packages" / "storage" / "python" / "src"

sys.path.insert(0, str(RADIO_SRC))
sys.path.insert(0, str(STORAGE_SRC))

from radio_ingestion.discovery.radio_browser import RadioBrowserClient  # noqa: E402
from radio_ingestion.storage.radio_repositories import RadioSourceRepository  # noqa: E402
from mumbl_storage.db import get_connection  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover and insert radio stations")
    parser.add_argument(
        "--countries",
        nargs="+",
        required=True,
        help="ISO 3166-1 alpha-3 country codes (e.g., SOM GHA)",
    )
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--page-size", type=int, default=200)
    parser.add_argument("--max-pages", type=int, default=0)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    parser.add_argument(
        "--api-urls",
        nargs="+",
        default=["https://de1.api.radio-browser.info/json"],
        help="Radio Browser API base URLs (space-separated)",
    )
    parser.add_argument("--language", default=None)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args()


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def main() -> None:
    args = parse_args()
    ensure_database_url()

    total_discovered = 0
    total_inserted = 0
    iso3_to_iso2 = {
        "GHA": "GH",
        "SOM": "SO",
    }

    with get_connection() as conn:
        repo = RadioSourceRepository(conn)
        for country in args.countries:
            country_code = None
            country_param = country
            if len(country) == 2:
                country_code = country.upper()
                country_param = None
            elif len(country) == 3 and country.upper() in iso3_to_iso2:
                country_code = iso3_to_iso2[country.upper()]
                country_param = None
            stations = []
            last_error = None
            for api_url in args.api_urls:
                try:
                    client = RadioBrowserClient(
                        api_url=api_url,
                        timeout_seconds=args.timeout,
                        max_retries=args.retries,
                    )
                    print(f"{country}: using {api_url}")

                    offset = 0
                    page = 0
                    parsed_batch = []
                    while True:
                        page += 1
                        if args.max_pages and page > args.max_pages:
                            break

                        page_results = client.search_stations(
                            country=country_param,
                            country_code=country_code,
                            language=args.language,
                            limit=args.page_size,
                            offset=offset,
                            order="votes",
                            reverse=True,
                        )
                        if not page_results:
                            break

                        parsed_batch.extend(page_results)
                        offset += args.page_size
                        if len(page_results) < args.page_size:
                            break

                        time.sleep(args.sleep_seconds)

                    stations = []
                    for station in parsed_batch:
                        parsed = client.parse_station(station)
                        if parsed.get("stream_url"):
                            stations.append(parsed)
                        if args.limit and len(stations) >= args.limit:
                            break

                    break
                except Exception as exc:
                    last_error = exc
                    print(f"{country}: failed via {api_url}: {exc}")

            if not stations and last_error:
                raise last_error

            unique_stations = []
            seen_keys = set()
            for station in stations:
                key = station.get("station_uuid") or station.get("stream_url")
                if not key:
                    continue
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                unique_stations.append(station)

            total_discovered += len(unique_stations)
            ids = repo.insert_many(unique_stations)
            inserted = len([sid for sid in ids if sid is not None])
            total_inserted += inserted
            print(f"{country}: discovered {len(unique_stations)} stations, inserted {inserted}")

    print(f"Total discovered: {total_discovered}")
    print(f"Total inserted: {total_inserted}")


if __name__ == "__main__":
    main()
