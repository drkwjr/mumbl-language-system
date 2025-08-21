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
cd apps/admin-ui
npm run dev  # Starts on http://localhost:5173
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
- **Monorepo Structure**: Clean, organized architecture
- **Data Contracts**: Python Pydantic + TypeScript models with validation
- **Admin UI**: Modern React dashboard with Tailwind CSS
- **Profile Validation CLI**: Command-line validation tool
- **Legacy Migration**: All old modules moved to `legacy/` with migration plan

### 🔄 Next Steps
- Migrate legacy modules to new structure
- Implement core pipeline applications
- Add comprehensive test coverage
- Deploy infrastructure components

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