# YouTube Fetch — the plan

How we pull spoken-language data off YouTube at scale, what works, what doesn't, and where the levers are.

## The hard constraint

YouTube gates automated access two ways:
1. **Per-IP throttle** — sustained requests from one IP slow to a crawl (~100s/clip after ~200 pulls).
2. **Datacenter bot-wall** — "Sign in to confirm you're not a bot" on datacenter IP ranges (AWS, Vultr…),
   even for a single request on normal content. *This is why the Vultr fleet is parked.*

Both are defeated by the same thing: **residential IPs that rotate.**

## The tiers (cheapest → most expensive per clip)

| Tier | Method | Cost | Yield | When |
|---|---|---|---|---|
| 1 | **Captions** (manual) | ~free, no audio, no ASR | accurate text — but rare for Akan | channels that caption in Akan |
| 2 | **Captions** (auto) | ~free | YouTube's Akan ASR is weak; English auto common | low-trust signal / English fallback |
| 3 | **Audio + Gemini ASR via residential proxy** | ~$0.001 + bandwidth | the workhorse — works everywhere | **the default** |
| — | ~~Datacenter fleet~~ | ~free bandwidth | **0 — bot-walled** | never, for YouTube |

**The doctrine: try captions first where they exist, fall back to proxy audio+ASR for everything else.**
Captions cost no bandwidth and no ASR, so for a caption-having channel they're strictly better — but manual
Akan captions are a minority, so tier 3 (proxy) remains the backbone.

## The backbone: residential proxy (working today)

- `HARVEST_PROXY` (IPRoyal) → fresh exit IP per request → beats both the throttle and the bot-wall.
- Measured: ~25s/clip vs ~100s throttled-direct. `harvest_pool.py` runs it checkpointed in the background.
- **Cost lever = bandwidth** (~1.8 MB/clip). The full 996-channel pull ≈ ~21 GB. Watch the IPRoyal balance.

### Levers to tune the proxy run
- **Fail rate** (~35% currently) is mostly dead/private/live videos + occasional proxy timeouts, not bot-walls.
  Retry-with-backoff is already in; raising it trades time for completeness.
- **Concurrency**: the proxy rotates IPs, so workers can go fairly high — bounded by the IPRoyal plan's
  max concurrent connections, not by YouTube. ~10–15 is the safe band.
- **Disk**: audio accumulates (~21 GB for the full run). Keep it for non-Akan seeds + audio-pairing;
  drop Akan audio after ASR if disk gets tight (`--drop-audio`, see harvest_pool).

## Captions (the cheap complement) — caption_fetch.py

`yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "ak,tw,en.*"` (through the proxy) pulls
caption tracks with **no audio download and no ASR**. For the subset of channels with manual Akan captions
this is free, accurate Twi text — strictly better than ASR. We already flag caption-having channels during
discovery (`discover_channels.has_manual_subs`); prioritize those here.

## Deliberately NOT doing

- **Cookie/account auth** (would let datacenter IPs through): one account's cookies across many workers gets
  flagged and banned fast, and it's ToS-adjacent. Not worth it while the residential proxy works.
- **YouTube Data API** for content: it doesn't serve audio, and caption download needs OAuth + is restricted.
  Fine for richer *discovery* metadata later, not for fetching speech.

## Bottom line

Residential-proxy audio+ASR is the backbone and it works now. Captions are a free win on the channels that
have them. The fleet is the wrong tool for YouTube (datacenter wall) but kept for non-walled sources. Scale
is bounded by proxy bandwidth, not by any technical wall.
