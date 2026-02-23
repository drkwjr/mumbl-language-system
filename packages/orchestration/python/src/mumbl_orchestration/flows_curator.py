from mumbl_orchestration.batch_types import BatchManifest
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import (
    AudioSegmentRepository,
    DatasetRepository,
    SegmentScoreRepository,
    TextSegmentRepository,
)
from prefect import flow, task

# Import curator modules - package should be installed
try:
    from curator.processor import CuratorProcessor
except ImportError as e:
    raise ImportError(f"Could not import curator. Install with: pip install -e apps/curator") from e


@task
def score_and_dedupe(man: BatchManifest) -> BatchManifest:
    """
    Score segments and perform deduplication.
    """
    processor = CuratorProcessor()

    # Connect to database
    with get_connection() as conn:
        text_repo = TextSegmentRepository(conn)
        audio_repo = AudioSegmentRepository(conn)
        score_repo = SegmentScoreRepository(conn)

        # Load segments from database
        text_segments_data = text_repo.get_by_batch(man.batch_id)
        audio_segments_data = audio_repo.get_by_batch(man.batch_id)

        # Convert to contract objects
        from mumbl_data_contracts.segments import AudioSegment, Labels, SourceRef, TextSegment

        text_segments = []
        for row in text_segments_data:
            text_segments.append(
                TextSegment(
                    text=row["text"],
                    lang=row["lang"],
                    labels=Labels(
                        is_dialogue=row["is_dialogue"],
                        topic=row.get("topic"),
                        register_type=row.get("register_type"),
                        code_switch_spans=row.get("code_switch_spans", []),
                    ),
                    source_ref=SourceRef(
                        doc_id=row["doc_id"],
                        start=row["start_offset"],
                        end=row["end_offset"],
                    ),
                )
            )

        audio_segments = []
        for row in audio_segments_data:
            audio_segments.append(
                {
                    "segment": AudioSegment(
                        audio_file=row["audio_file"],
                        start=row["start_time"],
                        end=row["end_time"],
                        speaker_id=row.get("speaker_id"),
                        transcript_text=row.get("transcript_text"),
                        lang=row.get("lang"),
                        alignment_confidence=row.get("alignment_confidence"),
                        diarization_confidence=row.get("diarization_confidence"),
                    ),
                    "audio_hash": row.get("audio_hash"),
                }
            )

        # Process through curator
        result = processor.process_segments(
            text_segments=text_segments,
            audio_segments=audio_segments,
            batch_id=man.batch_id,
            language=man.language,
            dialect=man.dialect,
            target="training",  # Default to training dataset
        )

        # Store scores in database
        # (In a full implementation, we'd store scores for all segments)

        # Store result in manifest
        man.metrics["text_segments_scored"] = result["stats"]["text_segments_scored"]
        man.metrics["audio_segments_scored"] = result["stats"]["audio_segments_scored"]
        man.metrics["eligible_segments"] = (
            result["stats"]["text_segments_eligible"] + result["stats"]["audio_segments_eligible"]
        )
        man.metrics["duplicates_removed"] = result["stats"]["exact_duplicates_removed"]

        # Store snapshot info for next step
        man.outputs["snapshot"] = result["snapshot"]

    return man


@task
def snapshot_and_register(man: BatchManifest) -> BatchManifest:
    """
    Create dataset snapshot and register in database.
    """
    snapshot = man.outputs.get("snapshot")
    if not snapshot:
        raise ValueError("No snapshot found in manifest outputs")

    # Connect to database
    with get_connection() as conn:
        dataset_repo = DatasetRepository(conn)

        # Register dataset snapshot
        dataset_id = dataset_repo.create_snapshot(
            name=f"{man.language}_{man.dialect}_{snapshot['version']}",
            language=man.language,
            dialect=man.dialect,
            dataset_type="tts_training",
            manifest_json=snapshot,
            version=snapshot["version"],
            description=f"TTS training dataset for {man.language} ({man.dialect})",
            artifact_uri=snapshot.get("snapshot_path"),
        )

        man.outputs["dataset_id"] = dataset_id
        man.outputs["dataset_dir"] = snapshot.get("snapshot_path", "")
        man.outputs["curated_manifest"] = snapshot.get("snapshot_path", "").replace(
            ".json", ".jsonl"
        )

    return man


@flow(name="curator")
def curator_flow(manifest: dict) -> dict:
    """
    Curator Prefect flow orchestrating scoring, deduplication, and dataset creation.
    """
    man = BatchManifest(**manifest)

    # Score and deduplicate
    man = score_and_dedupe.submit(man).result()

    # Create snapshot and register
    man = snapshot_and_register.submit(man).result()

    man.status = "succeeded"
    return man.dict()
