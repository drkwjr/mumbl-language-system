"""
Radio Ingestion Flow - Integrates radio segments into Mumbl pipeline.
"""

from prefect import flow, task
from typing import List, Dict, Any, Optional
from mumbl_orchestration.batch_types import BatchManifest
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import AudioSegmentRepository

# Import radio ingestion adapter
try:
    from radio_ingestion.integration.pipeline_adapter import RadioPipelineAdapter, create_adapter
except ImportError as e:
    raise ImportError(
        f"Could not import radio_ingestion. Install with: pip install -e apps/radio-ingestion"
    ) from e


@task
def export_radio_segments(man: BatchManifest) -> BatchManifest:
    """
    Export high-quality radio segments for ASR processing.
    
    Reads radio_segments from database, filters by quality, converts to AudioSegment contracts.
    """
    adapter = create_adapter(
        min_speech_ratio=0.7,
        min_confidence=0.8
    )
    
    all_audio_segments = []
    
    with get_connection() as conn:
        # Batch export segments
        exported = adapter.batch_export_for_asr(
            db_conn=conn,
            source_id=None,  # Export from all sources
            min_confidence=0.8,
            limit=100  # Limit for initial batch
        )
        
        # Store in audio_segments table
        audio_repo = AudioSegmentRepository(conn)
        
        for item in exported:
            audio_segment = item["segment"]
            batch_id = item.get("batch_id", man.batch_id)
            
            # Extract metadata from item
            audio_hash = item.get("audio_hash")
            granularity = item.get("granularity", "sentence")
            sample_rate = item.get("sample_rate", 22050)
            dialect = item.get("dialect")
            
            # Insert with metadata (format matches audio-lane)
            segment_id = audio_repo.insert(
                audio_segment,
                batch_id=batch_id,
                audio_hash=audio_hash,
                dialect=dialect,
                granularity=granularity,
                sample_rate=sample_rate
            )
            
            if segment_id:
                all_audio_segments.append(audio_segment)
                # Store radio-specific metadata for tracking
                item["audio_segment_id"] = segment_id
    
    # Update manifest
    man.metrics["radio_segments_exported"] = len(all_audio_segments)
    man.metrics["radio_segments_total"] = len(exported)
    man.outputs["radio_segments"] = all_audio_segments
    
    return man


@task
def process_radio_with_asr(man: BatchManifest) -> BatchManifest:
    """
    Process exported radio segments through ASR.
    
    Note: This reuses existing audio-lane ASR infrastructure.
    Radio segments are already in audio_segments table and can be processed
    by the standard audio-lane flow.
    """
    # Radio segments are now in audio_segments table
    # The existing audio-lane flow can process them
    # This task is a placeholder for radio-specific ASR processing if needed
    
    man.metrics["asr_queued"] = man.metrics.get("radio_segments_exported", 0)
    
    return man


@flow(name="radio-ingestion")
def radio_ingestion_flow(manifest: dict) -> dict:
    """
    Radio Ingestion Prefect flow.
    
    Exports high-quality radio segments and feeds them into audio-lane pipeline.
    """
    man = BatchManifest(**manifest)
    
    # Export radio segments to audio_segments table
    man = export_radio_segments.submit(man).result()
    
    # Queue for ASR processing (or process directly)
    man = process_radio_with_asr.submit(man).result()
    
    man.status = "succeeded"
    return man.dict()


@flow(name="radio-to-audio-lane")
def radio_to_audio_lane_flow(
    batch_id: str,
    language: str,
    dialect: Optional[str] = None,
    min_confidence: float = 0.8,
    limit: Optional[int] = None
) -> dict:
    """
    Integrated flow: Export radio segments → Process through audio-lane → Curator.
    
    Args:
        batch_id: Batch ID for tracking
        language: Language code
        dialect: Optional dialect code
        min_confidence: Minimum confidence threshold
        limit: Maximum segments to process
    
    Returns:
        Flow result dictionary
    """
    from mumbl_orchestration.flows_audio import audio_lane_flow
    from mumbl_orchestration.flows_curator import curator_flow
    
    # Step 1: Export radio segments
    adapter = create_adapter(min_confidence=min_confidence)
    
    with get_connection() as conn:
        exported = adapter.batch_export_for_asr(
            db_conn=conn,
            min_confidence=min_confidence,
            limit=limit
        )
        
        if not exported:
            return {
                "status": "skipped",
                "message": "No high-quality segments found",
                "batch_id": batch_id
            }
        
        # Step 2: Store in audio_segments (already done by adapter)
        # Step 3: Process through audio-lane (for ASR if not already done)
        # For radio segments, ASR might already be in progress or completed
        # This flow assumes segments need ASR
        
        # Create audio-lane manifest
        audio_manifest = {
            "batch_id": batch_id,
            "lane": "audio",
            "language": language,
            "dialect": dialect or language,
            "inputs": [
                {
                    "uri": item["segment"].audio_file,
                    "doc_id": f"radio_segment_{item['radio_segment_id']}"
                }
                for item in exported[:limit] if limit
            ]
        }
        
        # Run audio-lane flow (will process ASR, diarization, etc.)
        audio_result = audio_lane_flow(audio_manifest)
        
        # Step 4: Run curator
        curator_manifest = {
            "batch_id": batch_id,
            "language": language,
            "dialect": dialect or language,
            "target": "training"
        }
        
        curator_result = curator_flow(curator_manifest)
        
        return {
            "status": "succeeded",
            "batch_id": batch_id,
            "radio_segments_exported": len(exported),
            "audio_lane_result": audio_result,
            "curator_result": curator_result
        }

