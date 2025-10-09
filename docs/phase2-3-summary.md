# Phase 2 & 3 Complete: Text Lane MVP ✅

**Date**: October 9, 2025  
**Status**: ✅ Functional and tested end-to-end

---

## 🎯 What We Built

### Phase 2: Data Plane
- ✅ PostgreSQL schema with 8 tables
- ✅ Database migration system with rollback support
- ✅ Storage package with connection management
- ✅ Repository pattern for data access
- ✅ Example language profile (Akan/Ghana) inserted

### Phase 3: Text Lane MVP
- ✅ Text chunking with overlap (preserves context)
- ✅ Mock LangExtract (dialogue detection, topic/register labeling)
- ✅ Database integration with deduplication
- ✅ JSONL export with format guardian validation
- ✅ End-to-end pipeline tested successfully

---

## 📊 Test Results

### Document Processed
- **Input**: `test_documents/sample_akan.txt` (2,413 characters)
- **Language**: Akan (ak-GH)
- **Chunks**: 6 (with 100-char overlap)
- **Segments Extracted**: 37
- **Segments Inserted**: 34
- **Duplicates Detected**: 3 (from chunk overlap - working as designed!)

### Labels Detected
- **Dialogue segments**: 21 (57%)
- **Non-dialogue segments**: 16 (43%)
- **Topics**: education (6), casual (5), technology (3), health (3), business (1), politics (1)
- **Registers**: neutral (27), informal (9), formal (1)

### Deduplication Working ✅
- Text hash deduplication prevents exact duplicates
- Overlap between chunks creates intentional duplicates (3 detected and skipped)
- Database constraint enforces uniqueness on `text_hash`

---

## 🗄️ Database Schema

### Tables Created
1. **`raw_artifacts`**: Source tracking (YouTube, files, wiki)
2. **`text_segments`**: Labeled text with grounding ⭐ (Text Lane output)
3. **`audio_segments`**: Speech clips with transcripts (Audio Lane output)
4. **`segment_scores`**: Quality scores (Curator output)
5. **`language_profiles`**: G2P rules and TTS config
6. **`datasets`**: Immutable training dataset snapshots
7. **`model_registry`**: Trained TTS models with versions
8. **`voices`**: Production voices mapped to models

### Key Features
- **Grounding**: Every text segment stores exact source offsets (`doc_id`, `start_offset`, `end_offset`)
- **Deduplication**: SHA-256 text hash with unique constraint
- **Metadata**: Batch tracking, processing version, timestamps
- **JSONB columns**: Flexible storage for labels, dialect probabilities, policy flags

---

## 🔄 Text Lane Flow (Implemented)

```
Input: Raw document text
  ↓
1. Chunking (500 chars, 100 overlap)
  ↓
2. Mock LangExtract per chunk
   - Sentence splitting
   - Dialogue detection
   - Topic detection (keyword matching)
   - Register detection (formal/informal/neutral)
   - Code-switching detection (non-ASCII proxy)
  ↓
3. Convert to TextSegment contracts
   - Merge chunk offsets to global offsets
   - Validate grounding
  ↓
4. Database storage
   - Deduplication via text hash
   - Returns segment IDs
  ↓
5. JSONL export
   - Format guardian validation
  ↓
Output: Validated text_dialogue_corpus.jsonl
```

---

## 💡 Design Decisions & Why They Matter

### 1. **Overlap Chunking**
**Why**: LangExtract needs context to accurately label dialogue and register. Sentences at chunk boundaries get incomplete context without overlap.

**Result**: 3 duplicate segments from overlap (expected). These are caught by deduplication and skipped.

### 2. **Grounding Requirement**
**Why**: Prevents AI hallucination. Every label must point to exact character offsets in source.

**Implementation**: Chunk-relative offsets converted to document-global offsets using `chunker.merge_chunk_offsets()`.

### 3. **Mock LangExtract**
**Why**: Development unblocked while waiting for real LangExtract integration.

