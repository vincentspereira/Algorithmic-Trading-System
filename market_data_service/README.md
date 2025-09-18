# Market Data Service

A comprehensive, enterprise-grade market data service with multi-source feeds, automatic fallback mechanisms, and real-time streaming capabilities. This service is designed to provide uninterrupted market data access across multiple asset classes with high availability and fault tolerance.

## Features

### 🔄 Multi-Source Data Feeds
- **Primary Provider**: Yahoo Finance (free, reliable)
- **Fallback Chain**: Alpha Vantage → Finnhub → Polygon → Twelve Data
- **Asset-Class Specific**: Different fallback chains per asset class
- **Automatic Switching**: Seamless provider switching on failure

### 📊 Supported Asset Classes
- **Stocks & ETFs**: Global equities and exchange-traded funds
- **Forex**: Major and minor currency pairs
- **Cryptocurrency**: Bitcoin, Ethereum, and major altcoins
- **Futures**: Stock index and commodity futures
- **Options**: Stock and index options (where supported)

### ⚡ Real-Time Capabilities
- **Live Data Streaming**: Real-time price updates via Kafka
- **WebSocket Support**: Low-latency data delivery
- **Subscription Management**: Subscribe/unsubscribe to symbols
- **Rate Limiting**: Intelligent request throttling

### 🛡️ Reliability Features
- **Circuit Breaker**: Automatic provider isolation on failures
- **Health Monitoring**: Continuous provider health checks
- **Caching**: Intelligent data caching for performance
- **Retry Logic**: Exponential backoff for failed requests

### 📈 Performance Monitoring
- **Metrics Collection**: Request counts, latencies, success rates
- **Provider Analytics**: Per-provider performance tracking
- **Health Dashboard**: Real-time system health status
- **Alerting**: Configurable alerts for system issues

## Quick Start

### Installation

```bash
# Install required dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Basic Usage

```python
import asyncio
from market_data_service import create_data_feed_manager, AssetClass, DataType

async def main():
    # Create and start data feed manager
    manager = create_data_feed_manager()
    await manager.start()
    
    try:
        # Get real-time quote
        data = await manager.get_real_time_data(
            symbol="AAPL",
            asset_class=AssetClass.STOCKS,
            data_type=DataType.QUOTE
        )
        
        print(f"AAPL Price: ${data.data['current_price']}")
        print(f"Provider: {data.provider}")
        
    finally:
        await manager.stop()

asyncio.run(main())
```

### Configuration

```python
from market_data_service.config import MarketDataConfig

# Load configuration from environment
config = MarketDataConfig.from_env()

# Or create custom configuration
config = MarketDataConfig(
    primary_provider="yahoo_finance",
    fallback_enabled=True,
    kafka_streaming_enabled=True,
    cache_ttl=300,  # 5 minutes
    max_retries=3
)
```

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Market Data Service                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Data Feed      │  │   Provider      │  │   Kafka     │ │
│  │   Manager       │  │   Manager       │  │  Streaming  │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Circuit Breaker │  │     Cache       │  │  Health     │ │
│  │    Manager      │  │    Manager      │  │  Monitor    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     Data Providers                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────┐ │
│  │   Yahoo     │ │    Alpha    │ │   Finnhub   │ │  ...  │ │
│  │  Finance    │ │  Vantage    │ │             │ │       │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Request Initiation**: Client requests market data
2. **Provider Selection**: Primary provider attempted first
3. **Fallback Logic**: On failure, next provider in chain is tried
4. **Data Processing**: Raw data normalized to common format
5. **Caching**: Processed data cached for performance
6. **Streaming**: Real-time data streamed via Kafka
7. **Monitoring**: All operations logged and monitored

## API Reference

### DataFeedManager

Main interface for market data operations.

#### Methods

##### `get_real_time_data(symbol, asset_class, data_type)`
Retrieve real-time market data for a symbol.

**Parameters:**
- `symbol` (str): Trading symbol (e.g., "AAPL")
- `asset_class` (AssetClass): Asset class enum
- `data_type` (DataType): Type of data requested

**Returns:** `MarketDataPoint` object

##### `get_historical_data(symbol, asset_class, start_date, end_date, interval)`
Retrieve historical market data.

**Parameters:**
- `symbol` (str): Trading symbol
- `asset_class` (AssetClass): Asset class enum
- `start_date` (datetime): Start date for data
- `end_date` (datetime): End date for data
- `interval` (str): Data interval ("1m", "5m", "1h", "1D")

**Returns:** List of `MarketDataPoint` objects

##### `subscribe_real_time(symbol, asset_class, callback)`
Subscribe to real-time data streaming.

**Parameters:**
- `symbol` (str): Trading symbol
- `asset_class` (AssetClass): Asset class enum
- `callback` (callable): Function to handle data updates

##### `get_provider_health_status()`
Get health status of all providers.

**Returns:** Dictionary with provider health information

### MarketDataAPI

FastAPI-based REST API for market data access.

#### Endpoints

##### `GET /api/v1/quote/{symbol}`
Get real-time quote for a symbol.

**Parameters:**
- `symbol`: Trading symbol
- `asset_class`: Asset class (query parameter)

**Response:**
```json
{
  "symbol": "AAPL",
  "current_price": 150.25,
  "change": 2.15,
  "change_percent": 1.45,
  "volume": 45678900,
  "provider": "yahoo_finance",
  "timestamp": "2024-01-15T15:30:00Z"
}
```

##### `GET /api/v1/historical/{symbol}`
Get historical data for a symbol.

**Parameters:**
- `symbol`: Trading symbol
- `start_date`: Start date (query parameter)
- `end_date`: End date (query parameter)
- `interval`: Data interval (query parameter)
- `asset_class`: Asset class (query parameter)

##### `GET /api/v1/health`
Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "providers": {
    "yahoo_finance": {"status": "healthy", "last_check": "2024-01-15T15:30:00Z"},
    "alpha_vantage": {"status": "healthy", "last_check": "2024-01-15T15:30:00Z"}
  },
  "metrics": {
    "total_requests": 1250,
    "successful_requests": 1200,
    "avg_response_time": 145.5
  }
}
```

