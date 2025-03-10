#!/usr/bin/env python3
"""
Wiktionary Scraper for the Mumbl Language Processing System

This module contains a Scrapy spider for extracting linguistic data from Wiktionary.
It extracts words, definitions, pronunciations, and examples.
"""
import os
import re
import json
import time
import logging
import scrapy
import sys
from scrapy.crawler import CrawlerProcess
from scrapy.spidermiddlewares.httperror import HttpError
from twisted.internet.error import DNSLookupError, TimeoutError, TCPTimedOutError
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_connection_string, get_connection_dict
from scraper.scraper_config import (
    get_scraper_config, get_domain_for_language, 
    log_failed_page, calculate_exponential_backoff, log_progress,
    generate_word_list, get_grammar_rule_sources
)


class WiktionarySpider(scrapy.Spider):
    """Spider for scraping Wiktionary definitions."""
    name = 'wiktionary_spider'
    
    def __init__(self, language='en', words=None, output_filename=None, *args, **kwargs):
        """Initialize the spider with configuration parameters."""
        super(WiktionarySpider, self).__init__(*args, **kwargs)
        self.language = language
        self.primary_domain = f"{language}.wiktionary.org"
        self.fallback_domain = "en.wiktionary.org"  # Fallback to English if primary language is not available
        self.words = words or []
        self.word_count = 0
        self.total_words = len(self.words)
        self.output_filename = output_filename
        self.total_successes = 0
        self.total_failures = 0
        self.start_time = datetime.now()
        
        # Log basic info
        logger.info(f"Starting scraper: Target language: {language}, "
                   f"Primary domain: {self.primary_domain}, "
                   f"Fallback domain: {self.fallback_domain}")
        
        if self.total_words:
            logger.info(f"Will process up to {self.total_words} words")
    
    def start_requests(self):
        """Generate initial requests to scrape words."""
        for word in self.words:
            if word.strip():  # Skip empty words
                url = f"https://{self.primary_domain}/wiki/{word.strip()}"
                yield scrapy.Request(url, callback=self.parse, meta={'word': word.strip()})
    
    def parse(self, response):
        """Parse the Wiktionary page for the word."""
        word = response.meta.get('word', '')
        logger.info(f"Processing word: {word}")
        self.word_count += 1
        
        # Extract data
        result = self.extract_data(response, word)
        
        # Update progress
        self.update_progress()
        
        return result
        
    def extract_data(self, response, word):
        """Extract word data from the response."""
        # Initialize the data structure
        data = {
            'word': word,
            'language': self.language,
            'definitions': [],
            'pronunciations': [],
            'examples': [],
            'part_of_speech': [],
            'etymology': [],
            'related_words': [],
            'url': response.url,
            'scrape_date': datetime.now().isoformat()
        }
        
        # Extract definitions using direct extraction
        definitions = self.extract_definitions(response)
        data['definitions'] = definitions
        logger.info(f"Found {len(definitions)} definitions using direct extraction")
        
        # Clean up definitions to remove duplicates and empty entries
        cleaned_definitions = self.clean_definitions(definitions)
        data['definitions'] = cleaned_definitions
        logger.info(f"Cleaned up definitions, keeping {len(cleaned_definitions)} valid entries")
        
        # Extract pronunciations
        pronunciations = self.extract_pronunciations(response)
        data['pronunciations'] = pronunciations
        logger.info(f"Found {len(pronunciations)} unique pronunciations")
        
        # Extract examples
        examples = self.extract_examples(response)
        data['examples'] = examples
        logger.info(f"Found {len(examples)} clean examples")
        
        # Extract related words
        related_words = self.extract_related_words(response)
        if related_words:
            data['related_words'] = related_words
        else:
            logger.warning(f"No related words found for {word}")
        
        return data
    
    def clean_definitions(self, definitions):
        """Clean up definitions, remove duplicates and empty entries."""
        # Remove empty entries
        cleaned = [d for d in definitions if d.strip()]
        # Remove exact duplicates
        cleaned = list(dict.fromkeys(cleaned))
        return cleaned
    
    def extract_definitions(self, response):
        """Extract definitions from the Wiktionary page."""
        definitions = []
        
        # Extract from definition sections
        def_elements = response.css('ol > li')
        for elem in def_elements:
            # Get text directly from the list item
            def_text = elem.css('::text').getall()
            def_text = ' '.join([t.strip() for t in def_text if t.strip()])
            
            # Also get text from spans inside the list item
            span_text = elem.css('span::text').getall()
            span_text = ' '.join([t.strip() for t in span_text if t.strip()])
            
            # Combine them
            combined_text = ' '.join([t for t in [def_text, span_text] if t])
            
            if combined_text:
                definitions.append(combined_text)
        
        return definitions
    
    def extract_pronunciations(self, response):
        """Extract pronunciations from the Wiktionary page."""
        pronunciations = []
        
        # Extract IPA pronunciations (common format in Wiktionary)
        ipa_elements = response.css('span.IPA::text').getall()
        pronunciations.extend([p.strip() for p in ipa_elements if p.strip()])
        
        # Also try to get pronunciations from lists
        pron_lists = response.css('li span.IPA::text').getall()
        pronunciations.extend([p.strip() for p in pron_lists if p.strip()])
        
        # Remove duplicates
        return list(dict.fromkeys(pronunciations))
    
    def extract_examples(self, response):
        """Extract examples from the Wiktionary page."""
        examples = []
        
        # Extract examples from quotes
        quote_elements = response.css('dl dd cite::text, dl dd::text').getall()
        examples.extend([q.strip() for q in quote_elements if q.strip()])
        
        # Extract examples from usage sections
        usage_elements = response.css('div.usage-example::text').getall()
        examples.extend([u.strip() for u in usage_elements if u.strip()])
        
        # Clean examples
        cleaned_examples = []
        for example in examples:
            # Remove citation markers like [1], [2], etc.
            cleaned = re.sub(r'\[\d+\]', '', example)
            # Remove empty or too short examples
            if cleaned and len(cleaned) > 5:
                cleaned_examples.append(cleaned)
        
        return cleaned_examples
    
    def extract_related_words(self, response):
        """Extract related words from the Wiktionary page."""
        related = []
        
        # Extract from synonym/antonym sections
        related_sections = response.css('div#Synonyms, div#Antonyms, div#Related_terms')
        for section in related_sections:
            words = section.css('li a::text').getall()
            related.extend([w.strip() for w in words if w.strip()])
        
        return related
    
    def update_progress(self):
        """Update and log progress."""
        if self.total_words <= 0:
            return
            
        progress = (self.word_count / self.total_words) * 100
        
        # Calculate ETA
        elapsed = (datetime.now() - self.start_time).total_seconds()
        words_per_second = self.word_count / elapsed if elapsed > 0 else 0
        remaining_words = self.total_words - self.word_count
        eta_seconds = remaining_words / words_per_second if words_per_second > 0 else 0
        eta = str(timedelta(seconds=int(eta_seconds)))
        
        logger.info(f"[PROGRESS] {self.word_count} of {self.total_words} words processed "
                   f"({progress:.1f}% complete, ETA: {eta})")
        
    def closed(self, reason):
        """Called when the spider is closed."""
        duration = datetime.now() - self.start_time
        logger.info("="*70)
        logger.info(f"Spider closed: {reason}")
        logger.info(f"Processed {self.word_count} words with {self.total_failures} failures in {duration_to_string(duration)}")
        logger.info("="*70)


