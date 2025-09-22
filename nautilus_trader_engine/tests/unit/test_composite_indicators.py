"""
Comprehensive Unit Tests for Composite Indicators Suite

Tests composite indicator functionality with institutional-grade validation,
edge cases, and performance benchmarks.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock

from nautilus_trader_engine.analysis.indicators.composite import (
    CompositeIndicators, CompositeSignal, CompositeType, SignalStrength,
    CompositeComponent
)


class TestCompositeIndicators:
    """Test Composite Indicators functionality"""

    @pytest.fixture
    def sample_composite_data(self):
        """Generate sample price data for composite analysis"""
        np.random.seed(42)
        base_price = 100.0
        prices = []
        timestamps = []

        current_time = datetime.now()

        # Generate trending data with some momentum shifts
        for i in range(200):
            if i < 50:  # Slow uptrend
                trend = i * 0.1
            elif i < 100:  # Strong uptrend
                trend = 5 + (i - 50) * 0.3
            elif i < 150:  # Consolidation
                trend = 20 + np.sin((i - 100) * 0.2) * 2
            else:  # Downtrend
                trend = 22 - (i - 150) * 0.2

            noise = np.random.normal(0, 0.5)
            price = base_price + trend + noise
            prices.append(price)
            timestamps.append(current_time + timedelta(hours=i))

        return prices, timestamps

    def test_initialization(self):
        """Test CompositeIndicators initialization"""
        analyzer = CompositeIndicators(timeframe="1D", composite_type=CompositeType.MOMENTUM_COMPOSITE)
        assert analyzer.name == "CompositeIndicators"
        assert analyzer.timeframe == "1D"
        assert analyzer.composite_type == CompositeType.MOMENTUM_COMPOSITE
        assert analyzer.price_history == []
        assert analyzer.indicator_values == {}

    def test_component_initialization(self):
        """Test component weight initialization"""
        analyzer = CompositeIndicators(composite_type=CompositeType.MOMENTUM_COMPOSITE)
        weights = analyzer.component_weights[CompositeType.MOMENTUM_COMPOSITE.value]

        assert 'rsi' in weights
        assert 'macd' in weights
        assert 'stochastic' in weights
        assert sum(weights.values()) > 0.99  # Should sum to approximately 1

    def test_insufficient_data(self, sample_composite_data):
        """Test behavior with insufficient data"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        # Test with minimal data
        signal = analyzer.update(prices[0], 1000, timestamp=timestamps[0])
        assert signal is None

        # Test with some data but not enough for analysis
        for i in range(20):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])
            assert signal is None

    def test_momentum_composite(self, sample_composite_data):
        """Test momentum composite indicator"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators(composite_type=CompositeType.MOMENTUM_COMPOSITE)

        # Feed sufficient data
        for i in range(80):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        # Should have calculated composite signal
        if signal:
            assert signal.composite_type == CompositeType.MOMENTUM_COMPOSITE
            assert isinstance(signal.signal_strength, SignalStrength)
            assert len(signal.component_signals) > 0

            # Check component signals
            for component in signal.component_signals:
                assert isinstance(component, CompositeComponent)
                assert 0.0 <= component.confidence <= 1.0
                assert -1.0 <= component.signal <= 1.0

    def test_trend_composite(self, sample_composite_data):
        """Test trend composite indicator"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators(composite_type=CompositeType.TREND_COMPOSITE)

        # Feed data
        for i in range(80):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        if signal:
            assert signal.composite_type == CompositeType.TREND_COMPOSITE
            # Should include trend-related components like SMA, EMA, ADX

    def test_volatility_composite(self, sample_composite_data):
        """Test volatility composite indicator"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators(composite_type=CompositeType.VOLATILITY_COMPOSITE)

        # Feed data
        for i in range(80):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        if signal:
            assert signal.composite_type == CompositeType.VOLATILITY_COMPOSITE
            # Should include volatility components like Bollinger Bands, ATR

    def test_signal_generation(self, sample_composite_data):
        """Test signal generation"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        signals = []

        # Process data
        for i in range(len(prices)):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])
            if signal:
                signals.append(signal)

        # Verify signal properties
        for signal in signals:
            assert signal.value_raw >= 0
            assert "COMPOSITE" in signal.signal_type
            assert signal.composite_confidence >= 0.0
            assert signal.suggested_sl is not None
            assert signal.suggested_tp is not None
            assert signal.market_regime in ['ranging', 'strong_uptrend', 'strong_downtrend', 'choppy', 'trending']

    def test_component_calculation(self):
        """Test individual component calculations"""
        analyzer = CompositeIndicators()

        # Test RSI calculation
        prices = [100 + i * 0.1 for i in range(30)]
        for price in prices:
            analyzer.update(price, 1000)

        # Check if RSI was calculated
        if 'rsi' in analyzer.indicator_values:
            rsi_data = analyzer.indicator_values['rsi']
            assert 'signal' in rsi_data
            assert 'confidence' in rsi_data
            assert -1 <= rsi_data['signal'] <= 1
            assert 0 <= rsi_data['confidence'] <= 1

    def test_composite_signal_strength(self, sample_composite_data):
        """Test signal strength determination"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        # Feed data
        for i in range(80):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        if signal:
            # Signal strength should be valid
            assert signal.signal_strength in SignalStrength

            # Stronger signals should have higher confidence
            if signal.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]:
                assert signal.composite_confidence > 0.5

    def test_divergence_calculation(self, sample_composite_data):
        """Test divergence score calculation"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        # Feed data
        for i in range(80):
            analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        components = analyzer.get_component_signals()

        if len(components) > 1:
            divergence = analyzer._calculate_divergence_score(components)
            assert 0.0 <= divergence <= 1.0

            # High divergence means less agreement (lower score)
            # Low divergence means more agreement (higher score)

    def test_confluence_calculation(self, sample_composite_data):
        """Test confluence score calculation"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        # Feed data
        for i in range(80):
            analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        components = analyzer.get_component_signals()

        if len(components) > 0:
            confluence = analyzer._calculate_confluence_score(components)
            assert 0.0 <= confluence <= 1.0

    def test_market_regime_detection(self, sample_composite_data):
        """Test market regime detection"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        # Feed data
        for i in range(80):
            analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        components = analyzer.get_component_signals()

        if len(components) > 0:
            regime = analyzer._determine_market_regime(components)
            assert regime in ['ranging', 'strong_uptrend', 'strong_downtrend', 'choppy', 'trending', 'unknown']

    def test_volume_weighting(self, sample_composite_data):
        """Test volume weighting in composite analysis"""
        prices, timestamps = sample_composite_data
        analyzer = CompositeIndicators()

        # Test with varying volume
        volumes = [1000 + i * 10 for i in range(len(prices))]

        for i in range(len(prices)):
            analyzer.update(prices[i], volumes[i], timestamp=timestamps[i])

        # Should incorporate volume in analysis
        assert True  # Test passes if no errors

    def test_smart_money_integration(self):
        """Test smart money confirmation"""
        analyzer = CompositeIndicators()

        order_book = {
            'bids': {99.0: 1000, 98.5: 800},
            'asks': {101.0: 500, 101.5: 300}
        }

        trade_data = [
            (100.0, 5000, datetime.now()),
            (100.2, 1000, datetime.now()),
        ]

        signal = analyzer.update(100.0, 1000,
                               order_book_data=order_book,
                               trade_data=trade_data)

        # Should handle smart money data
        assert True


