"""
Helper functions for the Mumbl Language Processing System.

This module contains utility functions that are used across the system.
"""
import os
import re
import json
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import psycopg2
from psycopg2.extras import DictCursor

# Import local modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_connection_dict


def setup_logger(name, log_file=None, level=logging.INFO):
    """
    Set up a logger with file and console handlers.
    
    Args:
        name (str): Name of the logger
        log_file (str): Path to log file (optional)
        level (int): Logging level
        
    Returns:
        Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log_file provided)
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_database_connection(db_config=None):
    """
    Get a connection to the database.
    
    Args:
        db_config (dict): Database connection parameters
        
    Returns:
        tuple: (Connection, Cursor) or (None, None) on error
    """
    try:
        # Get configuration
        config = db_config or get_connection_dict()
        
        # Connect to database
        conn = psycopg2.connect(**config)
        cursor = conn.cursor(cursor_factory=DictCursor)
        
        return conn, cursor
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None, None


def execute_query(query, params=None, fetchone=False, db_config=None):
    """
    Execute a database query and return results.
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters
        fetchone (bool): Whether to fetch one row or all rows
        db_config (dict): Database connection parameters
        
    Returns:
        list/dict: Query results or None on error
    """
    conn, cursor = get_database_connection(db_config)
    
    if not conn or not cursor:
        return None
    
    try:
        # Execute query
        cursor.execute(query, params or ())
        
        # Fetch results
        if fetchone:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        # Commit if not a SELECT query
        if not query.strip().upper().startswith('SELECT'):
            conn.commit()
        
        return result
    except Exception as e:
        conn.rollback()
        logging.error(f"Query execution error: {e}")
        return None
    finally:
        # Close cursor and connection
        cursor.close()
        conn.close()


def compute_hash(text):
    """
    Compute a hash for a text string.
    
    Args:
        text (str): Text to hash
        
    Returns:
        str: SHA-256 hash of the text
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize_text(text, lowercase=True, remove_punctuation=True, remove_whitespace=False):
    """
    Normalize text for comparison or analysis.
    
    Args:
        text (str): Text to normalize
        lowercase (bool): Whether to convert to lowercase
        remove_punctuation (bool): Whether to remove punctuation
        remove_whitespace (bool): Whether to remove whitespace
        
    Returns:
        str: Normalized text
    """
    if not text:
        return ""
    
    # Convert to lowercase
    if lowercase:
        text = text.lower()
    
    # Remove punctuation
    if remove_punctuation:
        text = re.sub(r'[^\w\s]', '', text)
    
    # Remove whitespace
    if remove_whitespace:
        text = re.sub(r'\s+', '', text)
    else:
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def save_json(data, filepath):
    """
    Save data to a JSON file.
    
    Args:
        data: Data to save
        filepath (str): Path to save file
        
    Returns:
        bool: Success status
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Save data to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logging.error(f"Error saving JSON file: {e}")
        return False


def load_json(filepath):
    """
    Load data from a JSON file.
    
    Args:
        filepath (str): Path to JSON file
        
    Returns:
        dict: Loaded data or None on error
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON file: {e}")
        return None


def is_valid_language_code(language_code):
    """
    Check if a language code is valid.
    
    Args:
        language_code (str): Language code to check
        
    Returns:
        bool: Whether the language code is valid
    """
    # ISO 639-1 language codes are 2 letters
    if re.match(r'^[a-z]{2}$', language_code):
        return True
    
    # ISO 639-3 language codes are 3 letters
    if re.match(r'^[a-z]{3}$', language_code):
        return True
    
    # Language-region codes (e.g., en-US, pt-BR)
    if re.match(r'^[a-z]{2}-[A-Z]{2}$', language_code):
        return True
    
    return False


def get_language_name(language_code):
    """
    Get the full name of a language from its code.
    
    Args:
        language_code (str): Language code
        
    Returns:
        str: Language name or None if not found
    """
    # Common language codes
    language_map = {
        'en': 'English',
        'es': 'Spanish',
        'fr': 'French',
        'de': 'German',
        'it': 'Italian',
        'pt': 'Portuguese',
        'ru': 'Russian',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic',
        'hi': 'Hindi',
        # Add more as needed
    }
    
    # Check the map
    if language_code in language_map:
        return language_map[language_code]
    
    # If not in map, check the database
    query = "SELECT language_name FROM languages WHERE language_code = %s"
    result = execute_query(query, (language_code,), fetchone=True)
    
    if result:
        return result['language_name']
    
    return None


