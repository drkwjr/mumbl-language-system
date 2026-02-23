"""Text chunking with overlap for context preservation"""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class TextChunk:
    """A chunk of text with its position in the original document"""

    text: str
    start: int  # Character offset in original
    end: int  # Character offset in original
    chunk_index: int


class TextChunker:
    """
    Splits text into overlapping chunks to preserve context.

    Why overlap? LangExtract needs context to accurately label dialogue and
    determine register/topic. Overlapping chunks ensure sentences at chunk
    boundaries have sufficient context.
    """

    def __init__(self, chunk_size: int = 2000, overlap: int = 200):
        """
        Args:
            chunk_size: Target characters per chunk
            overlap: Characters to overlap between chunks
        """
        if overlap >= chunk_size:
            raise ValueError("overlap must be less than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.stride = chunk_size - overlap

    def chunk(self, text: str) -> List[TextChunk]:
        """
        Split text into overlapping chunks.

        Strategy:
        1. Split on natural boundaries (paragraph breaks) when possible
        2. Preserve overlap for context
        3. Track exact character offsets for grounding validation

        Args:
            text: Full document text

        Returns:
            List of TextChunk objects with positions
        """
        if not text:
            return []

        chunks = []
        chunk_index = 0
        start = 0

        while start < len(text):
            # Calculate end of this chunk
            end = min(start + self.chunk_size, len(text))

            # If not at document end, try to break at sentence/paragraph boundary
            if end < len(text):
                end = self._find_break_point(text, start, end)

            # Extract chunk text
            chunk_text = text[start:end]

            chunks.append(TextChunk(text=chunk_text, start=start, end=end, chunk_index=chunk_index))

            chunk_index += 1

            # Move to next chunk with overlap
            if end >= len(text):
                break
            start = end - self.overlap

        return chunks

    def _find_break_point(self, text: str, start: int, target_end: int) -> int:
        """
        Find a natural break point near target_end.

        Priority:
        1. Paragraph break (double newline)
        2. Single newline
        3. Period + space
        4. Any whitespace
        5. Target end (if no good break found)
        """
        # Search window: target_end ± 100 chars
        search_start = max(start, target_end - 100)
        search_end = min(len(text), target_end + 100)
        window = text[search_start:search_end]

        # Try to find paragraph break
        para_break = window.rfind("\n\n")
        if para_break != -1:
            return search_start + para_break + 2

        # Try newline
        newline = window.rfind("\n")
        if newline != -1:
            return search_start + newline + 1

        # Try sentence end
        sentence_end = window.rfind(". ")
        if sentence_end != -1:
            return search_start + sentence_end + 2

        # Try any whitespace
        space = window.rfind(" ")
        if space != -1:
            return search_start + space + 1

        # No good break found, use target
        return target_end

    def merge_chunk_offsets(
        self, chunk: TextChunk, local_offset: Tuple[int, int]
    ) -> Tuple[int, int]:
        """
        Convert chunk-local offsets to document-global offsets.

        This is critical for grounding validation - LangExtract returns
        offsets relative to the chunk it processed, but we need global
        offsets for the full document.

        Args:
            chunk: The chunk that was processed
            local_offset: (start, end) relative to chunk

        Returns:
            (start, end) relative to full document
        """
        local_start, local_end = local_offset
        return (chunk.start + local_start, chunk.start + local_end)
