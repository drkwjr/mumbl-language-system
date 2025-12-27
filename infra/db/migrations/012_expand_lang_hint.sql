-- Migration 012: Expand lang_hint length for richer station hints
-- Created: 2025-12-26

ALTER TABLE radio_sources
    ALTER COLUMN lang_hint TYPE VARCHAR(50);
