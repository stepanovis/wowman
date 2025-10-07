#!/bin/bash

# Database Restore Script for Ovulo Bot
# This script restores a PostgreSQL database from a backup file
# Works both locally and in Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
ENV_FILE="${ENV_FILE:-./.env}"
USE_DOCKER=false
CONTAINER_NAME=""
VERBOSE=false
FORCE=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] BACKUP_FILE

Restore the Ovulo PostgreSQL database from a backup file.

ARGUMENTS:
    BACKUP_FILE             Path to the backup file (.sql or .sql.gz)

OPTIONS:
    -h, --help              Show this help message
    -e, --env FILE          Path to .env file (default: ./.env)
    -c, --container NAME    Use Docker container (specify container name)
    -f, --force             Don't ask for confirmation
    -v, --verbose           Verbose output
    --host HOST             Database host (overrides .env)
    --port PORT             Database port (overrides .env)
    --db NAME               Database name (overrides .env)
    --user USER             Database user (overrides .env)
    --password PASS         Database password (overrides .env)

EXAMPLES:
    # Restore local database from backup
    $0 backups/ovulo_backup_20240101_120000.sql.gz

    # Restore to Docker container
    $0 -c ovulo-postgres backups/ovulo_backup_20240101_120000.sql.gz

    # Restore with custom settings
    $0 --host localhost --port 5433 --db ovulo_dev backup.sql

    # Force restore without confirmation
    $0 -f backup.sql

EOF
}

# Check if file exists
check_file() {
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: Backup file not found: $1${NC}"
        exit 1
    fi
}

# Confirm restore operation
confirm_restore() {
    echo -e "${YELLOW}⚠️  WARNING: This will DELETE all existing data in the database!${NC}"
    echo -e "${YELLOW}Database: $DB_NAME on $DB_HOST:$DB_PORT${NC}"
    echo ""
    read -p "Are you sure you want to restore from backup? (yes/no): " -r
    echo
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${RED}Restore cancelled.${NC}"
        exit 0
    fi
}

# Parse command line arguments
BACKUP_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -c|--container)
            USE_DOCKER=true
            CONTAINER_NAME="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --host)
            DB_HOST="$2"
            shift 2
            ;;
        --port)
            DB_PORT="$2"
            shift 2
            ;;
        --db)
            DB_NAME="$2"
            shift 2
            ;;
        --user)
            DB_USER="$2"
            shift 2
            ;;
        --password)
            DB_PASSWORD="$2"
            shift 2
            ;;
        *)
            if [ -z "$BACKUP_FILE" ]; then
                BACKUP_FILE="$1"
            else
                echo -e "${RED}Unknown option: $1${NC}"
                show_usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if backup file is provided
if [ -z "$BACKUP_FILE" ]; then
    echo -e "${RED}Error: Backup file not specified${NC}"
    echo ""
    show_usage
    exit 1
fi

# Check if backup file exists
check_file "$BACKUP_FILE"

# Load environment variables if not provided via command line
if [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Loading environment from: $ENV_FILE${NC}"
    export $(cat "$ENV_FILE" | grep -v '^#' | grep -v '^$' | xargs)
else
    echo -e "${YELLOW}Warning: .env file not found at $ENV_FILE${NC}"
fi

# Set database connection parameters
DB_HOST="${DB_HOST:-${POSTGRES_HOST:-localhost}}"
DB_PORT="${DB_PORT:-${POSTGRES_PORT:-5432}}"
DB_NAME="${DB_NAME:-${POSTGRES_DB:-ovulo_dev}}"
DB_USER="${DB_USER:-${POSTGRES_USER:-ovulo_user}}"
DB_PASSWORD="${DB_PASSWORD:-${POSTGRES_PASSWORD:-ovulo_password_dev}}"

# Show configuration
echo -e "${GREEN}=== Database Restore Configuration ===${NC}"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "User: $DB_USER"
echo "Backup file: $BACKUP_FILE"

if [ "$USE_DOCKER" = true ]; then
    echo "Using Docker container: $CONTAINER_NAME"
fi

echo ""

# Ask for confirmation if not forced
if [ "$FORCE" = false ]; then
    confirm_restore
fi

# Prepare backup file
TEMP_SQL_FILE=""
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo -e "${YELLOW}Decompressing backup file...${NC}"
    TEMP_SQL_FILE="/tmp/ovulo_restore_$(date +%s).sql"
    gunzip -c "$BACKUP_FILE" > "$TEMP_SQL_FILE"
    SQL_FILE="$TEMP_SQL_FILE"
else
    SQL_FILE="$BACKUP_FILE"
fi

# Perform restore
echo -e "${YELLOW}Starting restore...${NC}"

if [ "$USE_DOCKER" = true ]; then
    # Check if container exists and is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}Error: Container '$CONTAINER_NAME' is not running${NC}"
        [ -n "$TEMP_SQL_FILE" ] && rm "$TEMP_SQL_FILE"
        exit 1
    fi

    # Drop and recreate database
    echo -e "${YELLOW}Dropping existing database...${NC}"
    docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
        psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

    echo -e "${YELLOW}Creating new database...${NC}"
    docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
        psql -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;" 2>/dev/null

    # Copy SQL file to container
    echo -e "${YELLOW}Copying backup file to container...${NC}"
    docker cp "$SQL_FILE" "$CONTAINER_NAME:/tmp/restore.sql"

    # Restore using Docker exec
    echo -e "${YELLOW}Restoring database...${NC}"
    if [ "$VERBOSE" = true ]; then
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /tmp/restore.sql
    else
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 -f /tmp/restore.sql > /dev/null 2>&1
    fi

    # Clean up
    docker exec "$CONTAINER_NAME" rm /tmp/restore.sql
else
    # Direct restore using psql
    export PGPASSWORD="$DB_PASSWORD"

    # Drop and recreate database
    echo -e "${YELLOW}Dropping existing database...${NC}"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -c "DROP DATABASE IF EXISTS $DB_NAME;" 2>/dev/null || true

    echo -e "${YELLOW}Creating new database...${NC}"
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
        -c "CREATE DATABASE $DB_NAME;" 2>/dev/null

    # Restore database
    echo -e "${YELLOW}Restoring database...${NC}"
    if [ "$VERBOSE" = true ]; then
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -v ON_ERROR_STOP=1 -f "$SQL_FILE"
    else
        psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -v ON_ERROR_STOP=1 -f "$SQL_FILE" > /dev/null 2>&1
    fi

    unset PGPASSWORD
fi

# Clean up temporary file
[ -n "$TEMP_SQL_FILE" ] && rm "$TEMP_SQL_FILE"

# Check if restore was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully!${NC}"

    # Run migrations if alembic is available
    if command -v alembic &> /dev/null; then
        echo -e "${YELLOW}Running database migrations...${NC}"
        cd "$(dirname "$ENV_FILE")" && alembic upgrade head
        echo -e "${GREEN}✓ Migrations completed${NC}"
    fi

    # Show summary
    echo ""
    echo -e "${CYAN}=== Restore Summary ===${NC}"
    echo "Database: $DB_NAME"
    echo "Restored from: $BACKUP_FILE"
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

    exit 0
else
    echo -e "${RED}✗ Restore failed!${NC}"
    exit 1
fi