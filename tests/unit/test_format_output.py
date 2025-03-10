"""Unit tests for the format_output.py module."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from scraper.format_output import format_json_file, format_word_data


class TestFormatOutput:
    """Test class for format_output.py functionality."""

    @pytest.fixture
    def sample_word_data(self):
        """Fixture providing sample word data for testing."""
        return {
            "word": "test",
            "language": "en",
            "definitions": [
                "A procedure intended to establish the quality or performance of something.",
                "A cupel or cupelling hearth in which precious metals are melted for trial and refinement.",
            ],
            "pronunciations": ["/tɛst/"],
            "examples": [
                "This is a test example.",
                "We need to test this thoroughly.",
            ],
            "related_words": ["testing", "tester"],
            "url": "https://en.wiktionary.org/wiki/test",
            "scrape_date": "2025-03-10",
        }

    @patch("scraper.format_output.re.sub")
    def test_format_word_data(self, mock_re_sub, sample_word_data):
        """Test that word data is formatted correctly."""
        # Mock the re.sub function to return the input string
        mock_re_sub.side_effect = lambda pattern, repl, string: string

        # Call the function
        formatted_output = format_word_data(sample_word_data)

        # Verify it contains expected sections
        assert "**Word:** test" in formatted_output
        assert "**Language:** en" in formatted_output
        assert "**Definitions:**" in formatted_output
        assert "**Pronunciations:**" in formatted_output
        assert "**Examples:**" in formatted_output
        assert "**Related Words:**" in formatted_output
        assert "**URL:**" in formatted_output
        assert "**Scrape Date:**" in formatted_output

    @patch("scraper.format_output.re.sub")
    def test_format_word_data_missing_fields(self, mock_re_sub):
        """Test that the formatter handles missing fields gracefully."""
        # Mock the re.sub function to return the input string
        mock_re_sub.side_effect = lambda pattern, repl, string: string

        # Word data with missing fields
        incomplete_data = {
            "word": "test",
            "language": "en",
            "definitions": ["A procedure for testing."],
            # Missing pronunciations
            # Missing examples
            # Missing related_words
            "url": "https://en.wiktionary.org/wiki/test",
            "scrape_date": "2025-03-10",
        }

        # Call the function
        formatted_output = format_word_data(incomplete_data)

        # Verify it still works and includes available data
        assert "**Word:** test" in formatted_output
        assert "**Definitions:**" in formatted_output
        assert "A procedure for testing" in formatted_output
        assert "**URL:**" in formatted_output

        # The format_word_data function does not add sections for missing fields
        # so we should NOT check for these sections

    @patch("scraper.format_output.format_word_data")
    def test_format_json_file(self, mock_format_word_data, sample_word_data):
        """Test that the JSON file formatting works correctly."""
        # Mock the format_word_data function to return a simple string
        mock_format_word_data.return_value = "Formatted word data"

        # Create a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary JSON file with sample data
            temp_json_path = os.path.join(temp_dir, "test_data.json")
            with open(temp_json_path, "w") as f:
                json.dump([sample_word_data], f)

            # Create a path for the output file
            temp_output_path = os.path.join(temp_dir, "test_output.md")

            # Call the function
            result = format_json_file(temp_json_path, temp_output_path)

            # Verify the output file was created
            assert os.path.exists(temp_output_path)

            # Verify the function returns the path to the output file
            assert result == temp_output_path

            # Verify format_word_data was called with the right data
            mock_format_word_data.assert_called_once_with(sample_word_data)
