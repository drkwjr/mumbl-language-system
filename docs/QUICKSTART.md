# Mumbl Language System - Quick Start Guide

**Updated**: December 26, 2025  
**Status**: Text Lane Functional ✅ + Radio Discovery/Ingress Ready ✅

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node 20+
- PostgreSQL 14+ (running)

### Initial Setup
```bash
# 1. Bootstrap environment
make bootstrap

# 2. Setup database
make setup-db

# 3. Install storage package
pip install -e packages/storage/python

# 4. Install text lane
make install-text-lane

# 5. Verify installation
make test-text-lane
```

---

## 🎯 What Works Right Now

### ✅ Text Lane (Fully Functional)
Process documents through dialogue detection and labeling:

```python
from text_lane.processor import TextLaneProcessor

# Initialize
processor = TextLaneProcessor(
    language="ak",
    dialect="ak-GH",
    chunk_size=2000,
    overlap=200
)

# Process a document
result = processor.process_document(
    text=your_document_text,
    doc_id="DOC-001",
    batch_id="batch-001"
)

# Check results
print(f"Segments: {result['segments_inserted']}")
print(f"Topics: {result['stats']['topics']}")
```

### ✅ Database Access
Query stored segments:

```python
from mumbl_storage.db import get_connection
from mumbl_storage.repositories import TextSegmentRepository

with get_connection() as conn:
    repo = TextSegmentRepository(conn)
    
    # Get segments by batch
    segments = repo.get_by_batch("batch-001")
    
    # Count by language
    count = repo.count_by_language("ak")
```

### ✅ Format Validation
Validate outputs:

```bash
# Validate language profile
profile-validate --path docs/examples/ak-GH.language-profile.json

# Validate text segments
validate-text-jsonl --path output.jsonl

# Validate audio dataset
validate-audio-dataset --clips_dir ./clips --csv metadata.csv

# Validate scores
validate-scores --path scores.jsonl
```

---

## 📊 Database Management

### Useful Commands
```bash
# Connect to database
make db-connect

# Reset test data (keeps schema)
make db-reset

# Full database recreation
make setup-db  # Will prompt to drop existing
```

### Database Schema
- `raw_artifacts` - Source tracking
- `text_segments` - Labeled text (Text Lane output) ⭐
- `audio_segments` - Speech clips (Audio Lane - coming soon)
- `segment_scores` - Quality scores (Curator - coming soon)
- `language_profiles` - G2P rules and TTS config
- `datasets` - Training dataset snapshots
- `model_registry` - Trained models
- `voices` - Production voices

---

## 🔄 Text Lane Pipeline

```
Your Document
     ↓
Text Chunker (with overlap for context)
     ↓
Mock LangExtract (dialogue, topic, register detection)
     ↓
TextSegment Contracts (with grounded offsets)
     ↓
Database Storage (with deduplication)
     ↓
JSONL Export + Validation
```

**Features**:
- Chunking with overlap preserves context
- Grounding: Every label has source offsets
- Deduplication: SHA-256 hash prevents duplicates
- Validation: Format guardians catch drift

---

## 📁 Example: Process a Document

Create a test document:
```bash
cat > my_document.txt << 'EOF'
Dr. Mensah said: "The Akan language is rich in proverbs."

"Can you teach me some?" the student asked eagerly.

In everyday conversation, people say "Wo ho te sɛn?" which means "How are you?"

The university offers courses in both formal and informal Akan.
EOF
```

Process it:
```python
from text_lane.processor import TextLaneProcessor

# Load document
with open("my_document.txt") as f:
    text = f.read()

# Process
processor = TextLaneProcessor(language="ak", dialect="ak-GH")
result = processor.process_document(
    text=text,
    doc_id="MY-DOC-001",
    batch_id="my-batch"
)

# Export
with open("output.jsonl", "w") as f:
    for segment in segments:
        f.write(segment.model_dump_json() + "\n")
```

