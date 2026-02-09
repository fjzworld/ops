#!/bin/bash
set -e

echo "==================================="
echo "OPS Platform Backend Initialization"
echo "==================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to log messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for PostgreSQL to be ready
log_info "Waiting for PostgreSQL to be ready..."
max_retries=30
retry_count=0

while ! pg_isready -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER:-opsuser}" > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        log_error "PostgreSQL is not available after ${max_retries} retries"
        exit 1
    fi
    log_warn "PostgreSQL is unavailable - sleeping (attempt $retry_count/$max_retries)"
    sleep 2
done

log_info "PostgreSQL is ready!"

# Wait for Redis to be ready
log_info "Waiting for Redis to be ready..."
retry_count=0

while ! redis-cli -h "${REDIS_HOST:-redis}" ping > /dev/null 2>&1; do
    retry_count=$((retry_count + 1))
    if [ $retry_count -ge $max_retries ]; then
        log_error "Redis is not available after ${max_retries} retries"
        exit 1
    fi
    log_warn "Redis is unavailable - sleeping (attempt $retry_count/$max_retries)"
    sleep 2
done

log_info "Redis is ready!"

# Run database migrations with Alembic (if exists)
if [ -f "alembic.ini" ]; then
    log_info "Running database migrations..."
    alembic upgrade head
    log_info "Database migrations completed!"
else
    log_warn "No alembic.ini found, skipping migrations"
    log_info "Creating database tables..."
    python -c "from app.core.database import Base, engine; Base.metadata.create_all(bind=engine)"
    log_info "Database tables created!"
fi

# Validate environment variables
log_info "Validating environment variables..."

if [ "${SECRET_KEY}" = "your-secret-key-change-in-production" ] || [ "${SECRET_KEY}" = "CHANGE_ME_GENERATE_RANDOM_KEY_WITH_openssl_rand_hex_32" ]; then
    log_error "SECRET_KEY is using default value! Please set a secure random key."
    log_error "Generate one with: openssl rand -hex 32"
    if [ "${ENVIRONMENT}" = "production" ]; then
        exit 1
    else
        log_warn "Continuing in development mode with insecure key..."
    fi
fi

if [ "${POSTGRES_PASSWORD}" = "opspass" ] || [ "${POSTGRES_PASSWORD}" = "CHANGE_ME_STRONG_PASSWORD_HERE" ]; then
    log_warn "POSTGRES_PASSWORD is using a weak or default value!"
    if [ "${ENVIRONMENT}" = "production" ]; then
        log_error "Cannot start in production with weak database password!"
        exit 1
    fi
fi

log_info "Environment validation completed!"

# Initialize default data (optional)
if [ "${INIT_DEFAULT_DATA:-false}" = "true" ]; then
    log_info "Initializing default data..."
    if [ -f "scripts/init_data.py" ]; then
        python scripts/init_data.py
        log_info "Default data initialized!"
    else
        log_warn "No init_data.py script found, skipping"
    fi
fi

log_info "Initialization completed successfully!"
echo "==================================="

# Execute the main command
log_info "Starting application: $@"
exec "$@"
