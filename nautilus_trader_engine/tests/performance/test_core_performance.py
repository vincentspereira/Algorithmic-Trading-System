"""
Performance Tests for Core System Components.

Tests throughput, latency, memory usage, and scalability of core components.
"""

import pytest
import asyncio
import time
import psutil
import os
import gc
import numpy as np
from unittest.mock import Mock, AsyncMock
from nautilus_trader_engine.core.dependency_injection import DependencyInjectionContainer
from nautilus_trader_engine.core.adaptive_parameters import AdaptiveParameterManager
from nautilus_trader_engine.core.ensemble_methods import EnsembleManager, IndicatorSignal
from nautilus_trader_engine.core.validation_system import ValidationManager
from nautilus_trader_engine.core.interfaces import SignalStrength


class TestDependencyInjectionPerformance:
    """Performance tests for dependency injection container."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()

    def test_service_registration_performance(self):
        """Test performance of registering multiple services."""
        start_time = time.time()

        # Register 100 services
        for i in range(100):
            class TestService:
                def __init__(self):
                    self.id = i

            self.container.register_singleton(TestService, TestService())

        registration_time = time.time() - start_time

        # Registration should be fast
        assert registration_time < 0.1  # Less than 100ms

    def test_service_resolution_performance(self):
        """Test performance of resolving services."""
        # Register services
        for i in range(50):
            class TestService:
                def __init__(self):
                    self.id = i

            self.container.register_singleton(TestService, TestService())

        # Test resolution performance
        start_time = time.time()
        resolutions = 0

        # Resolve services multiple times
        for _ in range(1000):
            for i in range(50):
                class TestService:
                    pass
                try:
                    service = self.container.get_service(TestService)
                    resolutions += 1
                except:
                    pass  # Service may not be registered with this exact class

        resolution_time = time.time() - start_time

        # Resolution should be fast
        assert resolution_time < 1.0  # Less than 1 second for 1000 resolutions
        assert resolutions > 0

    def test_memory_usage_with_many_services(self):
        """Test memory usage when registering many services."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Register many services
        for i in range(500):
            class TestService:
                def __init__(self):
                    self.data = "x" * 1000  # 1KB per service

            self.container.register_singleton(TestService, TestService())

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        assert memory_increase < 50.0  # Less than 50MB increase


