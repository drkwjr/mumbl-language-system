-- Migration 007: Ensure update_updated_at trigger function exists
-- Created: 2025-12-27
-- Purpose: Provide update_updated_at() for schemas that skip 001_initial_schema.sql

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
