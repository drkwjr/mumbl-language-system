"""
Grammar Subagent for the Mumbl Language Processing System

This module analyzes grammar rules and sentence structures. It extracts
grammatical patterns, categorizes grammar rules, and helps identify
linguistic constructions.
"""
import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import DictCursor
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.tag import pos_tag
from nltk.parse import CoreNLPParser
from nltk.corpus import treebank

# Import local modules
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_connection_dict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/grammar_agent_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('grammar_agent')

# Ensure NLTK resources are available
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    logger.info("Downloading required NLTK resources...")
    nltk.download('punkt')
    nltk.download('averaged_perceptron_tagger')
    nltk.download('treebank')


class GrammarAgent:
    """
    Agent for analyzing grammar rules and sentence structures.
    
    This agent handles:
    1. Extracting grammar rules from text
    2. Categorizing rules by type (syntax, morphology, etc.)
    3. Analyzing sentence complexity and structure
    4. Identifying common grammatical patterns
    """
    
    def __init__(self, db_config=None):
        """
        Initialize the grammar agent.
        
        Args:
            db_config (dict): Database connection parameters
        """
        self.db_config = db_config or get_connection_dict()
        self.conn = None
        self.cursor = None
        
        # Grammar rule patterns
        self.rule_patterns = {
            'syntax': [
                r'(subject|object|predicate).*(precede|follow)',
                r'(clause|phrase).*(structure|order)',
                r'(word order|sentence structure)',
                r'(SVO|SOV|VSO|VOS|OSV|OVS)',
            ],
            'morphology': [
                r'(prefix|suffix|infix|circumfix)',
                r'(inflection|derivation|compounding)',
                r'(plural|singular).*(formation|form)',
                r'(tense|aspect|mood).*(marking|form)',
            ],
            'phonology': [
                r'(vowel|consonant).*(harmony|assimilation)',
                r'(stress|accent|tone).*(pattern|rule)',
                r'(syllable|phoneme|allophone)',
                r'(pronunciation|sound).*(change|shift)',
            ],
            'semantics': [
                r'(meaning|semantic).*(rule|principle)',
                r'(polysemy|homonymy|synonymy)',
                r'(metaphor|metonymy|synecdoche)',
                r'(denotation|connotation)',
            ],
            'pragmatics': [
                r'(context|usage).*(rule|principle)',
                r'(speech act|implicature)',
                r'(politeness|formality)',
                r'(discourse|conversation).*(rule|principle)',
            ]
        }
    
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
    
    def categorize_grammar_rule(self, rule_name, rule_description):
        """
        Categorize a grammar rule based on its name and description.
        
        Args:
            rule_name (str): Name of the grammar rule
            rule_description (str): Description of the grammar rule
            
        Returns:
            str: Category of the grammar rule (syntax, morphology, etc.)
        """
        if not rule_name or not rule_description:
            return None
            
        # Combine name and description for pattern matching
        text = f"{rule_name} {rule_description}".lower()
        
        # Check patterns for each category
        for category, patterns in self.rule_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        
        # Default to syntax if no pattern matches
        return 'syntax'
    
    def extract_grammar_rule_formula(self, rule_description):
        """
        Extract a formal representation of a grammar rule from its description.
        
        Args:
            rule_description (str): Description of the grammar rule
            
        Returns:
            str: Formal representation of the rule
        """
        if not rule_description:
            return None
            
        # Look for patterns that suggest rule formulations
        formula = None
        
        # Look for explicit formulas with →, ->, or =
        formula_match = re.search(r'([A-Za-z0-9\+]+)\s*(?:→|->|=)\s*([A-Za-z0-9\+\s]+)', rule_description)
        if formula_match:
            formula = f"{formula_match.group(1)} → {formula_match.group(2)}"
        
        # Look for "X becomes Y" patterns
        elif re.search(r'([A-Za-z0-9\+]+)\s+becomes\s+([A-Za-z0-9\+\s]+)', rule_description, re.IGNORECASE):
            match = re.search(r'([A-Za-z0-9\+]+)\s+becomes\s+([A-Za-z0-9\+\s]+)', rule_description, re.IGNORECASE)
            formula = f"{match.group(1)} → {match.group(2)}"
        
        # Look for "If X, then Y" patterns
        elif re.search(r'if\s+([^,]+),\s+then\s+([^\.]+)', rule_description, re.IGNORECASE):
            match = re.search(r'if\s+([^,]+),\s+then\s+([^\.]+)', rule_description, re.IGNORECASE)
            formula = f"{match.group(1)} → {match.group(2)}"
        
        return formula
    
    def analyze_sentence_complexity(self, sentence):
        """
        Analyze the complexity of a sentence.
        
        Args:
            sentence (str): Sentence to analyze
            
        Returns:
            dict: Analysis results including complexity score
        """
        if not sentence:
            return {'complexity_score': 0, 'features': {}}
            
        # Tokenize and tag parts of speech
        tokens = word_tokenize(sentence)
        pos_tags = pos_tag(tokens)
        
        # Initialize features
        features = {
            'word_count': len(tokens),
            'avg_word_length': sum(len(word) for word in tokens) / max(1, len(tokens)),
            'clause_count': 1,  # Start with 1 for the main clause
            'conjunction_count': 0,
            'subordinate_clause_markers': 0,
            'complex_pos_patterns': 0,
        }
        
        # Count conjunctions and subordinate clause markers
        for word, tag in pos_tags:
            if word.lower() in ['and', 'or', 'but', 'yet', 'so', 'for', 'nor']:
                features['conjunction_count'] += 1
            
            if word.lower() in ['that', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how', 'if', 'because', 'although', 'since', 'while', 'unless', 'until']:
                features['subordinate_clause_markers'] += 1
                features['clause_count'] += 1
        
        # Check for complex patterns
        pos_sequence = ' '.join([tag for _, tag in pos_tags])
        
        complex_patterns = [
            r'VB[ZDP]? DT JJ NN',  # Verb + Det + Adj + Noun
            r'IN DT JJ NN VB[ZDP]?',  # Prep + Det + Adj + Noun + Verb
            r'VB[ZDP]? (TO VB|VBG)',  # Verb + Infinitive or Gerund
            r'MD VB',  # Modal + Verb
        ]
        
        for pattern in complex_patterns:
            if re.search(pattern, pos_sequence):
                features['complex_pos_patterns'] += 1
        
        # Calculate complexity score (0-10 scale)
        score_components = [
            min(features['word_count'] / 50, 1) * 3,  # Up to 3 points for length
            min(features['clause_count'] / 5, 1) * 3,  # Up to 3 points for clauses
            min(features['complex_pos_patterns'] / 3, 1) * 2,  # Up to 2 points for complexity
            min((features['conjunction_count'] + features['subordinate_clause_markers']) / 5, 1) * 2  # Up to 2 points for conjunctions/subordinators
        ]
        
        complexity_score = round(sum(score_components), 2)
        
        return {
            'complexity_score': min(complexity_score, 10),
            'features': features
        }
    
    def identify_grammar_tone(self, sentence):
        """
        Identify the grammatical tone of a sentence.
        
        Args:
            sentence (str): Sentence to analyze
            
        Returns:
            str: Identified tone of the sentence
        """
        if not sentence:
            return 'neutral'
            
        # Tokenize and tag parts of speech
        tokens = word_tokenize(sentence.lower())
        pos_tags = pos_tag(tokens)
        
        # Check for imperative (command) tone
        if pos_tags and pos_tags[0][1].startswith('VB') and not tokens[0] in ['is', 'are', 'was', 'were', 'am', 'be', 'being', 'been']:
            return 'imperative'
        
        # Check for interrogative (question) tone
        if sentence.endswith('?') or tokens[0] in ['what', 'who', 'whom', 'whose', 'which', 'when', 'where', 'why', 'how']:
            return 'interrogative'
        
        # Check for exclamatory tone
        if sentence.endswith('!'):
            return 'exclamatory'
        
        # Check for formal tone
        formal_indicators = ['shall', 'ought', 'whom', 'thereby', 'herein', 'thus', 'hence', 'henceforth']
        if any(word in tokens for word in formal_indicators):
            return 'formal'
        
        # Check for informal tone
        informal_indicators = ['gonna', 'wanna', 'gotta', 'kinda', 'sorta', 'ya', 'yeah', 'nope', 'yep']
        if any(word in tokens for word in informal_indicators):
            return 'informal'
        
        # Default to neutral
        return 'neutral'
    
    def extract_grammar_rules_from_sentence(self, sentence, language_code='en'):
        """
        Extract potential grammar rules from a sentence.
        
        Args:
            sentence (str): Sentence to analyze
            language_code (str): Language code
            
        Returns:
            list: Extracted grammar rules
        """
        if not sentence:
            return []
            
        # Tokenize and tag parts of speech
        tokens = word_tokenize(sentence)
        pos_tags = pos_tag(tokens)
        
        rules = []
        
        # Extract word order pattern
        word_order = []
        current_phrase = {'type': None, 'words': []}
        
        for i, (word, tag) in enumerate(pos_tags):
            # Subject identification (simplified)
            if tag.startswith('NN') and i == 0:
                current_phrase = {'type': 'SUBJ', 'words': [word]}
                
            # Verb identification
            elif tag.startswith('VB') and (current_phrase['type'] == 'SUBJ' or not current_phrase['type']):
                if current_phrase['type']:
                    word_order.append(current_phrase['type'])
                current_phrase = {'type': 'VERB', 'words': [word]}
                
            # Object identification (simplified)
            elif tag.startswith('NN') and current_phrase['type'] == 'VERB':
                if current_phrase['type']:
                    word_order.append(current_phrase['type'])
                current_phrase = {'type': 'OBJ', 'words': [word]}
                
            # Adjective before noun pattern
            elif tag.startswith('JJ') and i < len(pos_tags) - 1 and pos_tags[i+1][1].startswith('NN'):
                rules.append({
                    'rule_name': 'Adjective Placement',
                    'rule_description': 'Adjectives precede the nouns they modify',
                    'rule_type': 'syntax',
                    'rule_formula': 'ADJ + NOUN',
                    'examples': [f"{word} {pos_tags[i+1][0]}"],
                    'language_code': language_code
                })
                
            # Adverb modifying verb pattern
            elif tag.startswith('RB') and i < len(pos_tags) - 1 and pos_tags[i+1][1].startswith('VB'):
                rules.append({
                    'rule_name': 'Adverb Placement',
                    'rule_description': 'Adverbs can precede the verbs they modify',
                    'rule_type': 'syntax',
                    'rule_formula': 'ADV + VERB',
                    'examples': [f"{word} {pos_tags[i+1][0]}"],
                    'language_code': language_code
                })
                
            # Preposition followed by noun phrase
            elif tag == 'IN' and i < len(pos_tags) - 2 and pos_tags[i+1][1] in ['DT', 'PRP$'] and pos_tags[i+2][1].startswith('NN'):
                rules.append({
                    'rule_name': 'Prepositional Phrase',
                    'rule_description': 'Prepositions are followed by noun phrases',
                    'rule_type': 'syntax',
                    'rule_formula': 'PREP + DET + NOUN',
                    'examples': [f"{word} {pos_tags[i+1][0]} {pos_tags[i+2][0]}"],
                    'language_code': language_code
                })
        
        # Add the last phrase type if not added yet
        if current_phrase['type']:
            word_order.append(current_phrase['type'])
        
        # If we have a complete SVO pattern, add it as a rule
        if word_order and len(word_order) >= 2:
            word_order_str = '-'.join(word_order)
            rules.append({
                'rule_name': f"{word_order_str} Word Order",
                'rule_description': f"Basic sentence structure follows {word_order_str} pattern",
                'rule_type': 'syntax',
                'rule_formula': word_order_str,
                'examples': [sentence],
                'language_code': language_code
            })
        
        return rules
    
    def process_example_sentences(self):
        """
        Process example sentences to extract grammar rules and analyze complexity.
        
        Returns:
            bool: Success status
        """
        if not self.connect_to_db():
            return False
        
        try:
            # Find example sentences that haven't been analyzed
            self.cursor.execute("""
                SELECT es.sentence_id, es.sentence_text, es.complexity_score, es.tone,
                       l.language_code, l.language_id
                FROM example_sentences es
                JOIN languages l ON es.language_id = l.language_id
                WHERE es.complexity_score IS NULL
                   OR es.tone IS NULL
                LIMIT 50
            """)
            
            sentences = self.cursor.fetchall()
            logger.info(f"Found {len(sentences)} example sentences to process")
            
            for sentence in sentences:
                sentence_id = sentence['sentence_id']
                text = sentence['sentence_text']
                language_code = sentence['language_code']
                language_id = sentence['language_id']
                
                # Analyze sentence complexity
                complexity_analysis = self.analyze_sentence_complexity(text)
                complexity_score = complexity_analysis['complexity_score']
                
                # Identify grammatical tone
                tone = self.identify_grammar_tone(text)
                
                # Update the sentence record
                self.cursor.execute("""
                    UPDATE example_sentences 
                    SET complexity_score = %s,
                        tone = %s
                    WHERE sentence_id = %s
                """, (complexity_score, tone, sentence_id))
                
                # Extract potential grammar rules
                rules = self.extract_grammar_rules_from_sentence(text, language_code)
                
                # Insert new grammar rules
                for rule in rules:
                    # Check if a similar rule already exists
                    self.cursor.execute("""
                        SELECT rule_id FROM grammar_rules
                        WHERE language_id = %s
                          AND rule_name = %s
                    """, (language_id, rule['rule_name']))
                    
                    existing_rule = self.cursor.fetchone()
                    
                    if not existing_rule:
                        # Convert rule_type string to enum value
                        rule_type = rule['rule_type']
                        
                        # Insert new rule
                        self.cursor.execute("""
                            INSERT INTO grammar_rules (
                                language_id, rule_type, rule_name, rule_description,
                                rule_formula, complexity_level
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            RETURNING rule_id
                        """, (
                            language_id,
                            rule_type,
                            rule['rule_name'],
                            rule['rule_description'],
                            rule.get('rule_formula'),
                            int(complexity_score / 2)  # Scale 0-10 to 0-5 for complexity level
                        ))
                        
                        rule_id = self.cursor.fetchone()['rule_id']
                        logger.info(f"Created new grammar rule: {rule['rule_name']} (ID: {rule_id})")
                
                logger.info(f"Processed example sentence (ID: {sentence_id})")
            
            # Commit changes
            self.conn.commit()
            logger.info(f"Successfully processed {len(sentences)} example sentences")
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error processing example sentences: {e}")
            return False
        
        finally:
            self.close_connection()
    
    def categorize_uncategorized_rules(self):
        """
        Categorize grammar rules that have no assigned type.
        
        Returns:
            int: Number of rules categorized
        """
        if not self.connect_to_db():
            return 0
        
        try:
            # Find rules that need categorization
            self.cursor.execute("""
                SELECT rule_id, rule_name, rule_description
                FROM grammar_rules
                WHERE rule_type IS NULL
                LIMIT 100
            """)
            
            rules = self.cursor.fetchall()
            categorized_count = 0
            
            for rule in rules:
                rule_id = rule['rule_id']
                rule_name = rule['rule_name']
                rule_description = rule['rule_description']
                
                # Categorize the rule
                category = self.categorize_grammar_rule(rule_name, rule_description)
                
                if category:
                    # Extract formula if possible
                    formula = self.extract_grammar_rule_formula(rule_description)
                    
                    # Update the rule
                    self.cursor.execute("""
                        UPDATE grammar_rules
                        SET rule_type = %s,
                            rule_formula = COALESCE(%s, rule_formula)
                        WHERE rule_id = %s
                    """, (category, formula, rule_id))
                    
                    categorized_count += 1
                    logger.info(f"Categorized rule '{rule_name}' as {category}")
            
            # Commit changes
            self.conn.commit()
            logger.info(f"Successfully categorized {categorized_count} grammar rules")
            return categorized_count
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error categorizing grammar rules: {e}")
            return 0
        
        finally:
            self.close_connection()
    
    def run_batch_processing(self):
        """
        Run a batch processing job on sentences and grammar rules.
        
        Returns:
            dict: Processing results
        """
        results = {
            'sentences_processed': 0,
            'rules_categorized': 0,
            'success': False
        }
        
        # Process example sentences
        if self.process_example_sentences():
            results['sentences_processed'] = 50  # Approximation based on processing limit
        
        # Categorize grammar rules
        rules_categorized = self.categorize_uncategorized_rules()
        results['rules_categorized'] = rules_categorized
        
        results['success'] = (results['sentences_processed'] > 0 or results['rules_categorized'] > 0)
        return results


def main():
    """Main entry point for running the grammar agent."""
    agent = GrammarAgent()
    
    # Run batch processing
    results = agent.run_batch_processing()
    
    print(f"Grammar Agent Results:")
    print(f"Sentences processed: {results['sentences_processed']}")
    print(f"Rules categorized: {results['rules_categorized']}")
    print(f"Overall success: {results['success']}")


if __name__ == "__main__":
    main() 