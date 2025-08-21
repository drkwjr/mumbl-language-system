from dataclasses import dataclass, field
from typing import List, Dict, Tuple

@dataclass
class LintIssue:
    code: str
    msg: str

@dataclass
class LintReport:
    ok: bool
    issues: List[LintIssue] = field(default_factory=list)

def lint_tts_manifest(rows: List[Dict]) -> LintReport:
    ok = True
    issues = []
    # Checks: single sample rate, duration bounds, non-empty text/phonemes if required
    srs = {r.get("sample_rate") for r in rows}
    if len(srs) > 1:
        ok = False; issues.append(LintIssue("SAMPLE_RATE_MIX","Multiple sample rates detected"))
    for r in rows:
        dur = float(r.get("duration_s", 0))
        if not (1.5 <= dur <= 14.0):
            ok = False; issues.append(LintIssue("DURATION", f"{r.get('wav')} duration {dur} out of bounds"))
        if not r.get("text") and not r.get("phonemes"):
            ok = False; issues.append(LintIssue("NO_TEXT_OR_PHONEMES", f"{r.get('wav')} missing text/phonemes"))
    return LintReport(ok=ok, issues=issues)
