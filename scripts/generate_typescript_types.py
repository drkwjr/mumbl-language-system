#!/usr/bin/env python3
"""
Generate TypeScript types from JSON Schema files.
"""
import json
import subprocess
import sys
from pathlib import Path

def run_command(command, cwd=None):
    """Run a shell command and return the result."""
    result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"Error running command: {command}")
        print(f"Error: {result.stderr}")
        return False
    return True

def generate_typescript_from_schema(schema_file: Path, output_dir: Path):
    """Generate TypeScript types from a JSON schema file."""
    schema_name = schema_file.stem
    output_file = output_dir / f"{schema_name}.ts"
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Use json-schema-to-typescript via npx with absolute paths
    abs_schema = schema_file.absolute()
    abs_output = output_file.absolute()
    command = f"npx json-schema-to-typescript {abs_schema} > {abs_output}"
    
    if run_command(command, cwd="packages/data-contracts/typescript"):
        print(f"Generated TypeScript types: {output_file}")
        return output_file
    else:
        print(f"Failed to generate types for {schema_file}")
        return None

def create_index_file(generated_files, output_dir: Path):
    """Create an index.ts file that exports main interfaces only."""
    index_content = [
        "// Generated TypeScript types for Mumbl data contracts",
        "// This file is auto-generated. Do not edit manually.",
        "",
        "// Main interfaces - avoiding type alias conflicts",
    ]
    
    # Only export the main interfaces to avoid type alias conflicts
    main_exports = {
        'LanguageProfileV1': 'LanguageProfileV1',
        'TextSegment': 'TextSegment', 
        'AudioSegment': 'AudioSegment',
        'SegmentScore': 'SegmentScore',
        'G2PRule': 'G2PRule',
        'G2POverride': 'G2POverride',
        'TTSDefaults': 'TTSDefaults',
        'CurationTargets': 'CurationTargets',
        'SourceRef': 'SourceRef',
        'Labels': 'Labels'
    }
    
    for file in generated_files:
        if file and file.stem in main_exports:
            interface_name = main_exports[file.stem]
            index_content.append(f"export {{ {interface_name} }} from './{file.stem}';")
    
    index_content.append("")
    
    index_file = output_dir / "index.ts"
    with open(index_file, 'w') as f:
        f.write('\n'.join(index_content))
    
    print(f"Generated index file: {index_file}")

def main():
    """Generate TypeScript types from all JSON schemas."""
    schemas_dir = Path("packages/data-contracts/typescript/schemas")
    output_dir = Path("packages/data-contracts/typescript/src")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not schemas_dir.exists():
        print(f"Error: Schemas directory {schemas_dir} does not exist")
        print("Run generate_schemas.py first to create JSON schemas")
        sys.exit(1)
    
    schema_files = list(schemas_dir.glob("*.json"))
    # Filter out index.json
    schema_files = [f for f in schema_files if f.name != "index.json"]
    
    if not schema_files:
        print(f"No schema files found in {schemas_dir}")
        sys.exit(1)
    
    print(f"Found {len(schema_files)} schema files")
    
    generated_files = []
    for schema_file in schema_files:
        result = generate_typescript_from_schema(schema_file, output_dir)
        generated_files.append(result)
    
    # Create index file
    create_index_file(generated_files, output_dir)
    
    successful_files = [f for f in generated_files if f is not None]
    print(f"\nSuccessfully generated {len(successful_files)} TypeScript type files")

if __name__ == "__main__":
    main()
