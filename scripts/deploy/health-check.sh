#!/bin/bash

# Nautilus Trader - Comprehensive Health Check Script
# This script performs detailed health checks across all system components

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-nautilus-trader}"
TIMEOUT="${TIMEOUT:-300}"
HEALTH_CHECK_INTERVAL="${HEALTH_CHECK_INTERVAL:-10}"
MAX_RETRIES="${MAX_RETRIES:-30}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-json}"  # json, table, summary
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
declare -A HEALTH_RESULTS
OVERALL_HEALTH="healthy"

# Logging functions
log_info() {
    if [ "$VERBOSE" = "true" ]; then
        echo -e "${BLUE}[INFO]${NC} $1" >&2
    fi
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Function to check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
}

# Function to check namespace
check_namespace() {
    log_info "Checking namespace: $NAMESPACE"
    
    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        HEALTH_RESULTS["namespace"]="healthy"
        log_info "Namespace $NAMESPACE exists"
    else
        HEALTH_RESULTS["namespace"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "Namespace $NAMESPACE does not exist"
    fi
}

# Function to check Kubernetes resources
check_kubernetes_resources() {
    log_info "Checking Kubernetes resources"
    
    local resources=("deployments" "statefulsets" "services" "configmaps" "secrets" "persistentvolumeclaims")
    
    for resource in "${resources[@]}"; do
        log_info "Checking $resource"
        
        local count
        count=$(kubectl get "$resource" -n "$NAMESPACE" --no-headers 2>/dev/null | wc -l)
        
        if [ "$count" -gt 0 ]; then
            HEALTH_RESULTS["k8s_$resource"]="healthy"
            log_info "$resource: $count found"
        else
            HEALTH_RESULTS["k8s_$resource"]="warning"
            log_warning "$resource: none found"
        fi
    done
}

# Function to check pod health
check_pod_health() {
    log_info "Checking pod health"
    
    local pods
    pods=$(kubectl get pods -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [ -z "$pods" ]; then
        HEALTH_RESULTS["pods"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "No pods found in namespace $NAMESPACE"
        return 1
    fi
    
    local total_pods=0
    local running_pods=0
    local ready_pods=0
    local failed_pods=0
    
    while IFS= read -r pod_line; do
        if [ -n "$pod_line" ]; then
            total_pods=$((total_pods + 1))
            
            local pod_name
            pod_name=$(echo "$pod_line" | awk '{print $1}')
            local pod_status
            pod_status=$(echo "$pod_line" | awk '{print $3}')
            local pod_ready
            pod_ready=$(echo "$pod_line" | awk '{print $2}')
            
            case "$pod_status" in
                "Running")
                    running_pods=$((running_pods + 1))
                    if [[ "$pod_ready" == *"/"* ]]; then
                        local ready_count
                        local total_count
                        ready_count=$(echo "$pod_ready" | cut -d'/' -f1)
                        total_count=$(echo "$pod_ready" | cut -d'/' -f2)
                        if [ "$ready_count" = "$total_count" ]; then
                            ready_pods=$((ready_pods + 1))
                        fi
                    fi
                    ;;
                "Failed"|"Error"|"CrashLoopBackOff"|"ImagePullBackOff")
                    failed_pods=$((failed_pods + 1))
                    log_error "Pod $pod_name is in $pod_status state"
                    ;;
                *)
                    log_info "Pod $pod_name is in $pod_status state"
                    ;;
            esac
        fi
    done <<< "$pods"
    
    HEALTH_RESULTS["pods_total"]="$total_pods"
    HEALTH_RESULTS["pods_running"]="$running_pods"
    HEALTH_RESULTS["pods_ready"]="$ready_pods"
    HEALTH_RESULTS["pods_failed"]="$failed_pods"
    
    if [ "$failed_pods" -gt 0 ]; then
        HEALTH_RESULTS["pods"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "Pod health check failed: $failed_pods failed pods"
    elif [ "$ready_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
        HEALTH_RESULTS["pods"]="healthy"
        log_success "All pods are healthy ($ready_pods/$total_pods ready)"
    else
        HEALTH_RESULTS["pods"]="warning"
        log_warning "Some pods are not ready ($ready_pods/$total_pods ready)"
    fi
}

# Function to check API health
check_api_health() {
    log_info "Checking API health"
    
    # Check if API service exists
    if ! kubectl get service nautilus-trader-api -n "$NAMESPACE" &> /dev/null; then
        HEALTH_RESULTS["api"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "API service not found"
        return 1
    fi
    
    # Port forward to API service
    kubectl port-forward service/nautilus-trader-api 8080:8000 -n "$NAMESPACE" &
    local port_forward_pid=$!
    
    sleep 5  # Wait for port-forward to establish
    
    local retries=0
    local api_healthy=false
    
    while [ $retries -lt 5 ]; do
        local health_status
        if health_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health 2>/dev/null); then
            if [ "$health_status" = "200" ]; then
                api_healthy=true
                break
            fi
        fi
        retries=$((retries + 1))
        sleep 2
    done
    
    kill $port_forward_pid 2>/dev/null || true
    
    if [ "$api_healthy" = "true" ]; then
        HEALTH_RESULTS["api"]="healthy"
        log_success "API health check passed"
    else
        HEALTH_RESULTS["api"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "API health check failed"
    fi
}

# Function to check database health
check_database_health() {
    log_info "Checking database health"
    
    local postgres_pod
    if postgres_pod=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); then
        if [ -n "$postgres_pod" ]; then
            # Check if PostgreSQL is ready
            if kubectl exec -n "$NAMESPACE" -c postgresql "$postgres_pod" -- pg_isready -U nautilus &> /dev/null; then
                # Check database connectivity
                if kubectl exec -n "$NAMESPACE" -c postgresql "$postgres_pod" -- psql -U nautilus -d nautilus_trader -c "SELECT 1;" &> /dev/null; then
                    HEALTH_RESULTS["database"]="healthy"
                    log_success "Database health check passed"
                else
                    HEALTH_RESULTS["database"]="unhealthy"
                    OVERALL_HEALTH="unhealthy"
                    log_error "Database connectivity check failed"
                fi
            else
                HEALTH_RESULTS["database"]="unhealthy"
                OVERALL_HEALTH="unhealthy"
                log_error "PostgreSQL is not ready"
            fi
        else
            HEALTH_RESULTS["database"]="unhealthy"
            OVERALL_HEALTH="unhealthy"
            log_error "PostgreSQL pod not found"
        fi
    else
        HEALTH_RESULTS["database"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "PostgreSQL pod not found"
    fi
}

# Function to check Redis health
check_redis_health() {
    log_info "Checking Redis health"
    
    local redis_pod
    if redis_pod=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); then
        if [ -n "$redis_pod" ]; then
            if kubectl exec -n "$NAMESPACE" "$redis_pod" -- redis-cli ping | grep -q "PONG"; then
                HEALTH_RESULTS["redis"]="healthy"
                log_success "Redis health check passed"
            else
                HEALTH_RESULTS["redis"]="unhealthy"
                OVERALL_HEALTH="unhealthy"
                log_error "Redis ping failed"
            fi
        else
            HEALTH_RESULTS["redis"]="unhealthy"
            OVERALL_HEALTH="unhealthy"
            log_error "Redis pod not found"
        fi
    else
        HEALTH_RESULTS["redis"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "Redis pod not found"
    fi
}

# Function to check RabbitMQ health
check_rabbitmq_health() {
    log_info "Checking RabbitMQ health"
    
    local rabbitmq_pod
    if rabbitmq_pod=$(kubectl get pod -n "$NAMESPACE" -l app.kubernetes.io/name=rabbitmq -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); then
        if [ -n "$rabbitmq_pod" ]; then
            if kubectl exec -n "$NAMESPACE" "$rabbitmq_pod" -- rabbitmq-diagnostics ping &> /dev/null; then
                HEALTH_RESULTS["rabbitmq"]="healthy"
                log_success "RabbitMQ health check passed"
            else
                HEALTH_RESULTS["rabbitmq"]="unhealthy"
                OVERALL_HEALTH="unhealthy"
                log_error "RabbitMQ ping failed"
            fi
        else
            HEALTH_RESULTS["rabbitmq"]="unhealthy"
            OVERALL_HEALTH="unhealthy"
            log_error "RabbitMQ pod not found"
        fi
    else
        HEALTH_RESULTS["rabbitmq"]="unhealthy"
        OVERALL_HEALTH="unhealthy"
        log_error "RabbitMQ pod not found"
    fi
}

# Function to check ingress health
check_ingress_health() {
    log_info "Checking ingress health"
    
    if kubectl get ingress -n "$NAMESPACE" &> /dev/null; then
        local ingress_count
        ingress_count=$(kubectl get ingress -n "$NAMESPACE" --no-headers | wc -l)
        
        if [ "$ingress_count" -gt 0 ]; then
            HEALTH_RESULTS["ingress"]="healthy"
            log_success "Ingress resources found: $ingress_count"
        else
            HEALTH_RESULTS["ingress"]="warning"
            log_warning "No ingress resources found"
        fi
    else
        HEALTH_RESULTS["ingress"]="warning"
        log_warning "Ingress check failed"
    fi
}

# Function to check persistent volumes
check_persistent_volumes() {
    log_info "Checking persistent volumes"
    
    local pvcs
    pvcs=$(kubectl get pvc -n "$NAMESPACE" --no-headers 2>/dev/null)
    
    if [ -n "$pvcs" ]; then
        local bound_pvcs=0
        local total_pvcs=0
        
        while IFS= read -r pvc_line; do
            if [ -n "$pvc_line" ]; then
                total_pvcs=$((total_pvcs + 1))
                local pvc_status
                pvc_status=$(echo "$pvc_line" | awk '{print $2}')
                
                if [ "$pvc_status" = "Bound" ]; then
                    bound_pvcs=$((bound_pvcs + 1))
                fi
            fi
        done <<< "$pvcs"
        
        HEALTH_RESULTS["pvc_total"]="$total_pvcs"
        HEALTH_RESULTS["pvc_bound"]="$bound_pvcs"
        
        if [ "$bound_pvcs" -eq "$total_pvcs" ]; then
            HEALTH_RESULTS["persistent_volumes"]="healthy"
            log_success "All PVCs are bound ($bound_pvcs/$total_pvcs)"
        else
            HEALTH_RESULTS["persistent_volumes"]="warning"
            log_warning "Some PVCs are not bound ($bound_pvcs/$total_pvcs)"
        fi
    else
        HEALTH_RESULTS["persistent_volumes"]="warning"
        log_warning "No persistent volume claims found"
    fi
}

# Function to check resource usage
check_resource_usage() {
    log_info "Checking resource usage"
    
    # Check if metrics server is available
    if kubectl top nodes &> /dev/null; then
        # Get node resource usage
        local node_usage
        node_usage=$(kubectl top nodes --no-headers 2>/dev/null)
        
        if [ -n "$node_usage" ]; then
            HEALTH_RESULTS["node_metrics"]="healthy"
            log_success "Node metrics available"
        else
            HEALTH_RESULTS["node_metrics"]="warning"
            log_warning "Node metrics not available"
        fi
        
        # Get pod resource usage
        local pod_usage
        pod_usage=$(kubectl top pods -n "$NAMESPACE" --no-headers 2>/dev/null)
        
        if [ -n "$pod_usage" ]; then
            HEALTH_RESULTS["pod_metrics"]="healthy"
            log_success "Pod metrics available"
        else
            HEALTH_RESULTS["pod_metrics"]="warning"
            log_warning "Pod metrics not available"
        fi
    else
        HEALTH_RESULTS["node_metrics"]="warning"
        HEALTH_RESULTS["pod_metrics"]="warning"
        log_warning "Metrics server not available"
    fi
}

# Function to generate health report
generate_health_report() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$OUTPUT_FORMAT" in
        "json")
            cat << EOF
{
  "health_check_report": {
    "timestamp": "$timestamp",
    "namespace": "$NAMESPACE",
    "overall_health": "$OVERALL_HEALTH",
    "components": {
EOF
            local first=true
            for component in "${!HEALTH_RESULTS[@]}"; do
                if [ "$first" = "true" ]; then
                    first=false
                else
                    echo ","
                fi
                echo -n "      \"$component\": \"${HEALTH_RESULTS[$component]}\""
            done
            cat << EOF

    }
  }
}
EOF
            ;;
        "table")
            echo "Health Check Report - $timestamp"
            echo "Namespace: $NAMESPACE"
            echo "Overall Health: $OVERALL_HEALTH"
            echo ""
            printf "%-25s %-15s\n" "Component" "Status"
            printf "%-25s %-15s\n" "-------------------------" "---------------"
            for component in "${!HEALTH_RESULTS[@]}"; do
                printf "%-25s %-15s\n" "$component" "${HEALTH_RESULTS[$component]}"
            done
            ;;
        "summary")
            echo "Health Check Summary - $timestamp"
            echo "Namespace: $NAMESPACE"
            echo "Overall Health: $OVERALL_HEALTH"
            
            local healthy_count=0
            local warning_count=0
            local unhealthy_count=0
            
            for status in "${HEALTH_RESULTS[@]}"; do
                case "$status" in
                    "healthy") healthy_count=$((healthy_count + 1)) ;;
                    "warning") warning_count=$((warning_count + 1)) ;;
                    "unhealthy") unhealthy_count=$((unhealthy_count + 1)) ;;
                esac
            done
            
            echo "Healthy: $healthy_count"
            echo "Warning: $warning_count"
            echo "Unhealthy: $unhealthy_count"
            ;;
    esac
}

