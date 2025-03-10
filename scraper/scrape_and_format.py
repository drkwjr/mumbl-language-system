#!/usr/bin/env python3
"""
scrape_and_format.py - Combined scraper and formatter for Wiktionary

This script runs the Wiktionary scraper and then automatically formats the output,
providing a one-stop solution for generating nicely formatted Wiktionary data.

Usage:
  python scrape_and_format.py --language en --word-list word_lists/test_words.txt --limit 10 [--print]

Options:
  --language LANG       Language code to scrape (default: en)
  --word-list FILE      File containing list of words to scrape
  --single-word WORD    Single word to scrape instead of using a word list
  --limit N             Maximum number of words to scrape (default: no limit)
  --output DIR          Directory to save output (default: scraped_data)
  --print               Print formatted output to console
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Ensure we can import from the scraper directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import formatter
from format_output import format_json_file


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Run Wiktionary scraper and formatter')
    
    # Scraper arguments
    parser.add_argument('--language', default='en', help='Language code to scrape (default: en)')
    
    # Word source - mutually exclusive
    word_source = parser.add_mutually_exclusive_group(required=True)
    word_source.add_argument('--word-list', help='File containing list of words to scrape')
    word_source.add_argument('--single-word', help='Single word to scrape')
    
    parser.add_argument('--limit', type=int, help='Maximum number of words to scrape')
    parser.add_argument('--output', default='scraped_data', help='Directory to save output (default: scraped_data)')
    parser.add_argument('--print', action='store_true', help='Print formatted output to console')
    
    args = parser.parse_args()
    
    # Build the scraper command
    cmd = [
        'python',
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wiktionary_scraper.py'),
        '--language', args.language,
        '--output', args.output
    ]
    
    if args.word_list:
        cmd.extend(['--word-list', args.word_list])
    elif args.single_word:
        cmd.extend(['--single-word', args.single_word])
    
    if args.limit:
        cmd.extend(['--limit', str(args.limit)])
    
    # Run the scraper
    print(f"Running scraper with command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Error running scraper: {result.stderr}", file=sys.stderr)
        return result.returncode
    
    # Extract the output JSON file path from the scraper output
    output_file = None
    for line in result.stdout.split('\n'):
        if "Stored json feed" in line and "scraped_data/wiktionary_" in line:
            # Extract filename from the log line
            parts = line.split("scraped_data/")
            if len(parts) > 1:
                filename = parts[1].split(" ")[0].strip().rstrip('.')
                output_file = os.path.join(args.output, filename)
                break
    
    # If we can't find the output file from logs, try to find the most recent one
    if not output_file:
        # Find the most recent json file in the output directory
        output_dir = Path(args.output)
        json_files = list(output_dir.glob('wiktionary_*.json'))
        if json_files:
            # Sort by modification time, newest first
            output_file = str(sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[0])
    
    if not output_file:
        print("Could not determine output file from scraper. Aborting.", file=sys.stderr)
        return 1
    
    print(f"Scraper completed successfully. Output saved to: {output_file}")
    
    # Format the output
    print(f"Formatting output file: {output_file}")
    
    # Generate output filename for formatted data
    formatted_dir = os.path.join(args.output, 'formatted')
    os.makedirs(formatted_dir, exist_ok=True)
    
    # Extract the base filename without path or extension
    base_filename = os.path.basename(output_file)
    formatted_output = os.path.join(formatted_dir, f"{os.path.splitext(base_filename)[0]}_formatted.md")
    
    # Format the JSON file
    format_json_file(output_file, formatted_output, print_output=args.print)
    
    print(f"Formatting completed. Formatted output saved to: {formatted_output}")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 