# Placeholder for future grammar rule extraction
def extract_grammar_rules(language='en', output_path='scraped_data/grammar_rules'):
    """
    Placeholder function for future implementation of grammar rule extraction.
    
    Args:
        language (str): Language code
        output_path (str): Path to save extracted grammar rules
        
    Returns:
        str: Path to the output file
    """
    logging.info(f"Grammar rule extraction for {language} is not yet implemented")
    return None


def duration_to_string(duration):
    """Convert a timedelta to a human-readable string."""
    total_seconds = duration.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes}m {seconds}s"


class FormattedWiktionarySpider(WiktionarySpider):
    """Spider for scraping Wiktionary definitions with formatted output."""
    name = 'formatted_wiktionary_spider'
    
    def __init__(self, print_formatted=False, *args, **kwargs):
        """Initialize the spider with configuration parameters."""
        super(FormattedWiktionarySpider, self).__init__(*args, **kwargs)
        self.formatted_words = []
        self.print_formatted = print_formatted
    
    def format_word_data(self, word_data):
        """Format word data into a readable markdown format."""
        formatted = []
        
        # Add word and language
        formatted.append(f"**Word:** {word_data.get('word', 'Unknown')}")
        formatted.append("")
        formatted.append(f"**Language:** {word_data.get('language', 'Unknown')}")
        formatted.append("")
        
        # Add definitions
        if word_data.get('definitions'):
            formatted.append("**Definitions:**")
            for i, definition in enumerate(word_data['definitions'][:15], 1):
                # Clean and limit length
                def_text = re.sub(r'\s+', ' ', definition).strip()
                if len(def_text) > 100:
                    def_text = def_text[:97] + "..."
                formatted.append(f"    {i}. {def_text}")
            formatted.append("")
        
        # Add pronunciations
        if word_data.get('pronunciations'):
            formatted.append("**Pronunciations:**")
            for pronunciation in word_data['pronunciations'][:10]:
                formatted.append(f"    • {pronunciation}")
            formatted.append("")
        
        # Add examples
        if word_data.get('examples'):
            formatted.append("**Examples:**")
            for example in word_data['examples'][:10]:
                example_text = re.sub(r'\s+', ' ', example).strip()
                if len(example_text) > 100:
                    example_text = example_text[:97] + "..."
                formatted.append(f"    • \"{example_text}\"")
            formatted.append("")
        
        # Add URL and scrape date
        if word_data.get('url'):
            formatted.append(f"**URL:** {word_data['url']}")
        if word_data.get('scrape_date'):
            formatted.append(f"**Scrape Date:** {word_data['scrape_date']}")
        
        return "\n".join(formatted)
    
    def parse(self, response):
        """Parse the Wiktionary page for the word."""
        word_data = super().extract_data(response, response.meta.get('word', ''))
        
        # Format the word data and store it
        formatted_data = self.format_word_data(word_data)
        self.formatted_words.append(formatted_data)
        
        # Update progress
        self.update_progress()
        
        return word_data
    
    def closed(self, reason):
        """Called when the spider is closed."""
        super().closed(reason)
        
        # Save formatted output if there is any data
        if self.formatted_words:
            # Create formatted directory
            formatted_dir = os.path.join(os.path.dirname(self.output_filename), 'formatted')
            os.makedirs(formatted_dir, exist_ok=True)
            
            # Generate output filename for formatted data
            base_filename = os.path.basename(self.output_filename)
            formatted_output = os.path.join(formatted_dir, f"{os.path.splitext(base_filename)[0]}_formatted.md")
            
            # Write to file
            with open(formatted_output, 'w', encoding='utf-8') as f:
                f.write("\n\n")
                f.write("="*80)
                f.write(f"\nFORMATTED OUTPUT FOR {self.language.upper()}\n")
                f.write("="*80)
                f.write("\n\n")
                f.write("\n\n".join(self.formatted_words))
                f.write("\n\n")
            
            logger.info(f"Formatted output saved to {formatted_output}")
            
            # Print to console if requested
            if self.print_formatted:
                print("\n\n")
                print("="*80)
                print(f"FORMATTED OUTPUT FOR {self.language.upper()}")
                print("="*80)
                print("\n\n")
                print("\n\n".join(self.formatted_words))
                print("\n\n")


