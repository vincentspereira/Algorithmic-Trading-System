# AI Assistant Service Dockerfile for Algorithmic Trading System - Phase 3
# Uses Python 3.11 as base image with all required packages for LangChain integration

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8002

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    langchain==0.1.0 \
    langgraph==0.0.26 \
    TradingAgents==0.1.0 \
    openbb==4.1.6 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    requests==2.31.0 \
    python-dotenv==1.0.0 \
    ollama==0.1.7 \
    pydantic==2.5.0 \
    httpx==0.25.2 \
    aiofiles==23.2.1 \
    python-multipart==0.0.6 \
    jinja2==3.1.2 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    pandas==2.1.4 \
    numpy==1.24.3 \
    scikit-learn==1.3.2 \
    matplotlib==3.8.2 \
    plotly==5.17.0 \
    yfinance==0.2.28 \
    websockets==12.0 \
    redis==5.0.1 \
    celery==5.3.4 \
    sqlalchemy==2.0.23 \
    alembic==1.13.1 \
    psycopg2-binary==2.9.9 \
    prometheus-client==0.19.0 \
    structlog==23.2.0

# Install additional requirements if they exist
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/models && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 8002 (avoiding conflict with Phase 2 API on 8001)
EXPOSE 8002

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Set up entry point
ENTRYPOINT ["python", "-m", "uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "1"]

# Labels for better container management
LABEL maintainer="Algorithmic Trading System Team" \
      version="1.0.0" \
      description="AI Assistant Service for Algorithmic Trading System - Phase 3" \
      service="ai-assistant" \
      phase="3" \
      port="8002"

# Environment variables with defaults
ENV PHASE2_API_BASE_URL=http://localhost:8001 \
    AI_ASSISTANT_PORT=8002 \
    AI_ASSISTANT_HOST=0.0.0.0 \
    ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080 \
    OLLAMA_BASE_URL=http://localhost:11434 \
    DEBUG=false \
    LOG_LEVEL=info

# Volume mounts for persistent data
VOLUME ["/app/logs", "/app/data", "/app/models"]