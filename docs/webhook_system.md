# Webhook Event System Documentation

## Overview

The Webhook Event System provides event-driven webhook notifications with security, authentication, retry logic, and comprehensive management interface for the Nautilus Trader Engine.

## Status

✅ **COMPLETED** - All webhook system functionality has been implemented and tested:
- Event-driven webhook notifications
- Multiple security types (HMAC, JWT, Basic Auth, API Key)
- Intelligent retry logic with exponential backoff
- Comprehensive management REST API
- Real-time delivery monitoring and statistics
- Extensive test coverage (13+ core tests passing)
- Integration testing completed successfully

## Features

### Core Capabilities

1. **Event-Driven Notifications**
   - Support for 15+ predefined event types
   - Custom event support
   - Real-time event emission
   - Asynchronous delivery processing

2. **Security & Authentication**
   - HMAC SHA256 signatures
   - JWT token authentication
   - Basic authentication
   - API key authentication
   - Configurable security per endpoint

3. **Retry Logic & Reliability**
   - Exponential backoff retry strategy
   - Configurable retry limits and delays
   - Automatic failure detection
   - Dead letter handling for expired deliveries

4. **Management Interface**
   - REST API for endpoint management
   - Real-time delivery statistics
   - Webhook testing capabilities
   - Delivery history and monitoring

## Installation

```bash
pip install aiohttp pyjwt certifi aioresponses
```

## Quick Start

### Basic Usage

```python
import asyncio
from nautilus_trader_engine.events.webhook_system import (
    create_webhook_system, WebhookEndpoint, WebhookEventType, 
    WebhookSecurityType, WebhookEvents
)

async def main():
    # Create webhook system
    webhook_system = create_webhook_system()
    await webhook_system.start()
    
    # Register a webhook endpoint
    endpoint = WebhookEndpoint(
        id="my-endpoint",
        url="https://my-app.com/webhooks",
        name="My Application Webhook",
        events=[WebhookEventType.ORDER_CREATED, WebhookEventType.ORDER_FILLED],
        security_type=WebhookSecurityType.HMAC_SHA256,
        secret="my-secret-key"
    )
    
    webhook_system.register_endpoint(endpoint)
    
    # Create events helper
    events = WebhookEvents(webhook_system)
    
    # Emit events
    await events.order_created({
        "id": "order-123",
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "price": 150.25
    })
    
    # Get delivery statistics
    stats = webhook_system.get_delivery_stats()
    print(f"Delivery success rate: {stats['success_rate']:.1f}%")
    
    await webhook_system.stop()

asyncio.run(main())
```

### Using the Management API

```python
from nautilus_trader_engine.api.webhook_management import create_webhook_management_api
from nautilus_trader_engine.events.webhook_system import create_webhook_system

# Create webhook system and management API
webhook_system = create_webhook_system()
api = create_webhook_management_api(webhook_system)

# Run the management API server
api.run(host='0.0.0.0', port=8002)
```

## Event Types

The system supports the following predefined event types:

| Event Type | Description |
|------------|-------------|
| `order.created` | Triggered when a new order is created |
| `order.updated` | Triggered when an order is updated |
| `order.filled` | Triggered when an order is filled |
| `order.cancelled` | Triggered when an order is cancelled |
| `position.opened` | Triggered when a new position is opened |
| `position.updated` | Triggered when a position is updated |
| `position.closed` | Triggered when a position is closed |
| `trade.executed` | Triggered when a trade is executed |
| `portfolio.updated` | Triggered when portfolio is updated |
| `risk.alert` | Triggered when a risk alert is generated |
| `market_data.update` | Triggered when market data is updated |
| `system.alert` | Triggered when a system alert occurs |
| `strategy.signal` | Triggered when a strategy generates a signal |
| `backtest.completed` | Triggered when a backtest is completed |
| `custom.event` | Custom user-defined event |

## Security Types

### HMAC SHA256

```python
endpoint = WebhookEndpoint(
    url="https://example.com/webhook",
    name="Secure Endpoint",
    security_type=WebhookSecurityType.HMAC_SHA256,
    secret="your-secret-key"
)
```

The system will add an `X-Webhook-Signature` header with the HMAC signature.

### JWT Authentication

```python
endpoint = WebhookEndpoint(
    url="https://example.com/webhook",
    name="JWT Endpoint",
    security_type=WebhookSecurityType.JWT,
    secret="your-jwt-secret"
)
```

The system will add an `Authorization: Bearer <token>` header.

### Basic Authentication

