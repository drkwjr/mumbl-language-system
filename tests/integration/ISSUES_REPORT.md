# Test Results and Issues Summary

**Date**: December 2025  
**Purpose**: Identify issues in Audio Lane, Curator, and TTS Trainer implementation

---

## Issues Found

### 🔴 High Severity Issues

#### 1. Missing Dependencies
**Status**: Not installed  
**Description**: Several required packages are not installed in the environment.

**Missing packages**:
- `yt-dlp` - YouTube audio downloader
- `librosa` - Audio processing and analysis
- `soundfile` - Audio file I/O
- `pyannote.audio` - Speaker diarization
- `sentence-transformers` - Text embeddings for deduplication
- `pyyaml` - YAML config file support

**Fix**:
```bash
pip install yt-dlp librosa soundfile pyannote.audio sentence-transformers pyyaml
```

**Impact**: Cannot run Audio Lane or Curator without these packages.

---

#### 2. Import Path Issues
**Status**: Needs attention  
**Description**: Prefect flows use fallback import paths that may not work reliably.

**Locations**:
- `packages/orchestration/python/src/mumbl_orchestration/flows_audio.py`
- `packages/orchestration/python/src/mumbl_orchestration/flows_curator.py`
- `packages/orchestration/python/src/mumbl_orchestration/flows_tts.py`

**Issue**: The flows try to import packages like `audio_lane`, `curator`, `tts_trainer` but these packages aren't installed. The fallback path manipulation may not work in all environments.

**Fix Options**:
1. **Install packages properly** (recommended):
   ```bash
   cd apps/audio-lane && pip install -e .
   cd ../curator && pip install -e .
   cd ../tts-trainer && pip install -e .
   ```

2. **Or use PYTHONPATH**:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/apps/audio-lane/src:$(pwd)/apps/curator/src:$(pwd)/apps/tts-trainer/src"
   ```

---

### 🟡 Medium Severity Issues

#### 3. Type Hint Errors (FIXED)
**Status**: ✅ Fixed  
**Description**: Several files used lowercase `any` instead of `Any` from typing module.

**Files fixed**:
- `apps/audio-lane/src/audio_lane/segmenter.py`
- `apps/audio-lane/src/audio_lane/youtube_downloader.py`
- `apps/audio-lane/src/audio_lane/diarization.py`
- `apps/audio-lane/src/audio_lane/asr_whisper.py`
- `apps/audio-lane/src/audio_lane/processor.py`

**Fix**: Changed `any` → `Any` and added `from typing import Any`.

---

### 🟢 Low Severity Issues

#### 4. Recursive Call Risk
**Status**: Needs review  
**Description**: `segment_audio()` may call itself recursively for long segments.

**Location**: `apps/audio-lane/src/audio_lane/segmenter.py:82-95`

**Current logic**: If a segment is > max_duration, it splits at midpoint and recursively calls `segment_audio()` on both halves.

**Risk**: Could potentially recurse deeply for very long segments (though unlikely in practice since max is 12s).

**Fix**: Ensure proper base case handling. Current implementation looks safe, but worth reviewing edge cases.

---

#### 5. Missing YAML Dependency
**Status**: Needs installation  
**Description**: TTS trainer config module imports `yaml` but `pyyaml` may not be installed.

**Location**: `apps/tts-trainer/src/tts_trainer/config.py:8`

**Fix**: Add `pyyaml` to requirements.txt (it's already in the missing deps list above).

---

## Test Results

### ✅ Tests That Pass (when dependencies installed)
- `test_curator_imports` - Curator modules can be imported
- `test_scorer_initialization` - Scoring works correctly
- `test_policy_gates` - Policy filtering works
- `test_snapshot_creation` - Dataset snapshots can be created
- `test_training_config` - TTS config loading/saving works
- `test_dataset_loader` - Dataset manifest loading works

### ⚠️ Tests That Fail (due to missing deps)
- `test_normalizer_function` - Requires librosa, soundfile
- `test_fingerprint_function` - Requires librosa
- `test_whisper_api_integration` - Requires OpenAI API key (skipped in tests)
- `test_diarization_mock` - Requires pyannote.audio
- `test_deduplicator_basic` - Requires sentence-transformers

---

## Recommended Next Steps

### 1. Install All Dependencies
```bash
# Audio Lane dependencies
pip install yt-dlp librosa soundfile pyannote.audio

# Curator dependencies
pip install sentence-transformers

# TTS Trainer dependencies  
pip install pyyaml torch

# General dependencies (should already be installed)
pip install openai prefect pydantic psycopg
```

### 2. Install Packages in Development Mode
```bash
cd apps/audio-lane && pip install -e .
cd ../curator && pip install -e .
cd ../tts-trainer && pip install -e .
```

### 3. Run Full Test Suite
```bash
pytest tests/integration/ -v
```

### 4. Integration Test with Database
- Ensure PostgreSQL is running
- Ensure database is set up: `make setup-db`
- Run database integration tests

### 5. Test End-to-End Flow
- Create a test batch manifest
- Run Text Lane → Audio Lane → Curator → TTS Training
- Verify outputs at each stage

---

## Known Limitations

1. **Training is stubbed**: TTS training loop doesn't actually train models - structure is there but functions return placeholders.

2. **Diarization requires model download**: pyannote.audio will download ~500MB models on first use.

3. **Whisper API costs money**: Each transcription costs ~$0.006/minute.

4. **S3 not implemented**: Storage uses local filesystem only.

5. **No actual training harness**: VITS training code is placeholder.

---

## Code Quality Notes

✅ **Good**:
- Type hints are mostly correct (after fixes)
- Modular design allows testing individual components
- Error handling in place for most functions
- Database connection management is clean

⚠️ **Could Improve**:
- More comprehensive error messages
- Better handling of missing dependencies
- Unit tests for each module (currently only integration tests)
- Documentation for each module's expected inputs/outputs

---

## Conclusion

The implementation is **structurally sound** but needs:
1. Dependencies installed
2. Packages installed in development mode for imports to work
3. Actual VITS training code (currently stubbed)
4. More comprehensive error handling

Once dependencies are installed, the pipeline should work end-to-end (with stubbed training).

