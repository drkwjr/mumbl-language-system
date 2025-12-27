-- Migration 014: Discovery coverage reports
-- Created: 2025-12-26
-- Purpose: Store aggregated discovery coverage reports for admin visibility

CREATE TABLE IF NOT EXISTS discovery_coverage_reports (
    id SERIAL PRIMARY KEY,
    target_countries JSONB DEFAULT '[]',
    report JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_discovery_coverage_reports_created_at
    ON discovery_coverage_reports(created_at DESC);

COMMENT ON TABLE discovery_coverage_reports IS 'Aggregated discovery coverage reports for admin display';
