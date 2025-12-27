-- Migration 015: Language label mapping and canonical fields
-- Created: 2025-12-26
-- Purpose: Normalize observed LID labels into canonical ISO-639-3 codes

CREATE TABLE IF NOT EXISTS language_label_map (
    id SERIAL PRIMARY KEY,
    observed_label TEXT NOT NULL UNIQUE,
    canonical_iso639_3 VARCHAR(3) REFERENCES language_taxonomy(iso639_3),
    source TEXT,
    confidence FLOAT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE radio_segments
    ADD COLUMN IF NOT EXISTS primary_lang_raw TEXT,
    ADD COLUMN IF NOT EXISTS primary_lang_iso639_3 VARCHAR(3)
        REFERENCES language_taxonomy(iso639_3);

UPDATE radio_segments
SET primary_lang_raw = primary_lang
WHERE primary_lang_raw IS NULL
  AND primary_lang IS NOT NULL;

UPDATE radio_segments
SET primary_lang_iso639_3 = primary_lang
WHERE primary_lang_iso639_3 IS NULL
  AND primary_lang ~ '^[a-z]{3}$';

CREATE INDEX IF NOT EXISTS idx_radio_segments_primary_lang_iso639_3
    ON radio_segments(primary_lang_iso639_3);

COMMENT ON TABLE language_label_map IS 'Maps observed LID labels to canonical ISO-639-3 codes';
