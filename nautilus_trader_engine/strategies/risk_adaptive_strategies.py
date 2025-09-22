"""
Risk-Adaptive Strategies for Nautilus Trader Engine
Strategies that dynamically adjust risk parameters based on market conditions and performance.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from scipy import stats
import time

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classifications."""
    VERY_LOW = 0.2
    LOW = 0.4
    MODERATE = 0.6
    HIGH = 0.8
    VERY_HIGH = 1.0


class MarketCondition(Enum):
    """Market condition classifications."""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"


@dataclass
class RiskMetrics:
    """Current risk metrics for the strategy."""
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 1.0
    var_95: float = 0.0  # Value at Risk 95%
    expected_shortfall: float = 0.0
    concentration_risk: float = 0.0
    liquidity_risk: float = 0.0


@dataclass
class AdaptiveRiskParameters:
    """Adaptive risk parameters."""
    position_size_limit: float = 0.1  # Max position size as % of capital
    max_open_positions: int = 5
    stop_loss_multiplier: float = 1.0
    take_profit_multiplier: float = 2.0
    max_daily_loss: float = 0.05  # Max daily loss as % of capital
    max_total_drawdown: float = 0.15  # Max total drawdown
    volatility_adjustment: float = 1.0
    correlation_limit: float = 0.7
    sector_exposure_limit: float = 0.3
    rebalancing_frequency: str = "daily"


class RiskAssessmentEngine:
    """
    Engine for assessing and adapting to market risk conditions.
    """

    def __init__(self):
        self.risk_history: List[Tuple[datetime, RiskMetrics]] = []
        self.market_condition_history: List[Tuple[datetime, MarketCondition]] = []
        self.adaptation_history: List[Tuple[datetime, AdaptiveRiskParameters]] = []

    def assess_market_condition(self, market_data: pd.DataFrame,
                              portfolio_data: Optional[pd.DataFrame] = None) -> MarketCondition:
        """Assess current market condition."""
        if len(market_data) < 30:
            return MarketCondition.SIDEWAYS

        # Calculate trend indicators
        prices = market_data['close']
        sma_50 = prices.rolling(50).mean()
        sma_200 = prices.rolling(200).mean()

        current_price = prices.iloc[-1]
        current_sma_50 = sma_50.iloc[-1]
        current_sma_200 = sma_200.iloc[-1]

        # Trend assessment
        if current_price > current_sma_50 > current_sma_200:
            trend = "strong_bull"
        elif current_price > current_sma_50 and current_sma_50 < current_sma_200:
            trend = "weak_bull"
        elif current_price < current_sma_50 < current_sma_200:
            trend = "strong_bear"
        elif current_price < current_sma_50 and current_sma_50 > current_sma_200:
            trend = "weak_bear"
        else:
            trend = "sideways"

        # Volatility assessment
        returns = prices.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized

        # Determine market condition
        if volatility > 0.4:  # Very high volatility
            return MarketCondition.CRISIS
        elif volatility > 0.25:  # High volatility
            return MarketCondition.HIGH_VOLATILITY
        elif volatility < 0.15:  # Low volatility
            return MarketCondition.LOW_VOLATILITY
        elif trend in ["strong_bull", "weak_bull"]:
            return MarketCondition.BULL_MARKET
        elif trend in ["strong_bear", "weak_bear"]:
            return MarketCondition.BEAR_MARKET
        else:
            return MarketCondition.SIDEWAYS

    def calculate_risk_metrics(self, portfolio_data: pd.DataFrame,
                             market_data: pd.DataFrame) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        metrics = RiskMetrics()

        if portfolio_data.empty:
            return metrics

        # Portfolio returns
        portfolio_returns = portfolio_data['portfolio_value'].pct_change().dropna()

        if len(portfolio_returns) == 0:
            return metrics

        # Basic metrics
        metrics.volatility = portfolio_returns.std() * np.sqrt(252)

        # Sharpe ratio (assuming 2% risk-free rate)
        excess_returns = portfolio_returns - 0.02/252
        if excess_returns.std() > 0:
            metrics.sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

        # Drawdown calculation
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max

        metrics.current_drawdown = drawdown.iloc[-1]
        metrics.max_drawdown = drawdown.min()

        # Win rate and profit factor
        winning_trades = portfolio_data[portfolio_data['pnl'] > 0]
        losing_trades = portfolio_data[portfolio_data['pnl'] < 0]

        metrics.win_rate = len(winning_trades) / len(portfolio_data) if len(portfolio_data) > 0 else 0

        gross_profit = winning_trades['pnl'].sum() if not winning_trades.empty else 0
        gross_loss = abs(losing_trades['pnl'].sum()) if not losing_trades.empty else 0

        metrics.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # VaR calculation (95% confidence)
        if len(portfolio_returns) > 30:
            metrics.var_95 = np.percentile(portfolio_returns, 5)
            metrics.expected_shortfall = portfolio_returns[portfolio_returns <= metrics.var_95].mean()

        return metrics

    def adapt_risk_parameters(self, current_risk: RiskMetrics,
                            market_condition: MarketCondition,
                            base_parameters: AdaptiveRiskParameters) -> AdaptiveRiskParameters:
        """Adapt risk parameters based on current conditions."""
        adapted = AdaptiveRiskParameters()

        # Adjust based on drawdown
        drawdown_factor = 1.0
        if current_risk.current_drawdown < -0.05:  # 5% drawdown
            drawdown_factor = 0.8
        elif current_risk.current_drawdown < -0.10:  # 10% drawdown
            drawdown_factor = 0.6
        elif current_risk.current_drawdown < -0.15:  # 15% drawdown
            drawdown_factor = 0.4

        # Adjust based on volatility
        volatility_factor = 1.0
        if current_risk.volatility > 0.3:  # High volatility
            volatility_factor = 0.7
        elif current_risk.volatility > 0.2:  # Moderate volatility
            volatility_factor = 0.85

        # Adjust based on market condition
        market_factor = 1.0
        if market_condition == MarketCondition.CRISIS:
            market_factor = 0.3
        elif market_condition == MarketCondition.HIGH_VOLATILITY:
            market_factor = 0.6
        elif market_condition == MarketCondition.BEAR_MARKET:
            market_factor = 0.7
        elif market_condition == MarketCondition.BULL_MARKET:
            market_factor = 1.2

        # Combine factors
        overall_factor = min(1.5, max(0.2, drawdown_factor * volatility_factor * market_factor))

        # Apply adaptations
        adapted.position_size_limit = base_parameters.position_size_limit * overall_factor
        adapted.max_open_positions = max(1, int(base_parameters.max_open_positions * overall_factor))
        adapted.stop_loss_multiplier = base_parameters.stop_loss_multiplier * (2.0 - overall_factor)  # Tighter stops in risky conditions
        adapted.take_profit_multiplier = base_parameters.take_profit_multiplier * overall_factor
        adapted.max_daily_loss = base_parameters.max_daily_loss * (1.5 - overall_factor * 0.5)
        adapted.volatility_adjustment = overall_factor

        # Store adaptation
        self.adaptation_history.append((datetime.now(), adapted))

        return adapted


