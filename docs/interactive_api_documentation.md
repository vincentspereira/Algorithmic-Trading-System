# Interactive API Documentation - Algorithmic Trading System

## Overview

This interactive API documentation provides comprehensive coverage of the Algorithmic Trading System API with live examples, code snippets in multiple languages, and try-it-now functionality.

## Features

- **OpenAPI 3.0 Specification**: Complete API schema with validation
- **Interactive Testing**: Try endpoints directly from the documentation
- **Multi-language Examples**: Code samples in Python, JavaScript, Java, C#, and Go
- **Real-time Validation**: Request/response validation with immediate feedback
- **Authentication Playground**: Test authentication flows interactively
- **Rate Limiting Information**: Live rate limit status and guidelines

## Quick Start

## Authentication

All API endpoints require authentication. Get started by obtaining an access token:

```bash
curl -X POST "https://api.trading-system.com/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

## Making Your First API Call

Use the access token to make authenticated requests:

```bash
curl -X GET "https://api.trading-system.com/strategies" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## API Endpoints

### Authentication Endpoints

#### POST /auth/login
**Description**: Authenticate user and obtain access token

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "remember_me": false
}
```

**Code Examples:**

**Python:**
```python
import requests

def login(username, password):
    url = "https://api.trading-system.com/auth/login"
    payload = {
        "username": username,
        "password": password
    }
    response = requests.post(url, json=payload)
    return response.json()

# Usage
token_data = login("your_username", "your_password")
access_token = token_data["access_token"]
```

**JavaScript:**
```javascript
async function login(username, password) {
    const response = await fetch('https://api.trading-system.com/auth/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password
        })
    });
    return await response.json();
}

// Usage
const tokenData = await login('your_username', 'your_password');
const accessToken = tokenData.access_token;
```

**Java:**
```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;

public class TradingAPIClient {
    private static final String BASE_URL = "https://api.trading-system.com";
    
    public String login(String username, String password) throws Exception {
        HttpClient client = HttpClient.newHttpClient();
        String json = String.format("{\"username\":\"%s\",\"password\":\"%s\"}", 
                                   username, password);
        
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(BASE_URL + "/auth/login"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(json))
            .build();
            
        HttpResponse<String> response = client.send(request, 
                                                   HttpResponse.BodyHandlers.ofString());
        return response.body();
    }
}
```

**C#:**
```csharp
using System;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;

public class TradingApiClient
{
    private readonly HttpClient _httpClient;
    private const string BaseUrl = "https://api.trading-system.com";

    public TradingApiClient()
    {
        _httpClient = new HttpClient();
    }

    public async Task<string> LoginAsync(string username, string password)
    {
        var loginData = new { username, password };
        var json = JsonConvert.SerializeObject(loginData);
        var content = new StringContent(json, Encoding.UTF8, "application/json");

        var response = await _httpClient.PostAsync($"{BaseUrl}/auth/login", content);
        return await response.Content.ReadAsStringAsync();
    }
}
```

**Go:**
```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type LoginRequest struct {
    Username string `json:"username"`
    Password string `json:"password"`
}

type LoginResponse struct {
    AccessToken  string `json:"access_token"`
    TokenType    string `json:"token_type"`
    ExpiresIn    int    `json:"expires_in"`
    RefreshToken string `json:"refresh_token"`
}

func login(username, password string) (*LoginResponse, error) {
    loginReq := LoginRequest{
        Username: username,
        Password: password,
    }

    jsonData, err := json.Marshal(loginReq)
    if err != nil {
        return nil, err
    }

    resp, err := http.Post("https://api.trading-system.com/auth/login", 
                          "application/json", bytes.NewBuffer(jsonData))
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var loginResp LoginResponse
    err = json.NewDecoder(resp.Body).Decode(&loginResp)
    return &loginResp, err
}
```

### Strategy Management Endpoints

#### GET /strategies
**Description**: Retrieve all trading strategies for the authenticated user

**Headers:**
- `Authorization: Bearer {access_token}`

**Query Parameters:**
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of strategies per page (default: 20)
- `status` (optional): Filter by strategy status (active, inactive, draft)
- `asset_class` (optional): Filter by asset class (stocks, forex, crypto, commodities)

**Response:**
```json
{
  "strategies": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string",
      "status": "active",
      "asset_class": "stocks",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "performance": {
        "total_return": 15.5,
        "sharpe_ratio": 1.2,
        "max_drawdown": -5.3,
        "win_rate": 0.65
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100,
    "pages": 5
  }
}
```

**Code Examples:**

**Python:**
```python
import requests

