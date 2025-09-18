# Multi-stage build for production optimization
FROM python:3.11-slim as base

# Set build arguments
ARG PYTHON_VERSION=3.11
ARG NODE_VERSION=18

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure poetry and install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-root \
    && rm -rf $POETRY_CACHE_DIR

# Frontend build stage
FROM node:${NODE_VERSION}-alpine as frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm ci --only=production

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Production stage
FROM python:3.11-slim as production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy Python dependencies from base stage
COPY --from=base /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base /usr/local/bin /usr/local/bin

# Copy built frontend from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/temp \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8000 8001 8002

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

# Install development dependencies
RUN poetry install --with dev

# Install additional development tools
RUN pip install debugpy pytest-xdist

# Copy application code
COPY . .

# Create development user
RUN groupadd -r devuser && useradd -r -g devuser devuser \
    && mkdir -p /app/logs /app/data /app/temp \
    && chown -R devuser:devuser /app

USER devuser

# Expose additional development ports
EXPOSE 8000 8001 8002 5678

# Development command with hot reload
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Testing stage
FROM development as testing

# Copy test files
COPY tests/ ./tests/

# Run tests
RUN python -m pytest tests/ -v --tb=short

# Worker stage for background tasks
FROM production as worker

# Override command for worker processes
CMD ["python", "-m", "celery", "worker", "-A", "shared.tasks.celery_app", "--loglevel=info"]

# Scheduler stage for periodic tasks
FROM production as scheduler

# Override command for scheduler
CMD ["python", "-m", "celery", "beat", "-A", "shared.tasks.celery_app", "--loglevel=info"]

# Market data service stage
FROM production as market-data

# Expose market data specific port
EXPOSE 8001

# Override command for market data service
CMD ["python", "-m", "services.market_data.main"]

# Trading engine stage
FROM production as trading-engine

# Expose trading engine specific port
EXPOSE 8002

# Override command for trading engine
CMD ["python", "-m", "services.trading_engine.main"]