class RiskAdaptiveStrategy:
    """
    Base class for risk-adaptive trading strategies.
    """

    def __init__(self, name: str, initial_capital: float = 100000.0):
        self.name = name
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.risk_engine = RiskAssessmentEngine()
        self.base_risk_params = AdaptiveRiskParameters()
        self.current_risk_params = self.base_risk_params
        self.portfolio: Dict[str, Dict[str, Any]] = {}  # symbol -> position data
        self.trade_history: List[Dict[str, Any]] = []
        self.daily_pnl: List[Tuple[datetime, float]] = []

    def update_market_data(self, market_data: pd.DataFrame) -> None:
        """Update strategy with new market data."""
        # Assess market condition
        market_condition = self.risk_engine.assess_market_condition(market_data)

        # Calculate portfolio data for risk metrics
        portfolio_df = self._create_portfolio_dataframe()

        # Calculate risk metrics
        risk_metrics = self.risk_engine.calculate_risk_metrics(portfolio_df, market_data)

        # Adapt risk parameters
        self.current_risk_params = self.risk_engine.adapt_risk_parameters(
            risk_metrics, market_condition, self.base_risk_params
        )

        # Log adaptation
        logger.info(f"Risk adaptation for {self.name}: position_limit={self.current_risk_params.position_size_limit:.3f}, "
                   f"volatility_adj={self.current_risk_params.volatility_adjustment:.3f}")

    def _create_portfolio_dataframe(self) -> pd.DataFrame:
        """Create portfolio dataframe for risk calculations."""
        if not self.daily_pnl:
            return pd.DataFrame()

        dates, pnls = zip(*self.daily_pnl)
        portfolio_values = [self.initial_capital]
        current_value = self.initial_capital

        for pnl in pnls:
            current_value += pnl
            portfolio_values.append(current_value)

        df = pd.DataFrame({
            'date': dates,
            'pnl': pnls,
            'portfolio_value': portfolio_values[1:]
        })
        df.set_index('date', inplace=True)

        return df

    def can_open_position(self, symbol: str, position_size: float) -> Tuple[bool, str]:
        """Check if a position can be opened based on risk limits."""
        # Check position size limit
        max_position_value = self.current_capital * self.current_risk_params.position_size_limit
        if position_size > max_position_value:
            return False, f"Position size {position_size:.2f} exceeds limit {max_position_value:.2f}"

        # Check max open positions
        if len(self.portfolio) >= self.current_risk_params.max_open_positions:
            return False, f"Maximum open positions ({self.current_risk_params.max_open_positions}) reached"

        # Check daily loss limit
        today_pnl = sum(pnl for _, pnl in self.daily_pnl if _.date() == datetime.now().date())
        if today_pnl < -self.current_capital * self.current_risk_params.max_daily_loss:
            return False, f"Daily loss limit reached: {today_pnl:.2f}"

        # Check concentration risk
        total_exposure = sum(pos.get('value', 0) for pos in self.portfolio.values())
        if total_exposure + position_size > self.current_capital * 0.5:  # Max 50% concentration
            return False, "Concentration risk limit exceeded"

        return True, "OK"

    def calculate_position_size(self, symbol: str, entry_price: float,
                              stop_loss_price: float) -> float:
        """Calculate position size based on risk parameters."""
        # Risk per trade (1% of capital by default, adjusted by risk parameters)
        risk_per_trade = self.current_capital * 0.01 * self.current_risk_params.volatility_adjustment

        # Risk amount per share
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share == 0:
            return 0

        # Position size
        position_size = risk_per_trade / risk_per_share

        # Apply position size limit
        max_position_value = self.current_capital * self.current_risk_params.position_size_limit
        max_shares = max_position_value / entry_price
        position_size = min(position_size, max_shares)

        return position_size

    def open_position(self, symbol: str, quantity: float, entry_price: float,
                     stop_loss_price: float, take_profit_price: Optional[float] = None) -> bool:
        """Open a new position."""
        position_value = quantity * entry_price

        # Check if position can be opened
        can_open, reason = self.can_open_position(symbol, position_value)
        if not can_open:
            logger.warning(f"Cannot open position for {symbol}: {reason}")
            return False

        # Record position
        self.portfolio[symbol] = {
            'quantity': quantity,
            'entry_price': entry_price,
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'entry_time': datetime.now(),
            'value': position_value
        }

        # Update capital
        self.current_capital -= position_value

        logger.info(f"Opened position: {symbol} {quantity:.0f} shares @ {entry_price:.2f}")
        return True

    def close_position(self, symbol: str, exit_price: float, reason: str = "manual") -> bool:
        """Close an existing position."""
        if symbol not in self.portfolio:
            logger.warning(f"No position found for {symbol}")
            return False

        position = self.portfolio[symbol]
        quantity = position['quantity']
        entry_price = position['entry_price']

        # Calculate P&L
        pnl = (exit_price - entry_price) * quantity
        exit_value = quantity * exit_price

        # Update capital
        self.current_capital += exit_value

        # Record trade
        trade = {
            'symbol': symbol,
            'quantity': quantity,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'pnl': pnl,
            'entry_time': position['entry_time'],
            'exit_time': datetime.now(),
            'reason': reason
        }
        self.trade_history.append(trade)

        # Remove position
        del self.portfolio[symbol]

        logger.info(f"Closed position: {symbol} P&L: {pnl:.2f} ({reason})")
        return True

    def check_stop_loss_take_profit(self, market_data: pd.DataFrame) -> None:
        """Check and execute stop loss and take profit orders."""
        current_prices = {}
        if not market_data.empty:
            current_prices = {symbol: market_data['close'].iloc[-1] for symbol in self.portfolio.keys()}

        positions_to_close = []

        for symbol, position in self.portfolio.items():
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            stop_loss = position['stop_loss_price']
            take_profit = position.get('take_profit_price')

            # Check stop loss
            if position['quantity'] > 0:  # Long position
                if current_price <= stop_loss:
                    positions_to_close.append((symbol, current_price, "stop_loss"))
                elif take_profit and current_price >= take_profit:
                    positions_to_close.append((symbol, current_price, "take_profit"))
            else:  # Short position
                if current_price >= stop_loss:
                    positions_to_close.append((symbol, current_price, "stop_loss"))
                elif take_profit and current_price <= take_profit:
                    positions_to_close.append((symbol, current_price, "take_profit"))

        # Close positions
        for symbol, price, reason in positions_to_close:
            self.close_position(symbol, price, reason)

    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status."""
        total_value = self.current_capital
        for position in self.portfolio.values():
            # This is a simplified calculation - in reality you'd get current market prices
            total_value += position['value']

        return {
            'total_value': total_value,
            'cash': self.current_capital,
            'positions': len(self.portfolio),
            'unrealized_pnl': total_value - self.initial_capital,
            'current_risk_params': {
                'position_size_limit': self.current_risk_params.position_size_limit,
                'max_open_positions': self.current_risk_params.max_open_positions,
                'volatility_adjustment': self.current_risk_params.volatility_adjustment
            }
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        if not self.trade_history:
            return {}

        total_trades = len(self.trade_history)
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] < 0]

        total_pnl = sum(t['pnl'] for t in self.trade_history)
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0

        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'profit_factor': profit_factor,
            'avg_trade_pnl': total_pnl / total_trades if total_trades > 0 else 0
        }


class AdaptiveMeanReversionStrategy(RiskAdaptiveStrategy):
    """Adaptive mean reversion strategy with dynamic risk management."""

    def __init__(self, lookback_period: int = 20, entry_threshold: float = 2.0, **kwargs):
        super().__init__("Adaptive_Mean_Reversion", **kwargs)
        self.lookback_period = lookback_period
        self.entry_threshold = entry_threshold

    def generate_signals(self, market_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate trading signals based on mean reversion."""
        signals = []

        if len(market_data) < self.lookback_period:
            return signals

        # Calculate z-score
        prices = market_data['close']
        rolling_mean = prices.rolling(self.lookback_period).mean()
        rolling_std = prices.rolling(self.lookback_period).std()

        z_scores = (prices - rolling_mean) / rolling_std

        current_z = z_scores.iloc[-1]

        # Adjust threshold based on volatility
        adjusted_threshold = self.entry_threshold * self.current_risk_params.volatility_adjustment

        # Generate signals
        if current_z < -adjusted_threshold:
            # Oversold - buy signal
            signals.append({
                'symbol': market_data.index.name or 'UNKNOWN',
                'direction': 'buy',
                'strength': 'strong' if abs(current_z) > adjusted_threshold * 1.5 else 'moderate',
                'z_score': current_z,
                'threshold': adjusted_threshold
            })

        elif current_z > adjusted_threshold:
            # Overbought - sell signal
            signals.append({
                'symbol': market_data.index.name or 'UNKNOWN',
                'direction': 'sell',
                'strength': 'strong' if abs(current_z) > adjusted_threshold * 1.5 else 'moderate',
                'z_score': current_z,
                'threshold': adjusted_threshold
            })

        return signals

    def execute_signals(self, signals: List[Dict[str, Any]], market_data: pd.DataFrame) -> None:
        """Execute generated signals."""
        current_price = market_data['close'].iloc[-1]

        for signal in signals:
            symbol = signal['symbol']

            # Calculate stop loss and take profit
            volatility = market_data['close'].pct_change().std()
            stop_distance = current_price * volatility * self.current_risk_params.stop_loss_multiplier
            take_profit_distance = current_price * volatility * self.current_risk_params.take_profit_multiplier

            if signal['direction'] == 'buy':
                stop_loss_price = current_price - stop_distance
                take_profit_price = current_price + take_profit_distance
            else:
                stop_loss_price = current_price + stop_distance
                take_profit_price = current_price - take_profit_distance

            # Calculate position size
            position_size = self.calculate_position_size(symbol, current_price, stop_loss_price)

            if position_size > 0:
                quantity = position_size / current_price
                if signal['direction'] == 'buy':
                    quantity = quantity  # Long position
                else:
                    quantity = -quantity  # Short position

                self.open_position(symbol, quantity, current_price, stop_loss_price, take_profit_price)


