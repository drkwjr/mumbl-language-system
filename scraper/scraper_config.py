"""
Configuration settings for the Mumbl Language Processing System scrapers.
"""
import os
import time
import datetime
import logging
from pathlib import Path

# Base directories
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRAPED_DATA_DIR = BASE_DIR / "scraped_data"
LOG_DIR = BASE_DIR / "logs"

# Ensure necessary directories exist
SCRAPED_DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "scraper.log")
    ]
)

# Setup failed pages logging
failed_logger = logging.getLogger('failed_pages')
failed_logger.setLevel(logging.ERROR)
failed_handler = logging.FileHandler(LOG_DIR / "failed_pages.log")
failed_handler.setFormatter(logging.Formatter('%(asctime)s - Word: %(message)s'))
failed_logger.addHandler(failed_handler)

# Scraper settings
SCRAPER_SETTINGS = {
    # Wiktionary Scraper Settings
    'wiktionary': {
        'base_domain': '{language}.wiktionary.org',  # Dynamic domain based on language
        'fallback_domain': 'en.wiktionary.org',      # Fallback domain if language-specific one fails
        'user_agent': 'Mumbl Language Processing System Spider (educational/research use)',
        'robotstxt_obey': False,  # Set to False to avoid being blocked by robots.txt since we're using word-based access
        'download_delay': 1.5,  # Seconds between requests
        'concurrent_requests': 8,
        'max_retries': 3,
        'timeout': 60,  # Seconds
        'default_language': 'en',
        'default_limit': 100,
        'output_format': 'json',
        'log_level': 'INFO',
        'priority_languages': ['en', 'es', 'fr', 'de', 'ja', 'zh'],
        'extract_fields': [
            'definitions',
            'pronunciations',
            'examples',
            'etymology',
            'part_of_speech',
            'related_words'
        ],
        # Exponential backoff settings
        'backoff_factor': 2,
        'initial_backoff': 2,  # Initial backoff in seconds
        'show_progress': True,
        'estimate_time': True,
        # New settings for word list handling
        'AUTO_GENERATE_WORDLIST': False,  # Whether to auto-generate word lists
        'REQUIRE_WORDLIST': True,  # Require a word list to be provided
    },
    
    # Dictionary.com Scraper Settings
    'dictionary_com': {
        'allowed_domains': ['dictionary.com', 'www.dictionary.com'],
        'user_agent': 'Mumbl Language Processing System Spider (educational/research use)',
        'robotstxt_obey': False,
        'download_delay': 2.0,
        'concurrent_requests': 4,
        'max_retries': 3,
        'timeout': 60,
        'output_format': 'json',
        'log_level': 'INFO',
        'backoff_factor': 2,
        'initial_backoff': 2,
        'show_progress': True,
        'estimate_time': True,
    },
    
    # WordNet Extractor Settings
    'wordnet': {
        'use_local_wordnet': True,
        'extract_relations': True,
        'extract_examples': True,
        'max_words': 10000,
        'output_format': 'json',
        'show_progress': True,
        'estimate_time': True,
    },
    
    # Grammar Rules Scraper Settings (placeholder for future implementation)
    'grammar_rules': {
        'allowed_domains': ['{language}.wiktionary.org', 'en.wiktionary.org'],
        'user_agent': 'Mumbl Language Processing System Grammar Spider (educational/research use)',
        'robotstxt_obey': True,
        'download_delay': 2.0,
        'concurrent_requests': 4,
        'max_retries': 3,
        'timeout': 60,
        'output_format': 'json',
        'log_level': 'INFO',
        'priority_languages': ['en', 'es', 'fr', 'de', 'ja', 'zh'],
        'grammar_categories': [
            'verb_conjugation',
            'noun_declension',
            'adjective_comparison',
            'syntax_patterns',
            'grammar_rules'
        ],
        'show_progress': True,
        'estimate_time': True,
    }
}

# Word list sources
WORD_LIST_SOURCES = {
    'common_english': {
        'url': 'https://raw.githubusercontent.com/first20hours/google-10000-english/master/google-10000-english-usa-no-swears.txt',
        'local_path': BASE_DIR / 'word_lists/common_english.txt',
        'description': '10,000 most common English words, no swear words'
    },
    'academic_english': {
        'url': 'https://www.academicvocabulary.info/download/awllemmas.txt',
        'local_path': BASE_DIR / 'word_lists/academic_english.txt',
        'description': 'Academic Word List'
    }
}

