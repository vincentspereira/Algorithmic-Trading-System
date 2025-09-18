"""Performance tests for the trading system using Locust.

This module contains load testing scenarios for various trading system endpoints
to ensure the system can handle expected traffic loads and identify performance
bottlenecks.
"""

import json
import random
import time
from typing import Dict, Any

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


class TradingSystemUser(HttpUser):
    """Base user class for trading system load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    
    def on_start(self):
        """Called when a user starts. Authenticate and set up session."""
        self.auth_token = None
        self.user_id = None
        self.portfolio_id = None
        
        # Authenticate user
        self.authenticate()
        
        # Get user portfolio
        self.get_portfolio()
    
    def authenticate(self):
        """Authenticate user and get access token."""
        auth_data = {
            "username": f"testuser_{random.randint(1, 1000)}",
            "password": "testpassword123"
        }
        
        with self.client.post("/api/v1/auth/login", json=auth_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user_id")
                response.success()
            else:
                response.failure(f"Authentication failed: {response.status_code}")
                raise RescheduleTask()
    
    def get_portfolio(self):
        """Get user's portfolio information."""
        if not self.auth_token:
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get("/api/v1/portfolio", headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.portfolio_id = data.get("portfolio_id")
                response.success()
            else:
                response.failure(f"Portfolio fetch failed: {response.status_code}")
    
    def get_headers(self) -> Dict[str, str]:
        """Get authenticated headers."""
        return {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}


class MarketDataUser(TradingSystemUser):
    """User focused on market data operations."""
    
    weight = 3  # 30% of users
    
    @task(5)
    def get_market_quote(self):
        """Get real-time market quote."""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META"]
        symbol = random.choice(symbols)
        
        with self.client.get(f"/api/v1/market-data/quote/{symbol}", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Quote fetch failed: {response.status_code}")
    
    @task(3)
    def get_historical_data(self):
        """Get historical market data."""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        symbol = random.choice(symbols)
        
        params = {
            "period": random.choice(["1d", "5d", "1mo"]),
            "interval": random.choice(["1m", "5m", "15m", "1h"])
        }
        
        with self.client.get(f"/api/v1/market-data/history/{symbol}", 
                           params=params,
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Historical data fetch failed: {response.status_code}")
    
    @task(2)
    def get_market_scanner_results(self):
        """Get market scanner results."""
        scanner_params = {
            "min_volume": random.randint(100000, 1000000),
            "min_price": random.randint(10, 100),
            "max_price": random.randint(100, 500)
        }
        
        with self.client.get("/api/v1/market-scanner/scan", 
                           params=scanner_params,
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Market scan failed: {response.status_code}")


class TradingUser(TradingSystemUser):
    """User focused on trading operations."""
    
    weight = 4  # 40% of users
    
    @task(3)
    def place_order(self):
        """Place a trading order."""
        if not self.portfolio_id:
            return
            
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        order_data = {
            "symbol": random.choice(symbols),
            "side": random.choice(["BUY", "SELL"]),
            "order_type": random.choice(["MARKET", "LIMIT"]),
            "quantity": random.randint(1, 100),
            "price": round(random.uniform(100, 300), 2) if random.choice([True, False]) else None,
            "time_in_force": "DAY"
        }
        
        with self.client.post("/api/v1/trading/orders", 
                            json=order_data,
                            headers=self.get_headers(), 
                            catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Order placement failed: {response.status_code}")
    
    @task(5)
    def get_orders(self):
        """Get user's orders."""
        with self.client.get("/api/v1/trading/orders", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Orders fetch failed: {response.status_code}")
    
    @task(2)
    def cancel_order(self):
        """Cancel a random order."""
        # First get orders
        with self.client.get("/api/v1/trading/orders", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                orders = response.json().get("orders", [])
                if orders:
                    order_id = random.choice(orders).get("order_id")
                    
                    # Cancel the order
                    with self.client.delete(f"/api/v1/trading/orders/{order_id}", 
                                          headers=self.get_headers(), 
                                          catch_response=True) as cancel_response:
                        if cancel_response.status_code in [200, 204]:
                            cancel_response.success()
                        else:
                            cancel_response.failure(f"Order cancellation failed: {cancel_response.status_code}")
    
    @task(4)
    def get_positions(self):
        """Get user's positions."""
        with self.client.get("/api/v1/portfolio/positions", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Positions fetch failed: {response.status_code}")


class PortfolioUser(TradingSystemUser):
    """User focused on portfolio management."""
    
    weight = 2  # 20% of users
    
    @task(5)
    def get_portfolio_summary(self):
        """Get portfolio summary."""
        with self.client.get("/api/v1/portfolio/summary", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Portfolio summary failed: {response.status_code}")
    
    @task(3)
    def get_portfolio_performance(self):
        """Get portfolio performance metrics."""
        params = {
            "period": random.choice(["1d", "1w", "1m", "3m", "1y"])
        }
        
        with self.client.get("/api/v1/portfolio/performance", 
                           params=params,
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Portfolio performance failed: {response.status_code}")
    
    @task(2)
    def get_risk_metrics(self):
        """Get portfolio risk metrics."""
        with self.client.get("/api/v1/portfolio/risk", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Risk metrics failed: {response.status_code}")
    
    @task(1)
    def optimize_portfolio(self):
        """Run portfolio optimization."""
        optimization_params = {
            "objective": random.choice(["max_sharpe", "min_volatility", "max_return"]),
            "constraints": {
                "max_weight": 0.3,
                "min_weight": 0.01
            }
        }
        
        with self.client.post("/api/v1/portfolio/optimize", 
                            json=optimization_params,
                            headers=self.get_headers(), 
                            catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Portfolio optimization failed: {response.status_code}")


class AnalyticsUser(TradingSystemUser):
    """User focused on analytics and research."""
    
    weight = 1  # 10% of users
    
    @task(3)
    def run_backtest(self):
        """Run a strategy backtest."""
        backtest_config = {
            "strategy": "mean_reversion",
            "symbols": ["AAPL", "GOOGL"],
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 100000,
            "parameters": {
                "lookback_period": random.randint(10, 50),
                "threshold": random.uniform(0.01, 0.05)
            }
        }
        
        with self.client.post("/api/v1/analytics/backtest", 
                            json=backtest_config,
                            headers=self.get_headers(), 
                            catch_response=True) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Backtest failed: {response.status_code}")
    
    @task(2)
    def get_technical_analysis(self):
        """Get technical analysis for a symbol."""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        symbol = random.choice(symbols)
        
        params = {
            "indicators": ["RSI", "MACD", "BB", "SMA"],
            "period": random.choice(["1d", "1w", "1m"])
        }
        
        with self.client.get(f"/api/v1/analytics/technical/{symbol}", 
                           params=params,
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Technical analysis failed: {response.status_code}")
    
    @task(1)
    def get_ai_insights(self):
        """Get AI-generated market insights."""
        with self.client.get("/api/v1/ai/insights", 
                           headers=self.get_headers(), 
                           catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"AI insights failed: {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def my_request_handler(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Custom request handler for additional metrics."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print("Starting performance test...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print("Performance test completed.")
    
    # Print summary statistics
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")


class WebSocketUser(HttpUser):
    """User for testing WebSocket connections."""
    
    weight = 1  # 10% of users for WebSocket testing
    wait_time = between(5, 15)  # Longer wait times for WebSocket connections
    
    def on_start(self):
        """Set up WebSocket connection."""
        # Note: Locust doesn't natively support WebSocket testing
        # This is a placeholder for WebSocket testing logic
        # You would need to use a WebSocket library like websocket-client
        pass
    
    @task
    def simulate_websocket_activity(self):
        """Simulate WebSocket activity through HTTP endpoints."""
        # Simulate real-time data subscription
        with self.client.get("/api/v1/websocket/status", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"WebSocket status check failed: {response.status_code}")


# Custom load shape for realistic trading patterns
class TradingLoadShape:
    """Custom load shape that simulates trading day patterns."""
    
    def tick(self):
        """Define load pattern over time."""
        run_time = self.get_run_time()
        
        # Market open surge (first 30 minutes)
        if run_time < 1800:  # 30 minutes
            return (200, 20)  # 200 users, spawn 20 per second
        
        # Mid-day trading (30 minutes to 6 hours)
        elif run_time < 21600:  # 6 hours
            return (100, 10)  # 100 users, spawn 10 per second
        
        # Market close surge (last 30 minutes)
        elif run_time < 23400:  # 6.5 hours
            return (150, 15)  # 150 users, spawn 15 per second
        
        # After hours (minimal activity)
        else:
            return (20, 2)  # 20 users, spawn 2 per second


if __name__ == "__main__":
    # This allows running the locustfile directly for testing
    import subprocess
    import sys
    
    # Run locust with this file
    cmd = [
        sys.executable, "-m", "locust", 
        "-f", __file__, 
        "--host=http://localhost:8000",
        "--users=50",
        "--spawn-rate=5",
        "--run-time=2m",
        "--headless"
    ]
    
    subprocess.run(cmd)