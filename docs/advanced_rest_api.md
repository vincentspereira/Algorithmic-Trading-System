# Advanced REST API System

## Overview

The Advanced REST API System provides a comprehensive, enterprise-grade REST API for the Nautilus Trader Engine with OpenAPI 3.0 specification, advanced rate limiting, API versioning, backward compatibility, and extensive documentation capabilities.

## Features

### Core Capabilities

1. **OpenAPI 3.0 Specification**
   - Automatic specification generation
   - Interactive API documentation with Swagger UI
   - Schema validation and type safety
   - Comprehensive endpoint documentation

2. **Advanced Rate Limiting**
   - Multiple rate limiting strategies (per-second, per-minute, per-hour, per-day)
   - Redis-backed distributed rate limiting
   - Memory-based fallback for development
   - Configurable limits per API key and user

3. **API Versioning**
   - Multiple versioning strategies (URL path, query parameter, headers)
   - Backward compatibility management
   - Deprecation warnings and sunset dates
   - Automatic data transformation between versions

4. **Authentication & Authorization**
   - API key management with permissions
   - JWT token support
   - OAuth 2.0 integration ready
   - Role-based access control

5. **Comprehensive Documentation**
   - Auto-generated API documentation
   - Interactive API explorer
   - Code examples and usage guides
   - Migration guides for version changes

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    Advanced REST API System                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ API Gateway     │  │ Rate Limiter    │  │ Version Manager │  │
│  │                 │  │                 │  │                 │  │
│  │ - Routing       │  │ - Redis Backend │  │ - URL Path      │  │
│  │ - Middleware    │  │ - Memory Cache  │  │ - Headers       │  │
│  │ - Error Handling│  │ - Sliding Window│  │ - Query Params  │  │
│  │ - CORS Support  │  │ - Per-Key Limits│  │ - Deprecation   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Authentication  │  │ OpenAPI         │  │ Data Transform  │  │
│  │                 │  │ Generator       │  │                 │  │
│  │ - API Keys      │  │ - Spec Gen      │  │ - Field Mapping │  │
│  │ - JWT Tokens    │  │ - Swagger UI    │  │ - Type Convert  │  │
│  │ - OAuth 2.0     │  │ - Validation    │  │ - Compatibility │  │
│  │ - Permissions   │  │ - Documentation │  │ - Migration     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow

1. **Request Reception**
   ```
   Client Request → CORS Check → Authentication → Rate Limiting → Version Detection
   ```

2. **Processing**
   ```
   Data Transformation → Endpoint Routing → Business Logic → Response Generation
   ```

3. **Response**
   ```
   Data Transformation → Headers Addition → Rate Limit Headers → Client Response
   ```

## Implementation

### Basic Setup

```python
from nautilus_trader_engine.api.advanced_rest_api import create_advanced_api

# Create API with Redis rate limiting
api = create_advanced_api(redis_url="redis://localhost:6379/0")

# Run the API server
api.run(host="0.0.0.0", port=8000, debug=False)
```

### API Key Management

```python
# Create API key
api_key, raw_key = api.api_key_manager.create_api_key(
    user_id="user_123",
    name="Trading Bot API Key",
    permissions=["trading:read", "trading:write", "portfolio:read"],
    rate_limits={
        "default": RateLimitRule(limit=1000, period=3600, per="hour"),
        "trading": RateLimitRule(limit=100, period=60, per="minute")
    },
    expires_hours=8760  # 1 year
)

print(f"API Key: {raw_key}")
print(f"Key ID: {api_key.key_id}")
```

### Rate Limiting Configuration

```python
from nautilus_trader_engine.api.advanced_rest_api import RateLimitRule

# Define rate limits
rate_limits = {
    "default": RateLimitRule(limit=1000, period=3600, per="hour"),
    "trading": RateLimitRule(limit=100, period=60, per="minute"),
    "market_data": RateLimitRule(limit=5000, period=3600, per="hour"),
    "analytics": RateLimitRule(limit=50, period=60, per="minute")
}

# Apply to API key
api_key.rate_limits = rate_limits
```

