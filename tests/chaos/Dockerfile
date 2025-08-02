FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    procps \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy chaos engineering framework
COPY . .

# Create directories for results and reports
RUN mkdir -p /app/results /app/reports /app/game_day_reports

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port for monitoring (if needed)
EXPOSE 8080

# Default command
CMD ["python", "chaos_engineering_framework.py"]