-- Migration 010: Language taxonomy
-- Created: 2025-12-27
-- Purpose: Store languages, families, and dialects for labeling

CREATE TABLE IF NOT EXISTS language_families (
    id SERIAL PRIMARY KEY,
    family_code VARCHAR(50),
    name TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE language_families
    ADD COLUMN IF NOT EXISTS family_code VARCHAR(50),
    ADD COLUMN IF NOT EXISTS notes TEXT;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'language_families'
          AND column_name = 'description'
    ) THEN
        EXECUTE 'UPDATE language_families SET notes = COALESCE(notes, description) WHERE description IS NOT NULL';
    END IF;
END $$;

UPDATE language_families
SET family_code = COALESCE(
    family_code,
    lower(regexp_replace(name, '[^a-z0-9]+', '_', 'g'))
)
WHERE family_code IS NULL;

WITH ranked AS (
    SELECT id,
           family_code,
           ROW_NUMBER() OVER (PARTITION BY family_code ORDER BY id) AS rn
    FROM language_families
)
UPDATE language_families
SET family_code = CONCAT(language_families.family_code, '_', ranked.id)
FROM ranked
WHERE language_families.id = ranked.id
  AND ranked.rn > 1;

ALTER TABLE language_families
    ALTER COLUMN family_code SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'language_families_family_code_key'
    ) THEN
        ALTER TABLE language_families
            ADD CONSTRAINT language_families_family_code_key UNIQUE (family_code);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS language_taxonomy (
    id SERIAL PRIMARY KEY,
    iso639_3 VARCHAR(3) NOT NULL UNIQUE,
    iso639_1 VARCHAR(2),
    name TEXT NOT NULL,
    family_code VARCHAR(50) REFERENCES language_families(family_code),
    countries JSONB DEFAULT '[]',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS language_dialects (
    id SERIAL PRIMARY KEY,
    language_iso639_3 VARCHAR(3) NOT NULL REFERENCES language_taxonomy(iso639_3) ON DELETE CASCADE,
    dialect_code VARCHAR(50) NOT NULL,
    name TEXT NOT NULL,
    region TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language_iso639_3, dialect_code)
);

CREATE INDEX IF NOT EXISTS idx_language_taxonomy_family ON language_taxonomy(family_code);
CREATE INDEX IF NOT EXISTS idx_language_taxonomy_countries ON language_taxonomy USING GIN (countries);
CREATE INDEX IF NOT EXISTS idx_language_dialects_language ON language_dialects(language_iso639_3);

COMMENT ON TABLE language_taxonomy IS 'Canonical language taxonomy for labeling and model training';
COMMENT ON TABLE language_dialects IS 'Dialect registry mapped to language taxonomy';
