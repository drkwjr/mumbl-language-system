"""
Database configuration settings for the Mumbl Language Processing System.
"""
import os
from configparser import ConfigParser


def config(filename='database.ini', section='postgresql'):
    """Load database configuration from the specified INI file."""
    # Create a parser
    parser = ConfigParser()
    # Read config file
    parser.read(filename)

    # Get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(f'Section {section} not found in the {filename} file')

    return db


# Default database configuration
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'mumbl_language'),
    'user': os.getenv('DB_USER', 'mumbl_user'),
    'password': os.getenv('DB_PASSWORD', 'mumbl_password'),
    'port': os.getenv('DB_PORT', '5432')
}


def get_connection_string():
    """Return a formatted connection string for SQLAlchemy or direct psycopg2 use."""
    config = DATABASE_CONFIG
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"


def get_connection_dict():
    """Return connection parameters as a dictionary."""
    return DATABASE_CONFIG


# Sample database.ini file content (create this file in your project root)
SAMPLE_CONFIG_FILE = """
[postgresql]
host=localhost
database=mumbl_language
user=mumbl_user
password=mumbl_password
port=5432

[postgresql_test]
host=localhost
database=mumbl_language_test
user=mumbl_user
password=mumbl_password
port=5432
"""


def create_sample_config(filepath='database.ini'):
    """Create a sample database configuration file."""
    with open(filepath, 'w') as configfile:
        configfile.write(SAMPLE_CONFIG_FILE.strip())
    print(f"Sample configuration file created at {filepath}")


if __name__ == "__main__":
    # If this file is executed directly, create a sample config file
    create_sample_config() 