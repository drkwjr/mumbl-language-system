#!/usr/bin/env python3
"""Background pool harvester — fill the spoken-Twi transcript cache at scale, safely, resumably.

The expensive half of the pipeline (download + ASR over hundreds of channels) split out so it can run
for hours in the background and survive interruption. Reads the channel pool (channels.jsonl), lists each
channel's videos, and downloads+transcribes fresh clips through a worker pool. Every clip is cached by
video id and recorded in a checkpoint, so a re-run resumes exactly where it stopped — nothing is pulled
twice. Downloads route through HARVEST_PROXY (IPRoyal rotating residential) when set, which is what lets
the workers actually parallelize past YouTube's per-IP throttle.

This does NOT aggregate/stage — it only grows the transcript corpus. After a run, feed the corpus to the
miners: media_discover (corroborated unknowns) and construction_miner (syntax) re-read the _media cache.

ScriptOps: idempotent (cache+checkpoint), resumable, deduped by video id, transient failures retried with
a cap. Bounded by --minutes (wall budget) and --max-clips so a background run is always finite.

  set -a; source ../mumbl-server/.env; set +a
  HARVEST_PROXY="http://user:pass@geo.iproyal.com:12321" \
  python3 bank/ingest/harvest_pool.py --per-channel 12 --secs 180 --workers 16 --minutes 120
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ING = Path(__file__).resolve().parent
sys.path.insert(0, str(ING))
import media_discover as md  # proxy-aware audio() + transcribe()  # noqa: E402
import verify_channels as vc  # channel_videos()  # noqa: E402

DATA = ING.parents[0] / "data" / "aka"
POOL = DATA / "channels.jsonl"
VERIFIED = DATA / "channels-verified.jsonl"
STATE = DATA / "harvest_state.json"
MAX_RETRY = 2


def arg(flag, default, cast=int):
    return cast(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default


def load_state():
    if STATE.exists():
        s = json.loads(STATE.read_text(encoding="utf-8"))
        return set(s.get("done", [])), s.get("failed", {})
    return set(), {}


def save_state(done, failed):
    STATE.write_text(json.dumps({"done": sorted(done), "failed": failed}, ensure_ascii=False), encoding="utf-8")


def channels():
    """Verified channels first (known-good), then the rest of the discovered pool."""
    seen, refs = set(), []
    for f in (VERIFIED, POOL):
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            cid = r.get("channel_id") or r.get("url")
            if cid and cid not in seen:
                seen.add(cid)
                refs.append(cid)
    return refs


def main():
    md.CACHE.mkdir(parents=True, exist_ok=True)
    per = arg("--per-channel", 12)
    secs = arg("--secs", 180)
    workers = arg("--workers", int(__import__("os").environ.get("HARVEST_WORKERS", "12")))
    budget_min = arg("--minutes", 0)
    max_clips = arg("--max-clips", 0)
    proxied = bool(__import__("os").environ.get("HARVEST_PROXY", "").strip())

    done, failed = load_state()
    refs = channels()
    t0 = time.time()
    print(f"pool: {len(refs)} channels · {per} clips/ch × {secs}s · {workers} workers · "
          f"proxy {'ON' if proxied else 'OFF (direct — will throttle)'} · "
          f"budget {budget_min or '∞'}min · already done {len(done)}\n", flush=True)

    # build the fresh job list (skip cached transcripts + checkpointed dones + exhausted failures)
    jobs = []
    for i, ref in enumerate(refs, 1):
        if budget_min and (time.time() - t0) / 60 > budget_min:
            print("  (budget reached during listing — harvesting what we have)", flush=True)
            break
        url, _ = vc.resolve(ref)
        if not url:
            continue
        for vid in vc.channel_videos(url, per):
            if vid in done or failed.get(vid, 0) > MAX_RETRY:
                continue
            if (md.CACHE / f"{vid}.twi.txt").exists():
                done.add(vid)
                continue
            jobs.append(vid)
        if i % 25 == 0:
            print(f"  listed {i}/{len(refs)} channels · {len(jobs)} fresh clips queued", flush=True)
        if max_clips and len(jobs) >= max_clips:
            break
    if max_clips:
        jobs = jobs[:max_clips]
    print(f"\nharvesting {len(jobs)} fresh clips...\n", flush=True)

    def pull(vid):
        try:
            m = md.audio(vid, secs)
            if not m:
                return vid, None
            return vid, md.transcribe(m)
        except Exception:
            return vid, None

    ok = fail = words = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(pull, v): v for v in jobs}
        for n, fut in enumerate(as_completed(futures), 1):
            vid, text = fut.result()
            if text:
                ok += 1
                words += len(text.split())
                done.add(vid)
                failed.pop(vid, None)
            else:
                fail += 1
                failed[vid] = failed.get(vid, 0) + 1
            if n % 20 == 0:
                save_state(done, failed)
                el = (time.time() - t0) / 60
                print(f"  [{n}/{len(jobs)}] ok {ok} · fail {fail} · ~{words:,} words · {el:.0f}min "
                      f"· {ok * secs / 60:.0f}min audio", flush=True)
            if budget_min and (time.time() - t0) / 60 > budget_min:
                print("  (wall budget reached — stopping; re-run to resume)", flush=True)
                for leftover in futures:
                    leftover.cancel()
                break

    save_state(done, failed)
    el = (time.time() - t0) / 60
    print(f"\nHARVESTED {ok} clips · ~{ok * secs / 60:.0f}min audio · ~{words:,} words · "
          f"{fail} fails · {el:.0f}min wall · corpus cache {len(list(md.CACHE.glob('*.twi.txt')))} transcripts")
    print("next: re-mine -> python3 bank/ingest/construction_miner.py ; python3 bank/export_for_app.py")


if __name__ == "__main__":
    main()
