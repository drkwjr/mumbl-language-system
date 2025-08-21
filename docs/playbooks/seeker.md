# Playbook — seeker jobs

**Goal**: Fill gaps shown by metrics.

## Text seeker panel

Fields:
- Language, Dialect
- Target topics and registers
- Keywords
- Source filters: wiki, news, subtitles, e-books, blogs
- Time window
- Max segments
- Dedupe tolerance
- Budget and concurrency caps

Outputs:
- Projected labeled segments and topic/register deltas
- Cost estimate (compute and storage)

## Audio seeker panel

Fields:
- Language, Dialect
- Source types: YouTube, podcasts, radio, lectures, interviews
- Link paste or channel ID
- Clip duration bounds
- Preferred speakers (optional)
- License filter
- Processing plan: ASR only, ASR+diarization, +alignment
- Storage plan: keep raw, keep clips only
- Budget caps

Outputs:
- Projected curated minutes ≥90 and phoneme coverage deltas
- Dialect balance delta
- Cost estimate
