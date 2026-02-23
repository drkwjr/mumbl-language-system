"""
Production LangExtract integration for dialogue and metadata extraction.

Uses Google's LangExtract library with source grounding for accurate labeling.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import langextract as lx


@dataclass
class LangExtractResult:
    """Result from LangExtract with grounding"""

    text: str
    start: int  # Character offset in source
    end: int
    is_dialogue: bool
    speaker: Optional[str] = None
    topic: Optional[str] = None
    register_type: Optional[str] = None  # 'formal', 'informal', 'neutral'
    code_switch_spans: List[tuple] = None
    confidence: float = 1.0  # Extraction confidence

    def __post_init__(self):
        if self.code_switch_spans is None:
            self.code_switch_spans = []


class RealLangExtract:
    """
    Production LangExtract processor using Google's library.

    Features:
    - Source grounding (exact character offsets)
    - Confidence scores
    - Structured extraction with examples
    - Multi-language support
    - Dialogue detection
    - Topic/register classification
    """

    def __init__(
        self,
        language: str = "en",
        dialect: str = "en-US",
        model_id: str = "gpt-4o",
        api_key: Optional[str] = None,
    ):
        """
        Initialize LangExtract processor.

        Args:
            language: Target language code
            dialect: Target dialect code
            model_id: LLM model to use (gpt-4o, gemini-2.5-flash, etc.)
            api_key: API key (or from env: OPENAI_API_KEY, LANGEXTRACT_API_KEY)
        """
        self.language = language
        self.dialect = dialect
        self.model_id = model_id
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LANGEXTRACT_API_KEY")

        if not self.api_key:
            raise ValueError(
                "API key required. Set OPENAI_API_KEY or LANGEXTRACT_API_KEY "
                "environment variable, or pass api_key parameter."
            )

    def process_chunk(self, text: str) -> List[LangExtractResult]:
        """
        Process a text chunk and extract labeled segments with grounding.

        Args:
            text: Chunk of text to process

        Returns:
            List of labeled segments with character offsets
        """
        # Define extraction schema with examples
        prompt_description = f"""
Extract dialogue and speech segments from this {self.language} text.
For each segment, identify:
1. Whether it's dialogue (someone speaking)
2. The speaker (if identifiable)
3. The topic (education, health, business, casual, etc.)
4. The register (formal, informal, or neutral)
5. Any code-switching (mixing languages)

Return ALL dialogue turns and significant speech segments with their exact
character positions in the source text.
"""

        # Few-shot examples to guide extraction
        examples = [
            {
                "text": 'Dr. Smith said: "Education is crucial for development."',
                "output": [
                    {
                        "text": "Education is crucial for development.",
                        "start": 16,
                        "end": 54,
                        "is_dialogue": True,
                        "speaker": "Dr. Smith",
                        "topic": "education",
                        "register_type": "formal",
                    }
                ],
            },
            {
                "text": '"Hey, wanna grab coffee?" she asked casually.',
                "output": [
                    {
                        "text": "Hey, wanna grab coffee?",
                        "start": 1,
                        "end": 24,
                        "is_dialogue": True,
                        "speaker": "she",
                        "topic": "casual",
                        "register_type": "informal",
                    }
                ],
            },
        ]

        try:
            # Call LangExtract with grounding
            result = lx.extract(
                text_or_documents=text,
                prompt_description=prompt_description,
                examples=examples,
                model_id=self.model_id,
                api_key=self.api_key,
                fence_output=True,  # Required for OpenAI
                use_schema_constraints=False,  # OpenAI limitation
            )

            # Convert LangExtract results to our format
            segments = self._parse_langextract_results(result, text)
            return segments

        except Exception as e:
            print(f"LangExtract error: {e}")
            # Fallback to simple extraction if API fails
            return self._fallback_extraction(text)

    def _parse_langextract_results(
        self, result: Any, original_text: str
    ) -> List[LangExtractResult]:
        """
        Parse LangExtract API results into our LangExtractResult format.

        LangExtract returns results with source attribution (grounding).
        We extract the structured data and offsets.
        """
        segments = []

        # LangExtract returns a list of extracted items with grounding
        for item in result:
            # Extract text and offsets from grounding
            text_content = item.get("text", "")
            start = item.get("start", 0)
            end = item.get("end", len(text_content))

            # Validate offsets
            if start < 0 or end > len(original_text):
                continue

            segments.append(
                LangExtractResult(
                    text=text_content,
                    start=start,
                    end=end,
                    is_dialogue=item.get("is_dialogue", False),
                    speaker=item.get("speaker"),
                    topic=item.get("topic"),
                    register_type=item.get("register_type", "neutral"),
                    code_switch_spans=item.get("code_switch_spans", []),
                    confidence=item.get("confidence", 0.9),
                )
            )

        return segments

    def _fallback_extraction(self, text: str) -> List[LangExtractResult]:
        """
        Simple fallback if API call fails.

        Uses basic heuristics to extract dialogue (not production quality,
        but prevents complete failure).
        """
        import re

        segments = []

        # Simple pattern: quoted text
        pattern = r'"([^"]+)"'
        for match in re.finditer(pattern, text):
            segments.append(
                LangExtractResult(
                    text=match.group(1),
                    start=match.start(1),
                    end=match.end(1),
                    is_dialogue=True,
                    confidence=0.5,  # Low confidence for fallback
                )
            )

        return segments
