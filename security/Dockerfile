# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies
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
COPY security/requirements.txt .

# Install security scanning dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install additional security tools
RUN pip install bandit[toml] semgrep

# Copy security scanning scripts
COPY security/ .

# Make scripts executable
RUN chmod +x comprehensive_security_scan.py threat_modeling.py

# Create directory for reports
RUN mkdir -p security_reports

# Environment variables
ENV NVD_API_KEY=""
ENV SEMGREP_APP_TOKEN=""

# Run the comprehensive security scan by default
CMD ["python", "comprehensive_security_scan.py"]