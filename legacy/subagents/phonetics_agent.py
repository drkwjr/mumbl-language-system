"""
Phonetics Subagent for the Mumbl Language Processing System

This module processes phonetic information, including IPA pronunciation
and dialect variations. It normalizes IPA notation, analyzes pronunciation
patterns, and helps identify phonological rules.
"""
import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor

# Import local modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_connection_dict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/phonetics_agent_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('phonetics_agent')

# IPA normalization mapping
IPA_NORMALIZATION = {
    # Vowels
    'ɑ': 'ɑ',  # Open back unrounded
    'æ': 'æ',  # Near-open front unrounded
    'ɐ': 'ɐ',  # Near-open central
    'ə': 'ə',  # Mid central (schwa)
    'ɚ': 'əɹ',  # R-colored schwa
    # Consonants 
    'ʃ': 'ʃ',  # Voiceless postalveolar fricative
    'ʒ': 'ʒ',  # Voiced postalveolar fricative
    'θ': 'θ',  # Voiceless dental fricative
    'ð': 'ð',  # Voiced dental fricative
    # Add more mappings as needed
}

# Dialect-specific pronunciation patterns
DIALECT_PATTERNS = {
    'American': {
        'rhoticity': True,  # Pronounces 'r' in all positions
        'patterns': {
            r't(?=n)': 't|ʔ',  # 't' can be glottalized before 'n'
            r'nt(?=\w)': 'n(t)|ʔ',  # 'nt' can be glottalized
            r'æ(?=([mnŋ][dk]))|æ(?=[sk]|sp)': 'æ|eə',  # 'æ' can be tensed
        }
    },
    'British': {
        'rhoticity': False,  # Only pronounces 'r' before vowels
        'patterns': {
            r'ɑː': 'ɑː',  # Long 'a' in words like 'bath'
            r't(?=\w)': 't',  # No flapping of 't'
            r'ju(?=\w)': 'ju|u',  # 'u' can lose its 'y' sound
        }
    },
    'Australian': {
        'rhoticity': False,  # Non-rhotic like British
        'patterns': {
            r'eɪ': 'æɪ',  # 'Day' sounds more like 'dye'
            r'aɪ': 'ɑɪ',  # 'High' with a broader first element
            r'əʊ': 'əʉ',  # 'Go' with a fronted second element
        }
    },
}


