# Wiktionary Scraper

This directory contains scripts for scraping word definitions, pronunciations, examples, and other linguistic data from Wiktionary.

## Features

- Scrape word definitions, pronunciations, examples, and related words from Wiktionary
- Support for scraping from a word list file or a single word
- Formatted output in both JSON and Markdown formats
- Progress tracking and ETA estimation
- Configurable limits on the number of words to scrape

## Scripts

### wiktionary_scraper.py

The main scraper script that extracts data from Wiktionary.

```bash
# Scrape a single word
python wiktionary_scraper.py --single-word "example" --language en

# Scrape words from a word list file
python wiktionary_scraper.py --word-list word_lists/test_words.txt --language en --limit 10

# Generate formatted output
python wiktionary_scraper.py --word-list word_lists/test_words.txt --formatted --print
```

### format_output.py

A standalone script for formatting JSON output from the scraper into readable Markdown.

```bash
# Format a JSON file and print to console
python format_output.py scraped_data/wiktionary_en_YYYYMMDD_HHMMSS.json --print

# Format a JSON file and save to a specific output file
python format_output.py scraped_data/wiktionary_en_YYYYMMDD_HHMMSS.json --output formatted_output.md
```

### scrape_and_format.py

A combined script that runs the scraper and formatter in one command.

```bash
# Scrape a single word and format the output
python scrape_and_format.py --single-word "example" --print

# Scrape words from a word list file and format the output
python scrape_and_format.py --word-list word_lists/test_words.txt --limit 10 --print
```

## Command-line Arguments

### wiktionary_scraper.py

- `--language`: Language code to scrape (default: en)
- `--word-list`: File containing list of words to scrape
- `--single-word`: Single word to scrape
- `--limit`: Maximum number of words to scrape
- `--output`: Directory to save output (default: scraped_data)
- `--formatted`: Save output in formatted markdown format
- `--print`: Print formatted output to console

### format_output.py

- `input_file`: JSON file to format
- `--output`: Output file for formatted data (default: input_file_formatted.md)
- `--print`: Print formatted output to console

### scrape_and_format.py

- `--language`: Language code to scrape (default: en)
- `--word-list`: File containing list of words to scrape
- `--single-word`: Single word to scrape
- `--limit`: Maximum number of words to scrape
- `--output`: Directory to save output (default: scraped_data)
- `--print`: Print formatted output to console

## Output Format

### JSON Format

The scraper outputs data in JSON format with the following structure:

```json
[
  {
    "word": "example",
    "language": "en",
    "definitions": ["Definition 1", "Definition 2", ...],
    "pronunciations": ["/ɪɡˈzɑːm.pəl/", ...],
    "examples": ["Example 1", "Example 2", ...],
    "part_of_speech": ["noun", "verb", ...],
    "etymology": ["Etymology information"],
    "related_words": ["Related word 1", "Related word 2", ...],
    "url": "https://en.wiktionary.org/wiki/example",
    "scrape_date": "2025-03-10T12:55:08.742853"
  },
  ...
]
```

### Markdown Format

The formatter converts the JSON data into a readable Markdown format:

```markdown
**Word:** example

**Language:** en

**Definitions:**
    1. Definition 1
    2. Definition 2
    ...

**Pronunciations:**
    • /ɪɡˈzɑːm.pəl/
    • ...

**Examples:**
    • "Example 1"
    • "Example 2"
    • ...

**URL:** https://en.wiktionary.org/wiki/example
**Scrape Date:** 2025-03-10T12:55:08.742853

---
```

## Output Files

- JSON files are saved to the `scraped_data` directory with a timestamp in the filename
- Formatted Markdown files are saved to the `scraped_data/formatted` directory with the same base filename plus `_formatted.md` 