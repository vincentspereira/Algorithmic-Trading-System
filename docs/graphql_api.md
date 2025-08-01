# GraphQL API Implementation

## Overview

The GraphQL API Implementation provides a comprehensive GraphQL interface for the Nautilus Trader Engine with real-time subscriptions, query optimization, intelligent caching, and an interactive GraphQL playground for flexible data queries and mutations.

## Status

✅ **COMPLETED** - All GraphQL API functionality has been implemented and tested:
- Core GraphQL schema with queries, mutations, and subscriptions
- Query complexity analysis and validation
- Caching system with Redis support
- Real-time subscriptions for market data and order updates
- GraphQL Playground interface
- Comprehensive test coverage (29/29 tests passing)
- Integration testing completed successfully

## Features

### Core Capabilities

1. **Comprehensive GraphQL Schema**
   - Complete type system for trading operations
   - Queries for data retrieval
   - Mutations for data modification
   - Subscriptions for real-time updates

2. **Real-Time Subscriptions**
   - Live order updates
   - Position changes
   - Market data streams
   - Portfolio updates

3. **Query Optimization**
   - Complexity analysis and limiting
   - Query depth restrictions
   - Field counting and validation
   - Performance monitoring

4. **Intelligent Caching**
   - Redis-backed query result caching
   - Memory-based fallback caching
   - Automatic cache invalidation
   - Configurable TTL per query type

5. **Interactive Development**
   - GraphQL Playground interface
   - Schema introspection
   - Query validation and testing
   - Real-time query execution

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    GraphQL API System                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ GraphQL Schema  │  │ Query Cache     │  │ Complexity      │  │
│  │                 │  │                 │  │ Analyzer        │  │
│  │ - Types         │  │ - Redis Backend │  │                 │  │
│  │ - Queries       │  │ - Memory Cache  │  │ - Depth Check   │  │
│  │ - Mutations     │  │ - TTL Management│  │ - Field Count   │  │
│  │ - Subscriptions │  │ - Invalidation  │  │ - Score Calc    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Resolvers       │  │ Subscriptions   │  │ Playground      │  │
│  │                 │  │                 │  │                 │  │
│  │ - Data Fetching │  │ - WebSocket     │  │ - Interactive   │  │
│  │ - Business Logic│  │ - Real-time     │  │ - Schema Docs   │  │
│  │ - Error Handling│  │ - Event Streams │  │ - Query Testing │  │
│  │ - Validation    │  │ - Auto Cleanup  │  │ - Examples      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Query Processing**
   ```
   GraphQL Query → Complexity Analysis → Cache Check → Resolver Execution → Response
   ```

2. **Real-Time Subscriptions**
   ```
   Client Subscribe → WebSocket Connection → Event Stream → Live Updates
   ```

3. **Caching Strategy**
   ```
   Query → Cache Key Generation → Redis/Memory Lookup → Store Result → Return
   ```

## Implementation

### Basic Setup

```python
from nautilus_trader_engine.api.graphql_api import create_graphql_api

# Create GraphQL API with Redis caching
api = create_graphql_api(redis_url="redis://localhost:6379/0")

# Run the API server
api.run(host="0.0.0.0", port=8001, debug=False)
```

### Custom Schema Extension

```python
import graphene
from graphene import ObjectType, String, Field, List

class CustomType(ObjectType):
    """Custom GraphQL type"""
    id = String(required=True)
    name = String(required=True)
    value = String()
    
    @staticmethod
    def resolve_value(root, info):
        return f"Custom value for {root.get('name', 'unknown')}"

class ExtendedQuery(ObjectType):
    """Extended query with custom fields"""
    custom_data = Field(CustomType, id=graphene.Argument(String, required=True))
    custom_list = List(CustomType)
    
    async def resolve_custom_data(self, info, id):
        return {
            'id': id,
            'name': f'Custom Item {id}',
            'value': f'Value for {id}'
        }
    
    async def resolve_custom_list(self, info):
        return [
            {'id': '1', 'name': 'Item 1'},
            {'id': '2', 'name': 'Item 2'},
            {'id': '3', 'name': 'Item 3'}
        ]

# Extend the schema
from graphene import Schema
extended_schema = Schema(query=ExtendedQuery)
```

### Caching Configuration

```python
from nautilus_trader_engine.api.graphql_api import GraphQLCache

# Create cache with custom TTL
cache = GraphQLCache(default_ttl=600)  # 10 minutes

# Cache specific query
query = "query { portfolio { totalValue } }"
result = {"data": {"portfolio": {"totalValue": 150000.0}}}

await cache.set(query, {}, result, ttl=300)  # Cache for 5 minutes

# Retrieve cached result
cached_result = await cache.get(query, {})

# Invalidate cache pattern
await cache.invalidate_pattern("portfolio")
```

