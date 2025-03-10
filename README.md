# Mumbl Language System

A comprehensive system for collecting, processing, and managing linguistic data.

## Overview

The Mumbl Language System is designed to facilitate the collection, processing, and management of linguistic data from various sources. The system currently includes a Wiktionary scraper with formatting capabilities and plans for manual data upload features.

## Features

### Wiktionary Scraper

- Scrapes linguistic data (definitions, pronunciations, examples, etc.) from Wiktionary
- Supports scraping from both word lists and single words
- Formats output in both JSON and Markdown
- Includes progress tracking with ETA
- Configurable limits for scraping

### Planned Features

- Manual data upload capabilities
- Advanced data processing and analysis
- Database integration for structured storage
- API for accessing the linguistic data

## Project Structure

```
mumbl-language-system/
├── scraper/                  # Wiktionary scraper module
│   ├── wiktionary_scraper.py # Main scraper script
│   ├── format_output.py      # Formatting script for JSON output
│   ├── scrape_and_format.py  # Combined script for scraping and formatting
│   ├── scraper_config.py     # Configuration settings for the scraper
│   └── README.md             # Documentation for the scraper
├── word_lists/               # Lists of words for scraping
├── scraped_data/             # Output directory for scraped data
│   └── formatted/            # Formatted markdown output
├── database/                 # Database module (future)
├── docs/                     # Documentation
└── utils/                    # Utility functions
```

## Getting Started

### Prerequisites

- Python 3.6 or higher
- Required Python packages (see requirements.txt)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/drkwjr/mumbl-language-system.git
   cd mumbl-language-system
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

### Usage

#### Wiktionary Scraper

To use the Wiktionary scraper with a word list:

```
python scraper/scrape_and_format.py --word-list word_lists/your_wordlist.txt --print
```

To scrape a single word:

```
python scraper/scrape_and_format.py --single-word "example" --print
```

For more options, see the documentation in `scraper/README.md`.

## Development

This project uses a branching strategy with:
- `main` - The main branch containing stable code
- `dev` - Development branch for ongoing work
- `prod` - Production branch for released versions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions or suggestions, please open an issue on GitHub. 