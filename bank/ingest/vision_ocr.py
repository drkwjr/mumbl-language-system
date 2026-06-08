#!/usr/bin/env python3
"""Programmatic vision OCR — faithful transcription of a page image, for re-OCR at scale.

The in-session route (Claude reads the JPG) is perfect for a handful of high-value pages but won't
scale to a 330-page folktale book. This drives a vision model over page images with an orthography-aware
prompt so the special characters survive (the whole point — djvu flattens ɛ/ɔ/ŋ/tone). Pairs with
iiif_page.py (fetch) to ingest bulk scanned sources into the conversational corpus.

  set -a; source ../mumbl-server/.env; set +a
  /tmp/ytenv/bin/python bank/ingest/vision_ocr.py <image.jpg> [--lang twi]
"""
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

MODEL = os.environ.get("OCR_MODEL", "gpt-4o")  # full 4o for special-char fidelity, not mini

TWI_PROMPT = (
    "You are transcribing a scanned page of a book that contains AKAN / TWI (a Ghanaian language). "
    "Transcribe the page EXACTLY as printed, preserving every special character and diacritic: ɛ ɔ ŋ, "
    "the nasal/length/tone marks, and any ATR marks. Do NOT normalize ɛ→e or ɔ→o. Keep line breaks. "
    "If the page has both Twi and English (e.g. a translation), transcribe both and label them "
    "[TWI] / [ENG] per paragraph. Output ONLY the transcription, no commentary."
)


def ocr_image(path: str, prompt: str = TWI_PROMPT) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENAI_API_KEY not set (source ../mumbl-server/.env)")
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
        ]}],
        "temperature": 0,
        "max_tokens": 4096,  # cap runaway outputs (a real column is ~400 tok; some loop to 20k+ -> cost)
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    res = json.loads(urllib.request.urlopen(req, timeout=180).read())
    return res["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    print(ocr_image(sys.argv[1]))


if __name__ == "__main__":
    main()
