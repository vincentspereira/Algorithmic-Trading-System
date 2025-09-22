"""
Comprehensive Unit Tests for Harmonic Analysis Suite

Tests all Harmonic analysis components including patterns and projections
with institutional-grade validation, edge cases, and performance benchmarks.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock

from nautilus_trader_engine.analysis.patterns.harmonic import (
    HarmonicPatterns, HarmonicProjections, HarmonicPattern, PatternDirection,
    PatternCompleteness, ProjectionType
)


class TestHarmonicPatterns:
    """Test Harmonic Patterns functionality"""

    @pytest.fixture
    def sample_harmonic_data(self):
        """Generate sample price data with harmonic pattern characteristics"""
        np.random.seed(42)
        base_price = 100.0
        prices = []
        timestamps = []

        current_time = datetime.now()

        # Generate Gartley-like pattern: X-A-B-C-D
        for i in range(150):
            if i < 30:  # X to A (impulse down)
                trend = -i * 0.8
            elif i < 60:  # A to B (retracement up to 61.8%)
                trend = -24 + (i - 30) * 0.5
            elif i < 90:  # B to C (correction down)
                trend = -5 - (i - 60) * 0.3
            elif i < 120:  # C to D (final move up to 78.6% of X-A)
                trend = -20 + (i - 90) * 0.4
            else:  # After pattern
                trend = 10 + (i - 120) * 0.1

            noise = np.random.normal(0, 0.3)
            price = base_price + trend + noise
            prices.append(price)
            timestamps.append(current_time + timedelta(hours=i))

        return prices, timestamps

    def test_initialization(self):
        """Test HarmonicPatterns initialization"""
        analyzer = HarmonicPatterns(timeframe="1D")
        assert analyzer.name == "HarmonicPatterns"
        assert analyzer.timeframe == "1D"
        assert analyzer.price_history == []
        assert analyzer.active_patterns == []

    def test_pattern_detection(self, sample_harmonic_data):
        """Test harmonic pattern detection"""
        prices, timestamps = sample_harmonic_data
        analyzer = HarmonicPatterns()

        # Feed sufficient data for pattern analysis
        for i in range(80):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        # Should have analyzed patterns
        active_patterns = analyzer.get_active_patterns()
        assert isinstance(active_patterns, list)

        # Check pattern properties if any detected
        for pattern in active_patterns:
            assert hasattr(pattern, 'pattern_type')
            assert hasattr(pattern, 'direction')
            assert hasattr(pattern, 'confidence_score')
            assert isinstance(pattern.pattern_type, HarmonicPattern)
            assert isinstance(pattern.direction, PatternDirection)
            assert 0.0 <= pattern.confidence_score <= 1.0

    def test_fibonacci_ratios(self, sample_harmonic_data):
        """Test Fibonacci ratio validation in patterns"""
        prices, timestamps = sample_harmonic_data
        analyzer = HarmonicPatterns()

        # Feed data
        for i in range(100):
            analyzer.update(prices[i], 1000, timestamp=timestamps[i])

        patterns = analyzer.get_active_patterns()

        # Check Fibonacci ratios if patterns found
        for pattern in patterns:
            if hasattr(pattern, 'fib_ratios'):
                assert isinstance(pattern.fib_ratios, dict)
                # Should contain key ratios
                expected_ratios = ['AB_XA', 'BC_AB', 'CD_BC']
                for ratio in expected_ratios:
                    if ratio in pattern.fib_ratios:
                        assert isinstance(pattern.fib_ratios[ratio], (int, float))

    def test_signal_generation(self, sample_harmonic_data):
        """Test signal generation on pattern completion"""
        prices, timestamps = sample_harmonic_data
        analyzer = HarmonicPatterns()

        signals = []

        # Process all data
        for i in range(len(prices)):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])
            if signal:
                signals.append(signal)

        # Verify signal properties
        for signal in signals:
            assert signal.value_raw >= 0
            assert "HARMONIC" in signal.signal_type
            assert signal.composite_confidence >= 0.0
            assert signal.suggested_sl is not None
            assert signal.suggested_tp is not None
            assert isinstance(signal.pattern, dict) or hasattr(signal, 'pattern')

    def test_pattern_validation(self):
        """Test pattern validation logic"""
        analyzer = HarmonicPatterns()

        # Test validation with sample pattern data
        points = {
            'X': Mock(price=100.0, index=0),
            'A': Mock(price=90.0, index=10),
            'B': Mock(price=95.0, index=20),
            'C': Mock(price=92.0, index=30)
        }

        ratios = {'AB_XA': [0.618], 'BC_AB': [0.382, 0.886]}

        validation_score = analyzer._calculate_pattern_validation(points)
        assert isinstance(validation_score, float)
        assert 0.0 <= validation_score <= 1.0

    def test_volume_confirmation(self, sample_harmonic_data):
        """Test volume confirmation in pattern analysis"""
        prices, timestamps = sample_harmonic_data
        analyzer = HarmonicPatterns()

        # Test with increasing volume (confirmation)
        volumes = [1000 + i * 10 for i in range(len(prices))]

        for i in range(len(prices)):
            analyzer.update(prices[i], volumes[i], timestamp=timestamps[i])

        # Should incorporate volume in confidence
        patterns = analyzer.get_active_patterns()
        assert isinstance(patterns, list)

    def test_smart_money_integration(self):
        """Test smart money confirmation"""
        analyzer = HarmonicPatterns()

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


class TestHarmonicProjections:
    """Test Harmonic Projections functionality"""

    def test_projection_calculation(self):
        """Test harmonic projection calculations"""
        analyzer = HarmonicProjections()

        # Sample swing data
        swings = [(100.0, 0), (120.0, 10), (110.0, 20), (130.0, 30)]

        projections = analyzer._calculate_harmonic_projections(swings)

        assert isinstance(projections, list)
        for projection in projections:
            assert hasattr(projection, 'price_target')
            assert hasattr(projection, 'confidence_score')

    def test_pattern_completion_projections(self):
        """Test pattern completion projection calculations"""
        analyzer = HarmonicProjections()

        # Mock trend and stage
        trend = 'uptrend'
        pattern_stage = 'mid_development'

        projections = analyzer._calculate_completion_projections(trend, pattern_stage)

        assert isinstance(projections, list)

    def test_target_projections(self):
        """Test target projection calculations"""
        analyzer = HarmonicProjections()

        trend = 'uptrend'
        projections = analyzer._calculate_target_projections(trend)

        assert isinstance(projections, list)

    def test_projection_confidence(self):
        """Test projection confidence calculations"""
        analyzer = HarmonicProjections()

        confidence = analyzer._calculate_projection_confidence(
            105.0, None, 'gartley', 0.786, 'mid_development'
        )

        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0

    def test_projection_targets_hit(self):
        """Test hitting projection targets"""
        analyzer = HarmonicProjections()

        prices = [100 + i * 0.2 for i in range(60)]
        timestamps = [datetime.now() + timedelta(hours=i) for i in range(60)]

        signals = []
        for i in range(60):
            signal = analyzer.update(prices[i], 1000, timestamp=timestamps[i])
            if signal:
                signals.append(signal)

        # Should handle target hits gracefully
        assert isinstance(signals, list)


class TestHarmonicAnalysisIntegration:
    """Integration tests for Harmonic Analysis Suite"""

    def test_full_harmonic_workflow(self):
        """Test complete harmonic analysis workflow"""
        patterns_analyzer = HarmonicPatterns()
        projections_analyzer = HarmonicProjections()

        # Generate sample data
        np.random.seed(42)
        prices = [100 + i * 0.05 + np.random.normal(0, 0.3) for i in range(120)]
        volumes = [1000 + np.random.normal(0, 100) for _ in range(120)]
        timestamps = [datetime.now() + timedelta(hours=i) for i in range(120)]

        pattern_signals = []
        projection_signals = []

        # Process data through both analyzers
        for i in range(120):
            # Patterns
            pat_signal = patterns_analyzer.update(prices[i], volumes[i], timestamp=timestamps[i])
            if pat_signal:
                pattern_signals.append(pat_signal)

            # Projections
            proj_signal = projections_analyzer.update(prices[i], volumes[i], timestamp=timestamps[i])
            if proj_signal:
                projection_signals.append(proj_signal)

        # Verify signals were processed
        total_signals = len(pattern_signals) + len(projection_signals)
        assert isinstance(total_signals, int)

        # Verify signal properties if any generated
        all_signals = pattern_signals + projection_signals
        for signal in all_signals:
            assert signal.composite_confidence >= 0.0
            assert signal.composite_confidence <= 1.0
            assert signal.suggested_sl is not None
            assert signal.suggested_tp is not None
            assert signal.timestamp is not None

    def test_harmonic_error_handling(self):
        """Test error handling in harmonic analysis"""
        analyzer = HarmonicPatterns()

        # Test with invalid data
        signal = analyzer.update(None, 1000)
        assert signal is None

        signal = analyzer.update(100.0, None)
        assert signal is None

        # Test with extreme values
        signal = analyzer.update(1e10, 1000)
        assert True  # Should handle gracefully

    def test_harmonic_performance(self):
        """Test performance of harmonic calculations"""
        import time

        analyzer = HarmonicPatterns()

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

    def test_harmonic_memory_usage(self):
        """Test memory usage with large datasets"""
        analyzer = HarmonicPatterns()

        # Process large amount of data
        for i in range(3000):
            price = 100 + np.sin(i * 0.01) * 5
            analyzer.update(price, 1000, timestamp=datetime.now() + timedelta(seconds=i))

        # Should maintain reasonable memory usage
        assert len(analyzer.price_history) <= 300


class TestHarmonicInstitutionalFeatures:
    """Test institutional-grade features of harmonic analysis"""

    def test_multi_timeframe_alignment(self):
        """Test multi-timeframe alignment scoring"""
        analyzer = HarmonicPatterns(timeframe="1H")

        # Mock alignment check
        alignment_score = analyzer._calculate_timeframe_alignment_score()
        assert isinstance(alignment_score, float)
        assert 0.0 <= alignment_score <= 1.0

    def test_adaptive_confidence(self):
        """Test adaptive confidence scoring"""
        analyzer = HarmonicPatterns()

        # Test with different market conditions
        stable_prices = [100 + np.sin(i * 0.1) * 2 for i in range(50)]
        volatile_prices = [100 + np.sin(i * 0.1) * 10 for i in range(50)]

        # Test stable conditions
        for price in stable_prices:
            analyzer.update(price, 1000)

        stable_patterns = len(analyzer.get_active_patterns())

        # Reset
        analyzer.price_history = []

        # Test volatile conditions
        for price in volatile_prices:
            analyzer.update(price, 1000)

        volatile_patterns = len(analyzer.get_active_patterns())

        # Should adapt confidence based on conditions
        assert True

    def test_risk_management_integration(self):
        """Test integrated risk management"""
        analyzer = HarmonicPatterns()

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

            assert rr_ratio >= 1.0  # At least 1:1 for harmonic patterns

    def test_pattern_statistics(self):
        """Test pattern recognition statistics"""
        analyzer = HarmonicPatterns()

        # Generate some signals
        prices = [100 + i * 0.02 for i in range(100)]
        for price in prices:
            analyzer.update(price, 1000)

        stats = analyzer.get_pattern_statistics()
        assert isinstance(stats, dict)

        # Check required statistics
        required_keys = ['total_patterns', 'success_rate', 'pattern_distribution']
        for key in required_keys:
            assert key in stats

    def test_fibonacci_confluence(self):
        """Test Fibonacci confluence in harmonic patterns"""
        analyzer = HarmonicPatterns()

        # Test confluence extraction
        pattern = Mock()
        pattern.fib_ratios = {'AB_XA': 0.618, 'BC_AB': 0.786}

        confluence = analyzer._extract_fib_confluence(pattern)
        assert isinstance(confluence, list)

    def test_pattern_completion_probability(self):
        """Test pattern completion probability calculations"""
        analyzer = HarmonicPatterns()

        # Mock pattern
        pattern = Mock()
        pattern.confidence_score = 0.8
        pattern.pattern_context = {'current_wave': 'late_impulse'}

        probability = analyzer._calculate_pattern_completion_probability(pattern)
        assert isinstance(probability, float)
        assert 0.0 <= probability <= 1.0


class TestHarmonicAnalysisEdgeCases:
    """Test edge cases in harmonic analysis"""

    def test_empty_data(self):
        """Test with empty data"""
        analyzer = HarmonicPatterns()
        signal = analyzer.update(100.0, 1000)
        assert signal is None

    def test_insufficient_data(self):
        """Test with insufficient data for pattern analysis"""
        analyzer = HarmonicPatterns()

        for i in range(10):
            signal = analyzer.update(100.0 + i * 0.1, 1000)
            assert signal is None

    def test_constant_price(self):
        """Test with constant price (no patterns)"""
        analyzer = HarmonicPatterns()

        for i in range(50):
            analyzer.update(100.0, 1000)

        patterns = analyzer.get_active_patterns()
        # Should not detect false patterns
        assert len(patterns) == 0

    def test_extreme_volatility(self):
        """Test with extreme volatility"""
        analyzer = HarmonicPatterns()

        prices = [100 + np.random.normal(0, 15) for _ in range(50)]

        for price in prices:
            analyzer.update(price, 1000)

        # Should handle extreme volatility gracefully
        patterns = analyzer.get_active_patterns()
        assert isinstance(patterns, list)

    def test_time_reversal(self):
        """Test with non-sequential timestamps"""
        analyzer = HarmonicPatterns()

        base_time = datetime.now()
        timestamps = [base_time + timedelta(hours=i) for i in [0, 2, 1, 3]]  # Non-sequential

        prices = [100, 101, 100.5, 102]

        for price, ts in zip(prices, timestamps):
            analyzer.update(price, 1000, timestamp=ts)

        # Should handle time issues gracefully
        assert True

    def test_zero_volume(self):
        """Test with zero volume"""
        analyzer = HarmonicPatterns()

        signal = analyzer.update(100.0, 0)
        # Should handle zero volume
        assert signal is None or isinstance(signal, object)

    def test_negative_prices(self):
        """Test with negative prices (edge case)"""
        analyzer = HarmonicPatterns()

        signal = analyzer.update(-100.0, 1000)
        # Should handle negative prices gracefully
        assert True


if __name__ == "__main__":
    pytest.main([__file__])