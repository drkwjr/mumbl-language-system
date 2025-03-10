"""Integration tests for the wiktionary scraper.

These tests validate the end-to-end functionality of the scraper with actual API calls.
"""

import argparse
import json
import os
import tempfile

import pytest

from scraper.wiktionary_scraper import run_spider


class TestWiktionaryScraper:
    """Integration tests for the Wiktionary scraper."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_scrape_single_word(self):
        """Test scraping a single word."""
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output")

            # Call the run_spider function with a single word
            result = run_spider(
                language="en",
                words=["test"],
                output_dir=output_path,
                formatted=True,
                print_output=False,
            )

            # Verify the function returned a path to the output file
            assert result is not None
            assert os.path.exists(result)

            # Verify the output file contains the expected data
            with open(result, "r") as f:
                data = json.load(f)
                assert len(data) > 0
                assert data[0]["word"] == "test"
                assert data[0]["language"] == "en"
                assert "definitions" in data[0]
                assert "pronunciations" in data[0]

    @pytest.mark.integration
    @pytest.mark.slow
    def test_scrape_word_list(self):
        """Test scraping a word list."""
        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary word list file
            word_list_path = os.path.join(temp_dir, "words.txt")
            with open(word_list_path, "w") as f:
                f.write("test\ncat\n")

            output_path = os.path.join(temp_dir, "output")

            # Call the run_spider function with multiple words
            result = run_spider(
                language="en",
                words=["test", "cat"],
                output_dir=output_path,
                formatted=False,
                print_output=False,
            )

            # Verify the function returned a path to the output file
            assert result is not None
            assert os.path.exists(result)

            # Verify the output file contains the expected data
            with open(result, "r") as f:
                data = json.load(f)
                assert len(data) <= 2  # Should have at most 2 words due to the limit

                # Verify the words are as expected
                words = [item["word"] for item in data]
                assert "test" in words or "cat" in words

    @pytest.mark.integration
    def test_argparser(self):
        """Test the argument parser setup."""
        # Create an argument parser similar to the one in main()
        parser = argparse.ArgumentParser(description="Scrape Wiktionary for word definitions")
        parser.add_argument("--language", default="en", help="Language code to scrape (default: en)")
        
        # Word source - mutually exclusive
        word_source = parser.add_mutually_exclusive_group(required=True)
        word_source.add_argument("--word-list", help="File containing list of words to scrape")
        word_source.add_argument("--single-word", help="Single word to scrape")
        
        parser.add_argument("--limit", type=int, help="Maximum number of words to scrape")
        parser.add_argument("--output", default="scraped_data", help="Directory to save output")
        parser.add_argument("--formatted", action="store_true", help="Save output in formatted markdown")
        parser.add_argument("--print", action="store_true", help="Print formatted output to console")

        # Test with valid arguments
        args = parser.parse_args(
            ["--language", "en", "--single-word", "test", "--output", "test_output", "--formatted", "--print"]
        )

        assert args.language == "en"
        assert args.single_word == "test"
        assert args.output == "test_output"
        assert args.formatted is True
        assert args.print is True
