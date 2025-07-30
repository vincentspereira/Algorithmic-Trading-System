# Forex and Cryptocurrency Trading Support Documentation

## Overview

The Forex and Cryptocurrency Trading Support module provides comprehensive trading capabilities for foreign exchange (forex) and cryptocurrency markets. It includes exchange connectors, order management, market data integration, and risk management features specifically designed for these asset classes.

## Features

### Supported Markets
- **Forex Trading**: Major, minor, and exotic currency pairs
- **Cryptocurrency Trading**: Spot trading across multiple exchanges
- **Multi-Exchange Support**: Connect to multiple brokers/exchanges simultaneously
- **Unified Interface**: Common API for both forex and crypto trading

### Key Capabilities
- Real-time market data streaming
- Order placement and management
- Account balance monitoring
- Risk management and validation
- Performance tracking and analytics
- Exchange-specific optimizations

## Architecture

### Core Components

#### Currency and Currency Pairs
```python
# Define currencies
usd = Currency("USD", "US Dollar", CurrencyType.FIAT, precision=2)
btc = Currency("BTC", "Bitcoin", CurrencyType.CRYPTOCURRENCY, precision=8)

# Create currency pairs
eur_usd = CurrencyPair(
    base_currency=eur,
    quote_currency=usd,
    min_trade_size=1000,
    tick_size=0.00001
)
```

#### Trading Orders
```python
# Create trading order
order = TradingOrder(
    order_id="order_001",
    symbol="EUR/USD",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=10000,
    price=1.1000
)
```

#### Exchange Connectors
- **ForexConnector**: OANDA integration for forex trading
- **CryptoConnector**: Binance integration for cryptocurrency trading
- **Extensible Design**: Easy to add new exchange connectors

## Usage Examples

### Basic Setup

```python
from nautilus_trader_engine.assets.forex_crypto_support import (
    ForexCryptoTradingEngine, ForexConnector, CryptoConnector,
    TradingOrder, OrderSide, OrderType
)

# Initialize trading engine
engine = ForexCryptoTradingEngine()

# Add exchange connectors
forex_connector = ForexConnector("OANDA")
forex_connector.api_key = "your_oanda_api_key"
forex_connector.api_secret = "your_oanda_api_secret"

crypto_connector = CryptoConnector("Binance")
crypto_connector.api_key = "your_binance_api_key"
crypto_connector.api_secret = "your_binance_api_secret"

engine.add_connector(forex_connector)
engine.add_connector(crypto_connector)
```

### Connection Management

```python
# Connect to all exchanges
connections = await engine.connect_all()
print("Connection status:", connections)

# Check supported pairs
pairs = engine.get_supported_pairs()
print(f"Supported pairs: {len(pairs)}")

# Get account balances
balances = await engine.get_all_balances()
print("Account balances:", balances)
```

### Order Management

```python
# Place forex order
forex_order = TradingOrder(
    order_id="forex_001",
    symbol="EUR/USD",
    side=OrderSide.BUY,
    order_type=OrderType.LIMIT,
    quantity=10000,
    price=1.1000
)

result = await engine.place_order("OANDA", forex_order)
print(f"Order status: {result.status}")

# Place crypto order
crypto_order = TradingOrder(
    order_id="crypto_001",
    symbol="BTC/USDT",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    quantity=0.1
)

result = await engine.place_order("Binance", crypto_order)
print(f"Order status: {result.status}")
```

### Market Data

```python
# Get market data from all exchanges
market_data = await engine.get_market_data_all("BTC/USDT")
for exchange, data in market_data.items():
    print(f"{exchange}: {data['price']}")

# Get specific pair information
pair_info = engine.get_pair_info("EUR/USD")
print(f"Min trade size: {pair_info.min_trade_size}")
print(f"Tick size: {pair_info.tick_size}")
```

### Order Monitoring

```python
# Get active orders
active_orders = engine.get_active_orders()
print(f"Active orders: {len(active_orders)}")

# Update order statuses
await engine.update_order_statuses()

# Cancel order
success = await engine.cancel_order("OANDA", "order_id")
print(f"Order cancelled: {success}")
```