### API Versioning

```python
from nautilus_trader_engine.api.versioning import (
    create_version_manager, VersioningStrategy, VersionCompatibility, FieldMapping
)

# Create version manager
version_manager = create_version_manager(VersioningStrategy.URL_PATH)

# Add compatibility rule
compatibility = VersionCompatibility(
    source_version="v1",
    target_version="v2",
    field_mappings=[
        FieldMapping(
            old_field="order_state",
            new_field="order_status",
            transformer=lambda x: x.lower(),
            reverse_transformer=lambda x: x.upper()
        ),
        FieldMapping(
            old_field="created_time",
            new_field="created_at",
            transformer=lambda x: datetime.fromisoformat(x).isoformat()
        )
    ]
)

version_manager.add_compatibility_rule(compatibility)
```

### OpenAPI Documentation

```python
from nautilus_trader_engine.api.openapi_generator import (
    create_openapi_generator, OpenAPIEndpoint, OpenAPISchema, 
    OpenAPIParameter, OpenAPIResponse, DataType, ParameterLocation
)

# Create OpenAPI generator
openapi = create_openapi_generator(
    title="Nautilus Trader API",
    version="3.0.0",
    description="Advanced algorithmic trading platform API"
)

# Add servers
openapi.add_server("https://api.nautilustrader.io/v1", "Production")
openapi.add_server("https://staging-api.nautilustrader.io/v1", "Staging")
openapi.add_server("http://localhost:8000/api/v1", "Development")

# Define schema
order_schema = OpenAPISchema(
    name="Order",
    schema_type=DataType.OBJECT,
    properties={
        "order_id": {"type": "string", "description": "Unique order identifier"},
        "symbol": {"type": "string", "description": "Trading symbol"},
        "side": {"type": "string", "enum": ["buy", "sell"]},
        "quantity": {"type": "number", "minimum": 0},
        "price": {"type": "number", "minimum": 0},
        "order_type": {"type": "string", "enum": ["market", "limit", "stop"]},
        "status": {"type": "string", "enum": ["pending", "filled", "cancelled"]},
        "created_at": {"type": "string", "format": "date-time"}
    },
    required=["order_id", "symbol", "side", "quantity", "order_type"],
    description="Trading order object"
)

openapi.add_schema(order_schema)

# Define endpoint
endpoint = OpenAPIEndpoint(
    path="/trading/orders",
    method="POST",
    summary="Create trading order",
    description="Create a new trading order with specified parameters",
    tags=["Trading"],
    parameters=[
        OpenAPIParameter(
            name="X-API-Key",
            location=ParameterLocation.HEADER,
            data_type=DataType.STRING,
            required=True,
            description="API key for authentication"
        )
    ],
    request_body={
        "required": True,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/Order"}
            }
        }
    },
    responses=[
        OpenAPIResponse(
            status_code=201,
            description="Order created successfully",
            schema={"$ref": "#/components/schemas/Order"}
        ),
        OpenAPIResponse(
            status_code=400,
            description="Invalid order parameters",
            schema={"$ref": "#/components/schemas/Error"}
        )
    ]
)

openapi.add_endpoint(endpoint)

# Generate specification
spec = openapi.generate_specification()

# Save to files
openapi.save_specification("api_spec.json", "json")
openapi.save_specification("api_spec.yaml", "yaml")

# Generate HTML documentation
html_docs = openapi.generate_html_documentation()
with open("api_docs.html", "w") as f:
    f.write(html_docs)
```

## API Reference

### Authentication

#### API Key Authentication
```http
GET /api/v1/portfolio/positions
X-API-Key: your_api_key_here
```

#### JWT Token Authentication
```http
GET /api/v1/portfolio/positions
Authorization: Bearer your_jwt_token_here
```

### Core Endpoints

#### System Endpoints

##### Health Check
```http
GET /api/v1/system/health
```

