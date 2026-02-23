"""
Dataset loader for TTS training.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List


def load_dataset(manifest_path: str) -> List[Dict[str, Any]]:
    """
    Load dataset from manifest file.

    Args:
        manifest_path: Path to JSONL manifest file

    Returns:
        List of dataset entries with audio paths and transcripts
    """
    entries = []

    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line: {line[:50]}... Error: {e}")
                continue

    return entries


def validate_dataset_format(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate dataset format and return statistics.

    Args:
        entries: List of dataset entries

    Returns:
        Dict with validation results and statistics
    """
    stats = {
        "total_entries": len(entries),
        "valid_entries": 0,
        "invalid_entries": 0,
        "errors": [],
    }

    required_fields = ["audio_file", "transcript_text"]

    for idx, entry in enumerate(entries):
        is_valid = True
        errors = []

        # Check required fields
        for field in required_fields:
            if field not in entry:
                is_valid = False
                errors.append(f"Missing required field: {field}")

        # Check audio file exists
        if "audio_file" in entry:
            audio_path = entry["audio_file"]
            if not os.path.exists(audio_path):
                is_valid = False
                errors.append(f"Audio file not found: {audio_path}")

        # Check transcript is not empty
        if "transcript_text" in entry:
            transcript = entry.get("transcript_text", "").strip()
            if not transcript:
                is_valid = False
                errors.append("Empty transcript")

        if is_valid:
            stats["valid_entries"] += 1
        else:
            stats["invalid_entries"] += 1
            stats["errors"].append(
                {
                    "entry_index": idx,
                    "errors": errors,
                }
            )

    return stats