def batch_process(items, process_func, batch_size=100, sleep_time=0):
    """
    Process items in batches.
    
    Args:
        items (list): Items to process
        process_func (callable): Function to process each batch
        batch_size (int): Size of each batch
        sleep_time (float): Time to sleep between batches
        
    Returns:
        list: Processing results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_result = process_func(batch)
        
        if batch_result:
            if isinstance(batch_result, list):
                results.extend(batch_result)
            else:
                results.append(batch_result)
        
        # Sleep between batches if needed
        if sleep_time > 0 and i + batch_size < len(items):
            time.sleep(sleep_time)
    
    return results


def generate_export_file(query, params=None, output_path=None, format='csv'):
    """
    Generate an export file from a database query.
    
    Args:
        query (str): SQL query to execute
        params (tuple): Query parameters
        output_path (str): Path to save the export file
        format (str): Export format ('csv', 'json', or 'excel')
        
    Returns:
        str: Path to the export file or None on error
    """
    # Execute query
    results = execute_query(query, params)
    
    if not results:
        return None
    
    # Convert to DataFrame
    df = pd.DataFrame(results)
    
    # Generate default output path if not provided
    if not output_path:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"export_{timestamp}.{format}"
        output_path = os.path.join('exports', filename)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Export based on format
    try:
        if format == 'csv':
            df.to_csv(output_path, index=False, encoding='utf-8')
        elif format == 'json':
            df.to_json(output_path, orient='records', force_ascii=False, indent=2)
        elif format == 'excel':
            df.to_excel(output_path, index=False)
        else:
            logging.error(f"Unsupported export format: {format}")
            return None
        
        return output_path
    except Exception as e:
        logging.error(f"Error generating export file: {e}")
        return None


def word_exists(word_text, language_code):
    """
    Check if a word exists in the database.
    
    Args:
        word_text (str): Word to check
        language_code (str): Language code
        
    Returns:
        bool: Whether the word exists
    """
    query = """
        SELECT w.word_id 
        FROM words w
        JOIN languages l ON w.language_id = l.language_id
        WHERE w.word_text = %s AND l.language_code = %s
    """
    
    result = execute_query(query, (word_text, language_code), fetchone=True)
    
    return result is not None


def get_word_info(word_text, language_code):
    """
    Get information about a word.
    
    Args:
        word_text (str): Word to get info for
        language_code (str): Language code
        
    Returns:
        dict: Word information or None if not found
    """
    query = """
        SELECT w.word_id, w.word_text, w.frequency_rank, w.sentence_construction_importance,
               w.conversational_utility_score, w.part_of_speech, w.etymology,
               l.language_code, l.language_name
        FROM words w
        JOIN languages l ON w.language_id = l.language_id
        WHERE w.word_text = %s AND l.language_code = %s
    """
    
    word_info = execute_query(query, (word_text, language_code), fetchone=True)
    
    if not word_info:
        return None
    
    # Get definitions
    definitions_query = """
        SELECT definition_id, definition_text, context, domain, definition_order, is_primary
        FROM definitions
        WHERE word_id = %s
        ORDER BY definition_order
    """
    
    definitions = execute_query(definitions_query, (word_info['word_id'],))
    
    # Get pronunciations
    pronunciations_query = """
        SELECT p.phonetic_id, p.ipa_pronunciation, p.pronunciation_variant, p.is_primary,
               d.dialect_name
        FROM phonetics p
        LEFT JOIN dialects d ON p.dialect_id = d.dialect_id
        WHERE p.word_id = %s
    """
    
    pronunciations = execute_query(pronunciations_query, (word_info['word_id'],))
    
    # Get example sentences
    examples_query = """
        SELECT es.sentence_id, es.sentence_text, es.complexity_score, es.tone, es.context
        FROM example_sentences es
        JOIN word_sentence_map wsm ON es.sentence_id = wsm.sentence_id
        WHERE wsm.word_id = %s
    """
    
    examples = execute_query(examples_query, (word_info['word_id'],))
    
    # Combine all information
    result = dict(word_info)
    result['definitions'] = definitions or []
    result['pronunciations'] = pronunciations or []
    result['examples'] = examples or []
    
    return result


if __name__ == "__main__":
    # Example usage
    logger = setup_logger('helpers', 'logs/helpers.log')
    logger.info("Helper module loaded")
    
    # Test database connection
    conn, cursor = get_database_connection()
    if conn and cursor:
        logger.info("Database connection successful")
        cursor.close()
        conn.close()
    else:
        logger.error("Database connection failed")
        
    # Test text normalization
    sample_text = "  This is a SAMPLE text with punctuation!   "
    normalized = normalize_text(sample_text)
    logger.info(f"Normalized text: '{normalized}'")
    
    # Test JSON operations
    test_data = {"test": "data", "sample": [1, 2, 3]}
    if save_json(test_data, "logs/test_data.json"):
        logger.info("JSON data saved successfully")
        loaded_data = load_json("logs/test_data.json")
        if loaded_data:
            logger.info("JSON data loaded successfully") 