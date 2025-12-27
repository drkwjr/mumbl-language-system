# API Keys and Database Requirements

## OpenAI API Key for Whisper ✅

**YES, your OpenAI API key is enough!**

- ✅ **Same key works for Whisper API** - No separate key needed
- ✅ **Same key works for LangExtract** (used in Text Lane)
- ✅ **One key handles both services**

### How It Works

```python
# Whisper API (Audio Lane)
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)  # Uses same key

# LangExtract (Text Lane)  
api_key = os.getenv('OPENAI_API_KEY')
lx.extract(api_key=api_key)  # Same key
```

### Cost
- **Whisper API**: ~$0.006 per minute of audio
- **LangExtract**: Pay per token (similar to GPT-4 usage)

### Setup
```bash
# Set once, works everywhere
export OPENAI_API_KEY=sk-your-key-here

# Or in .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

---

## Optional: HuggingFace Token for Diarization ⚠️

**Not required, but recommended** for speaker diarization:

```bash
# Optional - helps download pyannote models faster
export HUGGINGFACE_TOKEN=your_token_here
```

**Without token**: Models still download, just slower (may hit rate limits)  
**With token**: Faster downloads, better reliability

**First run**: Downloads ~500MB models automatically (one-time)

---

## Database Requirements

### What You Need

1. **PostgreSQL 14+** (or any PostgreSQL version)
   - ✅ Local installation works perfectly
   - ✅ Cloud database (AWS RDS, Heroku Postgres, etc.) also works
   - ✅ Docker container works too

2. **No special setup required** - The setup script handles everything!

### Quick Setup (Local PostgreSQL)

**macOS:**
```bash
# Install PostgreSQL (if not already installed)
brew install postgresql@14

# Start PostgreSQL
brew services start postgresql@14

# Run setup script
make setup-db
```

**Linux (Ubuntu/Debian):**
```bash
# Install PostgreSQL
sudo apt install postgresql-14

# Start PostgreSQL
sudo systemctl start postgresql

# Run setup script
make setup-db
```

**Using Docker:**
```bash
# Run PostgreSQL in Docker
docker run --name mumbl-db \
  -e POSTGRES_PASSWORD=mumbl_dev_password \
  -e POSTGRES_USER=mumbl_user \
  -e POSTGRES_DB=mumbl_lang_system \
  -p 5432:5432 \
  -d postgres:14

# Then run migrations
make setup-db
```

### What the Setup Script Does

1. ✅ Checks if PostgreSQL is running
2. ✅ Creates database user (`mumbl_user`)
3. ✅ Creates database (`mumbl_lang_system`)
4. ✅ Runs all migrations (creates tables)
5. ✅ Tests connection
6. ✅ Saves connection string to `.env`

### Default Configuration

The setup script uses these defaults (can be overridden with env vars):

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mumbl_lang_system
DB_USER=mumbl_user
DB_PASSWORD=mumbl_dev_password
```

### Custom Database

If you want to use a different database (e.g., cloud hosted):

```bash
# Set environment variables
export DB_HOST=your-db-host.com
export DB_PORT=5432
export DB_NAME=your_db_name
export DB_USER=your_username
export DB_PASSWORD=your_password

# Or use connection string
export DATABASE_URL=postgresql://user:password@host:port/database

# Then run setup
make setup-db
```

### No Database? (Limited Functionality)

**Without database**:
- ❌ Can't store segments
- ❌ Can't run Curator (needs database)
- ❌ Can't create datasets
- ✅ Can still process files locally
- ✅ Can export to CSV/JSONL

**With database**:
- ✅ Full pipeline works
- ✅ Stores all segments
- ✅ Curator can score/deduplicate
- ✅ Dataset snapshots work
- ✅ Model registry works

---

## Complete Setup Checklist

### ✅ Required
- [x] OpenAI API key (`OPENAI_API_KEY`)
- [ ] PostgreSQL 14+ installed and running
- [ ] Database setup (`make setup-db`)

### ⚠️ Optional (Recommended)
- [ ] HuggingFace token (`HUGGINGFACE_TOKEN`) - for faster pyannote downloads

### ✅ Already Done
- [x] All Python packages installed
- [x] FFmpeg installed
- [x] All code ready

---

## Quick Start Commands

```bash
# 1. Set API key
export OPENAI_API_KEY=sk-your-key-here

# 2. Start PostgreSQL (if not running)
brew services start postgresql@14  # macOS
# or
sudo systemctl start postgresql  # Linux

# 3. Setup database
make setup-db

# 4. Verify everything works
python -c "
from mumbl_storage.db import get_connection
with get_connection() as conn:
    print('✅ Database connected!')
"

# 5. You're ready! Test with a YouTube link
```

---

## Summary

| Requirement | Status | Notes |
|------------|--------|-------|
| **OpenAI API Key** | ✅ **Required** | Works for Whisper + LangExtract |
| **PostgreSQL** | ✅ **Required** | Local or cloud, 14+ recommended |
| **HuggingFace Token** | ⚠️ **Optional** | Helps with pyannote downloads |
| **FFmpeg** | ✅ **Done** | Already installed |
| **Python Packages** | ✅ **Done** | All installed |

**You're almost there!** Just need:
1. ✅ Your OpenAI API key (you have this)
2. ✅ PostgreSQL running + `make setup-db`

Then you're ready to process YouTube links! 🚀