Response:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "1.0.0",
    "uptime": 86400
}
```

##### API Status
```http
GET /api/v1/system/status
```

Response:
```json
{
    "api_version": "v1",
    "total_requests": 150000,
    "avg_response_time": 0.125,
    "active_api_keys": 45,
    "supported_versions": ["v1", "v2", "v3"],
    "rate_limits": {
        "default": "1000/hour",
        "authenticated": "10000/hour"
    }
}
```

#### API Key Management

##### List API Keys
```http
GET /api/v1/system/api-keys
Authorization: Bearer your_jwt_token
```

Response:
```json
{
    "api_keys": [
        {
            "key_id": "key_123456",
            "name": "Trading Bot Key",
            "permissions": ["trading:read", "trading:write"],
            "created_at": "2024-01-01T00:00:00Z",
            "expires_at": "2025-01-01T00:00:00Z",
            "last_used": "2024-01-15T10:30:00Z",
            "usage_count": 1500,
            "is_active": true
        }
    ]
}
```

##### Create API Key
```http
POST /api/v1/system/api-keys
Authorization: Bearer your_jwt_token
Content-Type: application/json

{
    "name": "New Trading Key",
    "permissions": ["trading:read", "portfolio:read"],
    "expires_hours": 8760
}
```

Response:
```json
{
    "key_id": "key_789012",
    "api_key": "key_789012_abcdef123456...",
    "name": "New Trading Key",
    "permissions": ["trading:read", "portfolio:read"],
    "created_at": "2024-01-15T10:30:00Z",
    "expires_at": "2025-01-15T10:30:00Z"
}
```

##### Revoke API Key
```http
DELETE /api/v1/system/api-keys/{key_id}
Authorization: Bearer your_jwt_token
```

Response:
```json
{
    "message": "API key revoked successfully"
}
```

### Trading Endpoints

#### Get Orders
```http
GET /api/v1/trading/orders?page=1&per_page=20&status=pending
X-API-Key: your_api_key
```

#### Create Order
```http
POST /api/v1/trading/orders
X-API-Key: your_api_key
Content-Type: application/json

{
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 100,
    "order_type": "limit",
    "price": 150.25,
    "time_in_force": "DAY"
}
```

#### Cancel Order
```http
DELETE /api/v1/trading/orders/{order_id}
X-API-Key: your_api_key
```

### Portfolio Endpoints

#### Get Positions
```http
GET /api/v1/portfolio/positions
X-API-Key: your_api_key
```

#### Get Portfolio Summary
```http
GET /api/v1/portfolio/summary
X-API-Key: your_api_key
```

### Market Data Endpoints

#### Get Quote
```http
GET /api/v1/market/quote/{symbol}
X-API-Key: your_api_key
```

#### Get Historical Data
```http
GET /api/v1/market/history/{symbol}?timeframe=1D&start=2024-01-01&end=2024-01-15
X-API-Key: your_api_key
```

### Risk Management Endpoints

#### Get Risk Metrics
```http
GET /api/v1/risk/metrics
X-API-Key: your_api_key
```

#### Get VaR Analysis
```http
GET /api/v1/risk/var?confidence=0.95&horizon=1
X-API-Key: your_api_key
```

## Rate Limiting

### Rate Limit Headers

All API responses include rate limiting headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642248000
```

### Rate Limit Exceeded Response

When rate limits are exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1642248000
Retry-After: 3600

