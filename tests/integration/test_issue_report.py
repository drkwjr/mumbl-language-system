"""
Test Results and Issues Report

Run: python -m pytest tests/integration/ -v
"""

import pytest
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "audio-lane" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "curator" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "tts-trainer" / "src"))

def test_issue_report():
    """Generate a comprehensive issue report."""
    issues = []
    
    # Issue 1: Missing dependencies
    missing_deps = []
    try:
        import yt_dlp
    except ImportError:
        missing_deps.append("yt-dlp (for YouTube downloader)")
    
    try:
        import librosa
    except ImportError:
        missing_deps.append("librosa (for audio processing)")
    
    try:
        import soundfile
    except ImportError:
        missing_deps.append("soundfile (for audio I/O)")
    
    try:
        import pyannote
    except ImportError:
        missing_deps.append("pyannote.audio (for speaker diarization)")
    
    try:
        import sentence_transformers
    except ImportError:
        missing_deps.append("sentence-transformers (for embeddings)")
    
    try:
        import yaml
    except ImportError:
        missing_deps.append("pyyaml (for config files)")
    
    if missing_deps:
        issues.append({
            'type': 'missing_dependencies',
            'severity': 'high',
            'description': f'Missing required dependencies: {", ".join(missing_deps)}',
            'fix': 'Run: pip install yt-dlp librosa soundfile pyannote.audio sentence-transformers pyyaml'
        })
    
    # Issue 2: Type hint issues
    try:
        from audio_lane.segmenter import segment_audio
        import inspect
        sig = inspect.signature(segment_audio)
        # Check for 'any' vs 'Any'
        import ast
        source_file = Path(__file__).parent.parent.parent / "apps" / "audio-lane" / "src" / "audio_lane" / "segmenter.py"
        if source_file.exists():
            content = source_file.read_text()
            if "Dict[str, any]" in content:
                issues.append({
                    'type': 'type_hint_error',
                    'severity': 'medium',
                    'description': "segmenter.py uses 'any' instead of 'Any' in type hints",
                    'location': 'apps/audio-lane/src/audio_lane/segmenter.py:13',
                    'fix': "Change 'any' to 'Any' and add 'from typing import Any'"
                })
    except Exception:
        pass
    
    # Issue 3: Import path issues in flows
    try:
        from mumbl_orchestration.flows_audio import audio_lane_flow
        # Check if import fallback works
        import audio_lane.processor
    except ImportError:
        issues.append({
            'type': 'import_path_issue',
            'severity': 'high',
            'description': 'flows_audio.py tries to import audio_lane but path may not be in sys.path',
            'location': 'packages/orchestration/python/src/mumbl_orchestration/flows_audio.py',
            'fix': 'Need to ensure audio-lane package is installed or sys.path is set correctly'
        })
    
    # Issue 4: Database connection handling
    # Check if get_connection is used correctly
    from mumbl_storage.db import get_connection
    # This should work - it's a context manager
    
    # Issue 5: Recursive call in segmenter
    try:
        source_file = Path(__file__).parent.parent.parent / "apps" / "audio-lane" / "src" / "audio_lane" / "segmenter.py"
        if source_file.exists():
            content = source_file.read_text()
            if "segment_audio(" in content and content.count("segment_audio(") > 1:
                issues.append({
                    'type': 'recursive_call_risk',
                    'severity': 'low',
                    'description': 'segment_audio may call itself recursively - ensure base case handles correctly',
                    'location': 'apps/audio-lane/src/audio_lane/segmenter.py',
                    'fix': 'Review recursive logic for long segments'
                })
    except Exception:
        pass
    
    # Print issues
    print("\n" + "="*70)
    print("ISSUE REPORT")
    print("="*70 + "\n")
    
    if not issues:
        print("✅ No issues found!")
        return
    
    for i, issue in enumerate(issues, 1):
        print(f"Issue #{i}: {issue['type'].upper()}")
        print(f"  Severity: {issue['severity']}")
        print(f"  Description: {issue['description']}")
        if 'location' in issue:
            print(f"  Location: {issue['location']}")
        if 'fix' in issue:
            print(f"  Fix: {issue['fix']}")
        print()
    
    # Summary
    high = sum(1 for i in issues if i['severity'] == 'high')
    medium = sum(1 for i in issues if i['severity'] == 'medium')
    low = sum(1 for i in issues if i['severity'] == 'low')
    
    print("="*70)
    print(f"Summary: {len(issues)} issues found ({high} high, {medium} medium, {low} low)")
    print("="*70)

if __name__ == "__main__":
    test_issue_report()

