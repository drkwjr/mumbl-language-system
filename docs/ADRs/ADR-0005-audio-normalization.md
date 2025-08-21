# ADR-0005 — Audio normalization policy

Decision:
- Mono, 22.05 or 24 kHz, conservative silence trims, no heavy denoise.
- Record normalization parameters with artifacts.

Consequences:
- Stable training inputs and reproducible comparisons.
