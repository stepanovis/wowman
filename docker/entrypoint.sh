#!/bin/bash
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."

    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
            log_info "PostgreSQL is ready!"
            return 0
        fi

        attempt=$((attempt + 1))
        log_warning "PostgreSQL is not ready yet (attempt $attempt/$max_attempts)..."
        sleep 2
    done

    log_error "PostgreSQL did not become ready in time"
    return 1
}

# Function to check if database exists
database_exists() {
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"
}

# Function to create database if it doesn't exist
create_database_if_needed() {
    if ! database_exists; then
        log_info "Database '${DB_NAME}' does not exist. Creating..."
        PGPASSWORD="${DB_PASSWORD}" createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"
        log_info "Database '${DB_NAME}' created successfully"
    else
        log_info "Database '${DB_NAME}' already exists"
    fi
}

# Function to run Alembic migrations
run_migrations() {
    log_info "Running database migrations..."

    # Check if alembic.ini exists
    if [ ! -f "/app/alembic.ini" ]; then
        log_error "alembic.ini not found"
        return 1
    fi

    # Check if migrations directory exists
    if [ ! -d "/app/migrations" ]; then
        log_error "migrations directory not found"
        return 1
    fi

    # Run migrations
    cd /app

    # First, check current revision
    current_rev=$(alembic current 2>/dev/null | grep -oE '[a-f0-9]{12}' | head -1)
    if [ -z "$current_rev" ]; then
        log_info "No current revision found, initializing database schema..."
    else
        log_info "Current revision: $current_rev"
    fi

    # Run upgrade to head
    if alembic upgrade head; then
        log_info "Database migrations completed successfully"

        # Show new revision
        new_rev=$(alembic current 2>/dev/null | grep -oE '[a-f0-9]{12}' | head -1)
        if [ -n "$new_rev" ]; then
            log_info "Database is now at revision: $new_rev"
        fi
    else
        log_error "Failed to run database migrations"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting Ovulo Bot initialization..."

    # Set default values if not provided
    export DB_HOST="${DB_HOST:-localhost}"
    export DB_PORT="${DB_PORT:-5432}"
    export DB_NAME="${DB_NAME:-ovulo}"
    export DB_USER="${DB_USER:-postgres}"

    # Check required environment variables
    if [ -z "${DB_PASSWORD}" ]; then
        log_error "DB_PASSWORD environment variable is required"
        exit 1
    fi

    if [ -z "${BOT_TOKEN}" ]; then
        # Check alternative names
        if [ -n "${TOKEN}" ]; then
            export BOT_TOKEN="${TOKEN}"
        elif [ -n "${TELEGRAM_BOT_TOKEN}" ]; then
            export BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
        else
            log_error "BOT_TOKEN environment variable is required"
            exit 1
        fi
    fi

    # Wait for PostgreSQL
    if ! wait_for_postgres; then
        exit 1
    fi

    # Create database if needed
    create_database_if_needed

    # Run migrations
    if ! run_migrations; then
        log_error "Failed to initialize database"
        exit 1
    fi

    log_info "Initialization complete, starting bot..."

    # Execute the main command
    exec "$@"
}

# Run main function
main "$@"