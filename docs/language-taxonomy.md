# Language Taxonomy

**Date verified:** 2025-12-26

This taxonomy is the canonical language reference for labeling and model training.

## Tables

- `language_families`
- `language_taxonomy` (ISO‑639‑3 + optional ISO‑639‑1)
- `language_dialects`
- `language_label_map` (observed LID labels → canonical ISO‑639‑3)

## Seed data

Initial seed lives in:

```
data/language_taxonomy/ghana_somalia.json
```

Load it with:

```bash
python scripts/load_language_taxonomy.py
```

## Usage

The taxonomy is used by:

- LLM language classification (always-on verification)
- Station discovery enrichment
- Model training dataset labeling
- Label mapping to normalize raw LID outputs into canonical codes

## Label mapping workflow

1) Review unmapped labels in the admin.
2) Map to ISO-639-3 codes (writes to `language_label_map`).
3) Optional: seed label mappings from ISO prefix matches:

```bash
python scripts/language/seed_language_label_map.py
```

4) Run backfill to update existing segments:

```bash
python scripts/language/backfill_language_mapping.py
```
