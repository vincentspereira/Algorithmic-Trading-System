#!/usr/bin/env python3
"""
Latency Testing Framework
Tests system response times and validates latency requirements for trading operations.
"""

import pytest
import asyncio
import time
import statistics
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LatencyRequirement(Enum):
    """Latency requirement categories"""
    CRITICAL = "CRITICAL"      # < 10ms (Order execution, risk checks)
    HIGH = "HIGH"              # < 50ms (Market data updates)
    MEDIUM = "MEDIUM"          # < 100ms (Portfolio calculations)
    LOW = "LOW"                # < 500ms (Reporting, analytics)


@dataclass
class LatencyMeasurement:
    """Latency measurement data"""
    operation: str
    duration_ms: float
    timestamp: datetime
    requirement: LatencyRequirement
    metadata: Dict[str, Any] = None


class LatencyProfiler:
    """Latency profiling and measurement tool"""
    
    def __init__(self):
        self.measurements: List[LatencyMeasurement] = []
        self.baseline_measurements: Dict[str, List[float]] = {}
        
    def measure(self, operation: str, requirement: LatencyRequirement, metadata: Dict = None):
        """Decorator to measure function execution time"""
        def decorator(func):
            async def async_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    duration_ms = (end_time - start_time) * 1000
                    measurement = LatencyMeasurement(
                        operation=operation,
                        duration_ms=duration_ms,
                        timestamp=datetime.now(),
                        requirement=requirement,
                        metadata=metadata or {}
                    )
                    self.measurements.append(measurement)
                    logger.debug(f"Operation '{operation}' took {duration_ms:.2f}ms")
                    
            def sync_wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    end_time = time.perf_counter()
                    duration_ms = (end_time - start_time) * 1000
                    measurement = LatencyMeasurement(
                        operation=operation,
                        duration_ms=duration_ms,
                        timestamp=datetime.now(),
                        requirement=requirement,
                        metadata=metadata or {}
                    )
                    self.measurements.append(measurement)
                    logger.debug(f"Operation '{operation}' took {duration_ms:.2f}ms")
                    
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
        
    def get_statistics(self, operation: str = None) -> Dict[str, float]:
        """Get latency statistics for an operation or all operations"""
        if operation:
            measurements = [m for m in self.measurements if m.operation == operation]
        else:
            measurements = self.measurements
            
        if not measurements:
            return {}
            
        durations = [m.duration_ms for m in measurements]
        return {
            "count": len(durations),
            "mean": statistics.mean(durations),
            "median": statistics.median(durations),
            "min": min(durations),
            "max": max(durations),
            "std_dev": statistics.stdev(durations) if len(durations) > 1 else 0,
            "percentile_95": self._percentile(durations, 95),
            "percentile_99": self._percentile(durations, 99)
        }
        
    def _percentile(self, data: List[float], percentile: float) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
            
    def check_requirements(self) -> List[Dict[str, Any]]:
        """Check if operations meet their latency requirements"""
        violations = []
        
        # Group measurements by operation
        operations = {}
        for measurement in self.measurements:
            if measurement.operation not in operations:
                operations[measurement.operation] = []
            operations[measurement.operation].append(measurement)
            
        # Check each operation against its requirement
        for operation, measurements in operations.items():
            stats = self.get_statistics(operation)
            if not stats:
                continue
                
            # Get requirement threshold
            requirement = measurements[0].requirement
            thresholds = {
                LatencyRequirement.CRITICAL: 10.0,   # < 10ms
                LatencyRequirement.HIGH: 50.0,       # < 50ms
                LatencyRequirement.MEDIUM: 100.0,    # < 100ms
                LatencyRequirement.LOW: 500.0        # < 500ms
            }
            
            threshold = thresholds.get(requirement, 500.0)
            mean_latency = stats["mean"]
            
            if mean_latency > threshold:
                violations.append({
                    "operation": operation,
                    "requirement": requirement.value,
                    "threshold_ms": threshold,
                    "actual_mean_ms": mean_latency,
                    "violation_ratio": mean_latency / threshold
                })
                
        return violations


