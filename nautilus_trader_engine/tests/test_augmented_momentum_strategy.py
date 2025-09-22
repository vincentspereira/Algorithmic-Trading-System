import unittest
from datetime import datetime
import numpy as np

from nautilus_trader_engine.strategies.core.augmented_base_institutional_strategy import (
    AugmentedMomentumStrategy,
    MarketRegime,
    RiskLevel,
    SignalType,
)


class TestAugmentedMomentumStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = AugmentedMomentumStrategy(
            initial_capital=100000,
            max_position_size=0.1,
            risk_tolerance=RiskLevel.MEDIUM,
            custom_params={"lookback_period": 20},
        )

    def _generate_market_data(self, trend="up"):
        prices = {}
        for symbol in self.strategy.symbols:
            if trend == "up":
                prices[symbol] = np.linspace(100, 110, 20)
            elif trend == "down":
                prices[symbol] = np.linspace(110, 100, 20)
            else:  # sideways
                prices[symbol] = np.linspace(100, 101, 20)
        return prices

    def test_generate_buy_signal(self):
        market_prices = self._generate_market_data(trend="up")
        for symbol, prices in market_prices.items():
            self.strategy.price_history[symbol] = list(prices)
        signals = self.strategy.generate_augmented_signals({})
        for signal in signals.values():
            self.assertEqual(signal.signal_type, SignalType.BUY)
            self.assertGreater(signal.confidence, 0)

    def test_generate_sell_signal(self):
        market_prices = self._generate_market_data(trend="down")
        for symbol, prices in market_prices.items():
            self.strategy.price_history[symbol] = list(prices)
        signals = self.strategy.generate_augmented_signals({})
        for signal in signals.values():
            self.assertEqual(signal.signal_type, SignalType.SELL)
            self.assertGreater(signal.confidence, 0)

    def test_generate_hold_signal(self):
        market_prices = self._generate_market_data(trend="sideways")
        for symbol, prices in market_prices.items():
            self.strategy.price_history[symbol] = list(prices)
        signals = self.strategy.generate_augmented_signals({})
        for signal in signals.values():
            self.assertEqual(signal.signal_type, SignalType.HOLD)

    def test_detect_market_regime(self):
        market_prices = self._generate_market_data(trend="up")
        for symbol, prices in market_prices.items():
            self.strategy.price_history[symbol] = list(prices)
        regime = self.strategy.detect_market_regime({})
        self.assertEqual(regime, MarketRegime.TRENDING_UP)

    def test_run_strategy_cycle(self):
        market_prices = self._generate_market_data(trend="up")
        self.strategy.start_strategy()
        orders = []
        for i in range(20):
            tick_data = {symbol: {'price': prices[i]} for symbol, prices in market_prices.items()}
            orders.extend(self.strategy.run_strategy_cycle(tick_data))
        self.assertGreater(len(orders), 0)
        for order in orders:
            self.assertEqual(order.side, 'buy')


if __name__ == "__main__":
    unittest.main()