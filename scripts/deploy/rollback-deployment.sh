#!/bin/bash

# Nautilus Trader - Deployment Rollback Script
# This script provides automated rollback capabilities for failed deployments

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-nautilus-trader}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-nautilus-trader-api}"
ROLLBACK_REVISION="${ROLLBACK_REVISION:-}"
TIMEOUT="${TIMEOUT:-300}"
HEALTH_CHECK_RETRIES="${HEALTH_CHECK_RETRIES:-10}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-30}"

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

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
}

# Function to check if namespace exists
check_namespace() {
    if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_error "Namespace '$NAMESPACE' does not exist"
        exit 1
    fi
}

# Function to get deployment rollout history
get_rollout_history() {
    log_info "Getting rollout history for deployment '$DEPLOYMENT_NAME'"
    kubectl rollout history deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE"
}

# Function to get current revision
get_current_revision() {
    kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.metadata.annotations.deployment\.kubernetes\.io/revision}'
}

# Function to get previous revision
get_previous_revision() {
    local current_revision
    current_revision=$(get_current_revision)
    local previous_revision=$((current_revision - 1))
    
    if [ "$previous_revision" -lt 1 ]; then
        log_error "No previous revision available for rollback"
        exit 1
    fi
    
    echo "$previous_revision"
}

# Function to perform rollback
perform_rollback() {
    local target_revision="$1"
    
    log_info "Starting rollback to revision $target_revision"
    
    # Perform the rollback
    if kubectl rollout undo deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --to-revision="$target_revision"; then
        log_success "Rollback command executed successfully"
    else
        log_error "Failed to execute rollback command"
        exit 1
    fi
    
    # Wait for rollback to complete
    log_info "Waiting for rollback to complete (timeout: ${TIMEOUT}s)"
    if kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback timed out or failed"
        exit 1
    fi
}

# Function to verify deployment health
verify_deployment_health() {
    log_info "Verifying deployment health"
    
    local retries=0
    while [ $retries -lt $HEALTH_CHECK_RETRIES ]; do
        # Check if all replicas are ready
        local ready_replicas
        ready_replicas=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.status.readyReplicas}')
        local desired_replicas
        desired_replicas=$(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.replicas}')
        
        if [ "$ready_replicas" = "$desired_replicas" ] && [ "$ready_replicas" -gt 0 ]; then
            log_success "All replicas are ready ($ready_replicas/$desired_replicas)"
            
            # Additional health check via API endpoint
            if check_api_health; then
                log_success "API health check passed"
                return 0
            else
                log_warning "API health check failed, retrying..."
            fi
        else
            log_warning "Replicas not ready yet ($ready_replicas/$desired_replicas), retrying..."
        fi
        
        retries=$((retries + 1))
        if [ $retries -lt $HEALTH_CHECK_RETRIES ]; then
            log_info "Waiting ${HEALTH_CHECK_INTERVAL}s before next health check..."
            sleep $HEALTH_CHECK_INTERVAL
        fi
    done
    
    log_error "Health check failed after $HEALTH_CHECK_RETRIES attempts"
    return 1
}

# Function to check API health
check_api_health() {
    local service_url
    service_url=$(kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.clusterIP}')
    local service_port
    service_port=$(kubectl get service "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].port}')
    
    # Use kubectl port-forward for health check
    kubectl port-forward service/"$DEPLOYMENT_NAME" 8080:$service_port -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    sleep 5  # Wait for port-forward to establish
    
    local health_status
    if health_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null); then
        kill $port_forward_pid 2>/dev/null || true
        if [ "$health_status" = "200" ]; then
            return 0
        fi
    fi
    
    kill $port_forward_pid 2>/dev/null || true
    return 1
}

