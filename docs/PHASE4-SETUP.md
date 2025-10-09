# Phase 4 Setup: Production Text Lane with LangExtract

**Date**: October 9, 2025  
**Status**: Ready for Configuration

---

## 🎯 What's New in Phase 4

### **Real LangExtract Integration**
- ✅ Google's [LangExtract library](https://github.com/google/langextract) installed (16.2k ⭐)
- ✅ Production-ready dialogue extraction with source grounding
- ✅ Supports OpenAI (gpt-4o), Gemini, and Ollama models
- ✅ Confidence scores and structured extraction

### **Multi-Format Document Parser**
- ✅ EPUB support (`.epub`)
- ✅ PDF support (`.pdf`)
- ✅ Plain text (`.txt`, `.md`)
- ✅ HTML support (`.html`, `.htm`)
- ✅ Ready for Anna's Archive documents

### **Python 3.10 Upgrade**
- ✅ Upgraded from Python 3.9 → 3.10 (LangExtract requirement)
- ✅ New venv: `.venv-310`
- ✅ All packages reinstalled and working

---

## ⚙️ Configuration Steps

### **Step 1: Set OpenAI API Key**

LangExtract needs an API key to call the LLM. Add to your `.env`:

```bash
# Add to .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

Or export in your shell:

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Get your key**: https://platform.openai.com/api-keys

### **Step 2: Switch to Python 3.10 Environment**

```bash
# Activate the new Python 3.10 environment
source .venv-310/bin/activate

# Verify Python version
python --version  # Should show 3.10.13
```

### **Step 3: Update Makefile** (Optional)

To make the new environment default, update the `Makefile`:

```makefile
# Change bootstrap target to use Python 3.10
bootstrap:
	python3.10 -m venv .venv-310
	source .venv-310/bin/activate && pip install -e packages/...
```

---

## 📚 Using the Document Parser

### **Parse an EPUB**

```python
from text_lane.document_parser import DocumentParser

parser = DocumentParser()

# Parse EPUB
doc = parser.parse("path/to/book.epub")

print(f"Format: {doc.format}")
print(f"Title: {doc.metadata.get('title')}")
print(f"Text length: {len(doc.text)} characters")
print(f"Preview: {doc.text[:200]}...")
```

### **Parse a PDF**

```python
doc = parser.parse("path/to/document.pdf")
print(f"Pages: {doc.metadata['pages']}")
print(f"Text: {doc.text[:500]}...")
```

### **Supported Formats**

| Format | Extension | Library Used | Metadata Extracted |
|--------|-----------|--------------|-------------------|
| EPUB | `.epub` | ebooklib | title, author, language, publisher |
| PDF | `.pdf` | PyPDF2 | title, author, page count |
| Text | `.txt`, `.md` | built-in | filename, size |
| HTML | `.html`, `.htm` | BeautifulSoup | title, filename |

---

## 🤖 Using Real LangExtract

### **Basic Usage**

```python
from text_lane.real_langextract import RealLangExtract
import os

# Initialize with API key
extractor = RealLangExtract(
    language="ak",
    dialect="ak-GH",
    model_id="gpt-4o",
    api_key=os.getenv('OPENAI_API_KEY')
)

# Process a chunk
text = """
Dr. Mensah said: "The Akan language has many dialects."

"Which dialect should I learn?" the student asked.

In formal settings, people use more traditional vocabulary.
"""

results = extractor.process_chunk(text)

for result in results:
    print(f"Text: {result.text}")
    print(f"Is dialogue: {result.is_dialogue}")
    print(f"Speaker: {result.speaker}")
    print(f"Register: {result.register_type}")
    print(f"Offsets: [{result.start}:{result.end}]")
    print(f"Confidence: {result.confidence}")
    print()
```

### **Key Features**

1. **Source Grounding**: Every extraction has exact character offsets
2. **Confidence Scores**: Know how certain the extraction is
3. **Structured Output**: Dialogue, speaker, topic, register all labeled
4. **Fallback**: Simple regex fallback if API fails
5. **Multi-Model**: Supports GPT-4, Gemini, local Ollama

---

## 🔄 Switching Between Mock and Real

The mock is still available for development/testing without API calls:

```python
# Use mock (no API key needed)
from text_lane.langextract import MockLangExtract
extractor = MockLangExtract(language="ak", dialect="ak-GH")