def run_spider(language="en", words=None, output_dir="scraped_data", 
            formatted=False, print_output=False):
    """
    Run the Wiktionary spider to scrape word definitions.
    
    Args:
        language (str): Language code to scrape.
        words (list): List of words to scrape.
        output_dir (str): Directory to save output.
        formatted (bool): Whether to use formatted output.
        print_output (bool): Whether to print formatted output to console.
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up the output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = os.path.join(output_dir, f"wiktionary_{language}_{timestamp}.json")
    
    # Determine which spider class to use
    spider_class = FormattedWiktionarySpider if formatted else WiktionarySpider
    
    # Set up spider arguments
    spider_kwargs = {
        'language': language,
        'words': words,
        'output_filename': output_filename,
    }
    
    # Add print_formatted flag only if needed
    if formatted and print_output:
        spider_kwargs['print_formatted'] = True
    
    # Set up the crawler process
    process = CrawlerProcess(settings={
        'USER_AGENT': 'Mumbl Language Processing System Spider (educational/research use)',
        'LOG_LEVEL': 'INFO',
        'LOG_STDOUT': True,
        'FEED_URI': f'file:{output_filename}',
        'FEED_FORMAT': 'json',
        'DOWNLOAD_DELAY': 1.5,  # Be nice to the server
        'CONCURRENT_REQUESTS': 8,
        'RETRY_ENABLED': False,  # Don't retry failed requests to avoid hammering the server
    })
    
    # Start the crawler
    process.crawl(spider_class, **spider_kwargs)
    process.start()
    
    logger.info(f"Scraping completed. Data saved to {output_filename}")
    return output_filename


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Scrape Wiktionary for word definitions')
    parser.add_argument('--language', default='en', help='Language code to scrape (default: en)')
    
    # Word source - mutually exclusive
    word_source = parser.add_mutually_exclusive_group(required=True)
    word_source.add_argument('--word-list', help='File containing list of words to scrape')
    word_source.add_argument('--single-word', help='Single word to scrape')
    
    parser.add_argument('--limit', type=int, help='Maximum number of words to scrape')
    parser.add_argument('--output', default='scraped_data', help='Directory to save output (default: scraped_data)')
    parser.add_argument('--formatted', action='store_true', help='Save output in formatted markdown format')
    parser.add_argument('--print', action='store_true', help='Print formatted output to console')
    
    args = parser.parse_args()
    
    output_dir = args.output
    os.makedirs(output_dir, exist_ok=True)
    
    # Create word list to use
    words = []
    if args.word_list:
        # Load words from file
        try:
            with open(args.word_list, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(words)} words from {args.word_list}")
        except Exception as e:
            logger.error(f"Error loading word list: {e}")
            return 1
    elif args.single_word:
        # Use the single word provided
        words = [args.single_word]
        logger.info(f"Using single word: {args.single_word}")
        
    if not words:
        logger.error("No words to process. Exiting.")
        return 1
        
    if args.limit and args.limit > 0:
        words = words[:args.limit]
        
    # Run the spider with the specified arguments
    run_spider(
        language=args.language, 
        words=words, 
        output_dir=output_dir,
        formatted=args.formatted,
        print_output=args.print
    )
    
    return 0


if __name__ == "__main__":
    main() 