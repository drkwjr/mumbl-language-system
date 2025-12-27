#!/usr/bin/env python3
"""Verify local runtime dependencies for radio ingestion."""

import shutil
import sys


REQUIRED_COMMANDS = [
    "ffmpeg",
]

PYTHON_IMPORTS = [
    ("torch", "torch"),
    ("speechbrain", "speechbrain"),
    ("webrtcvad", "webrtcvad"),
]


def check_commands() -> int:
    missing = []
    for command in REQUIRED_COMMANDS:
        if shutil.which(command) is None:
            missing.append(command)
    if missing:
        print("Missing system commands:")
        for cmd in missing:
            print(f"- {cmd}")
        return 1
    print("System commands OK.")
    return 0


def check_python_imports() -> int:
    missing = []
    for module_name, label in PYTHON_IMPORTS:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(label)
    if missing:
        print("Missing Python packages:")
        for pkg in missing:
            print(f"- {pkg}")
        return 1
    print("Python packages OK.")
    return 0


def main() -> int:
    exit_code = 0
    if check_commands() != 0:
        exit_code = 1
    if check_python_imports() != 0:
        exit_code = 1
    if exit_code == 0:
        print("Ingest dependency check passed.")
    else:
        print("Ingest dependency check failed.")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