class PhoneticsAgent:
    """
    Agent for processing phonetic information in the language database.
    
    This agent handles:
    1. Normalization of IPA pronunciations
    2. Dialect variation analysis
    3. Audio file path management
    4. Phonological pattern extraction
    """
    
    def __init__(self, db_config=None):
        """
        Initialize the phonetics agent.
        
        Args:
            db_config (dict): Database connection parameters
        """
        self.db_config = db_config or get_connection_dict()
        self.conn = None
        self.cursor = None
    
    def connect_to_db(self):
        """Establish a connection to the database."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.cursor = self.conn.cursor(cursor_factory=DictCursor)
            logger.info("Connected to database successfully")
            return True
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            return False
    
    def close_connection(self):
        """Close the database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")
    
    def normalize_ipa(self, ipa_string):
        """
        Normalize IPA pronunciation by applying standard conventions.
        
        Args:
            ipa_string (str): IPA pronunciation string
            
        Returns:
            str: Normalized IPA string
        """
        if not ipa_string:
            return None
            
        # Remove enclosing slashes or brackets if present
        ipa_string = re.sub(r'^[/\[\(]|[/\]\)]$', '', ipa_string)
        
        # Apply normalization mappings
        for old, new in IPA_NORMALIZATION.items():
            ipa_string = ipa_string.replace(old, new)
        
        # Remove stress marks for primary normalization
        normalized = re.sub(r'[ˈˌ]', '', ipa_string)
        
        return normalized
    
    def detect_dialect_features(self, ipa_string, language='en'):
        """
        Analyze pronunciation to detect dialect-specific features.
        
        Args:
            ipa_string (str): IPA pronunciation string
            language (str): Language code
            
        Returns:
            dict: Detected dialect features
        """
        results = {
            'likely_dialects': [],
            'features': {}
        }
        
        # Skip processing if no IPA string
        if not ipa_string:
            return results
            
        # Check for rhoticity (r-pronunciation)
        has_rhotic_r = bool(re.search(r'[ɹɻrɾ]($|[^aeiouəɑɛɪɔʊʌæɒ])', ipa_string))
        results['features']['rhoticity'] = has_rhotic_r
        
        # Check dialect-specific patterns
        for dialect, properties in DIALECT_PATTERNS.items():
            dialect_match_score = 0
            
            # Check rhoticity consistency
            if properties['rhoticity'] == has_rhotic_r:
                dialect_match_score += 1
            
            # Check pronunciation patterns
            for pattern, expected in properties['patterns'].items():
                if re.search(pattern, ipa_string):
                    expected_options = expected.split('|')
                    for option in expected_options:
                        if option in ipa_string:
                            dialect_match_score += 1
                            results['features'][f"{dialect}_{pattern}"] = True
            
            if dialect_match_score > 0:
                results['likely_dialects'].append({
                    'dialect': dialect,
                    'confidence': min(dialect_match_score / 5, 1.0)  # Scale to 0-1
                })
        
        # Sort dialects by confidence
        results['likely_dialects'].sort(key=lambda x: x['confidence'], reverse=True)
        
        return results
    
    def process_new_pronunciations(self):
        """
        Process new pronunciation entries in the database.
        
        This includes:
        1. Normalizing IPA notation
        2. Detecting dialect features
        3. Updating pronunciation variants
        """
        if not self.connect_to_db():
            return False
        
        try:
            # Find phonetics entries that haven't been processed
            self.cursor.execute("""
                SELECT p.phonetic_id, p.word_id, p.ipa_pronunciation, 
                       w.word_text, l.language_code, d.dialect_name
                FROM phonetics p
                JOIN words w ON p.word_id = w.word_id
                JOIN languages l ON w.language_id = l.language_id
                LEFT JOIN dialects d ON p.dialect_id = d.dialect_id
                WHERE p.pronunciation_variant IS NULL
                  OR p.notes IS NULL
                LIMIT 100
            """)
            
            entries = self.cursor.fetchall()
            logger.info(f"Found {len(entries)} pronunciation entries to process")
            
            for entry in entries:
                phonetic_id = entry['phonetic_id']
                word_id = entry['word_id']
                ipa = entry['ipa_pronunciation']
                word_text = entry['word_text']
                language_code = entry['language_code']
                dialect_name = entry['dialect_name']
                
                # Normalize IPA
                normalized_ipa = self.normalize_ipa(ipa)
                
                # Detect dialect features
                dialect_features = self.detect_dialect_features(normalized_ipa, language_code)
                
                # Determine pronunciation variant
                variant = "standard"
                if dialect_features['likely_dialects']:
                    top_dialect = dialect_features['likely_dialects'][0]
                    if top_dialect['confidence'] > 0.7 and not dialect_name:
                        variant = f"{top_dialect['dialect'].lower()}"
                        
                        # Try to find or create appropriate dialect_id
                        self.cursor.execute("""
                            SELECT dialect_id FROM dialects 
                            WHERE dialect_name = %s AND language_id = 
                                (SELECT language_id FROM languages WHERE language_code = %s)
                        """, (top_dialect['dialect'], language_code))
                        
                        dialect_result = self.cursor.fetchone()
                        dialect_id = dialect_result['dialect_id'] if dialect_result else None
                        
                        if dialect_id:
                            # Update the dialect_id
                            self.cursor.execute("""
                                UPDATE phonetics SET dialect_id = %s
                                WHERE phonetic_id = %s
                            """, (dialect_id, phonetic_id))
                
                # Generate notes
                features_notes = []
                for feature, value in dialect_features['features'].items():
                    if value and not feature.startswith(('American_', 'British_', 'Australian_')):
                        features_notes.append(f"{feature}: {value}")
                
                notes = f"Normalized from '{ipa}' to '{normalized_ipa}'. "
                if features_notes:
                    notes += "Features: " + ", ".join(features_notes)
                
                # Update the database
                self.cursor.execute("""
                    UPDATE phonetics 
                    SET ipa_pronunciation = %s,
                        pronunciation_variant = %s,
                        notes = %s
                    WHERE phonetic_id = %s
                """, (normalized_ipa, variant, notes, phonetic_id))
                
                logger.info(f"Processed pronunciation for '{word_text}' (ID: {phonetic_id})")
            
            # Commit changes
            self.conn.commit()
            logger.info(f"Successfully processed {len(entries)} pronunciation entries")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error processing pronunciations: {e}")
            return False
        
        finally:
            self.close_connection()
    
    def analyze_language_phonology(self, language_code):
        """
        Analyze phonological patterns for a specific language.
        
        Args:
            language_code (str): Language code to analyze
            
        Returns:
            dict: Phonological analysis results
        """
        if not self.connect_to_db():
            return None
        
        try:
            # Find all pronunciations for the language
            self.cursor.execute("""
                SELECT p.ipa_pronunciation, w.word_text
                FROM phonetics p
                JOIN words w ON p.word_id = w.word_id
                JOIN languages l ON w.language_id = l.language_id
                WHERE l.language_code = %s
                  AND p.is_primary = TRUE
                LIMIT 1000
            """, (language_code,))
            
            pronunciations = self.cursor.fetchall()
            if not pronunciations:
                logger.warning(f"No pronunciations found for language {language_code}")
                return None
            
            # Analyze phonological patterns
            analysis = {
                'language_code': language_code,
                'sample_size': len(pronunciations),
                'phoneme_inventory': set(),
                'consonant_clusters': {},
                'syllable_patterns': {},
                'timestamp': datetime.now().isoformat()
            }
            
            # Extract phonemes and patterns
            for p in pronunciations:
                ipa = p['ipa_pronunciation']
                word = p['word_text']
                
                # Extract phonemes (simplified approach)
                phonemes = re.findall(r'[^\s\-\.]+', ipa)
                for phoneme in phonemes:
                    analysis['phoneme_inventory'].add(phoneme)
                
                # Identify consonant clusters (simplified)
                consonant_pattern = r'[bcdfghjklmnpqrstvwxyzðθʃʒŋɹɾɻ]{2,}'
                clusters = re.findall(consonant_pattern, ipa, re.IGNORECASE)
                for cluster in clusters:
                    analysis['consonant_clusters'][cluster] = analysis['consonant_clusters'].get(cluster, 0) + 1
                
                # Identify syllable patterns (very simplified)
                if len(word) > 0:
                    syllable_count = max(1, len(re.findall(r'[aeiouæɑɛɪɔʊʌəɒ]+', ipa, re.IGNORECASE)))
                    key = f"{syllable_count}_syllable"
                    analysis['syllable_patterns'][key] = analysis['syllable_patterns'].get(key, 0) + 1
            
            # Convert phoneme inventory to list for JSON serialization
            analysis['phoneme_inventory'] = list(analysis['phoneme_inventory'])
            
            # Sort consonant clusters by frequency
            analysis['consonant_clusters'] = dict(
                sorted(analysis['consonant_clusters'].items(), key=lambda x: x[1], reverse=True)[:20]
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing language phonology: {e}")
            return None
        
        finally:
            self.close_connection()
    
    def generate_audio_placeholder(self, word_id):
        """
        Generate a placeholder for audio file paths.
        
        In a real implementation, this would generate actual audio files.
        
        Args:
            word_id (int): Word ID to generate audio for
            
        Returns:
            str: Path to the generated audio file (placeholder)
        """
        audio_dir = Path('audio_files')
        audio_dir.mkdir(exist_ok=True)
        
        # In a real implementation, generate actual audio
        # For now, just return a placeholder path
        return f"audio_files/word_{word_id}.mp3"
    
    def run_batch_processing(self, batch_size=100):
        """
        Run a batch processing job on unprocessed phonetics data.
        
        Args:
            batch_size (int): Number of entries to process in one batch
            
        Returns:
            int: Number of entries processed
        """
        if not self.connect_to_db():
            return 0
        
        try:
            # Get count of unprocessed entries
            self.cursor.execute("""
                SELECT COUNT(*) as count
                FROM phonetics
                WHERE pronunciation_variant IS NULL
                   OR notes IS NULL
            """)
            
            result = self.cursor.fetchone()
            total_unprocessed = result['count'] if result else 0
            
            if total_unprocessed == 0:
                logger.info("No unprocessed phonetics entries found")
                return 0
            
            # Process in batches
            processed_count = 0
            batch_count = min(batch_size, total_unprocessed)
            
            for _ in range(0, total_unprocessed, batch_size):
                if self.process_new_pronunciations():
                    processed_count += batch_count
                
                if processed_count >= total_unprocessed:
                    break
            
            logger.info(f"Batch processing complete. Processed {processed_count} entries.")
            return processed_count
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return 0
        
        finally:
            self.close_connection()


def main():
    """Main entry point for running the phonetics agent."""
    agent = PhoneticsAgent()
    
    # Process any unprocessed pronunciation entries
    processed_count = agent.run_batch_processing()
    print(f"Processed {processed_count} pronunciation entries")
    
    # Analyze phonology for English
    en_analysis = agent.analyze_language_phonology('en')
    if en_analysis:
        # In a real implementation, we would store this in the database
        # For now, just print a summary
        phonemes = len(en_analysis['phoneme_inventory'])
        clusters = list(en_analysis['consonant_clusters'].keys())[:5]
        print(f"English phonology analysis: {phonemes} phonemes identified")
        print(f"Top consonant clusters: {', '.join(clusters)}")


if __name__ == "__main__":
    main() 