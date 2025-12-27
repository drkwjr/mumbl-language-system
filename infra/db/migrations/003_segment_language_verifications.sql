-- Migration 003: Segment Language Verifications
-- Created: 2025-01-XX
-- Purpose: Store LLM/human language verification results for any segment type

CREATE TABLE IF NOT EXISTS segment_language_verifications (
    id SERIAL PRIMARY KEY,

    -- Polymorphic segment reference
    segment_type VARCHAR(20) NOT NULL,  -- 'audio', 'text', 'radio'
    segment_id INT NOT NULL,

    -- Verification source
    source VARCHAR(20) NOT NULL DEFAULT 'llm',  -- 'llm', 'human', 'asr'
    provider VARCHAR(50),                       -- e.g., 'openai'
    model VARCHAR(100),                         -- e.g., 'gpt-4o-mini'

    -- Inputs/outputs
    candidates JSONB,                           -- List of candidate language codes
    language VARCHAR(10),                       -- Verified language (ISO 639-1)
    dialect VARCHAR(30),                        -- Optional dialect tag (BCP-47)
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    rationale TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_lang_verify_segment ON segment_language_verifications(segment_type, segment_id);
CREATE INDEX idx_lang_verify_language ON segment_language_verifications(language);
CREATE INDEX idx_lang_verify_created_at ON segment_language_verifications(created_at DESC);

COMMENT ON TABLE segment_language_verifications IS 'Language verification results for segments (LLM/human/ASR)';
COMMENT ON COLUMN segment_language_verifications.segment_type IS 'Segment type: audio, text, or radio';
COMMENT ON COLUMN segment_language_verifications.candidates IS 'Candidate language codes used for verification';