def get_strategies(access_token, page=1, limit=20, status=None, asset_class=None):
    url = "https://api.trading-system.com/strategies"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"page": page, "limit": limit}
    
    if status:
        params["status"] = status
    if asset_class:
        params["asset_class"] = asset_class
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# Usage
strategies = get_strategies(access_token, status="active", asset_class="stocks")
```

**JavaScript:**
```javascript
async function getStrategies(accessToken, options = {}) {
    const params = new URLSearchParams({
        page: options.page || 1,
        limit: options.limit || 20,
        ...(options.status && { status: options.status }),
        ...(options.asset_class && { asset_class: options.asset_class })
    });

    const response = await fetch(`https://api.trading-system.com/strategies?${params}`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    
    return await response.json();
}

// Usage
const strategies = await getStrategies(accessToken, { 
    status: 'active', 
    asset_class: 'stocks' 
});
```

#### POST /strategies
**Description**: Create a new trading strategy

**Request Body:**
```json
{
  "name": "string",
  "description": "string",
  "asset_class": "stocks",
  "strategy_type": "momentum",
  "parameters": {
    "lookback_period": 20,
    "threshold": 0.02,
    "stop_loss": 0.05,
    "take_profit": 0.10
  },
  "risk_management": {
    "max_position_size": 0.05,
    "max_daily_loss": 0.02,
    "max_correlation": 0.7
  }
}
```

**Code Examples:**

**Python:**
```python
def create_strategy(access_token, strategy_data):
    url = "https://api.trading-system.com/strategies"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=strategy_data)
    return response.json()

# Usage
new_strategy = {
    "name": "Momentum Strategy",
    "description": "A momentum-based trading strategy",
    "asset_class": "stocks",
    "strategy_type": "momentum",
    "parameters": {
        "lookback_period": 20,
        "threshold": 0.02
    }
}

