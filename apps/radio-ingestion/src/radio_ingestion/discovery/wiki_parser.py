"""Wikipedia station parser with optional LLM normalization."""

import json
import os
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class WikiStationCandidate:
    name: str
    stream_url: Optional[str] = None
    homepage: Optional[str] = None
    languages: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    confidence: Optional[float] = None


class ListItemParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_li = False
        self.items: List[str] = []
        self.buffer: List[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.in_li = True

    def handle_endtag(self, tag):
        if tag == "li" and self.in_li:
            text = " ".join(self.buffer).strip()
            if text:
                self.items.append(text)
            self.buffer = []
            self.in_li = False

    def handle_data(self, data):
        if self.in_li:
            self.buffer.append(data)


def extract_list_items(html: str) -> List[str]:
    parser = ListItemParser()
    parser.feed(html)
    return [item for item in parser.items if len(item.strip()) > 3]


def _get_openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        logger.warning("OpenAI SDK not installed", error=str(exc))
        return None
    return OpenAI()


def _build_llm_prompt(source_meta: Dict[str, Any], items: List[str]) -> str:
    payload = {
        "source": source_meta,
        "candidates": items,
    }
    few_shot = {
        "stations": [
            {
                "name": "Radio Example",
                "stream_url": None,
                "homepage": "https://radio.example",
                "languages": ["aka"],
                "tags": ["talk", "news"],
                "confidence": 0.6,
            },
            {
                "name": "Community FM",
                "stream_url": None,
                "homepage": None,
                "languages": None,
                "tags": ["community"],
                "confidence": 0.3,
            },
        ]
    }
    return (
        "You are extracting radio station records from Wikipedia list data. "
        "Return JSON only, with a single key 'stations'. Each station must include: "
        "name (string), stream_url (string or null), homepage (string or null), "
        "languages (array of ISO-639-3 codes if known), tags (array of strings), "
        "confidence (0-1). If unsure, keep fields null and confidence <= 0.4. "
        "Do not invent stream URLs. Do not include extra keys.\n\n"
        f"FEW_SHOT_OUTPUT:\n{json.dumps(few_shot, ensure_ascii=True)}\n\n"
        f"INPUT:\n{json.dumps(payload, ensure_ascii=True)}"
    )


def _normalize_llm_payload(payload: Dict[str, Any]) -> List[WikiStationCandidate]:
    stations = payload.get("stations", [])
    normalized: List[WikiStationCandidate] = []
    for station in stations:
        if not isinstance(station, dict):
            continue
        name = station.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        languages = station.get("languages")
        if isinstance(languages, list):
            languages = [str(lang).strip().lower() for lang in languages if str(lang).strip()]
        else:
            languages = None
        tags = station.get("tags")
        if isinstance(tags, list):
            tags = [str(tag).strip().lower() for tag in tags if str(tag).strip()]
        else:
            tags = None
        confidence = station.get("confidence")
        try:
            confidence = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence = None
        normalized.append(
            WikiStationCandidate(
                name=name.strip(),
                stream_url=station.get("stream_url"),
                homepage=station.get("homepage"),
                languages=languages,
                tags=tags,
                confidence=confidence,
            )
        )
    return normalized


def parse_with_llm(items: List[str], source_meta: Dict[str, Any]) -> List[WikiStationCandidate]:
    client = _get_openai_client()
    if client is None:
        return []

    model = os.getenv("WIKI_PARSER_MODEL", "gpt-4o-mini")
    prompt = _build_llm_prompt(source_meta, items)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
    except TypeError:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
    content = response.choices[0].message.content
    payload = json.loads(content)
    return _normalize_llm_payload(payload)


def parse_wiki_page(
    html: str,
    source_meta: Dict[str, Any],
    allow_llm: bool = True,
    max_items: int = 200,
) -> List[WikiStationCandidate]:
    items = extract_list_items(html)
    if not items:
        return []

    items = items[:max_items]
    if allow_llm and os.getenv("OPENAI_API_KEY"):
        try:
            llm_results = parse_with_llm(items, source_meta)
            min_expected = max(5, int(len(items) * 0.2))
            if llm_results and len(llm_results) >= min_expected:
                logger.info(
                    "LLM wiki parse succeeded",
                    total_items=len(items),
                    parsed=len(llm_results),
                    min_expected=min_expected,
                )
                return llm_results
            logger.warning(
                "LLM wiki parse too small, falling back",
                total_items=len(items),
                parsed=len(llm_results),
                min_expected=min_expected,
            )
        except Exception as exc:
            logger.warning("LLM wiki parse failed", error=str(exc))

    return [WikiStationCandidate(name=item) for item in items]
