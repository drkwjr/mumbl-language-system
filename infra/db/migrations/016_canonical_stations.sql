-- Migration 016: Canonical stations + source links
-- Created: 2025-12-26
-- Purpose: De-duplicate stations across discovery sources

CREATE TABLE IF NOT EXISTS canonical_stations (
    id SERIAL PRIMARY KEY,
    canonical_key TEXT NOT NULL UNIQUE,
    normalized_name TEXT,
    homepage_domain TEXT,
    stream_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS station_source_links (
    id SERIAL PRIMARY KEY,
    canonical_id INT NOT NULL REFERENCES canonical_stations(id) ON DELETE CASCADE,
    source_id INT NOT NULL REFERENCES discovery_sources(id) ON DELETE CASCADE,
    station_provenance_id INT NOT NULL REFERENCES station_provenance(id) ON DELETE CASCADE,
    country VARCHAR(3),
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_provenance_id)
);

CREATE INDEX IF NOT EXISTS idx_canonical_stations_stream_url
    ON canonical_stations(stream_url);
CREATE INDEX IF NOT EXISTS idx_canonical_stations_homepage_domain
    ON canonical_stations(homepage_domain);
CREATE INDEX IF NOT EXISTS idx_station_source_links_country
    ON station_source_links(country);

COMMENT ON TABLE canonical_stations IS 'Canonical station identities to dedupe across sources';
COMMENT ON TABLE station_source_links IS 'Mapping from provenance to canonical stations';
