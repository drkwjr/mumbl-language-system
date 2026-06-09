#!/usr/bin/env python3
"""Multi-language capture — don't waste the non-Akan audio the wide net pulls in; label it for later.

Broad discovery (and broad Akan searches) inevitably surface other Ghanaian/African languages — Ga, Ewe,
Hausa, Dagbani, Yoruba, plus pure English. That's not noise; it's a head start on the NEXT language. But
our transcripts are ASR'd with a Twi-forced prompt, so a non-Akan clip's TEXT is garbage — the durable
seed is the cached AUDIO. This pass finds the non-Akan clips (low Akan purity), asks Gemini what language
the AUDIO actually is (one cheap call, audio not the bad transcript), and records vid -> language so the
clip becomes a labeled seed: when we stand up that language later, we pull its clips and re-ASR properly.

Cheap + checkpointed: only the non-Akan minority gets a language-ID call, and already-IDed clips are
skipped. Writes data/aka/_captured_languages.jsonl + prints the seed inventory (what we're accumulating).

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/language_capture.py [--max 200]
"""
import base64
import json
import os
import re
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ING = Path(__file__).resolve().parent
sys.path.insert(0, str(ING.parents[0]))
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402

MEDIA = ING.parents[0] / "corpus" / "aka-asante" / "_media"
OUT = ING.parents[0] / "data" / "aka" / "_captured_languages.jsonl"
TOK = re.compile(r"[a-zɛɔŋ'’]+", re.I)
AKAN_FLOOR = 55     # >= this %% Akan tokens -> it's our language, leave it
ENGLISH_FLOOR = 55  # >= this %% English -> just English, no need to ID


def akan_english_pct(text, bank):
    c = {"aka": 0, "eng": 0, "other": 0}
    for t in set(x.strip("'’").lower() for x in TOK.findall(text)):
        if len(t) < 2:
            continue
        m = lid.membership(t, bank)
        c["aka" if "aka" in m else "eng" if "eng" in m else "other"] += 1
    tot = sum(c.values()) or 1
    return 100 * c["aka"] // tot, 100 * c["eng"] // tot


# Constrain the ID to real, plausible languages — an unbounded prompt returned garbage ("A", "Viet",
# "Neder") on music/noisy clips. Off-list or low-confidence -> "unclear", never banked as a seed.
ALLOWED = ["Akan", "Ga", "Ewe", "Dagbani", "Dagaare", "Frafra", "Gonja", "Kasem", "Nzema", "Hausa",
           "Yoruba", "Igbo", "Fula", "Wolof", "English", "French", "Arabic"]


def id_audio_language(mp3):
    """One cheap Gemini call on the AUDIO (not the Twi-forced transcript): which language, from a fixed
    list. Returns a list language, or None for unclear/music/noise (so noise never becomes a fake seed)."""
    key = os.environ["GEMINI_API_KEY"]
    b64 = base64.b64encode(mp3.read_bytes()).decode()
    p = ("Identify the single language primarily SPOKEN in this audio. Reply with EXACTLY ONE of these "
         "words and nothing else: " + ", ".join(ALLOWED) + ", or 'unclear' if it is mostly music, noise, "
         "silence, or you are not confident.")
    body = json.dumps({"contents": [{"parts": [{"text": p}, {"inline_data": {"mime_type": "audio/mp3", "data": b64}}]}],
                       "generationConfig": {"temperature": 0, "maxOutputTokens": 30}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}), timeout=60).read())
        ans = r["candidates"][0]["content"]["parts"][0]["text"].strip().split("\n")[0].strip(".,!?\"' ")
        return next((a for a in ALLOWED if a.lower() == ans.lower()), None)  # only a real list match counts
    except Exception:
        return None


def main():
    bank = Bank()
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 150
    done = {}
    if OUT.exists():
        for line in OUT.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["vid"]] = r

    txts = sorted(MEDIA.glob("*.twi.txt"))
    new = 0
    for f in txts:
        vid = f.stem.replace(".twi", "")
        if vid in done:
            continue
        text = f.read_text(encoding="utf-8")
        if len(text) < 40:
            continue
        aka, eng = akan_english_pct(text, bank)
        if aka >= AKAN_FLOOR:
            done[vid] = {"vid": vid, "lang": "Akan", "aka_pct": aka, "ided": False}
            continue
        if eng >= ENGLISH_FLOOR:
            done[vid] = {"vid": vid, "lang": "English", "aka_pct": aka, "ided": False}
            continue
        mp3 = MEDIA / f"{vid}.mp3"  # low Akan + low English -> probably another language; ID the AUDIO
        if not mp3.exists():
            done[vid] = {"vid": vid, "lang": "unknown(no-audio)", "aka_pct": aka, "ided": False}
            continue
        lang = id_audio_language(mp3)
        done[vid] = {"vid": vid, "lang": lang or "unknown", "aka_pct": aka, "ided": True}
        new += 1
        if new >= mx:
            print(f"(hit --max {mx} language-ID calls; re-run to continue)", flush=True)
            break

    OUT.write_text("\n".join(json.dumps(v, ensure_ascii=False) for v in done.values()) + "\n", encoding="utf-8")

    # inventory: what seeds are we accumulating?
    by_lang = Counter(r["lang"] for r in done.values())
    audio_min = defaultdict(float)
    for r in done.values():
        if (MEDIA / f"{r['vid']}.mp3").exists():
            audio_min[r["lang"]] += 3  # ~3min/clip (we pull 180s)
    print(f"\nCAPTURED-LANGUAGE INVENTORY ({len(done)} clips classified, +{new} newly IDed):\n")
    for lang, n in by_lang.most_common():
        seed = "" if lang in ("Akan", "English") else f"  <- future-language seed (~{audio_min[lang]:.0f}min audio banked)"
        print(f"  {n:4d}  {lang}{seed}")
    others = sum(n for l, n in by_lang.items() if l not in ("Akan", "English", "unknown"))
    print(f"\n{others} non-Akan/English clips banked as labeled seeds -> {OUT.name}")
    print("when a language reaches critical mass, re-ASR its clips with a native prompt to bootstrap it.")


if __name__ == "__main__":
    main()
