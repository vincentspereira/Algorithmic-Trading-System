#!/bin/bash

# Algorithmic Trading System Deployment Script
# This script handles deployment to different environments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_REGISTRY="ghcr.io"
IMAGE_NAME="algorithmic-trading-system"
KUBECTL_TIMEOUT="600s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
    cat << EOF
Algorithmic Trading System Deployment Script

Usage: $0 [OPTIONS] ENVIRONMENT

Environments:
  local       Deploy to local Docker Compose
  staging     Deploy to staging Kubernetes cluster
  production  Deploy to production Kubernetes cluster

Options:
  -h, --help              Show this help message
  -v, --version VERSION   Specify image version/tag (default: latest)
  -f, --force             Force deployment without confirmation
  -d, --dry-run           Show what would be deployed without executing
  -r, --rollback          Rollback to previous version
  -s, --skip-tests        Skip running tests before deployment
  -b, --build             Build new image before deployment
  --no-cache              Build without using cache
  --config FILE           Use custom configuration file

Examples:
  $0 local                    # Deploy to local environment
  $0 staging -v v1.2.3        # Deploy version v1.2.3 to staging
  $0 production -f            # Force deploy to production
  $0 staging --rollback       # Rollback staging deployment
  $0 local -b --no-cache      # Build and deploy locally without cache

EOF
}

# Parse command line arguments
ENVIRONMENT=""
VERSION="latest"
FORCE=false
DRY_RUN=false
ROLLBACK=false
SKIP_TESTS=false
BUILD=false
NO_CACHE=false
CONFIG_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -r|--rollback)
            ROLLBACK=true
            shift
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -b|--build)
            BUILD=true
            shift
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        local|staging|production)
            ENVIRONMENT="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate environment
if [[ -z "$ENVIRONMENT" ]]; then
    log_error "Environment must be specified"
    show_help
    exit 1
fi

# Load configuration
load_config() {
    local config_file="${CONFIG_FILE:-$PROJECT_ROOT/config/deploy-$ENVIRONMENT.env}"
    
    if [[ -f "$config_file" ]]; then
        log_info "Loading configuration from $config_file"
        # shellcheck source=/dev/null
        source "$config_file"
    else
        log_warning "Configuration file not found: $config_file"
    fi
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for $ENVIRONMENT deployment..."
    
    # Check required tools
    local required_tools=()
    
    case $ENVIRONMENT in
        local)
            required_tools=("docker" "docker-compose")
            ;;
        staging|production)
            required_tools=("kubectl" "helm" "docker")
            ;;
    esac
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
    
    # Check Kubernetes context for staging/production
    if [[ "$ENVIRONMENT" == "staging" || "$ENVIRONMENT" == "production" ]]; then
        local current_context
        current_context=$(kubectl config current-context 2>/dev/null || echo "none")
        
        if [[ "$current_context" == "none" ]]; then
            log_error "No Kubernetes context configured"
            exit 1
        fi
        
        log_info "Current Kubernetes context: $current_context"
        
        if [[ "$ENVIRONMENT" == "production" && "$current_context" != *"prod"* ]]; then
            log_warning "Kubernetes context doesn't appear to be production"
            if [[ "$FORCE" != "true" ]]; then
                read -p "Continue anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    exit 1
                fi
            fi
        fi
    fi
}

# Run tests
run_tests() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log_warning "Skipping tests as requested"
        return 0
    fi
    
    log_info "Running tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run linting
    log_info "Running code quality checks..."
    if ! python -m black --check .; then
        log_error "Code formatting check failed"
        return 1
    fi
    
    if ! python -m flake8 .; then
        log_error "Linting failed"
        return 1
    fi
    
    # Run unit tests
    log_info "Running unit tests..."
    if ! python -m pytest tests/unit/ -v --tb=short; then
        log_error "Unit tests failed"
        return 1
    fi
    
    # Run integration tests for non-local environments
    if [[ "$ENVIRONMENT" != "local" ]]; then
        log_info "Running integration tests..."
        if ! python -m pytest tests/integration/ -v --tb=short; then
            log_error "Integration tests failed"
            return 1
        fi
    fi
    
    log_success "All tests passed"
}

# Build Docker image
build_image() {
    if [[ "$BUILD" != "true" ]]; then
        return 0
    fi
    
    log_info "Building Docker image..."
    
    local build_args=()
    build_args+=("--tag" "$DOCKER_REGISTRY/$IMAGE_NAME:$VERSION")
    build_args+=("--tag" "$DOCKER_REGISTRY/$IMAGE_NAME:latest")
    
    if [[ "$NO_CACHE" == "true" ]]; then
        build_args+=("--no-cache")
    fi
    
    # Multi-platform build for production
    if [[ "$ENVIRONMENT" == "production" ]]; then
        build_args+=("--platform" "linux/amd64,linux/arm64")
        build_args+=("--push")
    fi
    
    cd "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run: docker build ${build_args[*]} ."
        return 0
    fi
    
    if ! docker build "${build_args[@]}" .; then
        log_error "Docker build failed"
        return 1
    fi
    
    # Push image for staging/production
    if [[ "$ENVIRONMENT" != "local" && "$ENVIRONMENT" != "production" ]]; then
        log_info "Pushing image to registry..."
        docker push "$DOCKER_REGISTRY/$IMAGE_NAME:$VERSION"
        docker push "$DOCKER_REGISTRY/$IMAGE_NAME:latest"
    fi
    
    log_success "Image built successfully"
}

