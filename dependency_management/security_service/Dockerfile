# Use Python 3.12 slim image
FROM python:3.11-slim

# Install git and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY security_service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and config
COPY security_service/ .

# Make sure dependencies.json is in the correct location
RUN ls -la /app

# Environment variables
ENV NVD_API_KEY=""
ENV GITHUB_TOKEN=""

# Expose port for API
EXPOSE 8002

# Run the service
CMD ["python", "-m", "security_service"]
