#!/usr/bin/env python3
"""Batch-ingest Rattray's Akan-Ashanti Folk-Tales (1930) into the conversational corpus via vision re-OCR.

Checkpointed + resumable (re-run to continue; safe to interrupt). OCRs only the Twi pages (detected from
the djvu + scandata), keeps the [TWI] paragraphs, writes one record per page. Output is BULK corpus
(reduced Rattray orthography; run normalize_orthography.py next) -> gitignored, Postgres-bound later.

  set -a; source ../mumbl-server/.env; set +a
  /tmp/ytenv/bin/python bank/ingest/rattray_folktales.py            # all Twi pages (resumable)
  /tmp/ytenv/bin/python bank/ingest/rattray_folktales.py --limit 3  # first N (smoke test)
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from iiif_page import fetch_page  # noqa: E402
from vision_ocr import ocr_image  # noqa: E402

ITEM = "akanashantifolkt0000ratt"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources"
CORPUS = ROOT / "corpus" / "aka-asante"
OUT = CORPUS / "rattray-folktales.jsonl"
CKPT = CORPUS / ".rattray-folktales.ckpt.json"


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read()


def _cache(name, url):
    p = SRC / name
    if not p.exists():
        p.write_bytes(_get(url))
    return p.read_text(encoding="utf-8", errors="replace")


def twi_leaves():
    """Twi-dense printed pages (from djvu) -> scan leaves (from scandata)."""
    djvu = _cache("rattray-folktales.djvu.txt", f"https://archive.org/download/{ITEM}/{ITEM}_djvu.txt")
    scan = _cache("rattray-folktales.scandata.xml", f"https://archive.org/download/{ITEM}/{ITEM}_scandata.xml")
    parts = re.split(r"\n\s*(\d{1,3})\s*\n", djvu)
    twi_pages = set()
    for i in range(1, len(parts) - 1, 2):
        pg = int(parts[i]); body = parts[i + 1].lower()
        twi = sum(body.count(k) for k in (" na ", "ananse", " no ", " se ", " wo "))
        eng = sum(body.count(k) for k in (" the ", " and ", " he ", " said "))
        if twi > 12 and eng < 6 and 1 < pg < 400:
            twi_pages.add(pg)
    p2l = {}
    for b in re.finditer(r'<page leafNum="(\d+)"(.*?)</page>', scan, re.S):
        pn = re.search(r"<pageNumber>(.*?)</pageNumber>", b.group(2))
        if pn and pn.group(1).strip().isdigit():
            p2l[int(pn.group(1))] = int(b.group(1))
    return sorted({p2l[p]: p for p in twi_pages if p in p2l}.items())  # [(leaf, page), ...]


def load_ckpt():
    return set(json.loads(CKPT.read_text())) if CKPT.exists() else set()


def main():
    CORPUS.mkdir(parents=True, exist_ok=True)
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    if "--range" in sys.argv:  # explicit leaf range (the Twi-originals are a back section; djvu detection is unreliable)
        i = sys.argv.index("--range")
        a, b = int(sys.argv[i + 1]), int(sys.argv[i + 2])
        leaves = [(lf, lf) for lf in range(a, b + 1)]  # page unknown; keep [TWI] by label at normalize time
    else:
        leaves = twi_leaves()
    if limit:
        leaves = leaves[:limit]
    done = load_ckpt()
    todo = [(lf, pg) for lf, pg in leaves if lf not in done]
    print(f"Rattray folk-tales: {len(leaves)} Twi pages, {len(done)} done, {len(todo)} to OCR")

    for n, (leaf, page) in enumerate(todo, 1):
        try:
            img = fetch_page(ITEM, leaf, out_dir=CORPUS / "_img")
            text = ocr_image(str(img))
            twi = "\n".join(ln for ln in text.splitlines() if not ln.strip().startswith("[ENG]"))
            with OUT.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"source": "rattray-folktales", "dialect": "aka-asante",
                                    "orthography": "rattray-reduced", "leaf": leaf, "page": page,
                                    "text": text, "twi": twi}, ensure_ascii=False) + "\n")
            done.add(leaf)
            CKPT.write_text(json.dumps(sorted(done)))
            print(f"  [{n}/{len(todo)}] leaf {leaf} (p.{page}) OCR'd, {len(text)} chars")
        except Exception as e:
            print(f"  [{n}/{len(todo)}] leaf {leaf} FAILED: {e}")
    print(f"done. corpus -> {OUT} ({len(done)} pages). next: normalize_orthography.py")


if __name__ == "__main__":
    main()