## Exchange Connectors

### Forex Connector (OANDA)

The ForexConnector provides integration with OANDA's REST API for forex trading.

#### Features
- Account management and balance retrieval
- Order placement (market, limit, stop orders)
- Real-time market data
- Position management
- Historical data access

#### Configuration
```python
forex_connector = ForexConnector("OANDA")
forex_connector.api_key = "your_api_key"
forex_connector.account_id = "your_account_id"
forex_connector.sandbox_mode = True  # Use practice account
```

#### Supported Order Types
- Market orders
- Limit orders
- Stop orders
- Stop-limit orders

### Crypto Connector (Binance)

The CryptoConnector provides integration with Binance's REST API for cryptocurrency trading.

#### Features
- Spot trading
- Account balance management
- Order book data
- 24hr ticker statistics
- Trade history

#### Configuration
```python
crypto_connector = CryptoConnector("Binance")
crypto_connector.api_key = "your_api_key"
crypto_connector.api_secret = "your_api_secret"
crypto_connector.sandbox_mode = True  # Use testnet
```

#### Security
- HMAC-SHA256 signature authentication
- Timestamp validation
- Rate limiting compliance

## Risk Management

### Order Validation

The system includes comprehensive order validation:

```python
# Validation checks
- Supported currency pairs
- Minimum trade sizes
- Maximum position limits
- Daily loss limits
- Account balance sufficiency
```

### Risk Parameters

```python
# Configure risk limits
engine.max_position_size = 1000000  # Maximum position size
engine.max_daily_loss = 10000       # Maximum daily loss limit
```

### Position Monitoring

```python
# Monitor positions and P&L
summary = engine.get_performance_summary()
print(f"Daily P&L: {summary['daily_pnl']}")
print(f"Active positions: {summary['active_orders_count']}")
```

## Data Models

### Currency

```python
@dataclass
class Currency:
    code: str                    # Currency code (USD, BTC, etc.)
    name: str                    # Full name
    currency_type: CurrencyType  # FIAT, CRYPTOCURRENCY, COMMODITY
    precision: int               # Decimal precision
    min_amount: float           # Minimum tradeable amount
    
    # Type-specific fields
    country: str                # For fiat currencies
    blockchain: str             # For cryptocurrencies
    total_supply: float         # For cryptocurrencies
```

### Currency Pair

```python
@dataclass
class CurrencyPair:
    base_currency: Currency     # Base currency
    quote_currency: Currency    # Quote currency
    symbol: str                 # Trading symbol
    min_trade_size: float       # Minimum trade size
    tick_size: float           # Minimum price increment
    
    # Market data
    current_price: float
    bid_price: float
    ask_price: float
    volume_24h: float
```

### Trading Order

```python
@dataclass
class TradingOrder:
    order_id: str              # Unique order identifier
    symbol: str                # Currency pair symbol
    side: OrderSide            # BUY or SELL
    order_type: OrderType      # MARKET, LIMIT, STOP, etc.
    quantity: float            # Order quantity
    price: float               # Order price (for limit orders)
    
    # Status tracking
    status: OrderStatus        # Order status
    filled_quantity: float     # Filled amount
    average_price: float       # Average fill price
    fees: float               # Trading fees
```

## Error Handling

### Connection Errors
```python
try:
    result = await connector.connect()
    if not result:
        logger.error("Failed to connect to exchange")
except Exception as e:
    logger.error(f"Connection error: {e}")
```

### Order Errors
```python
# Order validation
if not engine._validate_order(order):
    order.status = OrderStatus.REJECTED
    return order

# Exchange errors
try:
    result = await connector.place_order(order)
except ExchangeError as e:
    logger.error(f"Exchange error: {e}")
    order.status = OrderStatus.REJECTED
```

### Rate Limiting
```python
# Automatic rate limiting
@rate_limit(calls=10, period=60)  # 10 calls per minute
async def api_call():
    # API call implementation
    pass
```

