"""
Backtesting Integration System for Nautilus Trader Engine
Provides comprehensive backtesting capabilities for indicators and strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import asyncio
from scipy import stats
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestMode(Enum):
    """Backtesting modes."""
    SINGLE_RUN = "single_run"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    OPTIMIZATION = "optimization"


class PerformanceMetric(Enum):
    """Performance metrics for backtesting."""
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    VOLATILITY = "volatility"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    CALMAR_RATIO = "calmar_ratio"
    INFORMATION_RATIO = "information_ratio"


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    commission: float = 0.001  # 0.1%
    slippage: float = 0.0005  # 0.05%
    benchmark_symbol: Optional[str] = None
    risk_free_rate: float = 0.02
    mode: BacktestMode = BacktestMode.SINGLE_RUN
    walk_forward_window: Optional[int] = None  # days
    monte_carlo_runs: int = 1000
    optimization_params: Optional[Dict[str, Any]] = None


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    symbol: str
    side: str  # 'buy' or 'sell'
    pnl: float = field(init=False)
    pnl_pct: float = field(init=False)

    def __post_init__(self):
        self.pnl = (self.exit_price - self.entry_price) * self.quantity if self.side == 'buy' else (self.entry_price - self.exit_price) * self.quantity
        self.pnl_pct = (self.exit_price / self.entry_price - 1) if self.side == 'buy' else (1 - self.exit_price / self.entry_price)


@dataclass
class BacktestResult:
    """Results from a backtest run."""
    config: BacktestConfig
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    drawdown_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    risk_metrics: Dict[str, float] = field(default_factory=dict)
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class SignalGenerator(ABC):
    """Abstract base class for signal generators."""

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Generate trading signals from market data."""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameters."""
        pass

    @abstractmethod
    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set parameters."""
        pass


