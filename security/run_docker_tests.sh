#!/bin/bash

# Fraud Detection Docker Test Runner
# This script builds and runs comprehensive tests in Docker environment

set -e

echo "🐳 Fraud Detection System - Docker Test Suite"
echo "=============================================="

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

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Navigate to security directory
cd "$(dirname "$0")"

# Clean up any existing containers
print_status "Cleaning up existing containers..."
docker-compose down --remove-orphans 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# Build the Docker image
print_status "Building Docker image..."
if docker-compose build fraud-detection-test; then
    print_success "Docker image built successfully"
else
    print_error "Failed to build Docker image"
    exit 1
fi

# Run the comprehensive tests
print_status "Running comprehensive fraud detection tests..."
echo "================================================"

if docker-compose run --rm fraud-detection-test; then
    print_success "All tests completed successfully!"
    
    # Copy test results from container
    print_status "Copying test results..."
    docker-compose run --rm -v "$(pwd):/host" fraud-detection-test cp /app/security/COMPREHENSIVE_TEST_REPORT.json /host/ 2>/dev/null || true
    
    if [ -f "COMPREHENSIVE_TEST_REPORT.json" ]; then
        print_success "Test report saved to COMPREHENSIVE_TEST_REPORT.json"
        
        # Display summary
        echo ""
        echo "📊 TEST SUMMARY"
        echo "==============="
        
        if command -v jq &> /dev/null; then
            jq -r '.summary | "Total Tests: \(.total_tests)\nPassed: \(.passed_tests)\nFailed: \(.failed_tests)\nSuccess Rate: \(.success_rate)"' COMPREHENSIVE_TEST_REPORT.json
        else
            print_warning "jq not available - install jq to see formatted test summary"
            echo "Raw test summary:"
            grep -o '"summary":{[^}]*}' COMPREHENSIVE_TEST_REPORT.json || echo "Could not extract summary"
        fi
    fi
    
else
    print_error "Tests failed!"
    
    # Show container logs for debugging
    print_status "Showing container logs for debugging..."
    docker-compose logs fraud-detection-test
    
    exit 1
fi

# Optional: Run the server for manual testing
read -p "Do you want to start the fraud detection server for manual testing? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Starting fraud detection server..."
    print_status "Server will be available at http://localhost:8080"
    print_status "Press Ctrl+C to stop the server"
    
    docker-compose up fraud-detection-server
fi

# Clean up
print_status "Cleaning up..."
docker-compose down --remove-orphans

print_success "Docker test suite completed!"
echo ""
echo "📋 Next Steps:"
echo "- Review the test report: COMPREHENSIVE_TEST_REPORT.json"
echo "- Check logs for any warnings or issues"
echo "- Deploy to production if all tests passed"