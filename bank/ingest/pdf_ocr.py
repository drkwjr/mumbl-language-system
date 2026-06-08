#!/usr/bin/env python3
"""Vision-OCR a scanned PDF with Gemini Flash — cheap (~$0.0003/page), special-char faithful.

Renders pages with pdftoppm, OCRs each in parallel, checkpoints per page (re-run resumes; never re-pay).
For the public-domain scanned books (FSI Twi textbook etc.). Output is bulk corpus text -> gitignored.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/pdf_ocr.py "/path/to.pdf" --name fsi-twi-course [--dpi 150] [--workers 6]
"""
import base64
import json
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "aka-asante" / "_books"
USAGE = {"in": 0, "out": 0, "lock": __import__("threading").Lock()}
PROMPT = ("Transcribe this page from a Twi (Akan) language textbook. Preserve every special character "
          "exactly — ɛ ɔ ŋ and tone marks — do not normalize to e/o. Keep the dialogue / drill / "
          "vocabulary layout. Output ONLY the transcription.")


def gemini_ocr(img_path):
    import os
    key = os.environ["GEMINI_API_KEY"]
    b64 = base64.b64encode(img_path.read_bytes()).decode()
    body = json.dumps({"contents": [{"parts": [{"text": PROMPT}, {"inline_data": {"mime_type": "image/png", "data": b64}}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 3000}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    for t in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=120).read())
            u = r.get("usageMetadata", {})
            with USAGE["lock"]:
                USAGE["in"] += u.get("promptTokenCount", 0)
                USAGE["out"] += u.get("candidatesTokenCount", 0)
            return r["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            __import__("time").sleep(2 * (t + 1))
    return ""


def main():
    pdf = sys.argv[1]
    name = sys.argv[sys.argv.index("--name") + 1] if "--name" in sys.argv else Path(pdf).stem
    dpi = int(sys.argv[sys.argv.index("--dpi") + 1]) if "--dpi" in sys.argv else 150
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 6

    imgdir = CORPUS / f"{name}_img"
    imgdir.mkdir(parents=True, exist_ok=True)
    if not list(imgdir.glob("p*.png")):
        print("rendering PDF pages...", flush=True)
        subprocess.run(["pdftoppm", "-png", "-r", str(dpi), pdf, str(imgdir / "p")], check=True)
    pages = sorted(imgdir.glob("p*.png"))

    out = CORPUS / f"{name}.jsonl"
    ckpt = CORPUS / f".{name}.ckpt.json"
    done = set(json.loads(ckpt.read_text())) if ckpt.exists() else set()
    todo = [p for p in pages if p.stem not in done]
    print(f"{name}: {len(pages)} pages, {len(done)} done, {len(todo)} to OCR, {workers} workers", flush=True)

    def work(p):
        return p.stem, gemini_ocr(p)

    n = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for stem, text in ex.map(work, todo):
            n += 1
            if text:
                with out.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"page": stem, "text": text}, ensure_ascii=False) + "\n")
                done.add(stem)
                ckpt.write_text(json.dumps(sorted(done)))
            if n % 20 == 0 or n == len(todo):
                print(f"  {n}/{len(todo)} pages", flush=True)
    cost = USAGE["in"] * 0.30 / 1e6 + USAGE["out"] * 2.50 / 1e6
    print(f"done -> {out}  · COST ~${cost:.4f} (gemini-2.5-flash)", flush=True)


if __name__ == "__main__":
    main()
