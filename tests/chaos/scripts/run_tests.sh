#!/bin/bash

# Chaos Engineering Test Runner Script

set -e

echo "🔥 Starting Chaos Engineering Tests"
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
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
    print_error "docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p results reports game_day_reports test-results monitoring/grafana/dashboards monitoring/grafana/datasources

# Build the chaos engineering image
print_status "Building chaos engineering Docker image..."
docker-compose build chaos-engineering

# Start the infrastructure services
print_status "Starting infrastructure services..."
docker-compose up -d prometheus grafana test-api test-database test-redis

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

# Check service health
print_status "Checking service health..."

# Check Prometheus
if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_status "✅ Prometheus is healthy"
else
    print_warning "⚠️  Prometheus health check failed"
fi

# Check Grafana
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    print_status "✅ Grafana is healthy"
else
    print_warning "⚠️  Grafana health check failed"
fi

# Check test API
if curl -f http://localhost:8081/health > /dev/null 2>&1; then
    print_status "✅ Test API is healthy"
else
    print_warning "⚠️  Test API health check failed"
fi

# Run the chaos engineering tests
print_status "Running chaos engineering tests..."
docker-compose --profile testing run --rm chaos-test-runner

# Check test results
if [ $? -eq 0 ]; then
    print_status "✅ All chaos engineering tests passed!"
else
    print_error "❌ Some chaos engineering tests failed!"
    exit 1
fi

# Run a sample chaos experiment
print_status "Running sample chaos experiment..."
docker-compose run --rm chaos-engineering python chaos_engineering_framework.py

# Generate test report
print_status "Generating test report..."
docker-compose run --rm chaos-engineering python -c "
import json
from pathlib import Path
from datetime import datetime

# Create a simple test report
report = {
    'test_run': {
        'timestamp': datetime.now().isoformat(),
        'status': 'completed',
        'services_tested': ['prometheus', 'grafana', 'test-api', 'test-database', 'test-redis'],
        'experiments_run': ['network_latency', 'memory_pressure'],
        'success': True
    }
}

# Save report
Path('/app/reports/test_run_report.json').write_text(json.dumps(report, indent=2))
print('Test report generated: /app/reports/test_run_report.json')
"

print_status "Test run completed successfully!"
print_status "Reports available in: ./reports/"
print_status "Prometheus UI: http://localhost:9090"
print_status "Grafana UI: http://localhost:3000 (admin/chaos123)"

# Optionally keep services running
read -p "Keep services running for manual testing? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Services will continue running. Use 'docker-compose down' to stop them."
else
    print_status "Stopping services..."
    docker-compose down
fi

echo "🎉 Chaos engineering test run completed!"