# Migration Notes

## Legacy Modules Moved

The following modules have been moved to `legacy/` for review and migration:

### 📁 **scraper/**
- **Purpose**: Wiktionary scraping and data extraction
- **Migration Target**: `apps/intake-worker/sources/wiktionary/`
- **Key Files**:
  - `wiktionary_scraper.py` - Main scraping logic
  - `format_output.py` - Output formatting
  - `scrape_and_format.py` - Combined workflow
  - `scraper_config.py` - Configuration settings

### 📁 **subagents/**
- **Purpose**: Specialized processing agents (phonetics, grammar, metadata)
- **Migration Target**: 
  - `packages/utils/` - For general utilities
  - `apps/profile-builder/` - For language-specific processing
- **Key Files**:
  - `phonetics_agent.py` - Phonetic analysis
  - `grammar_agent.py` - Grammar processing
  - `metadata_agent.py` - Metadata extraction

### 📁 **database/**
- **Purpose**: Database schema and configuration
- **Migration Target**: `infra/db/migrations/`
- **Key Files**:
  - `schema.sql` - Database schema
  - `db_config.py` - Database configuration

### 📁 **utils/**
- **Purpose**: General utility functions
- **Migration Target**: `packages/utils/`
- **Key Files**: Various helper modules

### 📁 **scraped_data/**
- **Purpose**: Output data from scraping operations
- **Migration Target**: `infra/storage/` or cloud storage
- **Note**: Contains historical scraped data

### 📁 **word_lists/**
- **Purpose**: Word lists for scraping
- **Migration Target**: `apps/intake-worker/sources/word-lists/`

### 📄 **Configuration Files**
- `database.ini` - Database connection config
- `openai_test.py` - OpenAI integration test

## Migration Plan

### Phase 1: Review and Assessment
1. **Audit each module** for functionality and dependencies
2. **Identify shared utilities** that should go to `packages/utils/`
3. **Map domain-specific code** to appropriate apps
4. **Document any breaking changes** or API modifications needed

### Phase 2: Gradual Migration
1. **Start with utilities** - Move to `packages/utils/` first
2. **Migrate scraper** - Adapt for `apps/intake-worker/`
3. **Port subagents** - Split between utils and profile-builder
4. **Update database** - Move schema to proper migrations
5. **Clean up data** - Archive or migrate scraped data

### Phase 3: Integration
1. **Update imports** across the codebase
2. **Add tests** for migrated modules
3. **Update documentation** and runbooks
4. **Remove legacy modules** once fully migrated

## Migration Guidelines

- **Preserve functionality** - Ensure no features are lost
- **Update dependencies** - Use new package structure
- **Add tests** - Include unit and integration tests
- **Document changes** - Update READMEs and docs
- **Incremental approach** - Migrate one module at a time

## Status

- ✅ **Moved to legacy**: All old modules relocated
- ✅ **Initial setup complete**: Monorepo structure, data contracts, admin UI, and tooling ready
- 🔄 **Next**: Begin Phase 1 review and assessment
- 📋 **Priority**: Start with `utils/` and `database/` modules
