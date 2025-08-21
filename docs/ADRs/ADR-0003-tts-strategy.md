# ADR-0003 — TTS strategy (per-language first, group for thin data)

Decision:
- Per-language multi-speaker VITS for top languages with data.
- Language-group VITS for low-resource clusters with `language` and `dialect` tokens.
- Optional cloud fallback for the long tail.

Consequences:
- Predictable quality and simpler QA.
- Path to cross-lingual identity via shared speakers or group models.
