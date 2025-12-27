#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Dict, Any

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM frequency enrichment")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--model", default=os.getenv("LLM_VERIFY_MODEL", "gpt-4o-mini"))
    return parser.parse_args()


def ensure_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is required")


def get_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("OpenAI client not installed") from exc
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")
    return OpenAI(api_key=api_key)


def strip_html(html: str) -> str:
    html = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style.*?>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_homepage_text(url: str, timeout: int) -> Optional[str]:
    try:
        response = requests.get(url, timeout=timeout, headers={"User-Agent": "mumbl-frequency-bot/0.1"})
        response.raise_for_status()
        return strip_html(response.text)[:2000]
    except Exception:
        return None


def call_llm(client, model: str, station_name: str, country: str, homepage_text: str) -> Dict[str, Any]:
    system = (
        "You extract radio station frequencies. Return JSON with keys: "
        "frequency_mhz (number or null), frequency_label (string or null), "
        "confidence (0-1), evidence_text (short snippet)."
    )
    user = (
        f"Station name: {station_name}\n"
        f"Country: {country}\n"
        "Homepage text:\n"
        f"{homepage_text}\n\n"
        "If no frequency is present, return null fields with confidence 0."
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content if response.choices else "{}"
    return json.loads(content)


def main() -> None:
    args = parse_args()
    ensure_database_url()
    client = get_openai_client()

    with get_connection() as conn:
        source_repo = RadioSourceRepository(conn)
        freq_repo = RadioFrequencyCandidateRepository(conn)
        sources = [s for s in source_repo.list_active() if not s.get("frequency_mhz")]
        sources = sources[: args.limit]

        added = 0
        for source in sources:
            homepage = source.get("homepage")
            if not homepage:
                continue
            homepage_text = fetch_homepage_text(homepage, args.timeout)
            if not homepage_text:
                continue
            payload = call_llm(
                client,
                args.model,
                source.get("name", ""),
                source.get("country") or "",
                homepage_text,
            )
            frequency_mhz = payload.get("frequency_mhz")
            frequency_label = payload.get("frequency_label")
            confidence = payload.get("confidence", 0.0)
            evidence_text = payload.get("evidence_text")
            if not frequency_mhz:
                continue
            try:
                frequency_mhz = float(frequency_mhz)
            except (ValueError, TypeError):
                continue
            freq_repo.insert(
                source_id=source["id"],
                frequency_mhz=frequency_mhz,
                frequency_label=frequency_label or f"{frequency_mhz} FM",
                source="llm",
                confidence=float(confidence) if confidence is not None else 0.0,
                evidence_url=homepage,
                evidence_text=evidence_text,
            )
            freq_repo.resolve_best_for_source(source["id"])
            added += 1

    print(f"LLM candidates added: {added}")


if __name__ == "__main__":
    main()
