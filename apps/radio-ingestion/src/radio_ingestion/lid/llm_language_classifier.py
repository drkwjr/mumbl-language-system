"""LLM-based language classification using taxonomy and LID signals."""

import json
from typing import Any, Dict, List, Optional

import structlog
from openai import OpenAI

logger = structlog.get_logger(__name__)


FEW_SHOT = """
EXAMPLE 1
TAXONOMY: {"languages":[{"iso639_3":"aka","name":"Akan","family_code":"niger-congo"}],"dialects":[{"language_iso639_3":"aka","dialect_code":"asante","name":"Asante Twi"}]}
SIGNALS:
- audio_lid_topk: {"aka":0.82,"eng":0.1}
- transcript: "Meda wo ase. Me din de Kofi."
- station_metadata: {"name":"Adom FM","country":"GH","tags":["akan","twi"],"lang_hint":"aka"}
- station_language_history: {"aka":0.9}
RESPONSE:
{"primary_language":"aka","dialect":"asante","language_family":"niger-congo","confidence":0.86,"rationale":"Audio and metadata align with Akan (Asante).","signals":{"audio_lid":["aka"],"metadata":["ghana","akan","twi"]},"uncertainty_flags":[]}

EXAMPLE 2
TAXONOMY: {"languages":[{"iso639_3":"som","name":"Somali"}],"dialects":[]}
SIGNALS:
- audio_lid_topk: {"som":0.42,"ara":0.38}
- transcript: ""
- station_metadata: {"name":"Radio Muqdisho","country":"SO","tags":["somalia"],"lang_hint":null}
- station_language_history: {}
RESPONSE:
{"primary_language":"unknown","dialect":"unknown","language_family":null,"confidence":0.35,"rationale":"Insufficient evidence; audio is mixed and no transcript.","signals":{"audio_lid":["som","ara"],"metadata":["somalia"]},"uncertainty_flags":["insufficient_evidence"]}
"""


def _response_to_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    chunks = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(text)
    if chunks:
        return "".join(chunks)

    raise ValueError("LLM response missing output text")


def _extract_json(content: str) -> str:
    if not content:
        raise ValueError("Empty LLM response")
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in response")
    return content[start : end + 1]


def _fallback_payload(reason: str) -> Dict[str, Any]:
    return {
        "primary_language": "unknown",
        "dialect": "unknown",
        "language_family": None,
        "confidence": 0.0,
        "rationale": reason,
        "signals": {},
        "uncertainty_flags": [reason],
    }


def _coerce_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return _fallback_payload("invalid_payload")

    primary_language = payload.get("primary_language")
    if not isinstance(primary_language, str) or not primary_language.strip():
        primary_language = "unknown"

    dialect = payload.get("dialect")
    if not isinstance(dialect, str) or not dialect.strip():
        dialect = "unknown"

    language_family = payload.get("language_family")
    if language_family is not None and not isinstance(language_family, str):
        language_family = None

    confidence = payload.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = 0.0

    rationale = payload.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        rationale = "llm_response"

    signals = payload.get("signals")
    if not isinstance(signals, dict):
        signals = {}

    uncertainty_flags = payload.get("uncertainty_flags")
    if not isinstance(uncertainty_flags, list):
        uncertainty_flags = []

    return {
        "primary_language": primary_language.strip(),
        "dialect": dialect.strip(),
        "language_family": language_family,
        "confidence": float(confidence),
        "rationale": rationale.strip(),
        "signals": signals,
        "uncertainty_flags": uncertainty_flags,
    }


def _parse_relaxed(content: str) -> Dict[str, Any]:
    if not content:
        return _fallback_payload("empty_response")

    try:
        payload = json.loads(content)
        return _coerce_payload(payload)
    except json.JSONDecodeError:
        pass

    try:
        payload = json.loads(_extract_json(content))
        return _coerce_payload(payload)
    except Exception:
        pass

    primary_language = None
    dialect = None
    for line in content.splitlines():
        if "primary_language" in line:
            primary_language = line.split(":", 1)[-1].strip().strip('",')
        if "dialect" in line and "primary_language" not in line:
            dialect = line.split(":", 1)[-1].strip().strip('",')

    payload = {
        "primary_language": primary_language or "unknown",
        "dialect": dialect or "unknown",
        "language_family": None,
        "confidence": 0.0,
        "rationale": "relaxed_parse",
        "signals": {},
        "uncertainty_flags": ["relaxed_parse"],
    }
    return _coerce_payload(payload)


def _build_prompt(
    taxonomy: Dict[str, Any],
    audio_lid_topk: Dict[str, float],
    transcript: Optional[str],
    station_metadata: Dict[str, Any],
    station_history: Optional[Dict[str, Any]],
) -> str:
    return (
        "You are a language classification engine. You must follow the taxonomy exactly. "
        'Return JSON only. If evidence is insufficient, set primary_language="unknown" '
        "and include uncertainty_flags.\n\n"
        "You must output a JSON object with keys: primary_language, dialect, language_family, "
        "confidence, rationale, signals, uncertainty_flags.\n\n"
        f"{FEW_SHOT}\n\n"
        "Classify the language and dialect for this segment using the taxonomy below.\n\n"
        f"TAXONOMY:\n{json.dumps(taxonomy, ensure_ascii=True)}\n\n"
        f"SIGNALS:\n- audio_lid_topk: {json.dumps(audio_lid_topk, ensure_ascii=True)}\n"
        f"- transcript: {transcript or ''}\n"
        f"- station_metadata: {json.dumps(station_metadata, ensure_ascii=True)}\n"
        f"- station_language_history: {json.dumps(station_history or {}, ensure_ascii=True)}\n\n"
        "RULES:\n"
        "1) Use ISO-639-3 codes for primary_language.\n"
        "2) Use dialect only if the taxonomy includes it.\n"
        "3) If audio and text disagree, keep confidence <= 0.6 and add an uncertainty flag.\n"
        '4) If evidence is missing, return "unknown" with confidence <= 0.4.\n'
        "5) Do NOT invent languages not in the taxonomy list.\n"
    )


class LLMLanguageClassifier:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI()

    def classify(
        self,
        taxonomy: Dict[str, Any],
        audio_lid_topk: Dict[str, float],
        transcript: Optional[str],
        station_metadata: Dict[str, Any],
        station_history: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt = _build_prompt(
            taxonomy=taxonomy,
            audio_lid_topk=audio_lid_topk,
            transcript=transcript,
            station_metadata=station_metadata,
            station_history=station_history,
        )

        content = ""
        for attempt in range(2):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    response_format={"type": "json_object"},
                )
            except TypeError:
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                )

            content = _response_to_text(response)
            payload = _parse_relaxed(content)
            if payload.get("uncertainty_flags"):
                logger.warning(
                    "LLM classifier returned non-strict JSON",
                    attempt=attempt + 1,
                    flags=payload.get("uncertainty_flags"),
                    content_preview=content[:200],
                )
            if payload.get("uncertainty_flags") and attempt == 0:
                prompt = "Return ONLY valid JSON. Do not include explanations.\n\n" + prompt
                continue
            return payload

        return _fallback_payload("parse_failed")
