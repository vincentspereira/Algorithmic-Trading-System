#!/bin/bash

# Environment variables
export KAFKA_SERVERS=kafka:9092
export REDIS_HOST=redis
export CLICKHOUSE_HOST=clickhouse

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "🚀 Starting deployment..."

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/clickhouse data/redis

# Build and start services
echo "🏗️ Building and starting services..."
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Initialize ClickHouse schema
echo "🗄️ Initializing ClickHouse schema..."
cat backtesting/service/schema.sql | docker exec -i $(docker-compose ps -q clickhouse) clickhouse-client

# Check services health
echo "🏥 Checking services health..."

check_service() {
    local service=$1
    local port=$2
    local endpoint=$3
    
    if nc -z localhost $port; then
        echo "${GREEN}✓ $service is running on port $port${NC}"
        return 0
    else
        echo "${RED}✗ $service is not responding on port $port${NC}"
        return 1
    fi
}

services_ok=true

# Check each service
check_service "Frontend" 3000 || services_ok=false
check_service "Backtest Service" 8000 || services_ok=false
check_service "ClickHouse" 8123 || services_ok=false
check_service "Kafka" 9092 || services_ok=false
check_service "Redis" 6379 || services_ok=false

if [ "$services_ok" = true ]; then
    echo "${GREEN}✅ All services are running!${NC}"
    echo "
    📊 Access the services:
    - Frontend: http://localhost:3000
    - Backtest API: http://localhost:8000/docs
    - ClickHouse UI: http://localhost:8123/play
    
    📝 Test the system with:
    curl -X POST http://localhost:8000/api/backtest \\
         -H 'Content-Type: application/json' \\
         -d '{
             \"strategy\": {
                 \"symbol\": \"AAPL\",
                 \"start_date\": \"2025-01-01T00:00:00Z\",
                 \"end_date\": \"2025-08-24T00:00:00Z\",
                 \"timeframe\": \"1d\",
                 \"fast_ma\": 20,
                 \"slow_ma\": 50
             }
         }'
    "
else
    echo "${RED}❌ Some services failed to start. Check the logs with:${NC}"
    echo "docker-compose logs"
    exit 1
fi
