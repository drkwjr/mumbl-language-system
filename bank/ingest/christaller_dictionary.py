#!/usr/bin/env python3
"""Ingest Christaller's 1881 Dictionary of the Asante and Fante Language via vision re-OCR.

The bulk vocabulary lever. The print carries Christaller's dotted orthography (ẹ=ɛ, ọ=ɔ, ŋ) + tone
marks, which the djvu flattened/mangled but vision recovers cleanly. Each entry -> headword (mapped to
modern ɛ/ɔ), POS, English gloss. Checkpointed/resumable. 709 leaves total -> a real paid batch; run a
small --range first.

  set -a; source ../mumbl-server/.env; set +a
  /tmp/ytenv/bin/python bank/ingest/christaller_dictionary.py --range 120 122    # sample
  /tmp/ytenv/bin/python bank/ingest/christaller_dictionary.py --range 30 709     # full (ask first; ~$15-20)
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iiif_page import fetch_page  # noqa: E402
from vision_ocr import ocr_image  # noqa: E402

ITEM = "adictionaryasan00chrigoog"
ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus" / "aka-akuapem"  # Christaller's standard is Akuapem-based
OUT = CORPUS / "christaller-dictionary.jsonl"
CKPT = CORPUS / ".christaller-dictionary.ckpt.json"

PROMPT = (
    "Transcribe this page from Christaller's 1881 Dictionary of the Asante and Fante (Twi) language. "
    "Preserve EVERY special character exactly: ẹ ọ ŋ ñ and the acute/grave tone marks — do NOT normalize "
    "them to e/o. Each dictionary entry begins with a bold headword, then part of speech, then the English "
    "definition (Twi example sentences may follow). Put ONE entry per line. Output only the entries."
)


def to_modern(headword):
    """Christaller dotted orthography -> modern Akan (ẹ->ɛ, ọ->ɔ); strip tone/diacritics + entry markup."""
    h = headword.replace("ẹ", "ɛ").replace("ọ", "ɔ").replace("ñ", "ŋ").replace("ụ", "u")
    h = re.sub(r"[̀-ͯ]", "", h)  # combining tone marks
    h = h.strip(" .,;[](){}*").replace("-", "").lower()
    return h


# Entries are blank-line-separated blocks; the headword is the leading word before the first comma/
# period (the model wraps it in **bold** only sometimes, so don't depend on that).
POS_RE = re.compile(r"\b(n|v|a|adj|adv|interj|prep|conj|num|pron|pl|inf|F|Ak|As|s|cf|syn|pr|red)\.")
TWI_CH = "a-zẹọŋñǫǭɛɔɪʊ'’"


def parse_entries(text):
    out = []
    for block in re.split(r"\n\s*\n", text):
        block = " ".join(block.replace("**", "").split())  # drop bold, collapse wrapped lines
        m = re.match(rf"\s*([{TWI_CH}][{TWI_CH}.̀-ͯ-]{{0,29}}?)\s*[,.]\s*(.+)", block, re.I)
        if not m:
            continue
        head = m.group(1).strip(" .,")
        rest = m.group(2).strip()
        if not head or len(head.split()) > 1 or not re.search(rf"[{TWI_CH}]", head, re.I):
            continue  # headword must be a single Twi-looking token
        pm = POS_RE.search(rest)
        out.append({"headword": head, "modern": to_modern(head), "pos": (pm.group(0) if pm else ""),
                    "gloss_en": rest[:160], "source": "christaller-dictionary", "dialect": "aka-akuapem",
                    "dialect_status": "attested", "orthography": "christaller-dotted", "verification": "sourced"})
    return out


# Pages are two dense columns; OCR each column separately (a whole page overloads one call -> timeout).
# IIIF percentage regions are robust to per-page size differences. Overlap the gutter so no entry is cut.
COLUMNS = [("L", "pct:0,0,53,100"), ("R", "pct:47,0,53,100")]


WORKERS = 8  # concurrent OCR calls — bulk OCR is I/O-bound on the API; sequential is far too slow


def ocr_column(leaf, region, tries=4):
    import time
    last = None
    for t in range(tries):
        try:
            img = fetch_page(ITEM, leaf, region=region, out_dir=CORPUS / "_img", size="1500,")
            return ocr_image(str(img), PROMPT)
        except Exception as e:
            last = e
            time.sleep(2 * (t + 1))  # backoff — polite under API rate limits on a large run
    raise last


def process_leaf(leaf):
    """OCR both columns of a leaf and parse. Returns (leaf, raw_rows, unique_entries). Runs in a worker."""
    raws, entries = [], []
    for col, region in COLUMNS:
        text = ocr_column(leaf, region)
        raws.append({"leaf": leaf, "col": col, "text": text})
        entries += parse_entries(text)
    seen, uniq = set(), []
    for e in entries:
        k = (e["modern"], e["pos"])
        if k not in seen:
            seen.add(k)
            uniq.append(dict(e, leaf=leaf))
    return leaf, raws, uniq


def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed

    CORPUS.mkdir(parents=True, exist_ok=True)
    i = sys.argv.index("--range")
    a, b = int(sys.argv[i + 1]), int(sys.argv[i + 2])
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else WORKERS
    done = set(json.loads(CKPT.read_text())) if CKPT.exists() else set()
    todo = [lf for lf in range(a, b + 1) if lf not in done]
    print(f"Christaller dictionary: leaves {a}..{b}, {len(done)} done, {len(todo)} to OCR, {workers} workers")
    RAW = OUT.with_name("christaller-dictionary.raw.jsonl")
    total, n = 0, 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(process_leaf, lf): lf for lf in todo}
        for fut in as_completed(futs):
            leaf = futs[fut]
            n += 1
            try:
                _, raws, uniq = fut.result()
            except Exception as e:
                print(f"  [{n}/{len(todo)}] leaf {leaf} FAILED after retries: {e}")
                continue
            # writes + checkpoint happen here in the main thread (serialized -> no locking needed)
            with RAW.open("a", encoding="utf-8") as rf:
                for r in raws:
                    rf.write(json.dumps(r, ensure_ascii=False) + "\n")
            with OUT.open("a", encoding="utf-8") as f:
                for e in uniq:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
            done.add(leaf)
            CKPT.write_text(json.dumps(sorted(done)))
            total += len(uniq)
            if n % 10 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)} pages, {total} entries")
    print(f"done. {total} entries -> {OUT}")


if __name__ == "__main__":
    main()
