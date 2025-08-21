# DB Schema — overview

Tables:
- `raw_artifacts(id, source, uri, meta, created_at)`
- `text_segments(id, doc_id, start, end, lang, labels_json, text, created_at)`
- `audio_segments(id, audio_file, start, end, speaker_id, transcript_text, lang, dialect_probs_json, align_conf, diar_conf, granularity, created_at)`
- `segment_scores(id, segment_id, clarity, alignment, diarization, transcript_accuracy, validity, shape, total, flags_json, created_at)`
- `language_profiles(id, dialect, profile_json, version, created_at, updated_at)`
- `datasets(id, name, description, manifest_json, created_at)`
- `voices(id, dialect, voice_id, model_id, minutes, mos_lite, stability, created_at)`
- `model_registry(id, kind, language, dialect, version, metrics_json, artifact_uri, created_at)`

Indexes:
- text_segments(doc_id, start)
- audio_segments(audio_file, start)
- segment_scores(segment_id)
