-- Migration 008: Station daypart aggregates
-- Created: 2025-12-27
-- Purpose: Track listening hours by station and daypart

CREATE TABLE IF NOT EXISTS radio_station_daypart (
    id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES radio_sources(id) ON DELETE CASCADE,
    day DATE NOT NULL,
    daypart VARCHAR(20) NOT NULL,           -- morning, afternoon, evening, night
    timezone_used VARCHAR(50),              -- IANA timezone or 'local'
    total_seconds FLOAT DEFAULT 0,
    speech_seconds FLOAT DEFAULT 0,
    shard_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_id, day, daypart)
);

CREATE INDEX IF NOT EXISTS idx_radio_station_daypart_source_id
    ON radio_station_daypart(source_id);
CREATE INDEX IF NOT EXISTS idx_radio_station_daypart_day
    ON radio_station_daypart(day DESC);
CREATE INDEX IF NOT EXISTS idx_radio_station_daypart_daypart
    ON radio_station_daypart(daypart);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'radio_station_daypart_updated_at'
    ) THEN
        CREATE TRIGGER radio_station_daypart_updated_at
            BEFORE UPDATE ON radio_station_daypart
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at();
    END IF;
END $$;

COMMENT ON TABLE radio_station_daypart IS 'Listening aggregates by station, day, and daypart';