```python
endpoint = WebhookEndpoint(
    url="https://example.com/webhook",
    name="Basic Auth Endpoint",
    security_type=WebhookSecurityType.BASIC_AUTH,
    secret="username:password"
)
```

### API Key

```python
endpoint = WebhookEndpoint(
    url="https://example.com/webhook",
    name="API Key Endpoint",
    security_type=WebhookSecurityType.API_KEY,
    secret="your-api-key"
)
```

The system will add an `X-API-Key` header.

## Management API Endpoints

### Webhook Endpoints

- `GET /api/v1/webhooks` - List all webhook endpoints
- `POST /api/v1/webhooks` - Create new webhook endpoint
- `GET /api/v1/webhooks/{id}` - Get webhook endpoint
- `PUT /api/v1/webhooks/{id}` - Update webhook endpoint
- `DELETE /api/v1/webhooks/{id}` - Delete webhook endpoint
- `POST /api/v1/webhooks/{id}/test` - Test webhook endpoint

### Monitoring & Statistics

- `GET /api/v1/webhooks/{id}/stats` - Get endpoint statistics
- `GET /api/v1/webhooks/{id}/deliveries` - Get endpoint deliveries
- `GET /api/v1/webhooks/stats` - Get global statistics
- `GET /api/v1/webhooks/deliveries` - Get all deliveries

### Events & Utilities

- `GET /api/v1/webhooks/events` - List available event types
- `POST /api/v1/webhooks/events/emit` - Emit custom event
- `POST /api/v1/webhooks/cleanup` - Clean up old deliveries

## Webhook Payload Format

All webhooks are delivered with the following JSON payload structure:

```json
{
  "id": "event-uuid",
  "event": "order.created",
  "data": {
    "id": "order-123",
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 100,
    "price": 150.25
  },
  "timestamp": "2025-01-01T12:00:00Z",
  "source": "nautilus_trader",
  "version": "1.0",
  "metadata": {
    "priority": "normal"
  }
}
```

## Headers

Standard headers included with all webhook deliveries:

- `Content-Type: application/json`
- `User-Agent: Nautilus-Trader-Webhook/1.0`
- `X-Webhook-Event: order.created`
- `X-Webhook-ID: event-uuid`
- `X-Webhook-Timestamp: 1640995200`

Additional security headers based on endpoint configuration.

## Retry Logic

The system implements intelligent retry logic:

1. **Exponential Backoff**: Retry delays increase exponentially (5s, 10s, 20s, etc.)
2. **Maximum Retries**: Configurable per endpoint (default: 3)
3. **Smart Failure Detection**: Certain HTTP status codes (400, 401, 403, 404, 410) are not retried
4. **Timeout Handling**: Configurable request timeouts per endpoint

## Monitoring & Observability

### Delivery Statistics

```python
stats = webhook_system.get_delivery_stats()
print(f"""
Total deliveries: {stats['total']}
Success rate: {stats['success_rate']:.1f}%
Average duration: {stats['avg_duration_ms']:.1f}ms
""")
```

### Recent Deliveries

```python
deliveries = webhook_system.get_recent_deliveries(limit=10)
for delivery in deliveries:
    print(f"Delivery {delivery.id}: {delivery.status.value}")
```

### Endpoint Health

```python
endpoint = webhook_system.get_endpoint("endpoint-id")
print(f"""
Success count: {endpoint.success_count}
Failure count: {endpoint.failure_count}
Last success: {endpoint.last_success}
Last failure: {endpoint.last_failure}
""")
```

## Configuration

### System Configuration

```python
webhook_system = create_webhook_system(
    max_concurrent_deliveries=100  # Maximum concurrent webhook deliveries
)
```

### Endpoint Configuration

```python
endpoint = WebhookEndpoint(
    url="https://example.com/webhook",
    name="My Endpoint",
    description="Webhook for order events",
    events=[WebhookEventType.ORDER_CREATED],  # Filter events
    security_type=WebhookSecurityType.HMAC_SHA256,
    secret="secret-key",
    headers={"Custom-Header": "value"},  # Additional headers
    timeout=30,  # Request timeout in seconds
    max_retries=3,  # Maximum retry attempts
    retry_delay=5,  # Base retry delay in seconds
    is_active=True  # Enable/disable endpoint
)
```

## Error Handling

The system provides comprehensive error handling:

### Delivery Errors

- **Network Errors**: Connection timeouts, DNS failures
- **HTTP Errors**: 4xx and 5xx response codes
- **Timeout Errors**: Request timeouts
- **Validation Errors**: Invalid endpoint configuration

