# Nautilus Trader Engine - Multi-Stage Docker Build
# Optimized for production deployment with security and performance in mind

# ================================
# Base Stage - Common Dependencies
# ================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r nautilus && useradd -r -g nautilus nautilus

# Set working directory
WORKDIR /app

# ================================
# Development Stage
# ================================
FROM base as development

# Copy requirements for development
COPY requirements-dev.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-dev.txt

# Copy source code
COPY . .

# Change ownership to non-root user
RUN chown -R nautilus:nautilus /app

# Switch to non-root user
USER nautilus

# Expose port for development server
EXPOSE 8000

# Default command for development
CMD ["python", "-m", "nautilus_trader_engine"]

# ================================
# Testing Stage
# ================================
FROM development as testing

# Run tests
RUN python -m pytest tests/ -v --cov=nautilus_trader_engine --cov-report=xml

# ================================
# Builder Stage - Dependencies Only
# ================================
FROM base as builder

# Copy requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# ================================
# Production Stage
# ================================
FROM python:3.11-slim as production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r nautilus && useradd -r -g nautilus nautilus

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/nautilus/.local

# Copy application code
COPY nautilus_trader_engine/ ./nautilus_trader_engine/
COPY scripts/ ./scripts/
COPY config/ ./config/

# Change ownership to non-root user
RUN chown -R nautilus:nautilus /app

# Create necessary directories
RUN mkdir -p /app/logs /app/data /app/cache && \
    chown -R nautilus:nautilus /app/logs /app/data /app/cache

# Set environment variables for production
ENV PATH=/home/nautilus/.local/bin:$PATH \
    PYTHONPATH=/app

# Switch to non-root user
USER nautilus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command for production
CMD ["python", "-m", "nautilus_trader_engine.core.main"]

# ================================
# GPU Stage - For ML workloads
# ================================
FROM python:3.11-slim as gpu

# Install CUDA runtime (adjust version as needed)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub | apt-key add - \
    && echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64 /" > /etc/apt/sources.list.d/cuda.list \
    && apt-get update && apt-get install -y \
    cuda-runtime-11-8 \
    libcudnn8 \
    && rm -rf /var/lib/apt/lists/*

# Copy from production stage
COPY --from=production /app /app
COPY --from=builder /root/.local /home/nautilus/.local

# Install GPU-specific packages
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Set GPU environment variables
ENV CUDA_VISIBLE_DEVICES=0 \
    PATH=/home/nautilus/.local/bin:$PATH \
    PYTHONPATH=/app

# Switch to non-root user
USER nautilus

# Health check for GPU
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "import torch; print('GPU available:', torch.cuda.is_available())" || exit 1

# ================================
# Debug Stage - For troubleshooting
# ================================
FROM production as debug

# Install debugging tools
USER root
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    net-tools \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Switch back to non-root user
USER nautilus

# Enable debug mode
ENV DEBUG=1

# ================================
# Minimal Stage - Ultra-lightweight
# ================================
FROM python:3.11-alpine as minimal

# Install minimal runtime dependencies
RUN apk add --no-cache \
    curl \
    && addgroup -g 1000 nautilus \
    && adduser -D -s /bin/sh -u 1000 -G nautilus nautilus

# Set working directory
WORKDIR /app

# Copy minimal application code
COPY --from=production /app/nautilus_trader_engine/core /app/nautilus_trader_engine/core
COPY --from=production /app/nautilus_trader_engine/__init__.py /app/nautilus_trader_engine/
COPY --from=builder /root/.local /home/nautilus/.local

# Set environment
ENV PATH=/home/nautilus/.local/bin:$PATH \
    PYTHONPATH=/app

# Switch to non-root user
USER nautilus

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-c", "print('Nautilus Trader Engine Minimal Container Running')"]