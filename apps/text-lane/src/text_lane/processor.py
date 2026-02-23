"""Text Lane Processor - Orchestrates chunking, labeling, and storage"""

import hashlib
from typing import Any, Dict, List, Optional

from mumbl_data_contracts.segments import Labels, SourceRef, TextSegment
from mumbl_storage.db import DatabaseConfig, get_connection
from mumbl_storage.repositories import TextSegmentRepository
from text_lane.chunker import TextChunker
from text_lane.langextract import LangExtractResult, MockLangExtract


class TextLaneProcessor:
    """
    Main text lane processor.

    Flow:
    1. Chunk document with overlap
    2. Process each chunk with LangExtract
    3. Convert to TextSegment contracts
    4. Validate and store in database
    5. Generate JSONL output
    """

    def __init__(
        self,
        language: str,
        dialect: str,
        chunk_size: int = 2000,
        overlap: int = 200,
        db_config: Optional[DatabaseConfig] = None,
    ):
        """
        Initialize processor.

        Args:
            language: Target language code (e.g., 'en', 'ak')
            dialect: Target dialect code (e.g., 'en-US', 'ak-GH')
            chunk_size: Characters per chunk
            overlap: Overlap between chunks for context
            db_config: Database configuration (uses env if None)
        """
        self.language = language
        self.dialect = dialect
        self.chunker = TextChunker(chunk_size=chunk_size, overlap=overlap)
        self.extractor = MockLangExtract(language=language, dialect=dialect)
        self.db_config = db_config or DatabaseConfig.from_env()

    def process_document(
        self, text: str, doc_id: str, batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a full document through the text lane.

        Args:
            text: Full document text
            doc_id: Unique document identifier
            batch_id: Batch ID for tracking (optional)

        Returns:
            Processing result with stats and segment IDs
        """
        # Step 1: Chunk the document
        chunks = self.chunker.chunk(text)

        # Step 2: Process each chunk
        all_segments = []
        for chunk in chunks:
            # Extract labeled segments from chunk
            results = self.extractor.process_chunk(chunk.text)

            # Convert to TextSegment contracts with global offsets
            for result in results:
                # Convert chunk-relative offsets to document-global offsets
                global_start, global_end = self.chunker.merge_chunk_offsets(
                    chunk, (result.start, result.end)
                )

                segment = TextSegment(
                    text=result.text,
                    lang=self.language,
                    labels=Labels(
                        is_dialogue=result.is_dialogue,
                        topic=result.topic,
                        register_type=result.register_type,
                        code_switch_spans=result.code_switch_spans or [],
                    ),
                    source_ref=SourceRef(doc_id=doc_id, start=global_start, end=global_end),
                )

                all_segments.append(segment)

        # Step 3: Store in database
        segment_ids = self._store_segments(all_segments, batch_id)

        # Step 4: Compile stats
        stats = self._compile_stats(all_segments, segment_ids)

        return {
            "status": "success",
            "doc_id": doc_id,
            "batch_id": batch_id,
            "total_chunks": len(chunks),
            "total_segments": len(all_segments),
            "segments_inserted": sum(1 for sid in segment_ids if sid is not None),
            "segments_duplicate": sum(1 for sid in segment_ids if sid is None),
            "stats": stats,
            "segment_ids": [sid for sid in segment_ids if sid is not None],
        }

    def _store_segments(
        self, segments: List[TextSegment], batch_id: Optional[str]
    ) -> List[Optional[int]]:
        """
        Store segments in database.

        Returns:
            List of segment IDs (None for duplicates that were skipped)
        """
        with get_connection(self.db_config) as conn:
            repo = TextSegmentRepository(conn)
            segment_ids = repo.insert_many(segments, batch_id=batch_id)

        return segment_ids

    def _compile_stats(
        self, segments: List[TextSegment], segment_ids: List[Optional[int]]
    ) -> Dict[str, Any]:
        """Compile statistics about processed segments"""
        dialogue_count = sum(1 for s in segments if s.labels.is_dialogue)

        # Count by topic
        topic_counts = {}
        for s in segments:
            if s.labels.topic:
                topic_counts[s.labels.topic] = topic_counts.get(s.labels.topic, 0) + 1

        # Count by register
        register_counts = {}
        for s in segments:
            if s.labels.register_type:
                register_counts[s.labels.register_type] = (
                    register_counts.get(s.labels.register_type, 0) + 1
                )

        return {
            "dialogue_segments": dialogue_count,
            "non_dialogue_segments": len(segments) - dialogue_count,
            "topics": topic_counts,
            "registers": register_counts,
            "avg_segment_length": (
                sum(len(s.text) for s in segments) / len(segments) if segments else 0
            ),
        }

    def export_jsonl(self, segments: List[TextSegment], output_path: str) -> None:
        """
        Export segments to JSONL format for validation and archival.

        Args:
            segments: List of TextSegment objects
            output_path: Path to output .jsonl file
        """
        import json

        with open(output_path, "w", encoding="utf-8") as f:
            for segment in segments:
                # Convert to dict using Pydantic's model_dump
                segment_dict = segment.model_dump(mode="json")
                f.write(json.dumps(segment_dict, ensure_ascii=False) + "\n")
