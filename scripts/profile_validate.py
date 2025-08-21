#!/usr/bin/env python3
"""
Profile Validation CLI

A command-line tool to validate LanguageProfile JSON files using Pydantic models.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add the data contracts to the path
sys.path.insert(0, 'packages/data-contracts/python/src')

from mumbl_data_contracts.profiles import LanguageProfileV1
from pydantic import ValidationError

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File '{file_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in '{file_path}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file '{file_path}': {e}")
        sys.exit(1)

def validate_profile(data: Dict[str, Any], file_path: Path) -> bool:
    """Validate a profile data against LanguageProfileV1 model."""
    try:
        profile = LanguageProfileV1(**data)
        print(f"✅ Valid: '{file_path}' passed validation")
        print(f"   Language: {profile.language} ({profile.dialect})")
        print(f"   Version: {profile.version}")
        print(f"   Phonemes: {len(profile.phoneme_inventory)} phonemes")
        print(f"   G2P Rules: {len(profile.g2p_rules)} rules")
        print(f"   G2P Overrides: {len(profile.g2p_overrides)} overrides")
        if profile.updated_at:
            print(f"   Updated: {profile.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        return True
        
    except ValidationError as e:
        print(f"❌ Invalid: '{file_path}' failed validation")
        print("   Validation errors:")
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error['loc'])
            print(f"     • {location}: {error['msg']}")
            if 'input' in error:
                print(f"       Input value: {error['input']}")
        return False
    except Exception as e:
        print(f"❌ Error validating '{file_path}': {e}")
        return False

def validate_files(file_paths: List[Path], verbose: bool = False) -> int:
    """Validate multiple profile files and return exit code."""
    total_files = len(file_paths)
    valid_files = 0
    
    print(f"Validating {total_files} profile file(s)...\n")
    
    for file_path in file_paths:
        if verbose:
            print(f"Validating {file_path}...")
        
        data = load_json_file(file_path)
        
        if validate_profile(data, file_path):
            valid_files += 1
        
        if verbose or len(file_paths) > 1:
            print()  # Empty line between files
    
    # Summary
    print(f"Summary: {valid_files}/{total_files} files passed validation")
    
    if valid_files == total_files:
        print("🎉 All files are valid!")
        return 0
    else:
        failed_files = total_files - valid_files
        print(f"⚠️  {failed_files} file(s) failed validation")
        return 1

def create_example_profile(output_path: Path) -> None:
    """Create an example LanguageProfile JSON file."""
    example_profile = LanguageProfileV1(
        language="English",
        dialect="US", 
        script="Latin",
        version="1.0.0",
        phoneme_inventory=[
            "p", "b", "t", "d", "k", "g",
            "f", "v", "θ", "ð", "s", "z", "ʃ", "ʒ", "h",
            "m", "n", "ŋ",
            "l", "r", "j", "w",
            "i", "ɪ", "e", "ɛ", "æ", "ɑ", "ɔ", "o", "ʊ", "u",
            "ə", "ɚ", "ɝ"
        ],
        g2p_rules=[
            {
                "pattern": "tion$",
                "ipa": "ʃən",
                "priority": 10
            },
            {
                "pattern": "th",
                "ipa": "θ",
                "conditions": {"position": "initial"},
                "priority": 5
            }
        ],
        g2p_overrides=[
            {
                "word": "the",
                "ipa": "ðə",
                "notes": "Most common pronunciation"
            }
        ],
        lexicon_refs=["cmudict", "wiktionary_en"],
        register_defaults={"formal": 0.3, "informal": 0.7},
        style_tokens=["calm", "conversational", "storytelling"],
        emotion_tokens=["neutral", "excited", "reassuring"],
        fallback_chain=["English-UK", "English-CA"],
        tts_strategy="standalone"
    )
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(example_profile.model_dump(), f, indent=2, default=str)
        print(f"✅ Example profile created: {output_path}")
    except Exception as e:
        print(f"❌ Error creating example profile: {e}")
        sys.exit(1)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate LanguageProfile JSON files using Pydantic models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single profile file
  python scripts/profile_validate.py profile.json
  
  # Validate multiple files
  python scripts/profile_validate.py profile1.json profile2.json
  
  # Validate with verbose output
  python scripts/profile_validate.py -v profile.json
  
  # Create an example profile
  python scripts/profile_validate.py --create-example example_profile.json
        """
    )
    
    parser.add_argument(
        'files',
        nargs='*',
        type=Path,
        help='Profile JSON files to validate'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--create-example',
        type=Path,
        metavar='OUTPUT_FILE',
        help='Create an example LanguageProfile JSON file'
    )
    
    args = parser.parse_args()
    
    # Handle example creation
    if args.create_example:
        create_example_profile(args.create_example)
        return
    
    # Validate files
    if not args.files:
        parser.error("No files specified. Use --help for usage information.")
    
    # Check that all files exist
    for file_path in args.files:
        if not file_path.exists():
            print(f"❌ Error: File '{file_path}' does not exist")
            sys.exit(1)
    
    exit_code = validate_files(args.files, args.verbose)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
