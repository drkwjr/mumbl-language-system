import argparse, sys, json
from mumbl_format_guardians.validate_profile import validate_profile_json_str

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", required=True)
    args = ap.parse_args()
    try:
        with open(args.path, "r", encoding="utf-8") as f:
            s = f.read()
        validate_profile_json_str(s)
        print("OK:", args.path)
        sys.exit(0)
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
