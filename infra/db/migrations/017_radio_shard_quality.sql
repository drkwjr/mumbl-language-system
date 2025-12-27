-- Migration 017: Radio shard quality fields
-- Created: 2025-12-27
-- Purpose: Store actual duration and duration ratio for quality rollups

ALTER TABLE radio_shards
    ADD COLUMN IF NOT EXISTS actual_duration FLOAT,
    ADD COLUMN IF NOT EXISTS duration_ratio FLOAT;

COMMENT ON COLUMN radio_shards.actual_duration IS 'Actual duration from ffprobe (seconds)';
COMMENT ON COLUMN radio_shards.duration_ratio IS 'actual_duration / duration (capture target)';
