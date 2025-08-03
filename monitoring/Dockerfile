FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for monitoring tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    curl \
    wget \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy monitoring requirements file
COPY monitoring/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy monitoring source code
COPY monitoring/ ./monitoring/

# Create necessary directories
RUN mkdir -p /app/data/metrics /app/data/logs /app/data/alerts /app/config

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MONITORING_MODE=production

# Expose ports for monitoring services
EXPOSE 8090 8091 8092 9090 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8090/health || exit 1

# Default command
CMD ["python", "monitoring/monitoring_server.py"]