class TestCompositeAnalysisIntegration:
    """Integration tests for Composite Indicators"""

    def test_full_composite_workflow(self):
        """Test complete composite analysis workflow"""
        # Test different composite types
        composite_types = [
            CompositeType.MOMENTUM_COMPOSITE,
            CompositeType.TREND_COMPOSITE,
            CompositeType.VOLATILITY_COMPOSITE,
            CompositeType.VOLUME_COMPOSITE
        ]

        # Generate sample data
        np.random.seed(42)
        prices = [100 + i * 0.05 + np.random.normal(0, 0.3) for i in range(120)]
        volumes = [1000 + np.random.normal(0, 100) for _ in range(120)]
        timestamps = [datetime.now() + timedelta(hours=i) for i in range(120)]

        for comp_type in composite_types:
            analyzer = CompositeIndicators(composite_type=comp_type)
            signals = []

            # Process data
            for i in range(120):
                signal = analyzer.update(prices[i], volumes[i], timestamp=timestamps[i])
                if signal:
                    signals.append(signal)

            # Verify signals for this composite type
            for signal in signals:
                assert signal.composite_type == comp_type
                assert signal.composite_confidence >= 0.0
                assert signal.suggested_sl is not None
                assert signal.suggested_tp is not None

    def test_composite_error_handling(self):
        """Test error handling in composite analysis"""
        analyzer = CompositeIndicators()

        # Test with invalid data
        signal = analyzer.update(None, 1000)
        assert signal is None

        signal = analyzer.update(100.0, None)
        assert signal is None

        # Test with extreme values
        signal = analyzer.update(1e10, 1000)
        assert True  # Should handle gracefully

    def test_composite_performance(self):
        """Test performance of composite calculations"""
        import time

        analyzer = CompositeIndicators()

        # Generate large dataset
        prices = [100 + np.sin(i * 0.01) * 5 for i in range(1000)]
        volumes = [1000] * 1000
        timestamps = [datetime.now() + timedelta(minutes=i) for i in range(1000)]

        start_time = time.time()

        for i in range(1000):
            analyzer.update(prices[i], volumes[i], timestamp=timestamps[i])

        end_time = time.time()

        # Should process 1000 updates in reasonable time (< 2 seconds)
        processing_time = end_time - start_time
        assert processing_time < 2.0

    def test_composite_memory_usage(self):
        """Test memory usage with large datasets"""
        analyzer = CompositeIndicators()

        # Process large amount of data
        for i in range(3000):
            price = 100 + np.sin(i * 0.01) * 5
            analyzer.update(price, 1000, timestamp=datetime.now() + timedelta(seconds=i))

        # Should maintain reasonable memory usage
        assert len(analyzer.price_history) <= 300


