#!/usr/bin/env python3
import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
RADIO_SRC = REPO_ROOT / "apps" / "radio-ingestion" / "src"
STORAGE_SRC = REPO_ROOT / "packages" / "storage" / "python" / "src"

sys.path.insert(0, str(RADIO_SRC))
sys.path.insert(0, str(STORAGE_SRC))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from radio_ingestion.storage.radio_repositories import (  # noqa: E402
    RadioSourceRepository,
    RadioFrequencyCandidateRepository,
)
from mumbl_storage.db import get_connection  # noqa: E402

COUNTRY_QIDS = {
    "GHA": "Q117",
    "SOM": "Q1045",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wikidata frequency enrichment")
    parser.add_argument("--countries", nargs="+", default=["GHA", "SOM"])
    parser.add_argument("--limit", type=int, default=200)
    return parser.parse_args()


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def normalize_name(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = text.replace("fm", " ")
    text = text.replace("radio", " ")
    text = text.replace("stereo", " ")
    return " ".join(text.split())


def fetch_wikidata_stations(country_qid: str) -> List[Dict[str, str]]:
    query = f"""
    SELECT ?station ?stationLabel ?frequency WHERE {{
      ?station wdt:P31/wdt:P279* wd:Q14350;
               wdt:P17 wd:{country_qid};
               wdt:P2144 ?frequency.
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    """
    response = requests.get(
        "https://query.wikidata.org/sparql",
        params={"format": "json", "query": query},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for row in data["results"]["bindings"]:
        results.append(
            {
                "station": row["station"]["value"],
                "label": row["stationLabel"]["value"],
                "frequency": row["frequency"]["value"],
            }
        )
    return results


def main() -> None:
    args = parse_args()
    ensure_database_url()

    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)
        freq_repo = RadioFrequencyCandidateRepository(conn)
        sources = source_repo.list_active()
        name_map = {}
        for source in sources:
            normalized = normalize_name(source.get("name", ""))
            if normalized:
                name_map.setdefault(normalized, []).append(source)

        total_added = 0
        for country in args.countries:
            qid = COUNTRY_QIDS.get(country.upper())
            if not qid:
                continue
            stations = fetch_wikidata_stations(qid)
            for station in stations[: args.limit]:
                normalized = normalize_name(station["label"])
                matches = name_map.get(normalized, [])
                if not matches:
                    continue
                try:
                    frequency_mhz = float(station["frequency"])
                except ValueError:
                    continue
                for match in matches:
                    freq_repo.insert(
                        source_id=match["id"],
                        frequency_mhz=frequency_mhz,
                        frequency_label=f"{frequency_mhz} FM",
                        source="wikidata",
                        confidence=0.8,
                        evidence_url=station["station"],
                        evidence_text=station["label"],
                    )
                    freq_repo.resolve_best_for_source(match["id"])
                    total_added += 1

    print(f"Wikidata candidates added: {total_added}")


if __name__ == "__main__":
    main()
