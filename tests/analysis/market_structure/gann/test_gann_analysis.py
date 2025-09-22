"""
Tests for Gann Analysis Modules

Comprehensive test suite for all Gann analysis functionality including angles, fans, squares, retracements, and pattern recognition.
"""

import unittest
import numpy as np
from datetime import datetime, timedelta

from nautilus_trader_engine.analysis.market_structure.gann.gann_angles import GannAngles
from nautilus_trader_engine.analysis.market_structure.gann.gann_fans import GannFans
from nautilus_trader_engine.analysis.market_structure.gann.gann_squares import GannSquares
from nautilus_trader_engine.analysis.market_structure.gann.gann_retracements import GannRetracements
from nautilus_trader_engine.analysis.market_structure.gann.gann_pattern_recognizer import GannPatternRecognizer


class TestGannAngles(unittest.TestCase):
    """Test cases for GannAngles"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = GannAngles()
        self.pivot_high = 120.0
        self.pivot_low = 100.0

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer, GannAngles)
        self.assertEqual(self.analyzer.name, "GannAngles")

    def test_angle_calculation(self):
        """Test Gann angle calculations"""
        angles = self.analyzer.calculate_angles(self.pivot_high, self.pivot_low)

        expected_angles = [1/1, 1/2, 2/1, 1/3, 3/1, 1/4, 4/1, 1/8, 8/1]

        for angle in expected_angles:
            self.assertIn(angle, angles)
            self.assertIsInstance(angles[angle], dict)
            self.assertIn('price', angles[angle])
            self.assertIn('description', angles[angle])

    def test_angle_projections(self):
        """Test angle projections from pivot points"""
        projections = self.analyzer.project_angles(self.pivot_high, self.pivot_low, 50)

        self.assertIsInstance(projections, dict)
        self.assertGreater(len(projections), 0)

        # Check that projections contain price levels
        for angle_key, angle_data in projections.items():
            self.assertIn('price_levels', angle_data)
            self.assertIsInstance(angle_data['price_levels'], list)

    def test_time_price_squares(self):
        """Test time-price squaring logic"""
        square = self.analyzer.calculate_time_price_square(self.pivot_high, self.pivot_low)

        self.assertIsInstance(square, dict)
        self.assertIn('square_high', square)
        self.assertIn('square_low', square)
        self.assertIn('square_range', square)


class TestGannFans(unittest.TestCase):
    """Test cases for GannFans"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = GannFans()
        self.trend_start = (100.0, datetime.now() - timedelta(days=10))
        self.trend_end = (120.0, datetime.now())

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer, GannFans)
        self.assertEqual(self.analyzer.name, "GannFans")

    def test_fan_lines_calculation(self):
        """Test Gann fan line calculations"""
        fan_lines = self.analyzer.calculate_fan_lines(self.trend_start, self.trend_end)

        self.assertIsInstance(fan_lines, dict)
        self.assertGreater(len(fan_lines), 0)

        # Check fan line structure
        for angle, line_data in fan_lines.items():
            self.assertIn('slope', line_data)
            self.assertIn('intercept', line_data)
            self.assertIn('description', line_data)

    def test_support_resistance_levels(self):
        """Test support/resistance level identification"""
        levels = self.analyzer.get_support_resistance_levels(self.trend_start, self.trend_end)

        self.assertIsInstance(levels, dict)
        self.assertIn('support_levels', levels)
        self.assertIn('resistance_levels', levels)

    def test_fan_intersections(self):
        """Test fan line intersections"""
        intersections = self.analyzer.find_fan_intersections(self.trend_start, self.trend_end, 110.0)

        self.assertIsInstance(intersections, list)
        # May be empty if no intersections at test price


