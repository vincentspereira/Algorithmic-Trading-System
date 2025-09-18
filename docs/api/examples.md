# API Usage Examples

This document provides comprehensive examples for integrating with the Algorithmic Trading System API.

## Table of Contents

1. [Authentication](#authentication)
2. [Market Data](#market-data)
3. [Trading Operations](#trading-operations)
4. [Portfolio Management](#portfolio-management)
5. [Risk Management](#risk-management)
6. [Strategy Development](#strategy-development)
7. [WebSocket Integration](#websocket-integration)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [SDK Examples](#sdk-examples)

## Authentication

### Login and Token Management

```python
import requests
import json
from datetime import datetime, timedelta

class TradingAPIClient:
    def __init__(self, base_url="https://api.trading-system.com/v1"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.token_expires = None
    
    def login(self, username, password):
        """Authenticate and obtain JWT tokens"""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={
                "username": username,
                "password": password
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
            return True
        else:
            raise Exception(f"Login failed: {response.json()['message']}")
    
    def refresh_access_token(self):
        """Refresh expired access token"""
        response = requests.post(
            f"{self.base_url}/auth/refresh",
            json={"refresh_token": self.refresh_token}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
        else:
            raise Exception("Token refresh failed")
    
    def get_headers(self):
        """Get authorization headers for API requests"""
        if not self.access_token:
            raise Exception("Not authenticated")
        
        # Check if token needs refresh
        if datetime.now() >= self.token_expires:
            self.refresh_access_token()
        
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

# Usage
client = TradingAPIClient()
client.login("your_username", "your_password")
```

### API Key Authentication

```python
class APIKeyClient:
    def __init__(self, api_key, base_url="https://api.trading-system.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
    
    def get_headers(self):
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

# Usage
api_client = APIKeyClient("your-api-key")
```

## Market Data

### Real-time Quotes

```python
def get_quote(client, symbol):
    """Get real-time quote for a symbol"""
    response = requests.get(
        f"{client.base_url}/market-data/quotes/{symbol}",
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get quote: {response.json()['message']}")

# Get Apple stock quote
aapl_quote = get_quote(client, "AAPL")
print(f"AAPL: ${aapl_quote['last']} (Bid: ${aapl_quote['bid']}, Ask: ${aapl_quote['ask']})")
```

### Historical Data

```python
from datetime import date, timedelta

def get_historical_data(client, symbol, days=30, interval="1d"):
    """Get historical price data"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    
    response = requests.get(
        f"{client.base_url}/market-data/historical/{symbol}",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "interval": interval
        },
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get historical data: {response.json()['message']}")

# Get 30 days of daily AAPL data
historical_data = get_historical_data(client, "AAPL", days=30)
print(f"Retrieved {len(historical_data['data'])} data points")
```

### Batch Quote Requests

```python
def get_multiple_quotes(client, symbols):
    """Get quotes for multiple symbols efficiently"""
    quotes = {}
    
    # Use concurrent requests for better performance
    import concurrent.futures
    import threading
    
    def fetch_quote(symbol):
        try:
            return symbol, get_quote(client, symbol)
        except Exception as e:
            return symbol, {"error": str(e)}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_quote, symbol) for symbol in symbols]
        
        for future in concurrent.futures.as_completed(futures):
            symbol, quote_data = future.result()
            quotes[symbol] = quote_data
    
    return quotes

# Get quotes for multiple stocks
symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
quotes = get_multiple_quotes(client, symbols)

for symbol, quote in quotes.items():
    if "error" not in quote:
        print(f"{symbol}: ${quote['last']}")
    else:
        print(f"{symbol}: Error - {quote['error']}")
```

## Trading Operations

### Place Market Order

```python
def place_market_order(client, symbol, side, quantity):
    """Place a market order"""
    order_data = {
        "symbol": symbol,
        "side": side,  # "buy" or "sell"
        "quantity": quantity,
        "order_type": "market",
        "time_in_force": "day"
    }
    
    response = requests.post(
        f"{client.base_url}/orders",
        json=order_data,
        headers=client.get_headers()
    )
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Order failed: {response.json()['message']}")

# Buy 100 shares of AAPL at market price
order = place_market_order(client, "AAPL", "buy", 100)
print(f"Order placed: {order['id']} - Status: {order['status']}")
```

### Place Limit Order

```python
def place_limit_order(client, symbol, side, quantity, price):
    """Place a limit order"""
    order_data = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_type": "limit",
        "price": price,
        "time_in_force": "gtc"  # Good Till Cancelled
    }
    
    response = requests.post(
        f"{client.base_url}/orders",
        json=order_data,
        headers=client.get_headers()
    )
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Order failed: {response.json()['message']}")

# Buy 50 shares of GOOGL at $150.00
order = place_limit_order(client, "GOOGL", "buy", 50, 150.00)
print(f"Limit order placed: {order['id']}")
```

### Stop Loss Order

```python
def place_stop_loss_order(client, symbol, quantity, stop_price):
    """Place a stop loss order"""
    order_data = {
        "symbol": symbol,
        "side": "sell",
        "quantity": quantity,
        "order_type": "stop",
        "stop_price": stop_price,
        "time_in_force": "gtc"
    }
    
    response = requests.post(
        f"{client.base_url}/orders",
        json=order_data,
        headers=client.get_headers()
    )
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Stop loss order failed: {response.json()['message']}")

# Set stop loss at $140 for 100 shares
stop_order = place_stop_loss_order(client, "AAPL", 100, 140.00)
print(f"Stop loss order placed: {stop_order['id']}")
```

### Order Management

```python
def get_orders(client, status=None, symbol=None, limit=20):
    """Get list of orders with optional filtering"""
    params = {"limit": limit}
    if status:
        params["status"] = status
    if symbol:
        params["symbol"] = symbol
    
    response = requests.get(
        f"{client.base_url}/orders",
        params=params,
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get orders: {response.json()['message']}")

def cancel_order(client, order_id):
    """Cancel a pending order"""
    response = requests.delete(
        f"{client.base_url}/orders/{order_id}",
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to cancel order: {response.json()['message']}")

# Get all pending orders
pending_orders = get_orders(client, status="pending")
print(f"Found {len(pending_orders)} pending orders")

# Cancel a specific order
if pending_orders:
    cancelled_order = cancel_order(client, pending_orders[0]['id'])
    print(f"Cancelled order: {cancelled_order['id']}")
```

## Portfolio Management

### Portfolio Overview

```python
def get_portfolio(client):
    """Get complete portfolio information"""
    response = requests.get(
        f"{client.base_url}/portfolio",
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get portfolio: {response.json()['message']}")

# Get portfolio summary
portfolio = get_portfolio(client)
print(f"Total Value: ${portfolio['total_value']:,.2f}")
print(f"Cash: ${portfolio['cash']:,.2f}")
print(f"Day P&L: ${portfolio['day_pnl']:,.2f}")
print(f"Total P&L: ${portfolio['total_pnl']:,.2f}")
```

### Positions

```python
def get_positions(client):
    """Get all current positions"""
    response = requests.get(
        f"{client.base_url}/portfolio/positions",
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get positions: {response.json()['message']}")

# Display all positions
positions = get_positions(client)
print("\nCurrent Positions:")
print("-" * 60)
for position in positions:
    print(f"{position['symbol']:<8} {position['quantity']:>8.0f} @ ${position['average_price']:>8.2f} "
          f"Market: ${position['market_value']:>10,.2f} P&L: ${position['unrealized_pnl']:>8,.2f}")
```

### Performance Metrics

```python
def get_performance(client, period="1m"):
    """Get portfolio performance metrics"""
    response = requests.get(
        f"{client.base_url}/portfolio/performance",
        params={"period": period},
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get performance: {response.json()['message']}")

# Get 1-month performance
performance = get_performance(client, "1m")
print(f"\nPerformance Metrics (1 Month):")
print(f"Total Return: {performance['total_return']:.2%}")
print(f"Annualized Return: {performance['annualized_return']:.2%}")
print(f"Volatility: {performance['volatility']:.2%}")
print(f"Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {performance['max_drawdown']:.2%}")
```

## Risk Management

### Risk Metrics

```python
def get_risk_metrics(client):
    """Get current risk metrics"""
    response = requests.get(
        f"{client.base_url}/risk/metrics",
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get risk metrics: {response.json()['message']}")

# Display risk metrics
risk = get_risk_metrics(client)
print(f"\nRisk Metrics:")
print(f"Portfolio Beta: {risk['portfolio_beta']:.2f}")
print(f"Leverage: {risk['leverage']:.2f}x")
print(f"Risk Score: {risk['risk_score']}/100")
print(f"Margin Used: ${risk['margin_used']:,.2f}")
print(f"Margin Available: ${risk['margin_available']:,.2f}")
```

### Value at Risk (VaR)

```python
def get_var(client, confidence_level=0.95, time_horizon=1):
    """Calculate Value at Risk"""
    response = requests.get(
        f"{client.base_url}/risk/var",
        params={
            "confidence_level": confidence_level,
            "time_horizon": time_horizon
        },
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get VaR: {response.json()['message']}")

# Get 1-day VaR at 95% confidence
var_metrics = get_var(client, 0.95, 1)
print(f"\nValue at Risk (95% confidence, 1 day):")
print(f"VaR: ${var_metrics['value_at_risk']:,.2f}")
print(f"Expected Shortfall: ${var_metrics['expected_shortfall']:,.2f}")
```

## Strategy Development

### Create Strategy

```python
def create_strategy(client, name, description, code, parameters=None):
    """Create a new trading strategy"""
    strategy_data = {
        "name": name,
        "description": description,
        "code": code,
        "parameters": parameters or {}
    }
    
    response = requests.post(
        f"{client.base_url}/strategies",
        json=strategy_data,
        headers=client.get_headers()
    )
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Failed to create strategy: {response.json()['message']}")

# Simple moving average crossover strategy
strategy_code = """
from nautilus_trader.model.data.bar import Bar
from nautilus_trader.trading.strategy import Strategy

class MovingAverageCrossover(Strategy):
    def __init__(self, config):
        super().__init__(config)
        self.fast_period = config.get('fast_period', 10)
        self.slow_period = config.get('slow_period', 20)
    
    def on_bar(self, bar: Bar):
        # Strategy logic here
        pass
"""

strategy = create_strategy(
    client,
    "MA Crossover",
    "Simple moving average crossover strategy",
    strategy_code,
    {"fast_period": 10, "slow_period": 20}
)
print(f"Strategy created: {strategy['id']}")
```

### Run Backtest

```python
def run_backtest(client, strategy_id, start_date, end_date, initial_capital=100000):
    """Run a backtest for a strategy"""
    backtest_data = {
        "start_date": start_date,
        "end_date": end_date,
        "initial_capital": initial_capital,
        "benchmark": "SPY"
    }
    
    response = requests.post(
        f"{client.base_url}/strategies/{strategy_id}/backtest",
        json=backtest_data,
        headers=client.get_headers()
    )
    
    if response.status_code == 202:
        return response.json()
    else:
        raise Exception(f"Failed to start backtest: {response.json()['message']}")

def get_backtest_results(client, job_id):
    """Get backtest results"""
    response = requests.get(
        f"{client.base_url}/backtests/{job_id}",
        headers=client.get_headers()
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to get backtest results: {response.json()['message']}")

# Run backtest
backtest_job = run_backtest(
    client, 
    strategy['id'], 
    "2023-01-01", 
    "2023-12-31"
)
print(f"Backtest started: {backtest_job['job_id']}")

# Wait for completion and get results
import time
while True:
    results = get_backtest_results(client, backtest_job['job_id'])
    if results['status'] == 'completed':
        print(f"\nBacktest Results:")
        print(f"Total Return: {results['performance']['total_return']:.2%}")
        print(f"Sharpe Ratio: {results['performance']['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['performance']['max_drawdown']:.2%}")
        break
    elif results['status'] == 'failed':
        print("Backtest failed")
        break
    else:
        print(f"Backtest status: {results['status']}")
        time.sleep(5)
```

## WebSocket Integration

### Real-time Market Data

```python
import websocket
import json
import threading

class TradingWebSocket:
    def __init__(self, token, url="wss://api.trading-system.com/v1/ws"):
        self.token = token
        self.url = url
        self.ws = None
        self.subscriptions = set()
    
    def on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'quote':
                self.on_quote_update(data)
            elif msg_type == 'order_update':
                self.on_order_update(data)
            elif msg_type == 'portfolio_update':
                self.on_portfolio_update(data)
            elif msg_type == 'error':
                print(f"WebSocket error: {data['error']['message']}")
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {message}")
    
    def on_quote_update(self, data):
        """Handle real-time quote updates"""
        quote = data['data']
        print(f"{quote['symbol']}: ${quote['last']} (Bid: ${quote['bid']}, Ask: ${quote['ask']})")
    
    def on_order_update(self, data):
        """Handle order status updates"""
        order = data['data']
        print(f"Order {order['order_id']}: {order['status']} - {order['symbol']} {order['side']} {order['quantity']}")
    
    def on_portfolio_update(self, data):
        """Handle portfolio updates"""
        portfolio = data['data']
        print(f"Portfolio Value: ${portfolio['total_value']:,.2f} (P&L: ${portfolio['day_pnl']:,.2f})")
    
    def on_open(self, ws):
        """Handle WebSocket connection open"""
        print("WebSocket connected")
        # Authenticate
        auth_msg = {
            "type": "auth",
            "token": self.token
        }
        ws.send(json.dumps(auth_msg))
    
    def on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        print("WebSocket disconnected")
    
    def on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
    
    def connect(self):
        """Connect to WebSocket"""
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self.on_message,
            on_open=self.on_open,
            on_close=self.on_close,
            on_error=self.on_error
        )
        
        # Run in separate thread
        wst = threading.Thread(target=self.ws.run_forever)
        wst.daemon = True
        wst.start()
    
    def subscribe_market_data(self, symbols):
        """Subscribe to market data for symbols"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            subscribe_msg = {
                "type": "subscribe",
                "channel": "market_data",
                "symbols": symbols
            }
            self.ws.send(json.dumps(subscribe_msg))
            self.subscriptions.update(symbols)
    
    def subscribe_orders(self):
        """Subscribe to order updates"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            subscribe_msg = {
                "type": "subscribe",
                "channel": "orders"
            }
            self.ws.send(json.dumps(subscribe_msg))
    
    def subscribe_portfolio(self):
        """Subscribe to portfolio updates"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            subscribe_msg = {
                "type": "subscribe",
                "channel": "portfolio"
            }
            self.ws.send(json.dumps(subscribe_msg))

# Usage
ws_client = TradingWebSocket(client.access_token)
ws_client.connect()

# Wait for connection and subscribe
time.sleep(2)
ws_client.subscribe_market_data(["AAPL", "GOOGL", "MSFT"])
ws_client.subscribe_orders()
ws_client.subscribe_portfolio()

# Keep the connection alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Disconnecting...")
```

## Error Handling

### Comprehensive Error Handling

```python
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import time
import logging

class TradingAPIError(Exception):
    """Custom exception for trading API errors"""
    def __init__(self, message, error_code=None, status_code=None):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code

class RobustTradingClient:
    def __init__(self, base_url, max_retries=3, retry_delay=1):
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()
        
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def make_request(self, method, endpoint, **kwargs):
        """Make HTTP request with retry logic and error handling"""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
                
                # Handle different status codes
                if response.status_code == 200 or response.status_code == 201:
                    return response.json()
                elif response.status_code == 401:
                    raise TradingAPIError("Authentication failed", status_code=401)
                elif response.status_code == 403:
                    raise TradingAPIError("Access forbidden", status_code=403)
                elif response.status_code == 404:
                    raise TradingAPIError("Resource not found", status_code=404)
                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    retry_after = int(response.headers.get('Retry-After', 60))
                    self.logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                elif response.status_code >= 500:
                    # Server error - retry
                    if attempt < self.max_retries:
                        self.logger.warning(f"Server error {response.status_code}. Retrying in {self.retry_delay} seconds...")
                        time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                        continue
                    else:
                        raise TradingAPIError(f"Server error: {response.status_code}", status_code=response.status_code)
                else:
                    # Other client errors
                    error_data = response.json() if response.content else {}
                    raise TradingAPIError(
                        error_data.get('message', f'HTTP {response.status_code}'),
                        error_code=error_data.get('code'),
                        status_code=response.status_code
                    )
                    
            except Timeout:
                if attempt < self.max_retries:
                    self.logger.warning(f"Request timeout. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise TradingAPIError("Request timeout after retries")
                    
            except ConnectionError:
                if attempt < self.max_retries:
                    self.logger.warning(f"Connection error. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    raise TradingAPIError("Connection error after retries")
                    
            except RequestException as e:
                raise TradingAPIError(f"Request failed: {str(e)}")
        
        raise TradingAPIError("Max retries exceeded")
    
    def place_order_with_validation(self, order_data):
        """Place order with comprehensive validation and error handling"""
        try:
            # Validate order data
            required_fields = ['symbol', 'side', 'quantity', 'order_type']
            for field in required_fields:
                if field not in order_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate quantity
            if order_data['quantity'] <= 0:
                raise ValueError("Quantity must be positive")
            
            # Validate price for limit orders
            if order_data['order_type'] == 'limit' and 'price' not in order_data:
                raise ValueError("Price required for limit orders")
            
            # Place the order
            result = self.make_request('POST', '/orders', json=order_data)
            self.logger.info(f"Order placed successfully: {result['id']}")
            return result
            
        except ValueError as e:
            self.logger.error(f"Order validation failed: {str(e)}")
            raise
        except TradingAPIError as e:
            self.logger.error(f"Order placement failed: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error placing order: {str(e)}")
            raise TradingAPIError(f"Unexpected error: {str(e)}")

# Usage with error handling
try:
    robust_client = RobustTradingClient("https://api.trading-system.com/v1")
    
    order_data = {
        "symbol": "AAPL",
        "side": "buy",
        "quantity": 100,
        "order_type": "market"
    }
    
    order = robust_client.place_order_with_validation(order_data)
    print(f"Order placed: {order['id']}")
    
except TradingAPIError as e:
    print(f"Trading API Error: {e} (Status: {e.status_code}, Code: {e.error_code})")
except ValueError as e:
    print(f"Validation Error: {e}")
except Exception as e:
    print(f"Unexpected Error: {e}")
```

## Rate Limiting

### Rate Limit Handling

```python
import time
from collections import deque
from threading import Lock

class RateLimiter:
    """Token bucket rate limiter"""
    def __init__(self, max_requests, time_window):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()
    
    def acquire(self):
        """Acquire permission to make a request"""
        with self.lock:
            now = time.time()
            
            # Remove old requests outside the time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # Check if we can make a request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            else:
                # Calculate wait time
                oldest_request = self.requests[0]
                wait_time = self.time_window - (now - oldest_request)
                return wait_time

class RateLimitedClient:
    def __init__(self, base_url):
        self.base_url = base_url
        
        # Different rate limiters for different endpoint types
        self.rate_limiters = {
            'general': RateLimiter(1000, 60),      # 1000 requests per minute
            'market_data': RateLimiter(10000, 60), # 10000 requests per minute
            'trading': RateLimiter(500, 60)        # 500 requests per minute
        }
    
    def make_rate_limited_request(self, endpoint_type, method, endpoint, **kwargs):
        """Make request with rate limiting"""
        rate_limiter = self.rate_limiters.get(endpoint_type, self.rate_limiters['general'])
        
        # Acquire rate limit permission
        result = rate_limiter.acquire()
        if result is not True:
            # Need to wait
            wait_time = result
            print(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
            time.sleep(wait_time)
            # Try again
            rate_limiter.acquire()
        
        # Make the request
        response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
        return response

# Usage
rate_limited_client = RateLimitedClient("https://api.trading-system.com/v1")

# Make market data requests
for symbol in ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]:
    response = rate_limited_client.make_rate_limited_request(
        'market_data', 
        'GET', 
        f'/market-data/quotes/{symbol}',
        headers=client.get_headers()
    )
    if response.status_code == 200:
        quote = response.json()
        print(f"{symbol}: ${quote['last']}")
```

## SDK Examples

### Python SDK

```python
# Example of a simplified Python SDK
class TradingSDK:
    def __init__(self, api_key=None, username=None, password=None, base_url="https://api.trading-system.com/v1"):
        self.client = RobustTradingClient(base_url)
        
        if api_key:
            self.client.session.headers.update({"X-API-Key": api_key})
        elif username and password:
            self.authenticate(username, password)
        else:
            raise ValueError("Either api_key or username/password must be provided")
    
    def authenticate(self, username, password):
        """Authenticate with username/password"""
        auth_data = {"username": username, "password": password}
        response = self.client.make_request('POST', '/auth/login', json=auth_data)
        token = response['access_token']
        self.client.session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Market Data Methods
    def get_quote(self, symbol):
        return self.client.make_request('GET', f'/market-data/quotes/{symbol}')
    
    def get_historical_data(self, symbol, start_date, end_date, interval='1d'):
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'interval': interval
        }
        return self.client.make_request('GET', f'/market-data/historical/{symbol}', params=params)
    
    # Trading Methods
    def buy_market(self, symbol, quantity):
        order_data = {
            'symbol': symbol,
            'side': 'buy',
            'quantity': quantity,
            'order_type': 'market'
        }
        return self.client.make_request('POST', '/orders', json=order_data)
    
    def sell_market(self, symbol, quantity):
        order_data = {
            'symbol': symbol,
            'side': 'sell',
            'quantity': quantity,
            'order_type': 'market'
        }
        return self.client.make_request('POST', '/orders', json=order_data)
    
    def buy_limit(self, symbol, quantity, price):
        order_data = {
            'symbol': symbol,
            'side': 'buy',
            'quantity': quantity,
            'order_type': 'limit',
            'price': price
        }
        return self.client.make_request('POST', '/orders', json=order_data)
    
    def cancel_order(self, order_id):
        return self.client.make_request('DELETE', f'/orders/{order_id}')
    
    # Portfolio Methods
    def get_portfolio(self):
        return self.client.make_request('GET', '/portfolio')
    
    def get_positions(self):
        return self.client.make_request('GET', '/portfolio/positions')
    
    def get_performance(self, period='1m'):
        return self.client.make_request('GET', '/portfolio/performance', params={'period': period})

# Usage
sdk = TradingSDK(username="your_username", password="your_password")

# Get quote
quote = sdk.get_quote("AAPL")
print(f"AAPL: ${quote['last']}")

# Place market buy order
order = sdk.buy_market("AAPL", 100)
print(f"Order placed: {order['id']}")

# Get portfolio
portfolio = sdk.get_portfolio()
print(f"Portfolio value: ${portfolio['total_value']:,.2f}")
```

This comprehensive API documentation provides examples for all major functionality of the trading system, including authentication, market data retrieval, trading operations, portfolio management, risk management, strategy development, WebSocket integration, error handling, and rate limiting. The examples are production-ready and include proper error handling and best practices.