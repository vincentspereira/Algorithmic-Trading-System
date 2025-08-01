#!/bin/bash

# Nautilus Trader - Disaster Recovery Script
# This script provides comprehensive disaster recovery capabilities

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-nautilus-trader}"
BACKUP_LOCATION="${BACKUP_LOCATION:-/backups/nautilus-trader}"
RECOVERY_MODE="${RECOVERY_MODE:-full}"  # full, partial, database-only
TIMEOUT="${TIMEOUT:-600}"
DRY_RUN="${DRY_RUN:-false}"

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

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for disaster recovery"
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check helm
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed or not in PATH"
        exit 1
    fi
    
    # Check backup location
    if [ ! -d "$BACKUP_LOCATION" ]; then
        log_error "Backup location does not exist: $BACKUP_LOCATION"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to create emergency backup before recovery
create_emergency_backup() {
    log_info "Creating emergency backup before recovery"
    
    local timestamp
    timestamp=$(date '+%Y%m%d-%H%M%S')
    local emergency_backup_dir="$BACKUP_LOCATION/emergency-$timestamp"
    
    mkdir -p "$emergency_backup_dir"
    
    # Backup current Kubernetes resources
    log_info "Backing up current Kubernetes resources"
    kubectl get all -n "$NAMESPACE" -o yaml > "$emergency_backup_dir/kubernetes-resources.yaml" || true
    kubectl get configmaps -n "$NAMESPACE" -o yaml > "$emergency_backup_dir/configmaps.yaml" || true
    kubectl get secrets -n "$NAMESPACE" -o yaml > "$emergency_backup_dir/secrets.yaml" || true
    kubectl get pvc -n "$NAMESPACE" -o yaml > "$emergency_backup_dir/persistent-volumes.yaml" || true
    
    # Backup database if accessible
    if kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=postgresql &> /dev/null; then
        log_info "Backing up database"
        kubectl exec -n "$NAMESPACE" -c postgresql \
            $(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}') \
            -- pg_dump -U nautilus nautilus_trader > "$emergency_backup_dir/database-dump.sql" || true
    fi
    
    log_success "Emergency backup created at: $emergency_backup_dir"
    echo "$emergency_backup_dir"
}

# Function to stop all services
stop_all_services() {
    log_info "Stopping all services in namespace: $NAMESPACE"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would stop all deployments and statefulsets"
        return 0
    fi
    
    # Scale down deployments
    local deployments
    deployments=$(kubectl get deployments -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')
    for deployment in $deployments; do
        log_info "Scaling down deployment: $deployment"
        kubectl scale deployment "$deployment" --replicas=0 -n "$NAMESPACE" || true
    done
    
    # Scale down statefulsets
    local statefulsets
    statefulsets=$(kubectl get statefulsets -n "$NAMESPACE" -o jsonpath='{.items[*].metadata.name}')
    for statefulset in $statefulsets; do
        log_info "Scaling down statefulset: $statefulset"
        kubectl scale statefulset "$statefulset" --replicas=0 -n "$NAMESPACE" || true
    done
    
    # Wait for pods to terminate
    log_info "Waiting for pods to terminate"
    kubectl wait --for=delete pods --all -n "$NAMESPACE" --timeout=300s || true
    
    log_success "All services stopped"
}

# Function to restore database
restore_database() {
    local backup_file="$1"
    
    log_info "Restoring database from: $backup_file"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would restore database from $backup_file"
        return 0
    fi
    
    # Start PostgreSQL if not running
    if ! kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=postgresql | grep Running &> /dev/null; then
        log_info "Starting PostgreSQL for database restore"
        kubectl scale statefulset postgresql --replicas=1 -n "$NAMESPACE"
        kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n "$NAMESPACE" --timeout=300s
    fi
    
    # Restore database
    local postgres_pod
    postgres_pod=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}')
    
    # Drop existing database and recreate
    kubectl exec -n "$NAMESPACE" -c postgresql "$postgres_pod" -- psql -U nautilus -c "DROP DATABASE IF EXISTS nautilus_trader;"
    kubectl exec -n "$NAMESPACE" -c postgresql "$postgres_pod" -- psql -U nautilus -c "CREATE DATABASE nautilus_trader;"
    
    # Restore from backup
    kubectl exec -i -n "$NAMESPACE" -c postgresql "$postgres_pod" -- psql -U nautilus nautilus_trader < "$backup_file"
    
    log_success "Database restored successfully"
}

