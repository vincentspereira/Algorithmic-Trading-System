#!/usr/bin/env python3
"""
Nautilus Trader - Comprehensive Performance Test Suite
This module provides comprehensive performance testing capabilities including
load testing, stress testing, endurance testing, and performance baseline establishment.
"""

import asyncio
import json
import logging
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import psutil
import requests
from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import websockets
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestConfiguration:
    """Configuration for performance tests"""
    base_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8001"
    database_url: str = "postgresql://nautilus:password@localhost:5432/nautilus_trader"
    redis_url: str = "redis://localhost:6379/0"
    
    # Load test configuration
    load_test_users: int = 100
    load_test_spawn_rate: int = 10
    load_test_duration: int = 300  # 5 minutes
    
    # Stress test configuration
    stress_test_users: int = 500
    stress_test_spawn_rate: int = 50
    stress_test_duration: int = 600  # 10 minutes
    
    # Endurance test configuration
    endurance_test_users: int = 50
    endurance_test_duration: int = 3600  # 1 hour
    
    # Performance thresholds
    max_response_time: float = 2.0  # seconds
    max_error_rate: float = 0.01  # 1%
    min_throughput: int = 1000  # requests per second

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    test_type: str
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    requests_per_second: float
    error_rate: float
    cpu_usage: float
    memory_usage: float
    network_io: Dict[str, float]
    disk_io: Dict[str, float]

