# Use Python 3.12 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY notification_service/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and templates
COPY notification_service/ .

# Create config directory
RUN mkdir -p /app/config

# Environment variables for configuration
ENV SLACK_WEBHOOK_URL=""
ENV TEAMS_WEBHOOK_URL=""
ENV EMAIL_SMTP_SERVER=""
ENV EMAIL_SMTP_PORT=""
ENV EMAIL_USERNAME=""
ENV EMAIL_PASSWORD=""

# Expose port for API
EXPOSE 8001

# Run the service
CMD ["python", "-m", "notification_service"]
