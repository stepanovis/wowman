#!/bin/bash

# Database Backup Script for Ovulo Bot
# This script creates a backup of the PostgreSQL database
# Works both locally and in Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BACKUP_DIR="${BACKUP_DIR:-./backups}"
ENV_FILE="${ENV_FILE:-./.env}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
USE_DOCKER=false
CONTAINER_NAME=""
VERBOSE=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Create a backup of the Ovulo PostgreSQL database.

OPTIONS:
    -h, --help              Show this help message
    -e, --env FILE          Path to .env file (default: ./.env)
    -d, --dir DIR           Backup directory (default: ./backups)
    -c, --container NAME    Use Docker container (specify container name)
    -v, --verbose           Verbose output
    --host HOST             Database host (overrides .env)
    --port PORT             Database port (overrides .env)
    --db NAME               Database name (overrides .env)
    --user USER             Database user (overrides .env)
    --password PASS         Database password (overrides .env)

EXAMPLES:
    # Backup local database using .env file
    $0

    # Backup from Docker container
    $0 -c ovulo-postgres

    # Backup with custom settings
    $0 --host localhost --port 5433 --db ovulo_dev

    # Backup with custom directory
    $0 -d /path/to/backups

EOF
}

# Parse command line arguments
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
        -d|--dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        -c|--container)
            USE_DOCKER=true
            CONTAINER_NAME="$2"
            shift 2
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
            echo -e "${RED}Unknown option: $1${NC}"
            show_usage
            exit 1
            ;;
    esac
done

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

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate backup filename
BACKUP_FILE="${BACKUP_DIR}/ovulo_backup_${DB_NAME}_${TIMESTAMP}.sql"

# Show configuration
echo -e "${GREEN}=== Database Backup Configuration ===${NC}"
echo "Database: $DB_NAME"
echo "Host: $DB_HOST"
echo "Port: $DB_PORT"
echo "User: $DB_USER"
echo "Backup file: $BACKUP_FILE"

if [ "$USE_DOCKER" = true ]; then
    echo "Using Docker container: $CONTAINER_NAME"
fi

echo ""

# Perform backup
echo -e "${YELLOW}Starting backup...${NC}"

if [ "$USE_DOCKER" = true ]; then
    # Check if container exists and is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo -e "${RED}Error: Container '$CONTAINER_NAME' is not running${NC}"
        exit 1
    fi

    # Backup using Docker exec
    if [ "$VERBOSE" = true ]; then
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            pg_dump -U "$DB_USER" -d "$DB_NAME" -v --no-owner --no-acl > "$BACKUP_FILE"
    else
        docker exec -e PGPASSWORD="$DB_PASSWORD" "$CONTAINER_NAME" \
            pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl > "$BACKUP_FILE" 2>/dev/null
    fi
else
    # Direct backup using pg_dump
    export PGPASSWORD="$DB_PASSWORD"

    if [ "$VERBOSE" = true ]; then
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            -v --no-owner --no-acl > "$BACKUP_FILE"
    else
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            --no-owner --no-acl > "$BACKUP_FILE" 2>/dev/null
    fi

    unset PGPASSWORD
fi

# Check if backup was successful
if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo -e "${GREEN}✓ Backup completed successfully!${NC}"
    echo "File: $BACKUP_FILE"
    echo "Size: $BACKUP_SIZE"

    # Compress the backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip "$BACKUP_FILE"

    if [ $? -eq 0 ]; then
        COMPRESSED_FILE="${BACKUP_FILE}.gz"
        COMPRESSED_SIZE=$(ls -lh "$COMPRESSED_FILE" | awk '{print $5}')
        echo -e "${GREEN}✓ Backup compressed successfully!${NC}"
        echo "Compressed file: $COMPRESSED_FILE"
        echo "Compressed size: $COMPRESSED_SIZE"
    fi

    # Clean old backups (keep last 10)
    echo -e "${YELLOW}Cleaning old backups (keeping last 10)...${NC}"
    ls -t "$BACKUP_DIR"/ovulo_backup_*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm
    echo -e "${GREEN}✓ Old backups cleaned${NC}"

    exit 0
else
    echo -e "${RED}✗ Backup failed!${NC}"
    [ -f "$BACKUP_FILE" ] && rm "$BACKUP_FILE"
    exit 1
fi