# Main health check function
main() {
    log_info "Starting comprehensive health check for Nautilus Trader"
    
    # Pre-flight checks
    check_kubectl
    
    # Perform health checks
    check_namespace
    check_kubernetes_resources
    check_pod_health
    check_api_health
    check_database_health
    check_redis_health
    check_rabbitmq_health
    check_ingress_health
    check_persistent_volumes
    check_resource_usage
    
    # Generate report
    generate_health_report
    
    # Exit with appropriate code
    if [ "$OVERALL_HEALTH" = "healthy" ]; then
        log_success "Overall system health: HEALTHY"
        exit 0
    else
        log_error "Overall system health: UNHEALTHY"
        exit 1
    fi
}

# Script usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -n, --namespace NAMESPACE       Kubernetes namespace (default: nautilus-trader)
    -t, --timeout TIMEOUT           Health check timeout in seconds (default: 300)
    -i, --interval INTERVAL         Health check interval in seconds (default: 10)
    -r, --retries RETRIES           Maximum retries for health checks (default: 30)
    -f, --format FORMAT             Output format: json, table, summary (default: json)
    -v, --verbose                   Enable verbose logging
    -h, --help                      Show this help message

Environment Variables:
    NAMESPACE                       Kubernetes namespace
    TIMEOUT                         Health check timeout
    HEALTH_CHECK_INTERVAL           Health check interval
    MAX_RETRIES                     Maximum retries
    OUTPUT_FORMAT                   Output format
    VERBOSE                         Enable verbose logging

Examples:
    $0                              # Basic health check with JSON output
    $0 -f table -v                  # Table format with verbose logging
    $0 -n production -t 600         # Check production namespace with 10min timeout

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -i|--interval)
            HEALTH_CHECK_INTERVAL="$2"
            shift 2
            ;;
        -r|--retries)
            MAX_RETRIES="$2"
            shift 2
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="true"
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