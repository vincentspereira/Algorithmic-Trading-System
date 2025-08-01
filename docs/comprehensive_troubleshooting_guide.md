# Nautilus Trader - Comprehensive Troubleshooting Guide

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Common Issues](#common-issues)
3. [Connection Problems](#connection-problems)
4. [Performance Issues](#performance-issues)
5. [Error Messages](#error-messages)
6. [Authentication Issues](#authentication-issues)
7. [Database Issues](#database-issues)
8. [Network Issues](#network-issues)
9. [Timeout Issues](#timeout-issues)
10. [System Resources](#system-resources)
11. [Logging and Debugging](#logging-and-debugging)
12. [Best Practices](#best-practices)

## Quick Diagnostics

### System Health Check

Before diving into specific issues, run these quick diagnostic commands:

```bash
# Check system status
./scripts/deploy/health-check.sh --namespace nautilus-trader --format table

# Check all services
kubectl get pods -n nautilus-trader

# Check logs for errors
kubectl logs -l app.kubernetes.io/name=nautilus-trader -n nautilus-trader --tail=100
```

### Common Diagnostic Commands

```bash
# Check API connectivity
curl -f http://localhost:8000/health

# Check WebSocket connectivity
wscat -c ws://localhost:8001/ws

# Check database connectivity
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "SELECT 1;"

# Check Redis connectivity
kubectl exec -it redis-0 -n nautilus-trader -- redis-cli ping
```

## Common Issues

### Issue: Application Won't Start

**Symptoms:**
- Pods stuck in `Pending` or `CrashLoopBackOff` state
- Error messages in logs about missing dependencies
- Services not responding to health checks

**Diagnosis:**
```bash
# Check pod status
kubectl describe pod <pod-name> -n nautilus-trader

# Check resource availability
kubectl top nodes
kubectl top pods -n nautilus-trader

# Check events
kubectl get events -n nautilus-trader --sort-by='.lastTimestamp'
```

**Solutions:**
1. **Resource Issues**: Increase resource limits or add more nodes
2. **Configuration Issues**: Verify ConfigMaps and Secrets
3. **Image Issues**: Check image availability and pull policies
4. **Dependency Issues**: Ensure all required services are running

### Issue: Slow Performance

**Symptoms:**
- High response times (>2 seconds)
- Low throughput (<1000 RPS)
- High CPU or memory usage

**Diagnosis:**
```bash
# Run performance benchmarks
python performance/comprehensive_test_suite.py

# Check resource usage
kubectl top pods -n nautilus-trader

# Check database performance
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "SELECT * FROM pg_stat_activity;"
```

**Solutions:**
1. **Scale horizontally**: Increase replica count
2. **Optimize queries**: Review and optimize database queries
3. **Add caching**: Implement Redis caching for frequently accessed data
4. **Tune JVM/Python**: Adjust garbage collection and memory settings

## Connection Problems

### Database Connection Issues

**Symptoms:**
- `Connection refused` errors
- `Too many connections` errors
- Intermittent database connectivity

**Diagnosis:**
```bash
# Check database pod status
kubectl get pods -l app.kubernetes.io/name=postgresql -n nautilus-trader

# Check database logs
kubectl logs postgresql-0 -n nautilus-trader

# Test connection from application pod
kubectl exec -it <api-pod> -n nautilus-trader -- nc -zv postgresql-service 5432
```

**Solutions:**
1. **Connection Pool Settings**:
   ```yaml
   DB_POOL_SIZE: "20"
   DB_MAX_OVERFLOW: "30"
   DB_POOL_TIMEOUT: "30"
   ```

2. **Database Configuration**:
   ```sql
   ALTER SYSTEM SET max_connections = 200;
   ALTER SYSTEM SET shared_buffers = '256MB';
   SELECT pg_reload_conf();
   ```

3. **Network Policies**: Verify Kubernetes network policies allow database access

### Redis Connection Issues

**Symptoms:**
- Cache misses
- `Connection timeout` errors
- Redis unavailable errors

**Diagnosis:**
```bash
# Check Redis status
kubectl exec -it redis-0 -n nautilus-trader -- redis-cli info

# Test Redis connectivity
kubectl exec -it <api-pod> -n nautilus-trader -- nc -zv redis-service 6379

# Check Redis configuration
kubectl exec -it redis-0 -n nautilus-trader -- redis-cli config get "*"
```

**Solutions:**
1. **Increase timeout values**:
   ```yaml
   REDIS_TIMEOUT: "5"
   REDIS_RETRY_ON_TIMEOUT: "true"
   ```

2. **Connection pooling**:
   ```yaml
   REDIS_MAX_CONNECTIONS: "100"
   REDIS_CONNECTION_POOL_SIZE: "50"
   ```

## Performance Issues

### High Latency

**Symptoms:**
- API response times > 100ms
- WebSocket message delays
- Trading execution delays

**Diagnosis:**
```bash
# Run latency benchmarks
python performance/latency_benchmarking_clean.py

# Check network latency
kubectl exec -it <pod> -n nautilus-trader -- ping google.com

# Profile application
python performance/resource_profiling.py
```

**Solutions:**
1. **Optimize algorithms**: Review and optimize trading algorithms
2. **Database indexing**: Add indexes for frequently queried columns
3. **Caching**: Implement intelligent caching strategies
4. **Network optimization**: Use faster network connections

### High Memory Usage

**Symptoms:**
- Memory usage > 85%
- Out of memory errors
- Pod restarts due to memory limits

**Diagnosis:**
```bash
# Check memory usage
kubectl top pods -n nautilus-trader

# Check memory limits
kubectl describe pod <pod-name> -n nautilus-trader

# Profile memory usage
python performance/resource_profiling.py
```

**Solutions:**
1. **Increase memory limits**:
   ```yaml
   resources:
     limits:
       memory: "4Gi"
     requests:
       memory: "2Gi"
   ```

2. **Memory optimization**:
   - Implement object pooling
   - Optimize garbage collection
   - Fix memory leaks

### High CPU Usage

**Symptoms:**
- CPU usage > 80%
- Slow response times
- High load averages

**Diagnosis:**
```bash
# Check CPU usage
kubectl top pods -n nautilus-trader

# Profile CPU usage
python performance/resource_profiling.py

# Check CPU limits
kubectl describe pod <pod-name> -n nautilus-trader
```

**Solutions:**
1. **Scale horizontally**: Add more replicas
2. **Optimize code**: Profile and optimize CPU-intensive operations
3. **Increase CPU limits**:
   ```yaml
   resources:
     limits:
       cpu: "2000m"
     requests:
       cpu: "1000m"
   ```

## Error Messages

### Common Error Patterns

#### "Connection refused"
**Cause**: Service is not running or not accessible
**Solution**: 
```bash
# Check service status
kubectl get svc -n nautilus-trader
kubectl get endpoints -n nautilus-trader
```

#### "Authentication failed"
**Cause**: Invalid credentials or expired tokens
**Solution**:
```bash
# Check secrets
kubectl get secrets -n nautilus-trader
kubectl describe secret nautilus-trader-secrets -n nautilus-trader
```

#### "Resource not found"
**Cause**: Missing configuration or incorrect resource names
**Solution**:
```bash
# Check resource names
kubectl get all -n nautilus-trader
kubectl describe configmap nautilus-trader-config -n nautilus-trader
```

#### "Timeout exceeded"
**Cause**: Operations taking too long or network issues
**Solution**:
```bash
# Increase timeout values
# Check network connectivity
# Optimize slow operations
```

## Authentication Issues

### JWT Token Problems

**Symptoms:**
- `Invalid token` errors
- `Token expired` errors
- Authentication failures

**Diagnosis:**
```bash
# Check JWT configuration
kubectl get configmap nautilus-trader-config -n nautilus-trader -o yaml | grep JWT

# Verify token generation
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"test"}'
```

**Solutions:**
1. **Token expiration**: Increase token lifetime
2. **Secret rotation**: Update JWT secrets
3. **Clock synchronization**: Ensure system clocks are synchronized

### API Key Issues

**Symptoms:**
- `Invalid API key` errors
- `API key not found` errors
- External service authentication failures

**Diagnosis:**
```bash
# Check API key configuration
kubectl get secrets nautilus-trader-secrets -n nautilus-trader -o yaml

# Test API key validity
curl -H "X-API-Key: <key>" https://api.external-service.com/test
```

**Solutions:**
1. **Key rotation**: Update expired API keys
2. **Permission issues**: Verify API key permissions
3. **Rate limiting**: Check for rate limit violations

## Database Issues

### PostgreSQL Problems

**Symptoms:**
- Slow queries
- Connection pool exhaustion
- Database locks

**Diagnosis:**
```bash
# Check database performance
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;"

# Check active connections
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "
SELECT count(*) FROM pg_stat_activity;"

# Check for locks
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "
SELECT * FROM pg_locks WHERE NOT granted;"
```

**Solutions:**
1. **Query optimization**: Add indexes, rewrite slow queries
2. **Connection pooling**: Implement proper connection pooling
3. **Database tuning**: Optimize PostgreSQL configuration

### Data Consistency Issues

**Symptoms:**
- Inconsistent data across services
- Transaction failures
- Data corruption

**Diagnosis:**
```bash
# Check data integrity
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public';"

# Verify foreign key constraints
kubectl exec -it postgresql-0 -n nautilus-trader -- psql -U nautilus -d nautilus_trader -c "
SELECT conname, conrelid::regclass, confrelid::regclass 
FROM pg_constraint 
WHERE contype = 'f';"
```

**Solutions:**
1. **Transaction management**: Implement proper transaction boundaries
2. **Data validation**: Add comprehensive data validation
3. **Backup and recovery**: Implement regular backups

## Network Issues

### Connectivity Problems

**Symptoms:**
- Intermittent connection failures
- High network latency
- Packet loss

**Diagnosis:**
```bash
# Test network connectivity
kubectl exec -it <pod> -n nautilus-trader -- ping <target-host>
kubectl exec -it <pod> -n nautilus-trader -- traceroute <target-host>
kubectl exec -it <pod> -n nautilus-trader -- nc -zv <host> <port>

# Check network policies
kubectl get networkpolicies -n nautilus-trader

# Check DNS resolution
kubectl exec -it <pod> -n nautilus-trader -- nslookup <service-name>
```

**Solutions:**
1. **Network policies**: Review and update network policies
2. **DNS configuration**: Fix DNS resolution issues
3. **Load balancing**: Implement proper load balancing
4. **Network optimization**: Optimize network configuration

### Firewall Issues

**Symptoms:**
- Connection timeouts
- Blocked ports
- External service access failures

**Diagnosis:**
```bash
# Check port accessibility
kubectl exec -it <pod> -n nautilus-trader -- telnet <host> <port>

# Check service endpoints
kubectl get endpoints -n nautilus-trader

# Test external connectivity
kubectl exec -it <pod> -n nautilus-trader -- curl -v https://external-api.com
```

**Solutions:**
1. **Firewall rules**: Update firewall configurations
2. **Security groups**: Modify cloud security groups
3. **Network ACLs**: Review network access control lists

## Timeout Issues

### Request Timeouts

**Symptoms:**
- HTTP 504 Gateway Timeout errors
- WebSocket connection timeouts
- Database query timeouts

**Diagnosis:**
```bash
# Check timeout configurations
kubectl get configmap nautilus-trader-config -n nautilus-trader -o yaml | grep -i timeout

# Monitor request durations
kubectl logs -f <api-pod> -n nautilus-trader | grep -i timeout

# Check load balancer timeouts
kubectl describe ingress nautilus-trader-ingress -n nautilus-trader
```

**Solutions:**
1. **Increase timeout values**:
   ```yaml
   API_TIMEOUT: "60"
   DB_TIMEOUT: "30"
   REDIS_TIMEOUT: "10"
   ```

2. **Optimize slow operations**: Profile and optimize slow code paths
3. **Implement async processing**: Use background jobs for long-running tasks

### Connection Timeouts

**Symptoms:**
- Connection establishment failures
- Keep-alive timeout errors
- Idle connection drops

**Solutions:**
1. **Connection pooling**: Implement proper connection pooling
2. **Keep-alive settings**: Configure appropriate keep-alive values
3. **Retry logic**: Implement exponential backoff retry logic

## System Resources

### Disk Space Issues

**Symptoms:**
- `No space left on device` errors
- Log rotation failures
- Database write failures

**Diagnosis:**
```bash
# Check disk usage
kubectl exec -it <pod> -n nautilus-trader -- df -h

# Check persistent volume usage
kubectl get pv
kubectl describe pv <pv-name>

# Check log sizes
kubectl exec -it <pod> -n nautilus-trader -- du -sh /var/log/*
```

**Solutions:**
1. **Increase storage**: Expand persistent volumes
2. **Log rotation**: Implement proper log rotation
3. **Cleanup**: Remove unnecessary files and old logs

### Memory Leaks

**Symptoms:**
- Gradually increasing memory usage
- Out of memory errors after extended runtime
- Pod restarts due to memory limits

**Diagnosis:**
```bash
# Monitor memory usage over time
python performance/resource_profiling.py

# Check for memory leaks
kubectl exec -it <pod> -n nautilus-trader -- ps aux --sort=-%mem | head -10

# Analyze heap dumps (if available)
kubectl exec -it <pod> -n nautilus-trader -- jmap -dump:format=b,file=heap.hprof <pid>
```

**Solutions:**
1. **Code review**: Review code for memory leaks
2. **Profiling**: Use memory profiling tools
3. **Garbage collection**: Optimize garbage collection settings

## Logging and Debugging

### Log Analysis

**Common log locations:**
```bash
# Application logs
kubectl logs <pod-name> -n nautilus-trader

# System logs
kubectl logs <pod-name> -n nautilus-trader -c <container-name>

# Previous container logs
kubectl logs <pod-name> -n nautilus-trader --previous
```

**Log levels and filtering:**
```bash
# Filter by log level
kubectl logs <pod-name> -n nautilus-trader | grep ERROR

# Follow logs in real-time
kubectl logs -f <pod-name> -n nautilus-trader

# Get logs from multiple pods
kubectl logs -l app.kubernetes.io/name=nautilus-trader -n nautilus-trader
```

### Debug Mode

**Enable debug logging:**
```yaml
# In ConfigMap
LOG_LEVEL: "DEBUG"
DEBUG_MODE: "true"
VERBOSE_LOGGING: "true"
```

**Debug specific components:**
```bash
# Enable database query logging
DB_LOG_QUERIES: "true"

# Enable API request logging
API_LOG_REQUESTS: "true"

# Enable WebSocket message logging
WEBSOCKET_LOG_MESSAGES: "true"
```

## Best Practices

### Monitoring and Alerting

1. **Set up comprehensive monitoring**:
   - Use Prometheus for metrics collection
   - Configure Grafana dashboards
   - Set up alerting rules

2. **Monitor key metrics**:
   - Response times and throughput
   - Error rates and success rates
   - Resource utilization (CPU, memory, disk)
   - Business metrics (trades, orders, positions)

3. **Implement health checks**:
   - Liveness probes for pod health
   - Readiness probes for traffic routing
   - Custom health check endpoints

### Preventive Measures

1. **Regular maintenance**:
   - Update dependencies regularly
   - Rotate secrets and certificates
   - Clean up old logs and data

2. **Capacity planning**:
   - Monitor resource trends
   - Plan for peak loads
   - Implement auto-scaling

3. **Disaster recovery**:
   - Regular backups
   - Test recovery procedures
   - Document runbooks

### Performance Optimization

1. **Database optimization**:
   - Regular VACUUM and ANALYZE
   - Monitor slow queries
   - Optimize indexes

2. **Application optimization**:
   - Profile code regularly
   - Implement caching strategies
   - Optimize algorithms

3. **Infrastructure optimization**:
   - Right-size resources
   - Use appropriate storage classes
   - Optimize network configuration

### Security Best Practices

1. **Access control**:
   - Use RBAC for Kubernetes access
   - Implement least privilege principle
   - Regular access reviews

2. **Secret management**:
   - Use Kubernetes secrets
   - Rotate secrets regularly
   - Avoid hardcoded credentials

3. **Network security**:
   - Implement network policies
   - Use TLS for all communications
   - Regular security audits

## Getting Help

### Internal Resources

1. **Documentation**: Check the comprehensive documentation in `/docs`
2. **Logs**: Always check application and system logs first
3. **Monitoring**: Use Grafana dashboards for system insights
4. **Health checks**: Run the health check script regularly

### External Resources

1. **Kubernetes documentation**: https://kubernetes.io/docs/
2. **PostgreSQL documentation**: https://www.postgresql.org/docs/
3. **Redis documentation**: https://redis.io/documentation
4. **Prometheus documentation**: https://prometheus.io/docs/

### Support Escalation

1. **Level 1**: Check this troubleshooting guide
2. **Level 2**: Review system logs and metrics
3. **Level 3**: Contact the development team with:
   - Detailed problem description
   - Steps to reproduce
   - Relevant logs and metrics
   - System configuration details

---

*This troubleshooting guide is maintained by the Nautilus Trader team. Last updated: August 2025*