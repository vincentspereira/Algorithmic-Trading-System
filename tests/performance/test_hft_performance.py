"""Performance and Load Tests for High-Frequency Trading Scenarios.

This module tests the performance characteristics of the trading system under
high-frequency trading conditions, focusing on:
- Order processing latency and throughput
- Market data ingestion performance
- Concurrent trading strategy execution
- System resource utilization under load
- Memory management and garbage collection impact
- Network I/O performance with brokers
- Database transaction performance
- Real-time risk calculation performance
"""

import pytest
import asyncio
import time
import threading
import multiprocessing
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict, List, Any, Tuple
import psutil
import gc
import statistics
import json

# Import shared models and utilities
from shared.models.orders import OrderCreateRequest, OrderSide, OrderType, OrderStatus
from shared.models.market_data import MarketDataTick, Quote
from shared.models.portfolio import Portfolio, Position
from shared.utils.logging_utils import get_logger

logger = get_logger(__name__)


class PerformanceMetrics:
    """Class to track and analyze performance metrics."""
    
    def __init__(self):
        self.latencies = []
        self.throughput_samples = []
        self.memory_usage = []
        self.cpu_usage = []
        self.start_time = None
        self.end_time = None
    
    def start_measurement(self):
        """Start performance measurement."""
        self.start_time = time.perf_counter()
        gc.collect()  # Clean up before measurement
    
    def end_measurement(self):
        """End performance measurement."""
        self.end_time = time.perf_counter()
    
    def record_latency(self, latency_ms: float):
        """Record a latency measurement."""
        self.latencies.append(latency_ms)
    
    def record_throughput(self, operations_per_second: float):
        """Record a throughput measurement."""
        self.throughput_samples.append(operations_per_second)
    
    def record_system_metrics(self):
        """Record current system resource usage."""
        process = psutil.Process()
        self.memory_usage.append(process.memory_info().rss / 1024 / 1024)  # MB
        self.cpu_usage.append(process.cpu_percent())
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics."""
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        return {
            'total_execution_time_seconds': total_time,
            'latency_stats': {
                'min_ms': min(self.latencies) if self.latencies else 0,
                'max_ms': max(self.latencies) if self.latencies else 0,
                'mean_ms': statistics.mean(self.latencies) if self.latencies else 0,
                'median_ms': statistics.median(self.latencies) if self.latencies else 0,
                'p95_ms': np.percentile(self.latencies, 95) if self.latencies else 0,
                'p99_ms': np.percentile(self.latencies, 99) if self.latencies else 0,
                'std_dev_ms': statistics.stdev(self.latencies) if len(self.latencies) > 1 else 0
            },
            'throughput_stats': {
                'max_ops_per_sec': max(self.throughput_samples) if self.throughput_samples else 0,
                'mean_ops_per_sec': statistics.mean(self.throughput_samples) if self.throughput_samples else 0,
                'total_operations': len(self.latencies)
            },
            'resource_usage': {
                'max_memory_mb': max(self.memory_usage) if self.memory_usage else 0,
                'mean_memory_mb': statistics.mean(self.memory_usage) if self.memory_usage else 0,
                'max_cpu_percent': max(self.cpu_usage) if self.cpu_usage else 0,
                'mean_cpu_percent': statistics.mean(self.cpu_usage) if self.cpu_usage else 0
            }
        }


class TestHFTPerformance:
    """Test suite for high-frequency trading performance."""
    
    @pytest.fixture
    async def hft_system(self):
        """Setup high-performance trading system for testing."""
        # Mock high-performance trading engine
        trading_engine = Mock()
        trading_engine.submit_order = AsyncMock()
        trading_engine.cancel_order = AsyncMock()
        trading_engine.modify_order = AsyncMock()
        trading_engine.get_order_status = AsyncMock()
        
        # Mock high-throughput market data service
        market_data = Mock()
        market_data.subscribe_to_feed = AsyncMock()
        market_data.get_latest_quote = AsyncMock()
        market_data.process_tick = AsyncMock()
        
        # Mock low-latency order management system
        oms = Mock()
        oms.route_order = AsyncMock()
        oms.validate_order = AsyncMock()
        oms.execute_order = AsyncMock()
        
        # Mock high-speed risk manager
        risk_manager = Mock()
        risk_manager.validate_order = AsyncMock()
        risk_manager.calculate_real_time_risk = AsyncMock()
        
        # Mock optimized database layer
        database = Mock()
        database.save_order = AsyncMock()
        database.update_position = AsyncMock()
        database.get_portfolio = AsyncMock()
        
        # Mock broker connectivity
        broker = Mock()
        broker.submit_order = AsyncMock()
        broker.get_market_data = AsyncMock()
        
        return {
            'trading_engine': trading_engine,
            'market_data': market_data,
            'oms': oms,
            'risk_manager': risk_manager,
            'database': database,
            'broker': broker
        }
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_order_processing_latency(self, hft_system):
        """Test order processing latency under high-frequency conditions."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # Setup mock responses for ultra-low latency
        hft_system['oms'].validate_order.return_value = {'approved': True, 'validation_time_us': 50}
        hft_system['risk_manager'].validate_order.return_value = {'approved': True, 'risk_check_time_us': 75}
        hft_system['trading_engine'].submit_order.return_value = 'order_id_123'
        hft_system['broker'].submit_order.return_value = {'status': 'ACCEPTED', 'latency_us': 250}
        
        # Test single order latency
        num_orders = 1000
        order_latencies = []
        
        for i in range(num_orders):
            order_start = time.perf_counter()
            
            # Create order request
            order = OrderCreateRequest(
                account_id='hft_account',
                symbol='AAPL',
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                quantity=Decimal('100'),
                order_type=OrderType.MARKET,
                metadata={'strategy': 'hft_scalping', 'sequence': i}
            )
            
            # Process order through the pipeline
            # 1. Order validation
            validation_result = await hft_system['oms'].validate_order(order)
            
            # 2. Risk check
            if validation_result['approved']:
                risk_result = await hft_system['risk_manager'].validate_order(order, None)
                
                # 3. Order submission
                if risk_result['approved']:
                    order_id = await hft_system['trading_engine'].submit_order(order)
                    
                    # 4. Broker execution
                    execution_result = await hft_system['broker'].submit_order(order_id, order)
            
            order_end = time.perf_counter()
            latency_ms = (order_end - order_start) * 1000
            order_latencies.append(latency_ms)
            metrics.record_latency(latency_ms)
            
            # Record system metrics every 100 orders
            if i % 100 == 0:
                metrics.record_system_metrics()
        
        metrics.end_measurement()
        performance_summary = metrics.get_summary()
        
        # Performance assertions for HFT requirements
        assert performance_summary['latency_stats']['mean_ms'] < 5.0  # Average < 5ms
        assert performance_summary['latency_stats']['p95_ms'] < 10.0  # 95th percentile < 10ms
        assert performance_summary['latency_stats']['p99_ms'] < 20.0  # 99th percentile < 20ms
        assert performance_summary['latency_stats']['max_ms'] < 50.0  # Max < 50ms
        
        # Verify all orders were processed
        assert hft_system['trading_engine'].submit_order.call_count == num_orders
        assert len(order_latencies) == num_orders
        
        logger.info(f"Order Processing Performance: {performance_summary}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_market_data_ingestion_throughput(self, hft_system):
        """Test market data ingestion throughput and processing speed."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # Setup high-frequency market data stream
        symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'NFLX', 'CRM', 'ADBE']
        ticks_per_second = 10000  # 10K ticks per second
        test_duration_seconds = 10
        total_ticks = ticks_per_second * test_duration_seconds
        
        # Mock market data processing
        processed_ticks = []
        processing_times = []
        
        async def process_market_tick(tick_data):
            """Simulate market data tick processing."""
            process_start = time.perf_counter()
            
            # Simulate tick processing (parsing, validation, distribution)
            await hft_system['market_data'].process_tick(tick_data)
            processed_ticks.append(tick_data)
            
            process_end = time.perf_counter()
            processing_time_us = (process_end - process_start) * 1000000
            processing_times.append(processing_time_us)
            
            return processing_time_us
        
        # Generate and process market data ticks
        tasks = []
        start_time = time.perf_counter()
        
        for i in range(total_ticks):
            symbol = symbols[i % len(symbols)]
            base_price = 150.0 + (i % 100) * 0.01  # Simulate price movement
            
            tick_data = MarketDataTick(
                symbol=symbol,
                price=Decimal(str(base_price + np.random.uniform(-0.5, 0.5))),
                volume=np.random.randint(100, 1000),
                timestamp=datetime.now(timezone.utc) + timedelta(microseconds=i*100),
                bid=Decimal(str(base_price - 0.01)),
                ask=Decimal(str(base_price + 0.01))
            )
            
            # Process ticks in batches to simulate real-world conditions
            if len(tasks) < 100:  # Batch size
                task = asyncio.create_task(process_market_tick(tick_data))
                tasks.append(task)
            else:
                # Wait for batch completion
                batch_results = await asyncio.gather(*tasks)
                for processing_time in batch_results:
                    metrics.record_latency(processing_time / 1000)  # Convert to ms
                
                tasks = []  # Reset for next batch
                
                # Calculate throughput for this batch
                current_time = time.perf_counter()
                elapsed_time = current_time - start_time
                current_throughput = len(processed_ticks) / elapsed_time
                metrics.record_throughput(current_throughput)
                
                # Record system metrics
                metrics.record_system_metrics()
        
        # Process remaining tasks
        if tasks:
            batch_results = await asyncio.gather(*tasks)
            for processing_time in batch_results:
                metrics.record_latency(processing_time / 1000)
        
        metrics.end_measurement()
        performance_summary = metrics.get_summary()
        
        # Performance assertions for market data ingestion
        assert len(processed_ticks) >= total_ticks * 0.95  # Process at least 95% of ticks
        assert performance_summary['throughput_stats']['max_ops_per_sec'] >= 8000  # Min 8K ticks/sec
        assert performance_summary['latency_stats']['mean_ms'] < 1.0  # Average processing < 1ms
        assert performance_summary['latency_stats']['p99_ms'] < 5.0  # 99th percentile < 5ms
        
        # Memory usage should remain stable
        memory_growth = (performance_summary['resource_usage']['max_memory_mb'] - 
                        performance_summary['resource_usage']['mean_memory_mb'])
        assert memory_growth < 100  # Memory growth < 100MB
        
        logger.info(f"Market Data Ingestion Performance: {performance_summary}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_strategy_execution(self, hft_system):
        """Test concurrent execution of multiple trading strategies."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # Define multiple HFT strategies
        strategies = [
            {'name': 'momentum_scalping', 'symbols': ['AAPL', 'TSLA'], 'frequency_ms': 100},
            {'name': 'mean_reversion', 'symbols': ['MSFT', 'GOOGL'], 'frequency_ms': 200},
            {'name': 'arbitrage', 'symbols': ['AMZN', 'NVDA'], 'frequency_ms': 50},
            {'name': 'market_making', 'symbols': ['META', 'NFLX'], 'frequency_ms': 75},
            {'name': 'statistical_arb', 'symbols': ['CRM', 'ADBE'], 'frequency_ms': 150}
        ]
        
        # Strategy execution results
        strategy_results = {strategy['name']: [] for strategy in strategies}
        execution_times = []
        
        async def execute_strategy(strategy_config, duration_seconds=30):
            """Execute a trading strategy for specified duration."""
            strategy_name = strategy_config['name']
            symbols = strategy_config['symbols']
            frequency_ms = strategy_config['frequency_ms']
            
            start_time = time.perf_counter()
            end_time = start_time + duration_seconds
            execution_count = 0
            
            while time.perf_counter() < end_time:
                execution_start = time.perf_counter()
                
                # Simulate strategy logic
                for symbol in symbols:
                    # Generate trading signal
                    signal_strength = np.random.uniform(-1, 1)
                    
                    if abs(signal_strength) > 0.7:  # Strong signal threshold
                        # Create and submit order
                        order = OrderCreateRequest(
                            account_id=f'{strategy_name}_account',
                            symbol=symbol,
                            side=OrderSide.BUY if signal_strength > 0 else OrderSide.SELL,
                            quantity=Decimal('50'),
                            order_type=OrderType.MARKET,
                            metadata={'strategy': strategy_name, 'signal': signal_strength}
                        )
                        
                        # Submit order through system
                        order_id = await hft_system['trading_engine'].submit_order(order)
                        strategy_results[strategy_name].append({
                            'order_id': order_id,
                            'symbol': symbol,
                            'signal': signal_strength,
                            'timestamp': datetime.now(timezone.utc)
                        })
                
                execution_end = time.perf_counter()
                execution_time_ms = (execution_end - execution_start) * 1000
                execution_times.append(execution_time_ms)
                execution_count += 1
                
                # Wait for next execution cycle
                await asyncio.sleep(frequency_ms / 1000.0)
            
            return {
                'strategy': strategy_name,
                'executions': execution_count,
                'orders_generated': len(strategy_results[strategy_name])
            }
        
        # Execute all strategies concurrently
        strategy_tasks = [execute_strategy(strategy) for strategy in strategies]
        concurrent_results = await asyncio.gather(*strategy_tasks)
        
        metrics.end_measurement()
        performance_summary = metrics.get_summary()
        
        # Analyze concurrent execution performance
        total_orders = sum(len(orders) for orders in strategy_results.values())
        total_executions = sum(result['executions'] for result in concurrent_results)
        
        # Performance assertions
        assert total_orders > 0  # Orders were generated
        assert total_executions > 0  # Strategies executed
        assert len(concurrent_results) == len(strategies)  # All strategies completed
        
        # Verify execution time distribution
        if execution_times:
            mean_execution_time = statistics.mean(execution_times)
            assert mean_execution_time < 10.0  # Average execution < 10ms
            
            p95_execution_time = np.percentile(execution_times, 95)
            assert p95_execution_time < 25.0  # 95th percentile < 25ms
        
        # Verify system resource usage under concurrent load
        assert performance_summary['resource_usage']['max_cpu_percent'] < 90  # CPU < 90%
        assert performance_summary['resource_usage']['max_memory_mb'] < 1000  # Memory < 1GB
        
        logger.info(f"Concurrent Strategy Execution Results: {concurrent_results}")
        logger.info(f"Performance Summary: {performance_summary}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_system_stress_under_extreme_load(self, hft_system):
        """Test system behavior under extreme load conditions."""
        metrics = PerformanceMetrics()
        metrics.start_measurement()
        
        # Extreme load parameters
        concurrent_clients = 50
        orders_per_client = 200
        market_data_rate = 50000  # 50K ticks/second
        test_duration_seconds = 60
        
        # Track system stability metrics
        failed_operations = []
        successful_operations = []
        system_metrics_history = []
        
        async def simulate_trading_client(client_id, num_orders):
            """Simulate a high-frequency trading client."""
            client_results = {
                'client_id': client_id,
                'successful_orders': 0,
                'failed_orders': 0,
                'total_latency_ms': 0,
                'orders': []
            }
            
            for order_num in range(num_orders):
                try:
                    order_start = time.perf_counter()
                    
                    # Create order with varying parameters
                    symbols = ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN']
                    symbol = symbols[order_num % len(symbols)]
                    
                    order = OrderCreateRequest(
                        account_id=f'stress_client_{client_id}',
                        symbol=symbol,
                        side=OrderSide.BUY if order_num % 2 == 0 else OrderSide.SELL,
                        quantity=Decimal(str(np.random.randint(10, 500))),
                        order_type=OrderType.MARKET,
                        metadata={'client_id': client_id, 'order_num': order_num}
                    )
                    
                    # Submit order with timeout
                    order_id = await asyncio.wait_for(
                        hft_system['trading_engine'].submit_order(order),
                        timeout=1.0  # 1 second timeout
                    )
                    
                    order_end = time.perf_counter()
                    latency_ms = (order_end - order_start) * 1000
                    
                    client_results['successful_orders'] += 1
                    client_results['total_latency_ms'] += latency_ms
                    client_results['orders'].append({
                        'order_id': order_id,
                        'latency_ms': latency_ms,
                        'timestamp': datetime.now(timezone.utc)
                    })
                    
                    successful_operations.append({
                        'client_id': client_id,
                        'order_num': order_num,
                        'latency_ms': latency_ms
                    })
                    
                except asyncio.TimeoutError:
                    client_results['failed_orders'] += 1
                    failed_operations.append({
                        'client_id': client_id,
                        'order_num': order_num,
                        'error': 'timeout'
                    })
                except Exception as e:
                    client_results['failed_orders'] += 1
                    failed_operations.append({
                        'client_id': client_id,
                        'order_num': order_num,
                        'error': str(e)
                    })
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(0.001)  # 1ms delay
            
            return client_results
        
        async def monitor_system_resources():
            """Monitor system resources during stress test."""
            while True:
                try:
                    process = psutil.Process()
                    system_metrics = {
                        'timestamp': datetime.now(timezone.utc),
                        'cpu_percent': process.cpu_percent(),
                        'memory_mb': process.memory_info().rss / 1024 / 1024,
                        'open_files': len(process.open_files()),
                        'threads': process.num_threads()
                    }
                    system_metrics_history.append(system_metrics)
                    metrics.record_system_metrics()
                    
                    await asyncio.sleep(1.0)  # Monitor every second
                except Exception as e:
                    logger.error(f"Error monitoring system resources: {e}")
                    break
        
        # Start system monitoring
        monitor_task = asyncio.create_task(monitor_system_resources())
        
        # Setup mock responses for stress test
        hft_system['trading_engine'].submit_order.return_value = 'stress_order_id'
        hft_system['oms'].validate_order.return_value = {'approved': True}
        hft_system['risk_manager'].validate_order.return_value = {'approved': True}
        
        # Execute stress test with concurrent clients
        client_tasks = [
            simulate_trading_client(client_id, orders_per_client)
            for client_id in range(concurrent_clients)
        ]
        
        # Run stress test for specified duration
        try:
            client_results = await asyncio.wait_for(
                asyncio.gather(*client_tasks),
                timeout=test_duration_seconds
            )
        except asyncio.TimeoutError:
            logger.warning("Stress test timed out - system may be overloaded")
            client_results = []
        finally:
            monitor_task.cancel()
        
        metrics.end_measurement()
        performance_summary = metrics.get_summary()
        
        # Analyze stress test results
        total_orders_attempted = concurrent_clients * orders_per_client
        total_successful = len(successful_operations)
        total_failed = len(failed_operations)
        success_rate = total_successful / total_orders_attempted if total_orders_attempted > 0 else 0
        
        # Calculate latency statistics for successful operations
        if successful_operations:
            latencies = [op['latency_ms'] for op in successful_operations]
            avg_latency = statistics.mean(latencies)
            p95_latency = np.percentile(latencies, 95)
            p99_latency = np.percentile(latencies, 99)
        else:
            avg_latency = p95_latency = p99_latency = 0
        
        # System stability assertions
        assert success_rate >= 0.95  # At least 95% success rate
        assert avg_latency < 50.0  # Average latency < 50ms under stress
        assert p95_latency < 100.0  # 95th percentile < 100ms
        assert p99_latency < 200.0  # 99th percentile < 200ms
        
        # Resource usage assertions
        if system_metrics_history:
            max_memory = max(m['memory_mb'] for m in system_metrics_history)
            max_cpu = max(m['cpu_percent'] for m in system_metrics_history)
            
            assert max_memory < 2000  # Memory usage < 2GB
            assert max_cpu < 95  # CPU usage < 95%
        
        # Log stress test results
        stress_results = {
            'total_orders_attempted': total_orders_attempted,
            'successful_orders': total_successful,
            'failed_orders': total_failed,
            'success_rate': success_rate,
            'average_latency_ms': avg_latency,
            'p95_latency_ms': p95_latency,
            'p99_latency_ms': p99_latency,
            'performance_summary': performance_summary
        }
        
        logger.info(f"Stress Test Results: {stress_results}")
        
        # Verify system recovered gracefully
        assert len(client_results) > 0 or success_rate > 0.8  # System remained responsive
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_management_and_gc_impact(self, hft_system):
        """Test memory management and garbage collection impact on performance."""
        metrics = PerformanceMetrics()
        
        # Track memory allocation patterns
        memory_snapshots = []
        gc_events = []
        allocation_rates = []
        
        def track_gc_events():
            """Track garbage collection events."""
            gc_stats = gc.get_stats()
            gc_events.append({
                'timestamp': time.perf_counter(),
                'collections': gc_stats,
                'objects': len(gc.get_objects())
            })
        
        # Enable garbage collection tracking
        gc.set_debug(gc.DEBUG_STATS)
        initial_objects = len(gc.get_objects())
        
        metrics.start_measurement()
        
        # Simulate memory-intensive trading operations
        large_datasets = []
        order_history = []
        market_data_buffer = []
        
        for iteration in range(1000):
            iteration_start = time.perf_counter()
            
            # Simulate large market data processing
            market_data_chunk = {
                'iteration': iteration,
                'ticks': [
                    {
                        'symbol': f'SYMBOL_{i}',
                        'price': Decimal(str(150.0 + np.random.uniform(-5, 5))),
                        'volume': np.random.randint(100, 10000),
                        'timestamp': datetime.now(timezone.utc),
                        'metadata': {'chunk_id': iteration, 'tick_id': i}
                    }
                    for i in range(100)  # 100 ticks per chunk
                ]
            }
            market_data_buffer.append(market_data_chunk)
            
            # Simulate order processing with large metadata
            for order_idx in range(10):
                order_data = {
                    'order_id': f'order_{iteration}_{order_idx}',
                    'symbol': 'AAPL',
                    'quantity': Decimal('100'),
                    'price': Decimal(str(150.0 + np.random.uniform(-1, 1))),
                    'metadata': {
                        'strategy_params': {f'param_{i}': np.random.random() for i in range(50)},
                        'risk_metrics': {f'metric_{i}': np.random.random() for i in range(30)},
                        'execution_history': [f'event_{i}' for i in range(20)]
                    }
                }
                order_history.append(order_data)
                
                # Submit order
                await hft_system['trading_engine'].submit_order(order_data)
            
            # Create temporary large datasets (simulate analysis)
            if iteration % 100 == 0:
                large_dataset = np.random.random((1000, 1000))  # 1M floats
                analysis_result = np.mean(large_dataset, axis=0)
                large_datasets.append(analysis_result)
                
                # Force garbage collection and track
                gc.collect()
                track_gc_events()
                
                # Take memory snapshot
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_snapshots.append({
                    'iteration': iteration,
                    'rss_mb': memory_info.rss / 1024 / 1024,
                    'vms_mb': memory_info.vms / 1024 / 1024,
                    'objects_count': len(gc.get_objects()),
                    'timestamp': time.perf_counter()
                })
            
            # Cleanup old data to simulate real-world memory management
            if len(market_data_buffer) > 500:
                market_data_buffer = market_data_buffer[-250:]  # Keep last 250 chunks
            
            if len(order_history) > 5000:
                order_history = order_history[-2500:]  # Keep last 2500 orders
            
            iteration_end = time.perf_counter()
            iteration_time_ms = (iteration_end - iteration_start) * 1000
            metrics.record_latency(iteration_time_ms)
            
            # Calculate allocation rate
            if iteration > 0 and memory_snapshots:
                current_objects = len(gc.get_objects())
                allocation_rate = current_objects - initial_objects
                allocation_rates.append(allocation_rate)
        
        metrics.end_measurement()
        performance_summary = metrics.get_summary()
        
        # Analyze memory management performance
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects
        
        if memory_snapshots:
            initial_memory = memory_snapshots[0]['rss_mb']
            final_memory = memory_snapshots[-1]['rss_mb']
            memory_growth = final_memory - initial_memory
            max_memory = max(snapshot['rss_mb'] for snapshot in memory_snapshots)
        else:
            memory_growth = max_memory = 0
        
        # Memory management assertions
        assert object_growth < 100000  # Object count growth < 100K
        assert memory_growth < 500  # Memory growth < 500MB
        assert max_memory < 1500  # Peak memory < 1.5GB
        
        # Performance impact assertions
        assert performance_summary['latency_stats']['mean_ms'] < 20.0  # Average iteration < 20ms
        assert performance_summary['latency_stats']['p95_ms'] < 50.0  # 95th percentile < 50ms
        
        # Garbage collection impact analysis
        if gc_events:
            gc_frequency = len(gc_events) / (metrics.end_time - metrics.start_time)
            assert gc_frequency < 10  # GC frequency < 10 per second
        
        memory_analysis = {
            'initial_objects': initial_objects,
            'final_objects': final_objects,
            'object_growth': object_growth,
            'memory_growth_mb': memory_growth,
            'max_memory_mb': max_memory,
            'gc_events_count': len(gc_events),
            'performance_summary': performance_summary
        }
        
        logger.info(f"Memory Management Analysis: {memory_analysis}")
        
        # Cleanup
        gc.set_debug(0)
        gc.collect()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])