#!/usr/bin/env python3
"""
Generate JSON Schema from Pydantic models for TypeScript type generation.
"""
import json
import os
from pathlib import Path

# Add the data contracts to the path
import sys
sys.path.insert(0, 'packages/data-contracts/python/src')

from mumbl_data_contracts.profiles import LanguageProfileV1, G2PRule, G2POverride, TTSDefaults, CurationTargets
from mumbl_data_contracts.segments import TextSegment, AudioSegment, SourceRef, Labels  
from mumbl_data_contracts.scores import SegmentScore

def generate_schema_file(model_class, output_dir: Path):
    """Generate JSON schema for a Pydantic model."""
    schema = model_class.model_json_schema()
    
    # Clean up schema for better TypeScript generation
    if '$defs' in schema:
        # Move definitions to the top level and resolve references
        defs = schema.pop('$defs')
        schema['definitions'] = defs
        
        # Replace $ref paths from #/$defs/ to #/definitions/
        schema_str = json.dumps(schema)
        schema_str = schema_str.replace('"#/$defs/', '"#/definitions/')
        schema = json.loads(schema_str)
    
    output_file = output_dir / f"{model_class.__name__}.json"
    with open(output_file, 'w') as f:
        json.dump(schema, f, indent=2)
    
    print(f"Generated schema: {output_file}")
    return output_file

def main():
    """Generate all JSON schemas."""
    output_dir = Path("packages/data-contracts/typescript/schemas")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # List of models to generate schemas for
    models = [
        # Profiles
        LanguageProfileV1,
        G2PRule,
        G2POverride, 
        TTSDefaults,
        CurationTargets,
        
        # Segments
        TextSegment,
        AudioSegment,
        SourceRef,
        Labels,
        
        # Scores
        SegmentScore,
    ]
    
    generated_files = []
    for model in models:
        schema_file = generate_schema_file(model, output_dir)
        generated_files.append(schema_file)
    
    print(f"\nGenerated {len(generated_files)} schema files:")
    for file in generated_files:
        print(f"  - {file}")
    
    # Generate index file listing all schemas
    index_content = {
        "schemas": [f.name for f in generated_files],
        "models": {
            "profiles": ["LanguageProfileV1", "G2PRule", "G2POverride", "TTSDefaults", "CurationTargets"],
            "segments": ["TextSegment", "AudioSegment", "SourceRef", "Labels"],
            "scores": ["SegmentScore"]
        }
    }
    
    index_file = output_dir / "index.json"
    with open(index_file, 'w') as f:
        json.dump(index_content, f, indent=2)
    
    print(f"\nGenerated index file: {index_file}")

if __name__ == "__main__":
    main()
