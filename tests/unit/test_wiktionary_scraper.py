"""Unit tests for the wiktionary_scraper.py module using mocks to avoid API calls."""

import argparse
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from scraper.wiktionary_scraper import run_spider


class TestWiktionaryScraper:
    """Unit tests for the Wiktionary scraper using mocks."""

    @pytest.fixture
    def mock_process(self):
        """Fixture providing a mock CrawlerProcess."""
        mock = MagicMock()
        mock.crawl.return_value = None
        mock.start.return_value = None
        return mock

    @patch("scraper.wiktionary_scraper.CrawlerProcess")
    @patch("scraper.wiktionary_scraper.datetime")
    def test_run_spider_single_word(self, mock_datetime, mock_crawler_process, mock_process):
        """Test running the spider with a single word."""
        # Mock the datetime to return a fixed value for the output filename
        mock_datetime.now.return_value.strftime.return_value = "20250310_123456"
        
        # Setup the mock
        mock_crawler_process.return_value = mock_process

        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Expected output file based on the mocked datetime
            expected_output = os.path.join(temp_dir, "wiktionary_en_20250310_123456.json")
            
            # Call the function
            result = run_spider(
                language="en",
                words=["test"],
                output_dir=temp_dir,
                formatted=False,
                print_output=False,
            )

            # Verify the function was called with the right parameters
            mock_crawler_process.assert_called_once()
            mock_process.crawl.assert_called_once()

            # Verify the result is the expected path
            assert result == expected_output

    @patch("scraper.wiktionary_scraper.CrawlerProcess")
    @patch("scraper.wiktionary_scraper.datetime")
    def test_run_spider_word_list(self, mock_datetime, mock_crawler_process, mock_process):
        """Test running the spider with a word list."""
        # Mock the datetime to return a fixed value for the output filename
        mock_datetime.now.return_value.strftime.return_value = "20250310_123456"
        
        # Setup the mock
        mock_crawler_process.return_value = mock_process

        # Create a temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary word list file
            word_list_path = os.path.join(temp_dir, "words.txt")
            with open(word_list_path, "w") as f:
                f.write("test\ncat\n")

            # Expected output file based on the mocked datetime
            expected_output = os.path.join(temp_dir, "wiktionary_en_20250310_123456.json")

            # Call the function
            result = run_spider(
                language="en",
                words=["test", "cat"],
                output_dir=temp_dir,
                formatted=False,
                print_output=False,
            )

            # Verify the function was called with the right parameters
            mock_crawler_process.assert_called_once()
            mock_process.crawl.assert_called_once()

            # Verify the result is the expected path
            assert result == expected_output

    def test_argparser(self):
        """Test the argument parser setup with various combinations."""
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

        # Test with single word
        args = parser.parse_args(["--language", "en", "--single-word", "test"])
        assert args.language == "en"
        assert args.single_word == "test"
        assert args.word_list is None

        # Test with word list
        args = parser.parse_args(["--language", "en", "--word-list", "words.txt"])
        assert args.language == "en"
        assert args.word_list == "words.txt"
        assert args.single_word is None

        # Test with limit
        args = parser.parse_args(["--language", "en", "--single-word", "test", "--limit", "5"])
        assert args.language == "en"
        assert args.limit == 5
