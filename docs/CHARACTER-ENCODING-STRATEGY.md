# Character Encoding & Storage Strategy

**Date**: October 9, 2025  
**Question**: "Should we store each language in their proper characters?"

---

## ✅ **Short Answer: YES - Native UTF-8 Everywhere**

We **MUST** store languages in their native characters because:
1. **Tone marks are pronunciation** (é vs e = different sounds in Twi)
2. **IPA symbols are phonemes** (ɛ vs e = different phonemes)
3. **TTS models need accurate input** (garbage in = garbage out)

**We're already doing this correctly!** ✅

---

## 🎯 **Our Character Storage Strategy**

### **Principle: Preserve Linguistic Accuracy**

```
GOOD ✅: Store "asasé" (with tone mark)
BAD  ❌: Store "asase" (removed tone mark → lost information)

GOOD ✅: Store IPA "ɛbɛ" (open-mid vowel)
BAD  ❌: Store "ebe" (wrong phoneme)

GOOD ✅: Store Somali "Waa gu mahadsantahay"
BAD  ❌: Transliterate or romanize differently
```

---

## 🗄️ **Database Configuration (Already Correct)**

### **PostgreSQL UTF-8:**
```sql
-- Already set up correctly!
Server encoding: UTF8
Client encoding: UTF8

-- All TEXT columns support ANY Unicode
CREATE TABLE text_segments (
    text TEXT NOT NULL,  -- Stores: Somali, Twi, Arabic, Chinese, etc.
    lang VARCHAR(10),    -- Language code
    ...
);
```

**Result**: Can store ANY language without conversion ✅

---

## 📝 **Python/JSON Configuration (Already Correct)**

### **Python Files:**
```python
# All .py files are UTF-8 by default in Python 3
# Can write: ɛ, ɔ, ŋ, é, etc. directly in code

phoneme_inventory = ["ɛ", "ɔ", "ŋ", "ɲ"]  # ✅ Works!
```

### **JSON Export:**
```python
# We already do this correctly!
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)  # ✅ Preserves Unicode
```

**Result**: JSON files preserve all special characters ✅

---

## 🔍 **What Characters We're Dealing With**

### **Twi/Akan Characters:**

**From your 2,327 pronunciation entries:**
- ✅ Tone marks: `é` (high tone), `è` (low tone), `ê` (falling), etc.
- ✅ IPA vowels: `ɛ` (open-mid), `ɔ` (open-mid back)
- ✅ IPA consonants: `ŋ` (velar nasal), `ɲ` (palatal nasal)
- ✅ Tie bars: `c͡ɕ` (combined consonant)

**Example from your data:**
```json
{
  "word": "asase",
  "ipa": "asasé",     // ✅ Tone mark preserved
  "phonemes": ["a", "s", "a", "s", "é"]
}
```

### **Somali Characters:**

**From OCR'd grammar:**
- ✅ Standard Latin: a-z, A-Z
- ✅ Special Latin: Limited (Somali uses fairly standard Latin)
- ⚠️ OCR artifacts: `¢`, `®`, `€` (need to remove)

---

## 🛠️ **What We Built: Smart Character Handling**

### **New Utility: `mumbl_utils.text_utils`**

```python
from mumbl_utils import clean_ocr_artifacts, extract_phonemes

# Clean OCR garbage while preserving linguistic symbols
text = "The cost is ¢5 for asasé"
cleaned = clean_ocr_artifacts(text)
# Result: "The cost is 5 for asasé"  ✅ Kept 'é', removed '¢'

# Extract phonemes from IPA
phonemes = extract_phonemes("asasé")
# Result: ['a', 's', 'a', 's', 'é']
```

**What it does:**
- ✅ Removes OCR garbage: `¢`, `®`, `€`, `™`
- ✅ Preserves linguistic symbols: `é`, `ɛ`, `ɔ`, `ŋ`, `ɲ`
- ✅ Handles Unicode normalization (NFC vs NFD)
- ✅ Validates IPA notation

---

## 📊 **Character Categories in Your Data**

### **Category 1: Keep Always** ✅
```
ASCII letters:  a-z, A-Z
ASCII digits:   0-9
Basic punct:    . , ! ? ' " -
IPA symbols:    ɛ ɔ ŋ ɲ ʃ ʒ θ ð ɡ ʔ
Tone marks:     á à â ã é è ê í ì ó ò ú ù
Combining:      ◌́  ◌̀  ◌̂  (combining accents)
```

### **Category 2: Remove (OCR Artifacts)** ❌
```
Currency:    ¢ £ ¥ € $
Symbols:     © ® ™ § ¶ † ‡
```

### **Category 3: Context-Dependent** ⚠️
```
Numbers in IPA:  "3" in "abdk3séni" ← OCR error, should be removed
Hyphens:         "-" in text ← Keep
                 "-" in page numbers ← Remove
```

---

## 🎯 **Recommended Storage Format**

### **For Text Segments:**

```python
{
  "text": "Waa gu mahadsantahay",  # Native Somali (UTF-8)
  "text_cleaned": "Waa gu mahadsantahay",  # OCR artifacts removed
  "lang": "so",
  "script": "Latn"  # Script identifier
}
```

### **For Pronunciations (G2P Overrides):**

```python
{
  "word": "asase",       # Native Twi (UTF-8)
  "ipa": "asasé",        # IPA with tone marks (UTF-8)
  "ipa_normalized": "asasé",  # NFC normalization
  "phonemes": ["a", "s", "a", "s", "é"]  # Extracted
}
```