Validate:
```bash
validate-text-jsonl --path output.jsonl
```

---

## 🎛️ Configuration

### Database (`.env`)
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mumbl_lang_system
DB_USER=mumbl_user
DB_PASSWORD=mumbl_dev_password

# Or use connection string
DATABASE_URL=postgresql://mumbl_user:mumbl_dev_password@localhost:5432/mumbl_lang_system
```

### Text Lane Parameters
```python
TextLaneProcessor(
    language="ak",           # Language code
    dialect="ak-GH",        # Dialect code
    chunk_size=2000,        # Characters per chunk
    overlap=200,            # Overlap for context
)
```

---

## 🐛 Troubleshooting

### "PostgreSQL not running"
```bash
# macOS
brew services start postgresql@14

# Linux
sudo systemctl start postgresql
```

### "Database connection failed"
```bash
# Test connection
pg_isready

# Check password
psql -U mumbl_user -d mumbl_lang_system
```

### "Module not found"
```bash
# Reinstall packages
make bootstrap

# Specific package
pip install -e packages/storage/python
```

### "Import error in text_lane"
```bash
# Reinstall text lane
make install-text-lane

# Verify
make test-text-lane
```

---

## 📚 Key Documentation

- **`docs/README.md`** - Documentation index + sources of truth
- **`docs/phase2-3-summary.md`** - What we just built
- **`docs/ROADMAP.md`** - Full V1 roadmap
- **`docs/architecture/overview.md`** - System architecture
- **`docs/runbooks/text-lane.md`** - Text lane operations
- **`docs/runbooks/ingest.md`** - Radio ingestion operations
- **`docs/station-discovery.md`** - Discovery pipeline details
- **`infra/db/schema.md`** - Database schema reference

---

## 🎯 What's Next

### Short Term (Phase 4)
- Replace MockLangExtract with real integration
- HTML spot-check generation
- S3 storage configuration

### Medium Term (Phase 5)
- Audio Lane: YouTube → ASR → clips
- Curator: Scoring and deduplication
- Dataset snapshots

### Long Term
- TTS training harness
- Runtime speech synthesis
- Admin UI backend integration

---

## 💡 Pro Tips

1. **Start small**: Test with short documents first
2. **Check logs**: Database errors show in terminal
3. **Use batch IDs**: Track related segments
4. **Validate early**: Run format guardians after changes
5. **Reset cleanly**: `make db-reset` for fresh test runs

---

## 🆘 Need Help?

1. Check `docs/phase2-3-summary.md` for details
2. Read error messages carefully (they're descriptive!)
3. Test database connection: `make db-connect`
4. Verify package install: `make test-text-lane`

---

**Built by**: Mumbl Team  
**Last Updated**: October 9, 2025  
**Version**: 0.1.0 (Text Lane MVP)
### ✅ Radio Discovery + Ingest (Ready)

Discovery and ingestion are now wired for Ghana/Somalia, with admin visibility.

```bash
# 1) Run station discovery
python scripts/discovery/seed_sources.py
python scripts/discovery/run_discovery.py

# 2) Start ingestion API (admin reads from this)
./scripts/start_radio_ingestion_api.sh

# 3) Run a one-shot capture cycle
python scripts/run_radio_ingest_once.py

# Optional: keep the scheduler running continuously
python scripts/run_radio_ingest_daemon.py

# 4) Validate recent outputs
python scripts/validate_radio_ingest.py
```

### ✅ Admin UI (Discovery + Pipeline Visibility)

```bash
./scripts/start_admin_ui.sh
```

The Sources page includes discovery activity and recent runs.

### "ffmpeg missing"
```bash
brew install ffmpeg
```

### "No recent shards/segments"
```bash
# Ensure discovery ran and streams are reachable
python scripts/discovery/run_discovery.py
python scripts/run_radio_ingest_once.py
python scripts/validate_radio_ingest.py
```
