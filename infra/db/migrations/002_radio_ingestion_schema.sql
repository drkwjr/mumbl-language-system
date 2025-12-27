-- Migration 002: Radio Ingestion Schema
-- Created: 2025-01-XX
-- Purpose: Tables for radio station discovery, capture, and language identification

-- ====================
-- Radio Sources (Stations)
-- ====================

CREATE TABLE IF NOT EXISTS radio_sources (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    stream_url TEXT NOT NULL,
    country VARCHAR(3),                  -- ISO 3166-1 alpha-3 country code
    timezone VARCHAR(50),                -- IANA timezone (e.g., 'Africa/Mogadishu')
    lang_hint VARCHAR(10),                -- Expected language code (e.g., 'so', 'ar')
    bitrate INT,                          -- Audio bitrate in kbps
    codec VARCHAR(20),                    -- Audio codec (e.g., 'mp3', 'aac')
    
    -- Metadata from Radio Browser API
    station_uuid VARCHAR(100),            -- Radio Browser station UUID
    homepage TEXT,                        -- Station homepage URL
    tags JSONB DEFAULT '[]',              -- Array of tags
    
    -- Status and lifecycle
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'inactive', 'failed', 'takedown'
    last_check TIMESTAMP WITH TIME ZONE,
    last_successful_capture TIMESTAMP WITH TIME ZONE,
    
    -- Legal and licensing
    license_hint TEXT,                    -- License information if known
    terms_snapshot_hash VARCHAR(64),       -- Hash of terms of service snapshot
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Prevent duplicate stations
    UNIQUE(station_uuid),
    UNIQUE(stream_url)
);

CREATE INDEX idx_radio_sources_country ON radio_sources(country);
CREATE INDEX idx_radio_sources_lang_hint ON radio_sources(lang_hint);
CREATE INDEX idx_radio_sources_status ON radio_sources(status);
CREATE INDEX idx_radio_sources_last_check ON radio_sources(last_check);

-- ====================
-- Radio Shards (Captured Audio Files)
-- ====================

