# Trading System API Documentation

Welcome to the Algorithmic Trading System API documentation. This comprehensive API enables developers to build sophisticated trading applications, integrate with market data feeds, manage portfolios, and execute trading strategies programmatically.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (recommended)
- Valid API credentials (API key or username/password)
- Basic understanding of financial markets and trading concepts

### Installation

```bash
# Install required dependencies
pip install requests websocket-client pandas numpy

# Optional: Install our Python SDK (when available)
pip install trading-system-sdk
```

### Authentication

The API supports two authentication methods:

1. **API Key Authentication** (Recommended for production)
2. **JWT Token Authentication** (Username/Password)

```python
import requests

# Method 1: API Key
headers = {
    "X-API-Key": "your-api-key",
    "Content-Type": "application/json"
}

# Method 2: JWT Token
auth_response = requests.post(
    "https://api.trading-system.com/v1/auth/login",
    json={"username": "your_username", "password": "your_password"}
)
token = auth_response.json()["access_token"]
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
```

### Your First API Call

```python
# Get system health status
response = requests.get(
    "https://api.trading-system.com/v1/health",
    headers=headers
)
print(response.json())

# Get a stock quote
response = requests.get(
    "https://api.trading-system.com/v1/market-data/quotes/AAPL",
    headers=headers
)
quote = response.json()
print(f"AAPL: ${quote['last']} (Bid: ${quote['bid']}, Ask: ${quote['ask']})")
```

## 📚 Documentation Structure

### Core Documentation

- **[OpenAPI Specification](./openapi.yml)** - Complete REST API specification
- **[WebSocket API](./websocket-api.yml)** - Real-time data streaming specification
- **[API Examples](./examples.md)** - Comprehensive code examples and use cases

### API Endpoints Overview

| Category | Endpoint | Description |
|----------|----------|-------------|
| **System** | `/health` | System health and status |
| **Authentication** | `/auth/*` | Login, logout, token management |
| **Market Data** | `/market-data/*` | Real-time quotes, historical data, market info |
| **Trading** | `/orders/*` | Order placement, management, execution |
| **Portfolio** | `/portfolio/*` | Portfolio overview, positions, performance |
| **Risk** | `/risk/*` | Risk metrics, VaR calculations, limits |
| **Strategies** | `/strategies/*` | Strategy development, backtesting |

## 🔑 Key Features

### Market Data
- **Real-time Quotes**: Live bid/ask prices and market data
- **Historical Data**: OHLCV data with multiple timeframes
- **Multi-Asset Support**: Stocks, ETFs, Options, Futures, Forex, Crypto
- **Market Scanner**: Real-time filtering across large symbol universes

### Trading Operations
- **Order Types**: Market, Limit, Stop, Stop-Limit, Trailing Stop
- **Advanced Orders**: VWAP, TWAP, Iceberg, Hidden
- **Multi-Broker Support**: Starting with Interactive Brokers
- **Paper Trading**: Risk-free testing environment

### Portfolio Management
- **Real-time Positions**: Live portfolio tracking
- **Performance Analytics**: Returns, Sharpe ratio, drawdown analysis
- **Asset Allocation**: Portfolio optimization and rebalancing
- **Multi-Currency Support**: Global trading capabilities

### Risk Management
- **Real-time Monitoring**: Live risk metrics and alerts
- **Value at Risk (VaR)**: Statistical risk measurements
- **Stress Testing**: Portfolio stress analysis
- **Compliance**: Automated compliance checking

### Strategy Development
- **Backtesting Engine**: Historical strategy validation
- **Live Trading**: Automated strategy execution
- **Performance Attribution**: Detailed strategy analysis
- **AI Integration**: Machine learning enhanced strategies

## 🌐 Base URLs

| Environment | Base URL |
|-------------|----------|
| **Production** | `https://api.trading-system.com/v1` |
| **Staging** | `https://staging-api.trading-system.com/v1` |
| **Development** | `https://dev-api.trading-system.com/v1` |

## 📊 Rate Limits

| Endpoint Category | Rate Limit | Time Window |
|-------------------|------------|-------------|
| **General** | 1,000 requests | 1 minute |
| **Market Data** | 10,000 requests | 1 minute |
| **Trading** | 500 requests | 1 minute |
| **WebSocket** | 100 connections | Per account |

### Rate Limit Headers

All API responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
Retry-After: 60
```

## 🔒 Security

### Authentication Security
- **API Keys**: Secure, revocable access tokens
- **JWT Tokens**: Short-lived, automatically refreshed
- **HTTPS Only**: All communications encrypted
- **IP Whitelisting**: Optional IP-based access control

### Data Protection
- **Encryption**: AES-256 encryption for sensitive data
- **Audit Logging**: Complete API access logging
- **Rate Limiting**: Protection against abuse
- **Input Validation**: Comprehensive request validation

## 📡 WebSocket API

### Connection

```javascript
const ws = new WebSocket('wss://api.trading-system.com/v1/ws');

// Authenticate
ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your-jwt-token'
    }));
};

// Handle messages
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

### Available Channels

- **market_data**: Real-time quotes and market updates
- **orders**: Order status and execution updates
- **portfolio**: Portfolio value and position changes
- **risk**: Risk metric updates and alerts
- **system**: System notifications and maintenance alerts

## 🛠️ SDKs and Libraries

### Official SDKs

