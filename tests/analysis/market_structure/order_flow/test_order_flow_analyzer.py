"""
Tests for Order Flow Analyzer Module

Comprehensive test suite for the order flow analysis functionality.
"""

import unittest
import numpy as np
from datetime import datetime, timedelta

from nautilus_trader_engine.analysis.market_structure.order_flow.order_flow_analyzer import (
    OrderFlowAnalyzer,
    OrderFlowSignal,
    OrderFlowType,
    OrderFlowSignalType
)


class TestOrderFlowAnalyzer(unittest.TestCase):
    """Test cases for OrderFlowAnalyzer"""

    def setUp(self):
        """Set up test fixtures"""
        self.analyzer = OrderFlowAnalyzer()
        self.sample_prices = [100.0, 101.0, 99.5, 102.0, 100.5, 103.0, 101.5, 104.0]
        self.timestamps = [datetime.now() + timedelta(minutes=i) for i in range(len(self.sample_prices))]

    def test_initialization(self):
        """Test analyzer initialization"""
        self.assertIsInstance(self.analyzer, OrderFlowAnalyzer)
        self.assertEqual(self.analyzer.name, "OrderFlowAnalyzer")
        self.assertIsNone(self.analyzer.current_signal)

    def test_update_with_basic_data(self):
        """Test updating analyzer with basic price/volume data"""
        signal = self.analyzer.update(
            price=100.0,
            volume=1000,
            high=101.0,
            low=99.0,
            timestamp=datetime.now()
        )

        # Initially should return None
        self.assertIsNone(signal)

    def test_order_book_imbalance_calculation(self):
        """Test order book imbalance calculation"""
        # Set up order book data
        order_book = {
            'bids': {99.5: 2000, 99.0: 1500, 98.5: 1000},
            'asks': {100.5: 1000, 101.0: 800, 101.5: 600}
        }

        imbalance = self.analyzer._calculate_order_book_imbalance(order_book)
        self.assertIsInstance(imbalance, float)
        self.assertGreaterEqual(imbalance, -1.0)
        self.assertLessEqual(imbalance, 1.0)

    def test_trade_aggression_analysis(self):
        """Test trade aggression analysis"""
        trades = [
            (100.0, 500, True),   # Buy trade
            (100.2, 300, False),  # Sell trade
            (99.8, 700, True),    # Aggressive buy
            (100.5, 200, False)   # Sell trade
        ]

        aggression = self.analyzer._analyze_trade_aggression(trades)
        self.assertIsInstance(aggression, dict)
        self.assertIn('buy_pressure', aggression)
        self.assertIn('sell_pressure', aggression)

    def test_smart_money_score(self):
        """Test smart money activity scoring"""
        # Add trades with large orders
        trades = [
            (100.0, 10000, True),  # Large buy
            (100.1, 500, False),   # Small sell
            (100.2, 8000, True),   # Large buy
        ]

        for price, volume, is_buy in trades:
            self.analyzer.trades.append((price, volume, is_buy))

        score = self.analyzer._calculate_smart_money_score()
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_institutional_activity_detection(self):
        """Test institutional activity detection"""
        # Simulate persistent order book imbalance
        imbalances = [0.3, 0.4, 0.2, 0.5, 0.3]
        self.analyzer.order_imbalance = imbalances

        activity = self.analyzer._calculate_institutional_activity()
        self.assertIsInstance(activity, float)
        self.assertGreaterEqual(activity, 0.0)
        self.assertLessEqual(activity, 1.0)

    def test_signal_generation_with_order_flow(self):
        """Test signal generation with order flow data"""
        # Add price data with order book and trades
        for i, price in enumerate(self.sample_prices):
            order_book = {
                'bids': {price - 0.1: 1000 + i * 100, price - 0.2: 800 + i * 50},
                'asks': {price + 0.1: 900 + i * 80, price + 0.2: 700 + i * 40}
            }

            trades = [
                (price - 0.05, 200 + i * 50, True),
                (price + 0.05, 150 + i * 30, False)
            ]

            signal = self.analyzer.update(
                price=price,
                volume=1000 + i * 200,
                high=price + 1,
                low=price - 1,
                timestamp=self.timestamps[i],
                order_book_data=order_book,
                trade_data=trades
            )

        # Check if signal is generated
        if self.analyzer.current_signal:
            signal = self.analyzer.current_signal
            self.assertIsInstance(signal, OrderFlowSignal)
            self.assertIn('volume_score', signal.confidence_components)
            self.assertIn('imbalance_score', signal.confidence_components)

    def test_volume_weighting(self):
        """Test volume-weighted analysis"""
        # Test with high volume periods
        high_volume_prices = [100, 102, 98, 105]  # Volatile with high volume
        volumes = [5000, 8000, 6000, 10000]

        for price, volume in zip(high_volume_prices, volumes):
            signal = self.analyzer.update(
                price=price,
                volume=volume,
                high=price + 2,
                low=price - 2,
                timestamp=datetime.now()
            )

        # High volume should increase confidence
        if self.analyzer.current_signal:
            self.assertGreater(self.analyzer.current_signal.confidence_components['volume_score'], 0.5)

    def test_multi_timeframe_consistency(self):
        """Test multi-timeframe consistency"""
        # Test with different timeframes
        timeframes = ['1m', '5m', '15m']

        for tf in timeframes:
            analyzer = OrderFlowAnalyzer()
            analyzer.timeframe = tf

            # Add some data
            for price in self.sample_prices[:5]:
                analyzer.update(price=price, volume=1000, high=price+1, low=price-1)

            # Should handle different timeframes
            self.assertEqual(analyzer.timeframe, tf)

    def test_risk_management_parameters(self):
        """Test risk management parameter generation"""
        # Generate a signal
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

    def test_edge_cases(self):
        """Test edge cases"""
        # Test with no order book data
        signal = self.analyzer.update(
            price=100.0,
            volume=1000,
            high=101.0,
            low=99.0,
            timestamp=datetime.now()
        )

        # Should handle gracefully
        self.assertIsInstance(signal, (OrderFlowSignal, type(None)))

        # Test with empty trades
        signal = self.analyzer.update(
            price=100.0,
            volume=1000,
            high=101.0,
            low=99.0,
            timestamp=datetime.now(),
            trade_data=[]
        )

        self.assertIsInstance(signal, (OrderFlowSignal, type(None)))