class IndicatorSignalGenerator(SignalGenerator):
    """Signal generator based on technical indicators."""

    def __init__(self, indicator_class: Type, parameters: Dict[str, Any]):
        self.indicator_class = indicator_class
        self.parameters = parameters.copy()
        self.indicator_instance = None

    def generate_signals(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Generate signals using the indicator."""
        if self.indicator_instance is None:
            self.indicator_instance = self.indicator_class(**self.parameters)

        signals = []
        for i in range(len(data)):
            current_data = data.iloc[:i+1]
            signal = self.indicator_instance.update(current_data)
            signals.append(signal)

        result_df = data.copy()
        result_df['signal'] = signals
        return result_df

    def get_parameters(self) -> Dict[str, Any]:
        return self.parameters.copy()

    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        self.parameters.update(parameters)
        self.indicator_instance = None  # Force recreation with new parameters


class StrategyBacktester:
    """
    Main backtesting engine for strategies and indicators.
    """

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.signal_generator: Optional[SignalGenerator] = None

    def set_signal_generator(self, generator: SignalGenerator) -> None:
        """Set the signal generator for the backtest."""
        self.signal_generator = generator

    def run_backtest(self, market_data: pd.DataFrame) -> BacktestResult:
        """Run the backtest."""
        start_time = time.time()

        # Filter data by date range
        mask = (market_data.index >= self.config.start_date) & (market_data.index <= self.config.end_date)
        data = market_data[mask].copy()

        if data.empty:
            raise ValueError("No data available for the specified date range")

        # Generate signals
        if self.signal_generator:
            data = self.signal_generator.generate_signals(data)

        # Execute trades based on signals
        result = self._execute_trades(data)

        result.execution_time = time.time() - start_time
        return result

    def _execute_trades(self, data: pd.DataFrame) -> BacktestResult:
        """Execute trades based on signals."""
        result = BacktestResult(config=self.config)
        capital = self.config.initial_capital
        position = 0
        entry_price = 0

        equity_curve = [(data.index[0], capital)]
        drawdown_curve = [(data.index[0], 0.0)]

        peak_equity = capital

        for i, (timestamp, row) in enumerate(data.iterrows()):
            current_price = row['close']

            # Check for signals
            if 'signal' in row and not np.isnan(row['signal']):
                signal = row['signal']

                # Entry signal
                if position == 0 and signal > 0:
                    quantity = (capital * 0.1) / current_price  # 10% of capital
                    entry_price = current_price * (1 + self.config.slippage)
                    position = quantity
                    capital -= quantity * entry_price * (1 + self.config.commission)

                # Exit signal
                elif position != 0 and signal < 0:
                    exit_price = current_price * (1 - self.config.slippage)
                    pnl = (exit_price - entry_price) * position * (1 - self.config.commission)

                    # Record trade
                    trade = Trade(
                        entry_time=timestamp if i > 0 else data.index[i-1],
                        exit_time=timestamp,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        quantity=position,
                        symbol=row.get('symbol', 'UNKNOWN'),
                        side='buy'
                    )
                    result.trades.append(trade)

                    capital += position * exit_price * (1 - self.config.commission)
                    position = 0

            # Update equity curve
            current_equity = capital + (position * current_price if position != 0 else 0)
            equity_curve.append((timestamp, current_equity))

            # Update drawdown
            peak_equity = max(peak_equity, current_equity)
            drawdown = (peak_equity - current_equity) / peak_equity
            drawdown_curve.append((timestamp, drawdown))

        result.equity_curve = equity_curve
        result.drawdown_curve = drawdown_curve

        # Calculate performance metrics
        result.performance_metrics = self._calculate_performance_metrics(result)
        result.risk_metrics = self._calculate_risk_metrics(result)

        return result

    def _calculate_performance_metrics(self, result: BacktestResult) -> Dict[str, float]:
        """Calculate performance metrics."""
        if not result.equity_curve:
            return {}

        initial_value = result.equity_curve[0][1]
        final_value = result.equity_curve[-1][1]

        # Basic returns
        total_return = (final_value - initial_value) / initial_value

        # Annualized return
        days = (result.config.end_date - result.config.start_date).days
        if days > 0:
            annualized_return = (1 + total_return) ** (365 / days) - 1
        else:
            annualized_return = 0

        # Win rate
        winning_trades = sum(1 for trade in result.trades if trade.pnl > 0)
        win_rate = winning_trades / len(result.trades) if result.trades else 0

        # Profit factor
        gross_profit = sum(trade.pnl for trade in result.trades if trade.pnl > 0)
        gross_loss = abs(sum(trade.pnl for trade in result.trades if trade.pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            PerformanceMetric.TOTAL_RETURN.value: total_return,
            PerformanceMetric.ANNUALIZED_RETURN.value: annualized_return,
            PerformanceMetric.WIN_RATE.value: win_rate,
            PerformanceMetric.PROFIT_FACTOR.value: profit_factor
        }

    def _calculate_risk_metrics(self, result: BacktestResult) -> Dict[str, float]:
        """Calculate risk metrics."""
        if not result.equity_curve:
            return {}

        equity_values = [eq for _, eq in result.equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]

        if len(returns) == 0:
            return {}

        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252)

        # Sharpe ratio
        excess_returns = returns - self.config.risk_free_rate / 252
        sharpe_ratio = np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0

        # Sortino ratio
        downside_returns = returns[returns < 0]
        sortino_ratio = np.mean(excess_returns) / np.std(downside_returns) if len(downside_returns) > 0 else 0

        # Maximum drawdown
        max_drawdown = max(dd for _, dd in result.drawdown_curve)

        # Calmar ratio
        annualized_return = result.performance_metrics.get(PerformanceMetric.ANNUALIZED_RETURN.value, 0)
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0

        return {
            PerformanceMetric.VOLATILITY.value: volatility,
            PerformanceMetric.SHARPE_RATIO.value: sharpe_ratio,
            PerformanceMetric.SORTINO_RATIO.value: sortino_ratio,
            PerformanceMetric.MAX_DRAWDOWN.value: max_drawdown,
            PerformanceMetric.CALMAR_RATIO.value: calmar_ratio
        }


class WalkForwardAnalyzer:
    """Walk-forward analysis for robust backtesting."""

    def __init__(self, window_size: int = 252):  # 1 year
        self.window_size = window_size

    def analyze(self, market_data: pd.DataFrame, signal_generator: SignalGenerator,
               config: BacktestConfig) -> List[BacktestResult]:
        """Perform walk-forward analysis."""
        results = []

        start_date = config.start_date
        end_date = config.end_date

        current_start = start_date

        while current_start < end_date:
            # Define training and testing windows
            train_end = current_start + timedelta(days=self.window_size)
            test_end = train_end + timedelta(days=self.window_size // 4)  # 3 months test

            if test_end > end_date:
                test_end = end_date

            # Training window
            train_config = BacktestConfig(
                start_date=current_start,
                end_date=train_end,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage
            )

            # Optimize parameters on training data
            train_data = market_data[
                (market_data.index >= current_start) & (market_data.index <= train_end)
            ]

            if len(train_data) < 50:  # Minimum data requirement
                break

            # For now, just run backtest on training data
            backtester = StrategyBacktester(train_config)
            backtester.set_signal_generator(signal_generator)
            train_result = backtester.run_backtest(train_data)

            # Testing window
            test_config = BacktestConfig(
                start_date=train_end,
                end_date=test_end,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage
            )

            test_data = market_data[
                (market_data.index >= train_end) & (market_data.index <= test_end)
            ]

            if not test_data.empty:
                backtester = StrategyBacktester(test_config)
                backtester.set_signal_generator(signal_generator)
                test_result = backtester.run_backtest(test_data)
                results.append(test_result)

            current_start = test_end

        return results


class MonteCarloAnalyzer:
    """Monte Carlo analysis for robustness testing."""

    def __init__(self, num_simulations: int = 1000):
        self.num_simulations = num_simulations

    def analyze(self, market_data: pd.DataFrame, signal_generator: SignalGenerator,
               config: BacktestConfig) -> Dict[str, Any]:
        """Perform Monte Carlo analysis."""
        results = []

        for i in range(self.num_simulations):
            # Bootstrap sample from original data
            sample_indices = np.random.choice(len(market_data), size=len(market_data), replace=True)
            sample_data = market_data.iloc[sample_indices].sort_index()

            # Run backtest on sample
            backtester = StrategyBacktester(config)
            backtester.set_signal_generator(signal_generator)
            result = backtester.run_backtest(sample_data)
            results.append(result)

        # Analyze distribution of results
        total_returns = [r.performance_metrics.get(PerformanceMetric.TOTAL_RETURN.value, 0) for r in results]
        sharpe_ratios = [r.risk_metrics.get(PerformanceMetric.SHARPE_RATIO.value, 0) for r in results]
        max_drawdowns = [r.risk_metrics.get(PerformanceMetric.MAX_DRAWDOWN.value, 0) for r in results]

        analysis = {
            "total_return": {
                "mean": np.mean(total_returns),
                "std": np.std(total_returns),
                "percentile_5": np.percentile(total_returns, 5),
                "percentile_95": np.percentile(total_returns, 95)
            },
            "sharpe_ratio": {
                "mean": np.mean(sharpe_ratios),
                "std": np.std(sharpe_ratios),
                "percentile_5": np.percentile(sharpe_ratios, 5),
                "percentile_95": np.percentile(sharpe_ratios, 95)
            },
            "max_drawdown": {
                "mean": np.mean(max_drawdowns),
                "std": np.std(max_drawdowns),
                "percentile_5": np.percentile(max_drawdowns, 5),
                "percentile_95": np.percentile(max_drawdowns, 95)
            },
            "num_simulations": self.num_simulations
        }

        return analysis


class BacktestOptimizer:
    """Parameter optimization for backtesting."""

    def __init__(self, optimization_config: Dict[str, Any]):
        self.config = optimization_config
        self.executor = ProcessPoolExecutor(max_workers=4)

    def optimize(self, market_data: pd.DataFrame, signal_generator: SignalGenerator,
                base_config: BacktestConfig, parameter_ranges: Dict[str, Tuple[float, float]]) -> Dict[str, Any]:
        """Optimize parameters using grid search or random search."""
        futures = []
        results = []

        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations(parameter_ranges)

        for params in param_combinations[:50]:  # Limit to 50 combinations for demo
            future = self.executor.submit(self._evaluate_parameters, market_data, signal_generator, base_config, params)
            futures.append((params, future))

        # Collect results
        for params, future in futures:
            try:
                result = future.result()
                results.append((params, result))
            except Exception as e:
                logger.error(f"Error evaluating parameters {params}: {e}")

        # Find best parameters
        if results:
            best_params, best_result = max(results, key=lambda x: x[1].performance_metrics.get(PerformanceMetric.SHARPE_RATIO.value, 0))

            return {
                "best_parameters": best_params,
                "best_result": best_result,
                "all_results": results,
                "optimization_method": "grid_search"
            }

        return {}

    def _generate_parameter_combinations(self, parameter_ranges: Dict[str, Tuple[float, float]]) -> List[Dict[str, float]]:
        """Generate parameter combinations for optimization."""
        combinations = [{}]

        for param_name, (min_val, max_val) in parameter_ranges.items():
            new_combinations = []
            for combo in combinations:
                # Try 5 values for each parameter
                for val in np.linspace(min_val, max_val, 5):
                    new_combo = combo.copy()
                    new_combo[param_name] = val
                    new_combinations.append(new_combo)
            combinations = new_combinations

        return combinations

    def _evaluate_parameters(self, market_data: pd.DataFrame, signal_generator: SignalGenerator,
                           config: BacktestConfig, parameters: Dict[str, float]) -> BacktestResult:
        """Evaluate a parameter set."""
        # Update signal generator parameters
        signal_generator.set_parameters(parameters)

        # Run backtest
        backtester = StrategyBacktester(config)
        backtester.set_signal_generator(signal_generator)

        return backtester.run_backtest(market_data)


# Global backtesting manager
_backtesting_manager: Dict[str, StrategyBacktester] = {}


def get_backtesting_manager(name: str, config: BacktestConfig) -> StrategyBacktester:
    """Get or create a backtesting manager."""
    if name not in _backtesting_manager:
        _backtesting_manager[name] = StrategyBacktester(config)

    return _backtesting_manager[name]


# Convenience functions
def run_backtest(name: str, config: BacktestConfig, market_data: pd.DataFrame,
                signal_generator: Optional[SignalGenerator] = None) -> BacktestResult:
    """Run a backtest globally."""
    backtester = get_backtesting_manager(name, config)
    if signal_generator:
        backtester.set_signal_generator(signal_generator)
    return backtester.run_backtest(market_data)


def run_walk_forward_analysis(market_data: pd.DataFrame, signal_generator: SignalGenerator,
                            config: BacktestConfig, window_size: int = 252) -> List[BacktestResult]:
    """Run walk-forward analysis."""
    analyzer = WalkForwardAnalyzer(window_size)
    return analyzer.analyze(market_data, signal_generator, config)


def run_monte_carlo_analysis(market_data: pd.DataFrame, signal_generator: SignalGenerator,
                           config: BacktestConfig, num_simulations: int = 1000) -> Dict[str, Any]:
    """Run Monte Carlo analysis."""
    analyzer = MonteCarloAnalyzer(num_simulations)
    return analyzer.analyze(market_data, signal_generator, config)


if __name__ == "__main__":
    # Example usage
    import yfinance as yf

    # Download sample data
    data = yf.download("AAPL", start="2020-01-01", end="2023-01-01")
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
    data.columns = ['open', 'high', 'low', 'close', 'volume']

    # Create backtest configuration
    config = BacktestConfig(
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2023, 1, 1),
        initial_capital=100000.0
    )

    # Create signal generator (simplified example)
    class SimpleSignalGenerator(SignalGenerator):
        def generate_signals(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
            signals = []
            for i in range(len(data)):
                if i < 20:
                    signals.append(0)
                else:
                    sma_10 = data['close'].iloc[i-10:i].mean()
                    sma_20 = data['close'].iloc[i-20:i].mean()
                    signals.append(1 if sma_10 > sma_20 else -1)
            data_copy = data.copy()
            data_copy['signal'] = signals
            return data_copy

        def get_parameters(self) -> Dict[str, Any]:
            return {}

        def set_parameters(self, parameters: Dict[str, Any]) -> None:
            pass

    signal_generator = SimpleSignalGenerator()

    # Run backtest
    result = run_backtest("example", config, data, signal_generator)

    print(f"Total Return: {result.performance_metrics.get(PerformanceMetric.TOTAL_RETURN.value, 0):.2%}")
    print(f"Sharpe Ratio: {result.risk_metrics.get(PerformanceMetric.SHARPE_RATIO.value, 0):.2f}")
    print(f"Max Drawdown: {result.risk_metrics.get(PerformanceMetric.MAX_DRAWDOWN.value, 0):.2%}")
    print(f"Number of Trades: {len(result.trades)}")