### Query Complexity Analysis

```python
from nautilus_trader_engine.api.graphql_api import QueryComplexityAnalyzer

# Create analyzer with custom limits
analyzer = QueryComplexityAnalyzer(
    max_complexity=100,
    max_depth=10
)

# Analyze query
from graphql import parse
query_ast = parse("""
    query {
        portfolio {
            positions {
                symbol
                quantity
                marketValue
            }
        }
    }
""")

analysis = analyzer.analyze_query(query_ast)
print(f"Complexity: {analysis['complexity']}")
print(f"Depth: {analysis['depth']}")
print(f"Valid: {analysis['is_valid']}")
```

## GraphQL Schema

### Types

#### Order Type
```graphql
type Order {
  id: String!
  symbol: String!
  side: String!
  quantity: Float!
  price: Float
  orderType: String!
  status: String!
  createdAt: String!
  updatedAt: String
  filledQuantity: Float
  averagePrice: Float
}
```

#### Position Type
```graphql
type Position {
  symbol: String!
  quantity: Float!
  averagePrice: Float!
  marketPrice: Float!
  marketValue: Float!
  unrealizedPnl: Float!
  realizedPnl: Float
  percentageChange: Float
}
```

#### Portfolio Type
```graphql
type Portfolio {
  totalValue: Float!
  cashBalance: Float!
  positions: [Position]
  totalPnl: Float
  dailyPnl: Float
  positionsCount: Int
}
```

#### Market Data Type
```graphql
type MarketData {
  symbol: String!
  lastPrice: Float!
  bid: Float
  ask: Float
  volume: Int
  change: Float
  changePercent: Float
  high: Float
  low: Float
  timestamp: String!
}
```

### Queries

#### Get Orders
```graphql
query GetOrders($symbol: String, $status: String, $limit: Int, $offset: Int) {
  orders(symbol: $symbol, status: $status, limit: $limit, offset: $offset) {
    id
    symbol
    side
    quantity
    price
    orderType
    status
    createdAt
  }
}
```

#### Get Portfolio
```graphql
query GetPortfolio {
  portfolio {
    totalValue
    cashBalance
    totalPnl
    dailyPnl
    positionsCount
    positions {
      symbol
      quantity
      averagePrice
      marketPrice
      marketValue
      unrealizedPnl
      percentageChange
    }
  }
}
```

#### Get Market Data
```graphql
query GetMarketData($symbol: String!) {
  marketData(symbol: $symbol) {
    symbol
    lastPrice
    bid
    ask
    volume
    change
    changePercent
    high
    low
    timestamp
  }
}
```

#### Get Multiple Market Data
```graphql
query GetMultipleMarketData($symbols: [String]!) {
  marketDataList(symbols: $symbols) {
    symbol
    lastPrice
    change
    changePercent
    volume
    timestamp
  }
}
```

#### Get Analytics
```graphql
query GetAnalytics($startDate: String, $endDate: String) {
  analytics(startDate: $startDate, endDate: $endDate) {
    totalTrades
    winRate
    profitFactor
    sharpeRatio
    maxDrawdown
    averageTradePnl
    bestTrade
    worstTrade
  }
}
```

### Mutations

#### Create Order
```graphql
mutation CreateOrder(
  $symbol: String!
  $side: String!
  $quantity: Float!
  $orderType: String!
  $price: Float
  $stopPrice: Float
) {
  createOrder(
    symbol: $symbol
    side: $side
    quantity: $quantity
    orderType: $orderType
    price: $price
    stopPrice: $stopPrice
  ) {
    success
    message
    order {
      id
      symbol
      side
      quantity
      price
      orderType
      status
      createdAt
    }
  }
}
```

#### Cancel Order
```graphql
mutation CancelOrder($orderId: String!) {
  cancelOrder(orderId: $orderId) {
    success
    message
  }
}
```

### Subscriptions

#### Order Updates
```graphql
subscription OrderUpdates($symbol: String) {
  orderUpdates(symbol: $symbol) {
    id
    symbol
    side
    quantity
    price
    orderType
    status
    createdAt
  }
}
```

#### Position Updates
```graphql
subscription PositionUpdates($symbol: String) {
  positionUpdates(symbol: $symbol) {
    symbol
    quantity
    averagePrice
    marketPrice
    marketValue
    unrealizedPnl
    percentageChange
  }
}
```

