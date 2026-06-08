#!/usr/bin/env python3
"""Deep harvest — the expansive spoken-Twi vocabulary engine.

Verify channels multi-sample, then harvest the genuine ones DEEP and corroborate unknown words by
document frequency across the WHOLE run (a real word recurs across clips/channels; ASR noise and proper
nouns appear once). The scale lever is here: more channels x more clips x more minutes. Resumable (audio
+ transcripts cached). Verify-not-trust — corroborated words are STAGED to discovered.jsonl, never
auto-added to the bank.

  set -a; source ../mumbl-server/.env; set +a
  python3 bank/ingest/harvest.py --from-discovery 12 --clips 15 --secs 240
  python3 bank/ingest/harvest.py @SVTVAfrica UCabc... --clips 20 --secs 300 --min-purity 70
"""
import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import media_discover as md  # noqa: E402  audio() + transcribe() + gloss() + USAGE + TWITOK
import verify_channels as vc  # noqa: E402  resolve() + channel_videos() + purity()
from serve import Bank  # noqa: E402
import language_id as lid  # noqa: E402
import morphophon as mp  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "aka"
VERIFIED = DATA / "channels-verified.jsonl"
STAGED = DATA / "discovered.jsonl"


def opts():
    refs, o, a, i = [], {}, sys.argv[1:], 0
    while i < len(a):
        if a[i].startswith("--"):
            has_val = i + 1 < len(a) and not a[i + 1].startswith("--")
            o[a[i]] = a[i + 1] if has_val else True
            i += 2 if has_val else 1
        else:
            refs.append(a[i]); i += 1
    return refs, o


def main():
    bank = Bank()
    refs, o = opts()
    clips = int(o.get("--clips", 15))
    secs = int(o.get("--secs", 240))
    vvids = int(o.get("--verify-vids", 4))
    vsecs = int(o.get("--verify-secs", 50))
    minpur = int(o.get("--min-purity", 70))
    topN = int(o.get("--from-discovery", 0))

    if topN:  # pull the top-purity candidates discover_channels found
        cand = [json.loads(l) for l in (DATA / "channels.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        cand.sort(key=lambda r: -r.get("twi_pct", 0))
        refs += [c["channel_id"] for c in cand[:topN] if c.get("channel_id")]
    refs = list(dict.fromkeys(refs))
    print(f"harvest: {len(refs)} channels · verify {vvids}x{vsecs}s (gate {minpur}%) · then {clips} clips x {secs}s each\n", flush=True)

    def sample(vid, s):
        m = md.audio(vid, s)
        if not m:
            return None
        try:
            return md.transcribe(m)
        except Exception:
            return None

    # ---- stage 1: resolve + multi-sample verify; gate; record the roster ----
    verified, plan = [], []  # plan = (channel_name, [harvest_vids])
    for ref in refs:
        url, name = vc.resolve(ref)
        if not url:
            print(f"  {ref[:30]:30} not found", flush=True)
            continue
        allv = vc.channel_videos(url, clips + vvids)
        vsample, harvest_vids = allv[:vvids], allv[vvids:vvids + clips]  # DISJOINT (md.audio caches by id only)
        with ThreadPoolExecutor(max_workers=vvids) as ex:
            scores = [vc.purity(bank, t) for t in ex.map(lambda v: sample(v, vsecs), vsample) if t is not None]
        if not scores:
            print(f"  {name[:30]:30} no samples", flush=True)
            continue
        mean, lo, hi = round(sum(scores) / len(scores)), min(scores), max(scores)
        ok = mean >= minpur
        print(f"  {name[:30]:30} mean {mean:3}% (range {lo}-{hi}/{len(scores)}) {'-> HARVEST' if ok else '-> skip'}", flush=True)
        if ok:
            verified.append({"ref": ref, "url": url, "name": name, "mean": mean, "min": lo, "max": hi, "n": len(scores)})
            plan.append((name, harvest_vids))

    if not plan:
        print("\nno channels passed the purity gate.")
        return

    # persist the trusted roster (accumulate; dedup by url)
    roster = {r["url"]: r for l in (VERIFIED.read_text(encoding="utf-8").splitlines() if VERIFIED.exists() else [])
              if l.strip() for r in [json.loads(l)]}
    for r in verified:
        roster[r["url"]] = r
    VERIFIED.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in roster.values()) + "\n", encoding="utf-8")

    # ---- stage 2: deep harvest — download + transcribe every clip in parallel ----
    jobs = [(name, vid) for name, vids in plan for vid in vids]
    print(f"\ndeep-harvesting {len(jobs)} clips across {len(plan)} channels ({secs}s each ~ {len(jobs)*secs//60} min of audio)...", flush=True)
    texts = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        for (name, vid), text in zip(jobs, ex.map(lambda j: sample(j[1], secs), jobs)):
            if text:
                texts[(name, vid)] = text

    # ---- stage 3: corroborate unknowns by document frequency across the whole run ----
    df, purity = defaultdict(set), {"Twi": 0, "Eng": 0, "unk": 0}
    for (name, vid), text in texts.items():
        for tok in set(t.strip("'’") for t in md.TWITOK.findall(text.lower())):
            if len(tok) < 2:
                continue
            m = lid.membership(tok, bank)
            purity["Twi" if "aka" in m else "Eng" if "eng" in m else "unk"] += 1
            if not mp.is_known_morph(bank, tok, bank.pkey_index)["known"] and not ("eng" in m and "aka" not in m):
                df[tok].add(vid)
    corroborated = sorted(((w, len(c)) for w, c in df.items() if len(c) >= 2), key=lambda x: -x[1])
    oneoff = sum(1 for c in df.values() if len(c) == 1)

    # ---- stage 4: gloss survivors + stage to discovered.jsonl (append, dedup) ----
    glosses = md.gloss([w for w, _ in corroborated[:60]])
    have = {json.loads(l)["word"] for l in (STAGED.read_text(encoding="utf-8").splitlines() if STAGED.exists() else []) if l.strip()}
    new = 0
    with STAGED.open("a", encoding="utf-8") as f:
        for w, n in corroborated:
            if w in have:
                continue
            g = glosses.get(w)
            f.write(json.dumps({"word": w, "freq": n, "gloss_proposed": g if g and g != "?" else None,
                                "method": "media-corroborated", "verification": "unverified",
                                "use": "staged-for-review"}, ensure_ascii=False) + "\n")
            new += 1

    tot = sum(purity.values()) or 1
    clips_done = len(texts)
    print(f"\n{'='*64}")
    print(f"HARVEST: {clips_done} clips · {clips_done*secs//60} min audio · {len(plan)} channels")
    print(f"PURITY: Twi {100*purity['Twi']//tot}% · English {100*purity['Eng']//tot}% · unknown {100*purity['unk']//tot}%")
    print(f"CORROBORATED unknowns (>=2 clips): {len(corroborated)}  ({oneoff} one-offs dropped as noise)  ·  {new} newly staged")
    for w, n in corroborated[:24]:
        g = glosses.get(w)
        print(f"  {w:16} in {n:2} clips   {'~ ' + g if g and g != '?' else ''}")
    cost = md.USAGE["in"] * 0.30 / 1e6 + md.USAGE["out"] * 2.50 / 1e6
    print(f"\nroster -> {VERIFIED.name} ({len(roster)} channels)   staged -> {STAGED.name}")
    print(f"COST: ~${cost:.4f} (gemini-2.5-flash)")


if __name__ == "__main__":
    main()
