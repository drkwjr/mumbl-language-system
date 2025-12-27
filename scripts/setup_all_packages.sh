#!/bin/bash
# Setup script to install all packages in correct order

set -e

echo "Installing Mumbl Language System packages..."
echo ""

# Get absolute path to project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT/mumbl-language-system"

# Activate virtual environment if it exists
if [ -d ".venv-310" ]; then
    source .venv-310/bin/activate
    echo "✅ Activated Python 3.10 virtual environment"
else
    echo "⚠️  Virtual environment not found. Using system Python."
fi

echo ""
echo "Phase 1: Installing core packages..."
echo ""

# Core packages first
echo "  - Installing data-contracts..."
cd packages/data-contracts/python
pip install -e . -q
cd "$PROJECT_ROOT/mumbl-language-system"

echo "  - Installing storage..."
cd packages/storage/python
pip install -e . -q
cd "$PROJECT_ROOT/mumbl-language-system"

echo ""
echo "Phase 2: Installing app packages..."
echo ""

# App packages
echo "  - Installing text-lane..."
cd apps/text-lane
pip install -e . -q || echo "    ⚠️  Text lane install had issues (may be OK)"
cd "$PROJECT_ROOT/mumbl-language-system"

echo "  - Installing audio-lane..."
cd apps/audio-lane
pip install -e . -q || echo "    ⚠️  Audio lane install had issues (may need dependencies)"
cd "$PROJECT_ROOT/mumbl-language-system"

echo "  - Installing curator..."
cd apps/curator
pip install -e . -q || echo "    ⚠️  Curator install had issues (may need dependencies)"
cd "$PROJECT_ROOT/mumbl-language-system"

echo "  - Installing tts-trainer..."
cd apps/tts-trainer
pip install -e . -q || echo "    ⚠️  TTS trainer install had issues (may need dependencies)"
cd "$PROJECT_ROOT/mumbl-language-system"

echo ""
echo "Phase 3: Installing orchestration..."
echo ""

# Orchestration package
echo "  - Installing orchestration..."
cd packages/orchestration/python
pip install -e . -q
cd "$PROJECT_ROOT/mumbl-language-system"

echo ""
echo "Phase 4: Verifying installations..."
echo ""

# Verify imports
python3 << 'EOF'
import sys
errors = []

try:
    from mumbl_data_contracts.segments import TextSegment, AudioSegment
    print("✅ mumbl-data-contracts")
except Exception as e:
    errors.append(f"mumbl-data-contracts: {e}")

try:
    from mumbl_storage.repositories import TextSegmentRepository
    print("✅ mumbl-storage")
except Exception as e:
    errors.append(f"mumbl-storage: {e}")

try:
    from audio_lane.processor import AudioLaneProcessor
    print("✅ audio-lane")
except Exception as e:
    errors.append(f"audio-lane: {e}")

try:
    from curator.processor import CuratorProcessor
    print("✅ curator")
except Exception as e:
    errors.append(f"curator: {e}")

try:
    from tts_trainer.trainer import TTSTrainer
    print("✅ tts-trainer")
except Exception as e:
    errors.append(f"tts-trainer: {e}")

try:
    from mumbl_orchestration.flows_audio import audio_lane_flow
    from mumbl_orchestration.flows_curator import curator_flow
    from mumbl_orchestration.flows_tts import tts_training_flow
    print("✅ orchestration flows")
except Exception as e:
    errors.append(f"orchestration: {e}")

if errors:
    print("\n⚠️  Some imports failed:")
    for err in errors:
        print(f"   - {err}")
    sys.exit(1)
else:
    print("\n✅ All packages installed and importable!")
EOF

echo ""
echo "Done! All packages installed."

