-- PostgreSQL Database Schema for Language Processing System

-- Enable UUID extension for unique identifiers
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Languages table
CREATE TABLE languages (
    language_id SERIAL PRIMARY KEY,
    language_code VARCHAR(10) NOT NULL UNIQUE,
    language_name VARCHAR(100) NOT NULL,
    language_family VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on language code for faster lookups
CREATE INDEX idx_languages_code ON languages(language_code);

-- Dialects table
CREATE TABLE dialects (
    dialect_id SERIAL PRIMARY KEY,
    language_id INTEGER NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    dialect_name VARCHAR(100) NOT NULL,
    region VARCHAR(100),
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language_id, dialect_name)
);

-- Create index for faster dialect lookups by language
CREATE INDEX idx_dialects_language_id ON dialects(language_id);

-- Words table
CREATE TABLE words (
    word_id SERIAL PRIMARY KEY,
    language_id INTEGER NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    word_text VARCHAR(255) NOT NULL,
    frequency_rank INTEGER,
    sentence_construction_importance DECIMAL(5,2),
    conversational_utility_score DECIMAL(5,2),
    part_of_speech VARCHAR(50),
    etymology TEXT,
    is_archaic BOOLEAN DEFAULT FALSE,
    is_slang BOOLEAN DEFAULT FALSE,
    is_vulgar BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language_id, word_text)
);

-- Create indexes for words lookups
CREATE INDEX idx_words_text ON words(word_text);
CREATE INDEX idx_words_language_id ON words(language_id);
CREATE INDEX idx_words_frequency ON words(frequency_rank);

