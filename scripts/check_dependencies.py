#!/usr/bin/env python3
"""
Dependency check script.

Verifies all required packages are installed and reports missing ones.
"""

import importlib
import sys

REQUIRED_PACKAGES = {
    # Core packages
    "mumbl_data_contracts": "pip install -e packages/data-contracts/python",
    "mumbl_storage": "pip install -e packages/storage/python",
    # Audio Lane dependencies
    "yt_dlp": "pip install yt-dlp",
    "librosa": "pip install librosa",
    "soundfile": "pip install soundfile",
    "pyannote": "pip install pyannote.audio",
    "torch": "pip install torch",
    # Curator dependencies
    "sentence_transformers": "pip install sentence-transformers",
    # TTS Trainer dependencies
    "yaml": "pip install pyyaml",
    # App packages
    "audio_lane": "pip install -e apps/audio-lane",
    "curator": "pip install -e apps/curator",
    "tts_trainer": "pip install -e apps/tts-trainer",
    # Orchestration
    "mumbl_orchestration": "pip install -e packages/orchestration/python",
}

OPTIONAL_PACKAGES = {
    "prefect": "pip install prefect",
    "openai": "pip install openai",
    "pytest": "pip install pytest",
}


def check_package(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name

    try:
        importlib.import_module(import_name)
        return True, None
    except ImportError as e:
        return False, str(e)


def main():
    """Check all dependencies."""
    print("Checking Mumbl Language System dependencies...")
    print("=" * 70)
    print()

    missing_required = []
    missing_optional = []

    # Check required packages
    print("Required Packages:")
    print("-" * 70)
    for package, install_cmd in REQUIRED_PACKAGES.items():
        is_installed, error = check_package(package)
        if is_installed:
            print(f"✅ {package:30s} installed")
        else:
            print(f"❌ {package:30s} MISSING")
            print(f"   Install: {install_cmd}")
            missing_required.append((package, install_cmd))
    print()

    # Check optional packages
    print("Optional Packages:")
    print("-" * 70)
    for package, install_cmd in OPTIONAL_PACKAGES.items():
        is_installed, error = check_package(package)
        if is_installed:
            print(f"✅ {package:30s} installed")
        else:
            print(f"⚠️  {package:30s} not installed (optional)")
            missing_optional.append((package, install_cmd))
    print()

    # Summary
    print("=" * 70)
    if missing_required:
        print(f"❌ {len(missing_required)} required packages missing")
        print()
        print("To install all missing packages, run:")
        print("  ./scripts/setup_all_packages.sh")
        print()
        for package, install_cmd in missing_required:
            print(f"  {install_cmd}")
        sys.exit(1)
    else:
        print("✅ All required packages installed!")
        if missing_optional:
            print(f"⚠️  {len(missing_optional)} optional packages not installed")
        sys.exit(0)


if __name__ == "__main__":
    main()
