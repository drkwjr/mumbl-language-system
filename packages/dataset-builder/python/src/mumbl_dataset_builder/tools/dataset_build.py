import argparse, json, os, sys
from typing import List, Dict
from mumbl_dataset_builder.build_tts import build_tts_snapshot

def _load_curated_manifest(path: str) -> List[Dict]:
    rows=[]
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            rows.append(json.loads(line))
    return rows

def main():
    ap = argparse.ArgumentParser(description="Build training dataset snapshots")
    sub = ap.add_subparsers(dest="cmd", required=True)

    tts = sub.add_parser("tts", help="Build TTS snapshot from curated manifest.jsonl")
    tts.add_argument("--input-manifest", required=True, help="Curated manifest.jsonl from curator")
    tts.add_argument("--out-dir", required=True, help="Output dataset directory (will be created)")
    tts.add_argument("--use-phonemes", action="store_true", help="Use phoneme strings for metadata.csv middle column")
    args = ap.parse_args()

    if args.cmd == "tts":
        rows = _load_curated_manifest(args.input_manifest)
        os.makedirs(args.out_dir, exist_ok=True)
        result = build_tts_snapshot(args.out_dir, rows, use_phonemes=args.use_phonemes)
        print("OK:", result)
        sys.exit(0)