**Heuristics**:
- Dialogue: Quotation marks, "said/asked/replied" patterns
- Topic: Keyword matching (education, business, health, etc.)
- Register: Formal markers (Dr., Professor) vs informal (can't, gonna)
- Code-switching: Non-ASCII detection (simplified)

**Replacement Path**: Swap `MockLangExtract` for real API client - interface stays the same.

### 4. **Repository Pattern**
**Why**: Clean separation between business logic and data access. Easy to mock for testing.

**Benefit**: Can switch databases or add caching without changing text lane code.

---

## 🎯 How This Answers Your Questions

### **"How do we take text/audio and pass it to phonetics?"**

**Answer**: We don't directly! Here's the actual flow:

1. **Text Lane** produces labeled text segments (topics, registers, dialogue)
2. **Audio Lane** produces speech clips with transcripts
3. **Both** go to **Curator** for scoring and pairing
4. **TTS Training** learns from paired text+audio:
   - Model learns: "This text with this label sounds like THIS audio"
   - G2P rules from `LanguageProfile` guide pronunciation
5. **Runtime**: New text → G2P → phonemes → TTS → speech

**Phonetics comes from TWO sources**:
- **LanguageProfile.g2p_rules**: Manual rules (e.g., "ky" → "c͡ɕ" in Akan)
- **TTS model weights**: Learned from training on paired data

### **"What's the value of just having text?"**

**Answer**: Text segments are valuable BEFORE pairing with audio:

1. **Training Data Labels**: Tell TTS model "This is formal education dialogue"
   - Model learns different prosody for formal vs casual
   - Better style conditioning

2. **Language Completeness Metrics**: Track coverage
   - "We have 100 casual segments but only 5 formal ones → seek more formal sources"
   - Identify topic gaps

3. **G2P Rule Testing**: Validate pronunciation rules on real text
   - Find words that break your rules
   - Build exception dictionary (`g2p_overrides`)

4. **Cheap to Collect**: Text is abundant and free
   - Establish language structure before expensive audio processing
   - Guide what audio sources to target

### **"How do subsequent documents not duplicate info?"**

**Answer**: Three-level deduplication strategy:

1. **Text Lane (Exact)**:
   - SHA-256 hash of segment text
   - Database unique constraint on `text_hash`
   - **Result**: Zero exact duplicates

2. **Chunk Overlap (Expected)**:
   - Intentional overlap creates ~3 duplicates per document
   - Caught and skipped during insert
   - **Result**: Context preserved, no storage waste

3. **Curator (Near-duplicate)** - Coming in Phase 5:
   - Embedding-based similarity (cosine > 0.95)
   - Catches paraphrases and similar content
   - **Result**: True semantic deduplication

**Test Proof**: 37 segments extracted, 34 inserted, 3 duplicates skipped ✅

---

## 📁 New Files Created

### Database & Storage
```
infra/db/
├── migrations/
│   ├── 001_initial_schema.sql          # PostgreSQL schema
│   └── 001_initial_schema_down.sql     # Rollback
└── setup_db.sh                          # Setup script

packages/storage/python/
└── src/mumbl_storage/
    ├── __init__.py
    ├── db.py                            # Connection management
    └── repositories.py                  # Data access layer
```

### Text Lane
```
apps/text-lane/
└── src/text_lane/
    ├── __init__.py
    ├── chunker.py                       # Overlap chunking
    ├── langextract.py                   # Mock LangExtract
    └── processor.py                     # Main orchestrator
```

### Test Data
```
test_documents/
├── sample_akan.txt                      # Test document
└── text_dialogue_corpus.jsonl          # Output
```

---

## 🚀 What's Next (Phase 4+)

### Immediate Next Steps
1. **Real LangExtract Integration**: Replace mock with actual API
2. **HTML Spot-Checks**: Generate visual grounding validation
3. **S3 Storage**: Configure object storage paths
4. **Audio Lane**: YouTube download, ASR, diarization
5. **Curator**: Scoring rubric, advanced deduplication

### Future Phases
- **Profile Builder**: G2P rule generation from data
- **TTS Training**: VITS training harness
- **Runtime API**: Full ASR → LLM → G2P → TTS pipeline
- **Seeker Agents**: Automated gap filling with metrics
- **Admin UI**: Connect backend to dashboard

---

## 🔧 How to Use

### Process a Document
```python
from text_lane.processor import TextLaneProcessor

processor = TextLaneProcessor(
    language="ak",
    dialect="ak-GH",
    chunk_size=2000,
    overlap=200
)

result = processor.process_document(
    text=document_text,
    doc_id="DOC-12345",
    batch_id="batch-2025-10"
)

print(f"Segments: {result['segments_inserted']}")
print(f"Topics: {result['stats']['topics']}")
```

### Query Database
```python
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import TextSegmentRepository

with get_connection() as conn:
    repo = TextSegmentRepository(conn)
    
    # Count by language
    count = repo.count_by_language("ak")
    
    # Get batch segments
    segments = repo.get_by_batch("batch-2025-10")
```

### Run Validation
```bash
validate-text-jsonl --path text_dialogue_corpus.jsonl
```

---

## 📝 Key Learnings

1. **Chunking with overlap is critical** for context preservation
2. **Grounding prevents hallucination** - every label has source offsets
3. **Mock implementations unblock development** - real integration comes later
4. **Database constraints enforce deduplication** - no application logic bugs
5. **Repository pattern enables testing** - clean separation of concerns
6. **Format guardians catch drift early** - validation at every boundary

---

## ✅ Success Criteria Met

- [x] Database schema deployed and tested
- [x] Text lane processes documents end-to-end
- [x] Segments stored with grounding
- [x] Deduplication working (3 duplicates caught from overlap)
- [x] JSONL export validated
- [x] Akan language profile in database
- [x] No linter errors or syntax issues
- [x] All tests passing

---

**Ready for Phase 4: Real LangExtract Integration & Audio Lane**

