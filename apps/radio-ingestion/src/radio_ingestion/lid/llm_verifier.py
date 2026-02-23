"""LLM-based language verification for LID disagreements."""

import json
import os
from typing import Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class LLMVerifier:
    """
    LLM-based language verification for cases where audio and text LID disagree.

    Uses an LLM to adjudicate language/dialect when audio and text LID disagree.
    If LLM is disabled or unavailable, falls back to higher-confidence prediction.
    """

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
    ):
        """
        Initialize LLM verifier.

        Args:
            enabled: Whether to actually call LLM (default: False for now)
            provider: LLM provider name (default: "openai")
            model: LLM model ID (default: "gpt-4o-mini")
            api_key: API key (defaults to OPENAI_API_KEY for OpenAI)
            timeout_seconds: LLM request timeout
            max_tokens: Max tokens for response
            temperature: Sampling temperature
            max_transcript_chars: Max transcript chars sent to LLM
        """
        self.enabled = enabled
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_transcript_chars = max_transcript_chars
        self._client = None
        logger.info("LLM verifier initialized", enabled=enabled, provider=provider, model=model)

    def _get_openai_client(self):
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("OpenAI client not installed; LLM verification disabled")
            return None

        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set; LLM verification disabled")
            return None

        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def _build_prompt(
        self,
        audio_lang: Optional[str],
        audio_confidence: float,
        text_lang: Optional[str],
        text_confidence: float,
        transcript: str,
        country: Optional[str],
        candidates: Optional[List[str]],
    ) -> List[Dict[str, str]]:
        safe_transcript = (transcript or "").strip()
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
            f"Audio LID: {audio_lang} (confidence {audio_confidence:.2f})\n"
            f"Text LID: {text_lang} (confidence {text_confidence:.2f})\n"
            f"Country context: {country or 'unknown'}\n"
            f"Candidate languages: {candidate_str}\n\n"
            "If candidate languages are provided, pick the best match from that list. "
            "Return JSON only."
        )

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

    def _parse_llm_response(self, content: str) -> Tuple[Optional[str], float, Optional[str], str]:
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

        return language, confidence_value, dialect, rationale

    def verify_disagreement(
        self,
        audio_lang: Optional[str],
        audio_confidence: float,
        text_lang: Optional[str],
        text_confidence: float,
        transcript: str,
        country: Optional[str] = None,
        candidates: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], float, str]:
        """
        Verify language when audio and text LID disagree.

        Args:
            audio_lang: Audio LID language code
            audio_confidence: Audio LID confidence
            text_lang: Text LID language code
            text_confidence: Text LID confidence
            transcript: Text transcript
            country: Country code for context
            candidates: List of candidate language codes

        Returns:
            Tuple of (verified_lang, confidence, reason)
        """
        # Check if there's a disagreement
        if audio_lang == text_lang:
            return audio_lang, (audio_confidence + text_confidence) / 2, "agreement"

        # Log disagreement
        logger.warning(
            "Audio and text LID disagree",
            audio_lang=audio_lang,
            audio_confidence=audio_confidence,
            text_lang=text_lang,
            text_confidence=text_confidence,
            transcript_preview=transcript[:100] if transcript else None,
            country=country,
        )

        if not self.enabled:
            return self._fallback_choice(audio_lang, audio_confidence, text_lang, text_confidence)

        if not transcript:
            logger.warning("LLM verification skipped; transcript missing")
            return self._fallback_choice(audio_lang, audio_confidence, text_lang, text_confidence)

        if self.provider != "openai":
            logger.warning("Unsupported LLM provider; using fallback", provider=self.provider)
            return self._fallback_choice(audio_lang, audio_confidence, text_lang, text_confidence)

        client = self._get_openai_client()
        if client is None:
            return self._fallback_choice(audio_lang, audio_confidence, text_lang, text_confidence)

        messages = self._build_prompt(
            audio_lang=audio_lang,
            audio_confidence=audio_confidence,
            text_lang=text_lang,
            text_confidence=text_confidence,
            transcript=transcript,
            country=country,
            candidates=candidates,
        )

        try:
            request_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
            }
            if self.timeout_seconds > 0:
                request_kwargs["timeout"] = self.timeout_seconds

            try:
                response = client.chat.completions.create(**request_kwargs)
            except TypeError:
                request_kwargs.pop("timeout", None)
                request_kwargs.pop("response_format", None)
                response = client.chat.completions.create(**request_kwargs)

            content = response.choices[0].message.content if response.choices else ""
            language, confidence, dialect, rationale = self._parse_llm_response(content)

            if candidates:
                allowed = {c for c in candidates if c}
                if language not in allowed:
                    logger.info(
                        "LLM returned language outside candidates; using fallback",
                        llm_language=language,
                        candidates=list(allowed),
                    )
                    return self._fallback_choice(
                        audio_lang,
                        audio_confidence,
                        text_lang,
                        text_confidence,
                    )

            if dialect:
                logger.info("LLM dialect hint", dialect=dialect, language=language)

            if language:
                return language, max(confidence, 0.0), rationale

            logger.info("LLM returned no language; using fallback", rationale=rationale)
        except Exception as exc:
            logger.warning("LLM verification failed; using fallback", error=str(exc))

        return self._fallback_choice(audio_lang, audio_confidence, text_lang, text_confidence)

    def _fallback_choice(
        self,
        audio_lang: Optional[str],
        audio_confidence: float,
        text_lang: Optional[str],
        text_confidence: float,
    ) -> Tuple[Optional[str], float, str]:
        if audio_confidence > text_confidence:
            return audio_lang, audio_confidence, "audio_higher_confidence"
        return text_lang, text_confidence, "text_higher_confidence"

    def should_verify(
        self,
        audio_lang: Optional[str],
        audio_confidence: float,
        text_lang: Optional[str],
        text_confidence: float,
        threshold: float = 0.8,
    ) -> bool:
        """
        Determine if verification should be triggered.

        Args:
            audio_lang: Audio LID language
            audio_confidence: Audio LID confidence
            text_lang: Text LID language
            text_confidence: Text LID confidence
            threshold: Confidence threshold (default: 0.8)

        Returns:
            True if verification should be triggered
        """
        # Verify if:
        # 1. Languages disagree AND
        # 2. Both confidences are below threshold
        if audio_lang == text_lang:
            return False

        if audio_confidence >= threshold and text_confidence >= threshold:
            # Both confident, but disagree - worth verifying
            return True

        if audio_confidence < threshold and text_confidence < threshold:
            # Both uncertain - worth verifying
            return True

        return False


def create_llm_verifier(enabled: bool = False) -> LLMVerifier:
    """Factory function to create LLM verifier"""
    env_enabled = os.getenv("LLM_VERIFY_ENABLED", "").lower() == "true"
    provider = os.getenv("LLM_VERIFY_PROVIDER", "openai")
    model = os.getenv("LLM_VERIFY_MODEL", "gpt-4o-mini")
    timeout_seconds = int(os.getenv("LLM_VERIFY_TIMEOUT_SECONDS", "20"))
    max_tokens = int(os.getenv("LLM_VERIFY_MAX_TOKENS", "200"))
    temperature = float(os.getenv("LLM_VERIFY_TEMPERATURE", "0.0"))
    max_transcript_chars = int(os.getenv("LLM_VERIFY_MAX_TRANSCRIPT_CHARS", "1500"))

    return LLMVerifier(
        enabled=enabled or env_enabled,
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
        temperature=temperature,
        max_transcript_chars=max_transcript_chars,
    )