# Function to restore Kubernetes resources
restore_kubernetes_resources() {
    local backup_dir="$1"
    
    log_info "Restoring Kubernetes resources from: $backup_dir"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would restore Kubernetes resources from $backup_dir"
        return 0
    fi
    
    # Restore in specific order
    local resource_files=(
        "secrets.yaml"
        "configmaps.yaml"
        "persistent-volumes.yaml"
        "kubernetes-resources.yaml"
    )
    
    for resource_file in "${resource_files[@]}"; do
        local file_path="$backup_dir/$resource_file"
        if [ -f "$file_path" ]; then
            log_info "Restoring: $resource_file"
            kubectl apply -f "$file_path" || log_warning "Failed to restore $resource_file"
        else
            log_warning "Backup file not found: $file_path"
        fi
    done
    
    log_success "Kubernetes resources restored"
}

# Function to restore from Helm backup
restore_helm_deployment() {
    local backup_dir="$1"
    
    log_info "Restoring Helm deployment"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY RUN] Would restore Helm deployment"
        return 0
    fi
    
    # Check if Helm values backup exists
    local helm_values_file="$backup_dir/helm-values.yaml"
    if [ -f "$helm_values_file" ]; then
        log_info "Restoring from Helm values backup"
        helm upgrade --install nautilus-trader ./k8s/helm/nautilus-trader \
            --namespace "$NAMESPACE" \
            --values "$helm_values_file" \
            --timeout "${TIMEOUT}s"
    else
        log_info "No Helm values backup found, using default values"
        helm upgrade --install nautilus-trader ./k8s/helm/nautilus-trader \
            --namespace "$NAMESPACE" \
            --timeout "${TIMEOUT}s"
    fi
    
    log_success "Helm deployment restored"
}

# Function to verify recovery
verify_recovery() {
    log_info "Verifying disaster recovery"
    
    local max_retries=20
    local retry_interval=30
    local retries=0
    
    while [ $retries -lt $max_retries ]; do
        log_info "Verification attempt $((retries + 1))/$max_retries"
        
        # Check if all pods are running
        local total_pods
        local running_pods
        total_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | wc -l)
        running_pods=$(kubectl get pods -n "$NAMESPACE" --no-headers | grep Running | wc -l)
        
        log_info "Pods status: $running_pods/$total_pods running"
        
        if [ "$running_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
            # Additional health checks
            if verify_api_health && verify_database_health; then
                log_success "Disaster recovery verification passed"
                return 0
            fi
        fi
        
        retries=$((retries + 1))
        if [ $retries -lt $max_retries ]; then
            log_info "Waiting ${retry_interval}s before next verification attempt"
            sleep $retry_interval
        fi
    done
    
    log_error "Disaster recovery verification failed after $max_retries attempts"
    return 1
}

# Function to verify API health
verify_api_health() {
    log_info "Verifying API health"
    
    # Port forward to API service
    kubectl port-forward service/nautilus-trader-api 8080:8000 -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    sleep 10  # Wait for port-forward to establish
    
    local health_status
    if health_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null); then
        kill $port_forward_pid 2>/dev/null || true
        if [ "$health_status" = "200" ]; then
            log_success "API health check passed"
            return 0
        fi
    fi
    
    kill $port_forward_pid 2>/dev/null || true
    log_warning "API health check failed"
    return 1
}

# Function to verify database health
verify_database_health() {
    log_info "Verifying database health"
    
    local postgres_pod
    if postgres_pod=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); then
        if kubectl exec -n "$NAMESPACE" -c postgresql "$postgres_pod" -- pg_isready -U nautilus &> /dev/null; then
            log_success "Database health check passed"
            return 0
        fi
    fi
    
    log_warning "Database health check failed"
    return 1
}

# Function to generate recovery report
generate_recovery_report() {
    local recovery_status="$1"
    local backup_used="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    local report_file="disaster-recovery-report-$(date '+%Y%m%d-%H%M%S').json"
    
    cat > "$report_file" << EOF
{
  "disaster_recovery_report": {
    "timestamp": "$timestamp",
    "namespace": "$NAMESPACE",
    "recovery_mode": "$RECOVERY_MODE",
    "backup_used": "$backup_used",
    "status": "$recovery_status",
    "dry_run": $DRY_RUN,
    "services_status": $(kubectl get deployments,statefulsets -n "$NAMESPACE" -o json | jq '.items[] | {name: .metadata.name, kind: .kind, replicas: .spec.replicas, readyReplicas: .status.readyReplicas}'),
    "pod_status": $(kubectl get pods -n "$NAMESPACE" -o json | jq '.items[] | {name: .metadata.name, status: .status.phase, ready: (.status.conditions[] | select(.type=="Ready") | .status)}')
  }
}
EOF
    
    log_info "Recovery report generated: $report_file"
}