# Rate limiting settings
RATE_LIMITING = {
    'requests_per_minute': 20,
    'respect_robots_txt': True,
    'max_retries': 3,
    'retry_delay': 10,  # Seconds
    'exponential_backoff': True
}

# Output settings
OUTPUT_SETTINGS = {
    'default_format': 'json',
    'save_raw_html': False,
    'compress_output': True,
    'backup_previous_runs': True,
    'max_backups': 5,
    'skip_validation': True,  # Validation will be handled separately by a dedicated validation subagent.
}

# Proxy settings (if needed)
PROXY_SETTINGS = {
    'use_proxy': False,
    'proxy_list': [],
    'proxy_rotation': 'round_robin'  # or 'random'
}


def get_scraper_config(scraper_name):
    """Get configuration for a specific scraper."""
    return SCRAPER_SETTINGS.get(scraper_name, {})


def get_word_list_source(source_name):
    """Get word list source configuration."""
    return WORD_LIST_SOURCES.get(source_name, {})


def get_domain_for_language(language, scraper_name='wiktionary'):
    """
    Get the appropriate domain for a specific language.
    Falls back to the default English domain if language-specific one is not available.
    """
    config = get_scraper_config(scraper_name)
    base_domain = config.get('base_domain', '{language}.wiktionary.org')
    return base_domain.format(language=language)


def log_failed_page(word, language, reason):
    """
    Log a failed page to the failed_pages.log file.
    
    Args:
        word (str): The word that failed to be scraped
        language (str): The language of the word
        reason (str): The reason for the failure
    """
    failed_logger.error(f"'{word}' ({language}) - Error: {reason}")


def calculate_exponential_backoff(attempt, config):
    """
    Calculate the exponential backoff time for retry attempts.
    
    Args:
        attempt (int): The current attempt number (0-based)
        config (dict): Scraper configuration containing backoff settings
    
    Returns:
        float: The number of seconds to wait before retrying
    """
    factor = config.get('backoff_factor', 2)
    initial = config.get('initial_backoff', 2)
    return initial * (factor ** attempt)


def log_progress(current, total, start_time):
    """
    Log the current progress and estimate remaining time.
    
    Args:
        current (int): Current number of items processed
        total (int): Total number of items to process
        start_time (float): Time when processing started (from time.time())
    
    Returns:
        str: A message containing progress information and estimated completion time
    """
    if current <= 0 or total <= 0:
        return "Progress: 0% complete"
    
    percent_complete = (current / total) * 100
    
    elapsed = time.time() - start_time
    if current == 0:
        eta_seconds = 0
    else:
        items_per_second = current / elapsed
        remaining_items = total - current
        eta_seconds = remaining_items / items_per_second if items_per_second > 0 else 0
    
    eta = datetime.timedelta(seconds=int(eta_seconds))
    
    return f"[PROGRESS] {current} of {total} words processed ({percent_complete:.1f}% complete, ETA: {eta})"


# Command line arguments for scrapers
DEFAULT_ARGS = {
    'wiktionary': [
        '--language', 'en',
        '--limit', '100',
        '--output', str(SCRAPED_DATA_DIR / 'wiktionary')
    ],
    'dictionary_com': [
        '--limit', '100',
        '--output', str(SCRAPED_DATA_DIR / 'dictionary_com')
    ],
    'wordnet': [
        '--max-words', '1000',
        '--output', str(SCRAPED_DATA_DIR / 'wordnet'),
        '--extract-relations'
    ]
}

# Add a function for future auto-generation of word lists
def generate_word_list(language, size=1000, category='common'):
    """
    Placeholder function for future implementation of automatic word list generation.
    
    Args:
        language (str): Language code
        size (int): Number of words to generate
        category (str): Word category (common, academic, technical, etc.)
        
    Returns:
        list: List of words
    """
    logging.info(f"Auto-generation of word lists for {language} is not yet implemented")
    logging.info(f"Please provide a word list manually or use a pre-defined word list")
    return []

# Placeholder function for future grammar rule extraction
def get_grammar_rule_sources(language):
    """
    Placeholder function for future implementation of grammar rule sources.
    
    Args:
        language (str): Language code
        
    Returns:
        dict: Dictionary of grammar rule sources
    """
    return {
        'verb_conjugation': f'https://{language}.wiktionary.org/wiki/Appendix:Verbs',
        'noun_declension': f'https://{language}.wiktionary.org/wiki/Appendix:Nouns',
        'adjective_comparison': f'https://{language}.wiktionary.org/wiki/Appendix:Adjectives',
        'syntax_patterns': f'https://{language}.wiktionary.org/wiki/Appendix:Glossary',
    } 