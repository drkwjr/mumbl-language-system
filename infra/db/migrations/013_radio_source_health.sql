-- Migration 013: Radio source health + shard quality metrics
-- Created: 2025-12-26

ALTER TABLE radio_sources
    ADD COLUMN IF NOT EXISTS health_status VARCHAR(20) DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS health_last_error TEXT,
    ADD COLUMN IF NOT EXISTS health_last_failure_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS health_consecutive_failures INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS health_last_success_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS idx_radio_sources_health_status ON radio_sources(health_status);
CREATE INDEX IF NOT EXISTS idx_radio_sources_health_failure ON radio_sources(health_last_failure_at);

ALTER TABLE radio_shards
    ADD COLUMN IF NOT EXISTS silence_ratio FLOAT;
