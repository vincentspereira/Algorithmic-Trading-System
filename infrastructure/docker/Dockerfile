# Use Python 3.11 slim as base image for optimal performance
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for NautilusTrader and financial libraries
# Including CUDA support for VectorBT GPU acceleration
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    cmake \
    git \
    curl \
    wget \
    pkg-config \
    libssl-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    libblas-dev \
    liblapack-dev \
    gfortran \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library
RUN cd /tmp && \
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr --libdir=/usr/lib --includedir=/usr/include && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/ta-lib*

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Set environment variables for TA-Lib
ENV TA_INCLUDE_PATH="/usr/include"
ENV TA_LIBRARY_PATH="/usr/lib"

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/config /app/data /app/logs

# Copy application code
COPY . /app/

# Set Python path
ENV PYTHONPATH=/app

# Create non-root user for security
RUN useradd -m -u 1000 trader && \
    chown -R trader:trader /app
USER trader

# Expose port for FastAPI
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
