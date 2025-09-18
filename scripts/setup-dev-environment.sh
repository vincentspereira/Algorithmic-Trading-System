#!/bin/bash
# =============================================================================
# Algorithmic Trading System - Development Environment Setup Script
# =============================================================================
# This script sets up the complete development environment using Docker Compose

set -e

# Default values
PROFILE="development"
SKIP_BUILD=false
CLEAN=false
MONITORING=false
AI=false
TESTING=false

# Color functions for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function log_info() {
    echo -e "${CYAN}$1${NC}"
}

function log_success() {
    echo -e "${GREEN}$1${NC}"
}

function log_warning() {
    echo -e "${YELLOW}$1${NC}"
}

function log_error() {
    echo -e "${RED}$1${NC}"
}

function show_help() {
    log_info "Algorithmic Trading System - Development Environment Setup"
    log_info "================================================================"
    echo ""
    log_info "Usage: ./setup-dev-environment.sh [OPTIONS]"
    echo ""
    log_info "Options:"
    log_info "  -p, --profile <name>    Docker Compose profile to use (default: development)"
    log_info "  -s, --skip-build        Skip building Docker images"
    log_info "  -c, --clean             Clean up existing containers and volumes"
    log_info "  -m, --monitoring        Include monitoring services (Prometheus, Grafana)"
    log_info "  -a, --ai                Include AI services (Qdrant, Jupyter)"
    log_info "  -t, --testing           Include testing services"
    log_info "  -h, --help              Show this help message"
    echo ""
    log_info "Examples:"
    log_info "  ./setup-dev-environment.sh                     # Basic development setup"
    log_info "  ./setup-dev-environment.sh -m                  # With monitoring"
    log_info "  ./setup-dev-environment.sh -a -m               # Full setup"
    log_info "  ./setup-dev-environment.sh -c                  # Clean and restart"
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--profile)
            PROFILE="$2"
            shift 2
            ;;
        -s|--skip-build)
            SKIP_BUILD=true
            shift
            ;;
        -c|--clean)
            CLEAN=true
            shift
            ;;
        -m|--monitoring)
            MONITORING=true
            shift
            ;;
        -a|--ai)
            AI=true
            shift
            ;;
        -t|--testing)
            TESTING=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Check if Docker is installed and running
function check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "❌ Docker is not installed"
        log_error "Please install Docker and Docker Compose"
        log_error "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "❌ Docker daemon is not running"
        log_error "Please start Docker and try again"
        exit 1
    fi
    
    if ! docker compose version &> /dev/null; then
        log_error "❌ Docker Compose is not available"
        log_error "Please install Docker Compose"
        exit 1
    fi
    
    log_success "✓ Docker is installed and running"
    log_success "✓ Docker Compose is available"
}

# Check if required files exist
function check_required_files() {
    local required_files=("docker-compose.yml" "Dockerfile" ".env.example")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -gt 0 ]]; then
        log_error "❌ Missing required files:"
        for file in "${missing_files[@]}"; do
            log_error "  - $file"
        done
        exit 1
    fi
    
    log_success "✓ All required files are present"
}

# Setup environment file
function setup_environment() {
    if [[ ! -f ".env" ]]; then
        log_info "📝 Creating .env file from .env.example..."
        cp ".env.example" ".env"
        log_success "✓ .env file created"
        log_warning "⚠️  Please review and update the .env file with your specific configuration"
    else
        log_success "✓ .env file already exists"
    fi
}

# Build profiles array
function get_profiles() {
    local profiles=("$PROFILE")
    
    if [[ "$MONITORING" == true ]]; then
        profiles+=("monitoring")
    fi
    
    if [[ "$AI" == true ]]; then
        profiles+=("ai")
    fi
    
    if [[ "$TESTING" == true ]]; then
        profiles+=("testing")
    fi
    
    echo "${profiles[@]}"
}

# Clean up existing containers and volumes
function cleanup() {
    log_info "🧹 Cleaning up existing containers and volumes..."
    
    # Stop all containers
    docker compose down --remove-orphans 2>/dev/null || true
    
    # Remove volumes (optional - commented out to preserve data)
    # docker compose down --volumes 2>/dev/null || true
    
    # Prune unused Docker resources
    docker system prune -f 2>/dev/null || true
    
    log_success "✓ Cleanup completed"
}

