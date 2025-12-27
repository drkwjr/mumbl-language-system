# Current System Status & Catch-Up Guide

**Date**: December 2025  
**Status**: Text Lane Functional, Radio Discovery/Ingest Active with Admin Visibility, Audio Lane + Curator in progress

See `docs/README.md` for sources of truth and doc ownership.

---

## 🎯 **What You Have Right Now**

### **✅ What's Working (Phase 2-4.5 + Radio Discovery/Ingest)**

**1. Database Layer** ✅
- PostgreSQL with migrations for text/audio/radio ingestion + discovery + pipeline events
- Storage package with repository pattern
- Migration system with rollback
- Supabase migrations applied via idempotent runner

**2. Text Lane** ✅ **FULLY FUNCTIONAL**
- Document parser: EPUB, PDF, TXT, HTML
- OCR support: Tesseract for scanned PDFs
- LangExtract integration: Google's library installed
- Text chunking: Overlap for context preservation
- Database integration: Stores segments with deduplication
- JSONL export: Validated with format guardians
- **Tested end-to-end**: Document → DB → Validated output ✅

**3. Extracted Corpus** ✅
- **Somali Grammar**: 128,737 chars extracted (82 pages OCR'd)
- **Twi Dictionary**: 337,317 chars extracted (340 pages)
- **Twi Pronunciations**: 2,327 word/IPA pairs mined
- Ready for LangExtract processing

**4. Character Handling** ✅
- UTF-8 encoding throughout
- OCR artifact cleaning
- IPA symbol preservation
- Unicode normalization

**5. Infrastructure** ✅
- Python 3.10 environment
- All packages installed
- Database running
- Makefile commands ready

**6. Radio Discovery + Ingest** ✅
- Station discovery (Radio Browser + Wikipedia) with provenance logging
- Canonical station dedupe + provenance linking
- Coverage reports stored and shown in admin
- Capture → VAD/LID → segments (radio ingestion)
- LLM verification + label mapping (raw LID → ISO-639-3)
- Per-station health, auto-quarantine for repeated hard failures
- Admin UI visibility for discovery + pipeline activity

---

## 🔄 **What's NOT Done Yet**

### **Phase 4: LangExtract** (Partially Done)
- ✅ Library installed
- ✅ Code written
- ⏸️ **Not tested with real API** (needs API key verification)
- ⏸️ **Not processed your corpus yet**

### **Phase 5: Audio Lane** ❌ (Not Started)
- ❌ YouTube download
- ❌ ASR (Automatic Speech Recognition)
- ❌ Speaker diarization
- ❌ Audio normalization
- ❌ Clip generation

### **Phase 6: Curator** ❌ (Stubbed Only)
- ❌ Scoring rubric implementation
- ❌ Deduplication (exact + near)
- ❌ Policy gates
- ❌ Dataset snapshots

### **Phase 7: TTS Training** ❌ (Not Started)
- ❌ Training harness
- ❌ Model registry
- ❌ Evaluation metrics
- ❌ Dataset building integration

### **Phase 8: Runtime** ⚠️ (Stubbed)
- ⚠️ API exists but stubbed
- ❌ ASR → LLM → G2P → TTS pipeline
- ❌ Speech synthesis

---

## 📊 **Current State Summary**

```
✅ Database:     Migrations + storage layer, Supabase ready
✅ Text Lane:    Fully functional, tested end-to-end
✅ Documents:    Somali + Twi extracted (ready for processing)
✅ Radio:        Discovery + ingest wired with admin visibility
✅ LangExtract:  Installed, not tested with API yet
❌ Audio Lane:   Not started
❌ Curator:      Stubbed only
❌ TTS Training: Not started
❌ Runtime:      Stubbed only
```

---

## 🎯 **Your Goal: "Set It Up So It COULD Work"**

You want to build the **infrastructure** so training is possible, even if you don't fully process a language right now.

**This means:**
1. ✅ Text Lane → **DONE** (can extract dialogue from documents)
2. ⏸️ Audio Lane → **BUILD** (can process YouTube/audio → clips)
3. ⏸️ Curator → **BUILD** (can score, dedupe, create datasets)
4. ⏸️ Dataset Builder → **WIRE** (can prepare training manifests)
5. ⏸️ TTS Training → **SETUP** (can train models, even if not running now)

---

## 🗺️ **Path Forward: One Milestone at a Time**

Let's tackle the **outstanding items** systematically:

### **Next Up: Audio Lane (Milestone D)**

**Why First?**
- Completes the data collection pipeline
- Text + Audio = Complete training data
- Curator needs both to score properly

**What We Need:**
1. **YouTube Download** (yt-dlp or similar)
2. **ASR Service** (Whisper API, local Whisper, or other)
3. **Speaker Diarization** (pyannote.audio or similar)
4. **Audio Normalization** (librosa or ffmpeg)
5. **Clip Generation** (2-12 second clips)

**Effort Estimate**: 2-3 days

---

### **Then: Curator (Milestone E)**

**Why Second?**
- Needs both text and audio segments to score
- Creates the quality gates
- Produces final training datasets

**What We Need:**
1. **Scoring Algorithm** (6 dimensions)
2. **Deduplication** (exact hash + audio fingerprint + near-dup embeddings)
3. **Policy Gates** (content filtering)
4. **Dataset Snapshots** (versioned datasets)

**Effort Estimate**: 2-3 days

---

### **Then: Dataset Builder Integration (Milestone E)**

**Why Third?**
- Links Curator outputs to TTS training
- Creates training manifests
- Validates dataset quality

**What We Need:**
1. **Wire Curator → Dataset Builder**
2. **Manifest Generation** (from curator snapshots)
3. **Quality Validation** (before training)

**Effort Estimate**: 1 day

---

### **Finally: TTS Training Setup (Milestone H)**

**Why Last?**
- Can be scaffolded without full training
- Just needs to accept datasets and produce models
- Actual training can happen later

**What We Need:**
1. **Training Script Structure** (VITS or similar)
2. **Config Management** (YAML/JSON configs)
3. **Model Registry** (store trained models)
4. **Evaluation Harness** (MOS-lite, stability)

**Effort Estimate**: 2-3 days (scaffolding only)

---

## 💡 **Discussion Points**

Before we start building, let's align on:

### **1. Audio Lane Priorities**

**Question**: What's your priority for audio sources?
- **A)** YouTube links (most flexible)
- **B)** File uploads (local control)
- **C)** Both (complete solution)