# Function to create rollback report
create_rollback_report() {
    local target_revision="$1"
    local rollback_status="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    local report_file="rollback-report-$(date '+%Y%m%d-%H%M%S').json"
    
    cat > "$report_file" << EOF
{
  "rollback_report": {
    "timestamp": "$timestamp",
    "namespace": "$NAMESPACE",
    "deployment": "$DEPLOYMENT_NAME",
    "target_revision": "$target_revision",
    "status": "$rollback_status",
    "current_revision": "$(get_current_revision)",
    "pod_status": $(kubectl get pods -l app.kubernetes.io/name=nautilus-trader -n "$NAMESPACE" -o json | jq '.items[] | {name: .metadata.name, status: .status.phase, ready: .status.conditions[] | select(.type=="Ready") | .status}'),
    "deployment_status": $(kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE" -o json | jq '{replicas: .spec.replicas, readyReplicas: .status.readyReplicas, updatedReplicas: .status.updatedReplicas}')
  }
}
EOF
    
    log_info "Rollback report created: $report_file"
}

# Function to send notifications
send_notification() {
    local status="$1"
    local revision="$2"
    
    # Slack notification (if webhook URL is configured)
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local color
        local message
        
        if [ "$status" = "success" ]; then
            color="good"
            message="✅ Rollback successful for $DEPLOYMENT_NAME to revision $revision"
        else
            color="danger"
            message="❌ Rollback failed for $DEPLOYMENT_NAME to revision $revision"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"text\":\"$message\",\"fields\":[{\"title\":\"Namespace\",\"value\":\"$NAMESPACE\",\"short\":true},{\"title\":\"Deployment\",\"value\":\"$DEPLOYMENT_NAME\",\"short\":true}]}]}" \
            "$SLACK_WEBHOOK_URL" || log_warning "Failed to send Slack notification"
    fi
    
    # Email notification (if configured)
    if [ -n "${EMAIL_RECIPIENT:-}" ] && command -v mail &> /dev/null; then
        local subject="Nautilus Trader Rollback $status"
        local body="Deployment rollback $status for $DEPLOYMENT_NAME in namespace $NAMESPACE to revision $revision"
        echo "$body" | mail -s "$subject" "$EMAIL_RECIPIENT" || log_warning "Failed to send email notification"
    fi
}

# Function to cleanup resources if rollback fails
cleanup_failed_rollback() {
    log_warning "Cleaning up failed rollback resources"
    
    # Scale down deployment to prevent further issues
    kubectl scale deployment "$DEPLOYMENT_NAME" --replicas=0 -n "$NAMESPACE" || true
    
    # Wait for pods to terminate
    sleep 30
    
    # Scale back up to minimum replicas
    kubectl scale deployment "$DEPLOYMENT_NAME" --replicas=1 -n "$NAMESPACE" || true
}

# Main rollback function
main() {
    log_info "Starting Nautilus Trader deployment rollback"
    
    # Pre-flight checks
    check_kubectl
    check_namespace
    
    # Determine target revision
    local target_revision
    if [ -n "$ROLLBACK_REVISION" ]; then
        target_revision="$ROLLBACK_REVISION"
        log_info "Using specified revision: $target_revision"
    else
        target_revision=$(get_previous_revision)
        log_info "Using previous revision: $target_revision"
    fi
    
    # Show current status
    log_info "Current deployment status:"
    kubectl get deployment "$DEPLOYMENT_NAME" -n "$NAMESPACE"
    
    # Show rollout history
    get_rollout_history
    
    # Confirm rollback
    if [ "${CONFIRM_ROLLBACK:-}" != "yes" ]; then
        echo -n "Are you sure you want to rollback to revision $target_revision? (yes/no): "
        read -r confirmation
        if [ "$confirmation" != "yes" ]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi
    fi
    
    # Perform rollback
    if perform_rollback "$target_revision"; then
        log_success "Rollback operation completed"
        
        # Verify health
        if verify_deployment_health; then
            log_success "Deployment health verification passed"
            create_rollback_report "$target_revision" "success"
            send_notification "success" "$target_revision"
        else
            log_error "Deployment health verification failed"
            create_rollback_report "$target_revision" "health_check_failed"
            send_notification "failed" "$target_revision"
            cleanup_failed_rollback
            exit 1
        fi
    else
        log_error "Rollback operation failed"
        create_rollback_report "$target_revision" "rollback_failed"
        send_notification "failed" "$target_revision"
        cleanup_failed_rollback
        exit 1
    fi
    
    log_success "Rollback completed successfully!"
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -n, --namespace NAMESPACE       Kubernetes namespace (default: nautilus-trader)
    -d, --deployment DEPLOYMENT     Deployment name (default: nautilus-trader-api)
    -r, --revision REVISION         Target revision for rollback (default: previous revision)
    -t, --timeout TIMEOUT           Rollback timeout in seconds (default: 300)
    -c, --confirm                   Skip confirmation prompt
    -h, --help                      Show this help message

Environment Variables:
    NAMESPACE                       Kubernetes namespace
    DEPLOYMENT_NAME                 Deployment name
    ROLLBACK_REVISION              Target revision
    TIMEOUT                        Rollback timeout
    HEALTH_CHECK_RETRIES           Number of health check retries
    HEALTH_CHECK_INTERVAL          Interval between health checks
    SLACK_WEBHOOK_URL              Slack webhook for notifications
    EMAIL_RECIPIENT                Email for notifications
    CONFIRM_ROLLBACK               Set to 'yes' to skip confirmation

Examples:
    $0                             # Rollback to previous revision
    $0 -r 5                        # Rollback to specific revision
    $0 -n production -d api        # Rollback specific deployment in namespace
    $0 -c                          # Rollback without confirmation prompt

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -d|--deployment)
            DEPLOYMENT_NAME="$2"
            shift 2
            ;;
        -r|--revision)
            ROLLBACK_REVISION="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -c|--confirm)
            CONFIRM_ROLLBACK="yes"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run main function
main "$@"