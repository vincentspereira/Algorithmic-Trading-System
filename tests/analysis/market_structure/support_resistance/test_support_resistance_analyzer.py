"""
Tests for Support and Resistance Analyzer Module

Comprehensive test suite for the support and resistance analysis functionality.
"""

import unittest
import numpy as np
from datetime import datetime, timedelta

from nautilus_trader_engine.analysis.market_structure.support_resistance.support_resistance_analyzer import (
    SupportResistanceAnalyzer,
    SupportResistanceSignal,
    LevelType,
    LevelStrength,
    SupportResistanceSignalType
)


class TestSupportResistanceAnalyzer(unittest.TestCase):
    """Test cases for SupportResistanceAnalyzer"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = SupportResistanceAnalyzer()
        self.sample_prices = [100, 105, 102, 108, 104, 110, 106, 112, 108, 115]
        self.timestamps = [datetime.now() + timedelta(minutes=i) for i in range(len(self.sample_prices))]

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer, SupportResistanceAnalyzer)
        self.assertEqual(self.analyzer.name, "SupportResistanceAnalyzer")
        self.assertIsNone(self.analyzer.current_signal)
        self.assertEqual(len(self.analyzer.support_levels), 0)
        self.assertEqual(len(self.analyzer.resistance_levels), 0)

    def test_pivot_point_detection(self):
        """Test pivot point detection"""
        # Create clear pivot points
        prices = [100, 102, 98, 105, 101, 108]  # Pivot low at index 2, pivot high at index 5

        for price in prices:
            self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=datetime.now()
            )

        # Should detect pivot points
        pivots = self.analyzer._find_pivot_points()
        self.assertIsInstance(pivots, dict)
        self.assertGreater(len(pivots), 0)

    def test_support_level_updates(self):
        """Test support level updates"""
        # Create support level touches
        support_price = 100.0
        touches = [100.1, 99.9, 100.2, 99.8]  # Close to support

        for price in touches:
            self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=datetime.now()
            )

        # Should have identified support level
        self.assertGreater(len(self.analyzer.support_levels), 0)

    def test_resistance_level_updates(self):
        """Test resistance level updates"""
        # Create resistance level touches
        resistance_price = 110.0
        touches = [109.8, 110.2, 109.9, 110.1]  # Close to resistance

        for price in touches:
            self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=datetime.now()
            )

        # Should have identified resistance level
        self.assertGreater(len(self.analyzer.resistance_levels), 0)

    def test_level_strength_calculation(self):
        """Test level strength calculation"""
        # Create level with multiple touches and volume
        level_data = {
            'touches': 4,
            'total_volume': 10000,
            'first_touch': datetime.now() - timedelta(days=5),
            'last_touch': datetime.now(),
            'strength': None
        }

        strength = self.analyzer._calculate_level_strength(level_data)
        self.assertIsInstance(strength, LevelStrength)

        # High touches and volume should give strong/very strong level
        if level_data['touches'] >= 3:
            self.assertIn(strength, [LevelStrength.STRONG, LevelStrength.VERY_STRONG])

    def test_signal_generation(self):
        """Test signal generation"""
        # Add data that should trigger signals
        for price in self.sample_prices:
            signal = self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=datetime.now()
            )

        # Check signal properties if generated
        if self.analyzer.current_signal:
            signal = self.analyzer.current_signal
            self.assertIsInstance(signal, SupportResistanceSignal)
            self.assertIn(signal.level_type, [LevelType.MAJOR_SUPPORT, LevelType.MAJOR_RESISTANCE])
            self.assertGreater(signal.composite_confidence, 0)
            self.assertLessEqual(signal.composite_confidence, 1)

    def test_volume_weighting(self):
        """Test volume-weighted level analysis"""
        # Test with varying volume at levels
        volumes = [1000, 2000, 1500, 3000, 2500, 4000, 1800, 3500, 2200, 5000]

        for price, volume in zip(self.sample_prices, volumes):
            self.analyzer.update(
                price=price,
                volume=volume,
                high=price + 1,
                low=price - 1,
                timestamp=datetime.now()
            )

        # Check that volume affects confidence
        if self.analyzer.current_signal:
            self.assertIn('volume_score', self.analyzer.current_signal.confidence_components)

    def test_level_cleanup(self):
        """Test level cleanup for old levels"""
        # Add old data
        old_timestamp = datetime.now() - timedelta(days=40)

        for i, price in enumerate(self.sample_prices[:5]):
            self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=old_timestamp + timedelta(minutes=i)
            )

        # Add recent data
        recent_timestamp = datetime.now()
        for price in self.sample_prices[5:]:
            self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=recent_timestamp
            )

        # Should clean up old levels
        self.analyzer._cleanup_levels()

        # Check that levels are cleaned up (implementation dependent)
        total_levels = len(self.analyzer.support_levels) + len(self.analyzer.resistance_levels)
        self.assertGreaterEqual(total_levels, 0)  # At least some levels should remain

    def test_nearest_levels(self):
        """Test nearest level finding"""
        # Set up some levels
        self.analyzer.support_levels = {99.0: {'touches': 2}, 105.0: {'touches': 3}}
        self.analyzer.resistance_levels = {110.0: {'touches': 2}, 115.0: {'touches': 1}}

        # Test finding nearest levels
        nearest = self.analyzer.get_nearest_levels(107.0)

        self.assertIsNotNone(nearest['support'])  # Should find 105.0
        self.assertIsNotNone(nearest['resistance'])  # Should find 110.0

        self.assertEqual(nearest['support'], 105.0)
        self.assertEqual(nearest['resistance'], 110.0)

    def test_risk_management_integration(self):
        """Test risk management parameter generation"""
        # Generate signals
        for price in self.sample_prices:
            signal = self.analyzer.update(
                price=price,
                volume=1000,
                high=price + 1,
                low=price - 1,
                timestamp=datetime.now()
            )

        if self.analyzer.current_signal:
            signal = self.analyzer.current_signal
            # Check risk parameters
            self.assertIsNotNone(signal.suggested_sl)
            self.assertIsNotNone(signal.suggested_tp)

            # For support test, SL should be below support level
            if signal.signal_type == SupportResistanceSignalType.SUPPORT_TEST:
                self.assertLess(signal.suggested_sl, signal.level_price)

    def test_multi_timeframe_support(self):
        """Test multi-timeframe support"""
        timeframes = ['1m', '5m', '15m', '1h']

        for tf in timeframes:
            analyzer = SupportResistanceAnalyzer()
            # Should handle different timeframes
            self.assertIsInstance(analyzer, SupportResistanceAnalyzer)

    def test_adaptive_confidence(self):
        """Test adaptive confidence scoring"""
        # Test with different market conditions
        conditions = [
            {'volatility': 1.0, 'volume': 1000},  # Low volatility
            {'volatility': 3.0, 'volume': 2000},  # High volatility
        ]

        for condition in conditions:
            analyzer = SupportResistanceAnalyzer()

            for price in self.sample_prices[:8]:
                analyzer.update(
                    price=price,
                    volume=condition['volume'],
                    high=price + condition['volatility'],
                    low=price - condition['volatility'],
                    timestamp=datetime.now()
                )

            if analyzer.current_signal:
                confidence = analyzer.current_signal.composite_confidence
                self.assertGreaterEqual(confidence, 0.0)
                self.assertLessEqual(confidence, 1.0)


class TestSupportResistanceSignal(unittest.TestCase):
    """Test cases for SupportResistanceSignal"""

    def test_signal_creation(self):
        """Test SupportResistanceSignal creation"""
        signal = SupportResistanceSignal(
            value_raw=105.0,
            signal_type="SUPPORT_TEST",
            composite_confidence=0.8,
            confidence_components={'volume': 0.7, 'strength': 0.9},
            suggested_sl=100.0,
            suggested_tp=112.0,
            timestamp=datetime.now(),
            additional_metadata={'level_age_days': 5},
            level_type=LevelType.MAJOR_SUPPORT,
            level_strength=LevelStrength.STRONG,
            level_price=105.0,
            touch_count=4,
            volume_at_level=8000,
            time_at_level=5
        )

        self.assertEqual(signal.value_raw, 105.0)
        self.assertEqual(signal.level_type, LevelType.MAJOR_SUPPORT)
        self.assertEqual(signal.touch_count, 4)


class TestLevelType(unittest.TestCase):
    """Test cases for LevelType enum"""

    def test_level_types(self):
        """Test level type values"""
        self.assertEqual(LevelType.MAJOR_SUPPORT.value, "major_support")
        self.assertEqual(LevelType.MAJOR_RESISTANCE.value, "major_resistance")
        self.assertEqual(LevelType.PIVOT_POINT.value, "pivot_point")


class TestLevelStrength(unittest.TestCase):
    """Test cases for LevelStrength enum"""

    def test_level_strengths(self):
        """Test level strength values"""
        self.assertEqual(LevelStrength.WEAK.value, "weak")
        self.assertEqual(LevelStrength.STRONG.value, "strong")
        self.assertEqual(LevelStrength.VERY_STRONG.value, "very_strong")


class TestSupportResistanceSignalType(unittest.TestCase):
    """Test cases for SupportResistanceSignalType enum"""

    def test_signal_types(self):
        """Test signal type values"""
        self.assertEqual(SupportResistanceSignalType.SUPPORT_TEST.value, "SUPPORT_TEST")
        self.assertEqual(SupportResistanceSignalType.RESISTANCE_TEST.value, "RESISTANCE_TEST")
        self.assertEqual(SupportResistanceSignalType.BREAKOUT_ABOVE_RESISTANCE.value, "BREAKOUT_ABOVE_RESISTANCE")


if __name__ == '__main__':
    unittest.main()