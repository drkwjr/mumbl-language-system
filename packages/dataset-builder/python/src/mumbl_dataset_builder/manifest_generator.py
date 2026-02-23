"""
Manifest generator: Convert curator dataset snapshots to TTS training format.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def generate_training_manifest(
    snapshot_path: str, output_path: Optional[str] = None, dataset_type: str = "tts_training"
) -> str:
    """
    Generate TTS training manifest from curator dataset snapshot.

    Args:
        snapshot_path: Path to dataset snapshot JSON file
        output_path: Path to write training manifest (auto-generated if None)
        dataset_type: Type of dataset ("tts_training", "tts_learner", etc.)

    Returns:
        Path to generated training manifest
    """
    # Load snapshot
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    # Generate output path if not provided
    if output_path is None:
        base_name = Path(snapshot_path).stem
        output_path = snapshot_path.replace(".json", "_training.jsonl")

    # Extract segment IDs from snapshot
    segment_ids = snapshot.get("segment_ids", [])

    # Generate manifest entries
    # Format: Each line is a JSON object with audio path, transcript, etc.
    manifest_entries = []

    for seg_id in segment_ids:
        # In a full implementation, we'd load segment data from database
        # For now, create placeholder entry structure
        entry = {
            "segment_id": seg_id,
            "dataset_type": dataset_type,
            # Additional fields would be populated from database
        }
        manifest_entries.append(entry)

    # Write JSONL manifest
    with open(output_path, "w", encoding="utf-8") as f:
        for entry in manifest_entries:
            json_line = json.dumps(entry, ensure_ascii=False)
            f.write(json_line + "\n")

    return output_path


def load_dataset_from_snapshot(snapshot_path: str, segment_repository=None) -> List[Dict[str, Any]]:
    """
    Load full dataset from snapshot manifest.

    Args:
        snapshot_path: Path to dataset snapshot JSON
        segment_repository: Repository for loading segment data (optional)

    Returns:
        List of segment dicts ready for training
    """
    # Load snapshot
    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    segment_ids = snapshot.get("segment_ids", [])

    # Load segments from database if repository provided
    if segment_repository:
        segments = []
        for seg_id in segment_ids:
            # Load segment data
            # This would need to be implemented based on repository interface
            pass
        return segments

    # Return placeholder structure
    return [{"segment_id": seg_id, "data": {}} for seg_id in segment_ids]