# Function to send recovery notifications
send_recovery_notification() {
    local status="$1"
    local backup_used="$2"
    
    # Slack notification
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        local color
        local message
        
        if [ "$status" = "success" ]; then
            color="good"
            message="✅ Disaster recovery completed successfully for Nautilus Trader"
        else
            color="danger"
            message="❌ Disaster recovery failed for Nautilus Trader"
        fi
        
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"attachments\":[{\"color\":\"$color\",\"text\":\"$message\",\"fields\":[{\"title\":\"Namespace\",\"value\":\"$NAMESPACE\",\"short\":true},{\"title\":\"Recovery Mode\",\"value\":\"$RECOVERY_MODE\",\"short\":true},{\"title\":\"Backup Used\",\"value\":\"$backup_used\",\"short\":false}]}]}" \
            "$SLACK_WEBHOOK_URL" || log_warning "Failed to send Slack notification"
    fi
}

# Main disaster recovery function
main() {
    log_info "Starting Nautilus Trader disaster recovery"
    log_info "Recovery mode: $RECOVERY_MODE"
    log_info "Namespace: $NAMESPACE"
    log_info "Dry run: $DRY_RUN"
    
    # Check prerequisites
    check_prerequisites
    
    # Find latest backup
    local latest_backup
    latest_backup=$(find "$BACKUP_LOCATION" -maxdepth 1 -type d -name "backup-*" | sort -r | head -n 1)
    
    if [ -z "$latest_backup" ]; then
        log_error "No backup found in $BACKUP_LOCATION"
        exit 1
    fi
    
    log_info "Using backup: $latest_backup"
    
    # Create emergency backup
    local emergency_backup
    emergency_backup=$(create_emergency_backup)
    
    # Confirm recovery
    if [ "${CONFIRM_RECOVERY:-}" != "yes" ] && [ "$DRY_RUN" != "true" ]; then
        echo -n "Are you sure you want to proceed with disaster recovery? This will stop all services and restore from backup. (yes/no): "
        read -r confirmation
        if [ "$confirmation" != "yes" ]; then
            log_info "Disaster recovery cancelled by user"
            exit 0
        fi
    fi
    
    # Perform recovery based on mode
    case "$RECOVERY_MODE" in
        "full")
            log_info "Performing full disaster recovery"
            stop_all_services
            restore_database "$latest_backup/database-dump.sql"
            restore_kubernetes_resources "$latest_backup"
            ;;
        "partial")
            log_info "Performing partial disaster recovery"
            restore_kubernetes_resources "$latest_backup"
            ;;
        "database-only")
            log_info "Performing database-only recovery"
            restore_database "$latest_backup/database-dump.sql"
            ;;
        "helm")
            log_info "Performing Helm-based recovery"
            stop_all_services
            restore_helm_deployment "$latest_backup"
            ;;
        *)
            log_error "Unknown recovery mode: $RECOVERY_MODE"
            exit 1
            ;;
    esac
    
    # Verify recovery
    if [ "$DRY_RUN" != "true" ]; then
        if verify_recovery; then
            log_success "Disaster recovery completed successfully"
            generate_recovery_report "success" "$latest_backup"
            send_recovery_notification "success" "$latest_backup"
        else
            log_error "Disaster recovery verification failed"
            generate_recovery_report "failed" "$latest_backup"
            send_recovery_notification "failed" "$latest_backup"
            exit 1
        fi
    else
        log_info "Dry run completed successfully"
        generate_recovery_report "dry_run_success" "$latest_backup"
    fi
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -n, --namespace NAMESPACE       Kubernetes namespace (default: nautilus-trader)
    -b, --backup-location PATH      Backup location (default: /backups/nautilus-trader)
    -m, --mode MODE                 Recovery mode: full, partial, database-only, helm (default: full)
    -t, --timeout TIMEOUT           Operation timeout in seconds (default: 600)
    -d, --dry-run                   Perform dry run without making changes
    -c, --confirm                   Skip confirmation prompt
    -h, --help                      Show this help message

Environment Variables:
    NAMESPACE                       Kubernetes namespace
    BACKUP_LOCATION                 Backup location path
    RECOVERY_MODE                   Recovery mode
    TIMEOUT                         Operation timeout
    DRY_RUN                         Set to 'true' for dry run
    CONFIRM_RECOVERY                Set to 'yes' to skip confirmation
    SLACK_WEBHOOK_URL               Slack webhook for notifications

Examples:
    $0                              # Full recovery from latest backup
    $0 -m database-only             # Database-only recovery
    $0 -d                           # Dry run to test recovery process
    $0 -b /custom/backup/path       # Use custom backup location

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -b|--backup-location)
            BACKUP_LOCATION="$2"
            shift 2
            ;;
        -m|--mode)
            RECOVERY_MODE="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN="true"
            shift
            ;;
        -c|--confirm)
            CONFIRM_RECOVERY="yes"
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