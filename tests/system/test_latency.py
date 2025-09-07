#!/usr/bin/env python3
"""
Latency Testing System
System tests for measuring and validating latency across different components and operations.
"""

import pytest
import asyncio
import time
import statistics
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, field
import uuid
import random
from decimal import Decimal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import psutil
import gc
from collections import defaultdict, deque
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LatencyType(Enum):
    """Latency measurement types"""
    ORDER_PLACEMENT = "order_placement"
    ORDER_EXECUTION = "order_execution"
    MARKET_DATA_FEED = "market_data_feed"
    RISK_CALCULATION = "risk_calculation"
    PORTFOLIO_UPDATE = "portfolio_update"
    DATABASE_QUERY = "database_query"
    API_RESPONSE = "api_response"
    NETWORK_ROUNDTRIP = "network_roundtrip"
    MEMORY_ACCESS = "memory_access"
    DISK_IO = "disk_io"


class LatencyTarget(Enum):
    """Latency targets in microseconds"""
    ULTRA_LOW = 100  # 100μs
    LOW = 1000  # 1ms
    MEDIUM = 10000  # 10ms
    HIGH = 100000  # 100ms
    ACCEPTABLE = 1000000  # 1s


@dataclass
class LatencyMeasurement:
    """Latency measurement data"""
    measurement_id: str
    latency_type: LatencyType
    start_time: float
    end_time: float
    duration_us: float  # Duration in microseconds
    operation: str
    component: str
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LatencyStatistics:
    """Latency statistics for a set of measurements"""
    measurement_count: int
    min_latency_us: float
    max_latency_us: float
    mean_latency_us: float
    median_latency_us: float
    p95_latency_us: float
    p99_latency_us: float
    std_dev_us: float
    success_rate: float
    target_compliance: Dict[LatencyTarget, float] = field(default_factory=dict)


class LatencyProfiler:
    """High-precision latency profiler"""
    
    def __init__(self):
        self.measurements = defaultdict(list)
        self.active_measurements = {}
        self.measurement_counter = 0
        
    def start_measurement(self, latency_type: LatencyType, operation: str, component: str, metadata: Dict[str, Any] = None) -> str:
        """Start a latency measurement"""
        measurement_id = f"{latency_type.value}_{self.measurement_counter}_{uuid.uuid4().hex[:8]}"
        self.measurement_counter += 1
        
        start_time = time.perf_counter()
        
        measurement = LatencyMeasurement(
            measurement_id=measurement_id,
            latency_type=latency_type,
            start_time=start_time,
            end_time=0,
            duration_us=0,
            operation=operation,
            component=component,
            metadata=metadata or {}
        )
        
        self.active_measurements[measurement_id] = measurement
        return measurement_id
        
    def end_measurement(self, measurement_id: str, success: bool = True, error_message: str = None) -> LatencyMeasurement:
        """End a latency measurement"""
        end_time = time.perf_counter()
        
        if measurement_id not in self.active_measurements:
            raise ValueError(f"Measurement {measurement_id} not found")
            
        measurement = self.active_measurements.pop(measurement_id)
        measurement.end_time = end_time
        measurement.duration_us = (end_time - measurement.start_time) * 1_000_000  # Convert to microseconds
        measurement.success = success
        measurement.error_message = error_message
        
        self.measurements[measurement.latency_type].append(measurement)
        
        return measurement
        
    def measure_sync(self, latency_type: LatencyType, operation: str, component: str, func: Callable, *args, **kwargs) -> Tuple[Any, LatencyMeasurement]:
        """Measure latency of a synchronous function"""
        measurement_id = self.start_measurement(latency_type, operation, component)
        
        try:
            result = func(*args, **kwargs)
            measurement = self.end_measurement(measurement_id, success=True)
            return result, measurement
        except Exception as e:
            measurement = self.end_measurement(measurement_id, success=False, error_message=str(e))
            raise e
            
    async def measure_async(self, latency_type: LatencyType, operation: str, component: str, coro) -> Tuple[Any, LatencyMeasurement]:
        """Measure latency of an asynchronous coroutine"""
        measurement_id = self.start_measurement(latency_type, operation, component)
        
        try:
            result = await coro
            measurement = self.end_measurement(measurement_id, success=True)
            return result, measurement
        except Exception as e:
            measurement = self.end_measurement(measurement_id, success=False, error_message=str(e))
            raise e
            
    def get_statistics(self, latency_type: LatencyType) -> Optional[LatencyStatistics]:
        """Get statistics for a latency type"""
        measurements = self.measurements.get(latency_type, [])
        
        if not measurements:
            return None
            
        durations = [m.duration_us for m in measurements]
        successful_measurements = [m for m in measurements if m.success]
        
        stats = LatencyStatistics(
            measurement_count=len(measurements),
            min_latency_us=min(durations),
            max_latency_us=max(durations),
            mean_latency_us=statistics.mean(durations),
            median_latency_us=statistics.median(durations),
            p95_latency_us=np.percentile(durations, 95),
            p99_latency_us=np.percentile(durations, 99),
            std_dev_us=statistics.stdev(durations) if len(durations) > 1 else 0,
            success_rate=len(successful_measurements) / len(measurements) * 100
        )
        
        # Calculate target compliance
        for target in LatencyTarget:
            compliant_count = sum(1 for d in durations if d <= target.value)
            stats.target_compliance[target] = compliant_count / len(durations) * 100
            
        return stats
        
    def get_all_statistics(self) -> Dict[LatencyType, LatencyStatistics]:
        """Get statistics for all latency types"""
        return {lt: self.get_statistics(lt) for lt in self.measurements.keys()}
        
    def clear_measurements(self, latency_type: LatencyType = None):
        """Clear measurements for a specific type or all types"""
        if latency_type:
            self.measurements[latency_type].clear()
        else:
            self.measurements.clear()
            
    def export_measurements(self, latency_type: LatencyType = None) -> List[Dict[str, Any]]:
        """Export measurements to dictionary format"""
        if latency_type:
            measurements = self.measurements.get(latency_type, [])
        else:
            measurements = []
            for measurement_list in self.measurements.values():
                measurements.extend(measurement_list)
                
        return [
            {
                'measurement_id': m.measurement_id,
                'latency_type': m.latency_type.value,
                'duration_us': m.duration_us,
                'operation': m.operation,
                'component': m.component,
                'success': m.success,
                'error_message': m.error_message,
                'metadata': m.metadata,
                'timestamp': m.timestamp.isoformat()
            }
            for m in measurements
        ]


