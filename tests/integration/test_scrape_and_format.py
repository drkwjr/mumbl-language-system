"""Integration tests for the scrape_and_format.py script."""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestScrapeAndFormat:
    """Integration tests for the scrape_and_format.py script."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_scrape_and_format_single_word(self):
        """Test the scrape_and_format.py script with a single word."""
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Run the script with a single word
            result = subprocess.run(
                [
                    "python",
                    "scraper/scrape_and_format.py",
                    "--single-word",
                    "test",
                    "--output",
                    temp_dir,
                    "--limit",
                    "1",
                ],
                capture_output=True,
                text=True,
            )

            # Check that the script ran successfully
            assert result.returncode == 0

            # Check that the output mentions the expected files
            assert "Scraping completed" in result.stdout
            assert "Formatting completed" in result.stdout

            # Check that the output files exist
            json_files = list(Path(temp_dir).glob("*.json"))
            assert len(json_files) > 0

            formatted_dir = os.path.join(temp_dir, "formatted")
            assert os.path.exists(formatted_dir)

            md_files = list(Path(formatted_dir).glob("*.md"))
            assert len(md_files) > 0

    @pytest.mark.integration
    @pytest.mark.slow
    def test_scrape_and_format_word_list(self):
        """Test the scrape_and_format.py script with a word list."""
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary word list file
            word_list_path = os.path.join(temp_dir, "words.txt")
            with open(word_list_path, "w") as f:
                f.write("test\ncat\n")

            # Run the script with the word list
            result = subprocess.run(
                [
                    "python",
                    "scraper/scrape_and_format.py",
                    "--word-list",
                    word_list_path,
                    "--output",
                    temp_dir,
                    "--limit",
                    "2",
                ],
                capture_output=True,
                text=True,
            )

            # Check that the script ran successfully
            assert result.returncode == 0

            # Check that the output mentions the expected files
            assert "Scraping completed" in result.stdout
            assert "Formatting completed" in result.stdout

            # Check that the output files exist
            json_files = list(Path(temp_dir).glob("*.json"))
            assert len(json_files) > 0

            formatted_dir = os.path.join(temp_dir, "formatted")
            assert os.path.exists(formatted_dir)

            md_files = list(Path(formatted_dir).glob("*.md"))
            assert len(md_files) > 0

    @pytest.mark.integration
    def test_scrape_and_format_help(self):
        """Test the scrape_and_format.py script help output."""
        # Run the script with --help
        result = subprocess.run(
            ["python", "scraper/scrape_and_format.py", "--help"],
            capture_output=True,
            text=True,
        )

        # Check that the script ran successfully
        assert result.returncode == 0

        # Check that the help output contains expected options
        assert "--single-word" in result.stdout
        assert "--word-list" in result.stdout
        assert "--output" in result.stdout
        assert "--limit" in result.stdout
        assert "--print" in result.stdout