CREATE TABLE IF NOT EXISTS radio_shards (
    id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES radio_sources(id) ON DELETE CASCADE,
    
    -- Capture metadata
    start_ts TIMESTAMP WITH TIME ZONE NOT NULL,
    end_ts TIMESTAMP WITH TIME ZONE NOT NULL,
    duration FLOAT NOT NULL,              -- Duration in seconds
    
    -- File storage
    path TEXT NOT NULL,                    -- Local file path
    s3_url TEXT,                           -- S3 URL if uploaded
    file_size_bytes BIGINT,                -- File size in bytes
    
    -- Audio metadata
    bitrate INT,
    codec VARCHAR(20),
    sample_rate INT DEFAULT 22050,        -- Normalized sample rate
    channels INT DEFAULT 1,               -- Normalized channels (mono)
    
    -- Processing status
    capture_status VARCHAR(20) DEFAULT 'captured',  -- 'captured', 'prefiltered', 'lid_done', 'error'
    error_message TEXT,
    
    -- Speech metrics (updated after prefilter)
    speech_ratio FLOAT,                   -- Ratio of speech to total audio (0-1)
    total_segments INT,                   -- Total segments extracted
    speech_segments INT,                   -- Speech-only segments
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_radio_shards_source_id ON radio_shards(source_id);
CREATE INDEX idx_radio_shards_start_ts ON radio_shards(start_ts);
CREATE INDEX idx_radio_shards_capture_status ON radio_shards(capture_status);
CREATE INDEX idx_radio_shards_created_at ON radio_shards(created_at DESC);

-- ====================
-- Radio Segments (Speech Windows)
-- ====================

CREATE TABLE IF NOT EXISTS radio_segments (
    id SERIAL PRIMARY KEY,
    shard_id INT NOT NULL REFERENCES radio_shards(id) ON DELETE CASCADE,
    
    -- Time boundaries (relative to shard start)
    start_sec FLOAT NOT NULL,              -- Start time in seconds
    end_sec FLOAT NOT NULL,                -- End time in seconds
    duration FLOAT GENERATED ALWAYS AS (end_sec - start_sec) STORED,
    
    -- Speech detection
    is_speech BOOLEAN NOT NULL DEFAULT true,
    music_prob FLOAT,                      -- Probability this is music (0-1)
    
    -- Language identification
    lang_probs JSONB NOT NULL,             -- Language probability distribution {"so": 0.84, "en": 0.10, ...}
    primary_lang VARCHAR(10),              -- Language with highest probability
    confidence FLOAT,                       -- Confidence in primary_lang (0-1)
    
    -- Optional: text-based LID (if transcript available)
    text_lang VARCHAR(10),
    text_confidence FLOAT,
    
    -- Optional: LLM verification (if disagreement)
    llm_verified_lang VARCHAR(10),
    llm_verification_confidence FLOAT,
    
    -- Features (optional, for analysis)
    mfcc_features JSONB,                   -- MFCC feature vector (if computed)
    
    -- File path (if segment extracted to separate file)
    path TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_radio_segments_shard_id ON radio_segments(shard_id);
CREATE INDEX idx_radio_segments_primary_lang ON radio_segments(primary_lang);
CREATE INDEX idx_radio_segments_is_speech ON radio_segments(is_speech);
CREATE INDEX idx_radio_segments_confidence ON radio_segments(confidence);
CREATE INDEX idx_radio_segments_created_at ON radio_segments(created_at);
-- GIN index for JSONB lang_probs queries
CREATE INDEX idx_radio_segments_lang_probs ON radio_segments USING GIN (lang_probs);

-- ====================
-- Radio Station Hourly Aggregates
-- ====================

CREATE TABLE IF NOT EXISTS radio_station_hourly (
    id SERIAL PRIMARY KEY,
    source_id INT NOT NULL REFERENCES radio_sources(id) ON DELETE CASCADE,
    
    -- Time window
    hour TIMESTAMP WITH TIME ZONE NOT NULL, -- Hour bucket (start of hour)
    
    -- Language statistics
    primary_lang VARCHAR(10),              -- Most common language this hour
    lang_mix JSONB NOT NULL,               -- Language distribution {"so": 0.84, "en": 0.10, ...}
    switch_rate FLOAT,                     -- Rate of language switches per minute
    
    -- Speech metrics
    total_segments INT DEFAULT 0,
    speech_segments INT DEFAULT 0,
    speech_ratio FLOAT,                    -- Average speech ratio
    
    -- Dialect analysis (optional)
    dialect_notes TEXT,
    dialect_token_counts JSONB,            -- Dialect-specific token counts if available
    
    -- Quality metrics
    avg_confidence FLOAT,                  -- Average LID confidence
    min_confidence FLOAT,
    max_confidence FLOAT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- One record per station per hour
    UNIQUE(source_id, hour)
);

CREATE INDEX idx_radio_station_hourly_source_id ON radio_station_hourly(source_id);
CREATE INDEX idx_radio_station_hourly_hour ON radio_station_hourly(hour DESC);
CREATE INDEX idx_radio_station_hourly_primary_lang ON radio_station_hourly(primary_lang);
-- GIN index for JSONB lang_mix queries
CREATE INDEX idx_radio_station_hourly_lang_mix ON radio_station_hourly USING GIN (lang_mix);

-- ====================
-- Evaluation Runs (for LID accuracy tracking)
-- ====================

CREATE TABLE IF NOT EXISTS radio_eval_runs (
    id SERIAL PRIMARY KEY,
    run_date DATE NOT NULL,
    language VARCHAR(10) NOT NULL,
    sample_size INT NOT NULL,              -- Number of segments sampled
    
    -- Human-annotated ground truth vs predictions
    precision FLOAT,                       -- Precision of LID predictions
    recall FLOAT,                          -- Recall of LID predictions
    f1_score FLOAT,                        -- F1 score
    
    -- Per-language breakdown (optional)
    per_lang_metrics JSONB,               -- {"so": {"precision": 0.95, ...}, ...}
    
    -- Notes
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(run_date, language)
);

CREATE INDEX idx_radio_eval_runs_run_date ON radio_eval_runs(run_date DESC);
CREATE INDEX idx_radio_eval_runs_language ON radio_eval_runs(language);

-- ====================
-- Triggers for updated_at
-- ====================

CREATE TRIGGER radio_sources_updated_at
    BEFORE UPDATE ON radio_sources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER radio_shards_updated_at
    BEFORE UPDATE ON radio_shards
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER radio_station_hourly_updated_at
    BEFORE UPDATE ON radio_station_hourly
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ====================
-- Comments for documentation
-- ====================

COMMENT ON TABLE radio_sources IS 'Radio stations discovered from Radio Browser API or manual entries';
COMMENT ON TABLE radio_shards IS 'Captured audio files from radio streams';
COMMENT ON TABLE radio_segments IS 'Speech windows extracted from shards with language labels';
COMMENT ON TABLE radio_station_hourly IS 'Aggregated language fingerprints per station per hour';
COMMENT ON TABLE radio_eval_runs IS 'Evaluation runs for tracking LID accuracy over time';

COMMENT ON COLUMN radio_segments.lang_probs IS 'JSONB language probability distribution from LID model';
COMMENT ON COLUMN radio_station_hourly.lang_mix IS 'Aggregated language distribution for the hour';
COMMENT ON COLUMN radio_sources.terms_snapshot_hash IS 'Hash of terms of service snapshot for legal compliance';
