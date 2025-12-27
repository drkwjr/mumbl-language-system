-- Migration 011: Capture target configuration
-- Created: 2025-12-27
-- Purpose: Store capture targets for admin control

CREATE TABLE IF NOT EXISTS capture_targets (
    id SERIAL PRIMARY KEY,
    countries JSONB NOT NULL DEFAULT '[]',
    languages JSONB NOT NULL DEFAULT '[]',
    active BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'capture_targets_updated_at'
    ) THEN
        CREATE TRIGGER capture_targets_updated_at
            BEFORE UPDATE ON capture_targets
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at();
    END IF;
END $$;

COMMENT ON TABLE capture_targets IS 'Admin-managed capture target settings';