#### Market Data Updates
```graphql
subscription MarketDataUpdates($symbol: String!) {
  marketDataUpdates(symbol: $symbol) {
    symbol
    lastPrice
    bid
    ask
    volume
    change
    changePercent
    timestamp
  }
}
```

#### Portfolio Updates
```graphql
subscription PortfolioUpdates {
  portfolioUpdates {
    totalValue
    cashBalance
    totalPnl
    dailyPnl
    positionsCount
  }
}
```

## Usage Examples

### Basic Query Execution

```python
import asyncio
from graphene import Schema

# Execute query
query = """
query {
  orders(limit: 10) {
    id
    symbol
    side
    quantity
    status
  }
}
"""

async def execute_query():
    result = await schema.execute_async(query)
    if result.errors:
        print("Errors:", result.errors)
    else:
        print("Data:", result.data)

asyncio.run(execute_query())
```

### Query with Variables

```python
query = """
query GetOrdersBySymbol($symbol: String!, $limit: Int) {
  orders(symbol: $symbol, limit: $limit) {
    id
    symbol
    side
    quantity
    price
    status
  }
}
"""

variables = {
    "symbol": "AAPL",
    "limit": 20
}

result = await schema.execute_async(query, variables=variables)
```

### Mutation Execution

```python
mutation = """
mutation CreateNewOrder(
  $symbol: String!
  $side: String!
  $quantity: Float!
  $orderType: String!
  $price: Float
) {
  createOrder(
    symbol: $symbol
    side: $side
    quantity: $quantity
    orderType: $orderType
    price: $price
  ) {
    success
    message
    order {
      id
      symbol
      status
    }
  }
}
"""

variables = {
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 100,
    "orderType": "limit",
    "price": 150.25
}

result = await schema.execute_async(mutation, variables=variables)
```

### Subscription Handling

```python
import asyncio

async def handle_subscription():
    subscription = """
    subscription {
      marketDataUpdates(symbol: "AAPL") {
        symbol
        lastPrice
        change
        changePercent
        timestamp
      }
    }
    """
    
    async for result in schema.subscribe(subscription):
        if result.data:
            market_data = result.data['marketDataUpdates']
            print(f"AAPL: ${market_data['lastPrice']:.2f} "
                  f"({market_data['changePercent']:+.2f}%)")

# Run subscription
asyncio.run(handle_subscription())
```

## GraphQL Playground

### Accessing the Playground

The GraphQL Playground is available at `/graphql/playground` and provides:

- Interactive query editor with syntax highlighting
- Schema documentation browser
- Query validation and autocomplete
- Real-time query execution
- Subscription testing
- Query history and sharing

### Sample Queries in Playground

```graphql
# Get portfolio overview
query PortfolioOverview {
  portfolio {
    totalValue
    cashBalance
    totalPnl
    dailyPnl
    positions {
      symbol
      quantity
      marketValue
      unrealizedPnl
    }
  }
}

# Create a limit order
mutation PlaceLimitOrder {
  createOrder(
    symbol: "AAPL"
    side: "buy"
    quantity: 100
    orderType: "limit"
    price: 150.25
  ) {
    success
    message
    order {
      id
      status
    }
  }
}

# Subscribe to real-time market data
subscription RealTimeMarketData {
  marketDataUpdates(symbol: "AAPL") {
    symbol
    lastPrice
    change
    changePercent
    timestamp
  }
}
```

## Performance Optimization

### Query Complexity Management

```python
# Configure complexity limits
analyzer = QueryComplexityAnalyzer(
    max_complexity=50,    # Maximum complexity score
    max_depth=8          # Maximum query depth
)

# Field complexity mapping
field_complexity = {
    'id': 1,             # Simple fields
    'orders': 5,         # Collection fields
    'analytics': 10,     # Computed fields
    'marketData': 25     # External data fields
}
```

### Caching Strategy

```python
# Cache configuration
cache_config = {
    'portfolio': 60,      # Cache portfolio for 1 minute
    'positions': 30,      # Cache positions for 30 seconds
    'orders': 10,         # Cache orders for 10 seconds
    'marketData': 5,      # Cache market data for 5 seconds
    'analytics': 300      # Cache analytics for 5 minutes
}

# Implement selective caching
async def cached_resolver(query, variables, resolver_func):
    cache_key = generate_cache_key(query, variables)
    
    # Check cache first
    cached_result = await cache.get(cache_key)
    if cached_result:
        return cached_result
    
    # Execute resolver
    result = await resolver_func()
    
    # Cache result
    ttl = get_cache_ttl(query)
    await cache.set(cache_key, result, ttl)
    
    return result
```

