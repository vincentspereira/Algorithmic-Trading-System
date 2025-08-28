@echo off

REM Production Deployment Script for Windows
REM This script automates the deployment of the trading system to a production environment.

echo Pulling latest code...
git pull origin main

echo Building and starting production containers...
docker-compose -f docker-compose.prod.yml up --build -d

REM Run database migrations (if any)
REM echo Running database migrations...
REM docker-compose -f docker-compose.prod.yml exec -T postgres alembic upgrade head

echo Verifying container status...
docker-compose -f docker-compose.prod.yml ps

echo Production deployment completed successfully.