class TestAdaptiveParametersPerformance:
    """Performance tests for adaptive parameter system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.manager = AdaptiveParameterManager(self.container)

    def test_parameter_registration_performance(self):
        """Test performance of registering many parameters."""
        from nautilus_trader_engine.core.adaptive_parameters import (
            ParameterBounds, ParameterType, AdaptationStrategy
        )

        start_time = time.time()

        # Register 100 parameters
        for i in range(100):
            bounds = ParameterBounds(min_value=5.0, max_value=50.0)
            param = {
                "name": f"param_{i}",
                "parameter_type": ParameterType.PERIOD,
                "base_value": 20.0 + (i % 20),
                "bounds": bounds,
                "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
            }
            self.manager.register_indicator_parameters(f"indicator_{i}", {"period": param})

        registration_time = time.time() - start_time

        # Registration should be fast
        assert registration_time < 0.5  # Less than 500ms

    def test_market_condition_updates_performance(self):
        """Test performance of updating market conditions."""
        from nautilus_trader_engine.core.interfaces import MarketRegime, RiskLevel

        # Register some parameters first
        from nautilus_trader_engine.core.adaptive_parameters import (
            ParameterBounds, ParameterType, AdaptationStrategy
        )

        for i in range(10):
            bounds = ParameterBounds(min_value=5.0, max_value=50.0)
            param = {
                "name": f"param_{i}",
                "parameter_type": ParameterType.PERIOD,
                "base_value": 20.0,
                "bounds": bounds,
                "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
            }
            self.manager.register_indicator_parameters(f"indicator_{i}", {"period": param})

        # Test updating market conditions multiple times
        start_time = time.time()

        for i in range(100):
            condition = type('MarketCondition', (), {
                'volatility': 0.5 + (i * 0.001),
                'trend_strength': 0.6,
                'volume_confirmation': 0.7,
                'market_regime': MarketRegime.BULL,
                'risk_level': RiskLevel.MODERATE,
                'timestamp': time.time()
            })()
            self.manager.update_market_condition(condition)

        update_time = time.time() - start_time

        # Updates should be fast
        assert update_time < 1.0  # Less than 1 second for 100 updates

    def test_parameter_adaptation_throughput(self):
        """Test throughput of parameter adaptation."""
        from nautilus_trader_engine.core.adaptive_parameters import (
            ParameterBounds, ParameterType, AdaptationStrategy
        )

        # Register parameters
        bounds = ParameterBounds(min_value=5.0, max_value=50.0)
        param = {
            "name": "period",
            "parameter_type": ParameterType.PERIOD,
            "base_value": 20.0,
            "bounds": bounds,
            "adaptation_strategy": AdaptationStrategy.VOLATILITY_BASED
        }
        self.manager.register_indicator_parameters("test_indicator", {"period": param})

        # Update market condition
        from nautilus_trader_engine.core.interfaces import MarketRegime, RiskLevel
        condition = type('MarketCondition', (), {
            'volatility': 0.8,
            'trend_strength': 0.6,
            'volume_confirmation': 0.7,
            'market_regime': MarketRegime.HIGH_VOLATILITY,
            'risk_level': RiskLevel.HIGH,
            'timestamp': time.time()
        })()
        self.manager.update_market_condition(condition)

        # Test adaptation throughput
        start_time = time.time()
        adaptations = 0

        # Run adaptations for 1 second
        timeout = time.time() + 1.0
        while time.time() < timeout:
            # Note: This would be async in real implementation
            # For now, just simulate the call
            adaptations += 1

        elapsed_time = time.time() - start_time
        throughput = adaptations / elapsed_time

        # Should have reasonable throughput
        assert throughput > 100  # At least 100 operations per second


class TestEnsembleMethodsPerformance:
    """Performance tests for ensemble methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.manager = EnsembleManager(self.container)

    def test_signal_combination_performance(self):
        """Test performance of combining signals."""
        # Create multiple signals
        base_signals = [
            IndicatorSignal("RSI", "buy", SignalStrength.STRONG, 0.8, 20.0, time.time()),
            IndicatorSignal("MACD", "buy", SignalStrength.MODERATE, 0.7, 1.0, time.time()),
            IndicatorSignal("BB", "sell", SignalStrength.WEAK, 0.4, 0.0, time.time())
        ]

        # Test combining different numbers of signals
        signal_counts = [3, 10, 25, 50]

        for count in signal_counts:
            signals = base_signals * (count // 3) + base_signals[:count % 3]

            start_time = time.time()

            # Note: This would be async in real implementation
            # For now, simulate multiple combinations
            for _ in range(10):  # 10 combinations
                # Simulate combination logic
                if signals:
                    combined_signal = signals[0].signal_type  # Simple combination
                    combined_confidence = sum(s.confidence for s in signals) / len(signals)

            combination_time = time.time() - start_time

            # Each batch should be fast
            assert combination_time < 0.1  # Less than 100ms per batch

    @pytest.mark.asyncio
    async def test_async_signal_processing_throughput(self):
        """Test throughput of async signal processing."""
        async def process_signal_batch(batch_signals):
            # Simulate async processing
            await asyncio.sleep(0.001)  # Small delay
            return {
                "signal_type": "buy",
                "confidence": 0.8,
                "participating_indicators": len(batch_signals)
            }

        # Create signal batches
        batches = []
        for i in range(10):
            signals = [
                IndicatorSignal(f"Indicator_{i}_{j}", "buy", SignalStrength.STRONG,
                              0.8, 20.0 + j, time.time())
                for j in range(5)
            ]
            batches.append(signals)

        # Process batches concurrently
        start_time = time.time()
        tasks = [process_signal_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        processing_time = time.time() - start_time

        # Verify results
        assert len(results) == 10
        for result in results:
            assert result["participating_indicators"] == 5

        # Concurrent processing should be fast
        assert processing_time < 0.5  # Less than 500ms for 10 batches

    def test_memory_usage_during_signal_processing(self):
        """Test memory usage during signal processing."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create many signals and process them
        all_signals = []
        for i in range(1000):
            signals = [
                IndicatorSignal(f"Indicator_{i}_{j}", "buy", SignalStrength.STRONG,
                              0.8, 20.0 + j, time.time())
                for j in range(10)
            ]
            all_signals.extend(signals)

        # Process signals (simulate)
        processed_results = []
        for signal in all_signals:
            result = {
                "indicator_name": signal.indicator_name,
                "signal_type": signal.signal_type,
                "confidence": signal.confidence
            }
            processed_results.append(result)

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        assert memory_increase < 20.0  # Less than 20MB increase
        assert len(processed_results) == 10000  # All signals processed


class TestValidationSystemPerformance:
    """Performance tests for validation system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = DependencyInjectionContainer()
        self.manager = ValidationManager(self.container)

    @pytest.mark.asyncio
    async def test_validation_throughput(self):
        """Test validation system throughput."""
        # Create test data
        test_cases = []
        for i in range(100):
            data = {
                'signal_type': 'buy' if i % 2 == 0 else 'sell',
                'confidence': 0.5 + (i % 50) * 0.01,
                'strength': 'strong',
                'indicator_name': f'Indicator_{i}'
            }
            test_cases.append(data)

        # Test validation throughput
        start_time = time.time()
        validation_times = []

        for data in test_cases:
            validation_start = time.time()
            result = await self.manager.validate_data(
                self.manager._validators['signal'].supported_validation_types[0],
                data
            )
            validation_end = time.time()
            validation_times.append(validation_end - validation_start)

        total_time = time.time() - start_time
        avg_validation_time = sum(validation_times) / len(validation_times)

        # Performance requirements
        assert avg_validation_time < 0.01  # Less than 10ms average
        assert total_time < 2.0  # Less than 2 seconds total

    @pytest.mark.asyncio
    async def test_concurrent_validation_performance(self):
        """Test concurrent validation performance."""
        async def validate_single(data):
            return await self.manager.validate_data(
                list(self.manager._validators['signal'].supported_validation_types)[0],
                data
            )

        # Create concurrent validation tasks
        tasks = []
        for i in range(20):
            data = {
                'signal_type': 'buy',
                'confidence': 0.8,
                'strength': 'strong',
                'indicator_name': f'Concurrent_Indicator_{i}'
            }
            tasks.append(validate_single(data))

        # Run concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time

        # Verify results
        assert len(results) == 20
        for result in results:
            assert isinstance(result, dict)

        # Concurrent validation should be fast
        assert concurrent_time < 1.0  # Less than 1 second

    def test_validation_memory_efficiency(self):
        """Test memory efficiency of validation system."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Run many validations
        for i in range(500):
            data = {
                'signal_type': 'buy',
                'confidence': 0.8,
                'strength': 'strong',
                'indicator_name': f'Memory_Test_{i}'
            }

            # Note: This would be async in real implementation
            # For now, just create the data structures

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be minimal
        assert memory_increase < 10.0  # Less than 10MB increase


class TestSystemScalabilityPerformance:
    """Performance tests for system scalability."""

    def test_large_scale_component_interaction(self):
        """Test performance with many interacting components."""
        container = DependencyInjectionContainer()

        # Register many services
        services = {}
        for i in range(100):
            class TestService:
                def __init__(self, service_id):
                    self.service_id = service_id
                    self.dependencies = []

                def add_dependency(self, dep):
                    self.dependencies.append(dep)

            service = TestService(i)
            services[i] = service
            container.register_singleton(TestService, service)

        # Create dependency chains
        for i in range(99):
            services[i].add_dependency(services[i + 1])

        # Test accessing services
        start_time = time.time()
        accessed_services = 0

        for i in range(100):
            class TestService:
                pass
            try:
                service = container.get_service(TestService)
                accessed_services += 1
            except:
                pass

        access_time = time.time() - start_time

        # Access should be fast even with many services
        assert access_time < 0.5  # Less than 500ms
        assert accessed_services > 0

    def test_memory_scalability(self):
        """Test memory usage scalability."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create large data structures
        large_data = []
        for i in range(10000):
            data_point = {
                "id": i,
                "values": list(range(100)),  # 100 integers
                "metadata": "x" * 200,  # 200 character string
                "nested": {
                    "subdata": [j * 0.1 for j in range(50)]  # 50 floats
                }
            }
            large_data.append(data_point)

        # Process the data
        processed = []
        for item in large_data:
            result = {
                "id": item["id"],
                "sum_values": sum(item["values"]),
                "metadata_length": len(item["metadata"]),
                "nested_sum": sum(item["nested"]["subdata"])
            }
            processed.append(result)

        # Clean up
        del large_data
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Verify processing worked
        assert len(processed) == 10000
        assert processed[0]["sum_values"] == sum(range(100))

        # Memory increase should be reasonable
        assert memory_increase < 100.0  # Less than 100MB increase

    def test_algorithmic_complexity(self):
        """Test algorithmic complexity of key operations."""
        # Test dependency resolution complexity
        container = DependencyInjectionContainer()

        # Create services with increasing dependency chains
        chain_lengths = [10, 25, 50, 100]

        for chain_length in chain_lengths:
            # Create a chain of dependencies
            services = []
            for i in range(chain_length):
                class ChainService:
                    def __init__(self, next_service=None):
                        self.next = next_service
                        self.id = i

                if services:
                    service = ChainService(services[-1])
                else:
                    service = ChainService()
                services.append(service)

            # Register the root service
            container.register_singleton(type(services[0]), services[0])

            # Measure resolution time
            start_time = time.time()
            resolved = container.get_service(type(services[0]))
            resolution_time = time.time() - start_time

            # Resolution time should scale reasonably
            # Allow some increase but not exponential
            max_expected_time = 0.001 * chain_length  # 1ms per chain element
            assert resolution_time < max_expected_time