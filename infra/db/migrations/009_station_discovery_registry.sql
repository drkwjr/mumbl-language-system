-- Migration 009: Station discovery registry
-- Created: 2025-12-27
-- Purpose: Track multi-source discovery runs and provenance

CREATE TABLE IF NOT EXISTS discovery_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    source_type VARCHAR(30) NOT NULL, -- directory, wiki, regulator, crawler
    base_url TEXT,
    countries JSONB DEFAULT '[]',
    notes TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS discovery_runs (
    id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES discovery_sources(id) ON DELETE CASCADE,
    country VARCHAR(3),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'running', -- running, completed, failed
    stats JSONB DEFAULT '{}',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS station_provenance (
    id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES discovery_sources(id) ON DELETE CASCADE,
    station_uuid TEXT,
    stream_url TEXT,
    homepage TEXT,
    station_name TEXT,
    country VARCHAR(3),
    tags JSONB DEFAULT '[]',
    evidence_url TEXT,
    confidence FLOAT,
    discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    raw_payload JSONB DEFAULT '{}',
    UNIQUE(source_id, station_uuid),
    UNIQUE(source_id, stream_url)
);

CREATE INDEX IF NOT EXISTS idx_discovery_sources_active ON discovery_sources(active);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_source_id ON discovery_runs(source_id);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_status ON discovery_runs(status);
CREATE INDEX IF NOT EXISTS idx_station_provenance_country ON station_provenance(country);
CREATE INDEX IF NOT EXISTS idx_station_provenance_source_id ON station_provenance(source_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'discovery_sources_updated_at'
    ) THEN
        CREATE TRIGGER discovery_sources_updated_at
            BEFORE UPDATE ON discovery_sources
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at();
    END IF;
END $$;

COMMENT ON TABLE discovery_sources IS 'Registry of station discovery sources';
COMMENT ON TABLE discovery_runs IS 'Execution history for discovery sources';
COMMENT ON TABLE station_provenance IS 'Source provenance records for discovered stations';
