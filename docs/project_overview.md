# Mumbl Language Processing System

## Project Overview

The Mumbl Language Processing System is a comprehensive platform designed for collecting, analyzing, and processing linguistic data. This document provides an overview of the system architecture, components, and workflows.

## System Purpose

The primary purpose of the Mumbl system is to create a robust database of language information including:

- Words and their frequency, construction importance, and conversational utility
- Multiple definitions for words with contextual information
- Phonetic data including IPA pronunciation and dialect variations
- Grammar rules categorized by type (syntax, morphology, phonology, semantics)
- Example sentences with complexity and tone metrics
- Data source metadata and reliability tracking
- Language relationships and similarities

## System Architecture

The Mumbl system is composed of several interconnected components:

### 1. Format Guardians & Validation

**Format Guardians Package** (`mumbl_format_guardians`): Automated validation tools that ensure data quality and prevent format drift.

- **Text Validation**: Validates `TextSegment` JSONL files with required labels and grounding checks
- **Audio Validation**: Validates audio datasets with sample rate, duration, and format requirements
- **Scores Validation**: Validates scoring data with range checks
- **Profile Validation**: Validates `LanguageProfile` JSON files

### 2. Dataset Building & Orchestration

**Dataset Builder Package** (`mumbl_dataset_builder`): CLI tools for building training datasets with built-in linting.

- **TTS Dataset Building**: Creates training-ready datasets from curated manifests
- **Dataset Linting**: Quality checks for sample rates, durations, and content requirements
- **Metadata Generation**: Produces CSV files and dataset cards

**Orchestration Package** (`mumbl_orchestration`): Prefect-based workflow orchestration for data processing lanes.

- **Text Lane Flows**: LangExtract integration for dialogue detection and labeling
- **Audio Lane Flows**: ASR, diarization, and audio normalization pipelines
- **Curator Flows**: Scoring, deduplication, and dataset snapshot creation

### 3. Runtime API

**Runtime API** (`apps/runtime`): FastAPI-based service for launching workflows and preflight checks.

- **Flow Launch Endpoints**: REST API for triggering text, audio, and curator workflows
- **Preflight Checks**: Cost and storage estimation for YouTube and file uploads
- **Health Monitoring**: System status and readiness endpoints

### 4. Data Contracts

**Data Contracts Package** (`mumbl_data_contracts`): Pydantic models defining the core data structures.

- **TextSegment**: Dialogue segments with labels and source references
- **AudioSegment**: Audio clips with metadata and alignment information
- **LanguageProfile**: Language-specific configuration and G2P rules
- **SegmentScore**: Quality scoring for curated content

### 5. PostgreSQL Database

The core of the system is a PostgreSQL database that stores all linguistic data. The database schema is designed to capture the complex relationships between language elements while maintaining data integrity through foreign key relationships and constraints.

### 6. Legacy Components

**Data Collection (Scrapers)**: Scrapy-based web scrapers that extract linguistic information from various sources.

**Processing Subagents**: Specialized agents for phonetics, grammar, and metadata processing.

## Data Flow

The typical data flow through the system is as follows:

### Text Lane Flow
1. **Input**: Raw text artifacts (documents, transcripts)
2. **Processing**: LangExtract schemas detect dialogue, topics, registers, code-switches
3. **Validation**: Format guardians validate `TextSegment` JSONL output
4. **Output**: Grounded dialogue corpus with HTML spot-checks

### Audio Lane Flow
1. **Input**: YouTube links or audio file uploads
2. **Preflight**: Cost and storage estimation
3. **Processing**: ASR + diarization → segmentation → normalization
4. **Validation**: Format guardians validate audio dataset
5. **Output**: Paired speech corpus CSV with clips

### Curator Flow
1. **Input**: Raw segments from text and audio lanes
2. **Processing**: Scoring, deduplication, policy gates
3. **Dataset Building**: Snapshot creation with dataset cards
4. **Output**: Curated training datasets ready for TTS

### Runtime API
- **Flow Launch**: REST endpoints for triggering workflows
- **Preflight Checks**: Cost estimation for YouTube and file uploads
- **Health Monitoring**: System status and readiness

### Legacy Flow
1. **Data Collection**: Web scrapers extract linguistic data from various sources
2. **Data Storage**: Raw data is stored in the PostgreSQL database
3. **Data Processing**: Subagents process and enrich the data
4. **Data Access**: Applications and services can access the processed data via database queries

## System Benefits

The Mumbl Language Processing System offers several benefits:

- **Comprehensive Language Model**: Captures multiple aspects of language in a structured format
- **Data Traceability**: Tracks sources and changes to maintain data quality
- **Flexible Architecture**: Can be extended with additional scrapers and processing agents
- **Rich Linguistic Context**: Stores relationships between words, grammar rules, and usage examples

## Future Directions

Potential future enhancements to the system include:

- **API Layer**: Building a REST API for external applications to access the data
- **Machine Learning Integration**: Adding ML models for language generation and analysis
- **Multi-language Support**: Expanding beyond initial language focus to support more languages
- **User Interface**: Creating a web interface for browsing and editing the linguistic data
- **Speech Synthesis**: Generating audio pronunciations from IPA notation

## Technical Requirements

The system requires:

### Core Dependencies
- PostgreSQL database (version 12+)
- Python 3.9+
- Pydantic 2.6+ for data validation
- Prefect 2.16+ for workflow orchestration
- FastAPI 0.110+ for runtime API
- psycopg[binary] 3.1+ for database connectivity

### Package Dependencies
- **Format Guardians**: pydantic, wave (for audio validation)
- **Dataset Builder**: pydantic, psycopg[binary], csv, json
- **Orchestration**: prefect, pydantic
- **Runtime API**: fastapi, uvicorn, pydantic

### Legacy Dependencies
- Scrapy for web scraping
- NLTK and related libraries for linguistic processing
- Pandas for data manipulation and export

## Getting Started

See the README.md file for instructions on setting up and running the system. 