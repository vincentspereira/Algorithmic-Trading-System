"""
Performance benchmarking tests for strategy execution.

This module provides comprehensive performance benchmarks for:
- Strategy initialization and execution speed
- Memory usage optimization
- Concurrent strategy execution
- Large dataset processing
- Real-time performance requirements
"""

import pytest
import time
import asyncio
import threading
import psutil
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from unittest.mock import Mock
import gc
import cProfile
import pstats
import io
from contextlib import contextmanager

# Import strategy modules
from nautilus_trader_engine.strategies.core.base_strategy import (
    BaseStrategy, StrategyConfig, RiskParameters, Position, Signal,
    StrategyType, PositionSide, SignalType, SignalStrength, StrategyState
)
from nautilus_trader_engine.strategies.utils.strategy_utilities import (
    StrategyUtilities, DataValidation, PositionSizing
)
from nautilus_trader_engine.strategies.utils.performance_tracker import (
    PerformanceTracker, TradeMetrics
)
from nautilus_trader_engine.strategies.utils.signal_processing import (
    SignalProcessor, TradingSignal
)


class PerformanceBenchmarks:
    """Performance benchmarking utilities and test cases."""
    
    @staticmethod
    @contextmanager
    def measure_time():
        """Context manager to measure execution time."""
        start_time = time.perf_counter()
        yield
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time:.4f} seconds")
    
    @staticmethod
    @contextmanager
    def measure_memory():
        """Context manager to measure memory usage."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        yield
        final_memory = process.memory_info().rss
        memory_delta = final_memory - initial_memory
        print(f"Memory delta: {memory_delta / 1024 / 1024:.2f} MB")
    
    @staticmethod
    @contextmanager
    def profile_performance():
        """Context manager for detailed performance profiling."""
        profiler = cProfile.Profile()
        profiler.enable()
        yield profiler
        profiler.disable()
        
        # Print top 10 functions by cumulative time
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(10)
        print(s.getvalue())
    
    @staticmethod
    def generate_large_dataset(num_rows: int = 10000) -> pd.DataFrame:
        """Generate large market data for performance testing."""
        np.random.seed(42)
        dates = pd.date_range(start='2020-01-01', periods=num_rows, freq='1min')
        
        # Generate realistic price movements
        returns = np.random.normal(0.0001, 0.01, num_rows)
        prices = 100 * np.exp(np.cumsum(returns))
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices * (1 + np.random.normal(0, 0.0005, num_rows)),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.002, num_rows))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.002, num_rows))),
            'close': prices,
            'volume': np.random.randint(100, 10000, num_rows)
        })


class MockHighPerformanceStrategy(BaseStrategy):
    """Mock strategy optimized for performance testing."""
    
    def generate_signals(self, market_data: pd.DataFrame) -> list[Signal]:
        """Generate signals with minimal processing overhead."""
        if len(market_data) < 20:
            return []
        
        # Simple moving average crossover
        short_ma = market_data['close'].rolling(5).mean()
        long_ma = market_data['close'].rolling(20).mean()
        
        signals = []
        if len(short_ma) > 0 and len(long_ma) > 0:
            if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
                signals.append(Signal(
                    signal_type=SignalType.BUY,
                    strength=SignalStrength.MEDIUM,
                    price=Decimal(str(market_data['close'].iloc[-1])),
                    confidence=0.7,
                    timestamp=datetime.now()
                ))
            elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
                signals.append(Signal(
                    signal_type=SignalType.SELL,
                    strength=SignalStrength.MEDIUM,
                    price=Decimal(str(market_data['close'].iloc[-1])),
                    confidence=0.7,
                    timestamp=datetime.now()
                ))
        
        return signals
    
    def calculate_position_size(self, signal: Signal, account_balance: Decimal) -> Decimal:
        """Fast position size calculation."""
        return min(account_balance * Decimal('0.1'), Decimal('10000'))


class TestStrategyPerformanceBenchmarks:
    """Performance benchmark test cases."""
    
    @pytest.fixture
    def performance_config(self):
        """Create configuration optimized for performance testing."""
        return StrategyConfig(
            name="performance_test_strategy",
            strategy_type=StrategyType.MOMENTUM,
            risk_parameters=RiskParameters(
                max_position_size=Decimal('100000'),
                stop_loss_pct=Decimal('0.02'),
                take_profit_pct=Decimal('0.05'),
                max_daily_loss=Decimal('10000'),
                position_sizing=PositionSizing.FIXED
            ),
            parameters={'lookback_period': 20, 'threshold': 0.02}
        )
    
    @pytest.fixture
    def high_performance_strategy(self, performance_config):
        """Create high-performance strategy for testing."""
        return MockHighPerformanceStrategy(performance_config)
    
    def test_strategy_initialization_performance(self, performance_config):
        """Benchmark strategy initialization time."""
        with PerformanceBenchmarks.measure_time():
            with PerformanceBenchmarks.measure_memory():
                strategies = []
                for i in range(100):
                    config = StrategyConfig(
                        name=f"strategy_{i}",
                        strategy_type=StrategyType.MOMENTUM,
                        risk_parameters=performance_config.risk_parameters,
                        parameters=performance_config.parameters
                    )
                    strategy = MockHighPerformanceStrategy(config)
                    strategies.append(strategy)
        
        # Verify all strategies were created successfully
        assert len(strategies) == 100
        for strategy in strategies:
            assert strategy.state == StrategyState.INITIALIZED
    
    def test_signal_generation_performance(self, high_performance_strategy):
        """Benchmark signal generation with large datasets."""
        large_dataset = PerformanceBenchmarks.generate_large_dataset(50000)
        
        with PerformanceBenchmarks.measure_time():
            with PerformanceBenchmarks.measure_memory():
                signals = high_performance_strategy.generate_signals(large_dataset)
        
        # Verify signals were generated
        assert isinstance(signals, list)
        print(f"Generated {len(signals)} signals from {len(large_dataset)} data points")
    
    def test_position_calculation_performance(self, high_performance_strategy):
        """Benchmark position size calculations."""
        # Create test signals
        signals = []
        for i in range(1000):
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strength=SignalStrength.MEDIUM,
                price=Decimal(str(100 + i * 0.1)),
                confidence=0.7,
                timestamp=datetime.now()
            ))
        
        account_balance = Decimal('1000000')
        
        with PerformanceBenchmarks.measure_time():
            position_sizes = []
            for signal in signals:
                size = high_performance_strategy.calculate_position_size(signal, account_balance)
                position_sizes.append(size)
        
        assert len(position_sizes) == 1000
        assert all(size > 0 for size in position_sizes)
    
    def test_concurrent_strategy_execution(self, performance_config):
        """Benchmark concurrent strategy execution."""
        dataset = PerformanceBenchmarks.generate_large_dataset(10000)
        
        def execute_strategy(strategy_id: int):
            """Execute strategy in separate thread."""
            config = StrategyConfig(
                name=f"concurrent_strategy_{strategy_id}",
                strategy_type=StrategyType.MOMENTUM,
                risk_parameters=performance_config.risk_parameters,
                parameters=performance_config.parameters
            )
            strategy = MockHighPerformanceStrategy(config)
            signals = strategy.generate_signals(dataset)
            return len(signals)
        
        with PerformanceBenchmarks.measure_time():
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(execute_strategy, i) for i in range(10)]
                results = [future.result() for future in futures]
        
        assert len(results) == 10
        assert all(isinstance(result, int) for result in results)
        print(f"Concurrent execution results: {results}")
    
    def test_memory_efficiency_large_positions(self, high_performance_strategy):
        """Test memory efficiency with large number of positions."""
        initial_memory = psutil.Process().memory_info().rss
        
        # Create many positions
        positions = {}
        for i in range(10000):
            position = Position(
                symbol=f"STOCK_{i:04d}",
                side=PositionSide.LONG,
                size=Decimal('100'),
                entry_price=Decimal(str(100 + i * 0.01)),
                timestamp=datetime.now()
            )
            positions[f"STOCK_{i:04d}"] = position
        
        # Add positions to strategy
        high_performance_strategy.positions = positions
        
        final_memory = psutil.Process().memory_info().rss
        memory_per_position = (final_memory - initial_memory) / 10000
        
        print(f"Memory per position: {memory_per_position:.2f} bytes")
        assert memory_per_position < 1000  # Should be less than 1KB per position
        
        # Cleanup
        high_performance_strategy.positions.clear()
        gc.collect()
    
    def test_performance_tracker_efficiency(self):
        """Benchmark performance tracker with many trades."""
        tracker = PerformanceTracker()
        
        with PerformanceBenchmarks.measure_time():
            with PerformanceBenchmarks.measure_memory():
                # Record many trades
                for i in range(10000):
                    tracker.record_trade(
                        symbol=f"STOCK_{i % 100}",
                        entry_price=100.0 + (i % 50),
                        exit_price=101.0 + (i % 50),
                        quantity=100.0,
                        side="long" if i % 2 == 0 else "short",
                        entry_time=datetime.now() - timedelta(hours=i),
                        exit_time=datetime.now() - timedelta(hours=i-1),
                        pnl=1.0 * (1 if i % 2 == 0 else -1)
                    )
        
        # Verify performance summary calculation
        with PerformanceBenchmarks.measure_time():
            summary = tracker.get_performance_summary()
        
        assert summary.total_trades == 10000
        print(f"Performance summary calculation completed for {summary.total_trades} trades")
    
    def test_signal_processing_throughput(self):
        """Benchmark signal processing throughput."""
        processor = SignalProcessor()
        
        # Generate many signals
        signals = []
        for i in range(10000):
            signal = TradingSignal(
                signal_type=SignalType.BUY if i % 2 == 0 else SignalType.SELL,
                strength=SignalStrength.MEDIUM,
                price=100.0 + (i % 100) * 0.1,
                confidence=0.5 + (i % 50) * 0.01,
                timestamp=datetime.now() - timedelta(seconds=i),
                metadata={'source': f'generator_{i % 10}'}
            )
            signals.append(signal)
        
        with PerformanceBenchmarks.measure_time():
            # Process signals in batches
            batch_size = 1000
            results = []
            for i in range(0, len(signals), batch_size):
                batch = signals[i:i + batch_size]
                result = processor.aggregate_signals(batch)
                results.append(result)
        
        assert len(results) == 10
        print(f"Processed {len(signals)} signals in {len(results)} batches")
    
    def test_utility_functions_performance(self):
        """Benchmark utility function performance."""
        # Test position sizing performance
        with PerformanceBenchmarks.measure_time():
            for i in range(10000):
                size = StrategyUtilities.calculate_position_size(
                    account_balance=Decimal('100000'),
                    risk_per_trade=Decimal('0.02'),
                    entry_price=Decimal(str(100 + i * 0.01)),
                    stop_loss_price=Decimal(str(98 + i * 0.01))
                )
                assert size > 0
        
        # Test risk metrics performance
        returns_data = pd.Series(np.random.normal(0.001, 0.02, 10000))
        
        with PerformanceBenchmarks.measure_time():
            for _ in range(100):
                metrics = StrategyUtilities.calculate_risk_metrics(
                    returns=returns_data,
                    risk_free_rate=0.02
                )
                assert 'sharpe_ratio' in metrics
    
    def test_data_validation_performance(self):
        """Benchmark data validation performance."""
        large_dataset = PerformanceBenchmarks.generate_large_dataset(100000)
        
        with PerformanceBenchmarks.measure_time():
            # Validate large dataset multiple times
            for _ in range(10):
                is_valid = DataValidation.validate_price_data(large_dataset)
                assert is_valid
        
        print(f"Validated dataset with {len(large_dataset)} rows")
    
    @pytest.mark.asyncio
    async def test_async_performance(self, high_performance_strategy):
        """Benchmark asynchronous strategy operations."""
        dataset = PerformanceBenchmarks.generate_large_dataset(5000)
        
        async def async_signal_generation(data_chunk):
            """Generate signals asynchronously."""
            await asyncio.sleep(0.001)  # Simulate async I/O
            return high_performance_strategy.generate_signals(data_chunk)
        
        # Split dataset into chunks
        chunk_size = 1000
        chunks = [dataset[i:i + chunk_size] for i in range(0, len(dataset), chunk_size)]
        
        with PerformanceBenchmarks.measure_time():
            # Process chunks concurrently
            tasks = [async_signal_generation(chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks)
        
        total_signals = sum(len(signals) for signals in results)
        print(f"Generated {total_signals} signals from {len(chunks)} chunks asynchronously")
    
    def test_real_time_performance_requirements(self, high_performance_strategy):
        """Test real-time performance requirements."""
        # Simulate real-time data processing
        real_time_data = PerformanceBenchmarks.generate_large_dataset(1000)
        
        # Measure latency for single data point processing
        latencies = []
        for i in range(100):
            single_row_data = real_time_data.iloc[i:i+50]  # 50 data points
            
            start_time = time.perf_counter()
            signals = high_performance_strategy.generate_signals(single_row_data)
            end_time = time.perf_counter()
            
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            latencies.append(latency)
        
        avg_latency = np.mean(latencies)
        max_latency = np.max(latencies)
        p95_latency = np.percentile(latencies, 95)
        
        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"Max latency: {max_latency:.2f}ms")
        print(f"95th percentile latency: {p95_latency:.2f}ms")
        
        # Assert performance requirements
        assert avg_latency < 10.0  # Average should be under 10ms
        assert p95_latency < 50.0  # 95th percentile should be under 50ms
    
    def test_stress_testing(self, performance_config):
        """Stress test with extreme conditions."""
        # Create many strategies with large datasets
        strategies = []
        datasets = []
        
        for i in range(5):
            config = StrategyConfig(
                name=f"stress_strategy_{i}",
                strategy_type=StrategyType.MOMENTUM,
                risk_parameters=performance_config.risk_parameters,
                parameters=performance_config.parameters
            )
            strategy = MockHighPerformanceStrategy(config)
            strategies.append(strategy)
            
            # Large dataset for each strategy
            dataset = PerformanceBenchmarks.generate_large_dataset(20000)
            datasets.append(dataset)
        
        with PerformanceBenchmarks.measure_time():
            with PerformanceBenchmarks.measure_memory():
                # Process all strategies concurrently
                def process_strategy(strategy_dataset_pair):
                    strategy, dataset = strategy_dataset_pair
                    return strategy.generate_signals(dataset)
                
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [
                        executor.submit(process_strategy, (strategy, dataset))
                        for strategy, dataset in zip(strategies, datasets)
                    ]
                    results = [future.result() for future in futures]
        
        total_signals = sum(len(signals) for signals in results)
        print(f"Stress test completed: {total_signals} total signals generated")
        assert total_signals >= 0  # Should complete without errors
    
    def test_profiling_detailed_analysis(self, high_performance_strategy):
        """Detailed performance profiling analysis."""
        dataset = PerformanceBenchmarks.generate_large_dataset(10000)
        
        with PerformanceBenchmarks.profile_performance() as profiler:
            # Execute comprehensive strategy operations
            for _ in range(10):
                signals = high_performance_strategy.generate_signals(dataset)
                
                for signal in signals[:5]:  # Process first 5 signals
                    position_size = high_performance_strategy.calculate_position_size(
                        signal, Decimal('100000')
                    )
                    
                    position = Position(
                        symbol="PROFILE_TEST",
                        side=PositionSide.LONG,
                        size=position_size,
                        entry_price=signal.price,
                        timestamp=datetime.now()
                    )
                    
                    # Update position price
                    new_price = signal.price * Decimal('1.01')
                    position.update_price(new_price)
        
        print("Profiling completed - see output above for detailed analysis")


if __name__ == "__main__":
    # Run specific performance tests
    pytest.main([__file__, "-v", "-s"])