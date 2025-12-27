# Radio Product Views

This project keeps the **radio ingestion pipeline** as the source of truth
(`radio_sources`, `radio_shards`, `radio_segments`). To keep the system coherent
while preserving existing product tables, we expose **read-only product views**
for dashboards and analysis.

## Views

### `radio_segment_product_view`

Join of `radio_segments` → `radio_shards` → `radio_sources` with a stable,
dashboard-friendly shape (station context, audio path, LID details, timestamps).

### `radio_segment_scores_view`

Join of `segment_scores` (where `segment_type = 'radio'`) with station + LID
context so score dashboards don’t need extra joins.

## Why this exists

- The radio pipeline is the **ingestion layer**.
- Existing tables (`audio_segments`, `segment_scores`, `datasets`, etc.) are the
  **product layer** and stay available for downstream use.
- Views provide a single, coherent interface without deleting historical tables.
