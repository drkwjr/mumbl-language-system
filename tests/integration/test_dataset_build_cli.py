import json, os, tempfile, subprocess, sys
from pathlib import Path

def test_dataset_build_from_manifest(tmp_path: Path):
    # write small manifest
    man = tmp_path/"manifest.jsonl"
    man.write_text('{"wav":"clips/a.wav","sample_rate":24000,"duration_s":2.2,"text":"hi","speaker_id":"spk"}\n')
    out = tmp_path/"out"
    cmd = [sys.executable, "-m", "mumbl_dataset_builder.tools.dataset_build", "tts",
           "--input-manifest", str(man), "--out-dir", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (out/"metadata.csv").exists()
    assert (out/"manifest.jsonl").exists()
    assert (out/"dataset_card.json").exists()
