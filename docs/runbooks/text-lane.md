# Runbook — text-lane

**Input**: raw text artifacts with metadata  
**Output**: `text_dialogue_corpus.jsonl` (TextSegment)

## Steps

1) Chunk with overlap.  
2) LangExtract schemas: dialogue detection, topic + register, code-switch spans.  
3) Validate grounding (offsets required).  
4) Emit JSONL and HTML spot-checks.  
5) Contract validation.

## Operational notes

- Parallelize by chunk.  
- Fail batch if grounding or validation fails.  
- Store artifacts in object storage with batch ID.

## Orchestration

Launch via API:
```bash
curl -X POST http://localhost:8000/flows/text \
-H "Content-Type: application/json" \
-d @docs/examples/batch-manifest.json
```
