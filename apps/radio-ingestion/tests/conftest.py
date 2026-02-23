"""Pytest configuration and fixtures"""

import sys
from pathlib import Path

import pytest

# Add src to path so tests can import radio_ingestion
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))
