#!/usr/bin/env python3
"""Vultr fleet harvester — distribute a pull across N cheap boxes, each its own IP.

⚠️ PARKED FOR YOUTUBE (2026-06): datacenter IPs are bot-walled. Validated empirically — yt-dlp on a Vultr
box downloads a hyper-cached video (Rick Astley) fine, but a normal Ghanaian-channel video returns
"Sign in to confirm you're not a bot." YouTube challenges datacenter IP ranges; only residential IPs pass.
So for YouTube the answer is the IPRoyal residential proxy (harvest_pool.py + HARVEST_PROXY), NOT this
fleet. This code is correct + safe (provision→run→collect→guaranteed-teardown all validated) and REUSABLE
for any source that is NOT datacenter-IP-walled — kept for that. Do not point it at YouTube expecting
results. Per-box concurrency was a red herring; the wall is the IP class, not the request rate.

This provisions N tiny Vultr boxes, shards the channel pool across them, runs box_worker.py on each over
SSH (download + ASR locally), pulls back the KB-sized transcripts, and DESTROYS every box.

SAFETY (the whole design goal — "don't break anything"):
  - Every box is tagged `mumbl-harvest`. `down` destroys ALL tagged boxes — one command nukes everything.
  - `harvest` wraps the run in try/finally so teardown ALWAYS happens, even on crash/Ctrl-C.
  - The Gemini key is passed over SSH per-run (env), never written to a box image or committed.
  - Idempotent destroy; `status` shows exactly what's live and the running cost.

Creds via env: VULTR_API_KEY, VULTR_SSH_KEY_ID, GEMINI_API_KEY (set from Bitwarden at call time).

  python3 fleet_harvest.py status                 # what's live + cost
  python3 fleet_harvest.py harvest 3              # provision 3, harvest, collect, destroy (TEST small first!)
  python3 fleet_harvest.py harvest 40             # the real run
  python3 fleet_harvest.py down                   # PANIC BUTTON: destroy everything tagged
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ING = Path(__file__).resolve().parent
DATA = ING.parents[0] / "data" / "aka"
MEDIA = ING.parents[0] / "corpus" / "aka-asante" / "_media"
POOL = DATA / "channels.jsonl"

API = "https://api.vultr.com/v2"
TAG = "mumbl-harvest"
PLAN = os.environ.get("FLEET_PLAN", "vc2-1c-1gb")   # $5/mo ≈ $0.007/hr; 1GB is safe for yt-dlp+ffmpeg
REGION = os.environ.get("FLEET_REGION", "ewr")
SSH = ["ssh", "-i", os.path.expanduser("~/.ssh/id_rsa"), "-o", "StrictHostKeyChecking=no",
       "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10", "-o", "LogLevel=ERROR"]
SCP = ["scp", "-i", os.path.expanduser("~/.ssh/id_rsa"), "-o", "StrictHostKeyChecking=no",
       "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR"]

CLOUD_INIT = """#!/bin/bash
exec > /var/log/mh-init.log 2>&1
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 ffmpeg curl
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp
chmod +x /usr/local/bin/yt-dlp
touch /root/ready
"""


def api(method, path, body=None):
    key = os.environ["VULTR_API_KEY"]
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:200]}


def list_boxes():
    out = api("GET", "/instances?per_page=200")
    return [i for i in out.get("instances", []) if i.get("tag") == TAG]


def os_id():
    for o in api("GET", "/os?per_page=500").get("os", []):
        if "Debian 12" in o.get("name", ""):
            return o["id"]
    return 2136  # Debian 12 x64 fallback


def provision(n):
    import base64
    ud = base64.b64encode(CLOUD_INIT.encode()).decode()
    oid = os_id()
    ids = []
    for i in range(n):
        r = api("POST", "/instances", {
            "region": REGION, "plan": PLAN, "os_id": oid, "label": f"mh-{i}", "tag": TAG,
            "sshkey_id": [os.environ["VULTR_SSH_KEY_ID"]], "user_data": ud, "backups": "disabled"})
        if r.get("instance"):
            ids.append(r["instance"]["id"])
        else:
            print(f"  provision {i} failed: {r.get('_error')} {r.get('_body','')}", flush=True)
    print(f"requested {len(ids)}/{n} boxes ({PLAN} @ {REGION})", flush=True)
    return ids


def wait_ready(timeout=420):
    """Poll until boxes are running with an IP and cloud-init's /root/ready sentinel exists."""
    t0 = time.time()
    ready = {}
    while time.time() - t0 < timeout:
        boxes = list_boxes()
        live = [b for b in boxes if b.get("main_ip") and b["main_ip"] != "0.0.0.0" and b.get("power_status") == "running"]
        for b in live:
            ip = b["main_ip"]
            if ip in ready:
                continue
            chk = subprocess.run(SSH + [f"root@{ip}", "test -f /root/ready && echo ok"],
                                 capture_output=True, text=True)
            if chk.stdout.strip() == "ok":
                ready[ip] = b["id"]
        print(f"  ready {len(ready)}/{len(boxes)} ({int(time.time()-t0)}s)", flush=True)
        if boxes and len(ready) == len(boxes):
            return ready
        time.sleep(15)
    return ready  # partial — proceed with whoever's ready