# Build Docker images
function build_images() {
    if [[ "$SKIP_BUILD" == true ]]; then
        log_info "⏭️  Skipping Docker image build"
        return
    fi
    
    log_info "🔨 Building Docker images..."
    
    local profiles
    IFS=' ' read -ra profiles <<< "$(get_profiles)"
    
    local profile_args=()
    for profile in "${profiles[@]}"; do
        profile_args+=("--profile" "$profile")
    done
    
    log_info "Running: docker compose ${profile_args[*]} build --parallel"
    
    if ! docker compose "${profile_args[@]}" build --parallel; then
        log_error "❌ Docker build failed"
        exit 1
    fi
    
    log_success "✓ Docker images built successfully"
}

# Start services
function start_services() {
    log_info "🚀 Starting services..."
    
    local profiles
    IFS=' ' read -ra profiles <<< "$(get_profiles)"
    
    local profile_args=()
    for profile in "${profiles[@]}"; do
        profile_args+=("--profile" "$profile")
    done
    
    log_info "Running: docker compose ${profile_args[*]} up -d"
    
    if ! docker compose "${profile_args[@]}" up -d; then
        log_error "❌ Failed to start services"
        exit 1
    fi
    
    log_success "✓ Services started successfully"
}

# Wait for services to be healthy
function wait_for_services() {
    log_info "⏳ Waiting for services to be healthy..."
    
    local max_wait=300  # 5 minutes
    local waited=0
    local interval=10
    
    while [[ $waited -lt $max_wait ]]; do
        local unhealthy_count
        unhealthy_count=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.Health == "unhealthy" or .State == "exited") | .Name' 2>/dev/null | wc -l || echo "0")
        
        if [[ $unhealthy_count -eq 0 ]]; then
            log_success "✓ All services are healthy"
            return
        fi
        
        log_info "Waiting for services... ($waited/$max_wait seconds)"
        sleep $interval
        waited=$((waited + interval))
    done
    
    log_warning "⚠️  Some services may not be fully ready. Check with 'docker compose ps'"
}

# Show service status and URLs
function show_service_info() {
    log_info "📊 Service Status:"
    docker compose ps --format table
    
    echo ""
    log_info "🌐 Available Services:"
    log_info "  Frontend Application:    http://localhost:3000"
    log_info "  API Gateway:            http://localhost:8001"
    log_info "  Market Data Service:    http://localhost:8002"
    log_info "  Trading Engine:         http://localhost:8003"
    log_info "  Portfolio Manager:      http://localhost:8004"
    log_info "  Risk Manager:           http://localhost:8005"
    log_info "  AI Assistant:           http://localhost:8006"
    
    if [[ "$MONITORING" == true ]]; then
        log_info "  Prometheus:             http://localhost:9090"
        log_info "  Grafana:                http://localhost:3001"
        log_info "  Jaeger:                 http://localhost:16686"
        log_info "  Kafka UI:               http://localhost:8080"
    fi
    
    if [[ "$AI" == true ]]; then
        log_info "  Jupyter Lab:            http://localhost:8888"
        log_info "  Qdrant Dashboard:       http://localhost:6333/dashboard"
    fi
    
    log_info "  MinIO Console:          http://localhost:9001"
    log_info "  Keycloak:               http://localhost:8090"
    echo ""
    log_info "📚 Documentation:"
    log_info "  API Documentation:      http://localhost:8001/docs"
    log_info "  WebSocket API:          ws://localhost:8001/ws"
    echo ""
    log_info "🔧 Management Commands:"
    log_info "  View logs:              docker compose logs -f [service_name]"
    log_info "  Stop services:          docker compose down"
    log_info "  Restart service:        docker compose restart [service_name]"
    log_info "  Shell access:           docker compose exec [service_name] /bin/bash"
}

# Main execution
function main() {
    log_info "🚀 Algorithmic Trading System - Development Environment Setup"
    log_info "================================================================"
    
    # Pre-flight checks
    check_docker
    check_required_files
    
    # Setup environment
    setup_environment
    
    # Clean up if requested
    if [[ "$CLEAN" == true ]]; then
        cleanup
    fi
    
    # Build and start services
    build_images
    start_services
    
    # Wait for services to be ready
    wait_for_services
    
    # Show service information
    show_service_info
    
    log_success "🎉 Development environment is ready!"
    log_info "💡 Tip: Use 'docker compose logs -f' to monitor service logs"
}

# Make script executable and run main function
chmod +x "$0" 2>/dev/null || true
main