class AdaptiveTrendFollowingStrategy(RiskAdaptiveStrategy):
    """Adaptive trend following strategy with dynamic risk management."""

    def __init__(self, fast_period: int = 10, slow_period: int = 30, **kwargs):
        super().__init__("Adaptive_Trend_Following", **kwargs)
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, market_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate trading signals based on trend following."""
        signals = []

        if len(market_data) < self.slow_period:
            return signals

        # Calculate moving averages
        prices = market_data['close']
        fast_ma = prices.rolling(self.fast_period).mean()
        slow_ma = prices.rolling(self.slow_period).mean()

        # Calculate trend strength
        trend_strength = abs(fast_ma - slow_ma) / slow_ma

        # Adjust for current risk parameters
        min_trend_strength = 0.02 / self.current_risk_params.volatility_adjustment  # Stronger trends in volatile markets

        current_trend = fast_ma.iloc[-1] - slow_ma.iloc[-1]
        current_trend_strength = trend_strength.iloc[-1]

        if current_trend > 0 and current_trend_strength > min_trend_strength:
            # Uptrend
            signals.append({
                'symbol': market_data.index.name or 'UNKNOWN',
                'direction': 'buy',
                'strength': 'strong' if current_trend_strength > min_trend_strength * 2 else 'moderate',
                'trend_strength': current_trend_strength,
                'fast_ma': fast_ma.iloc[-1],
                'slow_ma': slow_ma.iloc[-1]
            })

        elif current_trend < 0 and current_trend_strength > min_trend_strength:
            # Downtrend
            signals.append({
                'symbol': market_data.index.name or 'UNKNOWN',
                'direction': 'sell',
                'strength': 'strong' if current_trend_strength > min_trend_strength * 2 else 'moderate',
                'trend_strength': current_trend_strength,
                'fast_ma': fast_ma.iloc[-1],
                'slow_ma': slow_ma.iloc[-1]
            })

        return signals

    def execute_signals(self, signals: List[Dict[str, Any]], market_data: pd.DataFrame) -> None:
        """Execute generated signals."""
        current_price = market_data['close'].iloc[-1]

        for signal in signals:
            symbol = signal['symbol']

            # Calculate stop loss and take profit based on trend
            atr_period = 14
            high_low = market_data['high'] - market_data['low']
            high_close = (market_data['high'] - market_data['close'].shift(1)).abs()
            low_close = (market_data['low'] - market_data['close'].shift(1)).abs()
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(atr_period).mean().iloc[-1]

            stop_distance = atr * self.current_risk_params.stop_loss_multiplier
            take_profit_distance = atr * self.current_risk_params.take_profit_multiplier

            if signal['direction'] == 'buy':
                stop_loss_price = current_price - stop_distance
                take_profit_price = current_price + take_profit_distance
            else:
                stop_loss_price = current_price + stop_distance
                take_profit_price = current_price - take_profit_distance

            # Calculate position size
            position_size = self.calculate_position_size(symbol, current_price, stop_loss_price)

            if position_size > 0:
                quantity = position_size / current_price
                if signal['direction'] == 'buy':
                    quantity = quantity
                else:
                    quantity = -quantity

                self.open_position(symbol, quantity, current_price, stop_loss_price, take_profit_price)


# Global strategy registry
_risk_adaptive_strategies: Dict[str, Type[RiskAdaptiveStrategy]] = {
    'mean_reversion': AdaptiveMeanReversionStrategy,
    'trend_following': AdaptiveTrendFollowingStrategy
}


def create_risk_adaptive_strategy(strategy_type: str, **kwargs) -> RiskAdaptiveStrategy:
    """Create a risk-adaptive strategy instance."""
    if strategy_type not in _risk_adaptive_strategies:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

    strategy_class = _risk_adaptive_strategies[strategy_type]
    return strategy_class(**kwargs)


def get_available_strategies() -> List[str]:
    """Get list of available risk-adaptive strategies."""
    return list(_risk_adaptive_strategies.keys())


if __name__ == "__main__":
    # Example usage
    import yfinance as yf

    # Download sample data
    data = yf.download("AAPL", start="2023-01-01", end="2024-01-01")
    data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
    data.columns = ['open', 'high', 'low', 'close', 'volume']

    # Create adaptive strategy
    strategy = create_risk_adaptive_strategy('mean_reversion', initial_capital=100000)

    # Process data
    strategy.update_market_data(data)

    # Generate and execute signals
    signals = strategy.generate_signals(data)
    strategy.execute_signals(signals, data)

    # Check stop losses
    strategy.check_stop_loss_take_profit(data)

    # Get status
    status = strategy.get_portfolio_status()
    performance = strategy.get_performance_summary()

    print(f"Portfolio Status: {status}")
    print(f"Performance: {performance}")
    print(f"Current Risk Params: position_limit={strategy.current_risk_params.position_size_limit:.3f}")