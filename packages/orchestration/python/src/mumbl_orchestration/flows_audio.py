from prefect import flow, task
from mumbl_orchestration.batch_types import BatchManifest
import yt_dlp
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import (
    AudioSegmentRepository,
    SegmentLanguageVerificationRepository,
    PipelineEventRepository,
)
from mumbl_format_guardians.validate_audio import validate_audio_dataset

# Import audio lane modules - package should be installed
try:
    from audio_lane.processor import AudioLaneProcessor
    from audio_lane.llm_verifier import create_transcript_verifier
except ImportError as e:
    raise ImportError(
        f"Could not import audio_lane. Install with: pip install -e apps/audio-lane"
    ) from e


@task
def preflight(man: BatchManifest) -> BatchManifest:
    """
    Preflight: Probe YouTube URLs to estimate duration and cost.
    """
    total_duration = 0.0
    
    for input_item in man.inputs:
        url = input_item.uri
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                duration = info.get('duration', 0)
                total_duration += duration
        except Exception as e:
            # If probe fails, estimate conservatively
            total_duration += 300  # 5 minutes default
    
    # Estimate costs: Whisper API is ~$0.006 per minute
    hours_estimated = total_duration / 3600
    minutes_estimated = total_duration / 60
    cost_estimated = minutes_estimated * 0.006
    
    man.metrics["hours_estimated"] = hours_estimated
    man.metrics["minutes_estimated"] = minutes_estimated
    man.metrics["cost_estimated_usd"] = cost_estimated
    man.metrics["duration_seconds"] = total_duration
    
    return man


@task
def asr_diar_align_normalize(man: BatchManifest) -> BatchManifest:
    """
    Full Audio Lane pipeline: download → normalize → ASR → diarize → segment → store.
    """
    processor = AudioLaneProcessor()
    verifier = create_transcript_verifier()
    
    all_segments = []
    
    # Connect to database
    with get_connection() as conn:
        audio_repo = AudioSegmentRepository(conn)
        verification_repo = SegmentLanguageVerificationRepository(conn)
        event_repo = PipelineEventRepository(conn)
        
        for input_item in man.inputs:
            url = input_item.uri
            
            # Process YouTube URL
            result = processor.process_youtube(
                url=url,
                language=man.language,
                batch_id=man.batch_id,
                dialect=man.dialect
            )
            
            # Store segments in database
            segment_ids = audio_repo.insert_many(
                result['segments'],
                batch_id=man.batch_id
            )

            detected_language = result.get("detected_language")
            candidates = [man.language, detected_language]
            candidates = [c for c in candidates if c]

            for item, segment_id in zip(result['segments'], segment_ids):
                if not segment_id:
                    continue
                event_repo.insert(
                    stage="segments",
                    event_type="audio_segment_ingested",
                    status="success",
                    source_id=item.get("source_id"),
                    segment_id=segment_id,
                    count=1,
                    message="Audio segment ingested",
                    payload={
                        "batch_id": man.batch_id,
                        "source_type": item.get("source_type"),
                        "radio_segment_id": item.get("radio_segment_id"),
                        "shard_id": item.get("shard_id"),
                    },
                )

            if verifier.should_verify(man.language, detected_language):
                for item, segment_id in zip(result['segments'], segment_ids):
                    if not segment_id:
                        continue
                    segment = item.get("segment")
                    transcript_text = segment.transcript_text if segment else None
                    if not transcript_text:
                        continue

                    language, confidence, dialect, rationale = verifier.verify_transcript(
                        transcript=transcript_text,
                        expected_lang=man.language,
                        detected_lang=detected_language,
                        candidates=candidates,
                    )
                    if not language:
                        continue

                    verification_repo.insert(
                        segment_type="audio",
                        segment_id=segment_id,
                        source="llm",
                        provider=verifier.provider,
                        model=verifier.model,
                        candidates=candidates,
                        language=language,
                        dialect=dialect,
                        confidence=confidence,
                        rationale=rationale,
                    )

                    radio_segment_id = item.get("radio_segment_id")
                    if radio_segment_id:
                        verification_repo.insert(
                            segment_type="radio",
                            segment_id=radio_segment_id,
                            source="llm",
                            provider=verifier.provider,
                            model=verifier.model,
                            candidates=candidates,
                            language=language,
                            dialect=dialect,
                            confidence=confidence,
                            rationale=rationale,
                        )
            
            all_segments.extend(result['segments'])
            
            # Generate CSV export
            csv_path = result['outputs']['csv']
            audio_repo.export_to_csv(
                csv_path,
                batch_id=man.batch_id,
                lang=man.language
            )
            
            # Update manifest outputs
            man.outputs["csv"] = csv_path
            man.outputs["clips_dir"] = result['outputs']['clips_dir']
            
            # Update metrics
            man.metrics["clips"] = len(all_segments)
            man.metrics["segments_processed"] = len([sid for sid in segment_ids if sid is not None])
            man.metrics["segments_duplicates"] = len([sid for sid in segment_ids if sid is None])

            event_repo.insert(
                stage="asr",
                event_type="asr_completed",
                status="success",
                count=len([sid for sid in segment_ids if sid is not None]),
                duration_seconds=result["stats"].get("duration_seconds"),
                message="ASR completed for input",
                payload={
                    "batch_id": man.batch_id,
                    "language": man.language,
                    "dialect": man.dialect,
                    "detected_language": detected_language,
                },
            )
    
    return man


@task
def validate_audio_outputs(man: BatchManifest) -> BatchManifest:
    """
    Validate audio outputs (placeholder for format guardian integration).
    """
    csv_path = man.outputs.get("csv")
    clips_dir = man.outputs.get("clips_dir")
    if not csv_path or not clips_dir:
        man.metrics["validation_passed"] = 0.0
        man.metrics["validation_errors"] = 1
        man.metrics["validation_error_codes"] = ["MISSING_OUTPUTS"]
        return man

    report = validate_audio_dataset(clips_dir=clips_dir, csv_path=csv_path)
    man.metrics["validation_passed"] = 1.0 if report.ok else 0.0
    man.metrics["validation_errors"] = len(report.errors)
    man.metrics["validation_error_codes"] = [issue.code for issue in report.errors[:5]]
    
    return man


@flow(name="audio-lane")
def audio_lane_flow(manifest: dict) -> dict:
    """
    Audio Lane Prefect flow orchestrating the full pipeline.
    """
    man = BatchManifest(**manifest)
    
    # Run preflight
    man = preflight.submit(man).result()
    
    # Run main processing
    man = asr_diar_align_normalize.submit(man).result()
    
    # Validate outputs
    man = validate_audio_outputs.submit(man).result()
    
    man.status = "succeeded"
    return man.dict()
