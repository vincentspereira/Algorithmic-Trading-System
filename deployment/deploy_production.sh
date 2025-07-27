#!/bin/bash

# Production Deployment Script
# This script automates the deployment of the trading system to a production environment.

# Exit immediately if a command exits with a non-zero status.
set -e

# 1. Pull the latest code from the repository
echo "Pulling latest code..."
git pull origin main

# 2. Build and start the Docker containers in detached mode
echo "Building and starting production containers..."
docker-compose -f docker-compose.prod.yml up --build -d

# 3. Run database migrations (if any)
# echo "Running database migrations..."
# docker-compose -f docker-compose.prod.yml exec -T postgres alembic upgrade head

# 4. Verify that all containers are running
echo "Verifying container status..."
docker-compose -f docker-compose.prod.yml ps

echo "Production deployment completed successfully."