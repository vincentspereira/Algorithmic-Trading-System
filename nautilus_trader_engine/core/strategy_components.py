"""
Modular Strategy Components for Institutional-Grade Trading.

This module provides a comprehensive framework for building modular trading strategies
with reusable, composable components that integrate with the 5-pillar institutional architecture:

- Entry Signal Generators: Multiple signal generation strategies
- Exit Signal Generators: Profit-taking and stop-loss mechanisms
- Position Sizing Modules: Risk-based and volatility-adjusted sizing
- Risk Management Components: Dynamic risk controls and limits
- Portfolio Allocation Strategies: Multi-asset portfolio management
- Order Execution Logic: Smart order routing and execution algorithms
- Performance Tracking: Real-time performance monitoring and attribution
- Strategy Composition Framework: Flexible strategy building and combination

The modular design enables rapid strategy development, testing, and deployment
while maintaining institutional-grade risk management and performance tracking.
"""

import asyncio
import math
import statistics
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from weakref import WeakSet

import numpy as np
from loguru import logger

from .dependency_injection import (
    DependencyInjectionContainer,
    get_container,
    injectable,
    singleton,
    ServiceLifetime
)
from .interfaces import SignalStrength, MarketRegime, RiskLevel
from .event_system import EventBus, get_event_bus, EventType, EventPriority


class ComponentType(Enum):
    """Strategy component types."""
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    POSITION_SIZING = "position_sizing"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_ALLOCATION = "portfolio_allocation"
    ORDER_EXECUTION = "order_execution"
    PERFORMANCE_TRACKING = "performance_tracking"


class SignalType(Enum):
    """Signal types for strategy components."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SCALE_IN = "scale_in"
    SCALE_OUT = "scale_out"
    CLOSE_POSITION = "close_position"


@dataclass
class StrategySignal:
    """Strategy signal with metadata."""
    signal_type: SignalType
    symbol: str
    strength: SignalStrength
    confidence: float
    quantity: Optional[float] = None
    price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    component_id: str = ""


@dataclass
class Position:
    """Position information."""
    symbol: str
    quantity: float
    average_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    timestamp: datetime
    entry_signals: List[StrategySignal] = field(default_factory=list)


@dataclass
class PortfolioState:
    """Portfolio state information."""
    total_value: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    risk_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class Order:
    """Order information."""
    order_id: str
    symbol: str
    side: str  # buy, sell
    quantity: float
    order_type: str  # market, limit, stop, etc.
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, filled, cancelled, rejected


class StrategyComponent(ABC):
    """Abstract base class for strategy components."""

    @abstractmethod
    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Process market data and generate signals."""
        pass

    @property
    @abstractmethod
    def component_type(self) -> ComponentType:
        """Get component type."""
        pass

    @property
    @abstractmethod
    def component_id(self) -> str:
        """Get unique component identifier."""
        pass

    def get_parameters(self) -> Dict[str, Any]:
        """Get component parameters."""
        return {}

    def set_parameters(self, parameters: Dict[str, Any]):
        """Set component parameters."""
        pass