{
    "error": {
        "code": 429,
        "name": "Too Many Requests",
        "description": "Rate limit exceeded"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "retry_after": 3600
}
```

### Rate Limiting Strategies

1. **Per-API-Key Limits**
   - Individual limits for each API key
   - Configurable per permission level
   - Separate limits for different endpoint categories

2. **Per-IP Limits**
   - Fallback limits for unauthenticated requests
   - Protection against abuse
   - Configurable thresholds

3. **Sliding Window**
   - Precise rate limiting using sliding time windows
   - Redis-backed for distributed systems
   - Memory fallback for development

## API Versioning

### Versioning Strategies

#### URL Path Versioning (Default)
```http
GET /api/v1/trading/orders
GET /api/v2/trading/orders
GET /api/v3/trading/orders
```

#### Header Versioning
```http
GET /api/trading/orders
Accept: application/vnd.nautilus.v2+json
```

#### Query Parameter Versioning
```http
GET /api/trading/orders?version=v2
```

### Version Compatibility

The API maintains backward compatibility through automatic data transformation:

#### V1 to V2 Transformation
```json
// V1 Request
{
    "order_state": "ACTIVE",
    "created_time": "2024-01-15T10:30:00"
}

// Automatically transformed to V2
{
    "order_status": "active",
    "created_at": "2024-01-15T10:30:00Z"
}
```

### Deprecation Management

#### Deprecation Headers
```http
X-API-Deprecation-Level: soft
X-API-Sunset-Date: 2025-01-15T00:00:00Z
X-API-Migration-Guide: https://docs.nautilustrader.io/api/migration/v1-to-v2
```

#### Deprecation Levels

1. **Soft Deprecation**
   - Warning headers included
   - Full functionality maintained
   - Migration guide provided

2. **Hard Deprecation**
   - Error responses for deprecated endpoints
   - Limited functionality
   - Forced migration required

3. **Sunset**
   - Complete removal of version
   - No longer accessible
   - Redirect to latest version

## Error Handling

### Standard Error Response

```json
{
    "error": {
        "code": 400,
        "name": "Bad Request",
        "description": "The request was invalid or malformed"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "path": "/api/v1/trading/orders",
    "method": "POST",
    "details": {
        "field": "quantity",
        "message": "Quantity must be greater than 0"
    }
}
```

### HTTP Status Codes

- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict
- `422 Unprocessable Entity` - Validation errors
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

## Security

### Authentication Methods

1. **API Keys**
   - Secure key generation with cryptographic randomness
   - Configurable expiration dates
   - Permission-based access control
   - Usage tracking and monitoring

2. **JWT Tokens**
   - Stateless authentication
   - Configurable expiration
   - Role-based claims
   - Refresh token support

3. **OAuth 2.0**
   - Industry standard authorization
   - Third-party integration support
   - Scope-based permissions
   - Secure token exchange

### Security Headers

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### Input Validation

- JSON schema validation
- Parameter type checking
- Range and format validation
- SQL injection prevention
- XSS protection

## Performance Optimization

### Caching Strategy

1. **Response Caching**
   - Redis-backed response cache
   - Configurable TTL per endpoint
   - Cache invalidation on data changes
   - ETag support for conditional requests

2. **Database Query Optimization**
   - Connection pooling
   - Query result caching
   - Index optimization
   - Read replica support

3. **CDN Integration**
   - Static asset caching
   - Geographic distribution
   - Edge caching for frequently accessed data

### Monitoring and Metrics

```python
# Usage analytics
analytics = api.get_usage_analytics(hours=24)

print(f"Total requests: {analytics['total_requests']}")
print(f"Average response time: {analytics['avg_response_time']:.3f}s")
print(f"Error rate: {analytics['error_rate']:.2f}%")
print(f"Top endpoints: {analytics['top_endpoints']}")
```

### Performance Metrics

- Request throughput (requests/second)
- Response time percentiles (P50, P95, P99)
- Error rates by endpoint and status code
- Rate limit utilization
- API key usage patterns
- Geographic request distribution

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "-m", "nautilus_trader_engine.api.advanced_rest_api"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@db:5432/nautilus
    depends_on:
      - redis
      - db

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: nautilus
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  redis_data:
  postgres_data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nautilus-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nautilus-api
  template:
    metadata:
      labels:
        app: nautilus-api
    spec:
      containers:
      - name: api
        image: nautilus-trader/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/system/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: nautilus-api-service
spec:
  selector:
    app: nautilus-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Testing

### Unit Tests

```bash
# Run API tests
python -m pytest tests/test_advanced_rest_api.py -v

# Run with coverage
python -m pytest tests/test_advanced_rest_api.py --cov=nautilus_trader_engine.api
```

### Integration Tests

```python
import requests

# Test API key creation
response = requests.post(
    "http://localhost:8000/api/v1/system/api-keys",
    headers={"Authorization": "Bearer test_token"},
    json={
        "name": "Test Key",
        "permissions": ["trading:read"]
    }
)

assert response.status_code == 201
api_key = response.json()["api_key"]

# Test authenticated request
response = requests.get(
    "http://localhost:8000/api/v1/portfolio/positions",
    headers={"X-API-Key": api_key}
)

assert response.status_code == 200
```

### Load Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 -H "X-API-Key: your_key" http://localhost:8000/api/v1/system/health

# Using wrk
wrk -t12 -c400 -d30s -H "X-API-Key: your_key" http://localhost:8000/api/v1/portfolio/positions
```

## Monitoring and Observability

### Logging

```python
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api.log'),
        logging.StreamHandler()
    ]
)
```

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'Request duration')
active_connections = Gauge('api_active_connections', 'Active connections')

# Use in middleware
request_count.labels(method='GET', endpoint='/orders', status='200').inc()
request_duration.observe(0.125)
```

### Health Checks

```python
# Custom health check
@api.system_ns.route('/health/detailed')
class DetailedHealthCheck(Resource):
    def get(self):
        """Detailed health check with dependencies"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "database": check_database_connection(),
                "redis": check_redis_connection(),
                "external_apis": check_external_apis()
            }
        }
        
        overall_status = all(check["status"] == "healthy" for check in health_status["checks"].values())
        health_status["status"] = "healthy" if overall_status else "unhealthy"
        
        return health_status, 200 if overall_status else 503
```

## Troubleshooting

### Common Issues

1. **Rate Limit Errors**
   - Check API key rate limits
   - Verify Redis connection
   - Monitor request patterns

2. **Authentication Failures**
   - Validate API key format
   - Check key expiration
   - Verify permissions

3. **Version Compatibility Issues**
   - Review compatibility rules
   - Check data transformation logic
   - Validate field mappings

4. **Performance Problems**
   - Monitor response times
   - Check database queries
   - Review caching strategy

### Debug Mode

```python
# Enable debug mode
api = create_advanced_api()
api.run(debug=True)

# Check logs
tail -f api.log | grep ERROR
```

### API Analytics

```python
# Get detailed analytics
analytics = api.get_usage_analytics(hours=24)

print("API Usage Analytics:")
print(f"Total Requests: {analytics['total_requests']}")
print(f"Error Rate: {analytics['error_rate']:.2f}%")
print(f"Avg Response Time: {analytics['avg_response_time']:.3f}s")

print("\nTop Endpoints:")
for endpoint in analytics['top_endpoints'][:5]:
    print(f"  {endpoint['endpoint']}: {endpoint['count']} requests")

print("\nStatus Code Distribution:")
for status, count in analytics['status_codes'].items():
    print(f"  {status}: {count}")
```

## Future Enhancements

### Planned Features

1. **GraphQL Support**
   - GraphQL endpoint alongside REST
   - Schema stitching
   - Real-time subscriptions
   - Query optimization

2. **Advanced Analytics**
   - Machine learning-based anomaly detection
   - Predictive rate limiting
   - Usage pattern analysis
   - Performance optimization recommendations

3. **Enhanced Security**
   - mTLS support
   - Advanced threat detection
   - Audit logging enhancements
   - Compliance reporting

4. **Developer Experience**
   - SDK generation for multiple languages
   - Interactive tutorials
   - Postman collections
   - Code examples repository

## Support and Documentation

### Resources

- **API Documentation**: Interactive Swagger UI at `/docs/`
- **OpenAPI Specification**: Available at `/api/openapi.json`
- **Migration Guides**: Version-specific migration documentation
- **Code Examples**: Sample implementations and use cases

### Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **Documentation**: Comprehensive guides and tutorials
- **Community Forum**: Developer discussions and support
- **Professional Support**: Enterprise support options available

The Advanced REST API System provides a robust, scalable, and well-documented API platform for the Nautilus Trader Engine, enabling seamless integration with trading applications, third-party services, and custom implementations.