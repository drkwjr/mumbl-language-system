# Station Frequency Enrichment

**Date (current): 2025-12-26**

## Goal
Capture station frequency metadata with provenance, confidence, and evidence, and resolve a single “best” frequency for UI/display.

## Data sources and methodology

### 1) Heuristic extraction (fast, low confidence)
- Parse `radio_sources.name` and `tags` for FM patterns (e.g., `100.7`, `100.7 FM`, `104.3 MHz`).
- Store candidate as `source=heuristic` with low confidence (default 0.35).
- Useful for quick wins; not authoritative.

### 2) LLM enrichment (medium confidence)
- Extract frequency from station homepage text (title/snippets).
- Store candidate as `source=llm` with LLM-provided confidence + evidence snippet.
- Useful when frequency is listed on the station site; still not authoritative.

### 3) External datasets (highest confidence when official)
- Primary target: official regulator lists per country.
- Secondary: Wikidata (community-maintained but structured).
- We store candidates with `source=regulator` or `source=wikidata` and resolve based on priority.

## Current research findings (Ghana + Somalia)

### Ghana
- Official regulator site (National Communications Authority): https://nca.org.gh/
  - Search results show “National Frequency Allocation Table” (not a station list): https://nca.org.gh/national-frequency-allocation-table/
- Wikidata property used for frequency: `P2144` (frequency in Hz / radio receive frequency)
  - Property page: https://www.wikidata.org/wiki/Property:P2144
  - Query service: https://query.wikidata.org/
  - Ghana query (example):  
    https://query.wikidata.org/sparql?format=json&query=SELECT+%3Fstation+%3FstationLabel+%3Ffrequency+WHERE+%7B+%3Fstation+wdt%3AP31%2Fwdt%3AP279%2A+wd%3AQ14350%3B+wdt%3AP17+wd%3AQ117%3B+wdt%3AP2144+%3Ffrequency.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D+%7D

### Somalia
- Wikidata query for Somalia frequencies currently returns no results:
  - https://query.wikidata.org/sparql?format=json&query=SELECT+%3Fstation+%3FstationLabel+%3Ffrequency+WHERE+%7B+%3Fstation+wdt%3AP31%2Fwdt%3AP279%2A+wd%3AQ14350%3B+wdt%3AP17+wd%3AQ1045%3B+wdt%3AP2144+%3Ffrequency.+SERVICE+wikibase%3Alabel+%7B+bd%3AserviceParam+wikibase%3Alanguage+%22en%22.+%7D+%7D
- Likely needs manual curation or regulator data if available.

## Resolution policy
We resolve a single “best” frequency per station using priority + confidence:

1. `manual`
2. `regulator`
3. `wikidata`
4. `llm`
5. `heuristic`

When multiple candidates exist at the same priority, we use the highest confidence, then most recent.

## Storage
- `station_frequency_candidates` stores all candidates with provenance + evidence.
- `radio_sources` stores resolved frequency fields:
  - `frequency_mhz`, `frequency_label`, `frequency_source`, `frequency_confidence`, `frequency_updated_at`

## Scripts
- Heuristic backfill: `scripts/enrich_station_frequency_heuristic.py`
- Wikidata enrichment: `scripts/enrich_station_frequency_wikidata.py`
- LLM enrichment: `scripts/enrich_station_frequency_llm.py`

## Next steps
- Identify official regulator station lists for Ghana/Somalia and add as `source=regulator`.
- Add UI badges for confidence/source and allow manual override for high-value stations.