@injectable
@singleton
class EntrySignalGenerator(StrategyComponent):
    """Entry signal generation component."""

    def __init__(self):
        self._indicators = {}
        self._signal_thresholds = {
            'momentum_threshold': 0.7,
            'volume_threshold': 0.6,
            'volatility_threshold': 0.5
        }

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.ENTRY_SIGNAL

    @property
    def component_id(self) -> str:
        return "entry_signal_generator"

    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Generate entry signals based on market conditions."""
        signals = []

        for symbol, data in market_data.items():
            # Skip if already have position
            if symbol in portfolio.positions:
                continue

            # Generate momentum-based signals
            momentum_signal = await self._generate_momentum_signal(symbol, data, context)
            if momentum_signal:
                signals.append(momentum_signal)

            # Generate mean-reversion signals
            mean_reversion_signal = await self._generate_mean_reversion_signal(symbol, data, context)
            if mean_reversion_signal:
                signals.append(mean_reversion_signal)

            # Generate breakout signals
            breakout_signal = await self._generate_breakout_signal(symbol, data, context)
            if breakout_signal:
                signals.append(breakout_signal)

        return signals

    async def _generate_momentum_signal(self, symbol: str, data: Dict[str, Any],
                                       context: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate momentum-based entry signals."""
        # Extract momentum indicators
        rsi = data.get('rsi', 50)
        macd = data.get('macd', 0)
        volume_ratio = data.get('volume_ratio', 1.0)

        # Momentum entry conditions
        if (rsi < 30 and macd < -0.5 and volume_ratio > self._signal_thresholds['volume_threshold']):
            return StrategySignal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                strength=SignalStrength.STRONG,
                confidence=min(0.9, (30 - rsi) / 30 + abs(macd) / 2),
                metadata={
                    'signal_source': 'momentum',
                    'rsi': rsi,
                    'macd': macd,
                    'volume_ratio': volume_ratio
                },
                component_id=self.component_id
            )

        return None

    async def _generate_mean_reversion_signal(self, symbol: str, data: Dict[str, Any],
                                             context: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate mean-reversion entry signals."""
        # Extract mean-reversion indicators
        bollinger_position = data.get('bollinger_position', 0.5)  # Position within Bollinger Bands
        rsi = data.get('rsi', 50)

        # Mean-reversion entry conditions
        if (bollinger_position < 0.1 and rsi < 25):  # Near lower Bollinger Band and oversold
            return StrategySignal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                strength=SignalStrength.MODERATE,
                confidence=min(0.8, (0.1 - bollinger_position) / 0.1 + (25 - rsi) / 25),
                metadata={
                    'signal_source': 'mean_reversion',
                    'bollinger_position': bollinger_position,
                    'rsi': rsi
                },
                component_id=self.component_id
            )

        return None

    async def _generate_breakout_signal(self, symbol: str, data: Dict[str, Any],
                                       context: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate breakout entry signals."""
        # Extract breakout indicators
        price = data.get('close', 0)
        resistance_level = data.get('resistance', price * 1.05)
        volume_sma = data.get('volume_sma', 1.0)
        current_volume = data.get('volume', 1.0)

        # Breakout entry conditions
        if (price > resistance_level * 0.995 and current_volume > volume_sma * 1.5):
            return StrategySignal(
                signal_type=SignalType.BUY,
                symbol=symbol,
                strength=SignalStrength.VERY_STRONG,
                confidence=min(0.95, (price - resistance_level) / resistance_level + current_volume / volume_sma - 1),
                metadata={
                    'signal_source': 'breakout',
                    'price': price,
                    'resistance': resistance_level,
                    'volume_ratio': current_volume / volume_sma
                },
                component_id=self.component_id
            )

        return None


@injectable
@singleton
class ExitSignalGenerator(StrategyComponent):
    """Exit signal generation component."""

    def __init__(self):
        self._profit_targets = {
            'conservative': 0.05,    # 5%
            'moderate': 0.10,        # 10%
            'aggressive': 0.20       # 20%
        }
        self._stop_losses = {
            'tight': 0.02,          # 2%
            'normal': 0.05,         # 5%
            'wide': 0.10            # 10%
        }

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.EXIT_SIGNAL

    @property
    def component_id(self) -> str:
        return "exit_signal_generator"

    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Generate exit signals for existing positions."""
        signals = []

        for symbol, position in portfolio.positions.items():
            data = market_data.get(symbol, {})

            # Generate profit-taking signals
            profit_signal = await self._generate_profit_taking_signal(symbol, position, data, context)
            if profit_signal:
                signals.append(profit_signal)

            # Generate stop-loss signals
            stop_signal = await self._generate_stop_loss_signal(symbol, position, data, context)
            if stop_signal:
                signals.append(stop_signal)

            # Generate trailing stop signals
            trailing_signal = await self._generate_trailing_stop_signal(symbol, position, data, context)
            if trailing_signal:
                signals.append(trailing_signal)

        return signals

    async def _generate_profit_taking_signal(self, symbol: str, position: Position,
                                           data: Dict[str, Any], context: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate profit-taking signals."""
        current_price = data.get('close', position.current_price)
        entry_price = position.average_price

        # Calculate profit percentage
        profit_pct = (current_price - entry_price) / entry_price

        # Profit-taking thresholds based on risk level
        risk_level = context.get('risk_level', 'moderate')
        profit_target = self._profit_targets.get(risk_level, self._profit_targets['moderate'])

        if profit_pct >= profit_target:
            return StrategySignal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=SignalStrength.STRONG,
                confidence=min(0.9, profit_pct / profit_target),
                quantity=position.quantity,  # Close entire position
                metadata={
                    'signal_source': 'profit_taking',
                    'profit_pct': profit_pct,
                    'target': profit_target,
                    'entry_price': entry_price,
                    'exit_price': current_price
                },
                component_id=self.component_id
            )

        return None

    async def _generate_stop_loss_signal(self, symbol: str, position: Position,
                                       data: Dict[str, Any], context: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate stop-loss signals."""
        current_price = data.get('close', position.current_price)
        entry_price = position.average_price

        # Calculate loss percentage
        loss_pct = (entry_price - current_price) / entry_price

        # Stop-loss thresholds based on risk level
        risk_level = context.get('risk_level', 'moderate')
        stop_loss = self._stop_losses.get(risk_level, self._stop_losses['normal'])

        if loss_pct >= stop_loss:
            return StrategySignal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=SignalStrength.VERY_STRONG,
                confidence=min(0.95, loss_pct / stop_loss),
                quantity=position.quantity,  # Close entire position
                metadata={
                    'signal_source': 'stop_loss',
                    'loss_pct': loss_pct,
                    'stop_level': stop_loss,
                    'entry_price': entry_price,
                    'exit_price': current_price
                },
                component_id=self.component_id
            )

        return None

    async def _generate_trailing_stop_signal(self, symbol: str, position: Position,
                                           data: Dict[str, Any], context: Dict[str, Any]) -> Optional[StrategySignal]:
        """Generate trailing stop signals."""
        current_price = data.get('close', position.current_price)
        entry_price = position.average_price

        # Calculate current profit
        profit_pct = (current_price - entry_price) / entry_price

        # Only apply trailing stop if profitable
        if profit_pct <= 0.02:  # Minimum 2% profit before trailing
            return None

        # Calculate trailing stop level (e.g., 5% below current high)
        # This is a simplified implementation
        trailing_pct = 0.05  # 5% trailing stop
        stop_price = current_price * (1 - trailing_pct)

        # Check if current price has dropped below trailing stop
        if current_price <= stop_price:
            return StrategySignal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=SignalStrength.STRONG,
                confidence=0.85,
                quantity=position.quantity,
                metadata={
                    'signal_source': 'trailing_stop',
                    'profit_pct': profit_pct,
                    'trailing_pct': trailing_pct,
                    'stop_price': stop_price,
                    'entry_price': entry_price,
                    'exit_price': current_price
                },
                component_id=self.component_id
            )

        return None


@injectable
@singleton
class PositionSizer(StrategyComponent):
    """Position sizing component."""

    def __init__(self):
        self._base_position_size = 0.02  # 2% of portfolio
        self._max_position_size = 0.10   # 10% of portfolio
        self._volatility_adjustment = True
        self._correlation_adjustment = True

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.POSITION_SIZING

    @property
    def component_id(self) -> str:
        return "position_sizer"

    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Calculate position sizes for signals."""
        signals = context.get('entry_signals', [])
        sized_signals = []

        for signal in signals:
            if signal.signal_type not in [SignalType.BUY, SignalType.SELL]:
                continue

            # Calculate base position size
            position_size = await self._calculate_position_size(signal, portfolio, market_data, context)

            # Apply risk adjustments
            if self._volatility_adjustment:
                position_size = await self._adjust_for_volatility(position_size, signal.symbol, market_data)

            if self._correlation_adjustment:
                position_size = await self._adjust_for_correlation(position_size, signal.symbol, portfolio)

            # Apply position limits
            position_size = min(position_size, self._max_position_size)

            # Create sized signal
            sized_signal = StrategySignal(
                signal_type=signal.signal_type,
                symbol=signal.symbol,
                strength=signal.strength,
                confidence=signal.confidence,
                quantity=position_size * portfolio.total_value,  # Convert to dollar amount
                price=market_data.get(signal.symbol, {}).get('close'),
                timestamp=signal.timestamp,
                metadata={
                    **signal.metadata,
                    'position_size_pct': position_size,
                    'portfolio_value': portfolio.total_value
                },
                component_id=self.component_id
            )

            sized_signals.append(sized_signal)

        return sized_signals

    async def _calculate_position_size(self, signal: StrategySignal, portfolio: PortfolioState,
                                     market_data: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate base position size."""
        # Kelly Criterion inspired sizing
        win_rate = context.get('win_rate', 0.55)
        avg_win = context.get('avg_win', 0.08)
        avg_loss = context.get('avg_loss', 0.04)

        if avg_loss == 0:
            return self._base_position_size

        # Kelly formula: (bp - q) / b
        # where b = odds (avg_win/avg_loss), p = win_rate, q = loss_rate
        b = avg_win / avg_loss
        kelly_fraction = (b * win_rate - (1 - win_rate)) / b

        # Use half-Kelly for safety
        position_size = max(0.005, min(kelly_fraction * 0.5, self._max_position_size))

        return position_size

    async def _adjust_for_volatility(self, position_size: float, symbol: str,
                                   market_data: Dict[str, Any]) -> float:
        """Adjust position size based on volatility."""
        data = market_data.get(symbol, {})
        volatility = data.get('volatility', 0.2)  # 20% default

        # Reduce position size for high volatility
        if volatility > 0.3:  # High volatility
            adjustment = 0.3 / volatility
            position_size *= adjustment

        return position_size

    async def _adjust_for_correlation(self, position_size: float, symbol: str,
                                    portfolio: PortfolioState) -> float:
        """Adjust position size based on portfolio correlation."""
        # Simplified correlation adjustment
        # In practice, this would calculate correlation with existing positions
        existing_symbols = list(portfolio.positions.keys())

        if not existing_symbols:
            return position_size

        # Assume some correlation - reduce size if adding to concentrated portfolio
        concentration_factor = len(existing_symbols) / 10.0  # Max 10 positions
        correlation_adjustment = max(0.5, 1.0 - concentration_factor)

        return position_size * correlation_adjustment


@injectable
@singleton
class RiskManager(StrategyComponent):
    """Risk management component."""

    def __init__(self):
        self._max_portfolio_risk = 0.02  # 2% max daily loss
        self._max_position_risk = 0.01   # 1% max position loss
        self._max_correlation = 0.7      # Max correlation between positions
        self._var_limit = 0.05          # 5% VaR limit

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.RISK_MANAGEMENT

    @property
    def component_id(self) -> str:
        return "risk_manager"

    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Apply risk management rules."""
        signals = []

        # Check portfolio-level risk
        portfolio_signals = await self._check_portfolio_risk(portfolio, context)
        signals.extend(portfolio_signals)

        # Check position-level risk
        for symbol, position in portfolio.positions.items():
            position_signals = await self._check_position_risk(symbol, position, market_data, context)
            signals.extend(position_signals)

        # Check correlation risk
        correlation_signals = await self._check_correlation_risk(portfolio, market_data, context)
        signals.extend(correlation_signals)

        return signals

    async def _check_portfolio_risk(self, portfolio: PortfolioState,
                                   context: Dict[str, Any]) -> List[StrategySignal]:
        """Check portfolio-level risk limits."""
        signals = []

        # Calculate portfolio VaR
        portfolio_var = portfolio.risk_metrics.get('var_95', 0.02)

        if portfolio_var > self._var_limit:
            # Generate risk reduction signals
            risk_reduction_pct = min(0.5, (portfolio_var - self._var_limit) / self._var_limit)

            for symbol, position in portfolio.positions.items():
                signals.append(StrategySignal(
                    signal_type=SignalType.SELL,
                    symbol=symbol,
                    strength=SignalStrength.STRONG,
                    confidence=0.9,
                    quantity=position.quantity * risk_reduction_pct,
                    metadata={
                        'signal_source': 'portfolio_risk_management',
                        'portfolio_var': portfolio_var,
                        'var_limit': self._var_limit,
                        'risk_reduction_pct': risk_reduction_pct
                    },
                    component_id=self.component_id
                ))

        return signals

    async def _check_position_risk(self, symbol: str, position: Position,
                                  market_data: Dict[str, Any], context: Dict[str, Any]) -> List[StrategySignal]:
        """Check position-level risk."""
        signals = []

        data = market_data.get(symbol, {})
        current_price = data.get('close', position.current_price)

        # Calculate position P&L
        pnl_pct = (current_price - position.average_price) / position.average_price

        if pnl_pct <= -self._max_position_risk:
            # Stop loss triggered
            signals.append(StrategySignal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=SignalStrength.VERY_STRONG,
                confidence=0.95,
                quantity=position.quantity,
                metadata={
                    'signal_source': 'position_risk_management',
                    'pnl_pct': pnl_pct,
                    'max_risk': self._max_position_risk,
                    'entry_price': position.average_price,
                    'current_price': current_price
                },
                component_id=self.component_id
            ))

        return signals

    async def _check_correlation_risk(self, portfolio: PortfolioState,
                                     market_data: Dict[str, Any], context: Dict[str, Any]) -> List[StrategySignal]:
        """Check correlation risk between positions."""
        signals = []

        # Simplified correlation check
        # In practice, this would calculate actual correlations
        symbols = list(portfolio.positions.keys())

        if len(symbols) < 2:
            return signals

        # Assume high correlation if too many positions in same sector
        # This is a placeholder for actual correlation analysis
        if len(symbols) > 5:
            # Reduce position sizes for over-concentration
            reduction_signals = await self._generate_concentration_signals(portfolio)
            signals.extend(reduction_signals)

        return signals

    async def _generate_concentration_signals(self, portfolio: PortfolioState) -> List[StrategySignal]:
        """Generate signals to reduce portfolio concentration."""
        signals = []

        # Reduce 20% of each position to decrease concentration
        reduction_pct = 0.2

        for symbol, position in portfolio.positions.items():
            signals.append(StrategySignal(
                signal_type=SignalType.SELL,
                symbol=symbol,
                strength=SignalStrength.MODERATE,
                confidence=0.7,
                quantity=position.quantity * reduction_pct,
                metadata={
                    'signal_source': 'concentration_risk_management',
                    'reduction_pct': reduction_pct,
                    'total_positions': len(portfolio.positions)
                },
                component_id=self.component_id
            ))

        return signals


@injectable
@singleton
class OrderExecutor(StrategyComponent):
    """Order execution component."""

    def __init__(self):
        self._execution_algorithms = {
            'market': self._execute_market_order,
            'limit': self._execute_limit_order,
            'twap': self._execute_twap_order,
            'vwap': self._execute_vwap_order
        }

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.ORDER_EXECUTION

    @property
    def component_id(self) -> str:
        return "order_executor"

    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Execute orders based on signals."""
        signals = context.get('execution_signals', [])
        executed_orders = []

        for signal in signals:
            if signal.quantity is None or signal.quantity <= 0:
                continue

            # Determine order type based on signal strength and market conditions
            order_type = await self._determine_order_type(signal, market_data, context)

            # Execute order
            order = await self._execute_order(signal, order_type, market_data, context)
            if order:
                executed_orders.append(order)

        return executed_orders

    async def _determine_order_type(self, signal: StrategySignal, market_data: Dict[str, Any],
                                   context: Dict[str, Any]) -> str:
        """Determine optimal order type."""
        volatility = context.get('volatility', 0.2)
        liquidity = context.get('liquidity', 0.5)

        # Use limit orders in low volatility, high liquidity conditions
        if volatility < 0.15 and liquidity > 0.7 and signal.strength in [SignalStrength.WEAK, SignalStrength.MODERATE]:
            return 'limit'

        # Use TWAP/VWAP for large orders
        if signal.quantity and signal.quantity > 10000:  # Large order threshold
            return 'vwap' if liquidity > 0.5 else 'twap'

        # Default to market orders
        return 'market'

    async def _execute_order(self, signal: StrategySignal, order_type: str,
                           market_data: Dict[str, Any], context: Dict[str, Any]) -> Optional[Order]:
        """Execute a trading order."""
        execution_func = self._execution_algorithms.get(order_type, self._execute_market_order)

        try:
            order = await execution_func(signal, market_data, context)
            logger.info(f"Executed {order_type} order for {signal.symbol}: {order.quantity} @ {order.price}")
            return order
        except Exception as e:
            logger.error(f"Failed to execute {order_type} order for {signal.symbol}: {e}")
            return None

    async def _execute_market_order(self, signal: StrategySignal, market_data: Dict[str, Any],
                                   context: Dict[str, Any]) -> Order:
        """Execute market order."""
        data = market_data.get(signal.symbol, {})
        price = data.get('close', signal.price or 100.0)

        # Add slippage for market orders
        slippage = price * 0.0005  # 0.05% slippage
        if signal.signal_type == SignalType.SELL:
            execution_price = price - slippage
        else:
            execution_price = price + slippage

        return Order(
            order_id=f"order_{int(time.time())}_{signal.symbol}",
            symbol=signal.symbol,
            side=signal.signal_type.value,
            quantity=signal.quantity,
            order_type='market',
            price=execution_price,
            status='filled'
        )

    async def _execute_limit_order(self, signal: StrategySignal, market_data: Dict[str, Any],
                                  context: Dict[str, Any]) -> Order:
        """Execute limit order."""
        data = market_data.get(signal.symbol, {})
        base_price = data.get('close', signal.price or 100.0)

        # Set limit price slightly better than market
        if signal.signal_type == SignalType.SELL:
            limit_price = base_price * 1.001  # 0.1% better
        else:
            limit_price = base_price * 0.999  # 0.1% better

        return Order(
            order_id=f"order_{int(time.time())}_{signal.symbol}",
            symbol=signal.symbol,
            side=signal.signal_type.value,
            quantity=signal.quantity,
            order_type='limit',
            price=limit_price,
            status='pending'  # Limit orders may not fill immediately
        )

    async def _execute_twap_order(self, signal: StrategySignal, market_data: Dict[str, Any],
                                 context: Dict[str, Any]) -> Order:
        """Execute Time-Weighted Average Price (TWAP) order."""
        # Simplified TWAP implementation
        data = market_data.get(signal.symbol, {})
        price = data.get('close', signal.price or 100.0)

        return Order(
            order_id=f"twap_{int(time.time())}_{signal.symbol}",
            symbol=signal.symbol,
            side=signal.signal_type.value,
            quantity=signal.quantity,
            order_type='twap',
            price=price,
            metadata={'execution_algorithm': 'twap'},
            status='filled'
        )

    async def _execute_vwap_order(self, signal: StrategySignal, market_data: Dict[str, Any],
                                 context: Dict[str, Any]) -> Order:
        """Execute Volume-Weighted Average Price (VWAP) order."""
        # Simplified VWAP implementation
        data = market_data.get(signal.symbol, {})
        price = data.get('close', signal.price or 100.0)

        return Order(
            order_id=f"vwap_{int(time.time())}_{signal.symbol}",
            symbol=signal.symbol,
            side=signal.signal_type.value,
            quantity=signal.quantity,
            order_type='vwap',
            price=price,
            metadata={'execution_algorithm': 'vwap'},
            status='filled'
        )


@injectable
@singleton
class PerformanceTracker(StrategyComponent):
    """Performance tracking component."""

    def __init__(self):
        self._performance_history: Dict[str, List[Dict[str, Any]]] = {}
        self._benchmark_returns: List[Tuple[datetime, float]] = []

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.PERFORMANCE_TRACKING

    @property
    def component_id(self) -> str:
        return "performance_tracker"

    async def process(self, market_data: Dict[str, Any], portfolio: PortfolioState,
                     context: Dict[str, Any]) -> List[StrategySignal]:
        """Track and analyze performance."""
        # Update performance metrics
        await self._update_performance_metrics(portfolio, context)

        # Generate performance-based signals
        signals = await self._generate_performance_signals(portfolio, context)

        return signals

    async def _update_performance_metrics(self, portfolio: PortfolioState, context: Dict[str, Any]):
        """Update performance metrics."""
        timestamp = portfolio.timestamp

        # Calculate portfolio return
        total_value = portfolio.total_value
        positions_value = sum(pos.market_value for pos in portfolio.positions.values())
        cash = portfolio.cash

        # Store performance data
        performance_data = {
            'timestamp': timestamp,
            'total_value': total_value,
            'positions_value': positions_value,
            'cash': cash,
            'num_positions': len(portfolio.positions),
            'risk_metrics': portfolio.risk_metrics.copy()
        }

        # Store by strategy/component
        strategy_id = context.get('strategy_id', 'default')
        if strategy_id not in self._performance_history:
            self._performance_history[strategy_id] = []

        self._performance_history[strategy_id].append(performance_data)

        # Maintain history size
        if len(self._performance_history[strategy_id]) > 10000:
            self._performance_history[strategy_id].pop(0)

    async def _generate_performance_signals(self, portfolio: PortfolioState,
                                          context: Dict[str, Any]) -> List[StrategySignal]:
        """Generate signals based on performance analysis."""
        signals = []

        strategy_id = context.get('strategy_id', 'default')
        history = self._performance_history.get(strategy_id, [])

        if len(history) < 20:  # Need minimum history
            return signals

        # Analyze recent performance
        recent_performance = history[-20:]
        returns = []

        prev_value = recent_performance[0]['total_value']
        for record in recent_performance[1:]:
            current_value = record['total_value']
            daily_return = (current_value - prev_value) / prev_value
            returns.append(daily_return)
            prev_value = current_value

        if returns:
            # Calculate performance metrics
            avg_return = statistics.mean(returns)
            volatility = statistics.stdev(returns) if len(returns) > 1 else 0
            sharpe_ratio = avg_return / volatility if volatility > 0 else 0

            # Generate signals based on performance
            if sharpe_ratio < 0.5:  # Poor risk-adjusted performance
                signals.append(StrategySignal(
                    signal_type=SignalType.HOLD,
                    symbol='PORTFOLIO',  # Portfolio-level signal
                    strength=SignalStrength.MODERATE,
                    confidence=0.7,
                    metadata={
                        'signal_source': 'performance_based',
                        'sharpe_ratio': sharpe_ratio,
                        'avg_return': avg_return,
                        'volatility': volatility,
                        'reason': 'poor_risk_adjusted_performance'
                    },
                    component_id=self.component_id
                ))

        return signals

    def get_performance_metrics(self, strategy_id: str = 'default',
                               days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for a strategy."""
        history = self._performance_history.get(strategy_id, [])

        if not history:
            return {}

        # Filter by time period
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_history = [h for h in history if h['timestamp'] >= cutoff_date]

        if not recent_history:
            return {}

        # Calculate metrics
        values = [h['total_value'] for h in recent_history]
        initial_value = values[0]
        final_value = values[-1]

        total_return = (final_value - initial_value) / initial_value

        # Calculate daily returns
        daily_returns = []
        prev_value = initial_value
        for value in values[1:]:
            daily_return = (value - prev_value) / prev_value
            daily_returns.append(daily_return)
            prev_value = value

        if daily_returns:
            avg_daily_return = statistics.mean(daily_returns)
            volatility = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
            sharpe_ratio = avg_daily_return / volatility * math.sqrt(252) if volatility > 0 else 0

            # Calculate drawdown
            peak = initial_value
            max_drawdown = 0
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)

            return {
                'total_return': total_return,
                'annualized_return': (1 + total_return) ** (365 / days) - 1,
                'volatility': volatility * math.sqrt(252),  # Annualized
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'calmar_ratio': (total_return / days * 365) / max_drawdown if max_drawdown > 0 else 0,
                'num_days': len(recent_history),
                'final_value': final_value,
                'initial_value': initial_value
            }

        return {}


