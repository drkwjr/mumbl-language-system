-- Migration 001: Initial Schema for Mumbl Language System
-- Created: 2025-10-09
-- Purpose: Core tables for text/audio lanes, scoring, and profiles

-- ====================
-- Core Artifact Tracking
-- ====================

CREATE TABLE IF NOT EXISTS raw_artifacts (
    id SERIAL PRIMARY KEY,
    source VARCHAR(100) NOT NULL,  -- 'youtube', 'file_upload', 'wiki', etc.
    uri TEXT NOT NULL,              -- S3 path or URL
    language VARCHAR(10),
    dialect VARCHAR(20),
    meta JSONB DEFAULT '{}',        -- Flexible metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, uri)             -- Prevent duplicate artifact ingestion
);

CREATE INDEX idx_raw_artifacts_language ON raw_artifacts(language);
CREATE INDEX idx_raw_artifacts_source ON raw_artifacts(source);
CREATE INDEX idx_raw_artifacts_created_at ON raw_artifacts(created_at DESC);

-- ====================
-- Text Segments (from Text Lane)
-- ====================

CREATE TABLE IF NOT EXISTS text_segments (
    id SERIAL PRIMARY KEY,
    doc_id VARCHAR(255) NOT NULL,   -- Source document identifier
    start_offset INT NOT NULL,      -- Character offset in source
    end_offset INT NOT NULL,        -- Character offset in source
    text TEXT NOT NULL,
    text_hash VARCHAR(64) NOT NULL, -- SHA-256 of text for deduplication
    lang VARCHAR(10) NOT NULL,
    
    -- Labels from LangExtract
    is_dialogue BOOLEAN NOT NULL DEFAULT false,
    topic VARCHAR(100),
    register_type VARCHAR(50),       -- 'formal', 'informal', 'technical', etc.
    code_switch_spans JSONB DEFAULT '[]', -- Array of [start, end] tuples
    
    -- Metadata
    batch_id VARCHAR(100),
    processing_version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Deduplication constraint
    UNIQUE(text_hash)
);

CREATE INDEX idx_text_segments_doc_id ON text_segments(doc_id);
CREATE INDEX idx_text_segments_lang ON text_segments(lang);
CREATE INDEX idx_text_segments_is_dialogue ON text_segments(is_dialogue);
CREATE INDEX idx_text_segments_topic ON text_segments(topic);
CREATE INDEX idx_text_segments_register ON text_segments(register_type);
CREATE INDEX idx_text_segments_batch_id ON text_segments(batch_id);
CREATE INDEX idx_text_segments_hash ON text_segments(text_hash);

-- ====================
-- Audio Segments (from Audio Lane)
-- ====================

CREATE TABLE IF NOT EXISTS audio_segments (
    id SERIAL PRIMARY KEY,
    audio_file VARCHAR(500) NOT NULL,  -- S3 path to WAV clip
    audio_hash VARCHAR(64),            -- Acoustic fingerprint for deduplication
    start_time FLOAT NOT NULL,         -- Start time in original audio
    end_time FLOAT NOT NULL,           -- End time in original audio
    duration FLOAT GENERATED ALWAYS AS (end_time - start_time) STORED,
    
    speaker_id VARCHAR(100),
    transcript_text TEXT,
    lang VARCHAR(10),
    dialect VARCHAR(20),
    dialect_probs JSONB,               -- Dialect confidence scores
    
    -- Quality metrics
    alignment_confidence FLOAT,        -- ASR alignment confidence (0-1)
    diarization_confidence FLOAT,      -- Speaker diarization confidence (0-1)
    granularity VARCHAR(20),           -- 'sentence', 'word', or 'phone'
    
    -- Technical metadata
    sample_rate INT,                   -- 22050 or 24000 Hz
    normalization_params JSONB,        -- Record normalization applied
    
    -- Metadata
    batch_id VARCHAR(100),
    processing_version VARCHAR(20) DEFAULT '1.0.0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Optional deduplication constraint (empty string if fingerprinting not applied)
    UNIQUE(audio_hash)
);

