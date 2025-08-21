# Metrics and Language Completeness

## Language Completeness (0–100)

Weighted composite of:
- Curated minutes ≥90
- Training minutes ≥70
- Phoneme coverage
- Minimal pair coverage
- Dialect balance divergence (lower is better)
- Topic/register balance divergence (lower is better)
- Voice inventory count and quality
- Runtime KPIs (ASR WER, TTS MOS-lite, stability, p95 latency)

## Definitions

- **Curated minutes ≥90** = sum of clip duration where `SegmentScore.total ≥ 90` and content passes policy.
- **Training minutes ≥70** analogous with `70 ≤ total < 90`.
- **Phoneme coverage** = unique phonemes observed in ≥90 clips / phoneme_inventory.
- **Minimal pair coverage** = fraction of target pair list observed at least once.
- **Dialect balance** = Jensen–Shannon divergence vs target distribution (or Gini if no target).
- **Topic/register balance** = divergence vs target plan.
- **Voice inventory** = voices with ≥30 minutes curated and MOS-lite ≥ threshold.
- **Runtime KPIs** gathered from eval harness and runtime logs.

## Status colors

- Green: meets or exceeds target.
- Yellow: within 15 percent of target.
- Red: below.
