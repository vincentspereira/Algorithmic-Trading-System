#!/bin/bash

# Algorithmic Trading System Rollback Script
# This script handles rollback operations for different environments

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
Algorithmic Trading System Rollback Script

Usage: $0 [OPTIONS] ENVIRONMENT

Environments:
  staging     Rollback staging Kubernetes deployment
  production  Rollback production Kubernetes deployment

Options:
  -h, --help              Show this help message
  -v, --version VERSION   Rollback to specific version (default: previous)
  -f, --force             Force rollback without confirmation
  -d, --dry-run           Show what would be rolled back without executing
  -r, --revision N        Rollback to specific revision number
  -l, --list              List available rollback revisions
  -s, --status            Show current deployment status
  --health-check          Perform health check after rollback
  --skip-validation       Skip pre-rollback validation

Examples:
  $0 staging                      # Rollback staging to previous version
  $0 production -v v1.2.3         # Rollback production to specific version
  $0 staging -r 5                 # Rollback staging to revision 5
  $0 production -l                # List production rollback revisions
  $0 staging --status             # Show staging deployment status
  $0 production -f --health-check # Force rollback with health check

EOF
}

# Parse command line arguments
ENVIRONMENT=""
VERSION=""
FORCE=false
DRY_RUN=false
REVISION=""
LIST_REVISIONS=false
SHOW_STATUS=false
HEALTH_CHECK=false
SKIP_VALIDATION=false

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
        -r|--revision)
            REVISION="$2"
            shift 2
            ;;
        -l|--list)
            LIST_REVISIONS=true
            shift
            ;;
        -s|--status)
            SHOW_STATUS=true
            shift
            ;;
        --health-check)
            HEALTH_CHECK=true
            shift
            ;;
        --skip-validation)
            SKIP_VALIDATION=true
            shift
            ;;
        staging|production)
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

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
    exit 1
fi

# Set namespace based on environment
NAMESPACE="trading-system"
if [[ "$ENVIRONMENT" == "staging" ]]; then
    NAMESPACE="trading-system-staging"
fi

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for $ENVIRONMENT rollback..."
    
    # Check required tools
    local required_tools=("kubectl" "helm")
    
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool not found: $tool"
            exit 1
        fi
    done
    
    # Check Kubernetes context
    local current_context
    current_context=$(kubectl config current-context 2>/dev/null || echo "none")
    
    if [[ "$current_context" == "none" ]]; then
        log_error "No Kubernetes context configured"
        exit 1
    fi
    
    log_info "Current Kubernetes context: $current_context"
    
    # Verify namespace exists
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace does not exist: $NAMESPACE"
        exit 1
    fi
    
    # Check if deployments exist
    local deployments=("trading-system-api" "trading-system-market-data" "trading-system-trading-engine")
    
    for deployment in "${deployments[@]}"; do
        if ! kubectl get deployment "$deployment" -n "$NAMESPACE" &> /dev/null; then
            log_error "Deployment does not exist: $deployment"
            exit 1
        fi
    done
}

# List available revisions
list_revisions() {
    log_info "Available rollback revisions for $ENVIRONMENT:"
    echo
    
    local deployments=("trading-system-api" "trading-system-market-data" "trading-system-trading-engine")
    
    for deployment in "${deployments[@]}"; do
        log_info "Deployment: $deployment"
        kubectl rollout history deployment "$deployment" -n "$NAMESPACE" | tail -n +2
        echo
    done
}

# Show deployment status
show_deployment_status() {
    log_info "Current deployment status for $ENVIRONMENT:"
    echo
    
    local deployments=("trading-system-api" "trading-system-market-data" "trading-system-trading-engine")
    
    for deployment in "${deployments[@]}"; do
        log_info "Deployment: $deployment"
        kubectl get deployment "$deployment" -n "$NAMESPACE" -o wide
        kubectl rollout status deployment "$deployment" -n "$NAMESPACE" --timeout=10s || true
        echo
    done
    
    # Show pods status
    log_info "Pod status:"
    kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=trading-system
    echo
    
    # Show services
    log_info "Service status:"
    kubectl get services -n "$NAMESPACE"
}

