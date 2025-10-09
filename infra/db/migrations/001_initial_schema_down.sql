-- Rollback for Migration 001: Initial Schema
-- Purpose: Clean removal of all tables and functions

-- Drop triggers first
DROP TRIGGER IF EXISTS voices_updated_at ON voices;
DROP TRIGGER IF EXISTS language_profiles_updated_at ON language_profiles;

-- Drop function
DROP FUNCTION IF EXISTS update_updated_at();

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS voices CASCADE;
DROP TABLE IF EXISTS model_registry CASCADE;
DROP TABLE IF EXISTS datasets CASCADE;
DROP TABLE IF EXISTS language_profiles CASCADE;
DROP TABLE IF EXISTS segment_scores CASCADE;
DROP TABLE IF EXISTS audio_segments CASCADE;
DROP TABLE IF EXISTS text_segments CASCADE;
DROP TABLE IF EXISTS raw_artifacts CASCADE;

