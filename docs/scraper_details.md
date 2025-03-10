# Scraper Documentation

## Overview

The Mumbl Language Processing System includes a powerful web scraping component built on Scrapy for extracting linguistic data from various online sources. This document details the scraper architecture, capabilities, and usage.

## Scraper Architecture

The scraper component is designed with flexibility and extensibility in mind, allowing for the collection of data from multiple sources. The primary components are:

### 1. Wiktionary Scraper

The `wiktionary_scraper.py` module contains a Scrapy spider specifically designed to extract linguistic data from Wiktionary. It can extract:

- Words and their properties
- Multiple definitions
- IPA pronunciations
- Example sentences
- Etymology information
- Related words

### 2. Configuration System

The `scraper_config.py` module provides a centralized configuration system for the scrapers, including:

- User agent settings
- Request rate limiting
- Output formats and locations
- Source-specific settings
- Word list sources

## Data Extraction Process

The general process for data extraction is:

1. **Spider Initialization**: The spider is initialized with parameters such as target language, word limit, and optional word list
2. **Page Traversal**: The spider navigates through Wiktionary pages, either following a predefined word list or discovering words through links
3. **Data Extraction**: For each word page, the spider extracts structured data using CSS selectors and regular expressions
4. **Data Transformation**: Extracted data is cleaned, normalized, and transformed into a consistent structure
5. **Data Storage**: Processed data is saved to JSON files and can later be imported into the database

## Scraper Features

### Word List Processing

The scraper can process a list of words provided in a text file, allowing for targeted scraping of specific vocabulary. This is useful for:

- Extracting information for high-frequency words
- Focusing on domain-specific terminology
- Updating information for a specific subset of words

### Language Filtering

The scraper can target specific languages, allowing for the collection of monolingual or multilingual data as needed.

### Rate Limiting and Ethical Scraping

The scraper implements several features to ensure ethical and responsible web scraping:

- Respects robots.txt directives
- Implements configurable request delays
- Uses a descriptive user agent identifying the project
- Limits the number of requests per session

### Extensible Output

The scraped data is saved in a structured JSON format that contains:

```json
{
  "word": "example",
  "language": "English",
  "timestamp": "2023-05-01T12:34:56",
  "url": "https://en.wiktionary.org/wiki/example",
  "definitions": [
    {
      "definition_text": "Something that serves to illustrate or explain a rule.",
      "part_of_speech": "Noun",
      "order": 1
    }
  ],
  "pronunciations": [
    {
      "ipa": "ɪɡˈzæmpəl",
      "dialect": "General American"
    }
  ],
  "examples": [
    {
      "example_text": "This is an example of a sentence.",
      "part_of_speech": "Noun"
    }
  ],
  "etymology": "From Middle English, from Old French...",
  "related_words": ["sample", "exemplar", "exemplify"]
}
```

## Running the Scraper

### Basic Usage

To run the Wiktionary scraper with default settings:

```bash
python scraper/wiktionary_scraper.py
```

### Advanced Usage

For more control over the scraping process:

```bash
python scraper/wiktionary_scraper.py --language en --limit 1000 --word-list word_lists/common_english.txt --output scraped_data/english
```

Parameters:
- `--language`: Language code to scrape (default: en)
- `--word-list`: Path to file containing words to scrape (one per line)
- `--limit`: Maximum number of words to scrape (default: 100)
- `--output`: Output directory (default: scraped_data)

## Integrating New Data Sources

The scraper architecture is designed to be extensible. To add a new data source:

1. Create a new spider class in the `scraper` directory
2. Implement the data extraction logic specific to the new source
3. Add configuration settings to `scraper_config.py`
4. Ensure the output format is compatible with the database import process

## Data Quality Considerations

The scraper includes several mechanisms to ensure data quality:

- **Pattern Validation**: Extracted data is validated against expected patterns
- **Empty Value Handling**: Proper handling of missing or empty values
- **Error Recovery**: The spider can continue operation even if individual page scraping fails
- **Logging**: Comprehensive logging of the scraping process

## Future Enhancements

Planned enhancements to the scraper component include:

- **Multi-source Integration**: Combining data from multiple sources for more comprehensive coverage
- **Incremental Updates**: Updating only changed content rather than full re-scraping
- **Machine Learning Augmentation**: Using ML to improve data extraction accuracy
- **Real-time Database Integration**: Direct database updates during scraping

## Troubleshooting

Common issues and their solutions:

### Rate Limiting

If you encounter HTTP 429 (Too Many Requests) errors, adjust the `download_delay` setting in `scraper_config.py` to a higher value.

### Parsing Errors

If the scraper fails to extract data correctly, it may be due to changes in the source website's structure. Check the CSS selectors and update them as needed.

### Memory Issues

For large scraping jobs, the spider might consume significant memory. Use the `--limit` parameter to control the scope of the scraping task. 