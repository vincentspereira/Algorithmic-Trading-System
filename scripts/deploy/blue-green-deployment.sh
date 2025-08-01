#!/bin/bash

# Blue-Green Deployment Script for Nautilus Trader
# This script implements a blue-green deployment strategy with health checks and rollback capability

set -euo pipefail

# Configuration
NAMESPACE="nautilus-trader"
APP_NAME="nautilus-trader"
HELM_CHART="./k8s/helm/nautilus-trader"
VALUES_FILE="./k8s/helm/nautilus-trader/values-production.yaml"
HEALTH_CHECK_TIMEOUT=300
HEALTH_CHECK_INTERVAL=10

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

# Function to check if deployment is healthy
check_deployment_health() {
    local color=$1
    local namespace="${NAMESPACE}-${color}"
    
    log_info "Checking health of ${color} deployment..."
    
    # Wait for pods to be ready
    if kubectl wait --for=condition=ready pod \
        -l "app.kubernetes.io/name=${APP_NAME},deployment.color=${color}" \
        -n "${namespace}" \
        --timeout="${HEALTH_CHECK_TIMEOUT}s"; then
        
        # Additional health checks
        local api_pods=$(kubectl get pods -n "${namespace}" \
            -l "app.kubernetes.io/name=${APP_NAME},app.kubernetes.io/component=api,deployment.color=${color}" \
            --field-selector=status.phase=Running \
            --no-headers | wc -l)
        
        local websocket_pods=$(kubectl get pods -n "${namespace}" \
            -l "app.kubernetes.io/name=${APP_NAME},app.kubernetes.io/component=websocket,deployment.color=${color}" \
            --field-selector=status.phase=Running \
            --no-headers | wc -l)
        
        if [[ $api_pods -gt 0 && $websocket_pods -gt 0 ]]; then
            log_success "${color} deployment is healthy (API: ${api_pods}, WebSocket: ${websocket_pods})"
            return 0
        else
            log_error "${color} deployment is not healthy (API: ${api_pods}, WebSocket: ${websocket_pods})"
            return 1
        fi
    else
        log_error "${color} deployment failed health check"
        return 1
    fi
}

# Function to run smoke tests
run_smoke_tests() {
    local color=$1
    local namespace="${NAMESPACE}-${color}"
    
    log_info "Running smoke tests against ${color} deployment..."
    
    # Port forward to access the service
    kubectl port-forward -n "${namespace}" \
        service/${APP_NAME}-api 8080:8000 &
    local port_forward_pid=$!
    
    sleep 5
    
    # Run smoke tests
    if python tests/smoke/production_smoke_tests.py --endpoint=http://localhost:8080; then
        log_success "Smoke tests passed for ${color} deployment"
        kill $port_forward_pid 2>/dev/null || true
        return 0
    else
        log_error "Smoke tests failed for ${color} deployment"
        kill $port_forward_pid 2>/dev/null || true
        return 1
    fi
}

# Function to get current active color
get_active_color() {
    local current_selector=$(kubectl get service "${APP_NAME}-service" -n "${NAMESPACE}" \
        -o jsonpath='{.spec.selector.deployment\.color}' 2>/dev/null || echo "")
    
    if [[ "$current_selector" == "blue" ]]; then
        echo "blue"
    elif [[ "$current_selector" == "green" ]]; then
        echo "green"
    else
        echo "none"
    fi
}

# Function to switch traffic
switch_traffic() {
    local target_color=$1
    
    log_info "Switching traffic to ${target_color} deployment..."
    
    kubectl patch service "${APP_NAME}-service" -n "${NAMESPACE}" \
        -p "{\"spec\":{\"selector\":{\"deployment.color\":\"${target_color}\"}}}"
    
    log_success "Traffic switched to ${target_color} deployment"
}

