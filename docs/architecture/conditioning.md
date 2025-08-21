# Conditioning, G2P, and Profiles

## Tokens and knobs

- `language`: e.g., `es`, `ak`
- `dialect`: e.g., `es-MX`, `ak-GH`
- `style`: e.g., `calm`, `teaching`, `storytelling`
- `emotion`: e.g., `neutral`, `encouraging`
- Prosody: `speaking_rate`, `pitch_bias`, `pause_bias`, `filler_bias`

## G2P

- Rules map graphemes to phonemes. Overrides fix exceptions.
- Runtime order: override → rule → fallback_chain.

## LanguageProfile fields (dialect level)

- `language`, `dialect`, `script`
- `phoneme_inventory`
- `g2p_rules` and `g2p_overrides`
- `lexicon_refs`
- `register_defaults`
- `style_tokens`, `emotion_tokens`
- `tts_defaults`
- `fallback_chain`
- `curation_targets`
- `tts_strategy` (`standalone`, `grouped`, `cloud_fallback`)

Example profile is in `docs/examples/ak-GH.language-profile.json`.
