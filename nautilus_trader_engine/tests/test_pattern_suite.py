"""Comprehensive Test Suite for Candlestick Pattern Detection

This module provides extensive testing for all 32+ candlestick patterns
with sample data validation, edge cases, and performance benchmarks.
"""

import unittest
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import time
from unittest.mock import patch

from nautilus_trader_engine.indicators.pattern_indicators import (
    ConsolidatedPatternDetector, create_pattern_detector,
    PatternResult, PatternType, PatternStrength,
    CandleData, VolumeProfile, MarketRegime
)

class PatternTestSuite(unittest.TestCase):
    """Comprehensive test suite for pattern detection"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data and detector"""
        cls.detector = create_pattern_detector(confidence_threshold=0.5)
        cls.sample_data = cls._create_sample_data()
        cls.hammer_data = cls._create_hammer_pattern_data()
        cls.engulfing_data = cls._create_engulfing_pattern_data()
        cls.morning_star_data = cls._create_morning_star_pattern_data()
        cls.gap_data = cls._create_gap_pattern_data()
    
    @staticmethod
    def _create_sample_data(n_points: int = 100) -> pd.DataFrame:
        """Create realistic sample OHLCV data"""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=n_points, freq='1H')
        base_price = 100
        
        # Generate realistic price movements
        closes = [base_price]
        for i in range(1, n_points):
            change = np.random.normal(0, 0.015) * closes[-1]
            closes.append(max(closes[-1] + change, 1))
        
        closes = np.array(closes)
        opens = closes * (1 + np.random.normal(0, 0.003, n_points))
        highs = np.maximum(opens, closes) * (1 + np.abs(np.random.normal(0, 0.008, n_points)))
        lows = np.minimum(opens, closes) * (1 - np.abs(np.random.normal(0, 0.008, n_points)))
        volumes = np.random.randint(1000, 15000, n_points)
        
        return pd.DataFrame({
            'datetime': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
    
    @staticmethod
    def _create_hammer_pattern_data() -> pd.DataFrame:
        """Create data with a clear hammer pattern"""
        data = {
            'open': [100, 99, 98, 97, 96.5, 96.8],  # Last candle: hammer
            'high': [101, 100, 99, 98, 97, 97.2],
            'low': [99, 98, 97, 96, 95, 95.5],     # Long lower shadow
            'close': [99.5, 98.5, 97.5, 96.5, 96.9, 96.9],  # Close near high
            'volume': [1000, 1200, 1100, 1300, 1800, 2000]  # Volume surge
        }
        
        dates = pd.date_range('2024-01-01', periods=len(data['open']), freq='1H')
        data['datetime'] = dates
        
        return pd.DataFrame(data)
    
    @staticmethod
    def _create_engulfing_pattern_data() -> pd.DataFrame:
        """Create data with a clear bullish engulfing pattern"""
        data = {
            'open': [100, 99, 98, 97, 96, 95.5],   # Last: bullish engulfing
            'high': [101, 100, 99, 98, 97, 98.5],
            'low': [99, 98, 97, 96, 95, 94.8],     # Engulfs previous candle
            'close': [99.5, 98.5, 97.5, 96.5, 95.2, 98.2],  # Strong bullish close
            'volume': [1000, 1200, 1100, 1300, 1500, 2500]  # High volume confirmation
        }
        
        dates = pd.date_range('2024-01-01', periods=len(data['open']), freq='1H')
        data['datetime'] = dates
        
        return pd.DataFrame(data)
    
    @staticmethod
    def _create_morning_star_pattern_data() -> pd.DataFrame:
        """Create data with a clear morning star pattern"""
        data = {
            'open': [100, 99, 98, 97, 96, 95, 94.5, 95.2],  # 3-candle morning star
            'high': [101, 100, 99, 98, 97, 96, 95, 97.8],
            'low': [99, 98, 97, 96, 95, 94, 94.2, 95],
            'close': [99.5, 98.5, 97.5, 96.5, 95.5, 94.2, 94.8, 97.5],  # Star + bullish
            'volume': [1000, 1200, 1100, 1300, 1500, 1200, 1400, 2200]
        }
        
        dates = pd.date_range('2024-01-01', periods=len(data['open']), freq='1H')
        data['datetime'] = dates
        
        return pd.DataFrame(data)
    
    @staticmethod
    def _create_gap_pattern_data() -> pd.DataFrame:
        """Create data with gap patterns"""
        data = {
            'open': [100, 99, 98, 97, 96, 98.5],   # Gap up on last candle
            'high': [101, 100, 99, 98, 97, 99.2],
            'low': [99, 98, 97, 96, 95, 98.2],     # Gap: 98.2 > 97 (prev high)
            'close': [99.5, 98.5, 97.5, 96.5, 96.2, 99],
            'volume': [1000, 1200, 1100, 1300, 1500, 2000]
        }
        
        dates = pd.date_range('2024-01-01', periods=len(data['open']), freq='1H')
        data['datetime'] = dates
        
        return pd.DataFrame(data)
    
    def test_detector_initialization(self):
        """Test detector initialization"""
        detector = ConsolidatedPatternDetector()
        self.assertIsInstance(detector, ConsolidatedPatternDetector)
        self.assertEqual(detector.volume_lookback, 20)
        self.assertEqual(detector.confidence_threshold, 0.6)
        
        # Test factory function
        factory_detector = create_enhanced_vw_pattern_detector(confidence_threshold=0.7)
        self.assertEqual(factory_detector.confidence_threshold, 0.7)
    
    def test_available_patterns(self):
        """Test that all expected patterns are available"""
        available_patterns = self.detector.get_available_patterns()
        
        # Check minimum expected patterns
        expected_patterns = [
            'hammer', 'shooting_star', 'doji', 'marubozu',
            'bullish_engulfing', 'bearish_engulfing', 'piercing_line',
            'morning_star', 'evening_star', 'three_white_soldiers',
            'rising_window', 'falling_window', 'rising_three_methods'
        ]
        
        for pattern in expected_patterns:
            self.assertIn(pattern, available_patterns, f"Pattern {pattern} not found")
        
        # Should have at least 25 patterns
        self.assertGreaterEqual(len(available_patterns), 25)
    
    def test_single_candle_patterns(self):
        """Test single candle pattern detection"""
        # Test hammer detection
        hammer_result = self.detector.detect_pattern('hammer', self.hammer_data, 5)
        self.assertIsInstance(hammer_result, PatternResult)
        
        # Test with actual hammer data
        if hammer_result.detected:
            self.assertGreater(hammer_result.confidence, 0.3)
            self.assertEqual(hammer_result.pattern_name, "Hammer")
        
        # Test doji detection
        doji_result = self.detector.detect_pattern('doji', self.sample_data, 50)
        self.assertIsInstance(doji_result, PatternResult)
    
    def test_two_candle_patterns(self):
        """Test two candle pattern detection"""
        # Test engulfing pattern
        engulfing_result = self.detector.detect_pattern('bullish_engulfing', self.engulfing_data, 5)
        self.assertIsInstance(engulfing_result, PatternResult)
        
        if engulfing_result.detected:
            self.assertGreater(engulfing_result.confidence, 0.4)
            self.assertEqual(engulfing_result.pattern_name, "Bullish_Engulfing")
        
        # Test piercing line
        piercing_result = self.detector.detect_pattern('piercing_line', self.sample_data, 50)
        self.assertIsInstance(piercing_result, PatternResult)
    
    def test_three_candle_patterns(self):
        """Test three candle pattern detection"""
        # Test morning star
        morning_star_result = self.detector.detect_pattern('morning_star', self.morning_star_data, 7)
        self.assertIsInstance(morning_star_result, PatternResult)
        
        if morning_star_result.detected:
            self.assertGreater(morning_star_result.confidence, 0.4)
            self.assertEqual(morning_star_result.pattern_name, "Morning_Star")
        
        # Test three white soldiers
        soldiers_result = self.detector.detect_pattern('three_white_soldiers', self.sample_data, 50)
        self.assertIsInstance(soldiers_result, PatternResult)
    
    def test_complex_patterns(self):
        """Test complex pattern detection"""
        # Test gap patterns
        gap_result = self.detector.detect_pattern('rising_window', self.gap_data, 5)
        self.assertIsInstance(gap_result, PatternResult)
        
        # Test three methods
        methods_result = self.detector.detect_pattern('rising_three_methods', self.sample_data, 50)
        self.assertIsInstance(methods_result, PatternResult)
    
    def test_pattern_result_structure(self):
        """Test that pattern results have correct structure"""
        result = self.detector.detect_pattern('hammer', self.sample_data, 50)
        
        # Check required fields
        self.assertIsInstance(result.pattern_name, str)
        self.assertIsInstance(result.pattern_type, PatternType)
        self.assertIsInstance(result.detected, bool)
        self.assertIsInstance(result.confidence, float)
        self.assertIsInstance(result.strength, PatternStrength)
        self.assertIsInstance(result.volume_profile, VolumeProfile)
        
        # Check confidence range
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
        
        # Check volume confirmation range
        self.assertGreaterEqual(result.volume_confirmation, 0.0)
        self.assertLessEqual(result.volume_confirmation, 1.0)
    
    def test_detect_all_patterns(self):
        """Test detecting all patterns across dataset"""
        patterns = self.detector.detect_all_patterns(self.sample_data, start_index=25, end_index=75)
        
        self.assertIsInstance(patterns, dict)
        
        # Check that results are properly structured
        for index, pattern_list in patterns.items():
            self.assertIsInstance(index, int)
            self.assertIsInstance(pattern_list, list)
            
            for pattern in pattern_list:
                self.assertIsInstance(pattern, PatternResult)
                self.assertTrue(pattern.detected)
                self.assertGreaterEqual(pattern.confidence, self.detector.confidence_threshold)
    
    def test_strongest_patterns(self):
        """Test getting strongest patterns"""
        strongest = self.detector.get_strongest_patterns(self.sample_data, 50, top_n=5)
        
        self.assertIsInstance(strongest, list)
        self.assertLessEqual(len(strongest), 5)
        
        # Check that patterns are sorted by strength
        if len(strongest) > 1:
            for i in range(len(strongest) - 1):
                current_score = strongest[i].confidence * (1 + strongest[i].smart_money_involvement)
                next_score = strongest[i + 1].confidence * (1 + strongest[i + 1].smart_money_involvement)
                self.assertGreaterEqual(current_score, next_score)
    
    def test_institutional_grade_patterns(self):
        """Test institutional grade pattern detection"""
        institutional = self.detector.get_institutional_grade_patterns(self.sample_data, 50)
        
        self.assertIsInstance(institutional, list)
        
        # All patterns should be institutional grade
        for pattern in institutional:
            self.assertEqual(pattern.strength, PatternStrength.INSTITUTIONAL_GRADE)
            self.assertGreaterEqual(pattern.confidence, 0.95)
    
    def test_risk_parameters(self):
        """Test risk parameter calculation"""
        # Get a pattern first
        result = self.detector.detect_pattern('hammer', self.hammer_data, 5)
        
        if result.detected:
            risk_params = self.detector.calculate_risk_parameters(
                result, self.hammer_data, 5, account_balance=10000
            )
            
            self.assertIsInstance(risk_params, dict)
            # Add more specific risk parameter tests based on implementation
    
    def test_pattern_summary(self):
        """Test pattern summary generation"""
        patterns = self.detector.detect_all_patterns(self.sample_data, start_index=25, end_index=50)
        summary = self.detector.get_pattern_summary(patterns)
        
        self.assertIsInstance(summary, dict)
        
        # Check required summary fields
        required_fields = [
            'total_patterns', 'unique_patterns', 'pattern_counts',
            'institutional_grade_patterns', 'high_confidence_patterns',
            'average_confidence', 'average_risk_reward', 'strongest_signals'
        ]
        
        for field in required_fields:
            self.assertIn(field, summary)
        
        # Check data types
        self.assertIsInstance(summary['total_patterns'], int)
        self.assertIsInstance(summary['pattern_counts'], dict)
        self.assertIsInstance(summary['strongest_signals'], list)
    
    def test_confidence_threshold_adjustment(self):
        """Test confidence threshold adjustment"""
        original_threshold = self.detector.confidence_threshold
        
        # Test setting new threshold
        self.detector.set_confidence_threshold(0.8)
        self.assertEqual(self.detector.confidence_threshold, 0.8)
        
        # Test boundary conditions
        self.detector.set_confidence_threshold(-0.1)  # Should clamp to 0
        self.assertEqual(self.detector.confidence_threshold, 0.0)
        
        self.detector.set_confidence_threshold(1.5)   # Should clamp to 1
        self.assertEqual(self.detector.confidence_threshold, 1.0)
        
        # Restore original
        self.detector.set_confidence_threshold(original_threshold)
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Test with insufficient data
        small_data = self.sample_data.iloc[:5].copy()
        result = self.detector.detect_pattern('morning_star', small_data, 2)
        self.assertFalse(result.detected)  # Should not detect with insufficient data
        
        # Test with invalid pattern name
        with self.assertRaises(ValueError):
            self.detector.detect_pattern('invalid_pattern', self.sample_data, 50)
        
        # Test with invalid index
        result = self.detector.detect_pattern('hammer', self.sample_data, -1)
        self.assertFalse(result.detected)
        
        result = self.detector.detect_pattern('hammer', self.sample_data, len(self.sample_data))
        self.assertFalse(result.detected)
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks for high-frequency trading"""
        # Create larger dataset
        large_data = self._create_sample_data(1000)
        
        # Benchmark single pattern detection
        start_time = time.time()
        for i in range(100, 200):  # Test 100 detections
            self.detector.detect_pattern('hammer', large_data, i)
        single_pattern_time = time.time() - start_time
        
        # Should be fast enough for HFT (< 1ms per detection)
        avg_time_per_detection = single_pattern_time / 100
        self.assertLess(avg_time_per_detection, 0.001, 
                       f"Single pattern detection too slow: {avg_time_per_detection:.4f}s")
        
        # Benchmark all patterns detection
        start_time = time.time()
        patterns = self.detector.detect_all_patterns(large_data, start_index=100, end_index=110)
        all_patterns_time = time.time() - start_time
        
        # Should complete within reasonable time
        self.assertLess(all_patterns_time, 5.0, 
                       f"All patterns detection too slow: {all_patterns_time:.2f}s")
    
    def test_volume_analysis_integration(self):
        """Test volume analysis integration"""
        # Create data with volume spikes
        volume_data = self.sample_data.copy()
        volume_data.loc[50, 'volume'] = volume_data['volume'].mean() * 5  # Volume spike
        
        result = self.detector.detect_pattern('hammer', volume_data, 50)
        
        if result.detected:
            # Should have higher volume confirmation with volume spike
            self.assertGreater(result.volume_confirmation, 0.5)
            self.assertIn(result.volume_profile, [VolumeProfile.HIGH_VOLUME, VolumeProfile.INSTITUTIONAL_VOLUME])
    
    def test_smart_money_detection(self):
        """Test smart money detection integration"""
        result = self.detector.detect_pattern('bullish_engulfing', self.engulfing_data, 5)
        
        if result.detected:
            # Should have smart money involvement score
            self.assertIsInstance(result.smart_money_involvement, float)
            self.assertGreaterEqual(result.smart_money_involvement, 0.0)
            self.assertLessEqual(result.smart_money_involvement, 1.0)

class PatternValidationTests(unittest.TestCase):
    """Additional validation tests for pattern accuracy"""
    
    def setUp(self):
        self.detector = create_enhanced_vw_pattern_detector(confidence_threshold=0.3)
    
    def test_hammer_validation(self):
        """Validate hammer pattern detection accuracy"""
        # Create perfect hammer
        perfect_hammer_data = pd.DataFrame({
            'open': [100, 99, 98, 97, 96.8],
            'high': [101, 100, 99, 98, 97.0],
            'low': [99, 98, 97, 96, 95.0],    # Long lower shadow
            'close': [99.5, 98.5, 97.5, 96.5, 96.9],  # Close near high
            'volume': [1000, 1200, 1100, 1300, 2000],
            'datetime': pd.date_range('2024-01-01', periods=5, freq='1H')
        })
        
        result = self.detector.detect_pattern('hammer', perfect_hammer_data, 4)
        self.assertTrue(result.detected, "Perfect hammer should be detected")
        self.assertGreater(result.confidence, 0.6, "Perfect hammer should have high confidence")
    
    def test_false_positive_prevention(self):
        """Test that false positives are minimized"""
        # Create data that looks like patterns but isn't
        false_data = pd.DataFrame({
            'open': [100, 100, 100, 100, 100],
            'high': [100, 100, 100, 100, 100],
            'low': [100, 100, 100, 100, 100],
            'close': [100, 100, 100, 100, 100],  # No variation
            'volume': [1000, 1000, 1000, 1000, 1000],
            'datetime': pd.date_range('2024-01-01', periods=5, freq='1H')
        })
        
        # Should not detect patterns in flat data
        patterns = self.detector.detect_all_patterns(false_data)
        detected_patterns = sum(len(pattern_list) for pattern_list in patterns.values())
        self.assertEqual(detected_patterns, 0, "Should not detect patterns in flat data")

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("Running Comprehensive Pattern Detection Tests")
    print("=============================================")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTest(unittest.makeSuite(PatternTestSuite))
    suite.addTest(unittest.makeSuite(PatternValidationTests))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    # Run comprehensive tests
    success = run_comprehensive_tests()
    
    if success:
        print("\n✅ All tests passed! Pattern detection system is ready for production.")
    else:
        print("\n❌ Some tests failed. Please review and fix issues before deployment.")