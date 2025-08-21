# Data Contracts (V1)

Contracts are frozen in V1. Any breaking change requires a new version and a migration note.

## TextSegment (JSONL)
```json
{
  "text": "…",
  "lang": "ar",
  "labels": {
    "is_dialogue": true,
    "topic": "travel",
    "register": "informal",
    "code_switch_spans": [[123,148]]
  },
  "source_ref": {"doc_id":"SRC:abc123","start":110,"end":220}
}
```

## AudioSegment (CSV + WAV clips)

CSV columns:

* `audio_file,start,end,speaker_id,transcript_text,lang,dialect_probs,alignment_confidence,diarization_confidence,granularity`

Clips:

* mono WAV, 22.05 or 24 kHz, conservative trims, length 2–12 seconds.

## SegmentScore (JSON/DB)

```json
{
  "clarity": 92.5,
  "alignment": 88.0,
  "diarization": 90.0,
  "transcript_accuracy": 93.0,
  "validity": 100.0,
  "shape": 95.0,
  "total": 93.0,
  "eligible_learner": true,
  "eligible_training": true,
  "notes": "clean studio read"
}
```

## LanguageProfile (JSON/DB)

See `docs/architecture/conditioning.md` for fields and examples. Inheritance order:
Dialect → Language → Group.

## Runtime helpers

### ConversationTurn

```json
{
  "user_text": "Hi!",
  "bot_text": "Hello. How can I help?",
  "audio_url": "s3://…/hello.wav",
  "voice_id": "en-IE.mary.001",
  "style_tags": ["calm","conversational"],
  "tokens_used": 128
}
```

### VoiceSpec

```json
{
  "language": "en",
  "dialect": "en-IE",
  "voice_id": "en-IE.mary.001",
  "style_tags": ["calm","storytelling"],
  "speaking_rate": 1.0,
  "pause_bias": 0.1,
  "filler_bias": 0.05
}
```
