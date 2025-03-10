# Database Structure Documentation

## Overview

The Mumbl Language Processing System uses a PostgreSQL database to store linguistic data in a structured and relational format. This document details the database schema, including tables, relationships, and indexing strategies.

## Database Schema

The database schema is defined in `database/schema.sql` and consists of the following main components:

### Core Language Tables

#### Languages

Stores information about languages.

| Column | Type | Description |
|--------|------|-------------|
| language_id | SERIAL | Primary key |
| language_code | VARCHAR(10) | Unique language code (e.g., 'en', 'es') |
| language_name | VARCHAR(100) | Full name of the language |
| language_family | VARCHAR(100) | Language family (e.g., 'Indo-European') |
| is_active | BOOLEAN | Whether the language is actively maintained |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_languages_code` on `language_code`

#### Dialects

Stores dialect variations of languages.

| Column | Type | Description |
|--------|------|-------------|
| dialect_id | SERIAL | Primary key |
| language_id | INTEGER | Foreign key to languages table |
| dialect_name | VARCHAR(100) | Name of the dialect |
| region | VARCHAR(100) | Geographic region of the dialect |
| description | TEXT | Description of the dialect |
| is_active | BOOLEAN | Whether the dialect is actively maintained |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_dialects_language_id` on `language_id`

### Vocabulary Tables

#### Words

Stores core vocabulary data.

| Column | Type | Description |
|--------|------|-------------|
| word_id | SERIAL | Primary key |
| language_id | INTEGER | Foreign key to languages table |
| word_text | VARCHAR(255) | The word itself |
| frequency_rank | INTEGER | Frequency ranking of the word |
| sentence_construction_importance | DECIMAL(5,2) DEFAULT NULL | Importance score for sentence construction (NULL if unknown) |
| conversational_utility_score | DECIMAL(5,2) DEFAULT NULL | Utility score for conversations (NULL if unknown) |
| part_of_speech | VARCHAR(50) | Part of speech (noun, verb, etc.) |
| etymology | TEXT | Word origin information |
| is_archaic | BOOLEAN | Whether the word is archaic |
| is_slang | BOOLEAN | Whether the word is slang |
| is_vulgar | BOOLEAN | Whether the word is vulgar |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_words_text` on `word_text`
- `idx_words_language_id` on `language_id`
- `idx_words_frequency` on `frequency_rank`

#### Definitions

Stores multiple definitions for words.

| Column | Type | Description |
|--------|------|-------------|
| definition_id | SERIAL | Primary key |
| word_id | INTEGER | Foreign key to words table |
| definition_text | TEXT | The definition text |
| context | VARCHAR(100) | Context in which the definition applies |
| domain | VARCHAR(100) | Domain or field of the definition |
| usage_notes | TEXT | Notes on usage |
| definition_order | INTEGER | Order of the definition (for multiple definitions) |
| is_primary | BOOLEAN | Whether this is the primary definition |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_definitions_word_id` on `word_id`
- `idx_definitions_domain` on `domain`

### Pronunciation Tables

#### Phonetics

Stores pronunciation data for words.

| Column | Type | Description |
|--------|------|-------------|
| phonetic_id | SERIAL | Primary key |
| word_id | INTEGER | Foreign key to words table |
| dialect_id | INTEGER | Foreign key to dialects table (NULL if pronunciation applies broadly) |
| ipa_pronunciation | VARCHAR(255) | IPA notation for pronunciation |
| audio_file_path | VARCHAR(255) | Path to audio file |
| pronunciation_variant | VARCHAR(50) | Variant type (formal, casual, etc.) |
| is_primary | BOOLEAN | Whether this is the primary pronunciation |
| notes | TEXT | Additional notes |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_phonetics_word_id` on `word_id`
- `idx_phonetics_dialect_id` on `dialect_id`

A word may have multiple phonetic records, each representing a different dialect, pronunciation variant, or regional accent.

### Grammar Tables

#### Grammar Rules

Stores grammar rules categorized by type.

| Column | Type | Description |
|--------|------|-------------|
| rule_id | SERIAL | Primary key |
| language_id | INTEGER | Foreign key to languages table |
| rule_type | grammar_rule_type | Enum: syntax, morphology, phonology, semantics, pragmatics |
| rule_name | VARCHAR(255) | Name of the rule |
| rule_description | TEXT | Description of the rule |
| rule_formula | TEXT | Formal representation of the rule |
| exceptions | TEXT | Exceptions to the rule |
| complexity_level | INTEGER | Complexity level (1-10) |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_grammar_rules_language_id` on `language_id`
- `idx_grammar_rules_type` on `rule_type`

### Usage Examples

#### Example Sentences

Stores example sentences with complexity and tone metrics.