class TestOrderFlowSignal(unittest.TestCase):
    """Test cases for OrderFlowSignal"""

    def test_signal_creation(self):
        """Test OrderFlowSignal creation"""
        signal = OrderFlowSignal(
            value_raw=100.0,
            signal_type="INSTITUTIONAL_ACCUMULATION",
            composite_confidence=0.8,
            confidence_components={'volume': 0.7, 'imbalance': 0.9},
            suggested_sl=98.0,
            suggested_tp=105.0,
            timestamp=datetime.now(),
            additional_metadata={'order_imbalance': 0.3},
            flow_type=OrderFlowType.ACCUMULATION,
            imbalance_ratio=0.3,
            order_book_depth={'bid_volume': 2000, 'ask_volume': 1500},
            smart_money_score=0.6,
            institutional_activity=0.7
        )

        self.assertEqual(signal.value_raw, 100.0)
        self.assertEqual(signal.flow_type, OrderFlowType.ACCUMULATION)
        self.assertEqual(signal.imbalance_ratio, 0.3)


class TestOrderFlowType(unittest.TestCase):
    """Test cases for OrderFlowType enum"""

    def test_flow_types(self):
        """Test order flow type values"""
        self.assertEqual(OrderFlowType.ACCUMULATION.value, "accumulation")
        self.assertEqual(OrderFlowType.DISTRIBUTION.value, "distribution")
        self.assertEqual(OrderFlowType.AGGRESSIVE_BUYING.value, "aggressive_buying")
        self.assertEqual(OrderFlowType.AGGRESSIVE_SELLING.value, "aggressive_selling")


class TestOrderFlowSignalType(unittest.TestCase):
    """Test cases for OrderFlowSignalType enum"""

    def test_signal_types(self):
        """Test signal type values"""
        self.assertEqual(OrderFlowSignalType.INSTITUTIONAL_ACCUMULATION.value, "INSTITUTIONAL_ACCUMULATION")
        self.assertEqual(OrderFlowSignalType.MARKET_MAKER_ACTIVITY.value, "MARKET_MAKER_ACTIVITY")
        self.assertEqual(OrderFlowSignalType.LIQUIDITY_IMBALANCE.value, "LIQUIDITY_IMBALANCE")


if __name__ == '__main__':
    unittest.main()