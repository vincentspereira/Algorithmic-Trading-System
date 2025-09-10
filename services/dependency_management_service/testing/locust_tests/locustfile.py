"""
Locust performance testing for the Algorithmic Trading System.
Tests load and performance of critical trading components.
"""

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import random
import json
import time
from datetime import datetime

# Mock trading symbols
TRADING_SYMBOLS = [
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX", 
    "AMD", "INTC", "PYPL", "ADBE", "CRM", "V", "MA", "JPM", "BAC"
]

# Mock market data
MOCK_MARKET_DATA = {
    "AAPL": {"price": 175.50, "volume": 50000000, "change": 0.02},
    "GOOGL": {"price": 125.75, "volume": 30000000, "change": -0.01},
    "MSFT": {"price": 325.25, "volume": 25000000, "change": 0.015},
    "AMZN": {"price": 135.20, "volume": 40000000, "change": 0.005},
    "TSLA": {"price": 250.80, "volume": 80000000, "change": 0.03}
}

class TradingSystemUser(HttpUser):
    """Locust user for trading system performance testing."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.symbol = random.choice(TRADING_SYMBOLS)
        self.user_id = f"user_{random.randint(1000, 9999)}"
    
    @task(10)
    def get_market_data(self):
        """Get market data for a symbol."""
        symbol = random.choice(TRADING_SYMBOLS)
        with self.client.get(f"/api/market-data/{symbol}", 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got wrong response: {response.status_code}")
    
    @task(8)
    def get_technical_indicators(self):
        """Get technical indicators for a symbol."""
        symbol = random.choice(TRADING_SYMBOLS)
        with self.client.get(f"/api/indicators/{symbol}", 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got wrong response: {response.status_code}")
    
    @task(5)
    def get_trading_signals(self):
        """Get trading signals for a symbol."""
        symbol = random.choice(TRADING_SYMBOLS)
        with self.client.get(f"/api/signals/{symbol}", 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got wrong response: {response.status_code}")
    
    @task(3)
    def place_order(self):
        """Place a mock trading order."""
        symbol = random.choice(TRADING_SYMBOLS)
        order_data = {
            "user_id": self.user_id,
            "symbol": symbol,
            "side": random.choice(["BUY", "SELL"]),
            "quantity": random.randint(1, 100),
            "price": MOCK_MARKET_DATA.get(symbol, {"price": 100.0})["price"],
            "order_type": "MARKET"
        }
        
        with self.client.post("/api/orders", 
                            json=order_data,
                            catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Got wrong response: {response.status_code}")
    
    @task(2)
    def get_portfolio(self):
        """Get user portfolio."""
        with self.client.get(f"/api/portfolio/{self.user_id}", 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got wrong response: {response.status_code}")
    
    @task(1)
    def get_performance_metrics(self):
        """Get system performance metrics."""
        with self.client.get("/api/metrics", 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got wrong response: {response.status_code}")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Event triggered when test starts."""
    print("🚀 Starting performance test for Algorithmic Trading System")
    if isinstance(environment.runner, MasterRunner):
        print("👑 Running as master node")
    else:
        print("👤 Running as worker node")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Event triggered when test stops."""
    print("🏁 Performance test completed")
    print(f"📊 Total requests: {environment.stats.total.num_requests}")
    print(f"✅ Success rate: {environment.stats.total.success_ratio() * 100:.2f}%")
    print(f"⏱️  Average response time: {environment.stats.total.avg_response_time:.2f}ms")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Event triggered for each request."""
    if exception:
        print(f"❌ Request failed: {name} - {exception}")
    elif response.status_code not in [200, 201]:
        print(f"⚠️  Request warning: {name} - Status {response.status_code}")