# CI/CD Deployment Guide - Nautilus Trader

## Overview

This guide provides comprehensive instructions for deploying Nautilus Trader using our CI/CD pipeline with GitOps, blue-green deployments, canary releases, and disaster recovery capabilities.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GitOps Setup](#gitops-setup)
3. [Deployment Strategies](#deployment-strategies)
4. [Rollback Procedures](#rollback-procedures)
5. [Disaster Recovery](#disaster-recovery)
6. [Health Monitoring](#health-monitoring)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

- **Kubernetes Cluster**: v1.24+
- **kubectl**: Latest version
- **Helm**: v3.8+
- **ArgoCD**: v2.5+
- **Docker**: v20.10+
- **Git**: v2.30+

### Required Permissions

- Cluster admin access for initial setup
- Namespace admin access for deployments
- Container registry push/pull access

### Environment Setup

```bash
# Set environment variables
export NAMESPACE="nautilus-trader"
export REGISTRY="your-registry.com/nautilus-trader"
export ENVIRONMENT="production"  # or staging, development
```

## GitOps Setup

### 1. ArgoCD Installation

```bash
# Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Wait for ArgoCD to be ready
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd

# Get initial admin password
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

### 2. Configure ArgoCD Applications

```bash
# Apply ArgoCD applications
kubectl apply -f gitops/argocd/nautilus-trader-app.yaml

# Verify applications
kubectl get applications -n argocd
```

### 3. Repository Setup

```bash
# Configure repository access
argocd repo add https://github.com/your-org/nautilus-trader.git \
  --username your-username \
  --password your-token \
  --name nautilus-trader-repo
```

## Deployment Strategies

### Blue-Green Deployment

Blue-green deployment provides zero-downtime deployments by maintaining two identical production environments.

#### Usage

```bash
# Perform blue-green deployment
./scripts/deploy/blue-green-deployment.sh \
  --namespace nautilus-trader \
  --image nautilus-trader/api:v1.1.0 \
  --timeout 600

# With custom configuration
./scripts/deploy/blue-green-deployment.sh \
  --namespace nautilus-trader \
  --image nautilus-trader/api:v1.1.0 \
  --blue-replicas 3 \
  --green-replicas 3 \
  --health-check-retries 10 \
  --confirm
```

#### Process Flow

1. **Preparation**: Validate current blue environment
2. **Green Deployment**: Deploy new version to green environment
3. **Health Checks**: Verify green environment health
4. **Traffic Switch**: Route traffic from blue to green
5. **Cleanup**: Remove old blue environment

#### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--namespace` | Kubernetes namespace | `nautilus-trader` |
| `--image` | Container image to deploy | Required |
| `--blue-replicas` | Blue environment replicas | `3` |
| `--green-replicas` | Green environment replicas | `3` |
| `--timeout` | Deployment timeout (seconds) | `600` |
| `--health-check-retries` | Health check attempts | `10` |
| `--confirm` | Skip confirmation prompt | `false` |

### Canary Deployment

Canary deployment gradually rolls out new versions to a subset of users.

#### Usage

```bash
# Start canary deployment
./scripts/deploy/canary-deployment.sh \
  --namespace nautilus-trader \
  --image nautilus-trader/api:v1.1.0 \
  --canary-percentage 10

# Promote canary to full deployment
./scripts/deploy/canary-deployment.sh \
  --namespace nautilus-trader \
  --promote-canary \
  --canary-percentage 100
```

#### Canary Stages

1. **Initial Canary**: Deploy to 10% of traffic
2. **Monitoring**: Monitor metrics and error rates
3. **Gradual Rollout**: Increase to 25%, 50%, 75%
4. **Full Deployment**: Route 100% traffic to new version
5. **Cleanup**: Remove old version

#### Monitoring Metrics

- **Error Rate**: < 1% increase from baseline
- **Response Time**: < 10% increase from baseline
- **CPU/Memory**: Within acceptable limits
- **Business Metrics**: Trading performance indicators

### Rolling Deployment

Standard Kubernetes rolling deployment with enhanced monitoring.

```bash
# Rolling deployment via Helm
helm upgrade nautilus-trader ./k8s/helm/nautilus-trader \
  --namespace nautilus-trader \
  --set image.tag=v1.1.0 \
  --set replicaCount=5 \
  --timeout 10m

# Monitor rollout
kubectl rollout status deployment/nautilus-trader-api -n nautilus-trader
```

## Rollback Procedures

### Automatic Rollback

The system automatically triggers rollback when:
- Health checks fail for 5 consecutive minutes
- Error rate exceeds 5% for 3 minutes
- Response time increases by >50% for 5 minutes

### Manual Rollback

#### Quick Rollback to Previous Version

```bash
# Rollback to previous revision
./scripts/deploy/rollback-deployment.sh \
  --namespace nautilus-trader \
  --deployment nautilus-trader-api

# Rollback to specific revision
./scripts/deploy/rollback-deployment.sh \
  --namespace nautilus-trader \
  --deployment nautilus-trader-api \
  --revision 5
```

#### Rollback Process

1. **Validation**: Check current deployment status
2. **Revision Selection**: Choose target revision
3. **Rollback Execution**: Perform Kubernetes rollback
4. **Health Verification**: Verify system health
5. **Notification**: Send rollback status notifications

#### Rollback Verification

```bash
# Verify rollback success
kubectl get deployment nautilus-trader-api -n nautilus-trader
kubectl rollout history deployment/nautilus-trader-api -n nautilus-trader

# Check application health
./scripts/deploy/health-check.sh --namespace nautilus-trader --format table
```

## Disaster Recovery

### Backup Strategy

#### Automated Backups

- **Database**: Daily full backup, hourly incremental
- **Configuration**: Real-time backup to Git repository
- **Persistent Volumes**: Daily snapshots
- **Secrets**: Encrypted backup to secure storage

#### Backup Locations

- **Primary**: Cloud storage (S3/GCS/Azure Blob)
- **Secondary**: On-premises backup server
- **Tertiary**: Cross-region replication

### Recovery Procedures

#### Full System Recovery

```bash
# Full disaster recovery
./scripts/deploy/disaster-recovery.sh \
  --namespace nautilus-trader \
  --mode full \
  --backup-location /backups/nautilus-trader

# Database-only recovery
./scripts/deploy/disaster-recovery.sh \
  --namespace nautilus-trader \
  --mode database-only \
  --backup-location /backups/nautilus-trader
```

#### Recovery Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `full` | Complete system recovery | Total system failure |
| `partial` | Application-only recovery | Application corruption |
| `database-only` | Database recovery only | Database corruption |
| `helm` | Helm-based recovery | Configuration issues |

#### Recovery Testing

```bash
# Dry run disaster recovery
./scripts/deploy/disaster-recovery.sh \
  --namespace nautilus-trader-test \
  --mode full \
  --dry-run \
  --backup-location /backups/nautilus-trader
```

### RTO/RPO Targets

- **Recovery Time Objective (RTO)**: 15 minutes
- **Recovery Point Objective (RPO)**: 5 minutes
- **Maximum Tolerable Downtime**: 30 minutes

## Health Monitoring

### Comprehensive Health Checks

```bash
# Basic health check
./scripts/deploy/health-check.sh --namespace nautilus-trader

# Detailed health check with table output
./scripts/deploy/health-check.sh \
  --namespace nautilus-trader \
  --format table \
  --verbose

# Continuous monitoring
watch -n 30 './scripts/deploy/health-check.sh --namespace nautilus-trader --format summary'
```

### Health Check Components

#### System Components

- **Kubernetes Resources**: Deployments, services, pods
- **Database**: PostgreSQL connectivity and performance
- **Cache**: Redis availability and response time
- **Message Queue**: RabbitMQ health and queue status
- **API**: HTTP endpoints and response times
- **WebSocket**: Connection stability and message flow

#### Performance Metrics

- **Response Time**: API endpoint latency
- **Throughput**: Requests per second
- **Error Rate**: HTTP 4xx/5xx responses
- **Resource Usage**: CPU, memory, disk, network
- **Business Metrics**: Trading performance indicators

### Alerting Configuration

#### Alert Thresholds

```yaml
alerts:
  critical:
    - api_error_rate > 5%
    - database_connection_failures > 10
    - pod_restart_count > 5
  warning:
    - api_response_time > 2s
    - memory_usage > 80%
    - disk_usage > 85%
```

#### Notification Channels

- **Slack**: Real-time alerts to trading team
- **Email**: Detailed reports to operations team
- **PagerDuty**: Critical alerts for on-call engineers
- **SMS**: Emergency notifications

## Troubleshooting

### Common Issues

#### Deployment Failures

```bash
# Check deployment status
kubectl describe deployment nautilus-trader-api -n nautilus-trader

# Check pod logs
kubectl logs -l app.kubernetes.io/name=nautilus-trader -n nautilus-trader --tail=100

# Check events
kubectl get events -n nautilus-trader --sort-by='.lastTimestamp'
```

#### Database Connection Issues

```bash
# Check PostgreSQL pod
kubectl get pods -l app.kubernetes.io/name=postgresql -n nautilus-trader

# Test database connectivity
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "SELECT 1;"

# Check database logs
kubectl logs postgresql-0 -n nautilus-trader --tail=50
```

#### Performance Issues

```bash
# Check resource usage
kubectl top pods -n nautilus-trader
kubectl top nodes

# Check HPA status
kubectl get hpa -n nautilus-trader

# Check service mesh metrics (if using Istio)
kubectl get virtualservices,destinationrules -n nautilus-trader
```

### Debug Commands

#### Pod Debugging

```bash
# Get pod details
kubectl describe pod <pod-name> -n nautilus-trader

# Execute commands in pod
kubectl exec -it <pod-name> -n nautilus-trader -- /bin/bash

# Port forward for local debugging
kubectl port-forward <pod-name> 8080:8000 -n nautilus-trader
```

#### Network Debugging

```bash
# Test service connectivity
kubectl run debug --image=nicolaka/netshoot -it --rm -- /bin/bash

# Check DNS resolution
nslookup nautilus-trader-api.nautilus-trader.svc.cluster.local

# Test HTTP endpoints
curl -v http://nautilus-trader-api.nautilus-trader.svc.cluster.local:8000/health
```

### Log Analysis

#### Centralized Logging

```bash
# Query logs with kubectl
kubectl logs -l app.kubernetes.io/name=nautilus-trader -n nautilus-trader --since=1h

# Filter logs by level
kubectl logs -l app.kubernetes.io/name=nautilus-trader -n nautilus-trader | grep ERROR

# Follow logs in real-time
kubectl logs -f deployment/nautilus-trader-api -n nautilus-trader
```

#### Log Aggregation

- **ELK Stack**: Elasticsearch, Logstash, Kibana
- **Grafana Loki**: Lightweight log aggregation
- **Fluentd**: Log collection and forwarding

### Performance Tuning

#### Resource Optimization

```yaml
# Optimized resource requests/limits
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

#### Database Tuning

```sql
-- PostgreSQL optimization
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

#### Cache Optimization

```redis
# Redis optimization
CONFIG SET maxmemory 512mb
CONFIG SET maxmemory-policy allkeys-lru
CONFIG SET save "900 1 300 10 60 10000"
```

## Security Considerations

### Network Security

- **Network Policies**: Restrict pod-to-pod communication
- **TLS Encryption**: End-to-end encryption for all traffic
- **Service Mesh**: Istio for advanced traffic management

### Secret Management

- **Kubernetes Secrets**: Encrypted at rest
- **External Secret Operators**: Integration with HashiCorp Vault
- **Secret Rotation**: Automated credential rotation

### Image Security

- **Image Scanning**: Vulnerability scanning in CI/CD
- **Signed Images**: Container image signing
- **Minimal Base Images**: Distroless or Alpine-based images

## Best Practices

### Deployment Best Practices

1. **Always test in staging first**
2. **Use feature flags for gradual rollouts**
3. **Monitor business metrics during deployments**
4. **Have rollback procedures ready**
5. **Document all deployment changes**

### Monitoring Best Practices

1. **Set up comprehensive alerting**
2. **Monitor both technical and business metrics**
3. **Use distributed tracing for complex flows**
4. **Implement health checks at multiple levels**
5. **Regular disaster recovery testing**

### Security Best Practices

1. **Principle of least privilege**
2. **Regular security audits**
3. **Automated vulnerability scanning**
4. **Network segmentation**
5. **Audit logging for all operations**

## Support and Escalation

### Support Levels

- **L1**: Basic operational issues
- **L2**: Application and infrastructure issues
- **L3**: Complex system issues and architecture changes

### Escalation Procedures

1. **Immediate**: Critical production issues
2. **4 hours**: High priority issues
3. **24 hours**: Medium priority issues
4. **72 hours**: Low priority issues

### Contact Information

- **Operations Team**: ops@nautilus-trader.com
- **Development Team**: dev@nautilus-trader.com
- **On-Call Engineer**: +1-555-ON-CALL (24/7)

---

*This guide is maintained by the Nautilus Trader DevOps team. Last updated: $(date '+%Y-%m-%d')*