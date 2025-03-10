#!/usr/bin/env python
"""Script to run all code quality checks and tests."""
import os
import subprocess
import sys
from pathlib import Path

# Define colors for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_header(message):
    """Print a formatted header message."""
    print(f"\n{BOLD}{YELLOW}{'=' * 80}{RESET}")
    print(f"{BOLD}{YELLOW}= {message}{RESET}")
    print(f"{BOLD}{YELLOW}{'=' * 80}{RESET}\n")


def run_command(command, description):
    """Run a command and print its output."""
    print_header(description)
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"{RED}{result.stderr}{RESET}")
    return result.returncode


def main():
    """Run all code quality checks and tests."""
    # Change to the project root directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Track if any checks fail
    failed = False

    # Run isort check
    if run_command("isort --check-only --diff .", "Checking import sorting with isort") != 0:
        failed = True
        print(f"{RED}isort check failed. Run 'isort .' to fix import sorting.{RESET}")

    # Run black check
    if run_command("black --check .", "Checking code formatting with black") != 0:
        failed = True
        print(f"{RED}black check failed. Run 'black .' to fix code formatting.{RESET}")

    # Run flake8
    if run_command("flake8", "Checking code style with flake8") != 0:
        failed = True
        print(f"{RED}flake8 check failed. Please fix the style issues.{RESET}")

    # Run unit tests
    if run_command("pytest tests/unit -v", "Running unit tests") != 0:
        failed = True
        print(f"{RED}Unit tests failed.{RESET}")

    # Run integration tests if requested
    if "--integration" in sys.argv:
        if run_command("pytest tests/integration -v", "Running integration tests") != 0:
            failed = True
            print(f"{RED}Integration tests failed.{RESET}")

    # Print summary
    if failed:
        print(f"\n{RED}{BOLD}Some checks failed. Please fix the issues before committing.{RESET}")
        return 1
    else:
        print(f"\n{GREEN}{BOLD}All checks passed!{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