### **For Database:**

```sql
-- Already correct! Just add normalization on insert
INSERT INTO text_segments (text, ...)
VALUES (normalize_unicode(text, 'NFC'), ...);
```

---

## 💾 **Unicode Normalization (NFC vs NFD)**

### **The Problem:**
The letter `é` can be stored TWO ways:

1. **NFC (Composed)**: `é` = single character (U+00E9)
2. **NFD (Decomposed)**: `é` = `e` + combining accent (U+0065 + U+0301)

Both **display** the same but **compare** differently!

### **The Solution:**
```python
# Always normalize to NFC before storage
from mumbl_utils import normalize_unicode

text = normalize_unicode(text, 'NFC')  # Consistent storage
```

**Why NFC?**
- ✅ More compact (fewer characters)
- ✅ Better database performance
- ✅ Easier string comparison
- ✅ Standard for most applications

---

## ✅ **What This Means for Your System**

### **Current Status:** ✅ **CORRECT**

1. **Database**: UTF-8 PostgreSQL ✅
2. **Python**: UTF-8 default ✅
3. **JSON**: `ensure_ascii=False` ✅
4. **Storage**: Native characters preserved ✅

### **What We Added:**

1. **OCR Artifact Cleaning**: Remove `¢`, `®`, etc. but keep `é`, `ɛ`
2. **Phoneme Extraction**: Split IPA into individual sounds
3. **Unicode Normalization**: Consistent NFC form

---

## 🎯 **Practical Examples from Your Data**

### **Twi Dictionary Entry:**
```
Input:  "abdk3séni" (OCR artifact: '3' should be 'ɔ')
Clean:  "abdkɔséni" (if we had better OCR)
Store:  "abdk3séni" (as-is for now, Curator filters later)
```

### **Somali Sentence:**
```
Input:  "Waa gu mahadsantahay"
Clean:  "Waa gu mahadsantahay" (already clean)
Store:  "Waa gu mahadsantahay" (UTF-8)
```

### **IPA Notation:**
```
Input:  "asasé"
Normalize: "asasé" (NFC)
Extract:   ["a", "s", "a", "s", "é"]
Store:     "asasé" (UTF-8, NFC form)
```

---

## 🚨 **What NOT to Do**

### **❌ DON'T: ASCII-only Storage**
```python
# BAD!
text = text.encode('ascii', errors='ignore').decode('ascii')
# "asasé" → "asase" (LOST tone information!)
```

### **❌ DON'T: Remove All Special Characters**
```python
# BAD!
text = ''.join(c for c in text if ord(c) < 128)
# Destroys IPA: "ɛbɛ" → "bb" (WRONG!)
```

### **❌ DON'T: Mixed Normalization**
```python
# BAD! Some NFC, some NFD → comparison fails
if "café" == "café":  # Might be False if different forms!
```

---

## ✅ **What TO Do (Best Practices)**

### **1. Clean OCR Artifacts Early**
```python
from mumbl_utils import clean_ocr_artifacts

text = clean_ocr_artifacts(ocr_text)  # Remove ¢®€, keep éɛɔ
```

### **2. Normalize to NFC Before Storage**
```python
from mumbl_utils import normalize_unicode

text = normalize_unicode(text, 'NFC')  # Consistent form
```

### **3. Preserve Native Characters**
```python
# Store exactly as spoken/written
segment = TextSegment(
    text="asasé",  # Keep tone mark!
    lang="tw"
)
```

### **4. Validate IPA**
```python
from mumbl_utils import is_valid_ipa

if is_valid_ipa(pronunciation):
    store_in_database(pronunciation)
```

---

## 🎯 **Answer to Your Question**

> "Would it be better to store each language in their proper characters?"

**YES! Absolutely!** And we're already doing it correctly:

✅ **UTF-8 everywhere** (database, files, Python)  
✅ **Native characters preserved** (tone marks, IPA symbols)  
✅ **OCR artifacts cleaned** (remove garbage, keep linguistic symbols)  
✅ **NFC normalization** (consistent Unicode form)

**Additional safeguards added:**
- `clean_ocr_artifacts()` - Smart cleaning
- `normalize_unicode()` - Consistent form
- `extract_phonemes()` - IPA processing
- `is_valid_ipa()` - Validation

---

## 📋 **Integration with Pipeline**

### **Text Lane (Updated Flow):**
```python
# 1. Parse document (with OCR if needed)
doc = parser.parse("document.pdf")

# 2. Clean OCR artifacts
from mumbl_utils import clean_ocr_artifacts, normalize_unicode
text = clean_ocr_artifacts(doc.text)
text = normalize_unicode(text, 'NFC')

# 3. Process with LangExtract
segments = langextract.extract(text, ...)

# 4. Store in database (UTF-8)
repo.insert(segments)
```

---

## ✅ **Summary**

**Current State**: ✅ **CORRECT**
- UTF-8 storage working
- Special characters preserved
- Database supports all Unicode

**What We Added**:
- ✅ OCR artifact cleaning
- ✅ Unicode normalization
- ✅ Phoneme extraction
- ✅ IPA validation

**Recommendation**: 
- ✅ Continue storing native characters
- ✅ Use cleaning utilities on OCR text
- ✅ Normalize to NFC before database insert
- ✅ Never transliterate or remove linguistic symbols

**Your data integrity is solid!** 🎯

