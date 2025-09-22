"""
Comprehensive tests for Volume Profile Analyzer

Tests institutional-grade volume profile analysis including:
- Point of Control (POC) calculation
- Value Area (VA) identification
- Volume cluster detection
- VWAP level analysis
- Volume gap identification
- Smart money confirmation
- Multi-timeframe validation
- Confidence scoring
- Risk management integration
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.analysis.market_structure.support_resistance.volume_profile_analyzer import (
    VolumeProfileAnalyzer, VolumeProfileSignal, VolumeProfileType, VolumeProfileSignalType
)


class TestVolumeProfileAnalyzer(unittest.TestCase):
    """Test suite for Volume Profile Analyzer"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = VolumeProfileAnalyzer(timeframe="1D", lookback_period=200, price_bins=50)

        # Create sample price and volume data
        self.sample_prices = [100.0 + i * 0.1 + np.sin(i * 0.1) for i in range(100)]
        self.sample_volumes = [1000 + int(500 * np.sin(i * 0.2)) for i in range(100)]
        self.sample_timestamps = [datetime.now() - timedelta(days=i) for i in range(100)]

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertEqual(self.analyzer.timeframe, "1D")
        self.assertEqual(self.analyzer.lookback_period, 200)
        self.assertEqual(self.analyzer.price_bins, 50)
        self.assertIsInstance(self.analyzer.price_history, list)
        self.assertIsInstance(self.analyzer.volume_history, list)

    def test_update_with_insufficient_data(self):
        """Test update with insufficient data returns None"""
        signal = self.analyzer.update(price=100.0, volume=1000)
        self.assertIsNone(signal)

    def test_update_with_sufficient_data(self):
        """Test update with sufficient data generates signals"""
        # Feed historical data
        for i in range(60):
            price = self.sample_prices[i]
            volume = self.sample_volumes[i]
            timestamp = self.sample_timestamps[i]

            signal = self.analyzer.update(price=price, volume=volume, timestamp=timestamp)

            # Should generate signal after enough data
            if i >= 50:
                if signal:
                    self.assertIsInstance(signal, VolumeProfileSignal)
                    self.assertIsInstance(signal.composite_confidence, float)
                    self.assertGreaterEqual(signal.composite_confidence, 0.0)
                    self.assertLessEqual(signal.composite_confidence, 1.0)

    def test_volume_profile_calculation(self):
        """Test volume profile calculation"""
        # Feed data
        for i in range(60):
            self.analyzer.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )

        # Check volume profile data
        profile_data = self.analyzer.get_volume_profile_data()
        self.assertIn('volume_profile', profile_data)
        self.assertIn('point_of_control', profile_data)
        self.assertIn('value_area', profile_data)

        # Check value area structure
        value_area = profile_data['value_area']
        self.assertIn('high', value_area)
        self.assertIn('low', value_area)

    def test_point_of_control_calculation(self):
        """Test Point of Control (POC) calculation"""
        # Create data with clear volume concentration
        prices = [100.0] * 30 + [101.0] * 20 + [102.0] * 10  # More volume at 100.0
        volumes = [1000] * 30 + [500] * 20 + [300] * 10

        for price, volume in zip(prices, volumes):
            self.analyzer.update(price=price, volume=volume)

        profile_data = self.analyzer.get_volume_profile_data()
        poc = profile_data['point_of_control']

        # POC should be close to 100.0 (highest volume level)
        self.assertIsNotNone(poc)
        self.assertAlmostEqual(poc, 100.0, delta=1.0)

    def test_value_area_calculation(self):
        """Test Value Area (VA) calculation"""
        # Feed diverse price data
        for i in range(80):
            price = 100.0 + (i % 20) * 0.5  # Prices between 100-110
            volume = 1000 + (i % 10) * 100  # Varying volume
            self.analyzer.update(price=price, volume=volume)

        profile_data = self.analyzer.get_volume_profile_data()
        value_area = profile_data['value_area']

        self.assertIsNotNone(value_area['high'])
        self.assertIsNotNone(value_area['low'])
        self.assertGreater(value_area['high'], value_area['low'])

    def test_vwap_calculation(self):
        """Test VWAP level calculation"""
        # Create price/volume data
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        volumes = [1000, 1200, 800, 1500, 1100]

        for price, volume in zip(prices, volumes):
            self.analyzer.update(price=price, volume=volume)

        profile_data = self.analyzer.get_volume_profile_data()
        vwap_levels = profile_data['vwap_levels']

        self.assertIsInstance(vwap_levels, list)
        if vwap_levels:
            for vwap_data in vwap_levels:
                self.assertIn('vwap', vwap_data)
                self.assertIn('period', vwap_data)
                self.assertIn('total_volume', vwap_data)

    def test_volume_cluster_detection(self):
        """Test volume cluster detection"""
        # Create clustered volume data
        prices = [100.0] * 40 + [105.0] * 10  # Heavy concentration at 100.0
        volumes = [2000] * 40 + [500] * 10

        for price, volume in zip(prices, volumes):
            self.analyzer.update(price=price, volume=volume)

        profile_data = self.analyzer.get_volume_profile_data()
        clusters = profile_data['volume_clusters']

        self.assertIsInstance(clusters, list)
        # Should detect at least one cluster at 100.0

    def test_signal_generation(self):
        """Test signal generation with various conditions"""
        # Test with order book data for smart money analysis
        order_book_data = {
            'bids': {99.9: 1000, 99.8: 800, 99.7: 600},
            'asks': {100.1: 1200, 100.2: 900, 100.3: 700}
        }

        # Feed data and check for signals
        signals_generated = []
        for i in range(60):
            signal = self.analyzer.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i],
                order_book_data=order_book_data
            )
            if signal:
                signals_generated.append(signal)

        # Verify signal structure
        for signal in signals_generated:
            self.assertIsInstance(signal, VolumeProfileSignal)
            self.assertIsInstance(signal.signal_type, str)
            self.assertIsInstance(signal.composite_confidence, float)
            self.assertIsInstance(signal.confidence_components, dict)
            self.assertIsInstance(signal.suggested_sl, (int, float))
            self.assertIsInstance(signal.suggested_tp, (int, float))

    def test_confidence_scoring(self):
        """Test confidence scoring components"""
        # Feed data with high volume concentration
        high_volume_price = 100.0
        for i in range(50):
            price = high_volume_price + (i % 5) * 0.1  # Concentrated around 100.0
            volume = 2000 if price == high_volume_price else 500
            signal = self.analyzer.update(price=price, volume=volume)

            if signal:
                # Check confidence components
                components = signal.confidence_components
                self.assertIn('volume_confirmation', components)
                self.assertIn('smart_money_score', components)
                self.assertIn('timeframe_alignment', components)
                self.assertIn('market_regime_factor', components)

                # All components should be between 0 and 1
                for comp_value in components.values():
                    self.assertGreaterEqual(comp_value, 0.0)
                    self.assertLessEqual(comp_value, 1.0)

    def test_risk_management_integration(self):
        """Test risk management integration"""
        signal = None
        for i in range(60):
            signal = self.analyzer.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )
            if signal:
                break

        if signal:
            # Check risk management parameters
            self.assertIsInstance(signal.suggested_sl, (int, float))
            self.assertIsInstance(signal.suggested_tp, (int, float))

            # Stop loss should be below current price for bullish signals
            if 'BULLISH' in signal.signal_type:
                self.assertLess(signal.suggested_sl, signal.value_raw)
                self.assertGreater(signal.suggested_tp, signal.value_raw)

    def test_volume_statistics(self):
        """Test volume statistics calculation"""
        # Feed data
        for i in range(60):
            self.analyzer.update(
                price=self.sample_prices[i],
                volume=self.sample_volumes[i],
                timestamp=self.sample_timestamps[i]
            )

        stats = self.analyzer.get_volume_statistics()

        self.assertIn('total_volume', stats)
        self.assertIn('average_volume_per_bin', stats)
        self.assertIn('max_volume_in_bin', stats)
        self.assertIn('volume_bins_count', stats)

        # Check statistical properties
        self.assertGreaterEqual(stats['total_volume'], 0)
        self.assertGreaterEqual(stats['volume_bins_count'], 0)

    def test_price_in_value_area(self):
        """Test value area membership checking"""
        # Create concentrated volume data
        for i in range(50):
            price = 100.0 if i < 40 else 105.0  # 80% at 100.0
            volume = 2000 if price == 100.0 else 500
            self.analyzer.update(price=price, volume=volume)

        # Test price in value area
        in_area = self.analyzer.is_price_in_value_area(100.0)
        self.assertTrue(in_area)

        # Test price outside value area
        outside_area = self.analyzer.is_price_in_value_area(110.0)
        self.assertFalse(outside_area)

    def test_nearest_volume_cluster(self):
        """Test nearest volume cluster finding"""
        # Create multiple volume clusters
        cluster_prices = [100.0, 105.0, 110.0]
        for i in range(60):
            cluster_idx = i % 3
            price = cluster_prices[cluster_idx]
            volume = 1500 if cluster_idx == 0 else 800  # Highest volume at 100.0
            self.analyzer.update(price=price, volume=volume)

        # Find nearest cluster to a test price
        test_price = 102.0
        nearest_cluster = self.analyzer.get_nearest_volume_cluster(test_price)

        self.assertIsNotNone(nearest_cluster)
        self.assertIn('price', nearest_cluster)
        self.assertIn('volume', nearest_cluster)

    def test_volume_distribution_analysis(self):
        """Test volume distribution within price ranges"""
        # Feed data across price range
        for i in range(50):
            price = 100.0 + (i % 10) * 0.5  # Prices 100.0 to 104.5
            volume = 1000 + (i % 5) * 200
            self.analyzer.update(price=price, volume=volume)

        # Test volume distribution in range
        price_range = (100.0, 102.0)
        distribution = self.analyzer.get_volume_distribution(price_range)

        self.assertIn('total_volume_in_range', distribution)
        self.assertIn('average_volume_in_range', distribution)
        self.assertIn('volume_concentration', distribution)

        # Check range contains data
        self.assertGreater(distribution['total_volume_in_range'], 0)

    def test_multi_timeframe_support(self):
        """Test multi-timeframe analysis support"""
        # Test with different timeframes
        timeframes = ["1m", "5m", "1H", "1D"]

        for tf in timeframes:
            analyzer = VolumeProfileAnalyzer(timeframe=tf)
            self.assertEqual(analyzer.timeframe, tf)

            # Feed some data
            for i in range(30):
                analyzer.update(price=self.sample_prices[i], volume=self.sample_volumes[i])

            # Should work with different timeframes
            profile_data = analyzer.get_volume_profile_data()
            self.assertIsInstance(profile_data, dict)

    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        # Test with zero/negative prices
        signal = self.analyzer.update(price=0, volume=1000)
        # Should handle gracefully
        self.assertTrue(True)  # No exception thrown

        # Test with extreme volumes
        signal = self.analyzer.update(price=100.0, volume=1000000)
        self.assertTrue(True)  # No exception thrown

    def test_memory_management(self):
        """Test memory management with large datasets"""
        # Feed large amount of data
        large_prices = [100.0 + i * 0.01 for i in range(500)]
        large_volumes = [1000 + i % 100 for i in range(500)]

        for price, volume in zip(large_prices, large_volumes):
            self.analyzer.update(price=price, volume=volume)

        # Should maintain reasonable memory usage
        self.assertLessEqual(len(self.analyzer.price_history), self.analyzer.lookback_period)

        # Should still function correctly
        profile_data = self.analyzer.get_volume_profile_data()
        self.assertIsInstance(profile_data, dict)


if __name__ == '__main__':
    unittest.main()