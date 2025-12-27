# Architecture Discussion: Path to TTS Training

**Context**: Decision log for the TTS training path and related pipeline choices.

**Date**: December 2025  
**Goal**: Set up complete pipeline so training COULD work (even if not training now)

---

## 🎯 **Your Decisions Confirmed**

### **1. LangExtract API Key**
- **Answer**: Needs `OPENAI_API_KEY` (you have it in .env)
- **Note**: LangExtract uses OpenAI for GPT-4o, or can use Gemini with different key
- **Action**: Load from .env when initializing RealLangExtract

### **2. Audio Sources**
- **Now**: YouTube links only ✅
- **Future**: Radio stations (FM/AM) - separate system to design later
- **Action**: Build YouTube downloader, note radio requirement for future

### **3. ASR Service**
- **Choice**: OpenAI Whisper API ✅
- **Cost**: ~$0.006 per minute
- **Action**: Integrate Whisper API

### **4. Diarization**
- **Requirement**: Multi-speaker support ✅
- **Reason**: No cleanly segregated data yet
- **Action**: Integrate pyannote.audio or AssemblyAI diarization

### **5. TTS Training**
- **Scope**: Full scaffold ✅
- **Action**: Build structure, configs, registry (actual training later)

---

## 🤔 **Architecture Questions to Resolve**

### **Question 1: Storage Strategy**

**Current State:**
- Database: PostgreSQL ✅ (metadata, segments, scores)
- Object Storage: Mentioned in docs but not implemented

**Audio Lane Needs:**
- Raw audio files (large, can delete after clips)
- Normalized clips (keep forever, used for training)
- CSV metadata (paired_speech_corpus.csv)

**Options:**
- **A)** Local file system (simple, works for dev)
- **B)** S3-compatible (MinIO, AWS S3, etc.)
- **C)** Hybrid (local for dev, S3 for prod)

**My Recommendation**: Start with **local filesystem** (`data/audio/`), add S3 abstraction layer later.

**Your Preference?**

---

### **Question 2: Diarization Service**

**Multi-speaker diarization options:**

**Option A: pyannote.audio** (Local, Free)
- ✅ Free, open source
- ✅ Good quality
- ⚠️ Requires GPU for speed
- ⚠️ Model downloads (~500MB)
- ⚠️ Setup complexity

**Option B: AssemblyAI** (API, Paid)
- ✅ Simple API integration
- ✅ Good quality, handles multiple speakers
- ✅ Fast
- 💰 Cost: ~$0.30/hour of audio
- ⚠️ Additional API key needed

**Option C: Hybrid**
- Start with pyannote.audio (local)
- Add AssemblyAI as fallback/option
- Let user choose in config

**My Recommendation**: Start with **pyannote.audio** (free, good quality), add AssemblyAI option later.

**Your Preference?**

---

### **Question 3: Audio Processing Pipeline**

**Your Spec Says:**
1. Preflight (duration/cost estimate)
2. Download audio
3. ASR + diarization
4. Segmentation (2-12 second clips)
5. Normalization (mono, 22.05/24 kHz)
6. Alignment (sentence/word level)
7. Emit CSV + clips

**Architecture Questions:**

**A) Processing Order:**
```
Option 1: ASR → Diarization → Segmentation → Normalization
Option 2: Download → Normalize → ASR → Diarization → Segmentation
```

**Which makes more sense?**
- Normalize before ASR? (cleaner audio = better transcription)
- Or normalize after segmentation? (process clips individually)

**My Recommendation**: Normalize **before ASR** (better transcription quality), then segment normalized audio.

**B) Clip Length Strategy:**
- Fixed 2-12 seconds?
- Sentence-based? (natural breaks)
- Overlap allowed? (context preservation)

**My Recommendation**: Sentence-based segmentation (natural breaks), enforce 2-12s bounds.

**Your Preference?**

---

### **Question 4: Curator Scoring Logic**

**Your Spec Says:**
6 dimensions: clarity, alignment, diarization, transcript_accuracy, validity, shape

**Questions:**