class MockOrderSystem:
    """Mock order system for latency testing"""
    
    def __init__(self, base_latency_us: float = 500):
        self.base_latency_us = base_latency_us
        self.orders = {}
        self.order_counter = 0
        
    async def place_order(self, symbol: str, quantity: float, price: float) -> Dict[str, Any]:
        """Place an order with simulated latency"""
        # Simulate processing time
        processing_time = self.base_latency_us + random.uniform(-100, 100)
        await asyncio.sleep(processing_time / 1_000_000)  # Convert to seconds
        
        order_id = f"ORD_{self.order_counter:06d}"
        self.order_counter += 1
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'status': 'filled',
            'timestamp': datetime.now().isoformat()
        }
        
        self.orders[order_id] = order
        return order
        
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID with simulated latency"""
        # Simulate database lookup time
        time.sleep((self.base_latency_us / 2) / 1_000_000)
        return self.orders.get(order_id)
        
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order with simulated latency"""
        # Simulate cancellation processing time
        time.sleep(self.base_latency_us / 1_000_000)
        
        if order_id in self.orders:
            self.orders[order_id]['status'] = 'cancelled'
            return True
        return False


class MockMarketDataFeed:
    """Mock market data feed for latency testing"""
    
    def __init__(self, feed_latency_us: float = 200):
        self.feed_latency_us = feed_latency_us
        self.subscribers = []
        self.is_running = False
        self.data_counter = 0
        
    async def subscribe(self, callback: Callable):
        """Subscribe to market data feed"""
        self.subscribers.append(callback)
        
    async def start_feed(self):
        """Start market data feed"""
        self.is_running = True
        
        while self.is_running:
            # Generate market data
            market_data = {
                'symbol': 'TEST',
                'price': 100.0 + random.uniform(-5, 5),
                'volume': random.randint(1000, 10000),
                'timestamp': time.time_ns(),  # Nanosecond precision
                'sequence': self.data_counter
            }
            
            self.data_counter += 1
            
            # Simulate feed latency
            await asyncio.sleep(self.feed_latency_us / 1_000_000)
            
            # Notify subscribers
            for callback in self.subscribers:
                try:
                    await callback(market_data)
                except Exception as e:
                    logger.error(f"Error in market data callback: {e}")
                    
            # Feed frequency (1000 updates per second)
            await asyncio.sleep(0.001)
            
    def stop_feed(self):
        """Stop market data feed"""
        self.is_running = False