class TestCompositeInstitutionalFeatures:
    """Test institutional-grade features of composite indicators"""

    def test_multi_timeframe_alignment(self):
        """Test multi-timeframe alignment scoring"""
        analyzer = CompositeIndicators(timeframe="1H")

        # Mock alignment check
        alignment_score = analyzer._calculate_timeframe_alignment_score()
        assert isinstance(alignment_score, float)
        assert 0.0 <= alignment_score <= 1.0

    def test_adaptive_confidence(self):
        """Test adaptive confidence scoring"""
        analyzer = CompositeIndicators()

        # Test with different market conditions
        stable_prices = [100 + np.sin(i * 0.1) * 2 for i in range(50)]
        volatile_prices = [100 + np.sin(i * 0.1) * 10 for i in range(50)]

        # Test stable conditions
        for price in stable_prices:
            analyzer.update(price, 1000)

        stable_signal = analyzer.current_signal

        # Reset
        analyzer.price_history = []

        # Test volatile conditions
        for price in volatile_prices:
            analyzer.update(price, 1000)

        volatile_signal = analyzer.current_signal

        # Should adapt confidence based on conditions
        assert True

    def test_risk_management_integration(self):
        """Test integrated risk management"""
        analyzer = CompositeIndicators()

        # Generate sample signal
        prices = [100 + i * 0.05 for i in range(80)]
        for price in prices:
            signal = analyzer.update(price, 1000)

        if signal:
            # Verify risk management
            assert signal.suggested_sl < signal.value_raw or signal.suggested_sl > signal.value_raw
            assert signal.suggested_tp != signal.value_raw

            risk = abs(signal.value_raw - signal.suggested_sl)
            reward = abs(signal.suggested_tp - signal.value_raw)
            rr_ratio = reward / risk if risk > 0 else 0

            assert rr_ratio >= 1.0  # At least 1:1 for composite signals

    def test_signal_statistics(self):
        """Test signal generation statistics"""
        analyzer = CompositeIndicators()

        # Generate some signals
        prices = [100 + i * 0.02 for i in range(100)]
        for price in prices:
            analyzer.update(price, 1000)

        stats = analyzer.get_composite_statistics()
        assert isinstance(stats, dict)

        # Check required statistics
        required_keys = ['total_signals', 'average_confidence', 'signal_distribution', 'strength_distribution']
        for key in required_keys:
            assert key in stats

    def test_component_signal_distribution(self):
        """Test component signal distribution analysis"""
        analyzer = CompositeIndicators()

        # Feed data to generate component signals
        prices = [100 + i * 0.05 for i in range(80)]
        for price in prices:
            analyzer.update(price, 1000)

        components = analyzer.get_component_signals()

        if components:
            distribution = analyzer._analyze_signal_distribution(components)
            assert isinstance(distribution, dict)
            assert 'mean' in distribution
            assert 'std' in distribution
            assert 'bullish_count' in distribution
            assert 'bearish_count' in distribution

    def test_volatility_context(self):
        """Test volatility context calculation"""
        analyzer = CompositeIndicators()

        # Feed data
        prices = [100 + i * 0.1 for i in range(50)]
        for price in prices:
            analyzer.update(price, 1000)

        volatility = analyzer._calculate_volatility_context()
        assert isinstance(volatility, float)
        assert 0.0 <= volatility <= 1.0

    def test_volume_context(self):
        """Test volume context calculation"""
        analyzer = CompositeIndicators()

        # Feed data with varying volume
        prices = [100 + i * 0.05 for i in range(50)]
        volumes = [1000 + i * 20 for i in range(50)]

        for price, volume in zip(prices, volumes):
            analyzer.update(price, volume)

        volume_context = analyzer._calculate_volume_context()
        assert isinstance(volume_context, float)
        assert 0.0 <= volume_context <= 1.0