**A) Text vs Audio Scoring:**
- Text segments: Can score clarity, validity, shape
- Audio segments: Can score all 6 dimensions
- **Should we have different scoring logic for each?**

**B) Scoring Source:**
- Heuristics only? (fast, simple)
- ML models? (better quality, complex)
- Hybrid? (heuristics + ML where helpful)

**My Recommendation**: Start with **heuristics** (simple rules), add ML later if needed.

**C) Scoring Thresholds:**
- ≥90: Learner/Premium datasets
- ≥70: TTS Training datasets
- **How do we weight the 6 dimensions?**

**My Recommendation**: Equal weights initially, tune based on results.

**Your Preference?**

---

### **Question 5: Dataset Snapshot Strategy**

**Questions:**

**A) What's in a Snapshot?**
- Just manifest? (list of segment IDs)
- Full metadata? (all segment data)
- Clips included? (or referenced?)

**B) Versioning:**
- Semantic versioning? (v1.0.0, v1.1.0)
- Timestamp-based? (2025-12-09)
- Hash-based? (content hash)

**C) Storage:**
- Database only? (manifest JSONB)
- File system? (JSONL files)
- Both? (DB for query, files for portability)

**My Recommendation**: 
- Manifest JSONB in database (for querying)
- Export JSONL to filesystem (for portability)
- Semantic versioning (clear upgrade path)

**Your Preference?**

---

### **Question 6: TTS Training Scaffold Depth**

**What "Full Scaffold" Means:**

**Minimal Scaffold:**
- Config file structure
- Model registry (store models)
- Training script stub (returns placeholder)

**Full Scaffold:**
- Config file structure ✅
- Model registry ✅
- Training script structure (VITS template)
- Dataset loader (reads manifests)
- Training loop skeleton (epochs, batches)
- Checkpoint saving
- Evaluation harness (MOS-lite, stability)
- Model export/packaging

**My Recommendation**: **Full scaffold** - actual structure but stubbed training function (can replace with real training later).

**Your Preference?**

---

### **Question 7: Radio Station Integration** (Future)

**You Mentioned:**
- Separate system to plug into FM/AM stations
- Determine languages automatically
- Design in separate chat

**Architecture Implications:**
- Audio Lane should accept "radio stream" as input type
- Need language detection before processing
- Real-time vs batch processing?
- Storage strategy for continuous streams?

**For Now:**
- ✅ Note requirement in docs
- ✅ Design Audio Lane to accept "stream" input type
- ✅ Defer implementation to future

**Sound Good?**

---

## 🏗️ **Proposed Architecture**

### **Audio Lane Flow:**

```
YouTube Link
   ↓
1. Preflight (yt-dlp probe)
   - Duration estimate
   - Cost estimate (Whisper API)
   - Storage estimate
   ↓
2. Download Audio (yt-dlp)
   - Extract audio stream
   - Save as WAV/MP3
   ↓
3. Normalize (librosa/ffmpeg)
   - Mono conversion
   - 22.05 or 24 kHz resample
   - Conservative trim (remove silence)
   ↓
4. ASR + Diarization (parallel)
   - Whisper API: Transcription
   - pyannote.audio: Speaker labels
   - Combine: Timestamped transcript with speaker IDs
   ↓
5. Segmentation
   - Sentence boundaries (from ASR)
   - Split into 2-12 second clips
   - Preserve speaker continuity
   ↓
6. Alignment
   - Sentence-level (default)
   - Word-level (if available from Whisper)
   - Record granularity honestly
   ↓
7. Generate CSV + Clips
   - paired_speech_corpus.csv (AudioSegment format)
   - WAV clips in clips_dir/
   - Store in database
   ↓
8. Validation
   - validate-audio-dataset CLI
   - Quality checks
```

### **Curator Flow:**