# Validate rollback target
validate_rollback_target() {
    if [[ "$SKIP_VALIDATION" == "true" ]]; then
        log_warning "Skipping rollback validation as requested"
        return 0
    fi
    
    log_info "Validating rollback target..."
    
    local deployments=("trading-system-api" "trading-system-market-data" "trading-system-trading-engine")
    
    for deployment in "${deployments[@]}"; do
        # Check if there are previous revisions
        local revision_count
        revision_count=$(kubectl rollout history deployment "$deployment" -n "$NAMESPACE" | wc -l)
        
        if [[ $revision_count -le 2 ]]; then
            log_error "No previous revisions available for deployment: $deployment"
            return 1
        fi
        
        # If specific revision is requested, validate it exists
        if [[ -n "$REVISION" ]]; then
            if ! kubectl rollout history deployment "$deployment" -n "$NAMESPACE" --revision="$REVISION" &> /dev/null; then
                log_error "Revision $REVISION does not exist for deployment: $deployment"
                return 1
            fi
        fi
    done
    
    log_success "Rollback target validation passed"
}

# Perform pre-rollback backup
perform_backup() {
    log_info "Creating pre-rollback backup..."
    
    local backup_dir="$PROJECT_ROOT/backups/rollback-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup current deployment manifests
    local deployments=("trading-system-api" "trading-system-market-data" "trading-system-trading-engine")
    
    for deployment in "${deployments[@]}"; do
        kubectl get deployment "$deployment" -n "$NAMESPACE" -o yaml > "$backup_dir/$deployment-deployment.yaml"
        kubectl get service "$deployment" -n "$NAMESPACE" -o yaml > "$backup_dir/$deployment-service.yaml" 2>/dev/null || true
    done
    
    # Backup configmaps and secrets
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "$backup_dir/configmaps.yaml"
    kubectl get secrets -n "$NAMESPACE" -o yaml > "$backup_dir/secrets.yaml"
    
    log_success "Backup created at: $backup_dir"
    echo "$backup_dir" > /tmp/rollback-backup-path
}

# Execute rollback
execute_rollback() {
    log_info "Executing rollback for $ENVIRONMENT environment..."
    
    local deployments=("trading-system-api" "trading-system-market-data" "trading-system-trading-engine")
    local rollback_args=()
    
    if [[ -n "$REVISION" ]]; then
        rollback_args+=("--to-revision=$REVISION")
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] Would rollback the following deployments:"
        for deployment in "${deployments[@]}"; do
            log_info "[DRY RUN] kubectl rollout undo deployment/$deployment -n $NAMESPACE ${rollback_args[*]}"
        done
        return 0
    fi
    
    # Perform actual rollback
    for deployment in "${deployments[@]}"; do
        log_info "Rolling back deployment: $deployment"
        
        if ! kubectl rollout undo deployment "$deployment" -n "$NAMESPACE" "${rollback_args[@]}"; then
            log_error "Failed to rollback deployment: $deployment"
            return 1
        fi
    done
    
    # Wait for rollback to complete
    log_info "Waiting for rollback to complete..."
    
    for deployment in "${deployments[@]}"; do
        log_info "Waiting for deployment: $deployment"
        
        if ! kubectl rollout status deployment "$deployment" -n "$NAMESPACE" --timeout="$KUBECTL_TIMEOUT"; then
            log_error "Rollback failed for deployment: $deployment"
            return 1
        fi
    done
    
    log_success "Rollback completed successfully"
}