class MockRiskEngine:
    """Mock risk engine for latency testing"""
    
    def __init__(self, calculation_latency_us: float = 300):
        self.calculation_latency_us = calculation_latency_us
        self.risk_limits = {
            'max_position_size': 1000000,
            'max_leverage': 10.0,
            'max_var': 50000
        }
        
    async def calculate_risk(self, portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate portfolio risk with simulated latency"""
        # Simulate complex risk calculations
        calculation_time = self.calculation_latency_us + random.uniform(-50, 50)
        await asyncio.sleep(calculation_time / 1_000_000)
        
        # Mock risk calculations
        total_value = sum(pos.get('value', 0) for pos in portfolio.get('positions', []))
        var_95 = total_value * 0.02  # 2% VaR
        leverage = total_value / portfolio.get('cash', 1)
        
        return {
            'total_value': total_value,
            'var_95': var_95,
            'leverage': leverage,
            'risk_score': min(100, var_95 / 1000),
            'timestamp': datetime.now().isoformat()
        }
        
    def validate_order(self, order: Dict[str, Any], portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """Validate order against risk limits"""
        # Simulate validation latency
        time.sleep(self.calculation_latency_us / 2 / 1_000_000)
        
        order_value = order.get('quantity', 0) * order.get('price', 0)
        portfolio_value = sum(pos.get('value', 0) for pos in portfolio.get('positions', []))
        
        violations = []
        
        if order_value > self.risk_limits['max_position_size']:
            violations.append('Position size exceeds limit')
            
        if portfolio_value > 0 and order_value / portfolio_value > 0.1:
            violations.append('Order size too large relative to portfolio')
            
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'risk_score': len(violations) * 25
        }


class MockDatabase:
    """Mock database for latency testing"""
    
    def __init__(self, query_latency_us: float = 1000):
        self.query_latency_us = query_latency_us
        self.data = {}
        self.query_counter = 0
        
    async def query(self, sql: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """Execute database query with simulated latency"""
        self.query_counter += 1
        
        # Simulate query execution time based on complexity
        base_latency = self.query_latency_us
        
        if 'JOIN' in sql.upper():
            base_latency *= 2
        if 'ORDER BY' in sql.upper():
            base_latency *= 1.5
        if 'GROUP BY' in sql.upper():
            base_latency *= 1.3
            
        query_time = base_latency + random.uniform(-200, 200)
        await asyncio.sleep(query_time / 1_000_000)
        
        # Mock query results
        if 'SELECT' in sql.upper():
            return [
                {'id': i, 'value': f'result_{i}', 'timestamp': datetime.now().isoformat()}
                for i in range(random.randint(1, 10))
            ]
        else:
            return [{'affected_rows': 1}]
            
    def execute(self, sql: str, params: List[Any] = None) -> int:
        """Execute database command with simulated latency"""
        # Simulate execution time
        time.sleep(self.query_latency_us / 1_000_000)
        return 1


class TestLatencySystem:
    """Test suite for latency measurements and validation"""
    
    @pytest.fixture(autouse=True)
    async def setup_method(self):
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
    async def test_order_placement_latency(self):
        """Test order placement latency"""
        num_orders = 100
        
        for i in range(num_orders):
            measurement_id = self.profiler.start_measurement(
                LatencyType.ORDER_PLACEMENT,
                "place_market_order",
                "order_system"
            )
            
            try:
                await self.order_system.place_order("AAPL", 100, 150.0)
                self.profiler.end_measurement(measurement_id, success=True)
            except Exception as e:
                self.profiler.end_measurement(measurement_id, success=False, error_message=str(e))
                
        # Analyze results
        stats = self.profiler.get_statistics(LatencyType.ORDER_PLACEMENT)
        
        assert stats is not None
        assert stats.measurement_count == num_orders
        assert stats.success_rate >= 95.0  # At least 95% success rate
        assert stats.p95_latency_us <= LatencyTarget.LOW.value  # P95 should be under 1ms
        assert stats.mean_latency_us <= 700  # Mean should be around base latency
        
        logger.info(f"Order placement latency - Mean: {stats.mean_latency_us:.1f}μs, P95: {stats.p95_latency_us:.1f}μs")
        
    @pytest.mark.asyncio
    async def test_market_data_feed_latency(self):
        """Test market data feed latency"""
        received_data = []
        latency_measurements = []
        
        async def data_callback(market_data):
            receive_time = time.time_ns()
            send_time = market_data['timestamp']
            latency_ns = receive_time - send_time
            latency_us = latency_ns / 1000
            
            latency_measurements.append(latency_us)
            received_data.append(market_data)
            
        # Subscribe to feed
        await self.market_feed.subscribe(data_callback)
        
        # Start feed and collect data for 1 second
        feed_task = asyncio.create_task(self.market_feed.start_feed())
        await asyncio.sleep(1.0)
        self.market_feed.stop_feed()
        
        try:
            await asyncio.wait_for(feed_task, timeout=1.0)
        except asyncio.TimeoutError:
            pass
            
        # Analyze latency
        assert len(received_data) > 0
        assert len(latency_measurements) > 0
        
        mean_latency = statistics.mean(latency_measurements)
        p95_latency = np.percentile(latency_measurements, 95)
        
        assert mean_latency <= LatencyTarget.LOW.value  # Mean under 1ms
        assert p95_latency <= LatencyTarget.MEDIUM.value  # P95 under 10ms
        
        logger.info(f"Market data feed latency - Mean: {mean_latency:.1f}μs, P95: {p95_latency:.1f}μs")
        logger.info(f"Received {len(received_data)} market data updates")
        
    @pytest.mark.asyncio
    async def test_risk_calculation_latency(self):
        """Test risk calculation latency"""
        num_calculations = 50
        
        for i in range(num_calculations):
            # Modify portfolio slightly for each calculation
            test_portfolio = self.test_portfolio.copy()
            test_portfolio['positions'][0]['value'] += random.uniform(-1000, 1000)
            
            result, measurement = await self.profiler.measure_async(
                LatencyType.RISK_CALCULATION,
                "calculate_portfolio_risk",
                "risk_engine",
                self.risk_engine.calculate_risk(test_portfolio)
            )
            
            assert 'risk_score' in result
            assert measurement.success
            
        # Analyze results
        stats = self.profiler.get_statistics(LatencyType.RISK_CALCULATION)
        
        assert stats.measurement_count == num_calculations
        assert stats.success_rate == 100.0
        assert stats.p95_latency_us <= LatencyTarget.LOW.value  # P95 under 1ms
        assert stats.mean_latency_us <= 400  # Mean should be around base latency
        
        logger.info(f"Risk calculation latency - Mean: {stats.mean_latency_us:.1f}μs, P95: {stats.p95_latency_us:.1f}μs")
        
    @pytest.mark.asyncio
    async def test_database_query_latency(self):
        """Test database query latency"""
        queries = [
            "SELECT * FROM orders WHERE symbol = 'AAPL'",
            "SELECT * FROM positions JOIN portfolios ON positions.portfolio_id = portfolios.id",
            "SELECT symbol, SUM(quantity) FROM trades GROUP BY symbol ORDER BY SUM(quantity) DESC",
            "INSERT INTO orders (symbol, quantity, price) VALUES ('MSFT', 100, 300.0)",
            "UPDATE positions SET quantity = 150 WHERE symbol = 'GOOGL'"
        ]
        
        for query in queries:
            result, measurement = await self.profiler.measure_async(
                LatencyType.DATABASE_QUERY,
                f"execute_query",
                "database",
                self.database.query(query)
            )
            
            assert measurement.success
            assert isinstance(result, list)
            
        # Analyze results
        stats = self.profiler.get_statistics(LatencyType.DATABASE_QUERY)
        
        assert stats.measurement_count == len(queries)
        assert stats.success_rate == 100.0
        assert stats.p95_latency_us <= LatencyTarget.HIGH.value  # P95 under 100ms
        
        logger.info(f"Database query latency - Mean: {stats.mean_latency_us:.1f}μs, P95: {stats.p95_latency_us:.1f}μs")
        
    @pytest.mark.asyncio
    async def test_concurrent_operations_latency(self):
        """Test latency under concurrent load"""
        num_concurrent = 20
        operations_per_task = 10
        
        async def order_task():
            for i in range(operations_per_task):
                measurement_id = self.profiler.start_measurement(
                    LatencyType.ORDER_EXECUTION,
                    "concurrent_order",
                    "order_system"
                )
                
                try:
                    await self.order_system.place_order(f"STOCK_{i}", 100, 100.0)
                    self.profiler.end_measurement(measurement_id, success=True)
                except Exception as e:
                    self.profiler.end_measurement(measurement_id, success=False, error_message=str(e))
                    
        async def risk_task():
            for i in range(operations_per_task):
                measurement_id = self.profiler.start_measurement(
                    LatencyType.RISK_CALCULATION,
                    "concurrent_risk",
                    "risk_engine"
                )
                
                try:
                    await self.risk_engine.calculate_risk(self.test_portfolio)
                    self.profiler.end_measurement(measurement_id, success=True)
                except Exception as e:
                    self.profiler.end_measurement(measurement_id, success=False, error_message=str(e))
                    
        # Create concurrent tasks
        tasks = []
        for i in range(num_concurrent // 2):
            tasks.append(asyncio.create_task(order_task()))
            tasks.append(asyncio.create_task(risk_task()))
            
        # Execute all tasks concurrently
        start_time = time.time()
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Analyze results
        order_stats = self.profiler.get_statistics(LatencyType.ORDER_EXECUTION)
        risk_stats = self.profiler.get_statistics(LatencyType.RISK_CALCULATION)
        
        assert order_stats.measurement_count == (num_concurrent // 2) * operations_per_task
        assert risk_stats.measurement_count == (num_concurrent // 2) * operations_per_task
        
        # Under concurrent load, latency should not degrade significantly
        assert order_stats.p95_latency_us <= LatencyTarget.MEDIUM.value  # P95 under 10ms
        assert risk_stats.p95_latency_us <= LatencyTarget.MEDIUM.value  # P95 under 10ms
        
        total_operations = order_stats.measurement_count + risk_stats.measurement_count
        throughput = total_operations / total_time
        
        logger.info(f"Concurrent operations completed in {total_time:.2f}s")
        logger.info(f"Throughput: {throughput:.1f} operations/second")
        logger.info(f"Order latency under load - P95: {order_stats.p95_latency_us:.1f}μs")
        logger.info(f"Risk calculation latency under load - P95: {risk_stats.p95_latency_us:.1f}μs")
        
    @pytest.mark.asyncio
    async def test_memory_access_latency(self):
        """Test memory access latency patterns"""
        # Create large data structures to test memory access patterns
        large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(10000)}
        large_list = [random.random() for _ in range(100000)]
        
        # Test dictionary access
        for i in range(1000):
            key = f"key_{random.randint(0, 9999)}"
            
            measurement_id = self.profiler.start_measurement(
                LatencyType.MEMORY_ACCESS,
                "dict_lookup",
                "memory"
            )
            
            value = large_dict.get(key)
            self.profiler.end_measurement(measurement_id, success=value is not None)
            
        # Test list access
        for i in range(1000):
            index = random.randint(0, 99999)
            
            measurement_id = self.profiler.start_measurement(
                LatencyType.MEMORY_ACCESS,
                "list_access",
                "memory"
            )
            
            value = large_list[index]
            self.profiler.end_measurement(measurement_id, success=True)
            
        # Analyze results
        stats = self.profiler.get_statistics(LatencyType.MEMORY_ACCESS)
        
        assert stats.measurement_count == 2000
        assert stats.success_rate >= 99.0
        assert stats.p95_latency_us <= LatencyTarget.ULTRA_LOW.value  # Memory access should be very fast
        
        logger.info(f"Memory access latency - Mean: {stats.mean_latency_us:.3f}μs, P95: {stats.p95_latency_us:.3f}μs")
        
    @pytest.mark.asyncio
    async def test_latency_percentiles_and_distribution(self):
        """Test latency distribution and percentile calculations"""
        # Generate measurements with known distribution
        base_latency = 1000  # 1ms base
        num_measurements = 1000
        
        for i in range(num_measurements):
            # Create bimodal distribution (fast and slow operations)
            if i < num_measurements * 0.9:  # 90% fast operations
                latency = base_latency + random.uniform(-100, 100)
            else:  # 10% slow operations
                latency = base_latency * 5 + random.uniform(-500, 500)
                
            measurement_id = self.profiler.start_measurement(
                LatencyType.API_RESPONSE,
                "test_operation",
                "test_component"
            )
            
            # Simulate operation
            await asyncio.sleep(latency / 1_000_000)
            
            self.profiler.end_measurement(measurement_id, success=True)
            
        # Analyze distribution
        stats = self.profiler.get_statistics(LatencyType.API_RESPONSE)
        
        assert stats.measurement_count == num_measurements
        assert stats.success_rate == 100.0
        
        # Verify percentile relationships
        assert stats.min_latency_us < stats.median_latency_us
        assert stats.median_latency_us < stats.p95_latency_us
        assert stats.p95_latency_us < stats.p99_latency_us
        assert stats.p99_latency_us <= stats.max_latency_us
        
        # Check target compliance
        assert LatencyTarget.ULTRA_LOW in stats.target_compliance
        assert LatencyTarget.LOW in stats.target_compliance
        assert LatencyTarget.MEDIUM in stats.target_compliance
        
        # Most operations should meet the medium target (10ms)
        assert stats.target_compliance[LatencyTarget.MEDIUM] >= 90.0
        
        logger.info(f"Latency distribution analysis:")
        logger.info(f"  Min: {stats.min_latency_us:.1f}μs")
        logger.info(f"  Median: {stats.median_latency_us:.1f}μs")
        logger.info(f"  P95: {stats.p95_latency_us:.1f}μs")
        logger.info(f"  P99: {stats.p99_latency_us:.1f}μs")
        logger.info(f"  Max: {stats.max_latency_us:.1f}μs")
        logger.info(f"  Target compliance (10ms): {stats.target_compliance[LatencyTarget.MEDIUM]:.1f}%")
        
    @pytest.mark.asyncio
    async def test_latency_regression_detection(self):
        """Test detection of latency regressions"""
        # Baseline measurements
        baseline_latency = 500  # 500μs baseline
        
        for i in range(100):
            measurement_id = self.profiler.start_measurement(
                LatencyType.ORDER_PLACEMENT,
                "baseline_order",
                "order_system"
            )
            
            await asyncio.sleep((baseline_latency + random.uniform(-50, 50)) / 1_000_000)
            self.profiler.end_measurement(measurement_id, success=True)
            
        baseline_stats = self.profiler.get_statistics(LatencyType.ORDER_PLACEMENT)
        baseline_p95 = baseline_stats.p95_latency_us
        
        # Clear measurements for regression test
        self.profiler.clear_measurements(LatencyType.ORDER_PLACEMENT)
        
        # Simulate regression (2x slower)
        regressed_latency = baseline_latency * 2
        
        for i in range(100):
            measurement_id = self.profiler.start_measurement(
                LatencyType.ORDER_PLACEMENT,
                "regressed_order",
                "order_system"
            )
            
            await asyncio.sleep((regressed_latency + random.uniform(-100, 100)) / 1_000_000)
            self.profiler.end_measurement(measurement_id, success=True)
            
        regressed_stats = self.profiler.get_statistics(LatencyType.ORDER_PLACEMENT)
        regressed_p95 = regressed_stats.p95_latency_us
        
        # Detect regression
        regression_ratio = regressed_p95 / baseline_p95
        regression_threshold = 1.5  # 50% increase threshold
        
        assert regression_ratio > regression_threshold
        
        logger.info(f"Latency regression detected:")
        logger.info(f"  Baseline P95: {baseline_p95:.1f}μs")
        logger.info(f"  Regressed P95: {regressed_p95:.1f}μs")
        logger.info(f"  Regression ratio: {regression_ratio:.2f}x")
        
    @pytest.mark.asyncio
    async def test_system_resource_impact_on_latency(self):
        """Test how system resource usage affects latency"""
        # Measure baseline latency
        baseline_measurements = []
        
        for i in range(50):
            measurement_id = self.profiler.start_measurement(
                LatencyType.ORDER_PLACEMENT,
                "baseline_resource_test",
                "order_system"
            )
            
            await self.order_system.place_order("TEST", 100, 100.0)
            measurement = self.profiler.end_measurement(measurement_id, success=True)
            baseline_measurements.append(measurement.duration_us)
            
        baseline_mean = statistics.mean(baseline_measurements)
        
        # Create CPU load
        def cpu_intensive_task():
            # Simulate CPU-intensive work
            for _ in range(1000000):
                _ = sum(range(100))
                
        # Measure latency under CPU load
        cpu_load_measurements = []
        
        # Start CPU load in background
        with ThreadPoolExecutor(max_workers=2) as executor:
            cpu_futures = [executor.submit(cpu_intensive_task) for _ in range(2)]
            
            for i in range(50):
                measurement_id = self.profiler.start_measurement(
                    LatencyType.ORDER_PLACEMENT,
                    "cpu_load_test",
                    "order_system"
                )
                
                await self.order_system.place_order("TEST", 100, 100.0)
                measurement = self.profiler.end_measurement(measurement_id, success=True)
                cpu_load_measurements.append(measurement.duration_us)
                
            # Wait for CPU tasks to complete
            for future in cpu_futures:
                future.result()
                
        cpu_load_mean = statistics.mean(cpu_load_measurements)
        
        # Analyze impact
        latency_increase = (cpu_load_mean - baseline_mean) / baseline_mean * 100
        
        logger.info(f"System resource impact on latency:")
        logger.info(f"  Baseline mean latency: {baseline_mean:.1f}μs")
        logger.info(f"  CPU load mean latency: {cpu_load_mean:.1f}μs")
        logger.info(f"  Latency increase: {latency_increase:.1f}%")
        
        # Latency should not increase by more than 100% under moderate CPU load
        assert latency_increase < 100.0
        
    @pytest.mark.asyncio
    async def test_latency_monitoring_and_alerting(self):
        """Test latency monitoring and alerting thresholds"""
        # Define SLA thresholds
        sla_thresholds = {
            LatencyType.ORDER_PLACEMENT: LatencyTarget.LOW.value,  # 1ms
            LatencyType.RISK_CALCULATION: LatencyTarget.LOW.value,  # 1ms
            LatencyType.DATABASE_QUERY: LatencyTarget.HIGH.value,  # 100ms
        }
        
        violations = []
        
        # Test order placement
        for i in range(20):
            measurement_id = self.profiler.start_measurement(
                LatencyType.ORDER_PLACEMENT,
                "sla_test_order",
                "order_system"
            )
            
            # Occasionally simulate slow operations
            if i % 10 == 0:  # 10% slow operations
                await asyncio.sleep(0.002)  # 2ms delay (violates 1ms SLA)
                
            await self.order_system.place_order("TEST", 100, 100.0)
            measurement = self.profiler.end_measurement(measurement_id, success=True)
            
            # Check SLA violation
            if measurement.duration_us > sla_thresholds[LatencyType.ORDER_PLACEMENT]:
                violations.append({
                    'type': LatencyType.ORDER_PLACEMENT,
                    'measurement_id': measurement.measurement_id,
                    'latency_us': measurement.duration_us,
                    'threshold_us': sla_thresholds[LatencyType.ORDER_PLACEMENT]
                })
                
        # Test risk calculations
        for i in range(20):
            measurement_id = self.profiler.start_measurement(
                LatencyType.RISK_CALCULATION,
                "sla_test_risk",
                "risk_engine"
            )
            
            await self.risk_engine.calculate_risk(self.test_portfolio)
            measurement = self.profiler.end_measurement(measurement_id, success=True)
            
            if measurement.duration_us > sla_thresholds[LatencyType.RISK_CALCULATION]:
                violations.append({
                    'type': LatencyType.RISK_CALCULATION,
                    'measurement_id': measurement.measurement_id,
                    'latency_us': measurement.duration_us,
                    'threshold_us': sla_thresholds[LatencyType.RISK_CALCULATION]
                })
                
        # Analyze SLA compliance
        order_stats = self.profiler.get_statistics(LatencyType.ORDER_PLACEMENT)
        risk_stats = self.profiler.get_statistics(LatencyType.RISK_CALCULATION)
        
        order_violations = [v for v in violations if v['type'] == LatencyType.ORDER_PLACEMENT]
        risk_violations = [v for v in violations if v['type'] == LatencyType.RISK_CALCULATION]
        
        order_sla_compliance = (1 - len(order_violations) / order_stats.measurement_count) * 100
        risk_sla_compliance = (1 - len(risk_violations) / risk_stats.measurement_count) * 100
        
        logger.info(f"SLA compliance analysis:")
        logger.info(f"  Order placement SLA compliance: {order_sla_compliance:.1f}%")
        logger.info(f"  Risk calculation SLA compliance: {risk_sla_compliance:.1f}%")
        logger.info(f"  Total violations: {len(violations)}")
        
        # Should have some violations due to simulated slow operations
        assert len(order_violations) > 0  # We simulated violations
        assert order_sla_compliance < 100.0  # Not perfect due to simulated issues
        assert order_sla_compliance > 80.0  # But still mostly compliant
        
    @pytest.mark.asyncio
    async def test_end_to_end_latency_workflow(self):
        """Test complete end-to-end latency measurement workflow"""
        # Simulate complete trading workflow with latency measurement
        workflow_steps = [
            ("market_data_receive", LatencyType.MARKET_DATA_FEED),
            ("risk_validation", LatencyType.RISK_CALCULATION),
            ("order_placement", LatencyType.ORDER_PLACEMENT),
            ("portfolio_update", LatencyType.PORTFOLIO_UPDATE),
            ("database_persist", LatencyType.DATABASE_QUERY)
        ]
        
        num_workflows = 10
        workflow_latencies = []
        
        for workflow_id in range(num_workflows):
            workflow_start = time.perf_counter()
            step_measurements = []
            
            for step_name, latency_type in workflow_steps:
                measurement_id = self.profiler.start_measurement(
                    latency_type,
                    step_name,
                    "workflow",
                    metadata={'workflow_id': workflow_id}
                )
                
                # Simulate each step
                if latency_type == LatencyType.MARKET_DATA_FEED:
                    await asyncio.sleep(0.0002)  # 200μs
                elif latency_type == LatencyType.RISK_CALCULATION:
                    await self.risk_engine.calculate_risk(self.test_portfolio)
                elif latency_type == LatencyType.ORDER_PLACEMENT:
                    await self.order_system.place_order("WORKFLOW_TEST", 100, 100.0)
                elif latency_type == LatencyType.PORTFOLIO_UPDATE:
                    await asyncio.sleep(0.0001)  # 100μs
                elif latency_type == LatencyType.DATABASE_QUERY:
                    await self.database.query("INSERT INTO trades VALUES (...)")
                    
                measurement = self.profiler.end_measurement(measurement_id, success=True)
                step_measurements.append(measurement)
                
            workflow_end = time.perf_counter()
            total_workflow_latency = (workflow_end - workflow_start) * 1_000_000  # Convert to μs
            workflow_latencies.append(total_workflow_latency)
            
        # Analyze end-to-end latency
        mean_workflow_latency = statistics.mean(workflow_latencies)
        p95_workflow_latency = np.percentile(workflow_latencies, 95)
        
        # Get statistics for each step
        step_stats = {}
        for step_name, latency_type in workflow_steps:
            stats = self.profiler.get_statistics(latency_type)
            if stats:
                step_stats[step_name] = stats
                
        logger.info(f"End-to-end workflow latency analysis:")
        logger.info(f"  Mean workflow latency: {mean_workflow_latency:.1f}μs")
        logger.info(f"  P95 workflow latency: {p95_workflow_latency:.1f}μs")
        
        for step_name, stats in step_stats.items():
            logger.info(f"  {step_name} - Mean: {stats.mean_latency_us:.1f}μs, P95: {stats.p95_latency_us:.1f}μs")
            
        # Verify workflow performance
        assert mean_workflow_latency <= LatencyTarget.MEDIUM.value  # Total workflow under 10ms
        assert p95_workflow_latency <= LatencyTarget.HIGH.value  # P95 under 100ms
        
        # Verify all steps completed successfully
        for stats in step_stats.values():
            assert stats.success_rate == 100.0
            
        # Export measurements for analysis
        all_measurements = self.profiler.export_measurements()
        assert len(all_measurements) > 0
        
        logger.info(f"Exported {len(all_measurements)} latency measurements")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])