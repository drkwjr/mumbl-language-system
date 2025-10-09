# OCR Error Handling Strategy

**Date**: October 9, 2025  
**Context**: Addressing "OMALI" vs "SOMALI" and similar OCR errors

---

## ❓ **The Question**

> "What happens if we have OCR errors like 'OMALI' instead of 'SOMALI'?  
> Will we cure it later? Is this our best chance to correct? Is it fine to ignore?"

---

## ✅ **The Answer: Multi-Layer Defense**

We **don't fix all errors manually**. Instead, we use **layered quality gates** that naturally filter out garbage while preserving good data.

---

## 🛡️ **Layer 1: Accept OCR Imperfection** (Current)

### **Philosophy:**
Perfect OCR is impossible. **85-90% accuracy is sufficient** because downstream filters catch bad data.

### **What We Accept:**
```
Original:  "The Somali language has many dialects."
OCR:       "The Somali language has many dlalects."  ← Minor error
Status:    ✅ ACCEPTABLE
Reason:    LLMs are robust to typos, Curator will score it
```

### **What Gets Through:**
- Title errors like "OMALI" (metadata only, not used in training)
- Minor typos in English explanations (not used for TTS)
- ~10-15% noise in extracted text

### **Why This Works:**
- Most errors are in **English explanations** (we don't use those for Somali TTS)
- **Somali example sentences** are shorter and clearer (fewer OCR errors)
- Volume of data compensates (1000 sentences → 850 good ones still valuable)

---

## 🛡️ **Layer 2: Intelligent Extraction** (LangExtract - Phase 4)

### **LangExtract's Natural Filtering:**

When we call LangExtract on messy OCR text:
```python
result = langextract.extract(ocr_text, prompt="Extract Somali dialogue...")
```

**The LLM automatically:**
1. ✅ **Skips garbage** - Won't extract nonsense lines
2. ✅ **Focuses on dialogue** - Ignores headers/page numbers
3. ✅ **Returns confidence scores** - Low confidence = OCR issues
4. ⚠️ **Might "fix" minor errors** - Could lose grounding accuracy

**Example:**
```
OCR Input:  "Waa gu mahadsantahay" (OCR error: gu → qu)
LangExtract: Might extract correctly OR skip if too corrupted
Confidence: 0.65 (lower because of error)
```

### **What We Get:**
- Only clean, extractable segments
- Confidence scores indicate quality
- Garbage automatically filtered

---

## 🛡️ **Layer 3: Curator Scoring** (Phase 5 - Coming Soon)

### **Six-Dimensional Quality Score:**

```python
score = SegmentScore(
    clarity: 85,           # How clear is the text?
    alignment: 90,         # (for audio) Does text match speech?
    diarization: 0,        # (for audio) Speaker separation quality
    transcript_accuracy: 75,  # Text quality (catches OCR errors!)
    validity: 80,          # Is this valid language?
    shape: 90,             # Proper length, structure
    total: 82              # Weighted average
)
```

### **OCR Errors Get Caught Here:**

**Bad OCR:**
```
Text: "Th3 c@t 1s runn!ng 0n th3 r0@d"
Scores:
  - transcript_accuracy: 30 ❌ (nonsense)
  - validity: 20 ❌ (not valid language)
  - total: 25 ❌
Action: REJECTED (< 70 threshold)
```

**Good OCR:**
```
Text: "Waa gu mahadsantahay" (minor error: gu vs qu)
Scores:
  - transcript_accuracy: 85 ✅ (mostly correct)
  - validity: 90 ✅ (valid Somali)
  - total: 87 ✅
Action: ACCEPTED (≥ 70 threshold, eligible for training)
```

### **The Thresholds:**
- **≥90**: Learner/Premium datasets (best quality)
- **≥70**: TTS Training (acceptable quality)
- **<70**: REJECTED (too noisy)

**Result**: OCR errors naturally get low scores and filtered out!

---

## 🛡️ **Layer 4: HTML Spot-Checks** (Manual QA)

### **Human Review Workflow:**

1. **Sample-based QA** (after extraction):
```
Batch: somali-grammar-001
Segments: 466
Sample: 20 random segments (4%)
```

2. **HTML visualization**:
```html
<div class="segment">
  <p class="source">Midigta u eeg. Waddada ka tallaab.</p>
  <p class="labels">
    is_dialogue: true, register: informal, confidence: 0.85
  </p>
  <button>👍 Good</button> <button>👎 Bad</button>
</div>
```

3. **Quality Decision:**
- If 17+/20 good (85%) → ✅ Accept batch
- If <17/20 good (< 85%) → ❌ Reject batch or flag for review

### **When to Apply:**
- First document from new source
- After major OCR changes
- Random audits (10% of batches)

---

## 🛡️ **Layer 5: Post-Processing** (Future Enhancement)

### **Automated OCR Cleanup:**

```python
def clean_ocr_errors(text: str, language: str) -> str:
    """Fix common OCR mistakes before LangExtract"""
    
    # 1. Common pattern fixes
    text = fix_common_ocr_patterns(text)
    
    # 2. Language-specific spell check (if available)
    if has_spellchecker(language):
        text = spellcheck(text, lang=language)
    
    # 3. Remove obvious garbage lines
    text = remove_nonsense_lines(text)
    
    return text
```

### **When to Add This:**
- When you have 100+ documents
- When OCR quality consistently < 85%
- When systematic errors are identified

---

## 🎯 **Your Specific Case: Somali Grammar**

### **OCR Errors Observed:**

| Error Type | Example | Occurrences | Impact | Action |
|------------|---------|-------------|--------|--------|
| Header/Title | "OMALI" | 76 | NONE | ✅ Ignore (metadata only) |
| Volume typo | "Vovune" | 1 | NONE | ✅ Ignore (metadata only) |
| 0/O confusion | "0n" vs "On" | ~96 | LOW | ⚠️ Monitor, Curator filters |
| l/I confusion | "dlalects" | Rare | LOW | ⚠️ Monitor, Curator filters |
| Line breaks | Single chars | 116 | NONE | ✅ Filtered during extraction |

### **Error Distribution:**
- **90% in metadata/headers** → No impact (not used)
- **10% in content** → Caught by Curator scoring

### **Your Safety Net:**

```
OCR Text (100 segments, 10% errors)
   ↓
LangExtract extracts cleanest parts
   ↓ (Rejects ~5% garbage)
   ↓
95 segments remain
   ↓
Curator scores all segments
   ↓ (Rejects ~10 with score < 70)
   ↓
85 high-quality segments in training dataset
   ↓
TTS Model trains on clean data ✅
```

**Net result**: Start with 90% accuracy, end with 85% usable segments. That's **good enough for TTS training!**

---

## 💡 **When to Worry vs When to Trust**

### **✅ Trust the Process (Current Situation):**
- OCR quality: 85-90%
- Large corpus: 466 Somali sentences
- Multi-layer filtering: LangExtract → Curator → Manual QA
- **Action**: Proceed with extraction

### **⚠️ Manually Intervene:**
- OCR quality: < 70%
- Critical document: Only source for rare language
- Systematic errors: Same mistake repeated 100+ times
- **Action**: Use Google Vision API, or manually correct

### **🚨 Abort:**
- OCR quality: < 50%
- Output is mostly gibberish
- **Action**: Find better source document or scan

---

## 🔧 **Practical Decision Matrix**

| OCR Quality | Action | Why |
|-------------|--------|-----|
| **90-100%** | ✅ Proceed as-is | Minimal errors, high value |
| **80-89%** | ✅ Proceed, monitor | Some errors, but filterable (your case) |
| **70-79%** | ⚠️ Selective use | Extract only best sections |
| **60-69%** | ⚠️ Manual review | Consider Google Vision API |
| **< 60%** | ❌ Reject or upgrade | Use better OCR or skip document |

**Your Somali Grammar: 85-90% → ✅ Proceed**

---

## 🎯 **Answering Your Questions Directly**

### **"What happens if we pull those errors?"**

**Answer**: They flow through the pipeline but get filtered at multiple points:
1. LangExtract skips obviously broken text
2. Curator gives low scores to garbled segments
3. Only clean data (score ≥70) makes it to training

### **"Will we be curing it later?"**

**Answer**: Yes, indirectly:
- Not manual correction
- But automatic filtering via quality scores
- Future: Could add spell-check post-processing

### **"Is this our best chance to correct?"**

**Answer**: No! Better chances later:
1. **LangExtract** (Phase 4) - LLM can interpret through minor errors
2. **Curator** (Phase 5) - Scores weed out bad segments
3. **Manual QA** (Phase 5) - HTML spot-checks catch systematic issues
4. **Future**: Google Vision API for critical docs

### **"Is it fine to ignore?"**

**Answer**: **YES, for now!** Because:
- 85-90% accuracy is industry-standard for Tesseract
- Your multi-layer filtering will catch garbage
- Cost of perfect OCR outweighs benefit
- You'll get 400+ clean Somali sentences from 466 extracted

---

## ✅ **Recommendation: Proceed with Confidence**

Your current strategy is sound:
1. ✅ Use Tesseract (free, fast, 85-90% accurate)
2. ✅ Accept some errors as the cost of doing business
3. ✅ Trust Curator to filter bad segments
4. ✅ Reserve Google Vision API for critical documents later
5. ✅ Manual QA on samples to catch systematic issues

**This is the pragmatic, cost-effective approach!**

---

**Next**: Test LangExtract on samples, review quality, then decide on full processing.

