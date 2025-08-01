#!/usr/bin/env python3
"""
Nautilus Trader - Locust Performance Tests

This module provides Locust-based performance testing for web load testing
with realistic user behavior simulation.
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingUser(HttpUser):
    """Simulates a trading user behavior"""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts"""
        self.auth_token = None
        self.portfolio_id = None
        self.login()
    
    def login(self):
        """Authenticate user"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"user_{random.randint(1000, 9999)}",
            "password": "test_password"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("token")
            self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
            logger.info("User authenticated successfully")
        else:
            logger.error(f"Authentication failed: {response.status_code}")
    
    @task(10)
    def view_portfolio(self):
        """View portfolio - most common action"""
        with self.client.get("/api/v1/portfolio", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                self.portfolio_id = data.get("id")
                response.success()
            else:
                response.failure(f"Portfolio request failed: {response.status_code}")
    
    @task(8)
    def view_positions(self):
        """View current positions"""
        self.client.get("/api/v1/positions")
    
    @task(6)
    def view_orders(self):
        """View order history"""
        self.client.get("/api/v1/orders")
    
    @task(5)
    def get_market_data(self):
        """Get market data for symbols"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        symbol = random.choice(symbols)
        self.client.get(f"/api/v1/market-data/{symbol}")
    
    @task(3)
    def place_order(self):
        """Place a trading order"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        order_data = {
            "symbol": random.choice(symbols),
            "side": random.choice(["BUY", "SELL"]),
            "quantity": random.randint(1, 100),
            "order_type": "MARKET",
            "time_in_force": "DAY"
        }
        
        with self.client.post("/api/v1/orders", json=order_data, catch_response=True) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Order placement failed: {response.status_code}")
    
    @task(2)
    def cancel_order(self):
        """Cancel an existing order"""
        # First get orders
        response = self.client.get("/api/v1/orders?status=PENDING")
        if response.status_code == 200:
            orders = response.json().get("orders", [])
            if orders:
                order_id = random.choice(orders)["id"]
                self.client.delete(f"/api/v1/orders/{order_id}")
    
    @task(4)
    def graphql_query(self):
        """Execute GraphQL query"""
        query = """
        query {
            portfolio {
                totalValue
                dayChange
                positions {
                    symbol
                    quantity
                    marketValue
                    unrealizedPnL
                }
            }
        }
        """
        
        self.client.post("/graphql", json={"query": query})
    
    @task(1)
    def websocket_connection(self):
        """Simulate WebSocket connection for real-time data"""
        # Note: Locust doesn't natively support WebSocket, 
        # but we can simulate the HTTP upgrade request
        headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
            "Sec-WebSocket-Version": "13"
        }
        
        with self.client.get("/ws", headers=headers, catch_response=True) as response:
            if response.status_code == 101:
                response.success()
            else:
                response.failure(f"WebSocket upgrade failed: {response.status_code}")

class HighFrequencyTradingUser(HttpUser):
    """Simulates high-frequency trading user with minimal wait times"""
    
    wait_time = between(0.1, 0.5)  # Very short wait times
    
    def on_start(self):
        """Initialize HFT user"""
        self.auth_token = None
        self.login()
    
    def login(self):
        """Authenticate HFT user"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": f"hft_user_{random.randint(1000, 9999)}",
            "password": "hft_password"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("token")
            self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
    
    @task(20)
    def rapid_market_data(self):
        """Rapidly fetch market data"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        symbol = random.choice(symbols)
        self.client.get(f"/api/v1/market-data/{symbol}/realtime")
    
    @task(15)
    def rapid_order_placement(self):
        """Rapidly place and cancel orders"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        order_data = {
            "symbol": random.choice(symbols),
            "side": random.choice(["BUY", "SELL"]),
            "quantity": random.randint(100, 1000),
            "order_type": "LIMIT",
            "price": round(random.uniform(100, 200), 2),
            "time_in_force": "IOC"  # Immediate or Cancel
        }
        
        self.client.post("/api/v1/orders", json=order_data)
    
    @task(10)
    def order_book_data(self):
        """Get order book data"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        symbol = random.choice(symbols)
        self.client.get(f"/api/v1/market-data/{symbol}/orderbook")

class MarketDataUser(HttpUser):
    """Simulates users primarily consuming market data"""
    
    wait_time = between(0.5, 2)
    
    @task(15)
    def get_quotes(self):
        """Get real-time quotes"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN", "NVDA", "META"]
        symbol = random.choice(symbols)
        self.client.get(f"/api/v1/market-data/{symbol}/quote")
    
    @task(10)
    def get_historical_data(self):
        """Get historical price data"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        symbol = random.choice(symbols)
        timeframe = random.choice(["1m", "5m", "15m", "1h", "1d"])
        self.client.get(f"/api/v1/market-data/{symbol}/history?timeframe={timeframe}&limit=100")
    
    @task(8)
    def get_technical_indicators(self):
        """Get technical indicators"""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        symbol = random.choice(symbols)
        indicator = random.choice(["sma", "ema", "rsi", "macd", "bollinger"])
        self.client.get(f"/api/v1/market-data/{symbol}/indicators/{indicator}")
    
    @task(5)
    def get_market_news(self):
        """Get market news"""
        self.client.get("/api/v1/market-data/news")

class AdminUser(HttpUser):
    """Simulates administrative users"""
    
    wait_time = between(5, 15)  # Longer wait times for admin tasks
    
    def on_start(self):
        """Authenticate as admin"""
        response = self.client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin_password"
        })
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("token")
            self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
    
    @task(5)
    def view_system_metrics(self):
        """View system performance metrics"""
        self.client.get("/api/v1/admin/metrics")
    
    @task(3)
    def view_user_activity(self):
        """View user activity logs"""
        self.client.get("/api/v1/admin/users/activity")
    
    @task(2)
    def view_trading_statistics(self):
        """View trading statistics"""
        self.client.get("/api/v1/admin/trading/statistics")
    
    @task(1)
    def system_health_check(self):
        """Perform system health check"""
        self.client.get("/health")

# Custom event handlers for detailed reporting
@events.request.add_listener
def request_handler(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Custom request handler for detailed logging"""
    if exception:
        logger.error(f"Request failed: {request_type} {name} - {exception}")
    elif response_time > 1000:  # Log slow requests (>1s)
        logger.warning(f"Slow request: {request_type} {name} - {response_time}ms")

