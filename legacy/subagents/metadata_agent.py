"""
Metadata Subagent for the Mumbl Language Processing System

This module tracks data sources, assesses reliability, and maintains
change history for language data. It helps ensure data quality and
traceability.
"""
import os
import re
import json
import logging
import hashlib
import requests
from urllib.parse import urlparse
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
        logging.FileHandler(f"logs/metadata_agent_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('metadata_agent')

# Source reliability scoring factors
RELIABILITY_FACTORS = {
    'academic': {
        'base_score': 4.0,  # Academic sources start with a high base score
        'domains': ['edu', 'ac.uk', 'research', 'university'],
        'keywords': ['journal', 'published', 'research', 'study', 'peer-reviewed'],
    },
    'dictionary': {
        'base_score': 3.5,  # Dictionaries are generally reliable
        'domains': ['dictionary', 'lexicon', 'merriam-webster', 'oxford', 'cambridge'],
        'keywords': ['dictionary', 'definition', 'lexicon', 'wordlist'],
    },
    'linguistic_resource': {
        'base_score': 3.0,  # Specialized linguistic resources
        'domains': ['linguistics', 'language', 'grammar'],
        'keywords': ['corpus', 'linguistic', 'grammar', 'syntax', 'phonology'],
    },
    'general_reference': {
        'base_score': 2.5,  # General reference works
        'domains': ['reference', 'wikipedia', 'encyclopedia'],
        'keywords': ['reference', 'guide', 'encyclopedia', 'wiki'],
    },
    'user_contributed': {
        'base_score': 1.5,  # User-contributed content starts with a lower score
        'domains': ['forum', 'community', 'wiki', 'blog'],
        'keywords': ['forum', 'discussion', 'user', 'comment', 'blog'],
    }
}


class MetadataAgent:
    """
    Agent for tracking metadata and source reliability for language data.
    
    This agent handles:
    1. Tracking data sources and their reliability
    2. Linking entities to metadata sources
    3. Maintaining change history
    4. Assessing confidence levels for language data
    """
    
    def __init__(self, db_config=None, agent_id=None):
        """
        Initialize the metadata agent.
        
        Args:
            db_config (dict): Database connection parameters
            agent_id (int): ID of this subagent in the database
        """
        self.db_config = db_config or get_connection_dict()
        self.agent_id = agent_id
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
    
    def get_agent_id(self):
        """
        Get the ID of this subagent from the database, or create an entry if needed.
        
        Returns:
            int: Subagent ID
        """
        if self.agent_id:
            return self.agent_id
            
        if not self.connect_to_db():
            return None
        
        try:
            # Check if the Metadata Agent exists
            self.cursor.execute("""
                SELECT subagent_id FROM subagents 
                WHERE subagent_name = 'Metadata Agent'
            """)
            
            result = self.cursor.fetchone()
            
            if result:
                self.agent_id = result['subagent_id']
            else:
                # Create a new subagent entry
                self.cursor.execute("""
                    INSERT INTO subagents (
                        subagent_name, subagent_type, description, is_active
                    ) VALUES (
                        'Metadata Agent', 'Automated', 
                        'Tracks metadata, source reliability, and change history', TRUE
                    ) RETURNING subagent_id
                """)
                
                self.agent_id = self.cursor.fetchone()['subagent_id']
                self.conn.commit()
                logger.info(f"Created new subagent record with ID: {self.agent_id}")
            
            return self.agent_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error getting agent ID: {e}")
            return None
        
        finally:
            self.close_connection()
    
    def assess_source_reliability(self, source_name, source_url=None, source_type=None):
        """
        Assess the reliability of a data source.
        
        Args:
            source_name (str): Name of the source
            source_url (str): URL of the source, if available
            source_type (str): Type of source, if known
            
        Returns:
            float: Reliability score (0-5 scale)
        """
        if not source_name:
            return 0.0
            
        # Start with a neutral score
        reliability_score = 2.0
        
        # Determine source type if not provided
        if not source_type:
            source_type = self.determine_source_type(source_name, source_url)
        
        # Apply base score for the source type
        factor_data = RELIABILITY_FACTORS.get(source_type, RELIABILITY_FACTORS['general_reference'])
        reliability_score = factor_data['base_score']
        
        # Check for keywords in the source name
        for keyword in factor_data['keywords']:
            if keyword.lower() in source_name.lower():
                reliability_score += 0.1
        
        # Check domain if URL is provided
        if source_url:
            parsed_url = urlparse(source_url)
            domain = parsed_url.netloc.lower()
            
            # Check for respected domains
            for respected_domain in factor_data['domains']:
                if respected_domain in domain:
                    reliability_score += 0.3
                    break
            
            # Adjust for specific high-reliability domains
            high_reliability_domains = [
                'oxford', 'cambridge', 'merriam-webster', 'britannica',
                'edu', 'gov', 'ac.uk', 'linguisticsociety.org'
            ]
            for high_domain in high_reliability_domains:
                if high_domain in domain:
                    reliability_score += 0.5
                    break
        
        # Cap the score at 5.0
        return min(5.0, reliability_score)
    
    def determine_source_type(self, source_name, source_url=None):
        """
        Determine the type of a source based on its name and URL.
        
        Args:
            source_name (str): Name of the source
            source_url (str): URL of the source, if available
            
        Returns:
            str: Source type
        """
        source_name_lower = source_name.lower()
        
        # Check for academic sources
        if any(term in source_name_lower for term in ['journal', 'university', 'research', 'proceedings', 'academia']):
            return 'academic'
        
        # Check for dictionaries
        if any(term in source_name_lower for term in ['dictionary', 'lexicon', 'wordnet', 'oxford', 'cambridge', 'merriam', 'webster']):
            return 'dictionary'
        
        # Check for linguistic resources
        if any(term in source_name_lower for term in ['linguistics', 'corpus', 'grammar', 'phonology', 'syntax']):
            return 'linguistic_resource'
        
        # Check for user-contributed content
        if any(term in source_name_lower for term in ['forum', 'wiki', 'blog', 'community', 'user']):
            return 'user_contributed'
        
        # Check URL if available
        if source_url:
            domain = urlparse(source_url).netloc.lower()
            
            if any(term in domain for term in ['edu', 'ac.uk', 'research']):
                return 'academic'
            
            if any(term in domain for term in ['dictionary', 'lexicon', 'oxford', 'cambridge', 'merriam-webster']):
                return 'dictionary'
            
            if any(term in domain for term in ['linguistics', 'grammar', 'language']):
                return 'linguistic_resource'
            
            if any(term in domain for term in ['wiki', 'forum', 'blog']):
                return 'user_contributed'
        
        # Default to general reference
        return 'general_reference'
    
    def register_source(self, source_name, source_type=None, url=None, publication_date=None, license_info=None, notes=None):
        """
        Register a new metadata source or update an existing one.
        
        Args:
            source_name (str): Name of the source
            source_type (str): Type of source
            url (str): URL of the source
            publication_date (str): Publication date in YYYY-MM-DD format
            license_info (str): License information
            notes (str): Additional notes
            
        Returns:
            int: Source ID
        """
        if not source_name:
            return None
            
        if not self.connect_to_db():
            return None
        
        try:
            # Check if the source already exists
            self.cursor.execute("""
                SELECT source_id FROM metadata_sources 
                WHERE source_name = %s
            """, (source_name,))
            
            result = self.cursor.fetchone()
            
            if result:
                source_id = result['source_id']
                
                # Update existing source if needed
                if source_type or url or publication_date or license_info or notes:
                    self.cursor.execute("""
                        UPDATE metadata_sources 
                        SET source_type = COALESCE(%s, source_type),
                            url = COALESCE(%s, url),
                            publication_date = COALESCE(%s, publication_date),
                            license_info = COALESCE(%s, license_info),
                            notes = COALESCE(%s, notes),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE source_id = %s
                    """, (source_type, url, publication_date, license_info, notes, source_id))
                    
                    logger.info(f"Updated metadata source: {source_name} (ID: {source_id})")
            else:
                # Determine source type if not provided
                if not source_type:
                    source_type = self.determine_source_type(source_name, url)
                
                # Assess reliability
                reliability_score = self.assess_source_reliability(source_name, url, source_type)
                
                # Create new source
                self.cursor.execute("""
                    INSERT INTO metadata_sources (
                        source_name, source_type, reliability_score, url, 
                        publication_date, license_info, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING source_id
                """, (source_name, source_type, reliability_score, url, publication_date, license_info, notes))
                
                source_id = self.cursor.fetchone()['source_id']
                logger.info(f"Registered new metadata source: {source_name} (ID: {source_id})")
            
            # Commit changes
            self.conn.commit()
            return source_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error registering source: {e}")
            return None
        
        finally:
            self.close_connection()
    
    def link_entity_to_source(self, entity_type, entity_id, source_id, confidence_score=None, notes=None):
        """
        Link an entity to a metadata source.
        
        Args:
            entity_type (str): Type of entity (e.g., 'word', 'definition', 'phonetic')
            entity_id (int): ID of the entity
            source_id (int): ID of the metadata source
            confidence_score (float): Confidence score (0-1)
            notes (str): Additional notes
            
        Returns:
            bool: Success status
        """
        if not entity_type or not entity_id or not source_id:
            return False
            
        if not self.connect_to_db():
            return False
        
        try:
            # Check if the link already exists
            self.cursor.execute("""
                SELECT metadata_id FROM entity_metadata 
                WHERE entity_type = %s AND entity_id = %s AND source_id = %s
            """, (entity_type, entity_id, source_id))
            
            result = self.cursor.fetchone()
            
            if result:
                metadata_id = result['metadata_id']
                
                # Update existing link if needed
                if confidence_score is not None or notes:
                    self.cursor.execute("""
                        UPDATE entity_metadata 
                        SET confidence_score = COALESCE(%s, confidence_score),
                            notes = COALESCE(%s, notes)
                        WHERE metadata_id = %s
                    """, (confidence_score, notes, metadata_id))
                    
                    logger.info(f"Updated entity-metadata link (ID: {metadata_id})")
            else:
                # Create new link
                self.cursor.execute("""
                    INSERT INTO entity_metadata (
                        entity_type, entity_id, source_id, confidence_score, notes
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING metadata_id
                """, (entity_type, entity_id, source_id, confidence_score, notes))
                
                metadata_id = self.cursor.fetchone()['metadata_id']
                logger.info(f"Created entity-metadata link (ID: {metadata_id})")
            
            # Commit changes
            self.conn.commit()
            return True
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error linking entity to source: {e}")
            return False
        
        finally:
            self.close_connection()
    
    def record_change(self, table_modified, record_id, field_modified, previous_value, new_value, change_reason=None):
        """
        Record a change to the database.
        
        Args:
            table_modified (str): Table being modified
            record_id (int): ID of the record being modified
            field_modified (str): Field being modified
            previous_value (str): Previous value of the field
            new_value (str): New value of the field
            change_reason (str): Reason for the change
            
        Returns:
            int: Change ID
        """
        if not table_modified or not record_id or not field_modified:
            return None
            
        if not self.connect_to_db():
            return None
        
        try:
            # Ensure we have a subagent ID
            subagent_id = self.get_agent_id()
            
            # Record the change
            self.cursor.execute("""
                INSERT INTO change_history (
                    table_modified, record_id, field_modified, subagent_id,
                    change_description, previous_value, new_value, change_reason
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING change_id
            """, (
                table_modified,
                record_id,
                field_modified,
                subagent_id,
                f"Field {field_modified} updated in {table_modified}",
                previous_value,
                new_value,
                change_reason
            ))
            
            change_id = self.cursor.fetchone()['change_id']
            logger.info(f"Recorded change (ID: {change_id}) to {table_modified}.{field_modified}")
            
            # Commit changes
            self.conn.commit()
            return change_id
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error recording change: {e}")
            return None
        
        finally:
            self.close_connection()
    
    def verify_source_url(self, source_id):
        """
        Verify that a source URL is valid and accessible.
        
        Args:
            source_id (int): ID of the source to verify
            
        Returns:
            dict: Verification results
        """
        if not self.connect_to_db():
            return {'verified': False, 'error': 'Database connection failed'}
        
        try:
            # Get the source URL
            self.cursor.execute("""
                SELECT source_id, source_name, url 
                FROM metadata_sources 
                WHERE source_id = %s AND url IS NOT NULL
            """, (source_id,))
            
            result = self.cursor.fetchone()
            
            if not result or not result['url']:
                return {'verified': False, 'error': 'No URL found for this source'}
            
            source_id = result['source_id']
            source_name = result['source_name']
            url = result['url']
            
            # Attempt to verify the URL
            try:
                headers = {
                    'User-Agent': 'Mumbl Language Processing System (Verification Bot)'
                }
                response = requests.head(url, headers=headers, timeout=10)
                
                # Check for redirects
                if response.status_code in (301, 302, 303, 307, 308):
                    redirected_url = response.headers.get('Location')
                    
                    if redirected_url:
                        # Update the URL in the database
                        self.cursor.execute("""
                            UPDATE metadata_sources 
                            SET url = %s
                            WHERE source_id = %s
                        """, (redirected_url, source_id))
                        
                        # Record the change
                        self.record_change(
                            'metadata_sources',
                            source_id,
                            'url',
                            url,
                            redirected_url,
                            'URL redirection detected and updated'
                        )
                        
                        # Get the content of the redirected URL
                        response = requests.get(redirected_url, headers=headers, timeout=10)
                        url = redirected_url
                    
                # Check for successful response
                if response.status_code in (200, 203, 206):
                    verification_result = {
                        'verified': True,
                        'url': url,
                        'status_code': response.status_code,
                        'content_type': response.headers.get('Content-Type', 'unknown')
                    }
                    
                    # Update the last verification timestamp
                    notes = result.get('notes', '') or ''
                    updated_notes = f"{notes}\nURL verified on {datetime.now().isoformat()}"
                    
                    self.cursor.execute("""
                        UPDATE metadata_sources 
                        SET notes = %s
                        WHERE source_id = %s
                    """, (updated_notes, source_id))
                    
                else:
                    verification_result = {
                        'verified': False,
                        'url': url,
                        'status_code': response.status_code,
                        'error': f"URL returned status code {response.status_code}"
                    }
            
            except requests.RequestException as e:
                verification_result = {
                    'verified': False,
                    'url': url,
                    'error': str(e)
                }
            
            # Commit changes
            self.conn.commit()
            logger.info(f"Verified source URL for {source_name}: {verification_result['verified']}")
            
            return verification_result
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error verifying source URL: {e}")
            return {'verified': False, 'error': str(e)}
        
        finally:
            self.close_connection()
    
    def reassess_source_reliability(self, source_id=None):
        """
        Reassess the reliability of one or all sources.
        
        Args:
            source_id (int): ID of the source to reassess, or None for all
            
        Returns:
            int: Number of sources updated
        """
        if not self.connect_to_db():
            return 0
        
        try:
            # Prepare query to get sources
            if source_id:
                query = "SELECT source_id, source_name, source_type, url FROM metadata_sources WHERE source_id = %s"
                params = (source_id,)
            else:
                query = "SELECT source_id, source_name, source_type, url FROM metadata_sources"
                params = None
            
            # Execute the query
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
            
            sources = self.cursor.fetchall()
            updated_count = 0
            
            for source in sources:
                source_id = source['source_id']
                source_name = source['source_name']
                source_type = source['source_type']
                url = source['url']
                
                # Reassess reliability
                new_score = self.assess_source_reliability(source_name, url, source_type)
                
                # Update the score in the database
                self.cursor.execute("""
                    UPDATE metadata_sources 
                    SET reliability_score = %s
                    WHERE source_id = %s
                    RETURNING reliability_score
                """, (new_score, source_id))
                
                old_score = self.cursor.fetchone()['reliability_score']
                
                # Record the change if score changed
                if abs(old_score - new_score) > 0.01:
                    self.record_change(
                        'metadata_sources',
                        source_id,
                        'reliability_score',
                        str(old_score),
                        str(new_score),
                        'Automated reliability reassessment'
                    )
                    
                    updated_count += 1
                    logger.info(f"Updated reliability score for {source_name}: {old_score} -> {new_score}")
            
            # Commit changes
            self.conn.commit()
            logger.info(f"Reassessed {len(sources)} sources, updated {updated_count}")
            
            return updated_count
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error reassessing source reliability: {e}")
            return 0
        
        finally:
            self.close_connection()
    
    def run_maintenance(self):
        """
        Run maintenance tasks on metadata and change history.
        
        Returns:
            dict: Maintenance results
        """
        results = {
            'sources_reassessed': 0,
            'sources_verified': 0,
            'success': False
        }
        
        # Reassess reliability scores
        sources_reassessed = self.reassess_source_reliability()
        results['sources_reassessed'] = sources_reassessed
        
        # Verify a sample of source URLs
        if self.connect_to_db():
            try:
                # Get a sample of sources to verify
                self.cursor.execute("""
                    SELECT source_id FROM metadata_sources 
                    WHERE url IS NOT NULL
                    ORDER BY RANDOM()
                    LIMIT 5
                """)
                
                sources = self.cursor.fetchall()
                sources_verified = 0
                
                for source in sources:
                    result = self.verify_source_url(source['source_id'])
                    if result['verified']:
                        sources_verified += 1
                
                results['sources_verified'] = sources_verified
                
            except Exception as e:
                logger.error(f"Error in maintenance task: {e}")
                
            finally:
                self.close_connection()
        
        results['success'] = (results['sources_reassessed'] > 0 or results['sources_verified'] > 0)
        return results


def main():
    """Main entry point for running the metadata agent."""
    agent = MetadataAgent()
    
    # Register a sample source
    source_id = agent.register_source(
        "Wiktionary",
        "dictionary",
        "https://en.wiktionary.org/",
        None,
        "Creative Commons Attribution-ShareAlike License",
        "Collaborative dictionary project"
    )
    
    if source_id:
        print(f"Registered source with ID: {source_id}")
        
        # Verify the source URL
        verification = agent.verify_source_url(source_id)
        print(f"Source verification: {verification['verified']}")
    
    # Run maintenance tasks
    maintenance_results = agent.run_maintenance()
    print(f"Maintenance Results:")
    print(f"Sources reassessed: {maintenance_results['sources_reassessed']}")
    print(f"Sources verified: {maintenance_results['sources_verified']}")
    print(f"Overall success: {maintenance_results['success']}")


if __name__ == "__main__":
    main() 