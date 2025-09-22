"""Core engine for pairs trading analysis and backtesting."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from .data_models.data_models import PairData, PairStatistics, SignalType
from .indicator_suite import PairsIndicatorSuite
from .pair_selection import PairSelectionModule
from .spread_ratio_calculator import SpreadRatioCalculator
from .strategies.convergence_strategy import ConvergenceStrategy
from .strategies.divergence_strategy import DivergenceStrategy


class PairsTradingEngine:
    """Core engine for pairs trading analysis and backtesting."""

    def __init__(self, pair_selection_module: PairSelectionModule):
        self.pair_selection_module = pair_selection_module
        self.indicator_suite = PairsIndicatorSuite()
        self.spread_ratio_calculator = SpreadRatioCalculator()

    def analyze_pair(
        self, pair_data: PairData, strategy: Any, backtest_period: int = 252
    ) -> Dict[str, Any]:
        """Analyze a single pair with a given strategy."""
        stats = self.pair_selection_module.calculate_pair_statistics(
            pair_data.price_a, pair_data.price_b
        )

        if not stats.is_cointegrated:
            return {"error": "Pair is not cointegrated."}

        indicators = self._calculate_all_indicators(pair_data, stats)

        # Generate signals
        if isinstance(strategy, ConvergenceStrategy):
            signals = strategy.generate_signals(
                indicators["spread_z_score"], indicators["half_life"]
            )
        elif isinstance(strategy, DivergenceStrategy):
            signals = strategy.generate_signals(
                indicators["spread_z_score"], indicators["rolling_correlation"]
            )
        else:
            return {"error": "Unsupported strategy."}

        # Backtest
        backtest_results = self.backtest_strategy(pair_data, signals, backtest_period)

        return {
            "statistics": stats,
            "indicators": indicators,
            "signals": signals,
            "backtest_results": backtest_results,
        }

    def _calculate_all_indicators(
        self, pair_data: PairData, stats: PairStatistics
    ) -> Dict[str, np.ndarray]:
        """Calculate all relevant indicators for a pair."""
        spread = self.spread_ratio_calculator.calculate_spread(
            pair_data.price_a, pair_data.price_b, stats.hedge_ratio
        )
        ratio = self.spread_ratio_calculator.calculate_ratio(pair_data.price_a, pair_data.price_b)

        return {
            "spread_sma": self.indicator_suite.spread_sma(spread),
            "spread_ema": self.indicator_suite.spread_ema(spread),
            "spread_rsi": self.indicator_suite.spread_rsi(spread),
            "spread_z_score": self.indicator_suite.spread_z_score(spread),
            "half_life": self.indicator_suite.half_life_indicator(spread),
            "ratio_momentum": self.indicator_suite.ratio_momentum(ratio),
            "rolling_correlation": pd.Series(pair_data.price_a)
            .rolling(window=50)
            .corr(pd.Series(pair_data.price_b))
            .to_numpy(),
        }

    def backtest_strategy(
        self, pair_data: PairData, signals: List[Dict], backtest_period: int
    ) -> Dict[str, Any]:
        """Backtest a strategy and calculate performance."""
        returns = self._simulate_strategy_performance(pair_data, signals, backtest_period)
        return self._aggregate_backtest_results(returns)

    def _simulate_strategy_performance(
        self, pair_data: PairData, signals: List[Dict], backtest_period: int
    ) -> np.ndarray:
        """Simulate portfolio returns from signals."""
        prices_a = pair_data.price_a[-backtest_period:]
        prices_b = pair_data.price_b[-backtest_period:]
        returns = np.zeros(len(prices_a))
        position = 0

        for i in range(1, len(prices_a)):
            # Check for signals at this timestamp
            active_signal = next((s for s in signals if s.timestamp == len(pair_data.price_a) - backtest_period + i), None)

            if active_signal:
                if active_signal.signal_type == SignalType.BUY:
                    position = 1
                elif active_signal.signal_type == SignalType.SELL:
                    position = -1
                elif active_signal.signal_type == SignalType.EXIT:
                    position = 0

            # Calculate daily return
            if position == 1:  # Long spread (Buy A, Sell B)
                returns[i] = (prices_a[i] / prices_a[i - 1] - 1) - (prices_b[i] / prices_b[i - 1] - 1)
            elif position == -1:  # Short spread (Sell A, Buy B)
                returns[i] = (prices_b[i] / prices_b[i - 1] - 1) - (prices_a[i] / prices_a[i - 1] - 1)

        return returns

    def _aggregate_backtest_results(self, returns: np.ndarray) -> Dict[str, Any]:
        """Calculate summary statistics from returns."""
        total_return = np.sum(returns)
        sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        max_drawdown = np.min(np.cumsum(returns) - np.maximum.accumulate(np.cumsum(returns)))

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        }


# Example Usage
def create_sample_pair_data(length: int = 500) -> PairData:
    """Create sample correlated time series data for demonstration."""
    np.random.seed(42)
    price_a = 100 + np.random.randn(length).cumsum()
    price_b = price_a + 5 * np.random.randn(length)
    return PairData(
        timestamp=pd.to_datetime(pd.date_range(start="2022-01-01", periods=length)),
        price_a=price_a,
        price_b=price_b,
        volume_a=np.random.randint(1000, 5000, size=length),
        volume_b=np.random.randint(1000, 5000, size=length),
    )


def test_pairs_trading_engine():
    """Function to test the full pairs trading engine."""
    pair_data = create_sample_pair_data()
    pair_selection = PairSelectionModule()
    engine = PairsTradingEngine(pair_selection)

    # Test with Convergence Strategy
    convergence_strategy = ConvergenceStrategy(entry_z_score=2.0, exit_z_score=0.5)
    results = engine.analyze_pair(pair_data, convergence_strategy)

    print("--- Convergence Strategy Results ---")
    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        print(f"Sharpe Ratio: {results['backtest_results']['sharpe_ratio']:.2f}")
        print(f"Total Return: {results['backtest_results']['total_return']:.2%}")


if __name__ == "__main__":
    test_pairs_trading_engine()