**My Recommendation**: Start with **YouTube** (easier to test), add file uploads later.

---

### **2. ASR Service Choice**

**Options:**
- **A)** OpenAI Whisper API (easiest, $0.006/min)
- **B)** Local Whisper (free, but slower)
- **C)** Other ASR service (AssemblyAI, Deepgram, etc.)

**My Recommendation**: Start with **OpenAI Whisper API** (good quality, simple integration), can switch later.

---

### **3. Diarization Strategy**

**Options:**
- **A)** pyannote.audio (local, free, requires GPU)
- **B)** AssemblyAI (API, paid, good quality)
- **C)** Skip for now (single speaker assumption)

**My Recommendation**: Start with **single speaker** assumption, add diarization later (simpler path).

---

### **4. Curator Scoring**

**Question**: How sophisticated should scoring be?
- **A)** Simple heuristics (fast to build)
- **B)** ML-based scoring (better quality, more complex)
- **C)** Hybrid (heuristics + ML where helpful)

**My Recommendation**: Start with **simple heuristics** (6 dimensions from your spec), enhance later.

---

### **5. TTS Training Framework**

**Options:**
- **A)** VITS (your roadmap mentions this)
- **B)** Coqui TTS (easier to use)
- **C)** Scaffold only (just structure, no actual training)

**My Recommendation**: **Scaffold only** for now - create the structure, configs, registry. Actual training can be done later when you have datasets.

---

## 🎯 **Recommended Approach**

Let's build **functional scaffolding** that demonstrates the full pipeline:

### **Phase 1: Audio Lane MVP** (This Session)
- YouTube download (1-2 hours)
- ASR integration (1-2 hours)
- Simple normalization (1 hour)
- Clip generation (1 hour)
- **Result**: Can process one YouTube video → clips → CSV

### **Phase 2: Curator Scoring** (Next Session)
- Implement scoring rubric (2-3 hours)
- Add deduplication (1-2 hours)
- Basic policy gates (1 hour)
- **Result**: Can score segments → filter → create datasets

### **Phase 3: Dataset Builder Integration** (Quick)
- Wire curator outputs (1 hour)
- Manifest generation (1 hour)
- **Result**: Can create training-ready datasets

### **Phase 4: TTS Training Scaffold** (Final)
- Training script structure (2 hours)
- Config management (1 hour)
- Model registry integration (1 hour)
- Evaluation harness stub (1 hour)
- **Result**: Can accept datasets and "train" (stub returns placeholder)

---

## ❓ **Questions for You**

1. **Audio Lane**: YouTube first, or also file uploads?
2. **ASR**: OpenAI Whisper API or local?
3. **Diarization**: Single speaker first, or multi-speaker from start?
4. **TTS Training**: Full scaffold or just registry/configs?
5. **Priority**: Get Audio Lane working first, or set up everything in parallel?

---

## 🚀 **Suggested Next Steps**

**If you want to see the full pipeline quickly:**

1. **Today**: Audio Lane MVP (YouTube → ASR → clips)
2. **Next**: Curator scoring (score segments → datasets)
3. **Final**: TTS scaffold (structure ready, training later)

**OR if you want to be thorough:**

1. **Today**: Audio Lane + Curator together
2. **Next**: Dataset Builder + TTS scaffold
3. **Final**: Integration testing

**What's your preference?** 🎯
