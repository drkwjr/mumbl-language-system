# ADR-0002 — LangExtract with grounding for text labeling

Decision:
- Use LangExtract for dialogue detection, topic + register, and code-switch spans.
- Require grounding with source offsets.
- Use chunking with overlap and parallel execution.
- Produce HTML spot-checks per batch.

Consequences:
- Auditable labels, easier error triage, safer at scale.
