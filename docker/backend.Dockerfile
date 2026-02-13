# ==============================================
# Stage 1: Builder
# ==============================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies for building Python packages (psycopg2, etc.)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================
# Stage 2: Runtime
# ==============================================
FROM python:3.11-slim as runtime

WORKDIR /app

# distinct user for security
RUN groupadd -r opsuser && useradd -r -g opsuser opsuser

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y \
    libpq5 \
    postgresql-client \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder with correct ownership
COPY --from=builder --chown=opsuser:opsuser /opt/venv /opt/venv

# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code with correct ownership
COPY --chown=opsuser:opsuser . .

# Set permissions for entrypoint script
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER opsuser

# Expose port
EXPOSE 8000

# Use entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