# Deploy to local environment
deploy_local() {
    log_info "Deploying to local environment..."
    
    cd "$PROJECT_ROOT"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would run: docker-compose up -d"
        return 0
    fi
    
    # Stop existing containers
    docker-compose down --remove-orphans
    
    # Start services
    if ! docker-compose up -d; then
        log_error "Local deployment failed"
        return 1
    fi
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Health check
    if curl -f http://localhost:8000/health &> /dev/null; then
        log_success "Local deployment successful"
        log_info "API available at: http://localhost:8000"
        log_info "Grafana available at: http://localhost:3000"
        log_info "Kafka UI available at: http://localhost:8080"
    else
        log_error "Health check failed"
        return 1
    fi
}

# Deploy to Kubernetes
deploy_kubernetes() {
    local env="$1"
    log_info "Deploying to $env Kubernetes environment..."
    
    cd "$PROJECT_ROOT"
    
    # Set namespace
    local namespace="trading-system"
    if [[ "$env" == "staging" ]]; then
        namespace="trading-system-staging"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would deploy to namespace: $namespace"
        log_info "[DRY RUN] Would use image: $DOCKER_REGISTRY/$IMAGE_NAME:$VERSION"
        return 0
    fi
    
    # Create namespace if it doesn't exist
    kubectl create namespace "$namespace" --dry-run=client -o yaml | kubectl apply -f -
    
    # Apply configurations
    log_info "Applying Kubernetes manifests..."
    
    # Update image version in deployments
    find k8s/ -name "*.yaml" -exec sed -i "s|image: .*$IMAGE_NAME:.*|image: $DOCKER_REGISTRY/$IMAGE_NAME:$VERSION|g" {} \;
    
    # Apply manifests
    kubectl apply -f k8s/ -n "$namespace"
    
    # Wait for rollout to complete
    log_info "Waiting for deployment to complete..."
    kubectl rollout status deployment/trading-system-api -n "$namespace" --timeout="$KUBECTL_TIMEOUT"
    kubectl rollout status deployment/trading-system-market-data -n "$namespace" --timeout="$KUBECTL_TIMEOUT"
    kubectl rollout status deployment/trading-system-trading-engine -n "$namespace" --timeout="$KUBECTL_TIMEOUT"
    
    # Health check
    log_info "Performing health checks..."
    local api_pod
    api_pod=$(kubectl get pods -n "$namespace" -l app=trading-system-api -o jsonpath='{.items[0].metadata.name}')
    
    if kubectl exec -n "$namespace" "$api_pod" -- curl -f http://localhost:8000/health &> /dev/null; then
        log_success "$env deployment successful"
        
        # Show service URLs
        if [[ "$env" == "production" ]]; then
            log_info "Production API: https://api.trading-system.com"
            log_info "Production UI: https://trading-system.com"
        else
            log_info "Staging API: https://staging-api.trading-system.com"
            log_info "Staging UI: https://staging.trading-system.com"
        fi
    else
        log_error "Health check failed"
        return 1
    fi
}

# Rollback deployment
rollback_deployment() {
    local env="$1"
    log_info "Rolling back $env deployment..."
    
    local namespace="trading-system"
    if [[ "$env" == "staging" ]]; then
        namespace="trading-system-staging"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback deployments in namespace: $namespace"
        return 0
    fi
    
    # Rollback deployments
    kubectl rollout undo deployment/trading-system-api -n "$namespace"
    kubectl rollout undo deployment/trading-system-market-data -n "$namespace"
    kubectl rollout undo deployment/trading-system-trading-engine -n "$namespace"
    
    # Wait for rollback to complete
    kubectl rollout status deployment/trading-system-api -n "$namespace" --timeout="$KUBECTL_TIMEOUT"
    kubectl rollout status deployment/trading-system-market-data -n "$namespace" --timeout="$KUBECTL_TIMEOUT"
    kubectl rollout status deployment/trading-system-trading-engine -n "$namespace" --timeout="$KUBECTL_TIMEOUT"
    
    log_success "Rollback completed"
}

# Confirmation prompt
confirm_deployment() {
    if [[ "$FORCE" == "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo
    log_warning "You are about to deploy to $ENVIRONMENT environment"
    log_info "Image: $DOCKER_REGISTRY/$IMAGE_NAME:$VERSION"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        echo
        log_warning "⚠️  THIS IS A PRODUCTION DEPLOYMENT ⚠️"
        echo
    fi
    
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
}

# Main deployment function
main() {
    log_info "Starting deployment to $ENVIRONMENT environment"
    log_info "Version: $VERSION"
    
    # Load configuration
    load_config
    
    # Check prerequisites
    check_prerequisites
    
    # Handle rollback
    if [[ "$ROLLBACK" == "true" ]]; then
        if [[ "$ENVIRONMENT" == "local" ]]; then
            log_error "Rollback not supported for local environment"
            exit 1
        fi
        
        confirm_deployment
        rollback_deployment "$ENVIRONMENT"
        return 0
    fi
    
    # Run tests
    run_tests
    
    # Build image if requested
    build_image
    
    # Confirm deployment
    confirm_deployment
    
    # Deploy based on environment
    case $ENVIRONMENT in
        local)
            deploy_local
            ;;
        staging|production)
            deploy_kubernetes "$ENVIRONMENT"
            ;;
        *)
            log_error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    log_success "Deployment to $ENVIRONMENT completed successfully!"
}

# Trap errors and cleanup
trap 'log_error "Deployment failed with exit code $?"' ERR

# Run main function
main "$@"