result = create_strategy(access_token, new_strategy)
```

### Market Data Endpoints

#### GET /market-data/quotes/{symbol}
**Description**: Get real-time quote for a specific symbol

**Path Parameters:**
- `symbol`: Trading symbol (e.g., AAPL, EURUSD, BTCUSD)

**Query Parameters:**
- `fields` (optional): Comma-separated list of fields to return

**Response:**
```json
{
  "symbol": "AAPL",
  "bid": 150.25,
  "ask": 150.27,
  "last": 150.26,
  "volume": 1000000,
  "timestamp": "2024-01-01T15:30:00Z",
  "change": 2.15,
  "change_percent": 1.45
}
```

**Code Examples:**

**Python:**
```python
def get_quote(access_token, symbol, fields=None):
    url = f"https://api.trading-system.com/market-data/quotes/{symbol}"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {}
    
    if fields:
        params["fields"] = ",".join(fields)
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# Usage
quote = get_quote(access_token, "AAPL", fields=["bid", "ask", "last"])
```

### Backtesting Endpoints

#### POST /backtesting/run
**Description**: Run a backtest for a strategy

**Request Body:**
```json
{
  "strategy_id": "uuid",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "initial_capital": 100000,
  "benchmark": "SPY",
  "parameters": {
    "commission": 0.001,
    "slippage": 0.0005
  }
}
```

**Response:**
```json
{
  "backtest_id": "uuid",
  "status": "running",
  "estimated_completion": "2024-01-01T15:35:00Z"
}
```

### Trading Endpoints

#### GET /orders
**Description:** Retrieve trading orders for the authenticated user

**Headers:**
- `Authorization: Bearer {access_token}`

**Query Parameters:**
- `status` (optional): Filter by order status (pending, filled, cancelled, rejected)
- `symbol` (optional): Filter by trading symbol
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of orders per page (default: 20)

**Response:**
```json
{
  "orders": [
    {
      "id": "uuid",
      "symbol": "AAPL",
      "side": "buy",
      "order_type": "limit",
      "quantity": 100,
      "filled_quantity": 0,
      "price": 150.00,
      "status": "pending",
      "created_at": "2024-01-01T10:00:00Z",
      "updated_at": "2024-01-01T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 50,
    "pages": 3
  }
}
```

**Code Examples:**

**Python:**
```python
def get_orders(access_token, status=None, symbol=None):
    url = "https://api.trading-system.com/orders"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {}
    
    if status:
        params["status"] = status
    if symbol:
        params["symbol"] = symbol
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# Usage
orders = get_orders(access_token, status="pending", symbol="AAPL")
```

**JavaScript:**
```javascript
async function getOrders(accessToken, options = {}) {
    const params = new URLSearchParams({
        ...(options.status && { status: options.status }),
        ...(options.symbol && { symbol: options.symbol }),
        page: options.page || 1,
        limit: options.limit || 20
    });

    const response = await fetch(`https://api.trading-system.com/orders?${params}`, {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    });
    
    return await response.json();
}

// Usage
const orders = await getOrders(accessToken, { status: 'pending' });
```

#### POST /orders
**Description:** Place a new trading order

**Request Body:**
```json
{
  "symbol": "AAPL",
  "side": "buy",
  "order_type": "limit",
  "quantity": 100,
  "price": 150.00,
  "time_in_force": "day",
  "stop_price": null
}
```

**Response:**
```json
{
  "id": "uuid",
  "symbol": "AAPL",
  "side": "buy",
  "order_type": "limit",
  "quantity": 100,
  "filled_quantity": 0,
  "price": 150.00,
  "average_fill_price": null,
  "status": "pending",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

**Code Examples:**

**Python:**
```python
def place_order(access_token, order_data):
    url = "https://api.trading-system.com/orders"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers, json=order_data)
    return response.json()

# Usage
order_data = {
    "symbol": "AAPL",
    "side": "buy",
    "order_type": "limit",
    "quantity": 100,
    "price": 150.00
}

order = place_order(access_token, order_data)
```

**JavaScript:**
```javascript
async function placeOrder(accessToken, orderData) {
    const response = await fetch('https://api.trading-system.com/orders', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(orderData)
    });
    
    return await response.json();
}

// Usage
const orderData = {
    symbol: 'AAPL',
    side: 'buy',
    order_type: 'limit',
    quantity: 100,
    price: 150.00
};

const order = await placeOrder(accessToken, orderData);
```

#### PUT /orders/{order_id}
**Description:** Modify an existing order

**Path Parameters:**
- `order_id`: Order ID to modify

**Request Body:**
```json
{
  "quantity": 150,
  "price": 149.50
}
```

**Response:**
```json
{
  "id": "uuid",
  "symbol": "AAPL",
  "side": "buy",
  "order_type": "limit",
  "quantity": 150,
  "price": 149.50,
  "status": "pending",
  "updated_at": "2024-01-01T10:05:00Z"
}
```

#### DELETE /orders/{order_id}
**Description:** Cancel an existing order

**Path Parameters:**
- `order_id`: Order ID to cancel

**Response:**
```json
{
  "id": "uuid",
  "status": "cancelled",
  "cancelled_at": "2024-01-01T10:10:00Z"
}
```

### Risk Management Endpoints

#### GET /risk/limits
**Description:** Get current risk limits and usage

**Response:**
```json
{
  "daily_loss_limit": 0.02,
  "daily_loss_current": 0.005,
  "position_size_limit": 0.05,
  "max_positions": 10,
  "current_positions": 3,
  "correlation_limit": 0.7,
  "leverage_limit": 2.0,
  "current_leverage": 1.2
}
```

#### POST /risk/limits
**Description:** Update risk management limits

**Request Body:**
```json
{
  "daily_loss_limit": 0.015,
  "position_size_limit": 0.04,
  "max_positions": 8,
  "correlation_limit": 0.6
}
```

### Portfolio Management Endpoints

#### GET /portfolio
**Description:** Get current portfolio status

**Response:**
```json
{
  "total_value": 125000.00,
  "cash": 25000.00,
  "positions_value": 100000.00,
  "daily_pnl": 2500.00,
  "total_pnl": 25000.00,
  "positions": [
    {
      "symbol": "AAPL",
      "quantity": 100,
      "avg_price": 145.00,
      "current_price": 150.00,
      "market_value": 15000.00,
      "unrealized_pnl": 500.00,
      "weight": 0.12
    }
  ]
}
```

#### GET /portfolio/performance
**Description:** Get portfolio performance metrics

**Query Parameters:**
- `period` (optional): Time period (1d, 1w, 1m, 3m, 1y, all)

**Response:**
```json
{
  "period": "1m",
  "total_return": 0.08,
  "annualized_return": 0.12,
  "volatility": 0.15,
  "sharpe_ratio": 1.2,
  "max_drawdown": -0.05,
  "win_rate": 0.65,
  "profit_factor": 1.8,
  "benchmark_return": 0.06,
  "alpha": 0.02,
  "beta": 0.9
}
```

### WebSocket API

#### Real-time Market Data Stream

**Connection URL:** `wss://api.trading-system.com/ws/market-data`

**Authentication:** Send access token in the first message

**Subscribe to Symbols:**
```json
{
  "action": "subscribe",
  "symbols": ["AAPL", "GOOGL", "MSFT"],
  "data_types": ["quotes", "trades", "level2"]
}
```

**Code Examples:**

**Python (using websockets):**
```python
import asyncio
import websockets
import json

async def market_data_stream(access_token, symbols):
    uri = "wss://api.trading-system.com/ws/market-data"
    
    async with websockets.connect(uri) as websocket:
        # Authenticate
        auth_message = {
            "action": "authenticate",
            "token": access_token
        }
        await websocket.send(json.dumps(auth_message))
        
        # Subscribe to symbols
        subscribe_message = {
            "action": "subscribe",
            "symbols": symbols,
            "data_types": ["quotes"]
        }
        await websocket.send(json.dumps(subscribe_message))
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")

# Usage
asyncio.run(market_data_stream(access_token, ["AAPL", "GOOGL"]))
```

**JavaScript:**
```javascript
class MarketDataStream {
    constructor(accessToken) {
        this.accessToken = accessToken;
        this.ws = null;
    }
    
    connect() {
        this.ws = new WebSocket('wss://api.trading-system.com/ws/market-data');
        
        this.ws.onopen = () => {
            // Authenticate
            this.ws.send(JSON.stringify({
                action: 'authenticate',
                token: this.accessToken
            }));
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received:', data);
        };
    }
    
    subscribe(symbols) {
        this.ws.send(JSON.stringify({
            action: 'subscribe',
            symbols: symbols,
            data_types: ['quotes']
        }));
    }
}

// Usage
const stream = new MarketDataStream(accessToken);
stream.connect();
stream.subscribe(['AAPL', 'GOOGL']);
```

## Error Handling

### Standard Error Response Format

All API errors follow a consistent format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": {
      "field": "symbol",
      "reason": "Symbol not found"
    },
    "request_id": "uuid"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Valid authentication token required |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `RATE_LIMIT_EXCEEDED` | 429 | API rate limit exceeded |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `INTERNAL_ERROR` | 500 | Internal server error |

### Error Handling Examples

**Python:**
```python
def handle_api_response(response):
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        raise Exception("Authentication required")
    elif response.status_code == 429:
        retry_after = response.headers.get('Retry-After', 60)
        raise Exception(f"Rate limit exceeded. Retry after {retry_after} seconds")
    else:
        error_data = response.json()
        raise Exception(f"API Error: {error_data['error']['message']}")
```

## Rate Limiting

### Rate Limit Headers

All API responses include rate limiting information:

- `X-RateLimit-Limit`: Maximum requests per time window
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Time when the rate limit resets (Unix timestamp)

### Rate Limits by Endpoint Category

| Category | Limit | Window |
|----------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Market Data | 1000 requests | 1 minute |
| Strategy Management | 100 requests | 1 minute |
| Backtesting | 10 requests | 1 hour |
| WebSocket Connections | 5 connections | Per user |

## SDK Libraries

### Official SDKs

- **Python SDK**: `pip install trading-system-sdk`
- **JavaScript SDK**: `npm install @trading-system/sdk`
- **Java SDK**: Available on Maven Central
- **C# SDK**: Available on NuGet

### Python SDK Example

```python
from trading_system_sdk import TradingSystemClient

# Initialize client
client = TradingSystemClient(
    api_key="your_api_key",
    base_url="https://api.trading-system.com"
)

# Login
client.login("username", "password")

# Get strategies
strategies = client.strategies.list(status="active")

# Create new strategy
new_strategy = client.strategies.create({
    "name": "My Strategy",
    "asset_class": "stocks",
    "strategy_type": "momentum"
})

# Run backtest
backtest = client.backtesting.run(
    strategy_id=new_strategy.id,
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

## Testing Environment

### Sandbox API

Use the sandbox environment for testing:

**Base URL:** `https://sandbox-api.trading-system.com`

### Test Data

The sandbox includes:
- Historical market data for major symbols
- Simulated real-time data feeds
- Test portfolios and strategies
- Mock trading execution

### Getting Sandbox Access

1. Register for a developer account
2. Create a sandbox application
3. Use sandbox credentials for testing

## Support and Resources

### Documentation Links

- [API Reference](https://docs.trading-system.com/api)
- [SDK Documentation](https://docs.trading-system.com/sdks)
- [Tutorials](https://docs.trading-system.com/tutorials)
- [FAQ](https://docs.trading-system.com/faq)

### Community

- [Developer Forum](https://forum.trading-system.com)
- [Discord Community](https://discord.gg/trading-system)
- [GitHub Repository](https://github.com/trading-system/api-examples)

### Support Channels

- **Email**: api-support@trading-system.com
- **Chat**: Available in developer portal
- **Phone**: +1-555-TRADING (business hours)

## Changelog

### Version 2.1.0 (Latest)
- Added multi-asset class support
- Enhanced WebSocket API with level 2 data
- Improved error handling and validation
- New SDK versions with async support

### Version 2.0.0
- Major API redesign with RESTful principles
- Added GraphQL endpoint for complex queries
- Enhanced authentication with OAuth2
- Comprehensive rate limiting implementation

---

*This documentation is automatically updated. Last updated: January 1, 2024*