CREATE INDEX idx_audio_segments_lang ON audio_segments(lang);
CREATE INDEX idx_audio_segments_dialect ON audio_segments(dialect);
CREATE INDEX idx_audio_segments_speaker ON audio_segments(speaker_id);
CREATE INDEX idx_audio_segments_duration ON audio_segments(duration);
CREATE INDEX idx_audio_segments_batch_id ON audio_segments(batch_id);
CREATE INDEX idx_audio_segments_hash ON audio_segments(audio_hash);

-- ====================
-- Segment Scores (from Curator)
-- ====================

CREATE TABLE IF NOT EXISTS segment_scores (
    id SERIAL PRIMARY KEY,
    segment_type VARCHAR(20) NOT NULL,  -- 'text' or 'audio'
    segment_id INT NOT NULL,            -- Foreign key to text_segments or audio_segments
    
    -- Score dimensions (0-100 each)
    clarity FLOAT CHECK (clarity >= 0 AND clarity <= 100),
    alignment FLOAT CHECK (alignment >= 0 AND alignment <= 100),
    diarization FLOAT CHECK (diarization >= 0 AND diarization <= 100),
    transcript_accuracy FLOAT CHECK (transcript_accuracy >= 0 AND transcript_accuracy <= 100),
    validity FLOAT CHECK (validity >= 0 AND validity <= 100),
    shape FLOAT CHECK (shape >= 0 AND shape <= 100),
    total FLOAT CHECK (total >= 0 AND total <= 100),
    
    -- Eligibility flags
    eligible_learner BOOLEAN DEFAULT false,  -- total >= 90
    eligible_training BOOLEAN DEFAULT false, -- total >= 70
    
    -- Policy gates
    policy_flags JSONB DEFAULT '[]',         -- Array of policy violations
    
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one score per segment
    UNIQUE(segment_type, segment_id)
);

CREATE INDEX idx_segment_scores_segment ON segment_scores(segment_type, segment_id);
CREATE INDEX idx_segment_scores_total ON segment_scores(total DESC);
CREATE INDEX idx_segment_scores_eligible_learner ON segment_scores(eligible_learner);
CREATE INDEX idx_segment_scores_eligible_training ON segment_scores(eligible_training);

-- ====================
-- Language Profiles
-- ====================

CREATE TABLE IF NOT EXISTS language_profiles (
    id SERIAL PRIMARY KEY,
    language VARCHAR(10) NOT NULL,
    dialect VARCHAR(20) NOT NULL,
    script VARCHAR(50) NOT NULL,
    version VARCHAR(20) NOT NULL,  -- Semantic version
    
    -- Profile JSON blob (full LanguageProfileV1 model)
    profile_json JSONB NOT NULL,
    
    -- Extracted for query convenience
    tts_strategy VARCHAR(30),      -- 'standalone', 'grouped', 'cloud_fallback'
    phoneme_count INT,             -- Size of phoneme_inventory
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- One profile per dialect
    UNIQUE(dialect)
);

CREATE INDEX idx_language_profiles_language ON language_profiles(language);
CREATE INDEX idx_language_profiles_dialect ON language_profiles(dialect);
CREATE INDEX idx_language_profiles_strategy ON language_profiles(tts_strategy);

-- ====================
-- Datasets (Snapshots)
-- ====================

CREATE TABLE IF NOT EXISTS datasets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    language VARCHAR(10) NOT NULL,
    dialect VARCHAR(20),
    dataset_type VARCHAR(50) NOT NULL,  -- 'tts_training', 'tts_learner', 'asr', etc.
    
    -- Snapshot manifest
    manifest_json JSONB NOT NULL,       -- Full manifest with segment IDs and metadata
    
    -- Statistics
    segment_count INT,
    total_duration_seconds FLOAT,
    avg_score FLOAT,
    
    -- Storage
    artifact_uri TEXT,                  -- S3 path to dataset directory
    
    -- Versioning
    version VARCHAR(20),
    parent_dataset_id INT REFERENCES datasets(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(name, version)
);