# Function to cleanup old deployment
cleanup_deployment() {
    local color=$1
    local namespace="${NAMESPACE}-${color}"
    
    log_info "Cleaning up ${color} deployment..."
    
    if helm list -n "${namespace}" | grep -q "${APP_NAME}-${color}"; then
        helm uninstall "${APP_NAME}-${color}" -n "${namespace}"
        log_success "${color} deployment cleaned up"
    else
        log_warning "${color} deployment not found, skipping cleanup"
    fi
}

# Function to rollback deployment
rollback_deployment() {
    local current_color=$1
    local previous_color=$2
    
    log_warning "Rolling back from ${current_color} to ${previous_color}..."
    
    # Switch traffic back
    switch_traffic "${previous_color}"
    
    # Wait a bit for traffic to stabilize
    sleep 30
    
    # Verify rollback
    if run_smoke_tests "${previous_color}"; then
        log_success "Rollback to ${previous_color} successful"
        
        # Cleanup failed deployment
        cleanup_deployment "${current_color}"
        
        return 0
    else
        log_error "Rollback verification failed"
        return 1
    fi
}

# Main deployment function
main() {
    local image_tag=${1:-"latest"}
    
    log_info "Starting blue-green deployment with image tag: ${image_tag}"
    
    # Determine current and target colors
    local current_color=$(get_active_color)
    local target_color
    
    if [[ "$current_color" == "blue" ]]; then
        target_color="green"
    else
        target_color="blue"
    fi
    
    log_info "Current active color: ${current_color}"
    log_info "Target deployment color: ${target_color}"
    
    # Deploy to target environment
    local target_namespace="${NAMESPACE}-${target_color}"
    
    log_info "Deploying to ${target_color} environment..."
    
    helm upgrade --install "${APP_NAME}-${target_color}" "${HELM_CHART}" \
        --namespace "${target_namespace}" \
        --create-namespace \
        --set "image.tag=${image_tag}" \
        --set "environment=production" \
        --set "deployment.color=${target_color}" \
        --values "${VALUES_FILE}" \
        --wait --timeout=15m
    
    # Health check
    if ! check_deployment_health "${target_color}"; then
        log_error "Health check failed for ${target_color} deployment"
        cleanup_deployment "${target_color}"
        exit 1
    fi
    
    # Run smoke tests
    if ! run_smoke_tests "${target_color}"; then
        log_error "Smoke tests failed for ${target_color} deployment"
        cleanup_deployment "${target_color}"
        exit 1
    fi
    
    # Switch traffic
    switch_traffic "${target_color}"
    
    # Wait for traffic to stabilize
    log_info "Waiting for traffic to stabilize..."
    sleep 60
    
    # Final verification
    if run_smoke_tests "${target_color}"; then
        log_success "Blue-green deployment completed successfully"
        
        # Cleanup old deployment if it exists
        if [[ "$current_color" != "none" ]]; then
            cleanup_deployment "${current_color}"
        fi
        
        log_success "Deployment completed. Active color: ${target_color}"
    else
        log_error "Final verification failed, initiating rollback..."
        
        if [[ "$current_color" != "none" ]]; then
            if rollback_deployment "${target_color}" "${current_color}"; then
                log_success "Rollback completed successfully"
                exit 1
            else
                log_error "Rollback failed - manual intervention required"
                exit 2
            fi
        else
            log_error "No previous deployment to rollback to"
            cleanup_deployment "${target_color}"
            exit 1
        fi
    fi
}

# Script usage
usage() {
    echo "Usage: $0 [IMAGE_TAG]"
    echo "  IMAGE_TAG: Docker image tag to deploy (default: latest)"
    echo ""
    echo "Examples:"
    echo "  $0                    # Deploy latest tag"
    echo "  $0 v1.2.3            # Deploy specific version"
    echo "  $0 main-abc123       # Deploy specific commit"
}

# Parse command line arguments
if [[ $# -gt 1 ]]; then
    usage
    exit 1
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

# Check prerequisites
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is required but not installed"
    exit 1
fi

if ! command -v helm &> /dev/null; then
    log_error "helm is required but not installed"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    log_error "Unable to connect to Kubernetes cluster"
    exit 1
fi

# Run main function
main "${1:-latest}"