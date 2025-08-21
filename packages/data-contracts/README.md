# Data Contracts

Shared data models for profiles, segments, and scores across the Mumbl language system.

## Python Package

**Location**: `python/`
**Technologies**: Pydantic v2 models with validation

**Models**:
- `LanguageProfileV1`: Complete language profile with G2P rules, TTS defaults, and curation targets
- `TextSegment` & `AudioSegment`: Text and audio data segments with labels and source references  
- `SegmentScore`: Quality scores for segments with eligibility flags
- Supporting models: `G2PRule`, `G2POverride`, `TTSDefaults`, `CurationTargets`, `SourceRef`, `Labels`

**Installation**: `pip install -e packages/data-contracts/python/`

## TypeScript Package

**Location**: `typescript/`
**Technologies**: Auto-generated types from JSON Schema

**Usage**:
```typescript
import { LanguageProfileV1, TextSegment, AudioSegment, SegmentScore } from '@mumbl/data-contracts';
```

**Build**: `cd packages/data-contracts/typescript && npm run build`

## Code Generation

- **Schemas**: `python scripts/generate_schemas.py` - Generates JSON Schema from Pydantic models
- **TypeScript**: `python scripts/generate_typescript_types.py` - Generates TypeScript types from JSON Schema

## Version Compatibility

Both packages maintain the same contract versions. Changes require version bumps and migration notes.
