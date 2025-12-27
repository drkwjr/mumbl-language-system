-- Migration 004: Pipeline Events
-- Created: 2025-01-XX
-- Purpose: Store raw, human-readable pipeline events for visibility

CREATE TABLE IF NOT EXISTS pipeline_events (
    id SERIAL PRIMARY KEY,

    stage VARCHAR(30) NOT NULL,          -- capture, prefilter, lid, segments, asr, verification, discovery
    event_type VARCHAR(50) NOT NULL,     -- machine-friendly event name
    status VARCHAR(20),                  -- success, error, warn

    source_id INT,                       -- radio_sources.id if applicable
    shard_id INT,                        -- radio_shards.id if applicable
    segment_id INT,                      -- radio_segments.id or audio_segments.id if applicable

    count INT,                           -- number of items affected (segments, verifications, etc.)
    duration_seconds FLOAT,              -- elapsed time for event

    message TEXT,                        -- human-readable summary
    payload JSONB,                       -- raw metadata

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pipeline_events_stage ON pipeline_events(stage);
CREATE INDEX idx_pipeline_events_source_id ON pipeline_events(source_id);
CREATE INDEX idx_pipeline_events_created_at ON pipeline_events(created_at DESC);
CREATE INDEX idx_pipeline_events_event_type ON pipeline_events(event_type);

COMMENT ON TABLE pipeline_events IS 'Raw pipeline events for operational visibility';
COMMENT ON COLUMN pipeline_events.payload IS 'Raw event metadata (JSON)';