# Perform health check
perform_health_check() {
    if [[ "$HEALTH_CHECK" != "true" ]]; then
        return 0
    fi
    
    log_info "Performing post-rollback health check..."
    
    # Wait for pods to be ready
    sleep 30
    
    # Check pod health
    local unhealthy_pods
    unhealthy_pods=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=trading-system --field-selector=status.phase!=Running -o name | wc -l)
    
    if [[ $unhealthy_pods -gt 0 ]]; then
        log_error "Found $unhealthy_pods unhealthy pods after rollback"
        kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/name=trading-system
        return 1
    fi
    
    # Check API health endpoint
    local api_pod
    api_pod=$(kubectl get pods -n "$NAMESPACE" -l app=trading-system-api -o jsonpath='{.items[0].metadata.name}')
    
    if [[ -n "$api_pod" ]]; then
        log_info "Checking API health endpoint..."
        
        if kubectl exec -n "$NAMESPACE" "$api_pod" -- curl -f http://localhost:8000/health &> /dev/null; then
            log_success "API health check passed"
        else
            log_error "API health check failed"
            return 1
        fi
    fi
    
    # Check service endpoints
    log_info "Checking service endpoints..."
    kubectl get endpoints -n "$NAMESPACE"
    
    log_success "Health check completed successfully"
}

# Send notifications
send_notifications() {
    local status="$1"
    local message="Rollback $status for $ENVIRONMENT environment"
    
    # Load environment configuration for notification settings
    local config_file="$PROJECT_ROOT/config/deploy-$ENVIRONMENT.env"
    if [[ -f "$config_file" ]]; then
        # shellcheck source=/dev/null
        source "$config_file"
    fi
    
    # Send Slack notification if configured
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        local color="good"
        if [[ "$status" == "failed" ]]; then
            color="danger"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"text\":\"$message\"}]}" \
            "$SLACK_WEBHOOK_URL" &> /dev/null || true
    fi
    
    # Send email notification if configured
    if [[ -n "${ALERT_EMAIL_RECIPIENTS:-}" ]]; then
        echo "$message" | mail -s "Trading System Rollback $status" "$ALERT_EMAIL_RECIPIENTS" &> /dev/null || true
    fi
}

# Confirmation prompt
confirm_rollback() {
    if [[ "$FORCE" == "true" || "$DRY_RUN" == "true" ]]; then
        return 0
    fi
    
    echo
    log_warning "You are about to rollback $ENVIRONMENT environment"
    
    if [[ -n "$VERSION" ]]; then
        log_info "Target version: $VERSION"
    elif [[ -n "$REVISION" ]]; then
        log_info "Target revision: $REVISION"
    else
        log_info "Target: Previous revision"
    fi
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        echo
        log_warning "⚠️  THIS IS A PRODUCTION ROLLBACK ⚠️"
        echo
    fi
    
    read -p "Continue with rollback? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Rollback cancelled"
        exit 0
    fi
}

# Cleanup function
cleanup() {
    local exit_code=$?
    
    if [[ $exit_code -ne 0 ]]; then
        log_error "Rollback failed with exit code $exit_code"
        send_notifications "failed"
        
        # Show recent events for debugging
        log_info "Recent events in namespace $NAMESPACE:"
        kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | tail -20
    fi
    
    # Clean up temporary files
    rm -f /tmp/rollback-backup-path
}

# Main function
main() {
    log_info "Starting rollback operation for $ENVIRONMENT environment"
    
    # Handle special operations
    if [[ "$LIST_REVISIONS" == "true" ]]; then
        check_prerequisites
        list_revisions
        return 0
    fi
    
    if [[ "$SHOW_STATUS" == "true" ]]; then
        check_prerequisites
        show_deployment_status
        return 0
    fi
    
    # Check prerequisites
    check_prerequisites
    
    # Validate rollback target
    validate_rollback_target
    
    # Confirm rollback
    confirm_rollback
    
    # Create backup
    if [[ "$DRY_RUN" != "true" ]]; then
        perform_backup
    fi
    
    # Execute rollback
    execute_rollback
    
    # Perform health check
    perform_health_check
    
    # Send success notification
    if [[ "$DRY_RUN" != "true" ]]; then
        send_notifications "completed"
    fi
    
    log_success "Rollback operation completed successfully!"
    
    # Show final status
    show_deployment_status
}

# Trap errors and cleanup
trap cleanup EXIT

# Run main function
main "$@"