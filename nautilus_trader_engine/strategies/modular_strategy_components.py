"""
Modular Strategy Components for Nautilus Trader Engine
Provides reusable building blocks for creating complex trading strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Tuple, Union, Type, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod
from datetime import datetime, time
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ComponentType(Enum):
    """Types of strategy components."""
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    FILTER = "filter"
    RISK_MANAGER = "risk_manager"
    POSITION_SIZER = "position_sizer"
    EXECUTION_HANDLER = "execution_handler"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4


@dataclass
class Signal:
    """Trading signal with metadata."""
    symbol: str
    direction: str  # 'buy', 'sell', 'hold'
    strength: SignalStrength
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    price: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyComponent:
    """Base class for strategy components."""
    name: str
    component_type: ComponentType
    enabled: bool = True
    weight: float = 1.0
    parameters: Dict[str, Any] = field(default_factory=dict)

    @abstractmethod
    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> Any:
        """Process data and return result."""
        pass

    def validate_parameters(self) -> List[str]:
        """Validate component parameters."""
        return []


class EntrySignalComponent(StrategyComponent):
    """Component for generating entry signals."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, ComponentType.ENTRY_SIGNAL, **kwargs)

    @abstractmethod
    def generate_entry_signal(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        """Generate entry signal."""
        pass

    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        return self.generate_entry_signal(data, context)


class ExitSignalComponent(StrategyComponent):
    """Component for generating exit signals."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, ComponentType.EXIT_SIGNAL, **kwargs)

    @abstractmethod
    def generate_exit_signal(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        """Generate exit signal."""
        pass

    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        return self.generate_exit_signal(data, context)


class FilterComponent(StrategyComponent):
    """Component for filtering signals."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, ComponentType.FILTER, **kwargs)

    @abstractmethod
    def should_filter(self, signal: Signal, data: pd.DataFrame, context: Dict[str, Any]) -> bool:
        """Determine if signal should be filtered."""
        pass

    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> bool:
        signal = context.get('signal')
        if signal:
            return self.should_filter(signal, data, context)
        return False


class RiskManagerComponent(StrategyComponent):
    """Component for risk management."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, ComponentType.RISK_MANAGER, **kwargs)

    @abstractmethod
    def calculate_position_size(self, signal: Signal, capital: float, context: Dict[str, Any]) -> float:
        """Calculate position size based on risk management rules."""
        pass

    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> float:
        signal = context.get('signal')
        capital = context.get('capital', 0)
        if signal and capital > 0:
            return self.calculate_position_size(signal, capital, context)
        return 0


class PositionSizerComponent(StrategyComponent):
    """Component for position sizing."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, ComponentType.POSITION_SIZER, **kwargs)

    @abstractmethod
    def size_position(self, signal: Signal, available_capital: float, context: Dict[str, Any]) -> float:
        """Determine position size."""
        pass

    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> float:
        signal = context.get('signal')
        capital = context.get('available_capital', 0)
        if signal and capital > 0:
            return self.size_position(signal, capital, context)
        return 0


class ExecutionHandlerComponent(StrategyComponent):
    """Component for order execution."""

    def __init__(self, name: str, **kwargs):
        super().__init__(name, ComponentType.EXECUTION_HANDLER, **kwargs)

    @abstractmethod
    def execute_order(self, signal: Signal, quantity: float, context: Dict[str, Any]) -> bool:
        """Execute trading order."""
        pass

    def process(self, data: pd.DataFrame, context: Dict[str, Any]) -> bool:
        signal = context.get('signal')
        quantity = context.get('quantity', 0)
        if signal and quantity > 0:
            return self.execute_order(signal, quantity, context)
        return False


# Concrete Component Implementations

class MovingAverageCrossoverEntry(EntrySignalComponent):
    """Entry signal based on moving average crossover."""

    def __init__(self, fast_period: int = 10, slow_period: int = 20, **kwargs):
        super().__init__("MA_Crossover_Entry", **kwargs)
        self.parameters.update({
            'fast_period': fast_period,
            'slow_period': slow_period
        })

    def generate_entry_signal(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        if len(data) < self.parameters['slow_period']:
            return None

        fast_ma = data['close'].rolling(self.parameters['fast_period']).mean()
        slow_ma = data['close'].rolling(self.parameters['slow_period']).mean()

        # Check for crossover
        if len(fast_ma) >= 2 and len(slow_ma) >= 2:
            prev_fast = fast_ma.iloc[-2]
            prev_slow = slow_ma.iloc[-2]
            curr_fast = fast_ma.iloc[-1]
            curr_slow = slow_ma.iloc[-1]

            # Bullish crossover
            if prev_fast <= prev_slow and curr_fast > curr_slow:
                confidence = min(1.0, (curr_fast - curr_slow) / curr_slow)
                return Signal(
                    symbol=data.index.name or "UNKNOWN",
                    direction="buy",
                    strength=SignalStrength.STRONG if confidence > 0.5 else SignalStrength.MODERATE,
                    confidence=confidence,
                    price=data['close'].iloc[-1]
                )

            # Bearish crossover
            elif prev_fast >= prev_slow and curr_fast < curr_slow:
                confidence = min(1.0, (prev_slow - prev_fast) / prev_fast)
                return Signal(
                    symbol=data.index.name or "UNKNOWN",
                    direction="sell",
                    strength=SignalStrength.STRONG if confidence > 0.5 else SignalStrength.MODERATE,
                    confidence=confidence,
                    price=data['close'].iloc[-1]
                )

        return None


class RSIEntry(EntrySignalComponent):
    """Entry signal based on RSI."""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70, **kwargs):
        super().__init__("RSI_Entry", **kwargs)
        self.parameters.update({
            'period': period,
            'oversold': oversold,
            'overbought': overbought
        })

    def generate_entry_signal(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        if len(data) < self.parameters['period']:
            return None

        # Calculate RSI
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.parameters['period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.parameters['period']).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        # Generate signals
        if current_rsi <= self.parameters['oversold']:
            confidence = (self.parameters['oversold'] - current_rsi) / self.parameters['oversold']
            return Signal(
                symbol=data.index.name or "UNKNOWN",
                direction="buy",
                strength=SignalStrength.STRONG,
                confidence=min(1.0, confidence),
                price=data['close'].iloc[-1]
            )

        elif current_rsi >= self.parameters['overbought']:
            confidence = (current_rsi - self.parameters['overbought']) / (100 - self.parameters['overbought'])
            return Signal(
                symbol=data.index.name or "UNKNOWN",
                direction="sell",
                strength=SignalStrength.STRONG,
                confidence=min(1.0, confidence),
                price=data['close'].iloc[-1]
            )

        return None


class TimeBasedExit(ExitSignalComponent):
    """Exit signal based on time duration."""

    def __init__(self, max_hold_period: int = 5, **kwargs):  # days
        super().__init__("Time_Based_Exit", **kwargs)
        self.parameters.update({'max_hold_period': max_hold_period})

    def generate_exit_signal(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        entry_time = context.get('entry_time')
        if not entry_time:
            return None

        current_time = datetime.now()
        hold_duration = (current_time - entry_time).days

        if hold_duration >= self.parameters['max_hold_period']:
            return Signal(
                symbol=context.get('symbol', 'UNKNOWN'),
                direction="sell",
                strength=SignalStrength.MODERATE,
                confidence=0.7,
                price=data['close'].iloc[-1] if not data.empty else None
            )

        return None


class StopLossExit(ExitSignalComponent):
    """Exit signal based on stop loss."""

    def __init__(self, stop_loss_pct: float = 0.05, **kwargs):
        super().__init__("Stop_Loss_Exit", **kwargs)
        self.parameters.update({'stop_loss_pct': stop_loss_pct})

    def generate_exit_signal(self, data: pd.DataFrame, context: Dict[str, Any]) -> Optional[Signal]:
        entry_price = context.get('entry_price')
        current_price = context.get('current_price') or (data['close'].iloc[-1] if not data.empty else None)

        if not entry_price or not current_price:
            return None

        loss_pct = abs(current_price - entry_price) / entry_price

        if loss_pct >= self.parameters['stop_loss_pct']:
            direction = "sell" if current_price < entry_price else "buy"  # Close position
            return Signal(
                symbol=context.get('symbol', 'UNKNOWN'),
                direction=direction,
                strength=SignalStrength.STRONG,
                confidence=0.9,
                price=current_price
            )

        return None


class VolatilityFilter(FilterComponent):
    """Filter signals based on volatility."""

    def __init__(self, max_volatility: float = 0.3, **kwargs):
        super().__init__("Volatility_Filter", **kwargs)
        self.parameters.update({'max_volatility': max_volatility})

    def should_filter(self, signal: Signal, data: pd.DataFrame, context: Dict[str, Any]) -> bool:
        if len(data) < 20:
            return False

        # Calculate volatility (standard deviation of returns)
        returns = data['close'].pct_change().dropna()
        volatility = returns.std()

        return volatility > self.parameters['max_volatility']


class KellyCriterionRiskManager(RiskManagerComponent):
    """Risk management using Kelly Criterion."""

    def __init__(self, win_rate: float = 0.55, win_loss_ratio: float = 1.5, **kwargs):
        super().__init__("Kelly_Risk_Manager", **kwargs)
        self.parameters.update({
            'win_rate': win_rate,
            'win_loss_ratio': win_loss_ratio
        })

    def calculate_position_size(self, signal: Signal, capital: float, context: Dict[str, Any]) -> float:
        win_rate = self.parameters['win_rate']
        win_loss_ratio = self.parameters['win_loss_ratio']

        # Kelly formula: f = (bp - q) / b
        # where b = odds (win_loss_ratio), p = win probability, q = loss probability
        kelly_fraction = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio

        # Conservative Kelly (half)
        position_size = capital * max(0, kelly_fraction * 0.5)

        return position_size


class FixedPercentagePositionSizer(PositionSizerComponent):
    """Position sizing based on fixed percentage of capital."""

    def __init__(self, percentage: float = 0.1, **kwargs):
        super().__init__("Fixed_Percentage_Sizer", **kwargs)
        self.parameters.update({'percentage': percentage})

    def size_position(self, signal: Signal, available_capital: float, context: Dict[str, Any]) -> float:
        return available_capital * self.parameters['percentage']


class MarketOrderExecutionHandler(ExecutionHandlerComponent):
    """Simple market order execution handler."""

    def __init__(self, **kwargs):
        super().__init__("Market_Order_Handler", **kwargs)

    def execute_order(self, signal: Signal, quantity: float, context: Dict[str, Any]) -> bool:
        # Simulate order execution
        logger.info(f"Executing {signal.direction} order for {quantity} shares of {signal.symbol} at market price")

        # In a real implementation, this would interface with a broker API
        return True


class StrategyBuilder:
    """
    Builder for creating modular trading strategies.
    """

    def __init__(self, name: str):
        self.name = name
        self.components: Dict[ComponentType, List[StrategyComponent]] = {
            component_type: [] for component_type in ComponentType
        }
        self.component_weights: Dict[str, float] = {}

    def add_component(self, component: StrategyComponent) -> 'StrategyBuilder':
        """Add a component to the strategy."""
        self.components[component.component_type].append(component)
        self.component_weights[component.name] = component.weight
        return self

    def remove_component(self, component_name: str) -> 'StrategyBuilder':
        """Remove a component from the strategy."""
        for component_list in self.components.values():
            component_list[:] = [c for c in component_list if c.name != component_name]
        self.component_weights.pop(component_name, None)
        return self

    def get_components(self, component_type: ComponentType) -> List[StrategyComponent]:
        """Get components of a specific type."""
        return self.components[component_type]

    def validate_strategy(self) -> List[str]:
        """Validate the strategy configuration."""
        errors = []

        # Check for required components
        if not self.components[ComponentType.ENTRY_SIGNAL]:
            errors.append("Strategy must have at least one entry signal component")

        # Validate individual components
        for component_list in self.components.values():
            for component in component_list:
                component_errors = component.validate_parameters()
                errors.extend([f"{component.name}: {error}" for error in component_errors])

        return errors

    def get_strategy_summary(self) -> Dict[str, Any]:
        """Get a summary of the strategy."""
        summary = {
            "name": self.name,
            "components": {},
            "total_components": sum(len(components) for components in self.components.values())
        }

        for component_type, components in self.components.items():
            summary["components"][component_type.value] = [
                {"name": c.name, "enabled": c.enabled, "weight": c.weight}
                for c in components
            ]

        return summary


class ModularStrategy:
    """
    A modular trading strategy composed of reusable components.
    """

    def __init__(self, name: str, builder: StrategyBuilder):
        self.name = name
        self.builder = builder
        self.context: Dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def process_market_data(self, data: pd.DataFrame) -> List[Signal]:
        """Process market data and generate signals."""
        signals = []

        # Update context
        self.context.update({
            'current_price': data['close'].iloc[-1] if not data.empty else None,
            'timestamp': datetime.now(),
            'data': data
        })

        # Process entry signals
        entry_signals = await self._process_components(
            self.builder.get_components(ComponentType.ENTRY_SIGNAL),
            data, self.context.copy()
        )

        # Filter signals
        filtered_signals = await self._filter_signals(entry_signals, data)

        # Apply risk management
        risk_adjusted_signals = await self._apply_risk_management(filtered_signals, data)

        # Size positions
        sized_signals = await self._size_positions(risk_adjusted_signals, data)

        # Execute orders
        await self._execute_orders(sized_signals, data)

        return sized_signals

    async def _process_components(self, components: List[StrategyComponent],
                                data: pd.DataFrame, context: Dict[str, Any]) -> List[Signal]:
        """Process a list of components."""
        signals = []

        for component in components:
            if not component.enabled:
                continue

            try:
                # Run component in thread pool to avoid blocking
                result = await asyncio.get_event_loop().run_in_executor(
                    self.executor, component.process, data, context
                )

                if isinstance(result, Signal):
                    signals.append(result)

            except Exception as e:
                logger.error(f"Error processing component {component.name}: {e}")

        return signals

    async def _filter_signals(self, signals: List[Signal], data: pd.DataFrame) -> List[Signal]:
        """Apply filters to signals."""
        if not signals:
            return signals

        filters = self.builder.get_components(ComponentType.FILTER)
        filtered_signals = []

        for signal in signals:
            should_filter = False

            for filter_component in filters:
                if not filter_component.enabled:
                    continue

                context = self.context.copy()
                context['signal'] = signal

                try:
                    result = await asyncio.get_event_loop().run_in_executor(
                        self.executor, filter_component.process, data, context
                    )

                    if result:  # Filter returns True if signal should be filtered
                        should_filter = True
                        break

                except Exception as e:
                    logger.error(f"Error in filter {filter_component.name}: {e}")

            if not should_filter:
                filtered_signals.append(signal)

        return filtered_signals

    async def _apply_risk_management(self, signals: List[Signal], data: pd.DataFrame) -> List[Signal]:
        """Apply risk management to signals."""
        risk_managers = self.builder.get_components(ComponentType.RISK_MANAGER)

        for signal in signals:
            total_position_size = 0

            for risk_manager in risk_managers:
                if not risk_manager.enabled:
                    continue

                context = self.context.copy()
                context['signal'] = signal

                try:
                    position_size = await asyncio.get_event_loop().run_in_executor(
                        self.executor, risk_manager.process, data, context
                    )
                    total_position_size += position_size * risk_manager.weight

                except Exception as e:
                    logger.error(f"Error in risk manager {risk_manager.name}: {e}")

            signal.metadata['position_size'] = total_position_size

        return signals

    async def _size_positions(self, signals: List[Signal], data: pd.DataFrame) -> List[Signal]:
        """Apply position sizing to signals."""
        position_sizers = self.builder.get_components(ComponentType.POSITION_SIZER)

        for signal in signals:
            for sizer in position_sizers:
                if not sizer.enabled:
                    continue

                context = self.context.copy()
                context['signal'] = signal
                context['available_capital'] = self.context.get('available_capital', 100000)

                try:
                    size = await asyncio.get_event_loop().run_in_executor(
                        self.executor, sizer.process, data, context
                    )
                    signal.metadata['quantity'] = size

                except Exception as e:
                    logger.error(f"Error in position sizer {sizer.name}: {e}")

        return signals

    async def _execute_orders(self, signals: List[Signal], data: pd.DataFrame) -> None:
        """Execute orders for signals."""
        execution_handlers = self.builder.get_components(ComponentType.EXECUTION_HANDLER)

        for signal in signals:
            for handler in execution_handlers:
                if not handler.enabled:
                    continue

                context = self.context.copy()
                context['signal'] = signal
                context['quantity'] = signal.metadata.get('quantity', 0)

                try:
                    success = await asyncio.get_event_loop().run_in_executor(
                        self.executor, handler.process, data, context
                    )

                    if success:
                        logger.info(f"Successfully executed order for {signal.symbol}")
                    else:
                        logger.warning(f"Failed to execute order for {signal.symbol}")

                except Exception as e:
                    logger.error(f"Error in execution handler {handler.name}: {e}")

    def update_context(self, key: str, value: Any) -> None:
        """Update strategy context."""
        self.context[key] = value

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information."""
        return {
            "name": self.name,
            "builder_summary": self.builder.get_strategy_summary(),
            "context_keys": list(self.context.keys()),
            "active_components": sum(
                len([c for c in components if c.enabled])
                for components in self.builder.components.values()
            )
        }


# Global strategy registry
_strategy_registry: Dict[str, ModularStrategy] = {}


def create_strategy(name: str) -> StrategyBuilder:
    """Create a new strategy builder."""
    return StrategyBuilder(name)


def register_strategy(strategy: ModularStrategy) -> None:
    """Register a strategy globally."""
    _strategy_registry[strategy.name] = strategy


def get_strategy(name: str) -> Optional[ModularStrategy]:
    """Get a registered strategy."""
    return _strategy_registry.get(name)


def list_strategies() -> List[str]:
    """List all registered strategies."""
    return list(_strategy_registry.keys())


if __name__ == "__main__":
    # Example usage
    async def main():
        # Create strategy builder
        builder = create_strategy("Sample_Strategy")

        # Add components
        builder.add_component(MovingAverageCrossoverEntry(fast_period=10, slow_period=20))
        builder.add_component(RSIEntry(period=14, oversold=30, overbought=70))
        builder.add_component(TimeBasedExit(max_hold_period=5))
        builder.add_component(StopLossExit(stop_loss_pct=0.05))
        builder.add_component(VolatilityFilter(max_volatility=0.3))
        builder.add_component(KellyCriterionRiskManager(win_rate=0.55, win_loss_ratio=1.5))
        builder.add_component(FixedPercentagePositionSizer(percentage=0.1))
        builder.add_component(MarketOrderExecutionHandler())

        # Validate strategy
        errors = builder.validate_strategy()
        if errors:
            print("Strategy validation errors:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("Strategy validation passed!")

        # Create modular strategy
        strategy = ModularStrategy("Sample_Strategy", builder)
        register_strategy(strategy)

        # Create sample data
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        data = pd.DataFrame({
            'open': np.random.uniform(100, 110, 100),
            'high': np.random.uniform(105, 115, 100),
            'low': np.random.uniform(95, 105, 100),
            'close': np.random.uniform(100, 110, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        }, index=dates)

        # Process market data
        signals = await strategy.process_market_data(data)

        print(f"Generated {len(signals)} signals")
        for signal in signals[:5]:  # Show first 5 signals
            print(f"  {signal.direction} {signal.symbol} with confidence {signal.confidence:.2f}")

        # Get strategy info
        info = strategy.get_strategy_info()
        print(f"Strategy info: {info}")

    # Run example
    asyncio.run(main())