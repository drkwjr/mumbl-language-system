#!/usr/bin/env python3
"""Fetch faithful page images from archive.org scanned sources — the front half of vision re-OCR.

Why this exists: archive.org's `<id>_djvu.txt` is OCR'd by an engine with no model for phonetic
orthography, so for low-resource-language sources it silently flattens the special characters that
*carry the sound* (ɛ→e, ɔ→o, ŋ dropped, nasal/tone/length diacritics gone). Those characters are the
grapheme→phoneme key; we cannot lose them. The fix, reusable across every language and every scanned
source: pull the original page image and re-read it with a vision model (or a human/Claude in-session)
that is told the orthography. This module is the image side of that.

IIIF image API (verified working 2026-06-07):
  full page : https://iiif.archive.org/iiif/<id>$<leaf>/full/full/0/default.jpg
  region    : https://iiif.archive.org/iiif/<id>$<leaf>/<x>,<y>,<w>,<h>/full/0/default.jpg   (zoom a line/table)
Leaf is the 0-based scan index. Map printed page -> leaf via <id>_scandata.xml (leafNum/pageNumber)
or the fulltext search-inside API.

  python3 bank/ingest/iiif_page.py grammarofasantef00chriuoft 33            # one full page
  python3 bank/ingest/iiif_page.py grammarofasantef00chriuoft 33-40         # a range
  python3 bank/ingest/iiif_page.py grammarofasantef00chriuoft 33 0,1880,2005,170   # a region crop
"""
import sys
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
IIIF = "https://iiif.archive.org/iiif"
CACHE = Path(__file__).resolve().parents[1] / "sources" / "page-images"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read()


def fetch_page(item_id: str, leaf: int, region: str | None = None, out_dir: Path = CACHE) -> Path:
    """Fetch one page (or a region crop) at full resolution. `region` = 'x,y,w,h' to zoom a line/table."""
    reg = region or "full"
    url = f"{IIIF}/{item_id}${leaf}/{reg}/full/0/default.jpg"
    data = _get(url)
    if len(data) < 1000:  # archive.org returns a short text error body for a bad leaf/region
        raise RuntimeError(f"leaf {leaf} region={reg}: server returned {len(data)} bytes (likely not found)")
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"_{region.replace(',', '-')}" if region else ""
    out = out_dir / f"{item_id}_{leaf:04d}{tag}.jpg"
    out.write_bytes(data)
    return out


def _leaves(spec: str):
    if "-" in spec:
        a, b = spec.split("-", 1)
        return range(int(a), int(b) + 1)
    return [int(spec)]


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    item_id, spec = sys.argv[1], sys.argv[2]
    region = sys.argv[3] if len(sys.argv) > 3 else None
    for leaf in _leaves(spec):
        try:
            out = fetch_page(item_id, leaf, region)
            print(f"  leaf {leaf:4} -> {out}  ({out.stat().st_size} bytes)")
        except Exception as e:
            print(f"  leaf {leaf:4} -> ERROR: {e}")


if __name__ == "__main__":
    main()