def shards(n, cap=0):
    cids = []
    for line in POOL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            c = json.loads(line).get("channel_id") or json.loads(line).get("url")
            if c:
                cids.append(c)
    if cap:
        cids = cids[:cap]  # FLEET_MAX_CHANNELS — for small validation runs
    return [cids[i::n] for i in range(n)]  # round-robin split


def run_box(ip, shard, per, secs, workers):
    Path("/tmp/mh").mkdir(exist_ok=True)
    sf = Path(f"/tmp/mh/shard_{ip}.txt")
    sf.write_text("\n".join(shard), encoding="utf-8")
    subprocess.run(SCP + [str(ING / "box_worker.py"), f"root@{ip}:/root/box_worker.py"], capture_output=True)
    subprocess.run(SCP + [str(sf), f"root@{ip}:/root/shard.txt"], capture_output=True)
    cmd = (f"cd /root && GEMINI_API_KEY={os.environ['GEMINI_API_KEY']} "
           f"PER_CHANNEL={per} CLIP_SECS={secs} WORKERS={workers} python3 box_worker.py")
    r = subprocess.run(SSH + [f"root@{ip}", cmd], capture_output=True, text=True, timeout=7200)
    return ip, (r.stdout or "").strip().splitlines()[-1:] or ["(no output)"]


def collect(ip):
    dest = MEDIA
    dest.mkdir(parents=True, exist_ok=True)
    before = len(list(dest.glob("*.twi.txt")))
    subprocess.run(SCP + ["-r", f"root@{ip}:/root/out/.", str(dest)], capture_output=True)
    return len(list(dest.glob("*.twi.txt"))) - before


def destroy_all():
    boxes = list_boxes()
    for b in boxes:
        api("DELETE", f"/instances/{b['id']}")
    # verify
    time.sleep(3)
    left = list_boxes()
    print(f"destroyed {len(boxes)} boxes · {len(left)} still listed"
          + ("  ⚠️ re-run `down`!" if left else "  ✓ clean"), flush=True)
    return len(left)


def status():
    boxes = list_boxes()
    if not boxes:
        print("no fleet boxes live ✓ ($0 running)")
        return
    cost = len(boxes) * 0.007
    print(f"{len(boxes)} boxes live (~${cost:.3f}/hr):")
    for b in boxes:
        print(f"  {b.get('label'):8} {b.get('main_ip','-'):16} {b.get('power_status')}/{b.get('server_status')}")


def harvest(n, per=8, secs=180, workers=None):
    # LOW concurrency per box — YouTube bot-walls multiple concurrent pulls from one datacenter IP. The
    # parallelism comes from the IP COUNT (many boxes), not workers-per-box. 2 is the safe default.
    workers = workers or int(os.environ.get("FLEET_WORKERS", "2"))
    print(f"provisioning {n} boxes...", flush=True)
    provision(n)
    try:
        ready = wait_ready()
        if not ready:
            print("no boxes became ready — aborting", flush=True)
            return
        ips = list(ready)
        sh = shards(len(ips), int(os.environ.get("FLEET_MAX_CHANNELS", "0")))
        print(f"\n{len(ips)} boxes ready · sharding {sum(len(s) for s in sh)} channels · harvesting...\n", flush=True)
        with ThreadPoolExecutor(max_workers=len(ips)) as ex:
            futs = {ex.submit(run_box, ip, sh[i], per, secs, workers): ip for i, ip in enumerate(ips)}
            for fut in as_completed(futs):
                ip, tail = fut.result()
                print(f"  {ip}: {tail[0] if tail else ''}", flush=True)
        print("\ncollecting transcripts...", flush=True)
        total = 0
        with ThreadPoolExecutor(max_workers=len(ips)) as ex:
            for got in ex.map(collect, ips):
                total += got
        print(f"collected {total} new transcripts -> {MEDIA}", flush=True)
    finally:
        print("\nTEARDOWN (always runs)...", flush=True)
        destroy_all()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        status()
    elif cmd == "down":
        destroy_all()
    elif cmd == "harvest":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
        harvest(n)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
