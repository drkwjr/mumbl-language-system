#!/bin/bash
# Database Setup Script for Mumbl Language System
# Creates local PostgreSQL database and runs migrations

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Mumbl Database Setup ===${NC}\n"

# Load environment variables if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}Loading .env file...${NC}"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-mumbl_lang_system}
DB_USER=${DB_USER:-mumbl_user}
DB_PASSWORD=${DB_PASSWORD:-mumbl_dev_password}

echo -e "Database Configuration:"
echo -e "  Host: ${DB_HOST}"
echo -e "  Port: ${DB_PORT}"
echo -e "  Database: ${DB_NAME}"
echo -e "  User: ${DB_USER}\n"

# Check if PostgreSQL is running
echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
    echo -e "${RED}ERROR: PostgreSQL is not running or not accessible${NC}"
    echo -e "${YELLOW}On macOS, try: brew services start postgresql@14${NC}"
    echo -e "${YELLOW}On Linux, try: sudo systemctl start postgresql${NC}"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}\n"

# Check if database exists
echo -e "${YELLOW}Checking if database exists...${NC}"
if psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo -e "${YELLOW}Database '$DB_NAME' already exists.${NC}"
    read -p "Do you want to drop and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Dropping database...${NC}"
        psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
        psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "DROP USER IF EXISTS $DB_USER;"
    else
        echo -e "${GREEN}Using existing database${NC}"
    fi
fi

# Create user if not exists
echo -e "${YELLOW}Creating database user...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U postgres << EOF
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '$DB_USER') THEN
      CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
   END IF;
END
\$\$;
EOF
echo -e "${GREEN}✓ User created/verified${NC}\n"

# Create database if not exists
echo -e "${YELLOW}Creating database...${NC}"
psql -h "$DB_HOST" -p "$DB_PORT" -U postgres << EOF
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF
echo -e "${GREEN}✓ Database created/verified${NC}\n"

# Run migrations
echo -e "${YELLOW}Running migrations...${NC}"
MIGRATIONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/migrations" && pwd)"

if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo -e "${RED}ERROR: Migrations directory not found: $MIGRATIONS_DIR${NC}"
    exit 1
fi

# Run each migration in order
for migration in "$MIGRATIONS_DIR"/[0-9]*.sql; do
    if [ -f "$migration" ] && [[ ! "$migration" =~ _down\.sql$ ]]; then
        echo -e "  Applying: $(basename "$migration")"
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$migration"
    fi
done

echo -e "${GREEN}✓ Migrations applied${NC}\n"

# Test connection
echo -e "${YELLOW}Testing database connection...${NC}"
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database connection successful!${NC}\n"
    
    # Show table count
    TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
    echo -e "${GREEN}Tables created: $TABLE_COUNT${NC}\n"
    
    # Save connection string to .env if it doesn't exist
    if [ -f .env ] && ! grep -q "DATABASE_URL" .env; then
        echo "DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME" >> .env
        echo -e "${GREEN}✓ DATABASE_URL added to .env${NC}"
    fi
else
    echo -e "${RED}ERROR: Database connection failed${NC}"
    exit 1
fi

echo -e "${GREEN}=== Setup Complete! ===${NC}"
echo -e "\nConnection string:"
echo -e "${YELLOW}postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME${NC}\n"

