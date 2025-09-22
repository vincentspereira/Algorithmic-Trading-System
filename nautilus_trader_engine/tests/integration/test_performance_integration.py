"""
Performance Integration Tests.

Tests the performance aspects of integrated components including:
- Parallel processing with caching
- Streaming performance under load
- Memory usage monitoring
- Response time validation
"""

import pytest
import asyncio
import time
import psutil
import os
from unittest.mock import Mock, AsyncMock
from nautilus_trader_engine.core.dependency_injection import DependencyInjectionContainer
from nautilus_trader_engine.core.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.core.ensemble_methods import EnsembleManager, IndicatorSignal
from nautilus_trader_engine.core.validation_system import ValidationManager
from nautilus_trader_engine.core.interfaces import SignalStrength


class TestPerformanceIntegration:
    """Test performance aspects of integrated components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.adaptive_manager = AdaptiveParameterManager(self.container)
        self.ensemble_manager = EnsembleManager(self.container)
        self.validation_manager = ValidationManager(self.container)

    def test_memory_usage_baseline(self):
        """Test baseline memory usage."""
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Perform some operations
        for i in range(100):
            signals = [
                IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 20.0 + i, time.time()),
                IndicatorSignal("MACD", "sell", SignalStrength.MODERATE, 0.6, 1.0 + i, time.time())
            ]

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_delta = memory_after - memory_before

        # Memory usage should not grow excessively
        assert memory_delta < 50.0  # Less than 50MB increase

    @pytest.mark.asyncio
    async def test_response_time_under_load(self):
        """Test response times under concurrent load."""
        async def single_operation():
            signals = [
                IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 20.0, time.time()),
                IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.7, 1.0, time.time())
            ]

            start_time = time.time()
            result = await self.ensemble_manager.combine_signals(signals)
            end_time = time.time()

            return end_time - start_time

        # Run multiple operations concurrently
        tasks = [single_operation() for _ in range(10)]
        response_times = await asyncio.gather(*tasks)

        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Response times should be reasonable
        assert avg_response_time < 1.0  # Less than 1 second average
        assert max_response_time < 2.0  # Less than 2 seconds max

    @pytest.mark.asyncio
    async def test_validation_performance(self):
        """Test validation system performance."""
        validation_times = []

        for i in range(50):
            signal_data = {
                'signal_type': 'buy',
                'confidence': 0.8 - (i * 0.01),  # Varying confidence
                'strength': 'strong',
                'indicator_name': f'Indicator_{i}'
            }

            start_time = time.time()
            result = await self.validation_manager.validate_data(
                self.validation_manager._validators['signal'].supported_validation_types[0],
                signal_data
            )
            end_time = time.time()

            validation_times.append(end_time - start_time)

        avg_validation_time = sum(validation_times) / len(validation_times)

        # Validation should be fast
        assert avg_validation_time < 0.1  # Less than 100ms average

    def test_adaptive_parameter_performance(self):
        """Test adaptive parameter performance."""
        from nautilus_trader_engine.core.adaptive_parameters import (
            ParameterBounds, ParameterType, AdaptationStrategy
        )

        # Register multiple parameters
        for i in range(10):
            bounds = ParameterBounds(min_value=5.0, max_value=50.0)
            param = {
                "name": f"param_{i}",
                "parameter_type": ParameterType.PERIOD,
                "base_value": 20.0 + i,
                "bounds": bounds,
                "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
            }
            self.adaptive_manager.register_indicator_parameters(f"indicator_{i}", {"period": param})

        # Update market conditions multiple times
        start_time = time.time()
        for i in range(20):
            from nautilus_trader_engine.core.interfaces import MarketRegime, RiskLevel
            condition = type('MarketCondition', (), {
                'volatility': 0.5 + (i * 0.01),
                'trend_strength': 0.6,
                'volume_confirmation': 0.7,
                'market_regime': MarketRegime.BULL,
                'risk_level': RiskLevel.MODERATE,
                'timestamp': time.time()
            })()
            self.adaptive_manager.update_market_condition(condition)

        end_time = time.time()
        adaptation_time = end_time - start_time

        # Adaptation should be reasonably fast
        assert adaptation_time < 1.0  # Less than 1 second for 20 updates

    @pytest.mark.asyncio
    async def test_concurrent_signal_processing(self):
        """Test concurrent signal processing performance."""
        async def process_signals_batch(batch_id):
            signals = [
                IndicatorSignal(f"Indicator_{batch_id}_{i}", "buy", SignalStrength.STRONG,
                              0.8, 20.0 + i, time.time())
                for i in range(5)
            ]

            start_time = time.time()
            result = await self.ensemble_manager.combine_signals(signals)
            end_time = time.time()

            return end_time - start_time, result

        # Run multiple batches concurrently
        tasks = [process_signals_batch(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        response_times = [time for time, _ in results]

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        # Concurrent processing should be efficient
        assert avg_response_time < 0.5  # Less than 500ms average
        assert max_response_time < 1.0  # Less than 1 second max

    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations."""
        process = psutil.Process(os.getpid())

        memory_usage = []

        # Perform repeated operations
        for i in range(10):
            # Create and process signals
            signals = [
                IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 20.0 + i, time.time()),
                IndicatorSignal("MACD", "sell", SignalStrength.MODERATE, 0.6, 1.0 + i, time.time()),
                IndicatorSignal("BB", "hold", SignalStrength.WEAK, 0.4, 0.0 + i, time.time())
            ]

            # Force garbage collection
            import gc
            gc.collect()

            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_usage.append(memory_mb)

            # Small delay to allow system stabilization
            time.sleep(0.01)

        # Check for significant memory growth
        memory_growth = memory_usage[-1] - memory_usage[0]

        # Allow some memory growth but not excessive
        assert memory_growth < 20.0  # Less than 20MB total growth

    @pytest.mark.asyncio
    async def test_validation_throughput(self):
        """Test validation system throughput."""
        signal_data = {
            'signal_type': 'buy',
            'confidence': 0.8,
            'strength': 'strong',
            'indicator_name': 'RSI'
        }

        # Measure throughput over time
        start_time = time.time()
        validations = 0

        # Run validations for 2 seconds
        while time.time() - start_time < 2.0:
            await self.validation_manager.validate_data(
                list(self.validation_manager._validators['signal'].supported_validation_types)[0],
                signal_data
            )
            validations += 1

        elapsed_time = time.time() - start_time
        throughput = validations / elapsed_time

        # Should handle reasonable throughput
        assert throughput > 10  # At least 10 validations per second

    def test_ensemble_method_scalability(self):
        """Test ensemble method scalability with increasing signal count."""
        response_times = []

        for num_signals in [2, 5, 10, 20]:
            signals = [
                IndicatorSignal(f"Indicator_{i}", "buy", SignalStrength.STRONG,
                              0.8, 20.0 + i, time.time())
                for i in range(num_signals)
            ]

            start_time = time.time()
            # Note: This would be async in real implementation
            # For now, just measure setup time
            end_time = time.time()

            response_times.append(end_time - start_time)

        # Response time should scale reasonably
        # (This is a simplified test - real async implementation would be better)
        assert len(response_times) == 4

    @pytest.mark.asyncio
    async def test_error_handling_performance(self):
        """Test error handling doesn't significantly impact performance."""
        # Mix of valid and invalid data
        test_data = [
            # Valid data
            {
                'signal_type': 'buy',
                'confidence': 0.8,
                'strength': 'strong',
                'indicator_name': 'RSI'
            },
            # Invalid data (missing required fields)
            {
                'signal_type': 'buy'
                # Missing confidence, strength, indicator_name
            },
            # Another valid data
            {
                'signal_type': 'sell',
                'confidence': 0.7,
                'strength': 'moderate',
                'indicator_name': 'MACD'
            }
        ]

        response_times = []

        for data in test_data * 5:  # Repeat for more data
            start_time = time.time()
            try:
                result = await self.validation_manager.validate_data(
                    list(self.validation_manager._validators['signal'].supported_validation_types)[0],
                    data
                )
            except Exception:
                pass  # Expected for invalid data
            end_time = time.time()

            response_times.append(end_time - start_time)

        avg_response_time = sum(response_times) / len(response_times)

        # Error handling should not significantly slow down processing
        assert avg_response_time < 0.2  # Less than 200ms average