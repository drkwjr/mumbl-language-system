import argparse, sys
from mumbl_format_guardians.validate_scores import validate_scores_json

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    args = ap.parse_args()
    with open(args.path, "r", encoding="utf-8") as f:
        rep = validate_scores_json(f)
    if rep.ok:
        print(f"OK: {rep.checked} scores validated")
        sys.exit(0)
    else:
        for e in rep.errors:
            print(f"[{e.code}] {e.message} @ {e.path}", file=sys.stderr)
        sys.exit(1)
