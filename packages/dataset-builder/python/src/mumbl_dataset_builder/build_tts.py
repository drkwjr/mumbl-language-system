import csv, json, os
from typing import List, Dict, Optional
from .lints import lint_tts_manifest, LintIssue, LintReport

def build_metadata_csv(out_dir: str, manifest_rows: List[Dict], use_phonemes: bool = False):
    os.makedirs(os.path.join(out_dir, "clips"), exist_ok=True)
    csv_path = os.path.join(out_dir, "metadata.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="|")
        for r in manifest_rows:
            path = r["wav"]  # should be relative like "clips/uuid.wav"
            textfield = r.get("phonemes") if use_phonemes else r.get("text", "")
            spk = r.get("speaker_id", "spk_unknown")
            w.writerow([path, textfield, spk])
    return csv_path

def write_manifest_jsonl(out_dir: str, manifest_rows: List[Dict]):
    path = os.path.join(out_dir, "manifest.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in manifest_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path

def write_dataset_card(out_dir: str, stats: Dict):
    path = os.path.join(out_dir, "dataset_card.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return path

def build_tts_snapshot(out_dir: str, manifest_rows: List[Dict], use_phonemes: bool=False):
    lint = lint_tts_manifest(manifest_rows)
    if not lint.ok:
        msgs = "\n".join(f"[{i.code}] {i.msg}" for i in lint.issues)
        raise SystemExit(f"Dataset lints failed:\n{msgs}")
    mpath = write_manifest_jsonl(out_dir, manifest_rows)
    cpath = build_metadata_csv(out_dir, manifest_rows, use_phonemes=use_phonemes)
    # minimal stats
    stats = {
        "clips": len(manifest_rows),
        "sample_rate": list({r["sample_rate"] for r in manifest_rows}),
        "minutes": sum(float(r["duration_s"]) for r in manifest_rows)/60.0
    }
    dpath = write_dataset_card(out_dir, stats)
    return {"manifest": mpath, "metadata_csv": cpath, "dataset_card": dpath}
