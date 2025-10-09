"""
Mock LangExtract processor for development and testing.

This is a STUB that simulates dialogue detection and labeling.
In production, this will be replaced with real LangExtract API integration.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class LangExtractResult:
    """Result from LangExtract processing"""
    text: str
    start: int  # Character offset
    end: int
    is_dialogue: bool
    topic: Optional[str] = None
    register_type: Optional[str] = None
    code_switch_spans: List[Tuple[int, int]] = None
    
    def __post_init__(self):
        if self.code_switch_spans is None:
            self.code_switch_spans = []


class MockLangExtract:
    """
    Mock LangExtract processor using simple heuristics.
    
    IMPORTANT: This is a placeholder for development!
    Replace with real LangExtract once available.
    
    Detection strategy (simple heuristics):
    - Dialogue: Look for quotation marks, dialogue punctuation
    - Register: Detect formal markers (titles, proper nouns) vs informal (contractions, slang)
    - Topic: Simple keyword matching
    - Code-switching: For now, just detect obvious non-English words
    """
    
    # Simple keyword-based topic detection
    TOPIC_KEYWORDS = {
        'education': ['school', 'student', 'teacher', 'learn', 'study', 'university', 'class'],
        'business': ['company', 'market', 'sell', 'buy', 'customer', 'profit', 'trade'],
        'health': ['hospital', 'doctor', 'patient', 'medicine', 'health', 'sick', 'treatment'],
        'technology': ['computer', 'software', 'internet', 'phone', 'app', 'digital', 'tech'],
        'politics': ['government', 'president', 'minister', 'parliament', 'election', 'policy'],
        'sports': ['game', 'team', 'player', 'match', 'score', 'championship', 'coach'],
        'casual': ['hey', 'yeah', 'gonna', 'wanna', 'kinda', 'anyway', 'whatever'],
    }
    
    # Formal markers
    FORMAL_MARKERS = ['Mr.', 'Mrs.', 'Dr.', 'Professor', 'Minister', 'Honorable', 'furthermore', 'therefore', 'consequently']
    
    # Informal markers
    INFORMAL_MARKERS = ["can't", "won't", "don't", "isn't", "ain't", "gonna", "wanna", "yeah", "nah", "yo", "bro"]
    
    def __init__(self, language: str = "en", dialect: str = "en-US"):
        """
        Initialize mock extractor.
        
        Args:
            language: Target language code
            dialect: Target dialect code
        """
        self.language = language
        self.dialect = dialect
    
    def process_chunk(self, text: str) -> List[LangExtractResult]:
        """
        Process a text chunk and extract labeled segments.
        
        Args:
            text: Chunk of text to process
            
        Returns:
            List of labeled segments with grounded offsets
        """
        results = []
        
        # Split into sentences (simple sentence boundary detection)
        sentences = self._split_sentences(text)
        
        for sentence, start, end in sentences:
            # Skip empty or very short sentences
            if len(sentence.strip()) < 10:
                continue
            
            # Detect dialogue
            is_dialogue = self._is_dialogue(sentence)
            
            # Detect topic
            topic = self._detect_topic(sentence)
            
            # Detect register
            register = self._detect_register(sentence)
            
            # Detect code-switching (simplified: look for non-ASCII as proxy)
            code_switch_spans = self._detect_code_switching(sentence, start)
            
            results.append(LangExtractResult(
                text=sentence,
                start=start,
                end=end,
                is_dialogue=is_dialogue,
                topic=topic,
                register_type=register,
                code_switch_spans=code_switch_spans,
            ))
        
        return results
    
    def _split_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Split text into sentences with offsets.
        
        Returns:
            List of (sentence_text, start_offset, end_offset)
        """
        # Simple sentence splitting on common punctuation
        # In production, use proper sentence tokenizer
        pattern = r'[.!?]+\s+'
        sentences = []
        last_end = 0
        
        for match in re.finditer(pattern, text):
            end = match.end()
            sentence = text[last_end:end].strip()
            if sentence:
                sentences.append((sentence, last_end, end))
            last_end = end
        
        # Add final sentence if any
        if last_end < len(text):
            sentence = text[last_end:].strip()
            if sentence:
                sentences.append((sentence, last_end, len(text)))
        
        return sentences
    
    def _is_dialogue(self, text: str) -> bool:
        """Detect if text is dialogue using simple heuristics"""
        # Look for quotation marks
        if '"' in text or "'" in text:
            return True
        
        # Look for dialogue patterns
        dialogue_patterns = [
            r'\b(said|asked|replied|answered|responded|exclaimed|shouted|whispered)\b',
            r'^"',  # Starts with quote
            r':\s*"',  # Colon followed by quote
        ]
        
        for pattern in dialogue_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _detect_topic(self, text: str) -> Optional[str]:
        """Detect topic using keyword matching"""
        text_lower = text.lower()
        topic_scores = {}
        
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            # Return topic with highest score
            return max(topic_scores, key=topic_scores.get)
        
        return None
    
    def _detect_register(self, text: str) -> str:
        """Detect formal vs informal register"""
        formal_count = sum(1 for marker in self.FORMAL_MARKERS if marker in text)
        informal_count = sum(1 for marker in self.INFORMAL_MARKERS if marker.lower() in text.lower())
        
        if formal_count > informal_count:
            return "formal"
        elif informal_count > 0:
            return "informal"
        else:
            return "neutral"
    
    def _detect_code_switching(self, text: str, base_offset: int) -> List[Tuple[int, int]]:
        """
        Detect code-switching spans (simplified).
        
        In production, this would use language ID on word level.
        For now, we just detect non-ASCII as a simple proxy.
        """
        spans = []
        
        # Find sequences of non-ASCII characters
        for match in re.finditer(r'[^\x00-\x7F]+', text):
            start = base_offset + match.start()
            end = base_offset + match.end()
            spans.append((start, end))
        
        return spans

