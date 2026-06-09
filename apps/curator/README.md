# curator

Curates and scores text and audio segments for quality control.

Input: TextSegment and AudioSegment objects
Output: SegmentScore objects with eligibility flags (learner >= 90, training >= 70)

## Bank-fused validity

`validity` is backed by the **bank** (`bank/serve.py`) via `language_validity.BankValidator`: the
bank's verifier decides whether the text is real target-language content (the judgment heuristics
can't make), so English and noise no longer score as learner-eligible. The conversational labels from
the lanes (dialogue / topic / register) add learner-value **on top of** valid content and are carried
through in `SegmentScore.notes`; the unattested words the bank surfaces there are discovery/promotion
candidates, so curation feeds the bank's growth, not just the reverse. Degrades gracefully to the
metadata heuristic if the bank isn't importable, so the curator still runs standalone.

Scoring dimensions: clarity, alignment, diarization, transcript_accuracy, validity, shape.

TODO:
- Tune dimension weights + thresholds against real labeled data
- Wire the audio path's confidence inputs (alignment/diarization) end to end