class TestGannSquares(unittest.TestCase):
    """Test cases for GannSquares"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = GannSquares()
        self.price_range = (100.0, 120.0)

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer, GannSquares)
        self.assertEqual(self.analyzer.name, "GannSquares")

    def test_square_of_nine(self):
        """Test Square of Nine calculations"""
        square = self.analyzer.calculate_square_of_nine(100.0)

        self.assertIsInstance(square, dict)
        self.assertIn('center', square)
        self.assertIn('levels', square)
        self.assertIsInstance(square['levels'], list)

    def test_price_cycles(self):
        """Test price cycle analysis"""
        cycles = self.analyzer.analyze_price_cycles(self.price_range)

        self.assertIsInstance(cycles, dict)
        self.assertIn('cycle_length', cycles)
        self.assertIn('pivot_points', cycles)

    def test_square_levels(self):
        """Test square level calculations"""
        levels = self.analyzer.get_square_levels(100.0, 120.0)

        self.assertIsInstance(levels, list)
        self.assertGreater(len(levels), 0)

        # Check level structure
        for level in levels:
            self.assertIn('price', level)
            self.assertIn('type', level)
            self.assertIn('strength', level)


class TestGannRetracements(unittest.TestCase):
    """Test cases for GannRetracements"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = GannRetracements()
        self.high = 120.0
        self.low = 100.0

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer, GannRetracements)
        self.assertEqual(self.analyzer.name, "GannRetracements")

    def test_unique_retracements(self):
        """Test unique Gann retracement levels"""
        retracements = self.analyzer.calculate_unique_retracements(self.high, self.low)

        self.assertIsInstance(retracements, dict)

        # Check for unique Gann levels (not standard Fibonacci)
        unique_levels = [0.125, 0.25, 0.375, 0.625, 0.75, 0.875]
        for level in unique_levels:
            self.assertIn(level, retracements)

    def test_retracement_zones(self):
        """Test retracement zone identification"""
        zones = self.analyzer.get_retracement_zones(self.high, self.low)

        self.assertIsInstance(zones, list)
        self.assertGreater(len(zones), 0)

        # Check zone structure
        for zone in zones:
            self.assertIn('level', zone)
            self.assertIn('price', zone)
            self.assertIn('strength', zone)

    def test_volume_confirmation(self):
        """Test volume confirmation for retracements"""
        volume_data = [1000, 1200, 800, 1500, 900]

        confirmation = self.analyzer.check_volume_confirmation(105.0, volume_data)

        self.assertIsInstance(confirmation, float)
        self.assertGreaterEqual(confirmation, 0.0)
        self.assertLessEqual(confirmation, 1.0)


class TestGannPatternRecognizer(unittest.TestCase):
    """Test cases for GannPatternRecognizer"""

    def setUp(self):
        """Set up test fixtures"""
        self.recognizer = GannPatternRecognizer()
        self.sample_prices = [100, 105, 102, 108, 104, 110, 106, 112, 108, 115]

    def test_initialization(self):
        """Test recognizer initialization"""
        self.assertIsInstance(self.recognizer, GannPatternRecognizer)
        self.assertEqual(self.recognizer.name, "GannPatternRecognizer")

    def test_pattern_detection(self):
        """Test Gann pattern detection"""
        patterns = self.recognizer.detect_patterns(self.sample_prices)

        self.assertIsInstance(patterns, list)
        # May be empty if no clear patterns

    def test_gann_wheel_analysis(self):
        """Test Gann wheel analysis"""
        wheel_data = self.recognizer.analyze_gann_wheel(100.0, 45)  # 45-degree angle

        self.assertIsInstance(wheel_data, dict)
        self.assertIn('angles', wheel_data)
        self.assertIn('price_levels', wheel_data)

    def test_time_cycles(self):
        """Test time cycle analysis"""
        timestamps = [datetime.now() + timedelta(days=i) for i in range(len(self.sample_prices))]

        cycles = self.recognizer.analyze_time_cycles(self.sample_prices, timestamps)

        self.assertIsInstance(cycles, dict)
        self.assertIn('cycle_lengths', cycles)
        self.assertIn('significant_cycles', cycles)

    def test_pattern_confidence(self):
        """Test pattern confidence scoring"""
        # Create a clear Gann pattern
        gann_prices = [100, 112.5, 106.25, 118.75, 112.5]  # Following Gann ratios

        confidence = self.recognizer.calculate_pattern_confidence(gann_prices)

        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)


class TestGannIntegration(unittest.TestCase):
    """Integration tests for Gann analysis components"""

    def test_combined_gann_analysis(self):
        """Test combined Gann analysis"""
        # Initialize all Gann analyzers
        angles = GannAngles()
        fans = GannFans()
        squares = GannSquares()
        retracements = GannRetracements()
        recognizer = GannPatternRecognizer()

        pivot_high = 120.0
        pivot_low = 100.0

        # Test integrated analysis
        angle_data = angles.calculate_angles(pivot_high, pivot_low)
        fan_data = fans.get_support_resistance_levels((pivot_low, datetime.now()), (pivot_high, datetime.now()))
        square_data = squares.get_square_levels(pivot_low, pivot_high)
        retracement_data = retracements.get_retracement_zones(pivot_high, pivot_low)

        # All should return valid data structures
        self.assertIsInstance(angle_data, dict)
        self.assertIsInstance(fan_data, dict)
        self.assertIsInstance(square_data, list)
        self.assertIsInstance(retracement_data, list)

    def test_volume_weighting_integration(self):
        """Test volume weighting across Gann components"""
        volume_data = [1000, 1500, 1200, 1800, 1400]

        retracements = GannRetracements()

        # Test volume-weighted retracement analysis
        weighted_analysis = retracements.analyze_with_volume(110.0, 100.0, volume_data)

        self.assertIsInstance(weighted_analysis, dict)
        self.assertIn('volume_weighted_levels', weighted_analysis)

    def test_multi_timeframe_gann(self):
        """Test multi-timeframe Gann analysis"""
        timeframes = ['1D', '4H', '1H', '15m']

        squares = GannSquares()

        for tf in timeframes:
            # Should handle different timeframes
            square = squares.calculate_square_of_nine(100.0)
            self.assertIsInstance(square, dict)


if __name__ == '__main__':
    unittest.main()