### Subscription Optimization

```python
# Efficient subscription management
class SubscriptionManager:
    def __init__(self):
        self.subscriptions = {}
        self.data_streams = {}
    
    async def subscribe(self, subscription_id, query, variables):
        """Subscribe to data stream"""
        stream_key = self.get_stream_key(query, variables)
        
        if stream_key not in self.data_streams:
            # Create new data stream
            self.data_streams[stream_key] = self.create_data_stream(query, variables)
        
        # Add subscription to stream
        self.subscriptions[subscription_id] = stream_key
    
    async def unsubscribe(self, subscription_id):
        """Unsubscribe from data stream"""
        if subscription_id in self.subscriptions:
            stream_key = self.subscriptions[subscription_id]
            del self.subscriptions[subscription_id]
            
            # Clean up unused streams
            if not any(sk == stream_key for sk in self.subscriptions.values()):
                if stream_key in self.data_streams:
                    await self.data_streams[stream_key].close()
                    del self.data_streams[stream_key]
```

## Error Handling

### Query Validation Errors

```json
{
  "errors": [
    {
      "message": "Query too complex. Complexity: 75, Max: 50",
      "extensions": {
        "code": "QUERY_TOO_COMPLEX",
        "complexity": 75,
        "depth": 12
      }
    }
  ]
}
```

### Resolver Errors

```json
{
  "errors": [
    {
      "message": "Order not found",
      "locations": [{"line": 3, "column": 5}],
      "path": ["order"],
      "extensions": {
        "code": "ORDER_NOT_FOUND",
        "orderId": "12345"
      }
    }
  ],
  "data": {
    "order": null
  }
}
```

### Mutation Validation Errors

```json
{
  "data": {
    "createOrder": {
      "success": false,
      "message": "Invalid order parameters: Quantity must be greater than 0",
      "order": null
    }
  }
}
```

## Monitoring and Analytics

### Query Metrics

```python
# Get GraphQL metrics
metrics = api.get_metrics_summary(hours=24)

print(f"Total queries: {metrics['total_queries']}")
print(f"Average execution time: {metrics['avg_execution_time']:.3f}s")
print(f"Average complexity: {metrics['avg_complexity']:.1f}")
print(f"Error rate: {metrics['error_rate']:.2f}%")

# Top queries
for query_info in metrics['top_queries'][:5]:
    print(f"Query: {query_info['query'][:50]}... Count: {query_info['count']}")

# Complexity distribution
for complexity_range, count in metrics['complexity_distribution'].items():
    print(f"{complexity_range}: {count} queries")
```

### Performance Monitoring

```python
# Monitor subscription performance
subscription_metrics = {
    'active_subscriptions': len(subscription_manager.subscriptions),
    'active_streams': len(subscription_manager.data_streams),
    'memory_usage': get_memory_usage(),
    'cpu_usage': get_cpu_usage()
}

# Monitor cache performance
cache_metrics = {
    'cache_hits': cache.hit_count,
    'cache_misses': cache.miss_count,
    'cache_hit_rate': cache.hit_count / (cache.hit_count + cache.miss_count),
    'cache_size': len(cache.memory_cache),
    'cache_memory_usage': get_cache_memory_usage()
}
```

## Security Considerations

### Query Depth and Complexity Limits

```python
# Prevent DoS attacks through complex queries
complexity_analyzer = QueryComplexityAnalyzer(
    max_complexity=100,   # Limit total complexity
    max_depth=10,        # Limit nesting depth
    timeout=30           # Query timeout in seconds
)
```

### Authentication and Authorization

```python
# Add authentication to resolvers
async def authenticated_resolver(root, info, **kwargs):
    # Check authentication
    user = get_current_user(info.context)
    if not user:
        raise GraphQLError("Authentication required")
    
    # Check authorization
    if not user.has_permission('trading:read'):
        raise GraphQLError("Insufficient permissions")
    
    # Execute resolver logic
    return await resolve_data(**kwargs)
```

### Input Validation

```python
# Validate mutation inputs
async def create_order_resolver(root, info, symbol, side, quantity, **kwargs):
    # Validate symbol
    if not is_valid_symbol(symbol):
        raise GraphQLError(f"Invalid symbol: {symbol}")
    
    # Validate side
    if side not in ['buy', 'sell']:
        raise GraphQLError(f"Invalid side: {side}")
    
    # Validate quantity
    if quantity <= 0:
        raise GraphQLError("Quantity must be greater than 0")
    
    # Process order
    return await process_order(symbol, side, quantity, **kwargs)
```

## Testing

### Unit Tests

