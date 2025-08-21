import json
from mumbl_format_guardians.common import ValidationReport

FIELDS = ["clarity","alignment","diarization","transcript_accuracy","validity","shape","total"]

def validate_scores_json(lines):
    rep = ValidationReport(ok=True, checked=0)
    for i, line in enumerate(lines, start=1):
        line=line.strip()
        if not line: continue
        try:
            obj = json.loads(line)
        except Exception as e:
            rep.fail("JSON", f"Line {i}: {e}", path=f"[{i}]"); continue
        for k in FIELDS:
            v = obj.get(k)
            if v is None or not (0 <= float(v) <= 100):
                rep.fail("SCORE_RANGE", f"{k} must be 0..100", path=f"[{i}].{k}")
        rep.checked += 1
    return rep
