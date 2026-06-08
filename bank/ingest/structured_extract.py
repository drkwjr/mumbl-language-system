#!/usr/bin/env python3
"""Extract glossed Twi↔English PAIRS from a book's OCR text via Gemini STRUCTURED OUTPUT (responseSchema).

Clean JSON, no brittle parser, no format variance — the meaning side, not just bare words. Public-domain
books -> committed glosses layer (can feed generation); copyrighted -> restricted (verifier/gloss only).

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/structured_extract.py fsi-twi-course        # uses the _books/<name>.jsonl OCR text
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402

BOOKS = Path(__file__).resolve().parents[1] / "corpus" / "aka-asante" / "_books"
DATA = Path(__file__).resolve().parents[1] / "data" / "aka"
USAGE = {"in": 0, "out": 0, "lock": __import__("threading").Lock()}

# book -> (license, output path). public-domain -> committed data/; copyrighted -> restricted (gitignored).
CONFIG = {
    "fsi-twi-course": ("public-domain", DATA / "glosses-fsi.jsonl"),
    "denteh-spoken-twi": ("copyright-restricted", DATA / "_restricted" / "glosses-denteh.jsonl"),
    "yeboa-basic-twi": ("copyright-restricted", DATA / "_restricted" / "glosses-yeboa.jsonl"),
    # LearnAkan paid course (copyright-restricted -> _restricted; feeds verifier + gloss + generation)
    "learnakan-idioms": ("copyright-restricted", DATA / "_restricted" / "glosses-learnakan-idioms.jsonl"),
    "learnakan-conversational": ("copyright-restricted", DATA / "_restricted" / "glosses-learnakan-conversational.jsonl"),
    "learnakan-vocab-companion": ("copyright-restricted", DATA / "_restricted" / "glosses-learnakan-vocab.jsonl"),
}
SCHEMA = {"type": "array", "items": {"type": "object", "properties": {
    "twi": {"type": "string"}, "english": {"type": "string"}, "pos": {"type": "string"}}, "required": ["twi", "english"]}}


def extract_chunk(text):
    key = os.environ["GEMINI_API_KEY"]
    prompt = ("Extract every Twi word or short phrase paired with its English meaning from this Twi-course "
              "text. Preserve ɛ ɔ ŋ and tone marks exactly. Only genuine Twi↔English pairs — skip drills, "
              "exercises, page numbers, and English-only instructions.\n\n" + text)
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


def chunks(pages, size=6000):
    buf = ""
    for p in pages:
        buf += p["text"] + "\n"
        if len(buf) >= size:
            yield buf
            buf = ""
    if buf.strip():
        yield buf


def main():
    bank = Bank()
    name = sys.argv[1]
    lic, out = CONFIG.get(name, ("copyright-restricted", DATA / "_restricted" / f"glosses-{name}.jsonl"))
    pages = [json.loads(l) for l in (BOOKS / f"{name}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    cks = list(chunks(pages))
    print(f"{name}: {len(pages)} pages -> {len(cks)} chunks ({lic})", flush=True)

    pairs = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for res in ex.map(extract_chunk, cks):
            pairs += res

    # keep pairs whose Twi side is plausibly Twi (membership), dedup by (twi, english)
    seen, rows = set(), []
    for p in pairs:
        tw = (p.get("twi") or "").strip()
        en = (p.get("english") or "").strip()
        if not tw or not en:
            continue
        head = tw.lower().split()[0].strip("'’.,")
        if not any("aka" in lid.membership(t.strip("'’.,"), bank) or any(c in t for c in "ɛɔŋ")
                   for t in tw.lower().split()[:3]):
            continue  # no Twi evidence in the phrase -> skip
        k = (tw.lower(), en.lower())
        if k in seen:
            continue
        seen.add(k)
        rows.append({"twi": tw, "gloss_en": en, "pos": p.get("pos", ""), "source": name,
                     "dialect": "aka", "license": lic, "use": "gloss-pair" if lic == "public-domain" else "verifier-gloss-reference"})
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cost = USAGE["in"] * 0.30 / 1e6 + USAGE["out"] * 2.50 / 1e6
    print(f"  {len(rows)} glossed pairs -> {out.name}  · ~${cost:.4f}", flush=True)
    for r in rows[:6]:
        print(f"    {r['twi'][:24]:24} = {r['gloss_en'][:40]}")


if __name__ == "__main__":
    main()