- **Python SDK**: `pip install trading-system-sdk`
- **JavaScript SDK**: `npm install trading-system-js`
- **Go SDK**: `go get github.com/trading-system/go-sdk`

### Community Libraries

- **R Package**: Available on CRAN
- **Java Client**: Maven Central
- **C# Library**: NuGet Package

## 📈 Common Use Cases

### Algorithmic Trading
```python
# Example: Simple momentum strategy
def momentum_strategy(symbol, lookback_days=20):
    # Get historical data
    data = api.get_historical_data(symbol, days=lookback_days)
    
    # Calculate momentum
    returns = calculate_returns(data)
    momentum = returns.rolling(10).mean()
    
    # Generate signals
    if momentum[-1] > 0.02:  # 2% momentum threshold
        api.buy_market(symbol, 100)
    elif momentum[-1] < -0.02:
        api.sell_market(symbol, 100)
```

### Portfolio Rebalancing
```python
# Example: Monthly rebalancing
def rebalance_portfolio(target_weights):
    portfolio = api.get_portfolio()
    positions = api.get_positions()
    
    for symbol, target_weight in target_weights.items():
        current_weight = get_current_weight(positions, symbol)
        
        if abs(current_weight - target_weight) > 0.05:  # 5% threshold
            trade_amount = calculate_trade_amount(portfolio, target_weight, current_weight)
            
            if trade_amount > 0:
                api.buy_market(symbol, trade_amount)
            else:
                api.sell_market(symbol, abs(trade_amount))
```

### Risk Monitoring
```python
# Example: Real-time risk monitoring
def monitor_portfolio_risk():
    risk_metrics = api.get_risk_metrics()
    
    # Check VaR limits
    if risk_metrics['value_at_risk'] > MAX_VAR:
        send_alert("VaR limit exceeded")
        
    # Check leverage
    if risk_metrics['leverage'] > MAX_LEVERAGE:
        reduce_positions()
        
    # Check concentration risk
    positions = api.get_positions()
    for position in positions:
        if position['weight'] > MAX_POSITION_SIZE:
            trim_position(position['symbol'])
```

## 🔧 Error Handling

### HTTP Status Codes

| Code | Description | Action |
|------|-------------|--------|
| **200** | Success | Continue |
| **201** | Created | Resource created successfully |
| **400** | Bad Request | Check request parameters |
| **401** | Unauthorized | Check authentication |
| **403** | Forbidden | Check permissions |
| **404** | Not Found | Check resource exists |
| **429** | Rate Limited | Wait and retry |
| **500** | Server Error | Retry with backoff |

### Error Response Format

```json
{
    "error": {
        "code": "INVALID_SYMBOL",
        "message": "Symbol 'INVALID' not found",
        "details": {
            "symbol": "INVALID",
            "valid_symbols": ["AAPL", "GOOGL", "MSFT"]
        }
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "req_123456789"
}
```

### Retry Strategy

```python
import time
import random

def exponential_backoff_retry(func, max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            return func()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise e
            
            # Exponential backoff with jitter
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

## 📞 Support

### Getting Help

- **Documentation**: [https://docs.trading-system.com](https://docs.trading-system.com)
- **API Status**: [https://status.trading-system.com](https://status.trading-system.com)
- **Developer Forum**: [https://forum.trading-system.com](https://forum.trading-system.com)
- **Email Support**: [api-support@trading-system.com](mailto:api-support@trading-system.com)

### Reporting Issues

When reporting API issues, please include:

1. **Request ID** (from response headers)
2. **Timestamp** of the issue
3. **HTTP method and endpoint**
4. **Request parameters** (sanitized)
5. **Expected vs actual behavior**
6. **Error messages** (if any)

### Feature Requests

We welcome feature requests! Please submit them through:

- **GitHub Issues**: [https://github.com/trading-system/api-feedback](https://github.com/trading-system/api-feedback)
- **Developer Forum**: Feature request category
- **Email**: [feature-requests@trading-system.com](mailto:feature-requests@trading-system.com)

## 🔄 API Versioning

### Current Version: v1

- **Stable**: Full backward compatibility
- **Deprecation Policy**: 12 months notice for breaking changes
- **Version Header**: `API-Version: v1`

### Upcoming: v2 (Beta)

- **Enhanced Performance**: Improved response times
- **New Features**: Advanced order types, enhanced analytics
- **GraphQL Support**: Flexible query interface

## 📋 Changelog

### v1.3.0 (Latest)
- Added cryptocurrency trading support
- Enhanced WebSocket performance
- New risk management endpoints
- Improved error messages

### v1.2.0
- Added options trading support
- Portfolio optimization endpoints
- Enhanced market scanner
- Bug fixes and performance improvements

### v1.1.0
- Added futures trading support
- Real-time risk monitoring
- WebSocket API improvements
- Additional market data sources

### v1.0.0
- Initial release
- Core trading functionality
- Market data integration
- Portfolio management
- Basic risk controls

---

## 🚀 Ready to Start Trading?

1. **[Get API Credentials](https://app.trading-system.com/api-keys)** - Generate your API key
2. **[Read the Examples](./examples.md)** - Comprehensive code examples
3. **[Join the Community](https://forum.trading-system.com)** - Connect with other developers
4. **[Start Building](https://docs.trading-system.com/quickstart)** - Build your first trading application

---

*This documentation is continuously updated. Last updated: January 2024*