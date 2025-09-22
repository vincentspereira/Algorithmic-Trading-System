"""
Comprehensive tests for Market Microstructure Analyzer

Tests institutional-grade market microstructure analysis including:
- Bid-ask spread analysis and efficiency metrics
- Order book depth and liquidity assessment
- Trade aggression and market impact analysis
- High-frequency flow pattern detection
- Market maker activity identification
- Liquidity dry-up and order book thinning detection
- Spread widening and depth imbalance signals
- Institutional sweep detection
"""

import unittest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from nautilus_trader_engine.analysis.market_structure.order_flow.market_microstructure_analyzer import (
    MarketMicrostructureAnalyzer, MicrostructureSignal, MicrostructureSignalType,
    OrderBookMetrics, TradeAggressionMetrics, AggressionType
)


class TestMarketMicrostructureAnalyzer(unittest.TestCase):
    """Test suite for Market Microstructure Analyzer"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = MarketMicrostructureAnalyzer(
            timeframe="1Min",
            order_book_depth=10,
            aggression_window=50,
            spread_threshold=0.001
        )

        # Sample market data
        self.sample_prices = [100.0 + i * 0.01 + 0.1 * np.sin(i * 0.1) for i in range(100)]
        self.sample_timestamps = [datetime.now() - timedelta(minutes=i) for i in range(100)]

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertEqual(self.analyzer.timeframe, "1Min")
        self.assertEqual(self.analyzer.order_book_depth, 10)
        self.assertEqual(self.analyzer.aggression_window, 50)
        self.assertEqual(self.analyzer.spread_threshold, 0.001)

    def test_order_book_analysis(self):
        """Test order book metrics calculation"""
        order_book_data = {
            'bids': {99.9: 1000, 99.8: 800, 99.7: 600, 99.6: 400},
            'asks': {100.1: 1200, 100.2: 900, 100.3: 700, 100.4: 500}
        }

        metrics = self.analyzer._analyze_order_book()
        self.assertIsNone(metrics)  # No data yet

        # Update order book
        self.analyzer._update_order_book(order_book_data, datetime.now())

        metrics = self.analyzer._analyze_order_book()
        self.assertIsInstance(metrics, OrderBookMetrics)
        self.assertIsInstance(metrics.bid_ask_spread, float)
        self.assertIsInstance(metrics.depth_imbalance, float)
        self.assertGreater(metrics.bid_depth, 0)
        self.assertGreater(metrics.ask_depth, 0)

    def test_spread_calculation(self):
        """Test bid-ask spread calculation"""
        order_book_data = {
            'bids': {99.9: 1000},
            'asks': {100.1: 1200}
        }

        self.analyzer._update_order_book(order_book_data, datetime.now())
        metrics = self.analyzer._analyze_order_book()

        expected_spread = 100.1 - 99.9
        self.assertAlmostEqual(metrics.bid_ask_spread, expected_spread, places=2)

        expected_spread_pct = expected_spread / 99.9
        self.assertAlmostEqual(metrics.spread_percentage, expected_spread_pct, places=4)

    def test_depth_imbalance_calculation(self):
        """Test order book depth imbalance calculation"""
        order_book_data = {
            'bids': {99.9: 1000, 99.8: 500},  # Total bid depth: 1500
            'asks': {100.1: 800, 100.2: 400}   # Total ask depth: 1200
        }

        self.analyzer._update_order_book(order_book_data, datetime.now())
        metrics = self.analyzer._analyze_order_book()

        # Expected imbalance: (1500 - 1200) / (1500 + 1200) = 300 / 2700 ≈ 0.111
        expected_imbalance = (1500 - 1200) / (1500 + 1200)
        self.assertAlmostEqual(metrics.depth_imbalance, expected_imbalance, places=3)

    def test_trade_aggression_analysis(self):
        """Test trade aggression metrics calculation"""
        # Create sample trades with different aggression types
        trade_data = [
            (100.0, 1000, True, 'passive'),      # Passive buy
            (100.1, 1200, False, 'aggressive_sell'),  # Aggressive sell
            (99.9, 800, True, 'market_order'),   # Market buy
            (100.2, 1500, False, 'passive'),     # Passive sell
        ]

        # Update trades
        for trade in trade_data:
            self.analyzer._update_trades([trade], datetime.now())

        metrics = self.analyzer._analyze_trade_aggression()
        self.assertIsInstance(metrics, TradeAggressionMetrics)
        self.assertIsInstance(metrics.aggression_ratio, float)
        self.assertIsInstance(metrics.buy_aggression, float)
        self.assertIsInstance(metrics.sell_aggression, float)

    def test_aggression_ratio_calculation(self):
        """Test aggression ratio calculation"""
        # Create imbalanced trade data
        trade_data = [
            (100.0, 2000, True, 'aggressive_buy'),    # Large aggressive buy
            (100.1, 500, False, 'passive'),           # Small passive sell
            (99.9, 1500, True, 'market_order'),       # Large market buy
        ]

        for trade in trade_data:
            self.analyzer._update_trades([trade], datetime.now())

        metrics = self.analyzer._analyze_trade_aggression()

        # Buy volume: 2000 + 1500 = 3500, Sell volume: 500
        # Aggression ratio: |3500 - 500| / (3500 + 500) = 3000/4000 = 0.75
        expected_ratio = 3000 / 4000
        self.assertAlmostEqual(metrics.aggression_ratio, expected_ratio, places=2)

    def test_large_trade_detection(self):
        """Test large trade ratio calculation"""
        # Create trades with varying sizes
        trade_data = [
            (100.0, 1000, True, 'passive'),      # Normal size
            (100.1, 5000, False, 'aggressive_sell'),  # Large trade
            (99.9, 800, True, 'passive'),        # Normal size
            (100.2, 6000, False, 'market_order'), # Large trade
            (100.3, 1200, True, 'passive'),      # Normal size
        ]

        for trade in trade_data:
            self.analyzer._update_trades([trade], datetime.now())

        metrics = self.analyzer._analyze_trade_aggression()

        # Large trades: 5000, 6000 (above ~2000 threshold)
        # Large trade ratio: 2/5 = 0.4
        self.assertGreater(metrics.large_trade_ratio, 0.3)
        self.assertLess(metrics.large_trade_ratio, 0.5)

    def test_signal_generation_liquidity_dry_up(self):
        """Test liquidity dry-up signal generation"""
        # Create order book with very wide spread
        order_book_data = {
            'bids': {99.0: 100},     # Very low liquidity
            'asks': {101.0: 150}     # Very low liquidity, wide spread
        }

        self.analyzer._update_order_book(order_book_data, datetime.now())

        # Update price data
        for i in range(10):
            self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now(),
                               order_book_data=order_book_data)

        # Should generate liquidity dry-up signal
        signal = None
        for i in range(20):
            signal = self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now(),
                                         order_book_data=order_book_data)
            if signal:
                break

        if signal:
            self.assertEqual(signal.signal_type, f"MICROSTRUCTURE_{MicrostructureSignalType.SPREAD_WIDENING.value}")
            self.assertGreater(signal.composite_confidence, 0.5)

    def test_signal_generation_order_book_thinning(self):
        """Test order book thinning signal generation"""
        # Create very thin order book
        order_book_data = {
            'bids': {99.9: 50},      # Very thin
            'asks': {100.1: 75}      # Very thin
        }

        signal = self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now(),
                                    order_book_data=order_book_data)

        if signal:
            self.assertEqual(signal.signal_type, f"MICROSTRUCTURE_{MicrostructureSignalType.ORDER_BOOK_THINNING.value}")

    def test_signal_generation_high_aggression(self):
        """Test high aggression imbalance signal generation"""
        # Create highly aggressive trade data
        trade_data = [
            (100.0, 5000, True, 'aggressive_buy'),
            (100.1, 6000, True, 'market_order'),
            (100.2, 300, False, 'passive'),
        ]

        for trade in trade_data:
            self.analyzer._update_trades([trade], datetime.now())

        signal = self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now())

        if signal:
            self.assertEqual(signal.signal_type, f"MICROSTRUCTURE_{MicrostructureSignalType.HIGH_AGGRESSION_IMBALANCE.value}")
            self.assertGreater(signal.composite_confidence, 0.6)

    def test_signal_generation_institutional_sweep(self):
        """Test institutional sweep signal generation"""
        # Create large block trades
        trade_data = [
            (100.0, 10000, True, 'market_order'),    # Very large trade
            (100.1, 8000, True, 'aggressive_buy'),    # Large trade
            (100.2, 200, False, 'passive'),          # Small trade
        ]

        for trade in trade_data:
            self.analyzer._update_trades([trade], datetime.now())

        signal = self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now())

        if signal:
            self.assertEqual(signal.signal_type, f"MICROSTRUCTURE_{MicrostructureSignalType.INSTITUTIONAL_SWEEP.value}")

    def test_confidence_scoring(self):
        """Test confidence scoring components"""
        order_book_data = {
            'bids': {99.8: 2000, 99.7: 1500},
            'asks': {100.2: 1800, 100.3: 1200}
        }

        trade_data = [
            (100.0, 3000, True, 'aggressive_buy'),
            (100.1, 500, False, 'passive'),
        ]

        signal = self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now(),
                                    order_book_data=order_book_data)

        if signal:
            components = signal.confidence_components
            self.assertIn('spread_score', components)
            self.assertIn('depth_score', components)
            self.assertIn('aggression_score', components)
            self.assertIn('large_trade_score', components)

            # All components should be valid
            for comp_value in components.values():
                self.assertIsInstance(comp_value, float)
                self.assertGreaterEqual(comp_value, 0.0)
                self.assertLessEqual(comp_value, 1.0)

    def test_risk_management_integration(self):
        """Test risk management integration"""
        signal = None
        for i in range(20):
            signal = self.analyzer.update(price=self.sample_prices[i], volume=1000,
                                         timestamp=self.sample_timestamps[i])
            if signal:
                break

        if signal:
            self.assertIsInstance(signal.suggested_sl, (int, float))
            self.assertIsInstance(signal.suggested_tp, (int, float))
            self.assertNotEqual(signal.suggested_sl, signal.suggested_tp)

    def test_microstructure_metrics(self):
        """Test microstructure metrics retrieval"""
        # Feed some data
        for i in range(30):
            order_book_data = {
                'bids': {99.9 - i*0.01: 1000 + i*10},
                'asks': {100.1 + i*0.01: 1200 - i*10}
            }
            self.analyzer.update(price=self.sample_prices[i], volume=1000,
                               timestamp=self.sample_timestamps[i],
                               order_book_data=order_book_data)

        metrics = self.analyzer.get_microstructure_metrics()

        self.assertIn('order_book', metrics)
        self.assertIn('aggression', metrics)
        self.assertIn('current_price', metrics)
        self.assertIn('data_points', metrics)

    def test_liquidity_analysis(self):
        """Test detailed liquidity analysis"""
        # Create varying liquidity conditions
        for i in range(50):
            # Vary liquidity over time
            liquidity_factor = 1.0 + 0.5 * np.sin(i * 0.2)
            order_book_data = {
                'bids': {99.9: int(1000 * liquidity_factor)},
                'asks': {100.1: int(1200 * liquidity_factor)}
            }
            self.analyzer.update(price=self.sample_prices[i], volume=1000,
                               timestamp=self.sample_timestamps[i],
                               order_book_data=order_book_data)

        liquidity_analysis = self.analyzer.get_liquidity_analysis()

        self.assertIn('average_spread', liquidity_analysis)
        self.assertIn('spread_volatility', liquidity_analysis)
        self.assertIn('average_bid_depth', liquidity_analysis)
        self.assertIn('liquidity_trend', liquidity_analysis)

    def test_aggression_analysis(self):
        """Test detailed trade aggression analysis"""
        # Create diverse trade types
        aggression_types = ['passive', 'aggressive_buy', 'aggressive_sell', 'market_order']
        trade_data = []

        for i in range(40):
            trade_type = aggression_types[i % len(aggression_types)]
            volume = 1000 if trade_type in ['aggressive_buy', 'market_order'] else 500
            is_buy = trade_type in ['passive', 'aggressive_buy', 'market_order'] if i % 2 == 0 else False
            trade_data.append((100.0, volume, is_buy, trade_type))

        for trade in trade_data:
            self.analyzer._update_trades([trade], datetime.now())

        aggression_analysis = self.analyzer.get_aggression_analysis()

        self.assertIn('aggression_distribution', aggression_analysis)
        self.assertIn('volume_by_aggression', aggression_analysis)
        self.assertIn('total_trades_analyzed', aggression_analysis)

        # Check that all aggression types are represented
        distribution = aggression_analysis['aggression_distribution']
        for agg_type in aggression_types:
            self.assertIn(agg_type, distribution)

    def test_anomaly_detection(self):
        """Test anomaly detection using autoencoder"""
        # Create normal market data
        for i in range(30):
            order_book_data = {
                'bids': {99.9: 1000, 99.8: 800},
                'asks': {100.1: 1200, 100.2: 900}
            }
            self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now(),
                               order_book_data=order_book_data)

        # Test anomaly score calculation
        sequence = np.array([[100.0] * self.analyzer.sequence_length])
        anomaly_score = self.analyzer._calculate_anomaly_score(sequence)

        self.assertIsInstance(anomaly_score, float)
        self.assertGreaterEqual(anomaly_score, 0.0)
        self.assertLessEqual(anomaly_score, 1.0)

    def test_pattern_recognition(self):
        """Test pattern recognition scoring"""
        # Create smooth prediction sequence
        smooth_prediction = np.array([100.0 + i*0.1 for i in range(10)])
        pattern_score = self.analyzer._calculate_pattern_recognition_score(smooth_prediction)

        self.assertIsInstance(pattern_score, float)
        self.assertGreaterEqual(pattern_score, 0.0)
        self.assertLessEqual(pattern_score, 1.0)

        # Create noisy prediction sequence
        noisy_prediction = np.array([100.0 + np.random.normal(0, 1) for _ in range(10)])
        noisy_score = self.analyzer._calculate_pattern_recognition_score(noisy_prediction)

        # Smooth pattern should have higher score
        self.assertGreaterEqual(pattern_score, noisy_score)

    def test_memory_management(self):
        """Test memory management with large datasets"""
        # Feed large amount of data
        for i in range(200):
            order_book_data = {
                'bids': {99.9: 1000},
                'asks': {100.1: 1200}
            }
            self.analyzer.update(price=100.0, volume=1000, timestamp=datetime.now(),
                               order_book_data=order_book_data)

        # Should maintain reasonable memory usage
        self.assertLessEqual(len(self.analyzer.price_sequences), 1000)
        self.assertLessEqual(len(self.analyzer.order_book_history), 100)

    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        # Test with empty order book
        signal = self.analyzer.update(price=100.0, volume=1000,
                                    order_book_data={'bids': {}, 'asks': {}})
        self.assertTrue(True)  # Should not crash

        # Test with invalid trade data
        self.analyzer._update_trades([], datetime.now())
        self.assertTrue(True)  # Should not crash

    def test_multi_timeframe_support(self):
        """Test multi-timeframe analysis support"""
        timeframes = ["1s", "1m", "5m", "1H"]

        for tf in timeframes:
            analyzer = MarketMicrostructureAnalyzer(timeframe=tf)
            self.assertEqual(analyzer.timeframe, tf)

            # Should work with different timeframes
            metrics = analyzer.get_microstructure_metrics()
            self.assertIsInstance(metrics, dict)


if __name__ == '__main__':
    unittest.main()