"""
Dataset snapshot creation and versioning.
"""

import os
import json
import re
from typing import List, Dict, Optional, Any
from datetime import datetime


class DatasetSnapshot:
    """
    Create and manage dataset snapshots with semantic versioning.
    """
    
    def __init__(self, output_dir: str = "data/datasets"):
        """
        Initialize snapshot manager.
        
        Args:
            output_dir: Base directory for dataset snapshots
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def create_snapshot(
        self,
        segment_ids: List[int],
        language: str,
        dialect: str,
        version: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a dataset snapshot.
        
        Args:
            segment_ids: List of segment IDs to include
            language: Language code
            dialect: Dialect code
            version: Semantic version (auto-increments if None)
            metadata: Additional metadata
            
        Returns:
            Snapshot metadata dict
        """
        # Generate version if not provided
        if version is None:
            version = self._get_next_version(language, dialect)
        
        # Create snapshot manifest
        snapshot = {
            'version': version,
            'language': language,
            'dialect': dialect,
            'segment_ids': segment_ids,
            'segment_count': len(segment_ids),
            'created_at': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
        }
        
        # Save snapshot metadata
        snapshot_filename = f"{language}_{dialect}_{version}.json"
        snapshot_path = os.path.join(self.output_dir, snapshot_filename)
        
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2)
        
        snapshot['snapshot_path'] = snapshot_path
        
        return snapshot
    
    def export_jsonl(
        self,
        snapshot: Dict[str, Any],
        segments_data: List[Dict[str, Any]]
    ) -> str:
        """
        Export snapshot to JSONL format.
        
        Args:
            snapshot: Snapshot metadata dict
            segments_data: List of segment dicts (from database)
            
        Returns:
            Path to exported JSONL file
        """
        version = snapshot['version']
        language = snapshot['language']
        dialect = snapshot['dialect']
        
        jsonl_filename = f"{language}_{dialect}_{version}.jsonl"
        jsonl_path = os.path.join(self.output_dir, jsonl_filename)
        
        # Filter segments by IDs in snapshot
        segment_ids_set = set(snapshot['segment_ids'])
        filtered_segments = [
            seg for seg in segments_data
            if seg.get('id') in segment_ids_set
        ]
        
        # Write JSONL
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for seg in filtered_segments:
                json_line = json.dumps(seg, ensure_ascii=False)
                f.write(json_line + '\n')
        
        return jsonl_path
    
    def _get_next_version(self, language: str, dialect: str) -> str:
        """
        Get next semantic version for language/dialect.
        
        Args:
            language: Language code
            dialect: Dialect code
            
        Returns:
            Semantic version string (e.g., "1.0.0")
        """
        # Look for existing snapshots
        prefix = f"{language}_{dialect}_"
        existing_files = [
            f for f in os.listdir(self.output_dir)
            if f.startswith(prefix) and f.endswith('.json')
        ]
        
        if not existing_files:
            return "1.0.0"
        
        # Extract versions (simple semantic version parsing)
        versions = []
        for filename in existing_files:
            # Extract version from filename: {lang}_{dialect}_{version}.json
            version_part = filename.replace('.json', '').replace(prefix, '')
            # Parse semantic version (major.minor.patch)
            match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_part)
            if match:
                major, minor, patch = map(int, match.groups())
                versions.append((major, minor, patch))
        
        if not versions:
            return "1.0.0"
        
        # Find latest version
        latest = max(versions)
        # Increment patch version
        next_version = f"{latest[0]}.{latest[1]}.{latest[2] + 1}"
        
        return next_version
    
    def list_snapshots(
        self,
        language: Optional[str] = None,
        dialect: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all snapshots, optionally filtered by language/dialect.
        
        Returns:
            List of snapshot metadata dicts
        """
        snapshots = []
        
        for filename in os.listdir(self.output_dir):
            if not filename.endswith('.json'):
                continue
            
            # Parse filename: {lang}_{dialect}_{version}.json
            parts = filename.replace('.json', '').split('_')
            if len(parts) < 3:
                continue
            
            file_lang = parts[0]
            file_dialect = parts[1]
            version = '_'.join(parts[2:])
            
            # Filter if requested
            if language and file_lang != language:
                continue
            if dialect and file_dialect != dialect:
                continue
            
            # Load snapshot
            snapshot_path = os.path.join(self.output_dir, filename)
            try:
                with open(snapshot_path, 'r', encoding='utf-8') as f:
                    snapshot = json.load(f)
                    snapshot['snapshot_path'] = snapshot_path
                    snapshots.append(snapshot)
            except:
                pass
        
        # Sort by version (newest first)
        snapshots.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return snapshots