```
Text Segments + Audio Segments
   ↓
1. Scoring (6 dimensions)
   - clarity: Audio quality, SNR
   - alignment: ASR confidence, word timing
   - diarization: Speaker separation quality
   - transcript_accuracy: Transcription quality
   - validity: Language match, content quality
   - shape: Length, structure
   - total: Weighted average
   ↓
2. Deduplication
   - Exact: Text hash + audio fingerprint
   - Near-dup: Embedding similarity (cosine > 0.95)
   ↓
3. Policy Gates
   - Content filtering
   - Quality thresholds (≥70 for training, ≥90 for learner)
   ↓
4. Dataset Snapshot
   - Create manifest (segment IDs)
   - Version (semantic versioning)
   - Store metadata
   - Export JSONL
   ↓
5. Register Dataset
   - Add to datasets table
   - Link to language profile
   - Ready for TTS training
```

### **TTS Training Scaffold:**

```
Dataset Snapshot
   ↓
1. Load Dataset
   - Read manifest
   - Load clips + transcripts
   - Validate format
   ↓
2. Prepare Training Config
   - Model type (VITS)
   - Hyperparameters
   - Speaker configuration
   ↓
3. Training Loop (STUBBED)
   - for epoch in epochs:
       for batch in batches:
           # STUB: return placeholder metrics
           pass
   ↓
4. Evaluation
   - MOS-lite (subjective quality)
   - Pronunciation error rate
   - Stability (consistency)
   ↓
5. Model Registry
   - Store model artifacts
   - Record metrics
   - Version (semantic)
   - Status (dev/staging/prod)
```

---

## 📋 **Open Questions Summary**

### **Need Your Input:**

1. **Storage**: Local filesystem now, S3 later? ✅ (I assume yes)
2. **Diarization**: pyannote.audio (local) or AssemblyAI (API)? 
3. **Normalization Order**: Before ASR or after segmentation?
4. **Clip Strategy**: Sentence-based or fixed length?
5. **Scoring**: Heuristics only or ML-enhanced?
6. **Dataset Snapshots**: What's included? (manifest only or full data?)
7. **TTS Scaffold**: How deep? (full structure or minimal?)

### **Already Decided:**

✅ YouTube only (for now)  
✅ Whisper API for ASR  
✅ Multi-speaker support  
✅ Full scaffold depth  
✅ Radio stations = future separate system  

---

## 🎯 **Recommendations (If You Want Quick Decisions)**

**Storage**: Local filesystem (`data/audio/`), S3 abstraction layer  
**Diarization**: pyannote.audio (local, free)  
**Normalization**: Before ASR (better transcription)  
**Clips**: Sentence-based (natural breaks)  
**Scoring**: Heuristics (simple rules)  
**Snapshots**: Manifest JSONB + JSONL export  
**TTS Scaffold**: Full structure (training function stubbed)  

**Sound good?** Or want to discuss any of these first?

---

## 🚀 **What We'll Build**

Once decisions are made:

### **Phase 1: Audio Lane MVP** (~4-6 hours)
- YouTube downloader (yt-dlp)
- Whisper API integration
- pyannote.audio diarization
- Audio normalization (librosa)
- Clip generation (2-12s)
- CSV export + database storage

### **Phase 2: Curator Scoring** (~4-6 hours)
- Scoring rubric (6 dimensions)
- Deduplication (hash + fingerprint + embeddings)
- Policy gates
- Dataset snapshots
- Model registry integration

### **Phase 3: Dataset Builder Wire** (~2 hours)
- Curator → Dataset Builder connection
- Manifest generation
- Quality validation

### **Phase 4: TTS Training Scaffold** (~4-6 hours)
- Training script structure
- Config management
- Model registry
- Evaluation harness (stubbed)

**Total**: ~14-20 hours of work to get complete pipeline structure

---

## ❓ **Final Check**

**Before we start building, confirm:**

1. ✅ Storage: Local filesystem okay?
2. ❓ Diarization: pyannote.audio or AssemblyAI?
3. ✅ Normalization: Before ASR?
4. ✅ Clips: Sentence-based?
5. ✅ Scoring: Heuristics?
6. ✅ Snapshots: Manifest + JSONL export?
7. ✅ TTS: Full scaffold?

**Any other architectural concerns before we start coding?** 🤔