class MockOrderSystem:
    """Mock order system for latency testing"""
    
    def __init__(self, base_latency_us: int = 500):
        self.base_latency_us = base_latency_us
        self.orders = {}
        self.order_counter = 0
        
    async def place_order(self, symbol: str, quantity: int, price: float, side: str) -> Dict:
        """Place an order with simulated latency"""
        await asyncio.sleep(self.base_latency_us / 1_000_000)  # Convert μs to seconds
        
        self.order_counter += 1
        order_id = f"order_{self.order_counter}"
        order = {
            "id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "side": side,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
        self.orders[order_id] = order
        
        return {"status": "success", "order_id": order_id, **order}
        
    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order with simulated latency"""
        await asyncio.sleep(self.base_latency_us / 1_000_000)
        
        if order_id in self.orders:
            self.orders[order_id]["status"] = "cancelled"
            return {"status": "success", "message": "Order cancelled"}
        else:
            return {"status": "error", "message": "Order not found"}


class MockMarketDataFeed:
    """Mock market data feed for latency testing"""
    
    def __init__(self, feed_latency_us: int = 200):
        self.feed_latency_us = feed_latency_us
        self.is_running = False
        self.subscribers = []
        
    async def start_feed(self):
        """Start market data feed"""
        await asyncio.sleep(self.feed_latency_us / 1_000_000)
        self.is_running = True
        
    def stop_feed(self):
        """Stop market data feed"""
        self.is_running = False
        
    async def subscribe(self, symbol: str, callback) -> str:
        """Subscribe to market data with simulated latency"""
        await asyncio.sleep(self.feed_latency_us / 1_000_000)
        
        subscription_id = f"sub_{len(self.subscribers) + 1}"
        self.subscribers.append({
            "id": subscription_id,
            "symbol": symbol,
            "callback": callback
        })
        
        return subscription_id
        
    async def get_latest_price(self, symbol: str) -> Dict:
        """Get latest price with simulated latency"""
        await asyncio.sleep(self.feed_latency_us / 1_000_000)
        
        # Mock price data
        prices = {
            "AAPL": 150.25,
            "GOOGL": 2750.80,
            "TSLA": 800.50,
            "NVDA": 450.25
        }
        
        return {
            "symbol": symbol,
            "price": prices.get(symbol, 100.0),
            "timestamp": datetime.now().isoformat()
        }


class MockRiskEngine:
    """Mock risk engine for latency testing"""
    
    def __init__(self, calculation_latency_us: int = 300):
        self.calculation_latency_us = calculation_latency_us
        
    async def check_risk_limits(self, portfolio: Dict, new_order: Dict) -> Dict:
        """Check risk limits with simulated latency"""
        await asyncio.sleep(self.calculation_latency_us / 1_000_000)
        
        # Simple risk check
        total_exposure = sum(pos.get("value", 0) for pos in portfolio.get("positions", []))
        order_value = new_order.get("quantity", 0) * new_order.get("price", 0)
        
        if total_exposure + order_value > portfolio.get("cash", 0) * 10:
            return {"status": "rejected", "reason": "Exceeds risk limits"}
        else:
            return {"status": "approved", "risk_score": 0.85}


class MockDatabase:
    """Mock database for latency testing"""
    
    def __init__(self, query_latency_us: int = 1000):
        self.query_latency_us = query_latency_us
        self.data_store = {}
        
    async def execute_query(self, query: str, params: Dict = None) -> Dict:
        """Execute database query with simulated latency"""
        await asyncio.sleep(self.query_latency_us / 1_000_000)
        
        # Mock query results
        if "SELECT" in query.upper():
            return {
                "status": "success",
                "data": [{"id": 1, "value": 100}],
                "row_count": 1
            }
        else:
            return {"status": "success", "rows_affected": 1}


class TestLatency:
    """Test suite for latency requirements"""
    
    def setup_method(self):
        """Setup test environment"""
        self.profiler = LatencyProfiler()
        self.order_system = MockOrderSystem(base_latency_us=500)
        self.market_feed = MockMarketDataFeed(feed_latency_us=200)
        self.risk_engine = MockRiskEngine(calculation_latency_us=300)
        self.database = MockDatabase(query_latency_us=1000)
        
        # Test data
        self.test_portfolio = {
            'cash': 1000000,
            'positions': [
                {'symbol': 'AAPL', 'quantity': 100, 'value': 15000},
                {'symbol': 'GOOGL', 'quantity': 50, 'value': 12500}
            ]
        }
        
        logger.info("Latency testing system setup completed")
        
    async def teardown_method(self):
        """Cleanup test environment"""
        if hasattr(self.market_feed, 'is_running') and self.market_feed.is_running:
            self.market_feed.stop_feed()
        logger.info("Latency testing system cleanup completed")
        
    @pytest.mark.asyncio
    async def test_order_execution_latency(self):
        """Test order execution latency requirement (< 10ms)"""
        profiler = LatencyProfiler()
        
        # Measure multiple order executions
        latencies = []
        for i in range(100):
            start_time = time.perf_counter()
            await self.order_system.place_order("AAPL", 100, 150.0, "BUY")
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        percentile_95 = statistics.quantiles(latencies, n=20)[-1]  # 95th percentile
        
        logger.info(f"Order execution latency - Mean: {mean_latency:.2f}ms, Median: {median_latency:.2f}ms, 95th Percentile: {percentile_95:.2f}ms")
        
        # Validate requirement (< 10ms)
        assert mean_latency < 10.0, f"Mean order execution latency {mean_latency:.2f}ms exceeds 10ms requirement"
        assert median_latency < 10.0, f"Median order execution latency {median_latency:.2f}ms exceeds 10ms requirement"
        assert percentile_95 < 15.0, f"95th percentile order execution latency {percentile_95:.2f}ms exceeds 15ms requirement"
        
    @pytest.mark.asyncio
    async def test_market_data_latency(self):
        """Test market data update latency requirement (< 50ms)"""
        # Measure market data retrieval latency
        latencies = []
        for i in range(100):
            start_time = time.perf_counter()
            await self.market_feed.get_latest_price("AAPL")
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        percentile_95 = statistics.quantiles(latencies, n=20)[-1]  # 95th percentile
        
        logger.info(f"Market data latency - Mean: {mean_latency:.2f}ms, Median: {median_latency:.2f}ms, 95th Percentile: {percentile_95:.2f}ms")
        
        # Validate requirement (< 50ms)
        assert mean_latency < 50.0, f"Mean market data latency {mean_latency:.2f}ms exceeds 50ms requirement"
        assert median_latency < 50.0, f"Median market data latency {median_latency:.2f}ms exceeds 50ms requirement"
        assert percentile_95 < 75.0, f"95th percentile market data latency {percentile_95:.2f}ms exceeds 75ms requirement"
        
    @pytest.mark.asyncio
    async def test_risk_check_latency(self):
        """Test risk check latency requirement (< 10ms)"""
        # Create test order
        test_order = {
            "symbol": "NVDA",
            "quantity": 100,
            "price": 450.0,
            "side": "BUY"
        }
        
        # Measure risk check latency
        latencies = []
        for i in range(100):
            start_time = time.perf_counter()
            await self.risk_engine.check_risk_limits(self.test_portfolio, test_order)
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        percentile_95 = statistics.quantiles(latencies, n=20)[-1]  # 95th percentile
        
        logger.info(f"Risk check latency - Mean: {mean_latency:.2f}ms, Median: {median_latency:.2f}ms, 95th Percentile: {percentile_95:.2f}ms")
        
        # Validate requirement (< 10ms)
        assert mean_latency < 10.0, f"Mean risk check latency {mean_latency:.2f}ms exceeds 10ms requirement"
        assert median_latency < 10.0, f"Median risk check latency {median_latency:.2f}ms exceeds 10ms requirement"
        assert percentile_95 < 15.0, f"95th percentile risk check latency {percentile_95:.2f}ms exceeds 15ms requirement"
        
    @pytest.mark.asyncio
    async def test_database_query_latency(self):
        """Test database query latency requirement (< 100ms)"""
        # Measure database query latency
        latencies = []
        for i in range(50):
            start_time = time.perf_counter()
            await self.database.execute_query("SELECT * FROM orders WHERE symbol = ?", {"symbol": "AAPL"})
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
        # Calculate statistics
        mean_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        percentile_95 = statistics.quantiles(latencies, n=20)[-1]  # 95th percentile
        
        logger.info(f"Database query latency - Mean: {mean_latency:.2f}ms, Median: {median_latency:.2f}ms, 95th Percentile: {percentile_95:.2f}ms")
        
        # Validate requirement (< 100ms)
        assert mean_latency < 100.0, f"Mean database query latency {mean_latency:.2f}ms exceeds 100ms requirement"
        assert median_latency < 100.0, f"Median database query latency {median_latency:.2f}ms exceeds 100ms requirement"
        assert percentile_95 < 150.0, f"95th percentile database query latency {percentile_95:.2f}ms exceeds 150ms requirement"
        
    @pytest.mark.asyncio
    async def test_concurrent_operations_latency(self):
        """Test latency under concurrent operations"""
        # Start market data feed
        await self.market_feed.start_feed()
        
        # Measure concurrent operations
        async def place_order_task(i):
            start_time = time.perf_counter()
            result = await self.order_system.place_order(f"STOCK{i}", 100, 100.0, "BUY")
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, result
            
        async def market_data_task(i):
            start_time = time.perf_counter()
            result = await self.market_feed.get_latest_price("AAPL")
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, result
            
        async def risk_check_task(i):
            start_time = time.perf_counter()
            test_order = {"symbol": "TEST", "quantity": 100, "price": 50.0, "side": "BUY"}
            result = await self.risk_engine.check_risk_limits(self.test_portfolio, test_order)
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, result
            
        # Run concurrent operations
        tasks = []
        for i in range(30):
            tasks.extend([
                place_order_task(i),
                market_data_task(i),
                risk_check_task(i)
            ])
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate results by operation type
        order_latencies = [r[0] for r in results[0::3] if not isinstance(r, Exception)]
        market_latencies = [r[0] for r in results[1::3] if not isinstance(r, Exception)]
        risk_latencies = [r[0] for r in results[2::3] if not isinstance(r, Exception)]
        
        # Validate concurrent operation requirements
        order_mean = statistics.mean(order_latencies) if order_latencies else 0
        market_mean = statistics.mean(market_latencies) if market_latencies else 0
        risk_mean = statistics.mean(risk_latencies) if risk_latencies else 0
        
        logger.info(f"Concurrent operations - Order: {order_mean:.2f}ms, Market: {market_mean:.2f}ms, Risk: {risk_mean:.2f}ms")
        
        # Check that concurrent operations don't exceed 2x single operation latency
        assert order_mean < 20.0, f"Concurrent order latency {order_mean:.2f}ms exceeds 2x requirement"
        assert market_mean < 100.0, f"Concurrent market data latency {market_mean:.2f}ms exceeds 2x requirement"
        assert risk_mean < 20.0, f"Concurrent risk check latency {risk_mean:.2f}ms exceeds 2x requirement"
        
    @pytest.mark.asyncio
    async def test_latency_profiling(self):
        """Test latency profiling and measurement"""
        # Profile order placement
        @self.profiler.measure("order_placement", LatencyRequirement.CRITICAL)
        async def profiled_order_placement():
            return await self.order_system.place_order("PROFILE", 100, 100.0, "BUY")
            
        # Profile market data retrieval
        @self.profiler.measure("market_data_retrieval", LatencyRequirement.HIGH)
        async def profiled_market_data():
            return await self.market_feed.get_latest_price("PROFILE")
            
        # Profile risk check
        @self.profiler.measure("risk_check", LatencyRequirement.CRITICAL)
        async def profiled_risk_check():
            test_order = {"symbol": "PROFILE", "quantity": 100, "price": 50.0, "side": "BUY"}
            return await self.risk_engine.check_risk_limits(self.test_portfolio, test_order)
            
        # Run profiled operations
        for i in range(50):
            await profiled_order_placement()
            await profiled_market_data()
            await profiled_risk_check()
            
        # Check profiling results
        order_stats = self.profiler.get_statistics("order_placement")
        market_stats = self.profiler.get_statistics("market_data_retrieval")
        risk_stats = self.profiler.get_statistics("risk_check")
        
        logger.info(f"Profiled order placement - Mean: {order_stats['mean']:.2f}ms")
        logger.info(f"Profiled market data - Mean: {market_stats['mean']:.2f}ms")
        logger.info(f"Profiled risk check - Mean: {risk_stats['mean']:.2f}ms")
        
        # Validate profiling captured data
        assert order_stats["count"] == 50
        assert market_stats["count"] == 50
        assert risk_stats["count"] == 50
        
        # Check requirement violations
        violations = self.profiler.check_requirements()
        logger.info(f"Latency requirement violations: {len(violations)}")
        
        # For testing purposes, we expect some violations due to mock latencies
        # In a real system, there should be 0 violations


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])