| Column | Type | Description |
|--------|------|-------------|
| sentence_id | SERIAL | Primary key |
| language_id | INTEGER | Foreign key to languages table |
| sentence_text | TEXT | The sentence text |
| complexity_score | DECIMAL(5,2) | Complexity score (0-10) |
| tone | VARCHAR(50) | Tone of the sentence (formal, informal, etc.) |
| context | TEXT | Context of the sentence |
| translation | TEXT | Translation of the sentence |
| contains_idioms | BOOLEAN | Whether the sentence contains idioms |
| contains_slang | BOOLEAN | Whether the sentence contains slang |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_sentences_language_id` on `language_id`
- `idx_sentences_complexity` on `complexity_score`
- `idx_sentences_tone` on `tone`

#### Word-Sentence Map

Maps words to sentences they appear in (many-to-many relationship).

| Column | Type | Description |
|--------|------|-------------|
| map_id | SERIAL | Primary key |
| word_id | INTEGER | Foreign key to words table |
| sentence_id | INTEGER | Foreign key to example_sentences table |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |

**Indexes:**
- `idx_word_sentence_word_id` on `word_id`
- `idx_word_sentence_sentence_id` on `sentence_id`

### Metadata Tables

#### Metadata Sources

Tracks information about data sources and their reliability.

| Column | Type | Description |
|--------|------|-------------|
| source_id | SERIAL | Primary key |
| source_name | VARCHAR(255) | Name of the source |
| source_type | VARCHAR(100) | Type of source (academic, dictionary, etc.) |
| reliability_score | DECIMAL(3,2) | Reliability score (0-5) |
| url | VARCHAR(255) | URL of the source |
| publication_date | DATE | Publication date |
| license_info | TEXT | License information |
| notes | TEXT | Additional notes |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_metadata_source_name` on `source_name`
- `idx_metadata_source_type` on `source_type`
- `idx_metadata_reliability` on `reliability_score`

The system also tracks whether a data source is structured, semi-structured, or unstructured for better categorization and processing.

#### Entity Metadata

Links entities to their metadata sources.

| Column | Type | Description |
|--------|------|-------------|
| metadata_id | SERIAL | Primary key |
| entity_type | VARCHAR(50) | Type of entity (word, definition, etc.) |
| entity_id | INTEGER | ID of the entity |
| source_id | INTEGER | Foreign key to metadata_sources table |
| confidence_score | DECIMAL(3,2) | Confidence score (0-1) |
| notes | TEXT | Additional notes |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |

**Indexes:**
- `idx_entity_metadata_type_id` on `entity_type, entity_id`
- `idx_entity_metadata_source_id` on `source_id`

### Relationship Tables

#### Language Relationships

Tracks similarities and relationships between languages.

| Column | Type | Description |
|--------|------|-------------|
| relationship_id | SERIAL | Primary key |
| language_id_1 | INTEGER | Foreign key to languages table |
| language_id_2 | INTEGER | Foreign key to languages table |
| relationship_type | ENUM ('parent', 'sibling', 'influenced_by') | Type of relationship |
| similarity_score | DECIMAL(5,2) | Similarity score (0-100) |
| relationship_description | TEXT | Description of the relationship |
| evidence | TEXT | Evidence for the relationship |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_lang_rel_language1` on `language_id_1`
- `idx_lang_rel_language2` on `language_id_2`
- `idx_lang_rel_type` on `relationship_type`

### Agent and History Tables

#### Subagents

Tracks entities that make changes to the database.

| Column | Type | Description |
|--------|------|-------------|
| subagent_id | SERIAL | Primary key |
| subagent_name | VARCHAR(100) | Name of the subagent |
| subagent_type | VARCHAR(50) | Type of subagent |
| description | TEXT | Description of the subagent |
| is_active | BOOLEAN | Whether the subagent is active |
| created_at | TIMESTAMP WITH TIME ZONE | Record creation timestamp |
| updated_at | TIMESTAMP WITH TIME ZONE | Record update timestamp |

**Indexes:**
- `idx_subagents_name` on `subagent_name`

#### Change History

Tracks all modifications made to the database.

| Column | Type | Description |
|--------|------|-------------|
| change_id | SERIAL | Primary key |
| table_modified | VARCHAR(100) | Table that was modified |
| record_id | INTEGER | ID of the record that was modified |
| field_modified | VARCHAR(100) | Field that was modified |
| subagent_id | INTEGER | Foreign key to subagents table |
| change_description | TEXT | Description of the change |
| previous_value | JSONB | Previous value of the field (stored as structured JSON) |
| new_value | JSONB | New value of the field (stored as structured JSON) |
| change_timestamp | TIMESTAMP WITH TIME ZONE | Timestamp of the change |
| change_reason | TEXT | Reason for the change |

**Indexes:**
- `idx_change_history_table` on `table_modified`
- `idx_change_history_record` on `table_modified, record_id`
- `idx_change_history_subagent` on `subagent_id`
- `idx_change_history_timestamp` on `change_timestamp`

## Database Functions and Triggers

### update_timestamp()

A trigger function that automatically updates the `updated_at` field to the current timestamp whenever a record is updated.

### record_change()

A function that automatically records changes to tracked tables in the change_history table.

## Database Relationships

The database design incorporates numerous relationships to maintain referential integrity:

- Words belong to Languages (many-to-one)
- Definitions belong to Words (many-to-one)
- Phonetics belong to Words and optionally to Dialects (many-to-one)
- Grammar Rules belong to Languages (many-to-one)
- Example Sentences belong to Languages (many-to-one)
- Words and Example Sentences have a many-to-many relationship through Word-Sentence Map
- Entity Metadata links various entities to Metadata Sources (many-to-one)
- Language Relationships connect pairs of Languages
- Change History records can be linked to Subagents (many-to-one)

## Indexing Strategy

The database uses strategic indexing to optimize common query patterns:

1. **Primary Key Indexing**: All tables have primary key indexes
2. **Foreign Key Indexing**: Foreign key columns are indexed to optimize joins
3. **Search Field Indexing**: Common search fields like `word_text` and `language_code` are indexed
4. **Composite Indexing**: Some tables use composite indexes for frequently combined search conditions

## Database Configuration

Database connection settings are managed in `database/db_config.py`. This file provides functions to load database connection parameters from environment variables or configuration files. 