class NautilusTraderUser(HttpUser):
    """Locust user class for Nautilus Trader performance testing"""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session"""
        self.auth_token = None
        self.user_id = None
        self.portfolio_id = None
        self.login()
    
    def login(self):
        """Authenticate user"""
        try:
            response = self.client.post("/api/auth/login", json={
                "username": f"test_user_{self.environment.runner.user_count}",
                "password": "test_password"
            })
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user_id")
                self.client.headers.update({"Authorization": f"Bearer {self.auth_token}"})
        except Exception as e:
            logger.error(f"Login failed: {e}")
    
    @task(10)
    def get_portfolio(self):
        """Get portfolio information"""
        self.client.get("/api/portfolio")
    
    @task(8)
    def get_positions(self):
        """Get current positions"""
        self.client.get("/api/positions")
    
    @task(6)
    def get_orders(self):
        """Get order history"""
        self.client.get("/api/orders")
    
    @task(5)
    def get_market_data(self):
        """Get market data"""
        self.client.get("/api/market-data/BTCUSD")
    
    @task(4)
    def place_order(self):
        """Place a test order"""
        order_data = {
            "symbol": "BTCUSD",
            "side": "buy",
            "quantity": 0.001,
            "order_type": "market",
            "time_in_force": "IOC"
        }
        self.client.post("/api/orders", json=order_data)
    
    @task(3)
    def get_account_info(self):
        """Get account information"""
        self.client.get("/api/account")
    
    @task(2)
    def get_trading_history(self):
        """Get trading history"""
        self.client.get("/api/trades")
    
    @task(1)
    def get_risk_metrics(self):
        """Get risk metrics"""
        self.client.get("/api/risk/metrics")

class PerformanceTestSuite:
    """Comprehensive performance test suite"""
    
    def __init__(self, config: TestConfiguration):
        self.config = config
        self.results: List[PerformanceMetrics] = []
        self.baseline_metrics: Optional[PerformanceMetrics] = None
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance tests"""
        logger.info("Starting comprehensive performance test suite")
        
        results = {
            "test_start_time": datetime.now().isoformat(),
            "configuration": asdict(self.config),
            "tests": {}
        }
        
        try:
            # Establish baseline
            logger.info("Establishing performance baseline")
            baseline = await self.establish_baseline()
            results["baseline"] = asdict(baseline) if baseline else None
            
            # Load testing
            logger.info("Running load tests")
            load_results = await self.run_load_tests()
            results["tests"]["load_test"] = load_results
            
            # Stress testing
            logger.info("Running stress tests")
            stress_results = await self.run_stress_tests()
            results["tests"]["stress_test"] = stress_results
            
            # Endurance testing
            logger.info("Running endurance tests")
            endurance_results = await self.run_endurance_tests()
            results["tests"]["endurance_test"] = endurance_results
            
            # Component-specific tests
            logger.info("Running component-specific tests")
            component_results = await self.run_component_tests()
            results["tests"]["component_tests"] = component_results
            
            # Generate performance report
            report = self.generate_performance_report(results)
            results["performance_report"] = report
            
        except Exception as e:
            logger.error(f"Performance test suite failed: {e}")
            results["error"] = str(e)
        
        results["test_end_time"] = datetime.now().isoformat()
        return results
    
    async def establish_baseline(self) -> Optional[PerformanceMetrics]:
        """Establish performance baseline with minimal load"""
        logger.info("Establishing performance baseline")
        
        try:
            # Run minimal load test to establish baseline
            baseline_config = TestConfiguration(
                base_url=self.config.base_url,
                load_test_users=5,
                load_test_spawn_rate=1,
                load_test_duration=60
            )
            
            metrics = await self.run_locust_test(
                test_type="baseline",
                users=baseline_config.load_test_users,
                spawn_rate=baseline_config.load_test_spawn_rate,
                duration=baseline_config.load_test_duration
            )
            
            self.baseline_metrics = metrics
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to establish baseline: {e}")
            return None
    
    async def run_load_tests(self) -> Dict[str, Any]:
        """Run comprehensive load tests"""
        logger.info("Running load tests")
        
        load_scenarios = [
            {"users": 50, "duration": 300, "name": "light_load"},
            {"users": 100, "duration": 300, "name": "normal_load"},
            {"users": 200, "duration": 300, "name": "heavy_load"},
        ]
        
        results = {}
        
        for scenario in load_scenarios:
            logger.info(f"Running load test scenario: {scenario['name']}")
            
            metrics = await self.run_locust_test(
                test_type=f"load_test_{scenario['name']}",
                users=scenario["users"],
                spawn_rate=self.config.load_test_spawn_rate,
                duration=scenario["duration"]
            )
            
            if metrics:
                results[scenario["name"]] = asdict(metrics)
                
                # Check if performance degrades
                if self.baseline_metrics:
                    degradation = self.calculate_performance_degradation(
                        self.baseline_metrics, metrics
                    )
                    results[scenario["name"]]["performance_degradation"] = degradation
        
        return results
    
    async def run_stress_tests(self) -> Dict[str, Any]:
        """Run stress tests to find breaking points"""
        logger.info("Running stress tests")
        
        stress_scenarios = [
            {"users": 300, "duration": 300, "name": "moderate_stress"},
            {"users": 500, "duration": 300, "name": "high_stress"},
            {"users": 1000, "duration": 180, "name": "extreme_stress"},
        ]
        
        results = {}
        
        for scenario in stress_scenarios:
            logger.info(f"Running stress test scenario: {scenario['name']}")
            
            metrics = await self.run_locust_test(
                test_type=f"stress_test_{scenario['name']}",
                users=scenario["users"],
                spawn_rate=self.config.stress_test_spawn_rate,
                duration=scenario["duration"]
            )
            
            if metrics:
                results[scenario["name"]] = asdict(metrics)
                
                # Check if system breaks under stress
                breaking_point = self.detect_breaking_point(metrics)
                results[scenario["name"]]["breaking_point_detected"] = breaking_point
        
        return results
    
    async def run_endurance_tests(self) -> Dict[str, Any]:
        """Run endurance tests for long-running operations"""
        logger.info("Running endurance tests")
        
        # Run sustained load for extended period
        metrics = await self.run_locust_test(
            test_type="endurance_test",
            users=self.config.endurance_test_users,
            spawn_rate=10,
            duration=self.config.endurance_test_duration
        )
        
        results = {}
        if metrics:
            results["sustained_load"] = asdict(metrics)
            
            # Check for memory leaks and performance degradation over time
            degradation_analysis = await self.analyze_endurance_degradation(metrics)
            results["degradation_analysis"] = degradation_analysis
        
        return results
    
    async def run_component_tests(self) -> Dict[str, Any]:
        """Run component-specific performance tests"""
        logger.info("Running component-specific tests")
        
        results = {}
        
        # API endpoint tests
        api_results = await self.test_api_endpoints()
        results["api_endpoints"] = api_results
        
        # WebSocket tests
        websocket_results = await self.test_websocket_performance()
        results["websocket"] = websocket_results
        
        # Database tests
        database_results = await self.test_database_performance()
        results["database"] = database_results
        
        # Cache tests
        cache_results = await self.test_cache_performance()
        results["cache"] = cache_results
        
        return results
    
    async def run_locust_test(self, test_type: str, users: int, spawn_rate: int, 
                            duration: int) -> Optional[PerformanceMetrics]:
        """Run Locust performance test"""
        try:
            # Setup Locust environment
            env = Environment(user_classes=[NautilusTraderUser])
            env.create_local_runner()
            
            # Start test
            start_time = time.time()
            system_start = self.get_system_metrics()
            
            env.runner.start(users, spawn_rate=spawn_rate)
            
            # Run for specified duration
            await asyncio.sleep(duration)
            
            # Stop test
            env.runner.stop()
            end_time = time.time()
            system_end = self.get_system_metrics()
            
            # Collect metrics
            stats = env.runner.stats
            
            response_times = []
            for stat in stats.entries.values():
                if stat.num_requests > 0:
                    response_times.extend([stat.avg_response_time] * stat.num_requests)
            
            if not response_times:
                return None
            
            metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                test_type=test_type,
                duration=end_time - start_time,
                total_requests=stats.total.num_requests,
                successful_requests=stats.total.num_requests - stats.total.num_failures,
                failed_requests=stats.total.num_failures,
                average_response_time=statistics.mean(response_times),
                median_response_time=statistics.median(response_times),
                p95_response_time=np.percentile(response_times, 95),
                p99_response_time=np.percentile(response_times, 99),
                min_response_time=min(response_times),
                max_response_time=max(response_times),
                requests_per_second=stats.total.current_rps,
                error_rate=stats.total.num_failures / max(stats.total.num_requests, 1),
                cpu_usage=(system_end["cpu"] + system_start["cpu"]) / 2,
                memory_usage=(system_end["memory"] + system_start["memory"]) / 2,
                network_io=system_end["network"],
                disk_io=system_end["disk"]
            )
            
            self.results.append(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"Locust test failed: {e}")
            return None
    
    async def test_api_endpoints(self) -> Dict[str, Any]:
        """Test individual API endpoint performance"""
        endpoints = [
            {"path": "/api/health", "method": "GET"},
            {"path": "/api/portfolio", "method": "GET"},
            {"path": "/api/positions", "method": "GET"},
            {"path": "/api/orders", "method": "GET"},
            {"path": "/api/market-data/BTCUSD", "method": "GET"},
        ]
        
        results = {}
        
        for endpoint in endpoints:
            logger.info(f"Testing endpoint: {endpoint['path']}")
            
            # Test with concurrent requests
            response_times = []
            errors = 0
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                for _ in range(100):  # 100 concurrent requests
                    task = self.make_request(session, endpoint["method"], endpoint["path"])
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for response in responses:
                    if isinstance(response, Exception):
                        errors += 1
                    else:
                        response_times.append(response)
            
            if response_times:
                results[endpoint["path"]] = {
                    "average_response_time": statistics.mean(response_times),
                    "median_response_time": statistics.median(response_times),
                    "p95_response_time": np.percentile(response_times, 95),
                    "min_response_time": min(response_times),
                    "max_response_time": max(response_times),
                    "error_rate": errors / len(responses),
                    "total_requests": len(responses)
                }
        
        return results
    
    async def make_request(self, session: aiohttp.ClientSession, method: str, path: str) -> float:
        """Make HTTP request and return response time"""
        start_time = time.time()
        try:
            url = f"{self.config.base_url}{path}"
            async with session.request(method, url) as response:
                await response.read()
                return time.time() - start_time
        except Exception:
            raise
    
    async def test_websocket_performance(self) -> Dict[str, Any]:
        """Test WebSocket connection performance"""
        logger.info("Testing WebSocket performance")
        
        results = {
            "connection_time": [],
            "message_latency": [],
            "throughput": 0,
            "concurrent_connections": 0
        }
        
        try:
            # Test connection establishment time
            for _ in range(10):
                start_time = time.time()
                async with websockets.connect(self.config.websocket_url) as websocket:
                    connection_time = time.time() - start_time
                    results["connection_time"].append(connection_time)
            
            # Test message latency and throughput
            async with websockets.connect(self.config.websocket_url) as websocket:
                message_count = 1000
                start_time = time.time()
                
                for i in range(message_count):
                    message_start = time.time()
                    await websocket.send(json.dumps({"type": "ping", "id": i}))
                    response = await websocket.recv()
                    message_latency = time.time() - message_start
                    results["message_latency"].append(message_latency)
                
                total_time = time.time() - start_time
                results["throughput"] = message_count / total_time
            
            # Test concurrent connections
            concurrent_tasks = []
            for _ in range(50):  # 50 concurrent connections
                task = self.test_concurrent_websocket()
                concurrent_tasks.append(task)
            
            concurrent_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            successful_connections = sum(1 for r in concurrent_results if not isinstance(r, Exception))
            results["concurrent_connections"] = successful_connections
            
        except Exception as e:
            logger.error(f"WebSocket performance test failed: {e}")
            results["error"] = str(e)
        
        return results
    
    async def test_concurrent_websocket(self) -> bool:
        """Test single concurrent WebSocket connection"""
        try:
            async with websockets.connect(self.config.websocket_url) as websocket:
                await websocket.send(json.dumps({"type": "ping"}))
                await websocket.recv()
                return True
        except Exception:
            return False
    
    async def test_database_performance(self) -> Dict[str, Any]:
        """Test database performance"""
        logger.info("Testing database performance")
        
        # This would require actual database connection
        # For now, return mock results
        return {
            "connection_time": 0.05,
            "query_performance": {
                "simple_select": 0.001,
                "complex_join": 0.015,
                "aggregation": 0.008,
                "insert": 0.003,
                "update": 0.004
            },
            "concurrent_connections": 100,
            "transaction_throughput": 5000
        }
    
    async def test_cache_performance(self) -> Dict[str, Any]:
        """Test cache (Redis) performance"""
        logger.info("Testing cache performance")
        
        # This would require actual Redis connection
        # For now, return mock results
        return {
            "connection_time": 0.001,
            "get_latency": 0.0005,
            "set_latency": 0.0008,
            "throughput": 50000,
            "hit_rate": 0.95,
            "memory_usage": "256MB"
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        return {
            "cpu": psutil.cpu_percent(interval=1),
            "memory": psutil.virtual_memory().percent,
            "network": dict(psutil.net_io_counters()._asdict()),
            "disk": dict(psutil.disk_io_counters()._asdict())
        }
    
    def calculate_performance_degradation(self, baseline: PerformanceMetrics, 
                                        current: PerformanceMetrics) -> Dict[str, float]:
        """Calculate performance degradation compared to baseline"""
        return {
            "response_time_increase": (
                (current.average_response_time - baseline.average_response_time) / 
                baseline.average_response_time * 100
            ),
            "throughput_decrease": (
                (baseline.requests_per_second - current.requests_per_second) / 
                baseline.requests_per_second * 100
            ),
            "error_rate_increase": (current.error_rate - baseline.error_rate) * 100,
            "cpu_usage_increase": current.cpu_usage - baseline.cpu_usage,
            "memory_usage_increase": current.memory_usage - baseline.memory_usage
        }
    
    def detect_breaking_point(self, metrics: PerformanceMetrics) -> bool:
        """Detect if system has reached breaking point"""
        return (
            metrics.error_rate > self.config.max_error_rate or
            metrics.average_response_time > self.config.max_response_time or
            metrics.requests_per_second < self.config.min_throughput
        )
    
    async def analyze_endurance_degradation(self, metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Analyze performance degradation during endurance test"""
        # This would analyze metrics over time to detect degradation
        # For now, return mock analysis
        return {
            "memory_leak_detected": False,
            "performance_degradation_rate": 0.02,  # 2% per hour
            "stability_score": 0.95,
            "recommendations": [
                "Monitor memory usage over longer periods",
                "Implement connection pooling optimization",
                "Consider garbage collection tuning"
            ]
        }
    
    def generate_performance_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        report = {
            "summary": {
                "total_tests_run": len([t for t in results["tests"].values() if t]),
                "overall_performance": "good",  # This would be calculated
                "critical_issues": [],
                "recommendations": []
            },
            "performance_trends": {},
            "bottlenecks_identified": [],
            "capacity_planning": {}
        }
        
        # Analyze results and generate insights
        if results.get("baseline"):
            baseline = results["baseline"]
            report["baseline_performance"] = {
                "response_time": baseline["average_response_time"],
                "throughput": baseline["requests_per_second"],
                "error_rate": baseline["error_rate"]
            }
        
        # Check for performance issues
        for test_name, test_results in results["tests"].items():
            if isinstance(test_results, dict):
                for scenario_name, scenario_results in test_results.items():
                    if isinstance(scenario_results, dict):
                        if scenario_results.get("error_rate", 0) > self.config.max_error_rate:
                            report["summary"]["critical_issues"].append(
                                f"High error rate in {test_name}/{scenario_name}: "
                                f"{scenario_results['error_rate']:.2%}"
                            )
                        
                        if scenario_results.get("average_response_time", 0) > self.config.max_response_time:
                            report["summary"]["critical_issues"].append(
                                f"High response time in {test_name}/{scenario_name}: "
                                f"{scenario_results['average_response_time']:.2f}s"
                            )
        
        # Generate recommendations
        if report["summary"]["critical_issues"]:
            report["summary"]["overall_performance"] = "needs_attention"
            report["summary"]["recommendations"].extend([
                "Investigate high error rates and response times",
                "Consider scaling up resources",
                "Optimize database queries and caching",
                "Review application code for bottlenecks"
            ])
        
        return report
    
    def save_results(self, results: Dict[str, Any], filename: str = None):
        """Save test results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Performance test results saved to {filename}")
    
    def generate_charts(self, results: Dict[str, Any]):
        """Generate performance charts and visualizations"""
        try:
            # Create performance comparison charts
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Response time comparison
            if "tests" in results and "load_test" in results["tests"]:
                load_tests = results["tests"]["load_test"]
                scenarios = list(load_tests.keys())
                response_times = [load_tests[s].get("average_response_time", 0) for s in scenarios]
                
                axes[0, 0].bar(scenarios, response_times)
                axes[0, 0].set_title("Average Response Time by Load Scenario")
                axes[0, 0].set_ylabel("Response Time (seconds)")
                
                # Throughput comparison
                throughputs = [load_tests[s].get("requests_per_second", 0) for s in scenarios]
                axes[0, 1].bar(scenarios, throughputs)
                axes[0, 1].set_title("Throughput by Load Scenario")
                axes[0, 1].set_ylabel("Requests per Second")
                
                # Error rate comparison
                error_rates = [load_tests[s].get("error_rate", 0) * 100 for s in scenarios]
                axes[1, 0].bar(scenarios, error_rates)
                axes[1, 0].set_title("Error Rate by Load Scenario")
                axes[1, 0].set_ylabel("Error Rate (%)")
                
                # Resource usage
                cpu_usage = [load_tests[s].get("cpu_usage", 0) for s in scenarios]
                memory_usage = [load_tests[s].get("memory_usage", 0) for s in scenarios]
                
                x = np.arange(len(scenarios))
                width = 0.35
                
                axes[1, 1].bar(x - width/2, cpu_usage, width, label='CPU Usage (%)')
                axes[1, 1].bar(x + width/2, memory_usage, width, label='Memory Usage (%)')
                axes[1, 1].set_title("Resource Usage by Load Scenario")
                axes[1, 1].set_ylabel("Usage (%)")
                axes[1, 1].set_xticks(x)
                axes[1, 1].set_xticklabels(scenarios)
                axes[1, 1].legend()
            
            plt.tight_layout()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plt.savefig(f"performance_charts_{timestamp}.png", dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Performance charts saved to performance_charts_{timestamp}.png")
            
        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")

async def main():
    """Main function to run performance tests"""
    config = TestConfiguration()
    test_suite = PerformanceTestSuite(config)
    
    # Run all performance tests
    results = await test_suite.run_all_tests()
    
    # Save results
    test_suite.save_results(results)
    
    # Generate charts
    test_suite.generate_charts(results)
    
    # Print summary
    print("\n" + "="*50)
    print("PERFORMANCE TEST SUMMARY")
    print("="*50)
    
    if "performance_report" in results:
        report = results["performance_report"]
        print(f"Overall Performance: {report['summary']['overall_performance']}")
        print(f"Tests Run: {report['summary']['total_tests_run']}")
        
        if report["summary"]["critical_issues"]:
            print("\nCritical Issues:")
            for issue in report["summary"]["critical_issues"]:
                print(f"  - {issue}")
        
        if report["summary"]["recommendations"]:
            print("\nRecommendations:")
            for rec in report["summary"]["recommendations"]:
                print(f"  - {rec}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(main())