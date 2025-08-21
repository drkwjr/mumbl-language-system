# mumbl-language-system

Pipelines, profiles, and tooling for Mumbl language ingestion, labeling, curation, TTS training, and runtime speech generation.

This repo is separate from the `mumbl` product backend. The backend will call into `apps/runtime` or the API layer later.

## 🏗️ Architecture

- **`apps/*`**: Worker and service applications
  - `admin-ui/`: Modern React dashboard for system management
  - `intake-worker/`: Data ingestion from various sources
  - `text-lane/`: Text processing and LangExtract pipelines
  - `audio-lane/`: Audio processing and transcription
  - `curator/`: Quality control and segment scoring
  - `profile-builder/`: Language profile generation
  - `tts-trainer/`: TTS model training
  - `synth-gen/`: Speech synthesis
  - `runtime/`: Runtime API service

- **`packages/*`**: Shared libraries and contracts
  - `data-contracts/`: Python Pydantic + TypeScript models
  - `langextract-schemas/`: LangExtract schemas and few-shots
  - `scoring/`: Quality scoring algorithms
  - `storage/`: Database abstractions
  - `logging/`: Structured logging and telemetry
  - `utils/`: Common utilities

- **`infra/*`**: Infrastructure and deployment
  - `db/`: Database migrations and schema
  - `docker/`: Container configurations
  - `k8s/`: Kubernetes manifests

- **`tests/*`**: Unit, integration, and e2e tests
- **`docs/*`**: ADRs, runbooks, and playbooks
- **`legacy/*`**: Migration holding area for previous repo modules

## 🚀 Quick Start

### Prerequisites
- Python 3.9+ (3.11 recommended)
- Node 20+
- Git

### Setup
```bash
# Clone and setup
git clone <repository-url>
cd mumbl-language-system

# Bootstrap environment
make bootstrap

# Run checks
make check
```

### Development

#### Admin UI
```bash
# Quick start with full setup and browser opening
make admin-ui

# Or run the script directly
./scripts/start_admin_ui.sh

# Stop admin UI processes
make stop-admin-ui
# Or run the script directly
./scripts/stop_admin_ui.sh

# Manual start (if already set up)
cd apps/admin-ui
npm run dev  # Starts on http://localhost:3500
```

#### Profile Validation
```bash
# Validate a language profile
python scripts/profile_validate.py profile.json

# Create example profile
python scripts/profile_validate.py --create-example example.json
```

#### Data Contracts
```bash
# Generate schemas from Python models
python scripts/generate_schemas.py

# Generate TypeScript types
python scripts/generate_typescript_types.py

# Build TypeScript package
cd packages/data-contracts/typescript && npm run build
```

## 📋 Status

### ✅ Completed
- **Monorepo Structure**: Clean, organized architecture with proper separation of concerns
- **Data Contracts**: Python Pydantic v2 + TypeScript models with JSON Schema generation
- **Admin UI**: Modern React dashboard with Tailwind CSS v4 and PostCSS integration
- **Profile Validation CLI**: Command-line tool for LanguageProfile JSON validation
- **Legacy Migration**: All old modules moved to `legacy/` with detailed migration plan
- **Development Tooling**: Automated startup scripts, Makefile targets, and environment setup
- **TypeScript Integration**: Generated types from Pydantic models with proper export handling

### 🔄 Next Steps
- Migrate legacy modules to new structure (scraper, subagents, database, utils)
- Implement core pipeline applications (intake-worker, text-lane, audio-lane)
- Add comprehensive test coverage for data contracts and CLI tools
- Deploy infrastructure components (database, Docker, Kubernetes)

## 📚 Documentation

- **Architecture**: See `docs/ADRs/` for design decisions
- **Runbooks**: Operational procedures in `docs/runbooks/`
- **Playbooks**: Strategic guides in `docs/playbooks/`
- **Migration**: Detailed plan in `legacy/MIGRATION_NOTES.md`

## 🤝 Contributing

1. Follow the established monorepo structure
2. Use the data contracts for type safety
3. Add tests for new functionality
4. Update documentation for changes
5. Follow the migration plan for legacy code

## 📄 License

Copyright (c) 2025 Mumbl. All rights reserved. 