# Use real (requires API key)
from text_lane.real_langextract import RealLangExtract
extractor = RealLangExtract(language="ak", dialect="ak-GH", model_id="gpt-4o")
```

Update `text_lane/processor.py` to choose which one to use.

---

## 📥 Processing Your Documents

### **When You Upload EPUBs/PDFs**

1. **Place files** in a documents directory:
```bash
mkdir -p documents/akan
# Upload your EPUBs, PDFs here
```

2. **Parse and process**:
```python
from text_lane.document_parser import DocumentParser
from text_lane.processor import TextLaneProcessor

# Parse document
parser = DocumentParser()
doc = parser.parse("documents/akan/book.epub")

# Process through text lane
processor = TextLaneProcessor(
    language="ak",
    dialect="ak-GH",
    use_real_langextract=True  # Use production LangExtract
)

result = processor.process_document(
    text=doc.text,
    doc_id=f"EPUB:{doc.metadata.get('title', 'unknown')}",
    batch_id="akan-books-001"
)

print(f"Extracted {result['segments_inserted']} segments")
```

3. **Batch process** multiple files:
```python
import os

for filename in os.listdir("documents/akan"):
    if filename.endswith(('.epub', '.pdf')):
        filepath = os.path.join("documents/akan", filename)
        doc = parser.parse(filepath)
        result = processor.process_document(
            text=doc.text,
            doc_id=f"{doc.format.upper()}:{filename}",
            batch_id="akan-corpus-2025"
        )
        print(f"✓ {filename}: {result['segments_inserted']} segments")
```

---

## 💰 Cost Estimation

### **OpenAI GPT-4o Pricing** (as of Oct 2025)
- Input: $2.50 / 1M tokens (~750k words)
- Output: $10.00 / 1M tokens

### **Example Costs**
- **Small book** (50k words): ~$0.17 input + $0.67 output = **~$0.84**
- **Medium book** (100k words): ~$0.33 input + $1.33 output = **~$1.66**
- **Large corpus** (1M words): ~$3.33 input + $13.33 output = **~$16.66**

### **Cost Optimization Tips**
1. **Use smaller chunks**: Lower chunk_size = fewer tokens per call
2. **Use Gemini**: Often cheaper than GPT-4o
3. **Use local Ollama**: Free (runs on your machine)
4. **Batch processing**: Process multiple files in one session
5. **Filter first**: Only process high-quality sources

---

## 🧪 Testing the Setup

### **Test Document Parser**

```bash
# Create test EPUB (or use your own)
python -c "
from text_lane.document_parser import DocumentParser

parser = DocumentParser()

# Test with existing file
doc = parser.parse('test_documents/sample_akan.txt')
print(f'✓ Parsed {doc.format}: {len(doc.text)} chars')
"
```

### **Test LangExtract** (requires API key)

```bash
# Set API key first
export OPENAI_API_KEY="sk-your-key-here"

python -c "
from text_lane.real_langextract import RealLangExtract

extractor = RealLangExtract(language='en', dialect='en-US')
results = extractor.process_chunk('Dr. Smith said: \"Hello world.\"')

for r in results:
    print(f'✓ Extracted: {r.text} (dialogue={r.is_dialogue})')
"
```

---

## 🐛 Troubleshooting

### **"Module not found: langextract"**
```bash
# Make sure you're in the Python 3.10 environment
source .venv-310/bin/activate
pip install langextract openai
```

### **"API key required"**
```bash
# Set in environment
export OPENAI_API_KEY="sk-..."

# Or add to .env file
echo "OPENAI_API_KEY=sk-..." >> .env
```

### **"EPUB parsing failed"**
```bash
# Install ebooklib
pip install ebooklib beautifulsoup4
```

### **"Python 3.9 error"**
```bash
# Switch to 3.10 environment
source .venv-310/bin/activate
python --version  # Should show 3.10.13
```

---

## 📝 Next Steps

1. **Set API key** in `.env`
2. **Upload your documents** (EPUBs, PDFs) to a documents folder
3. **Test with one file** to verify extraction quality
4. **Batch process** your corpus
5. **Review outputs** in database and JSONL

When you're ready, I'll help you:
- Create batch processing scripts
- Optimize extraction prompts for Akan language
- Set up HTML spot-checks for QA
- Configure S3 storage for artifacts

---

**Ready to process your Akan corpus!** 🚀