## Performance Optimization

### Connection Pooling
- Reuse HTTP connections
- Connection keep-alive
- Automatic reconnection

### Batch Operations
```python
# Batch order updates
await engine.update_order_statuses()

# Batch market data retrieval
market_data = await engine.get_market_data_all(symbol)
```

### Caching
- Market data caching
- Exchange info caching
- Rate limit tracking

## Testing

### Unit Tests
```bash
# Run all tests
python -m pytest tests/test_forex_crypto_support.py -v

# Run specific test categories
python -m pytest tests/test_forex_crypto_support.py::TestCurrency -v
python -m pytest tests/test_forex_crypto_support.py::TestTradingOrder -v
```

### Mock Testing
```python
# Mock exchange responses for testing
@patch('requests.Session')
def test_order_placement(mock_session):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'orderId': 12345}
    mock_session.return_value.post.return_value = mock_response
    
    # Test order placement
    result = await connector.place_order(order)
    assert result.status == OrderStatus.OPEN
```

## Security Best Practices

### API Key Management
- Store API keys securely (environment variables)
- Use separate keys for production and testing
- Implement key rotation policies

### Network Security
- Use HTTPS for all API calls
- Validate SSL certificates
- Implement request signing

### Data Protection
- Encrypt sensitive data at rest
- Secure logging (no API keys in logs)
- Audit trail for all trading activities

## Monitoring and Observability

### Logging
```python
# Structured logging
logger.info("Order placed", extra={
    'order_id': order.order_id,
    'symbol': order.symbol,
    'exchange': exchange_name,
    'status': order.status.value
})
```

### Metrics
```python
# Performance metrics
summary = engine.get_performance_summary()
- Daily P&L tracking
- Order success rates
- Latency measurements
- Error rates by exchange
```

### Alerts
- Failed connection alerts
- Order rejection alerts
- Risk limit breach alerts
- Performance degradation alerts

## Integration Examples

### With Portfolio Management
```python
# Get positions for portfolio calculation
positions = {}
for exchange, balances in await engine.get_all_balances().items():
    positions[exchange] = balances

# Calculate portfolio value
total_value = calculate_portfolio_value(positions, current_prices)
```

### With Risk Management
```python
# Pre-trade risk checks
def validate_trade_risk(order, portfolio):
    # Check position limits
    # Check correlation limits
    # Check sector exposure
    return risk_approved

# Post-trade monitoring
await engine.update_order_statuses()
current_risk = calculate_portfolio_risk(positions)
```

### With Analytics
```python
# Performance analytics
history = engine.get_order_history(limit=1000)
analytics = calculate_trading_analytics(history)

print(f"Win rate: {analytics['win_rate']:.2%}")
print(f"Average profit: ${analytics['avg_profit']:.2f}")
print(f"Sharpe ratio: {analytics['sharpe_ratio']:.2f}")
```

## Troubleshooting

### Common Issues

#### Connection Problems
- Check API credentials
- Verify network connectivity
- Check exchange status
- Review rate limits

#### Order Issues
- Validate order parameters
- Check account balance
- Verify market hours
- Review exchange-specific rules

#### Data Issues
- Check symbol formatting
- Verify market data availability
- Review timestamp synchronization

### Debug Mode
```python
# Enable debug logging
logging.getLogger('nautilus_trader_engine.assets.forex_crypto_support').setLevel(logging.DEBUG)

# Test connectivity
result = await connector.connect()
if not result:
    # Check logs for detailed error information
    pass
```

## Future Enhancements

### Planned Features
- WebSocket streaming for real-time data
- Additional exchange connectors (Coinbase, Kraken, etc.)
- Advanced order types (OCO, trailing stops)
- Algorithmic trading strategies
- Portfolio optimization integration

### Extensibility
- Plugin architecture for new exchanges
- Custom order validation rules
- Configurable risk parameters
- Event-driven architecture

## Support

For questions or issues:
- Review the test files for usage examples
- Check the source code documentation
- Submit issues through the project repository
- Consult exchange API documentation for specific requirements