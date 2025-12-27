"""Transcript language verification using an LLM."""

import json
import os
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TranscriptLanguageVerifier:
    """LLM-based language verification for transcript text."""

    def __init__(
        self,
        enabled: bool = False,
        provider: str = "openai",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        timeout_seconds: int = 20,
        max_tokens: int = 200,
        temperature: float = 0.0,
        max_transcript_chars: int = 1500,
        min_transcript_chars: int = 40,
        verify_always: bool = False,
    ):
        self.enabled = enabled
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_transcript_chars = max_transcript_chars
        self.min_transcript_chars = min_transcript_chars
        self.verify_always = verify_always
        self._client = None

        logger.info(
            "Transcript language verifier initialized",
            extra={
                "enabled": enabled,
                "provider": provider,
                "model": model,
            },
        )

    def _get_openai_client(self):
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("OpenAI client not installed; transcript verification disabled")
            return None

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set; transcript verification disabled")
            return None

        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def should_verify(self, expected_lang: Optional[str], detected_lang: Optional[str]) -> bool:
        if not self.enabled:
            return False
        if self.verify_always:
            return True
        if not expected_lang:
            return False
        if not detected_lang:
            return True
        return expected_lang != detected_lang

    def verify_transcript(
        self,
        transcript: str,
        expected_lang: Optional[str],
        detected_lang: Optional[str],
        candidates: Optional[List[str]] = None,
        country: Optional[str] = None,
    ) -> Tuple[Optional[str], float, Optional[str], str]:
        if not transcript or len(transcript.strip()) < self.min_transcript_chars:
            return None, 0.0, None, "transcript_too_short"

        if self.provider != "openai":
            logger.warning("Unsupported LLM provider; skipping verification", extra={"provider": self.provider})
            return None, 0.0, None, "unsupported_provider"

        client = self._get_openai_client()
        if client is None:
            return None, 0.0, None, "client_unavailable"

        safe_transcript = transcript.strip()
        if self.max_transcript_chars > 0 and len(safe_transcript) > self.max_transcript_chars:
            safe_transcript = safe_transcript[: self.max_transcript_chars].rstrip()

        candidate_list = sorted({c for c in (candidates or []) if c})
        candidate_str = ", ".join(candidate_list) if candidate_list else "None provided"

        system_message = (
            "You are a language identification verifier for speech transcripts. "
            "Return a JSON object with keys: language, dialect, confidence, rationale. "
            "Use ISO 639-1 codes when possible. If a dialect is known, use a BCP-47 "
            "style tag (e.g., ak-GH-asante). If unsure, set language to null and "
            "confidence to 0."
        )
        user_message = (
            "Decide the most likely language for this transcript.\n\n"
            f"Transcript:\n{safe_transcript}\n\n"
            f"Expected language: {expected_lang or 'unknown'}\n"
            f"Detected language: {detected_lang or 'unknown'}\n"
            f"Country context: {country or 'unknown'}\n"
            f"Candidate languages: {candidate_str}\n\n"
            "If candidate languages are provided, pick the best match from that list. "
            "Return JSON only."
        )

        request_kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.timeout_seconds > 0:
            request_kwargs["timeout"] = self.timeout_seconds

        try:
            try:
                response = client.chat.completions.create(**request_kwargs)
            except TypeError:
                request_kwargs.pop("timeout", None)
                response = client.chat.completions.create(**request_kwargs)

            content = response.choices[0].message.content if response.choices else ""
            return self._parse_response(content, candidates=candidate_list)
        except Exception as exc:
            logger.warning("Transcript verification failed", extra={"error": str(exc)})
            return None, 0.0, None, "llm_failure"

    def _parse_response(
        self,
        content: str,
        candidates: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], float, Optional[str], str]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return None, 0.0, None, "llm_response_not_json"

        language = payload.get("language")
        dialect = payload.get("dialect")
        confidence = payload.get("confidence")
        rationale = payload.get("rationale") or "llm_verified"

        if isinstance(confidence, (int, float)):
            confidence_value = float(confidence)
        else:
            confidence_value = 0.0

        language = language if isinstance(language, str) and language.strip() else None
        dialect = dialect if isinstance(dialect, str) and dialect.strip() else None

        if candidates and language and language not in candidates:
            return None, 0.0, None, "llm_language_not_in_candidates"

        return language, confidence_value, dialect, rationale


def create_transcript_verifier() -> TranscriptLanguageVerifier:
    env_enabled = os.getenv("LLM_VERIFY_ENABLED", "").lower() == "true"
    provider = os.getenv("LLM_VERIFY_PROVIDER", "openai")
    model = os.getenv("LLM_VERIFY_MODEL", "gpt-4o-mini")
    timeout_seconds = int(os.getenv("LLM_VERIFY_TIMEOUT_SECONDS", "20"))
    max_tokens = int(os.getenv("LLM_VERIFY_MAX_TOKENS", "200"))
    temperature = float(os.getenv("LLM_VERIFY_TEMPERATURE", "0.0"))
    max_transcript_chars = int(os.getenv("LLM_VERIFY_MAX_TRANSCRIPT_CHARS", "1500"))
    min_transcript_chars = int(os.getenv("LLM_VERIFY_MIN_TRANSCRIPT_CHARS", "40"))
    verify_always = os.getenv("LLM_VERIFY_ALWAYS", "").lower() == "true"

    return TranscriptLanguageVerifier(
        enabled=env_enabled,
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        temperature=temperature,
        max_transcript_chars=max_transcript_chars,
        min_transcript_chars=min_transcript_chars,
        verify_always=verify_always,
    )
