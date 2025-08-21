# Runbook — curator

**Input**: TextSegment JSONL, AudioSegment CSV + clips  
**Output**: Scored segments, dataset snapshots with cards

## Steps

1) Score subscores: clarity, alignment, diarization, transcript accuracy, validity, shape.  
2) Compute total and thresholds.  
3) Deduplicate: exact hash, audio fingerprint, near-dup by embeddings.  
4) Policy filters.  
5) Snapshot with audit trail and metrics card.