@injectable
@singleton
class StrategyComposer:
    """
    Strategy Composition Framework for Institutional-Grade Trading.

    Features:
    - Modular strategy building with reusable components
    - Component orchestration and signal flow management
    - Dynamic strategy adaptation based on market conditions
    - Performance-based component weighting
    - Risk-aware signal filtering and prioritization
    - Real-time strategy optimization and parameter tuning
    """

    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
        self._event_bus = get_event_bus()
        self._components: Dict[str, StrategyComponent] = {}
        self._strategy_definitions: Dict[str, Dict[str, Any]] = {}
        self._active_strategies: Dict[str, List[StrategyComponent]] = {}
        self._lock = asyncio.Lock()

        # Initialize default components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize strategy components."""
        try:
            self._components = {
                'entry_signal': self._container.get_service(EntrySignalGenerator),
                'exit_signal': self._container.get_service(ExitSignalGenerator),
                'position_sizing': self._container.get_service(PositionSizer),
                'risk_management': self._container.get_service(RiskManager),
                'order_execution': self._container.get_service(OrderExecutor),
                'performance_tracking': self._container.get_service(PerformanceTracker)
            }
        except Exception as e:
            logger.warning(f"Failed to initialize some components: {e}")

    def define_strategy(self, strategy_id: str, component_config: Dict[str, Any]):
        """Define a strategy with component configuration."""
        self._strategy_definitions[strategy_id] = component_config
        logger.info(f"Defined strategy: {strategy_id}")

    def activate_strategy(self, strategy_id: str):
        """Activate a strategy with its components."""
        if strategy_id not in self._strategy_definitions:
            raise ValueError(f"Strategy {strategy_id} not defined")

        config = self._strategy_definitions[strategy_id]
        components = []

        # Build component list based on configuration
        for component_type, component_config in config.items():
            if component_type in self._components:
                component = self._components[component_type]

                # Apply component configuration
                if hasattr(component, 'set_parameters') and component_config:
                    component.set_parameters(component_config)

                components.append(component)

        self._active_strategies[strategy_id] = components
        logger.info(f"Activated strategy: {strategy_id} with {len(components)} components")

    async def execute_strategy(self, strategy_id: str, market_data: Dict[str, Any],
                              portfolio: PortfolioState, context: Dict[str, Any]) -> List[StrategySignal]:
        """
        Execute a strategy with all its components.

        Args:
            strategy_id: Strategy identifier
            market_data: Current market data
            portfolio: Current portfolio state
            context: Execution context

        Returns:
            List of strategy signals
        """
        if strategy_id not in self._active_strategies:
            raise ValueError(f"Strategy {strategy_id} not activated")

        components = self._active_strategies[strategy_id]
        all_signals = []

        # Execute components in order
        component_order = [
            ComponentType.ENTRY_SIGNAL,
            ComponentType.EXIT_SIGNAL,
            ComponentType.POSITION_SIZING,
            ComponentType.RISK_MANAGEMENT,
            ComponentType.ORDER_EXECUTION,
            ComponentType.PERFORMANCE_TRACKING
        ]

        current_context = context.copy()

        for component_type in component_order:
            # Find components of this type
            type_components = [c for c in components if c.component_type == component_type]

            for component in type_components:
                try:
                    # Add previous signals to context
                    current_context['previous_signals'] = all_signals.copy()

                    # Execute component
                    signals = await component.process(market_data, portfolio, current_context)

                    # Add component ID to signals
                    for signal in signals:
                        signal.component_id = component.component_id

                    all_signals.extend(signals)

                    # Update context with new signals
                    current_context[f'{component.component_type.value}_signals'] = signals

                except Exception as e:
                    logger.error(f"Error in component {component.component_id}: {e}")

                    # Publish error event
                    await self._event_bus.publish_event(
                        self._event_bus.create_event(
                            EventType.ERROR_OCCURRED,
                            "strategy_composer",
                            {
                                "strategy_id": strategy_id,
                                "component_id": component.component_id,
                                "error": str(e)
                            },
                            EventPriority.HIGH
                        )
                    )

        # Filter and prioritize signals
        final_signals = await self._filter_and_prioritize_signals(all_signals, context)

        # Publish strategy execution event
        await self._publish_strategy_event(strategy_id, len(final_signals), context)

        return final_signals

    async def _filter_and_prioritize_signals(self, signals: List[StrategySignal],
                                           context: Dict[str, Any]) -> List[StrategySignal]:
        """Filter and prioritize signals based on various criteria."""
        if not signals:
            return []

        # Remove conflicting signals
        filtered_signals = await self._remove_conflicting_signals(signals)

        # Prioritize signals by strength and confidence
        prioritized_signals = sorted(
            filtered_signals,
            key=lambda s: (s.strength.value, s.confidence),
            reverse=True
        )

        # Apply risk limits
        risk_filtered_signals = await self._apply_risk_limits(prioritized_signals, context)

        return risk_filtered_signals

    async def _remove_conflicting_signals(self, signals: List[StrategySignal]) -> List[StrategySignal]:
        """Remove conflicting signals for the same symbol."""
        symbol_signals: Dict[str, List[StrategySignal]] = {}

        # Group signals by symbol
        for signal in signals:
            if signal.symbol not in symbol_signals:
                symbol_signals[signal.symbol] = []
            symbol_signals[signal.symbol].append(signal)

        filtered_signals = []

        for symbol, symbol_signal_list in symbol_signals.items():
            if len(symbol_signal_list) == 1:
                filtered_signals.extend(symbol_signal_list)
                continue

            # Resolve conflicts based on priority
            # BUY/SELL conflicts: Choose higher confidence
            buy_signals = [s for s in symbol_signal_list if s.signal_type == SignalType.BUY]
            sell_signals = [s for s in symbol_signal_list if s.signal_type == SignalType.SELL]

            if buy_signals and sell_signals:
                # Choose the signal with higher combined score
                buy_score = max((s.confidence * s.strength.value) for s in buy_signals)
                sell_score = max((s.confidence * s.strength.value) for s in sell_signals)

                if buy_score >= sell_score:
                    filtered_signals.extend(buy_signals)
                else:
                    filtered_signals.extend(sell_signals)
            else:
                # No conflicts, keep all
                filtered_signals.extend(symbol_signal_list)

        return filtered_signals

    async def _apply_risk_limits(self, signals: List[StrategySignal],
                               context: Dict[str, Any]) -> List[StrategySignal]:
        """Apply risk limits to signals."""
        max_signals = context.get('max_signals_per_execution', 5)
        min_confidence = context.get('min_signal_confidence', 0.6)

        # Filter by confidence
        confident_signals = [s for s in signals if s.confidence >= min_confidence]

        # Limit number of signals
        return confident_signals[:max_signals]

    async def _publish_strategy_event(self, strategy_id: str, signal_count: int,
                                    context: Dict[str, Any]):
        """Publish strategy execution event."""
        event_data = {
            "strategy_id": strategy_id,
            "signal_count": signal_count,
            "execution_time": time.time(),
            "context": context
        }

        await self._event_bus.publish_event(
            self._event_bus.create_event(
                EventType.SYSTEM_HEALTH_CHANGED,
                "strategy_composer",
                event_data,
                EventPriority.NORMAL
            )
        )

    def get_strategy_performance(self, strategy_id: str) -> Dict[str, Any]:
        """Get performance metrics for a strategy."""
        if 'performance_tracking' in self._components:
            tracker = self._components['performance_tracking']
            if hasattr(tracker, 'get_performance_metrics'):
                return tracker.get_performance_metrics(strategy_id)

        return {}

    def get_active_strategies(self) -> Dict[str, List[str]]:
        """Get information about active strategies."""
        return {
            strategy_id: [c.component_id for c in components]
            for strategy_id, components in self._active_strategies.items()
        }

    def deactivate_strategy(self, strategy_id: str) -> bool:
        """Deactivate a strategy."""
        if strategy_id in self._active_strategies:
            del self._active_strategies[strategy_id]
            logger.info(f"Deactivated strategy: {strategy_id}")
            return True
        return False


# Global strategy composer instance
_strategy_composer = StrategyComposer()


def get_strategy_composer() -> StrategyComposer:
    """Get the global strategy composer."""
    return _strategy_composer


# Convenience functions
def define_strategy(strategy_id: str, component_config: Dict[str, Any]):
    """Define a strategy configuration."""
    _strategy_composer.define_strategy(strategy_id, component_config)


def activate_strategy(strategy_id: str):
    """Activate a strategy."""
    _strategy_composer.activate_strategy(strategy_id)


async def execute_strategy(strategy_id: str, market_data: Dict[str, Any],
                          portfolio: PortfolioState, context: Dict[str, Any]) -> List[StrategySignal]:
    """Execute a strategy."""
    return await _strategy_composer.execute_strategy(strategy_id, market_data, portfolio, context)