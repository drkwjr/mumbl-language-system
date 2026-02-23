#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

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

from mumbl_storage.db import get_connection  # noqa: E402
from radio_ingestion.storage.radio_repositories import (  # noqa: E402
    RadioFrequencyCandidateRepository,
    RadioSourceRepository,
    _extract_frequency,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heuristic frequency enrichment")
    parser.add_argument("--limit", type=int, default=200)
    return parser.parse_args()


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def main() -> None:
    args = parse_args()
    ensure_database_url()

    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)
        freq_repo = RadioFrequencyCandidateRepository(conn)
        sources = source_repo.list_active()[: args.limit]

        added = 0
        for source in sources:
            text_bits = [source.get("name", "")]
            tags = source.get("tags") or []
            if isinstance(tags, list):
                text_bits.extend(tags)
            text = " ".join([bit for bit in text_bits if bit])
            candidate = _extract_frequency(text)
            if not candidate:
                continue
            freq_repo.insert(
                source_id=source["id"],
                frequency_mhz=candidate["frequency_mhz"],
                frequency_label=candidate["frequency_label"],
                source="heuristic",
                confidence=0.35,
                evidence_text=text[:200],
            )
            freq_repo.resolve_best_for_source(source["id"])
            added += 1

    print(f"Heuristic candidates added: {added}")


if __name__ == "__main__":
    main()