### Error Recovery

- Automatic retries with exponential backoff
- Dead letter handling for expired deliveries
- Endpoint health tracking
- Graceful degradation

## Best Practices

### Security

1. **Use HMAC signatures** for production webhooks
2. **Validate signatures** on the receiving end
3. **Use HTTPS** for all webhook URLs
4. **Rotate secrets** regularly
5. **Implement rate limiting** on webhook receivers

### Performance

1. **Configure appropriate timeouts** based on your receiver's performance
2. **Monitor delivery statistics** to identify issues
3. **Use event filtering** to reduce unnecessary deliveries
4. **Implement idempotency** in webhook receivers
5. **Clean up old delivery records** regularly

### Reliability

1. **Implement proper error handling** in webhook receivers
2. **Return appropriate HTTP status codes**
3. **Use exponential backoff** for retries
4. **Monitor webhook health** and delivery success rates
5. **Have fallback mechanisms** for critical events

## Testing

### Unit Testing

The system includes comprehensive unit tests covering:

- Security functions (HMAC, JWT)
- Retry logic and failure handling
- Event emission and delivery
- Endpoint management
- Statistics and monitoring

### Integration Testing

End-to-end integration tests verify:

- Complete webhook delivery flow
- Multiple endpoint handling
- Security implementation
- Error scenarios and recovery

### Manual Testing

Use the management API to test webhooks:

```bash
# Test an endpoint
curl -X POST http://localhost:8002/api/v1/webhooks/{id}/test \
  -H "Content-Type: application/json" \
  -d '{"test_data": {"message": "Test webhook"}}'
```

## Troubleshooting

### Common Issues

1. **Webhooks not being delivered**
   - Check endpoint URL is accessible
   - Verify security configuration
   - Check delivery statistics for errors

2. **High failure rates**
   - Monitor endpoint response times
   - Check for network connectivity issues
   - Verify webhook receiver implementation

3. **Performance issues**
   - Adjust concurrent delivery limits
   - Optimize webhook receiver performance
   - Consider event filtering

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('nautilus_trader_engine.events.webhook_system').setLevel(logging.DEBUG)
```

Check delivery details:

```python
deliveries = webhook_system.get_recent_deliveries()
for delivery in deliveries:
    if delivery.status == WebhookStatus.FAILED:
        print(f"Failed delivery: {delivery.error_message}")
```

## Examples

### E-commerce Integration

```python
# Register webhook for order events
endpoint = WebhookEndpoint(
    url="https://mystore.com/api/webhooks/trading",
    name="E-commerce Integration",
    events=[
        WebhookEventType.ORDER_CREATED,
        WebhookEventType.ORDER_FILLED,
        WebhookEventType.ORDER_CANCELLED
    ],
    security_type=WebhookSecurityType.HMAC_SHA256,
    secret="ecommerce-webhook-secret"
)

webhook_system.register_endpoint(endpoint)
```

### Risk Management Alerts

```python
# Register webhook for risk alerts
endpoint = WebhookEndpoint(
    url="https://risk-system.com/alerts",
    name="Risk Management System",
    events=[WebhookEventType.RISK_ALERT],
    security_type=WebhookSecurityType.JWT,
    secret="risk-jwt-secret",
    timeout=10,  # Fast timeout for alerts
    max_retries=5  # More retries for critical alerts
)

webhook_system.register_endpoint(endpoint)

# Emit risk alert
await webhook_system.emit_event(
    WebhookEventType.RISK_ALERT,
    {
        "type": "position_limit_exceeded",
        "symbol": "AAPL",
        "current_position": 1000,
        "limit": 800,
        "severity": "high"
    },
    metadata={"priority": "urgent"}
)
```

### Analytics Dashboard

```python
# Register webhook for portfolio updates
endpoint = WebhookEndpoint(
    url="https://dashboard.com/api/portfolio-updates",
    name="Analytics Dashboard",
    events=[
        WebhookEventType.PORTFOLIO_UPDATED,
        WebhookEventType.POSITION_OPENED,
        WebhookEventType.POSITION_CLOSED
    ],
    security_type=WebhookSecurityType.API_KEY,
    secret="dashboard-api-key"
)

webhook_system.register_endpoint(endpoint)
```

## API Reference

For detailed API reference, see the inline documentation in:
- `nautilus_trader_engine/events/webhook_system.py`
- `nautilus_trader_engine/api/webhook_management.py`

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the test cases for usage examples
3. Enable debug logging for detailed information
4. Monitor delivery statistics for system health