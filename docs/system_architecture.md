# Mumbl Language System - System Architecture

## Overview

The Mumbl Language System is a comprehensive platform for processing, validating, and orchestrating language data pipelines. The system is built with a modular architecture that ensures data quality, provides automated validation, and enables scalable workflow orchestration.

## Core Architecture Components

### 1. Format Guardians Layer

**Purpose**: Prevent data format drift and ensure quality at every stage.

**Components**:
- **Text Validation**: Validates `TextSegment` JSONL files with required labels and grounding checks
- **Audio Validation**: Validates audio datasets with sample rate, duration, and format requirements  
- **Scores Validation**: Validates scoring data with range checks
- **Profile Validation**: Validates `LanguageProfile` JSON files

**Key Features**:
- Automated validation at pipeline boundaries
- Detailed error reporting with path information
- CLI tools for manual validation
- Integration points for orchestration workflows

### 2. Dataset Building Layer

**Purpose**: Transform raw data into training-ready datasets with quality guarantees.

**Components**:
- **TTS Dataset Builder**: Creates training-ready datasets from curated manifests
- **Dataset Linting**: Quality checks for sample rates, durations, and content requirements
- **Metadata Generation**: Produces CSV files and dataset cards
- **Snapshot Management**: Versioned dataset snapshots with audit trails

**Key Features**:
- Built-in quality linting before dataset creation
- Standardized output formats for TTS training
- Dataset statistics and metadata generation
- CLI interface for batch processing

### 3. Orchestration Layer

**Purpose**: Coordinate complex data processing workflows with reliability and observability.

**Components**:
- **Text Lane Flows**: LangExtract integration for dialogue detection and labeling
- **Audio Lane Flows**: ASR, diarization, and audio normalization pipelines
- **Curator Flows**: Scoring, deduplication, and dataset snapshot creation
- **Batch Management**: Batch manifest tracking and status management

**Key Features**:
- Prefect-based workflow orchestration
- Task-level parallelism and error handling
- Progress tracking and metrics collection
- Integration with validation and building layers

### 4. Runtime API Layer

**Purpose**: Provide REST API access for workflow management and system monitoring.

**Components**:
- **Flow Launch Endpoints**: REST API for triggering text, audio, and curator workflows
- **Preflight Checks**: Cost and storage estimation for YouTube and file uploads
- **Health Monitoring**: System status and readiness endpoints
- **Batch Management**: Batch creation, status tracking, and result retrieval

**Key Features**:
- FastAPI-based REST API
- Async request handling
- Comprehensive error handling
- Health and readiness monitoring

### 5. Data Contracts Layer

**Purpose**: Define and enforce data schemas across the entire system.

**Components**:
- **TextSegment**: Dialogue segments with labels and source references
- **AudioSegment**: Audio clips with metadata and alignment information
- **LanguageProfile**: Language-specific configuration and G2P rules
- **SegmentScore**: Quality scoring for curated content
- **BatchManifest**: Workflow batch tracking and metadata

**Key Features**:
- Pydantic-based schema validation
- TypeScript type generation
- JSON Schema export
- Versioned contract evolution

## Data Flow Architecture

### Text Processing Pipeline

```
Raw Text → LangExtract → TextSegment JSONL → Validation → Curator → Dataset Snapshot
```

1. **Input**: Raw text artifacts (documents, transcripts)
2. **Processing**: LangExtract schemas detect dialogue, topics, registers, code-switches
3. **Validation**: Format guardians validate `TextSegment` JSONL output
4. **Curation**: Scoring, deduplication, and quality gates
5. **Output**: Grounded dialogue corpus with HTML spot-checks

### Audio Processing Pipeline

```
YouTube/File → Preflight → ASR/Diarization → Segmentation → Normalization → Validation → Curator → Dataset Snapshot
```

1. **Input**: YouTube links or audio file uploads
2. **Preflight**: Cost and storage estimation
3. **Processing**: ASR + diarization → segmentation → normalization
4. **Validation**: Format guardians validate audio dataset
5. **Curation**: Scoring, deduplication, policy gates
6. **Output**: Paired speech corpus CSV with clips

### Curator Pipeline

```
Raw Segments → Scoring → Deduplication → Policy Gates → Dataset Building → Snapshot
```

1. **Input**: Raw segments from text and audio lanes
2. **Scoring**: Quality assessment with multiple criteria
3. **Deduplication**: Exact and near-duplicate detection
4. **Policy Gates**: Content filtering and quality thresholds
5. **Dataset Building**: Snapshot creation with dataset cards
6. **Output**: Curated training datasets ready for TTS

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary development language
- **Pydantic 2.6+**: Data validation and serialization
- **Prefect 2.16+**: Workflow orchestration
- **FastAPI 0.110+**: REST API framework
- **PostgreSQL**: Primary data store
- **S3-compatible Storage**: Object storage for artifacts

### Package Dependencies
- **Format Guardians**: pydantic, wave (for audio validation)
- **Dataset Builder**: pydantic, psycopg[binary], csv, json
- **Orchestration**: prefect, pydantic
- **Runtime API**: fastapi, uvicorn, pydantic

### Development Tools
- **pytest**: Testing framework
- **Make**: Build automation
- **Docker**: Containerization
- **Kubernetes**: Orchestration (planned)

## Quality Assurance

### Validation Strategy
- **Contract Validation**: Pydantic models enforce data schemas
- **Format Guardians**: Automated validation at pipeline boundaries
- **Dataset Linting**: Quality checks before dataset creation
- **Integration Testing**: End-to-end pipeline validation

### Error Handling
- **Graceful Degradation**: System continues operation on non-critical failures
- **Detailed Error Reporting**: Path-specific error messages for debugging
- **Retry Logic**: Automatic retry for transient failures
- **Dead Letter Queues**: Failed items are preserved for manual review

### Monitoring and Observability
- **Health Endpoints**: System status and readiness monitoring
- **Metrics Collection**: Performance and quality metrics
- **Logging**: Structured logging with correlation IDs
- **Tracing**: Request tracing across workflow boundaries

## Security and Compliance

### Data Security
- **Input Validation**: All inputs validated against schemas
- **Access Control**: Role-based access control for API endpoints
- **Audit Trails**: Complete audit trail for data transformations
- **Encryption**: Data encryption in transit and at rest

### Compliance
- **Data Privacy**: PII handling and data retention policies
- **Content Filtering**: Policy gates for sensitive content
- **Quality Standards**: Enforced quality thresholds for training data
- **Version Control**: Versioned datasets and models for reproducibility

## Scalability and Performance

### Horizontal Scaling
- **Stateless Services**: API and validation services can be scaled horizontally
- **Workflow Parallelism**: Prefect enables parallel task execution
- **Batch Processing**: Efficient batch processing for large datasets
- **Caching**: Strategic caching for frequently accessed data

### Performance Optimization
- **Async Processing**: Non-blocking I/O for API and validation operations
- **Streaming**: Streaming processing for large files
- **Resource Management**: Efficient resource utilization and cleanup
- **Monitoring**: Performance monitoring and alerting

## Future Enhancements

### Planned Features
- **Real-time Processing**: Stream processing for live data ingestion
- **Advanced ML Integration**: Machine learning models for quality assessment
- **Multi-language Support**: Expanded language support and cross-lingual processing
- **Advanced Analytics**: Comprehensive analytics and reporting dashboard

### Architecture Evolution
- **Microservices**: Further decomposition into microservices
- **Event-driven Architecture**: Event-driven processing for better scalability
- **Cloud-native**: Full cloud-native deployment with auto-scaling
- **Advanced Orchestration**: More sophisticated workflow orchestration patterns
