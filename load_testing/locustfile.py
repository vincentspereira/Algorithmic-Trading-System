from locust import HttpUser, task, between
import json

# This Locust file simulates user behavior for load testing the trading system.
# It includes tasks for hitting key API endpoints to measure performance
# under high-frequency trading scenarios.

class TradingUser(HttpUser):
    """
    Simulates a user interacting with the trading system.
    """
    wait_time = between(0.1, 0.5)  # Simulate high-frequency activity

    @task(10)
    def get_health(self):
        """Task to check the health of the system."""
        self.client.get("/health")

    @task(5)
    def run_backtest(self):
        """Task to run a backtest."""
        self.client.post("/api/v1/backtest/run", json={"symbol": "AAPL", "year": 2023})

    @task(2)
    def get_kafka_status(self):
        """Task to get Kafka status."""
        self.client.get("/api/v1/kafka/status")
        
    @task(1)
    def publish_trading_signal(self):
        """Task to publish a trading signal."""
        signal = {
            "symbol": "AAPL",
            "signal": "BUY",
            "confidence": 0.9,
        }
        self.client.post("/api/v1/kafka/signal", json=signal)

# To run this load test:
# 1. Install Locust: pip install locust
# 2. Run from the command line: locust -f load_testing/locustfile.py --host http://localhost:8000
# 3. Open your browser to http://localhost:8089 and start a new load test.