```python
import pytest
from graphene.test import Client

@pytest.fixture
def client():
    return Client(schema)

def test_orders_query(client):
    query = """
    query {
        orders(limit: 5) {
            id
            symbol
            status
        }
    }
    """
    
    result = client.execute(query)
    
    assert 'errors' not in result
    assert 'orders' in result['data']
    assert len(result['data']['orders']) == 5

def test_create_order_mutation(client):
    mutation = """
    mutation {
        createOrder(
            symbol: "AAPL"
            side: "buy"
            quantity: 100
            orderType: "limit"
            price: 150.25
        ) {
            success
            message
        }
    }
    """
    
    result = client.execute(mutation)
    
    assert 'errors' not in result
    assert result['data']['createOrder']['success'] is True
```

### Integration Tests

```python
import asyncio
import websockets
import json

async def test_subscription():
    """Test GraphQL subscription over WebSocket"""
    uri = "ws://localhost:8001/graphql"
    
    async with websockets.connect(uri, subprotocols=["graphql-ws"]) as websocket:
        # Send connection init
        await websocket.send(json.dumps({
            "type": "connection_init"
        }))
        
        # Wait for connection ack
        response = await websocket.recv()
        assert json.loads(response)["type"] == "connection_ack"
        
        # Start subscription
        await websocket.send(json.dumps({
            "id": "1",
            "type": "start",
            "payload": {
                "query": """
                subscription {
                    marketDataUpdates(symbol: "AAPL") {
                        symbol
                        lastPrice
                        timestamp
                    }
                }
                """
            }
        }))
        
        # Receive data
        for _ in range(5):
            response = await websocket.recv()
            data = json.loads(response)
            assert data["type"] == "data"
            assert "marketDataUpdates" in data["payload"]["data"]

# Run test
asyncio.run(test_subscription())
```

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Expose GraphQL port
EXPOSE 8001

# Run GraphQL API
CMD ["python", "-m", "nautilus_trader_engine.api.graphql_api"]
```

### Docker Compose with Redis

```yaml
version: '3.8'

services:
  graphql-api:
    build: .
    ports:
      - "8001:8001"
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./logs:/app/logs

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

volumes:
  redis_data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: graphql-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: graphql-api
  template:
    metadata:
      labels:
        app: graphql-api
    spec:
      containers:
      - name: graphql-api
        image: nautilus-trader/graphql-api:latest
        ports:
        - containerPort: 8001
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /graphql/playground
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: graphql-api-service
spec:
  selector:
    app: graphql-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8001
  type: LoadBalancer
```

## Best Practices

### Schema Design

1. **Use descriptive names** for types, fields, and arguments
2. **Follow GraphQL naming conventions** (camelCase for fields, PascalCase for types)
3. **Design for client needs** rather than database structure
4. **Use nullable fields** judiciously
5. **Provide comprehensive descriptions** for all schema elements

### Query Optimization

1. **Implement DataLoader** for N+1 query prevention
2. **Use query complexity analysis** to prevent abuse
3. **Cache frequently accessed data** with appropriate TTL
4. **Optimize resolver performance** with database indexing
5. **Monitor query performance** and identify bottlenecks

### Subscription Management

1. **Limit concurrent subscriptions** per client
2. **Implement proper cleanup** for disconnected clients
3. **Use efficient data streaming** mechanisms
4. **Monitor subscription memory usage**
5. **Provide subscription rate limiting**

### Error Handling

1. **Use structured error responses** with error codes
2. **Provide helpful error messages** for developers
3. **Log errors appropriately** for debugging
4. **Handle partial failures** gracefully
5. **Implement proper error boundaries**

## Troubleshooting

### Common Issues

1. **Query Complexity Errors**
   - Reduce query depth or field count
   - Optimize resolver implementations
   - Adjust complexity limits if appropriate

2. **Subscription Memory Leaks**
   - Ensure proper cleanup of disconnected subscriptions
   - Monitor active subscription count
   - Implement subscription limits

3. **Cache Performance Issues**
   - Check Redis connection and performance
   - Optimize cache key generation
   - Adjust TTL values based on data volatility

4. **Resolver Performance Problems**
   - Implement DataLoader for batch loading
   - Add database indexes for frequently queried fields
   - Use async resolvers for I/O operations

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('nautilus_trader_engine.api.graphql_api').setLevel(logging.DEBUG)

# Run with debug mode
api = create_graphql_api()
api.run(debug=True)
```

The GraphQL API Implementation provides a powerful, flexible, and performant interface for the Nautilus Trader Engine, enabling developers to build sophisticated trading applications with real-time capabilities and optimal data fetching patterns.