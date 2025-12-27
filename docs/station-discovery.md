# Station Discovery Strategy

**Date verified:** 2025-12-26

## Current sources

- **Radio Browser** (primary directory): https://www.radio-browser.info/
- **Wikipedia Ghana list** (multi-station index): https://en.wikipedia.org/wiki/Lists_of_radio_stations_in_Ghana
- **Wikipedia Somalia media** (contains radio lists): https://en.wikipedia.org/wiki/Mass_media_in_Somalia

## Open-source ecosystem (airwave listeners)

These require **hardware SDR receivers** (e.g., RTL-SDR dongles). They are useful
if we later choose to listen directly to the airwaves:

- **Gqrx** (SDR receiver GUI): https://github.com/gqrx-sdr/gqrx
- **gqrx-scanner** (scan and log frequencies): https://github.com/neural75/gqrx-scanner
- **LocalRadio** (RTL-SDR radio scanner): https://github.com/dsward2/LocalRadio
- **fm-dx-webserver** (FM DX receiver front-end): https://github.com/NoobishSVK/fm-dx-webserver
- **RTL-SDR overview** (hardware context): https://www.rtl-sdr.com/about-rtl-sdr/

## Discovery pipeline (multi-source, idempotent)

**Goals**
1) Avoid undercounting stations per country.
2) Track provenance and confidence per station.
3) Keep discovery idempotent and resumable.

**Stages**
1) **Source ingestion** (Radio Browser + Wikipedia + directories).
2) **Normalization** (stream URL, homepage domain, station name, tags).
3) **Deduplication** (UUID, stream URL, homepage domain, fuzzy name).
4) **Health check** (short capture, speech ratio, LID quick pass).
5) **Provenance logging** (source + timestamp + evidence URL).

## Concurrency + progress logging

- `scripts/discovery/run_discovery.py` runs each source+country pair concurrently.
- Configure `DISCOVERY_MAX_WORKERS` to control parallelism.
- Each run logs a structured progress line with run id, source, country, stats, and elapsed seconds.
- Use `python scripts/discovery/run_discovery.py --report-only` to refresh coverage metrics without running discovery.

## LLM wiki parser

Wikipedia pages are parsed with a universal LLM parser:
- Extracts `name`, `stream_url`, `homepage`, `languages`, `tags`, `confidence`.
- Falls back to list-item parsing if LLM is unavailable.
- Prompt spec: `docs/llm-prompts/wiki-station-extraction.md`.
- Enforces minimum coverage (>= 20% of candidates) before accepting LLM output.

Environment:
- `WIKI_PARSER_MODEL` (default: `gpt-4o-mini`)

## Admin visibility

- `GET /api/discovery/runs` (recent run status + stats)
- `GET /api/discovery/summary` (aggregate stats per source)
- `GET /api/discovery/coverage` (latest coverage report per country/source)

Coverage artifacts:
- Stored in `discovery_coverage_reports` for admin display.
- Written to `logs/discovery_coverage_latest.json` after each run.

## Discovery registry schema

- `discovery_sources`: source registry (name, type, base_url, countries).
- `discovery_runs`: run history + status.
- `station_provenance`: per-station records with evidence and raw payload.
- `canonical_stations`: deduped station identities across sources.
- `station_source_links`: provenance → canonical station links.

These tables allow resumable, idempotent discovery and make it easy to avoid
re-scraping the same sources repeatedly.

## De-duplication (cross-source)

Stations are de-duplicated into `canonical_stations` using:
- Normalized stream URL (preferred).
- Fallback: homepage domain + normalized station name.

Coverage reporting now includes both:
- **Source rows** (raw provenance per directory), and
- **Canonical station counts** (de-duplicated totals).

Backfill:
- `python scripts/discovery/backfill_canonical_stations.py` to link existing provenance.

## Scheduling priorities

Capture ordering prefers:
- Stations with no recent successful capture.
- Healthy stations before degraded/down.
- Fewer consecutive failures.
- Higher speech ratio and stronger LID confidence (hourly aggregates).

Language targets (if configured) filter capture to matching `lang_hint` values.

Deduplication during capture:
- If multiple sources resolve to the same canonical key, only the highest attention score is captured.

## LLM/agent placement

Use LLMs to:
- Normalize station names and tags.
- Extract stream URLs from directory pages.
- Classify station format (talk/music/mixed).
- Propose language candidates when LID is low confidence.

Agent searches (future):
- Run parallel web research agents to discover additional directories and country indexes.

## Constraints (no paid APIs)

- Use free/public sources first.
- Respect robots.txt and source terms.
- Prefer sources with multi-country coverage to avoid one-off integrations.

## Expansion plan

1) Add additional country directories as needed.
2) Track which sources are broad (multi-country) vs country-specific.
3) Prioritize high-coverage sources for new countries before one-off lists.