@events.test_start.add_listener
def test_start_handler(environment, **kwargs):
    """Handler for test start event"""
    logger.info("Performance test started")
    
    # Log test configuration
    if isinstance(environment.runner, MasterRunner):
        logger.info(f"Master runner started with {environment.runner.worker_count} workers")
    elif isinstance(environment.runner, WorkerRunner):
        logger.info("Worker runner started")
    else:
        logger.info("Standalone runner started")

@events.test_stop.add_listener
def test_stop_handler(environment, **kwargs):
    """Handler for test stop event"""
    logger.info("Performance test completed")
    
    # Log final statistics
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"RPS: {stats.total.current_rps:.2f}")

# Custom load shapes for different test scenarios
from locust import LoadTestShape

class StepLoadShape(LoadTestShape):
    """Step load shape that increases users in steps"""
    
    step_time = 60  # 60 seconds per step
    step_load = 10  # 10 users per step
    spawn_rate = 2  # 2 users per second
    time_limit = 600  # 10 minutes total
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > self.time_limit:
            return None
        
        current_step = run_time // self.step_time
        return (current_step * self.step_load, self.spawn_rate)

class SpikeLoadShape(LoadTestShape):
    """Spike load shape with sudden increases"""
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 60:
            return (10, 2)  # Baseline load
        elif run_time < 120:
            return (100, 10)  # Spike
        elif run_time < 180:
            return (10, 2)  # Back to baseline
        elif run_time < 240:
            return (200, 20)  # Bigger spike
        elif run_time < 300:
            return (10, 2)  # Back to baseline
        else:
            return None

class DoubleWaveLoadShape(LoadTestShape):
    """Double wave load shape"""
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > 600:
            return None
        
        # Create wave pattern
        import math
        wave1 = 50 * (1 + math.sin(2 * math.pi * run_time / 120))  # 2-minute cycle
        wave2 = 30 * (1 + math.sin(2 * math.pi * run_time / 180))  # 3-minute cycle
        
        user_count = int(wave1 + wave2)
        spawn_rate = max(1, user_count // 10)
        
        return (user_count, spawn_rate)

# Performance test scenarios
class PerformanceTestScenarios:
    """Predefined performance test scenarios"""
    
    @staticmethod
    def baseline_test():
        """Baseline performance test"""
        return {
            "users": 10,
            "spawn_rate": 2,
            "run_time": "5m",
            "user_classes": [TradingUser]
        }
    
    @staticmethod
    def load_test():
        """Standard load test"""
        return {
            "users": 100,
            "spawn_rate": 10,
            "run_time": "10m",
            "user_classes": [TradingUser, MarketDataUser]
        }
    
    @staticmethod
    def stress_test():
        """Stress test with high load"""
        return {
            "users": 500,
            "spawn_rate": 50,
            "run_time": "15m",
            "user_classes": [TradingUser, HighFrequencyTradingUser, MarketDataUser]
        }
    
    @staticmethod
    def spike_test():
        """Spike test with sudden load increases"""
        return {
            "load_shape": SpikeLoadShape,
            "user_classes": [TradingUser, MarketDataUser]
        }
    
    @staticmethod
    def endurance_test():
        """Long-running endurance test"""
        return {
            "users": 50,
            "spawn_rate": 5,
            "run_time": "2h",
            "user_classes": [TradingUser, MarketDataUser, AdminUser]
        }

if __name__ == "__main__":
    # This allows running the file directly for testing
    import subprocess
    import sys
    
    # Example: Run a basic load test
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--users", "50",
        "--spawn-rate", "5",
        "--run-time", "5m",
        "--host", "http://localhost:8000",
        "--html", "performance/locust_report.html"
    ]
    
    print("Starting Locust performance test...")
    print(f"Command: {' '.join(cmd)}")
    subprocess.run(cmd)