CREATE INDEX idx_datasets_language ON datasets(language);
CREATE INDEX idx_datasets_dialect ON datasets(dialect);
CREATE INDEX idx_datasets_type ON datasets(dataset_type);
CREATE INDEX idx_datasets_created_at ON datasets(created_at DESC);

-- ====================
-- Model Registry
-- ====================

CREATE TABLE IF NOT EXISTS model_registry (
    id SERIAL PRIMARY KEY,
    kind VARCHAR(50) NOT NULL,         -- 'tts', 'asr', 'g2p', etc.
    language VARCHAR(10) NOT NULL,
    dialect VARCHAR(20),
    model_name VARCHAR(200) NOT NULL,
    version VARCHAR(20) NOT NULL,      -- Semantic version
    
    -- Training metadata
    training_dataset_id INT REFERENCES datasets(id),
    training_config JSONB,
    
    -- Evaluation metrics
    metrics_json JSONB,                -- MOS-lite, WER, stability, etc.
    
    -- Artifact location
    artifact_uri TEXT NOT NULL,        -- S3 path or model registry URL
    
    -- Status
    status VARCHAR(30) DEFAULT 'dev',  -- 'dev', 'staging', 'prod'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(kind, language, dialect, version)
);

CREATE INDEX idx_model_registry_kind ON model_registry(kind);
CREATE INDEX idx_model_registry_language ON model_registry(language);
CREATE INDEX idx_model_registry_status ON model_registry(status);
CREATE INDEX idx_model_registry_created_at ON model_registry(created_at DESC);

-- ====================
-- Voices (TTS voices tied to models)
-- ====================

CREATE TABLE IF NOT EXISTS voices (
    id SERIAL PRIMARY KEY,
    dialect VARCHAR(20) NOT NULL,
    voice_id VARCHAR(100) NOT NULL UNIQUE,
    voice_name VARCHAR(200),
    model_id INT REFERENCES model_registry(id),
    
    -- Training data stats
    training_minutes FLOAT,
    speaker_count INT,
    
    -- Quality metrics
    mos_lite FLOAT,                    -- Mean Opinion Score (lite version)
    stability_score FLOAT,             -- Pronunciation stability
    
    -- Metadata
    style_tags JSONB DEFAULT '[]',     -- Array of style tokens
    is_active BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_voices_dialect ON voices(dialect);
CREATE INDEX idx_voices_model_id ON voices(model_id);
CREATE INDEX idx_voices_active ON voices(is_active);

-- ====================
-- Triggers for updated_at
-- ====================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER language_profiles_updated_at
    BEFORE UPDATE ON language_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER voices_updated_at
    BEFORE UPDATE ON voices
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ====================
-- Comments for documentation
-- ====================

COMMENT ON TABLE raw_artifacts IS 'Tracks all raw data ingested into the system';
COMMENT ON TABLE text_segments IS 'Labeled text segments from Text Lane with grounded offsets';
COMMENT ON TABLE audio_segments IS 'Audio clips from Audio Lane with transcripts and quality metrics';
COMMENT ON TABLE segment_scores IS 'Quality scores from Curator for both text and audio segments';
COMMENT ON TABLE language_profiles IS 'Per-dialect configuration including G2P rules and TTS settings';
COMMENT ON TABLE datasets IS 'Immutable dataset snapshots for training and evaluation';
COMMENT ON TABLE model_registry IS 'Trained models with versions and evaluation metrics';
COMMENT ON TABLE voices IS 'Production TTS voices mapped to trained models';

COMMENT ON COLUMN text_segments.text_hash IS 'SHA-256 hash for exact text deduplication';
COMMENT ON COLUMN audio_segments.audio_hash IS 'Acoustic fingerprint for audio deduplication';
COMMENT ON COLUMN segment_scores.eligible_learner IS 'Score >= 90, suitable for learner/premium datasets';
COMMENT ON COLUMN segment_scores.eligible_training IS 'Score >= 70, suitable for TTS training';