-- Definitions table
CREATE TABLE definitions (
    definition_id SERIAL PRIMARY KEY,
    word_id INTEGER NOT NULL REFERENCES words(word_id) ON DELETE CASCADE,
    definition_text TEXT NOT NULL,
    context VARCHAR(100),
    domain VARCHAR(100),
    usage_notes TEXT,
    definition_order INTEGER NOT NULL DEFAULT 1, -- For ordering multiple definitions
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for definition lookups
CREATE INDEX idx_definitions_word_id ON definitions(word_id);
CREATE INDEX idx_definitions_domain ON definitions(domain);

-- Phonetics table
CREATE TABLE phonetics (
    phonetic_id SERIAL PRIMARY KEY,
    word_id INTEGER NOT NULL REFERENCES words(word_id) ON DELETE CASCADE,
    dialect_id INTEGER REFERENCES dialects(dialect_id) ON DELETE SET NULL,
    ipa_pronunciation VARCHAR(255) NOT NULL,
    audio_file_path VARCHAR(255),
    pronunciation_variant VARCHAR(50), -- e.g., "formal", "casual", "regional"
    is_primary BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for phonetics lookups
CREATE INDEX idx_phonetics_word_id ON phonetics(word_id);
CREATE INDEX idx_phonetics_dialect_id ON phonetics(dialect_id);

-- Grammar rule types enum
CREATE TYPE grammar_rule_type AS ENUM ('syntax', 'morphology', 'phonology', 'semantics', 'pragmatics');

-- Grammar Rules table
CREATE TABLE grammar_rules (
    rule_id SERIAL PRIMARY KEY,
    language_id INTEGER NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    rule_type grammar_rule_type NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    rule_description TEXT NOT NULL,
    rule_formula TEXT, -- For formal representation of the rule
    exceptions TEXT,
    complexity_level INTEGER CHECK (complexity_level BETWEEN 1 AND 10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for grammar rule lookups
CREATE INDEX idx_grammar_rules_language_id ON grammar_rules(language_id);
CREATE INDEX idx_grammar_rules_type ON grammar_rules(rule_type);

-- Example Sentences table
CREATE TABLE example_sentences (
    sentence_id SERIAL PRIMARY KEY,
    language_id INTEGER NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    sentence_text TEXT NOT NULL,
    complexity_score DECIMAL(5,2) CHECK (complexity_score BETWEEN 0 AND 10),
    tone VARCHAR(50), -- e.g., formal, informal, angry, happy
    context TEXT,
    translation TEXT,
    contains_idioms BOOLEAN DEFAULT FALSE,
    contains_slang BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for sentence lookups
CREATE INDEX idx_sentences_language_id ON example_sentences(language_id);
CREATE INDEX idx_sentences_complexity ON example_sentences(complexity_score);
CREATE INDEX idx_sentences_tone ON example_sentences(tone);

-- Word-Sentence relationship (many-to-many)
CREATE TABLE word_sentence_map (
    map_id SERIAL PRIMARY KEY,
    word_id INTEGER NOT NULL REFERENCES words(word_id) ON DELETE CASCADE,
    sentence_id INTEGER NOT NULL REFERENCES example_sentences(sentence_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(word_id, sentence_id)
);

-- Create indexes for word-sentence relationship
CREATE INDEX idx_word_sentence_word_id ON word_sentence_map(word_id);
CREATE INDEX idx_word_sentence_sentence_id ON word_sentence_map(sentence_id);

-- Metadata Sources table
CREATE TABLE metadata_sources (
    source_id SERIAL PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(100) NOT NULL, -- e.g., academic, dictionary, corpus
    reliability_score DECIMAL(3,2) CHECK (reliability_score BETWEEN 0 AND 5),
    url VARCHAR(255),
    publication_date DATE,
    license_info TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for metadata source lookups
CREATE INDEX idx_metadata_source_name ON metadata_sources(source_name);
CREATE INDEX idx_metadata_source_type ON metadata_sources(source_type);
CREATE INDEX idx_metadata_reliability ON metadata_sources(reliability_score);

-- Entity Metadata link table (for associating sources with various entities)
CREATE TABLE entity_metadata (
    metadata_id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL, -- e.g., "word", "definition", "phonetic", "grammar_rule"
    entity_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL REFERENCES metadata_sources(source_id) ON DELETE CASCADE,
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity_type, entity_id, source_id)
);

-- Create indexes for entity metadata lookups
CREATE INDEX idx_entity_metadata_type_id ON entity_metadata(entity_type, entity_id);
CREATE INDEX idx_entity_metadata_source_id ON entity_metadata(source_id);

-- Language Relationships table
CREATE TABLE language_relationships (
    relationship_id SERIAL PRIMARY KEY,
    language_id_1 INTEGER NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    language_id_2 INTEGER NOT NULL REFERENCES languages(language_id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL, -- e.g., parent, sibling, influenced_by
    similarity_score DECIMAL(5,2) CHECK (similarity_score BETWEEN 0 AND 100),
    relationship_description TEXT,
    evidence TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (language_id_1 <> language_id_2)
);

-- Create indexes for language relationship lookups
CREATE INDEX idx_lang_rel_language1 ON language_relationships(language_id_1);
CREATE INDEX idx_lang_rel_language2 ON language_relationships(language_id_2);
CREATE INDEX idx_lang_rel_type ON language_relationships(relationship_type);

-- Subagents table (for tracking entities that make changes)
CREATE TABLE subagents (
    subagent_id SERIAL PRIMARY KEY,
    subagent_name VARCHAR(100) NOT NULL,
    subagent_type VARCHAR(50) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for subagent lookups
CREATE INDEX idx_subagents_name ON subagents(subagent_name);

-- Change History table
CREATE TABLE change_history (
    change_id SERIAL PRIMARY KEY,
    table_modified VARCHAR(100) NOT NULL,
    record_id INTEGER NOT NULL,
    field_modified VARCHAR(100) NOT NULL,
    subagent_id INTEGER REFERENCES subagents(subagent_id) ON DELETE SET NULL,
    change_description TEXT NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    change_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    change_reason TEXT
);

-- Create indexes for change history lookups
CREATE INDEX idx_change_history_table ON change_history(table_modified);
CREATE INDEX idx_change_history_record ON change_history(table_modified, record_id);
CREATE INDEX idx_change_history_subagent ON change_history(subagent_id);
CREATE INDEX idx_change_history_timestamp ON change_history(change_timestamp);

-- Schema modifications

-- 🔹 Modify words Table (Allow NULL for Placeholder Scores)
ALTER TABLE words ALTER COLUMN sentence_construction_importance DROP NOT NULL;
ALTER TABLE words ALTER COLUMN conversational_utility_score DROP NOT NULL;

-- 🔹 Ensure a Word Can Have Multiple Phonetic Records (Enforce word_id NOT NULL)
ALTER TABLE phonetics ALTER COLUMN word_id SET NOT NULL;

-- 🔹 Convert previous_value & new_value in change_history to JSONB
ALTER TABLE change_history ALTER COLUMN previous_value TYPE JSONB USING previous_value::jsonb;
ALTER TABLE change_history ALTER COLUMN new_value TYPE JSONB USING new_value::jsonb;

-- 🔹 Convert relationship_type in language_relationships to ENUM
CREATE TYPE relationship_enum AS ENUM ('parent', 'sibling', 'influenced_by');
ALTER TABLE language_relationships ALTER COLUMN relationship_type SET DATA TYPE relationship_enum USING relationship_type::relationship_enum; 