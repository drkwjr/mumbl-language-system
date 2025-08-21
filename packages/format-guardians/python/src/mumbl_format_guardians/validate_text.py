import json
from typing import Iterable
from mumbl_format_guardians.common import ValidationReport
from mumbl_data_contracts.segments import TextSegment

REQUIRED_LABELS = ["is_dialogue"]

def validate_text_jsonl(lines: Iterable[str]) -> ValidationReport:
    rep = ValidationReport(ok=True, checked=0)
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            rep.fail("JSON_DECODE", f"Line {i}: {e}", path=f"[{i}]")
            continue
        try:
            ts = TextSegment(**obj)
            # Required labels present
            for k in REQUIRED_LABELS:
                if getattr(ts.labels, k, None) is None:
                    rep.fail("LABEL_MISSING", f"Missing labels.{k}", path=f"[{i}].labels.{k}")
            # Grounding check
            if ts.source_ref.start >= ts.source_ref.end:
                rep.fail("GROUNDING_OFFSETS", "start >= end", path=f"[{i}].source_ref")
        except Exception as e:
            rep.fail("CONTRACT", f"Line {i} failed TextSegment schema: {e}", path=f"[{i}]")
        rep.checked += 1
    return rep
