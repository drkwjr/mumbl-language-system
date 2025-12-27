-- Migration 005: Station Frequency Candidates
-- Created: 2025-01-XX
-- Purpose: Store frequency candidates + resolved frequency on radio_sources

CREATE TABLE IF NOT EXISTS station_frequency_candidates (
    id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES radio_sources(id) ON DELETE CASCADE,
    frequency_mhz FLOAT,                 -- numeric frequency when parsed
    frequency_label TEXT,                -- original label (e.g., "100.7 FM")
    source VARCHAR(30) NOT NULL,         -- heuristic, llm, wikidata, regulator, manual
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    evidence_url TEXT,
    evidence_text TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_station_frequency_source_id ON station_frequency_candidates(source_id);
CREATE INDEX idx_station_frequency_source ON station_frequency_candidates(source);
CREATE INDEX idx_station_frequency_created_at ON station_frequency_candidates(created_at DESC);

ALTER TABLE radio_sources
    ADD COLUMN IF NOT EXISTS frequency_mhz FLOAT,
    ADD COLUMN IF NOT EXISTS frequency_label TEXT,
    ADD COLUMN IF NOT EXISTS frequency_source VARCHAR(30),
    ADD COLUMN IF NOT EXISTS frequency_confidence FLOAT,
    ADD COLUMN IF NOT EXISTS frequency_updated_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_radio_sources_frequency_mhz ON radio_sources(frequency_mhz);

COMMENT ON TABLE station_frequency_candidates IS 'Frequency candidates per station with provenance';
COMMENT ON COLUMN station_frequency_candidates.source IS 'Candidate source: heuristic, llm, wikidata, regulator, manual';
