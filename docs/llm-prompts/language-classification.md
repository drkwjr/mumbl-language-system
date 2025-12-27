# Language Classification Prompt Strategy

**Date verified:** 2025-12-26  
**Goal:** Produce consistent, high‑quality language labels for audio segments and stations.

## Inputs

We pass a structured bundle to the model:

- Audio LID distribution (top‑k with probabilities).
- Optional transcript (if available).
- Station metadata (name, tags, country, stream URL).
- Historical language mix (if known).
- Target taxonomy (ISO‑639‑3 + dialect list for the country).

## Output schema

The model must answer in JSON:

```json
{
  "primary_language": "aka",
  "dialect": "asante",
  "language_family": "niger-congo",
  "confidence": 0.84,
  "rationale": "short, grounded reason",
  "signals": {
    "audio_lid": ["aka", "twi"],
    "text_lid": ["aka"],
    "metadata": ["ghana", "twi", "akan"]
  },
  "uncertainty_flags": ["low_transcript_confidence"]
}
```

## Base prompt (system)

```
You are a language classification engine. You must follow the taxonomy exactly.
Return JSON only. If evidence is insufficient, set primary_language="unknown"
and include uncertainty_flags.
```

## User prompt (template)

```
Classify the language and dialect for this segment using the taxonomy below.

TAXONOMY:
{taxonomy_json}

SIGNALS:
- audio_lid_topk: {audio_lid_topk}
- transcript: {transcript_excerpt}
- station_metadata: {station_metadata}
- station_language_history: {station_history}

RULES:
1) Use ISO‑639‑3 codes for primary_language.
2) Use dialect only if the taxonomy includes it.
3) If audio and text disagree, keep confidence <= 0.6 and add an uncertainty flag.
4) If evidence is missing, return "unknown" with confidence <= 0.4.
5) Do NOT invent languages not in the taxonomy list.
```

## Scoring guidance

- **0.8–1.0**: consistent signals across audio + text + metadata.
- **0.6–0.79**: strong audio LID, weak metadata or no transcript.
- **0.4–0.59**: mixed or conflicting signals.
- **<0.4**: insufficient evidence.

## Dialect resolution

If multiple dialects are plausible (e.g., Akan variants), return:

```json
{
  "primary_language": "aka",
  "dialect": "unknown",
  "uncertainty_flags": ["dialect_ambiguous"]
}
```

## Implementation notes

- The taxonomy is authoritative. If a language is not in the taxonomy, do not guess.
- This prompt is used **everywhere** LLM verification runs (radio + text + audio lanes).
- Few-shot examples are embedded in the classifier prompt to enforce schema adherence.
- The classifier uses relaxed parsing + a retry to recover from non-strict JSON responses.
