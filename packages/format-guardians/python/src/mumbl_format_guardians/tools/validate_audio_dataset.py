import argparse, sys, os
from mumbl_format_guardians.validate_audio import validate_audio_dataset

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips_dir", required=True)
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()
    rep = validate_audio_dataset(args.clips_dir, args.csv)
    if rep.ok:
        print(f"OK: {rep.checked} rows validated")
        sys.exit(0)
    else:
        for e in rep.errors:
            print(f"[{e.code}] {e.message} @ {e.path}", file=sys.stderr)
        sys.exit(1)
