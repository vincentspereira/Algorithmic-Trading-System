# Order Management Service

This microservice manages the entire lifecycle of trading orders, from validation through execution and settlement.

## Core Responsibilities

- Order validation and pre-trade compliance checks
- Order routing and execution management
- Fill processing and trade settlement
- Order status tracking and reporting
- Smart order routing (SOR) algorithms
- Execution algorithms (TWAP, VWAP, Iceberg)

## Architecture

The service follows microservices principles:
- Single responsibility for order management
- Stateless design with external state storage
- Event-driven communication via Kafka
- RESTful API for synchronous operations
- WebSocket for real-time order updates

## API Endpoints

- `POST /orders` - Place new order
- `GET /orders/{order_id}` - Get order status
- `PUT /orders/{order_id}` - Modify order
- `DELETE /orders/{order_id}` - Cancel order
- `GET /orders/user/{user_id}` - Get user orders
- `WebSocket /orders/stream` - Real-time order updates

## Event Integration

### Consumed Events
- `market.data.*` - Market data for order execution
- `risk.check.request` - Risk assessment requests
- `portfolio.position.update` - Position updates

### Produced Events
- `order.created` - New order placed
- `order.filled` - Order execution completed
- `order.cancelled` - Order cancellation
- `order.rejected` - Order rejection
- `trade.settlement` - Trade settlement completed

## Configuration

Service configuration is managed through environment variables and configuration files:

- `ORDER_SERVICE_PORT` - Service port (default: 8001)
- `DATABASE_URL` - Database connection string
- `KAFKA_BROKERS` - Kafka broker addresses
- `RISK_SERVICE_URL` - Risk management service endpoint
- `BROKER_API_KEYS` - Broker API credentials

## Monitoring

The service exposes metrics for monitoring:

- Order processing latency
- Fill rates and slippage
- Error rates by order type
- Active order counts
- Broker connectivity status

## Development

See the main project documentation for development setup and testing procedures.