"""Optional radio ingest smoke test (requires live streams + deps)."""

import os
import subprocess

import pytest


def test_radio_ingest_smoke():
    if os.getenv("RUN_RADIO_INGEST_SMOKE") != "1":
        pytest.skip("Set RUN_RADIO_INGEST_SMOKE=1 to enable live ingest test.")

    result = subprocess.run(
        ["python", "scripts/run_radio_ingest_once.py"],
        check=False,
        capture_output=False,
    )
    assert result.returncode == 0

    validation = subprocess.run(
        ["python", "scripts/validate_radio_ingest.py"],
        check=False,
        capture_output=False,
    )
    assert validation.returncode == 0