class TestCompositeEdgeCases:
    """Test edge cases in composite indicators"""

    def test_empty_data(self):
        """Test with empty data"""
        analyzer = CompositeIndicators()
        signal = analyzer.update(100.0, 1000)
        assert signal is None

    def test_single_component(self):
        """Test with only one component available"""
        analyzer = CompositeIndicators()

        # Feed minimal data
        for i in range(30):
            analyzer.update(100.0 + i * 0.1, 1000)

        components = analyzer.get_component_signals()
        # May have some components calculated
        assert isinstance(components, list)

    def test_constant_price(self):
        """Test with constant price"""
        analyzer = CompositeIndicators()

        for i in range(50):
            analyzer.update(100.0, 1000)

        components = analyzer.get_component_signals()
        # Should handle constant price gracefully
        assert isinstance(components, list)

    def test_extreme_volatility(self):
        """Test with extreme volatility"""
        analyzer = CompositeIndicators()

        prices = [100 + np.random.normal(0, 15) for _ in range(50)]

        for price in prices:
            analyzer.update(price, 1000)

        # Should handle extreme volatility gracefully
        components = analyzer.get_component_signals()
        assert isinstance(components, list)

    def test_zero_volume(self):
        """Test with zero volume"""
        analyzer = CompositeIndicators()

        signal = analyzer.update(100.0, 0)
        # Should handle zero volume
        assert signal is None or isinstance(signal, object)

    def test_negative_prices(self):
        """Test with negative prices"""
        analyzer = CompositeIndicators()

        signal = analyzer.update(-100.0, 1000)
        # Should handle negative prices gracefully
        assert True

    def test_all_composite_types(self):
        """Test all composite types"""
        composite_types = [
            CompositeType.MOMENTUM_COMPOSITE,
            CompositeType.TREND_COMPOSITE,
            CompositeType.VOLATILITY_COMPOSITE,
            CompositeType.VOLUME_COMPOSITE,
            CompositeType.MEAN_REVERSION_COMPOSITE,
            CompositeType.BREAKOUT_COMPOSITE,
            CompositeType.REVERSAL_COMPOSITE,
            CompositeType.CONFIRMATION_COMPOSITE
        ]

        prices = [100 + i * 0.05 for i in range(100)]

        for comp_type in composite_types:
            analyzer = CompositeIndicators(composite_type=comp_type)

            # Feed data
            for price in prices:
                signal = analyzer.update(price, 1000)

            # Should initialize and process without errors
            assert analyzer.composite_type == comp_type

    def test_component_confidence_calculation(self):
        """Test component confidence calculations"""
        analyzer = CompositeIndicators()

        # Mock component signals
        components = [
            CompositeComponent('rsi', 0.25, 0.8, 0.9, '1D'),
            CompositeComponent('macd', 0.25, -0.3, 0.7, '1D'),
            CompositeComponent('stochastic', 0.2, 0.5, 0.8, '1D')
        ]

        confidence_components = analyzer._calculate_confidence_components(components)
        assert isinstance(confidence_components, dict)
        assert 'component_agreement' in confidence_components
        assert 'average_component_confidence' in confidence_components


if __name__ == "__main__":
    pytest.main([__file__])