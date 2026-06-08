#!/usr/bin/env python3
"""Extract the LearnAkan English-Twi Dictionary (a modern Asante Twi reference) into glossed pairs.

Digital text (real text layer — special chars ɛ ɔ ŋ come through clean, no OCR). It's a 2-column layout,
so crop each column region separately (pdftotext -x/-W) to keep entries in reading order, then pull every
English<->Twi sense pair + the bilingual example sentences via Gemini structured output (responseSchema).

Copyrighted (LearnAkan 2023) -> _restricted/ (verifier + gloss + generation grounding per the "use all
banked data" call; NOT redistributed — gitignored). {twi, gloss_en, pos, ...} per row.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/learnakan_dictionary.py "bank/sources/learnakan/LearnAkan English-Twi Dictionary....pdf"
"""
import json
import os
import re
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "aka"
OUT = DATA / "_restricted" / "learnakan-dictionary.jsonl"
USAGE = {"in": 0, "out": 0, "lock": __import__("threading").Lock()}
SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "twi": {"type": "string"}, "english": {"type": "string"}, "pos": {"type": "string"}},
    "required": ["twi", "english"]}}


def columns(pdf):
    """Extract the page as two cropped columns (left 0-216pt, right 216-432pt) so entries stay intact."""
    def crop(x, w):
        return subprocess.run(["pdftotext", "-layout", "-x", str(x), "-y", "0", "-W", str(w), "-H", "648", pdf, "-"],
                              capture_output=True, text=True).stdout
    return crop(0, 216) + "\n" + crop(216, 220)


def extract_chunk(text):
    key = os.environ["GEMINI_API_KEY"]
    prompt = ("This is text from an English-to-Asante-Twi dictionary. Each entry is an English headword, a "
              "part of speech (NOUN/VERB/ADJ/PHRASE/NUM...), and one or more numbered Twi translations; some "
              "entries have an example sentence (Twi | English). Extract EVERY English<->Twi pair: one row per "
              "Twi translation (twi = the Twi word/phrase, english = the headword's meaning), AND each example "
              "sentence as its own row (twi = the Twi sentence, english = its translation). Preserve ɛ ɔ ŋ and "
              "tone marks exactly. Skip running headers and page numbers.\n\n" + text)
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseMimeType": "application/json", "responseSchema": SCHEMA, "temperature": 0}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    for t in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=120).read())
            cands = r.get("candidates", [])
            parts = cands[0].get("content", {}).get("parts") if cands else None
            u = r.get("usageMetadata", {})
            with USAGE["lock"]:
                USAGE["in"] += u.get("promptTokenCount", 0)
                USAGE["out"] += u.get("candidatesTokenCount", 0)
            return json.loads(parts[0]["text"]) if parts else []
        except Exception:
            __import__("time").sleep(2 * (t + 1))
    return []


def chunks(text, size=6000):
    buf = ""
    for line in text.splitlines():
        buf += line + "\n"
        if len(buf) >= size:
            yield buf
            buf = ""
    if buf.strip():
        yield buf


def main():
    bank = Bank()
    pdf = sys.argv[1]
    print(f"extracting columns from {Path(pdf).name[:50]}...", flush=True)
    text = columns(pdf)
    cks = list(chunks(text))
    print(f"{len(text):,} chars -> {len(cks)} chunks", flush=True)

    pairs = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, res in enumerate(ex.map(extract_chunk, cks), 1):
            pairs += res
            if i % 15 == 0 or i == len(cks):
                print(f"  {i}/{len(cks)} chunks · {len(pairs)} pairs so far", flush=True)

    seen, rows = set(), []
    for p in pairs:
        tw = (p.get("twi") or "").strip()
        en = (p.get("english") or "").strip()
        if not tw or not en or len(tw) < 2:
            continue
        # keep pairs with Twi evidence (membership or special char) in the first few tokens
        if not any("aka" in lid.membership(t.strip("'’.,"), bank) or any(c in t for c in "ɛɔŋ")
                   for t in tw.lower().split()[:4]):
            continue
        k = (tw.lower(), en.lower())
        if k in seen:
            continue
        seen.add(k)
        rows.append({"twi": tw, "gloss_en": en, "pos": (p.get("pos") or "").lower(), "source": "learnakan-dictionary",
                     "dialect": "aka-asante", "license": "copyright-restricted", "use": "verifier-gloss-generation"})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cost = USAGE["in"] * 0.30 / 1e6 + USAGE["out"] * 2.50 / 1e6
    print(f"\n{len(rows):,} glossed pairs -> {OUT.name}  · ~${cost:.4f}", flush=True)
    for r in rows[:8]:
        print(f"    {r['twi'][:30]:30} = {r['gloss_en'][:34]}")


if __name__ == "__main__":
    main()
