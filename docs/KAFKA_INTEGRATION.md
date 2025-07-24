# Kafka Integration Documentation

## Overview

The Kafka integration provides real-time market data streaming capabilities for the algorithmic trading system. It enables the system to publish market data from various sources to Kafka topics and consume that data for trading decisions.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Feeds    │───▶│  Kafka Producer │───▶│  Kafka Topics   │
│   (11 sources)  │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌─────────────────┐             │
│ Trading Engine  │◀───│  Kafka Consumer │◀────────────┘
│                 │    │                 │
└─────────────────┘    └─────────────────┘
```

## Key Components

### 1. MarketDataStreamer
- **Purpose**: High-level service for streaming market data
- **Features**: 
  - Manages both producer and consumer
  - Handles multiple symbols and asset classes
  - Provides background streaming service
  - Integrates with data feed fallback system

### 2. KafkaProducerService
- **Purpose**: Publishes market data to Kafka topics
- **Features**:
  - JSON serialization
  - Error handling and retries
  - Rate limiting awareness
  - Metrics collection

### 3. KafkaConsumerService
- **Purpose**: Consumes market data from Kafka topics
- **Features**:
  - Configurable message handlers
  - Automatic offset management
  - Error recovery
  - Background processing

### 4. KafkaManager
- **Purpose**: High-level management and API integration
- **Features**:
  - Service lifecycle management
  - API endpoint integration
  - Status monitoring
  - Configuration management

## Kafka Topics

### Market Data Topics

| Topic | Purpose | Message Format |
|-------|---------|----------------|
| `market.stock.prices` | Stock price data | MarketDataMessage |
| `market.forex.rates` | Forex exchange rates | MarketDataMessage |
| `market.crypto.prices` | Cryptocurrency prices | MarketDataMessage |
| `market.futures.prices` | Futures contract prices | MarketDataMessage |
| `market.options.prices` | Options contract prices | MarketDataMessage |
| `market.commodities.prices` | Commodity prices | MarketDataMessage |
| `market.news` | Market news and events | NewsMessage |
| `market.indicators` | Economic indicators | IndicatorMessage |

### Trading Topics

| Topic | Purpose | Message Format |
|-------|---------|----------------|
| `trading.signals` | Trading signals | TradingSignal |
| `trading.backtest.results` | Backtest results | BacktestResult |

## Message Formats

### MarketDataMessage
```json
{
  "symbol": "AAPL",
  "asset_class": "stock",
  "timestamp": 1640995200.0,
  "data_source": "yahoo_finance",
  "data": [
    {
      "datetime": "2023-01-01T00:00:00",
      "open": 150.0,
      "high": 155.0,
      "low": 149.0,
      "close": 154.0,
      "volume": 1000000
    }
  ],
  "metadata": {
    "interval": "1d",
    "period": "1y"
  },
  "message_id": "AAPL_1640995200",
  "version": "1.0"
}
```

### TradingSignal
```json
{
  "type": "buy",
  "symbol": "AAPL",
  "price": 150.00,
  "quantity": 100,
  "timestamp": 1640995200.0,
  "strategy": "moving_average_crossover",
  "confidence": 0.85,
  "metadata": {
    "fast_ma": 10,
    "slow_ma": 30
  }
}
```

## API Endpoints

### Kafka Status
```http
GET /api/v1/kafka/status
```
Returns the current status of Kafka connections and streaming.

**Response:**
```json
{
  "status": "connected",
  "kafka_streaming": {
    "is_streaming": true,
    "producer_connected": true,
    "consumer_connected": true,
    "streaming_symbols": ["AAPL", "GOOGL"],
    "messages_published": 1250,
    "messages_consumed": 890
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Start Streaming
```http
POST /api/v1/kafka/streaming/start
Content-Type: application/json

{
  "symbol": "AAPL",
  "asset_class": "stock",
  "interval": "1m"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Started streaming for AAPL",
  "symbol": "AAPL",
  "asset_class": "stock",
  "interval": "1m"
}
```

### Stop Streaming
```http
POST /api/v1/kafka/streaming/stop
Content-Type: application/json

{
  "symbol": "AAPL"
}
```

### Get Streaming Symbols
```http
GET /api/v1/kafka/streaming/symbols
```

**Response:**
```json
{
  "symbols": [
    {
      "symbol": "AAPL",
      "asset_class": "stock",
      "topic": "market.stock.prices",
      "interval": "1m",
      "last_update": 1640995200.0
    }
  ],
  "count": 1,
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Get Kafka Topics
```http
GET /api/v1/kafka/topics
```

### Test Connection
```http
POST /api/v1/kafka/test
```

### Publish Trading Signal
```http
POST /api/v1/kafka/signal
Content-Type: application/json

{
  "type": "buy",
  "symbol": "AAPL",
  "price": 150.00,
  "quantity": 100,
  "strategy": "test_strategy"
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker addresses |
| `KAFKA_CLIENT_ID` | `nautilus-trader-engine` | Client identifier |
| `KAFKA_GROUP_ID` | `trading-system` | Consumer group ID |

### KafkaConfig Parameters

```python
config = KafkaConfig(
    bootstrap_servers="kafka:9092",
    client_id="nautilus-trader-engine",
    group_id="trading-system",
    auto_offset_reset="latest",
    compression_type="gzip",
    acks="all",
    retries=3
)
```

## Usage Examples

### Basic Streaming Setup

```python
from kafka_integration import MarketDataStreamer, KafkaConfig, AssetClass

# Create and initialize streamer
config = KafkaConfig(bootstrap_servers="kafka:9092")
streamer = MarketDataStreamer(config)
await streamer.initialize()

# Start streaming for a symbol
await streamer.start_streaming_symbol("AAPL", AssetClass.STOCK, "1m")

# Publish data
await streamer.publish_market_data_for_symbol("AAPL")

# Start consumer
await streamer.start_consumer()
```

### Custom Message Handler

```python
async def custom_handler(message_data):
    symbol = message_data.get('symbol')
    price_data = message_data.get('data', [])
    
    # Process the market data
    for record in price_data:
        print(f"{symbol}: {record['close']}")

# Register handler
streamer.consumer.register_handler(
    MarketDataTopic.STOCK_PRICES, 
    custom_handler
)
```

### Publishing Trading Signals

```python
signal = {
    "type": "buy",
    "symbol": "AAPL",
    "price": 150.00,
    "quantity": 100,
    "timestamp": time.time(),
    "strategy": "moving_average_crossover"
}

await streamer.producer.publish_trading_signal(signal)
```

## Testing

### Run Integration Tests

```bash
# Inside the container
python test_kafka_integration.py
```

### Test Individual Components

```python
# Test producer
await test_kafka_producer()

# Test consumer
await test_kafka_consumer()

# Test data feed integration
await test_data_feed_integration()
```

## Monitoring

### Prometheus Metrics

The system exposes Kafka-related metrics:

- `kafka_messages_published_total`: Total messages published
- `kafka_messages_consumed_total`: Total messages consumed
- `kafka_producer_errors_total`: Producer error count
- `kafka_consumer_errors_total`: Consumer error count
- `kafka_connection_status`: Connection status (0/1)

### Health Checks

Kafka health is monitored through:
- Connection status checks
- Message publishing tests
- Consumer group status
- Topic availability

### Grafana Dashboard

The Kafka metrics are visualized in Grafana dashboards:
- Message throughput graphs
- Error rate monitoring
- Connection status indicators
- Topic partition metrics

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if Kafka service is running
   - Verify `KAFKA_BOOTSTRAP_SERVERS` configuration
   - Ensure network connectivity

2. **Topic Not Found**
   - Topics are created automatically on first message
   - Check Kafka broker configuration
   - Verify topic naming conventions

3. **Consumer Lag**
   - Monitor consumer group status
   - Check message processing speed
   - Consider scaling consumers

4. **Serialization Errors**
   - Verify message format
   - Check JSON serialization
   - Validate data types

### Debug Commands

```bash
# Check Kafka topics
docker exec kafka kafka-topics --bootstrap-server localhost:9092 --list

# Check consumer groups
docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --list

# View topic messages
docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic market.stock.prices --from-beginning
```

## Performance Considerations

### Producer Optimization
- Use batch publishing for multiple messages
- Configure appropriate `linger_ms` for batching
- Enable compression (`gzip` recommended)
- Set `acks=all` for durability

### Consumer Optimization
- Process messages asynchronously
- Use appropriate `max_poll_records`
- Handle backpressure properly
- Monitor consumer lag

### Topic Configuration
- Configure appropriate partition count
- Set retention policies based on requirements
- Use appropriate replication factor
- Consider topic compaction for key-based data

## Security

### Authentication
- Configure SASL authentication if required
- Use SSL/TLS for encrypted communication
- Implement proper access controls

### Authorization
- Set up ACLs for topic access
- Restrict producer/consumer permissions
- Monitor access patterns

## Future Enhancements

1. **Schema Registry Integration**
   - Avro schema validation
   - Schema evolution support
   - Backward compatibility

2. **Advanced Routing**
   - Content-based routing
   - Dynamic topic selection
   - Message filtering

3. **Stream Processing**
   - Kafka Streams integration
   - Real-time aggregations
   - Complex event processing

4. **Multi-Cluster Support**
   - Cross-cluster replication
   - Disaster recovery
   - Geographic distribution