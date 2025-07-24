#!/bin/bash

# Phase 1 Infrastructure Startup Script
# Algorithmic Trading System

set -e

echo "=========================================="
echo "Algorithmic Trading System - Phase 1"
echo "Foundational Infrastructure Startup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success ".env file created from .env.example"
        print_warning "Please review and update the .env file with your preferred settings"
        print_warning "Especially update the PostgreSQL password for security"
    else
        print_error ".env.example file not found. Cannot create .env file."
        exit 1
    fi
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p config/postgres
mkdir -p config/jmx-exporter
mkdir -p nautilus_trader_engine
mkdir -p scripts

# Check if all required configuration files exist
required_files=(
    "config/prometheus.yml"
    "config/postgres/init.sql"
    "config/jmx-exporter/config.yaml"
    "nautilus_trader_engine/Dockerfile"
    "nautilus_trader_engine/main.py"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -ne 0 ]; then
    print_error "Missing required configuration files:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    print_error "Please ensure all configuration files are present before starting."
    exit 1
fi

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down > /dev/null 2>&1 || true

# Pull latest images
print_status "Pulling latest Docker images..."
docker-compose pull

# Build custom images
print_status "Building custom images..."
docker-compose build

# Start services
print_status "Starting Phase 1 services..."
print_status "This may take a few minutes on first run..."

# Start services in dependency order
print_status "Starting Zookeeper..."
docker-compose up -d zookeeper
sleep 10

print_status "Starting Kafka..."
docker-compose up -d kafka
sleep 15

print_status "Starting Schema Registry..."
docker-compose up -d schema-registry
sleep 10

print_status "Starting databases..."
docker-compose up -d postgres clickhouse duckdb
sleep 20

print_status "Starting monitoring services..."
docker-compose up -d prometheus grafana jmx-exporter
sleep 10

print_status "Starting management interfaces..."
docker-compose up -d pgadmin
sleep 5

print_status "Starting Nautilus Trader Engine..."
docker-compose up -d nautilus_trader_engine
sleep 15

# Check service status
print_status "Checking service status..."
docker-compose ps

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Display service URLs
echo ""
print_success "Phase 1 infrastructure started successfully!"
echo ""
echo "=========================================="
echo "SERVICE ENDPOINTS"
echo "=========================================="
echo "🚀 Nautilus Trader Engine:  http://localhost:8000"
echo "📊 Grafana Dashboard:       http://localhost:3000 (admin/admin)"
echo "📈 Prometheus:              http://localhost:9090"
echo "🗄️  pgAdmin:                 http://localhost:5433 (admin@trading.com/admin)"
echo "📋 Schema Registry:         http://localhost:8081"
echo "📊 ClickHouse:              http://localhost:8123"
echo "📊 JMX Exporter:            http://localhost:5556"
echo ""
echo "=========================================="
echo "NEXT STEPS"
echo "=========================================="
echo "1. Validate the infrastructure:"
echo "   python3 scripts/validate_phase1.py"
echo ""
echo "2. Check service health:"
echo "   curl http://localhost:8000/health"
echo ""
echo "3. View service logs:"
echo "   docker-compose logs -f"
echo ""
echo "4. Access Grafana dashboards at http://localhost:3000"
echo ""
echo "5. Review the Phase 1 documentation:"
echo "   cat README_PHASE1.md"
echo ""
print_success "Phase 1 infrastructure is ready for development!"
echo ""

# Optional: Run validation script if available
if [ -f "scripts/validate_phase1.py" ]; then
    echo "=========================================="
    read -p "Would you like to run the validation script now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Running infrastructure validation..."
        python3 scripts/validate_phase1.py
    fi
fi

print_success "Startup complete! Happy trading! 🚀"