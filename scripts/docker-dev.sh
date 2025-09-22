#!/bin/bash

# Nautilus Trader Engine - Docker Development Script
# Simplifies common Docker development tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to show usage
show_usage() {
    cat << EOF
Nautilus Trader Engine - Docker Development Script

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    build           Build all Docker images
    up              Start all services
    down            Stop all services
    restart         Restart all services
    logs            Show logs from all services
    shell           Open shell in main container
    test            Run tests in container
    clean           Remove all containers and volumes
    status          Show status of all services
    setup           Initial setup (build + up)
    dev             Start development environment
    prod            Start production environment
    monitor         Start with monitoring stack
    help            Show this help message

EXAMPLES:
    $0 setup                    # Initial setup
    $0 dev                      # Start development environment
    $0 test                     # Run tests
    $0 logs nautilus-trader-engine  # Show logs for specific service
    $0 shell                    # Open shell in main container

EOF
}

# Function to build images
build_images() {
    print_info "Building Docker images..."
    docker-compose build --parallel
    print_success "Images built successfully"
}

# Function to start services
start_services() {
    local profile=${1:-""}
    print_info "Starting services..."
    if [ -n "$profile" ]; then
        docker-compose --profile $profile up -d
    else
        docker-compose up -d
    fi
    print_success "Services started successfully"
    show_status
}

# Function to stop services
stop_services() {
    print_info "Stopping services..."
    docker-compose down
    print_success "Services stopped successfully"
}

# Function to show status
show_status() {
    print_info "Service Status:"
    docker-compose ps
    echo ""
    print_info "Health Check:"
    if curl -f http://localhost:8000/health >/dev/null 2>&1; then
        print_success "Main application is healthy"
    else
        print_warning "Main application health check failed"
    fi
}

# Function to show logs
show_logs() {
    local service=${1:-""}
    if [ -n "$service" ]; then
        docker-compose logs -f $service
    else
        docker-compose logs -f
    fi
}

# Function to open shell
open_shell() {
    print_info "Opening shell in main container..."
    docker-compose exec nautilus-trader-engine /bin/bash
}

# Function to run tests
run_tests() {
    print_info "Running tests..."
    docker-compose exec nautilus-trader-engine pytest tests/ -v --tb=short
}

# Function to clean up
cleanup() {
    print_warning "This will remove all containers and volumes. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "Cleaning up..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_info "Cleanup cancelled"
    fi
}

# Function to setup development environment
setup_dev() {
    print_info "Setting up development environment..."
    build_images
    start_services "dev"
    print_success "Development environment ready!"
    echo ""
    print_info "Access points:"
    echo "  - API: http://localhost:8002"
    echo "  - API Docs: http://localhost:8002/docs"
    echo "  - PgAdmin: http://localhost:5050 (admin@nautilus.dev / admin)"
    echo "  - Redis Commander: http://localhost:8081"
}

# Function to setup production environment
setup_prod() {
    print_info "Setting up production environment..."
    build_images
    start_services
    print_success "Production environment ready!"
    echo ""
    print_info "Access points:"
    echo "  - API: http://localhost:8000"
    echo "  - API Docs: http://localhost:8000/docs"
    echo "  - Metrics: http://localhost:8001/metrics"
}

# Function to setup monitoring environment
setup_monitoring() {
    print_info "Setting up monitoring environment..."
    build_images
    start_services "monitoring"
    print_success "Monitoring environment ready!"
    echo ""
    print_info "Access points:"
    echo "  - Grafana: http://localhost:3000 (admin/admin)"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Application: http://localhost:8000"
}

# Main script logic
main() {
    check_docker

    case "${1:-help}" in
        build)
            build_images
            ;;
        up)
            start_services
            ;;
        down)
            stop_services
            ;;
        restart)
            stop_services
            start_services
            ;;
        logs)
            show_logs "$2"
            ;;
        shell)
            open_shell
            ;;
        test)
            run_tests
            ;;
        clean)
            cleanup
            ;;
        status)
            show_status
            ;;
        setup)
            build_images
            start_services
            ;;
        dev)
            setup_dev
            ;;
        prod)
            setup_prod
            ;;
        monitor)
            setup_monitoring
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"