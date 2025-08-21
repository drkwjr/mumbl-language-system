# Runbook — audio-lane

**Input**: YouTube link or file upload  
**Output**: WAV clips + `paired_speech_corpus.csv` (AudioSegment rows)

## Steps

1) Preflight: duration and cost estimate.  
2) Download audio.  
3) ASR + diarization.  
4) Segmentation to 2–12 second clips.  
5) Normalization: mono, 22.05 or 24 kHz, conservative trims.  
6) Alignment: sentence-level default, word-level where feasible.  
7) Emit CSV with confidences and granularity.

## Operational notes

- Record granularity honestly.  
- Budget caps per language per day.  
- Option to delete raw audio after clips are cut.