## Configuration

### Environment Variables

```bash
# Provider API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FINNHUB_API_KEY=your_finnhub_key
POLYGON_API_KEY=your_polygon_key
TWELVE_DATA_API_KEY=your_twelve_data_key

# Service Configuration
PRIMARY_PROVIDER=yahoo_finance
FALLBACK_ENABLED=true
CACHE_TTL=300
MAX_RETRIES=3

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC_PREFIX=market_data
KAFKA_PRODUCER_ENABLED=true

# Rate Limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST_SIZE=10

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Provider Configuration

Each provider can be configured with specific settings:

```python
from market_data_service.provider_configs import PROVIDER_CONFIGS

# Yahoo Finance configuration
yahoo_config = PROVIDER_CONFIGS['yahoo_finance']
print(f"Rate limit: {yahoo_config.limits.requests_per_minute} req/min")
print(f"Supported assets: {yahoo_config.features.supported_asset_classes}")
```

## Fallback Chains

### Asset-Class Specific Chains

**Stocks & ETFs:**
1. Yahoo Finance (Primary)
2. Alpha Vantage
3. Finnhub
4. Polygon
5. Twelve Data

**Forex:**
1. Yahoo Finance (Primary)
2. Alpha Vantage
3. Twelve Data
4. Oanda (if configured)

**Cryptocurrency:**
1. Yahoo Finance (Primary)
2. Alpha Vantage
3. Finnhub
4. CoinGecko (if configured)

### Fallback Logic

1. **Primary Attempt**: Try primary provider first
2. **Health Check**: Verify provider is healthy
3. **Circuit Breaker**: Skip if circuit is open
4. **Retry Logic**: Exponential backoff on failures
5. **Next Provider**: Move to next in chain
6. **Cache Fallback**: Use cached data if all providers fail

## Monitoring and Alerting

### Metrics Collected

- **Request Metrics**: Total, successful, failed requests
- **Latency Metrics**: Average, P95, P99 response times
- **Provider Metrics**: Per-provider success rates
- **Cache Metrics**: Hit rates, eviction rates
- **Circuit Breaker**: Open/closed states, failure counts

### Health Checks

- **Provider Health**: Regular health checks for all providers
- **System Health**: Overall system status
- **Dependency Health**: Kafka, cache, database connectivity

### Alerting Rules

- **High Error Rate**: >5% error rate for 5 minutes
- **Provider Down**: Provider unavailable for >2 minutes
- **High Latency**: P95 latency >1000ms for 5 minutes
- **Circuit Breaker Open**: Any circuit breaker open

## Examples

See the `examples/` directory for comprehensive usage examples:

- `market_data_example.py`: Complete demonstration of all features
- `streaming_example.py`: Real-time data streaming
- `fallback_example.py`: Fallback mechanism testing
- `performance_example.py`: Performance monitoring

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/test_data_feed_manager.py

# Run with coverage
pytest --cov=market_data_service tests/
```

### Integration Tests

```bash
# Run integration tests (requires API keys)
pytest tests/integration/

# Test specific provider
pytest tests/integration/test_yahoo_finance.py
```

### Load Testing

```bash
# Run load tests
python tests/load/load_test.py

# Test with specific parameters
python tests/load/load_test.py --concurrent-users 100 --duration 300
```

## Deployment

### Docker

```bash
# Build image
docker build -t market-data-service .

# Run container
docker run -p 8000:8000 --env-file .env market-data-service
```

### Kubernetes

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -l app=market-data-service
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f market-data-service
```

## Troubleshooting

### Common Issues

#### Provider API Key Issues
```
Error: Invalid API key for Alpha Vantage
Solution: Check ALPHA_VANTAGE_API_KEY environment variable
```

#### Rate Limit Exceeded
```
Error: Rate limit exceeded for provider
Solution: Reduce request frequency or upgrade API plan
```

#### Kafka Connection Issues
```
Error: Failed to connect to Kafka
Solution: Check KAFKA_BOOTSTRAP_SERVERS configuration
```

### Debug Mode

```python
# Enable debug logging
import logging
logging.getLogger('market_data_service').setLevel(logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
```

### Health Check Endpoint

```bash
# Check service health
curl http://localhost:8000/api/v1/health

# Check specific provider
curl http://localhost:8000/api/v1/providers/yahoo_finance/health
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd market-data-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review the examples
- Join our community discussions

---

**Note**: This service is designed for paper trading and development purposes. For production live trading, ensure you have appropriate API subscriptions and comply with all relevant regulations.