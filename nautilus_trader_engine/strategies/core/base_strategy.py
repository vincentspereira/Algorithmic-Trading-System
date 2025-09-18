"""Base strategy classes and components for the trading system.

This module provides the foundational classes and components for building
trading strategies within the Nautilus Trader Engine. It includes:

- BaseStrategy: Abstract base class for all trading strategies
- StrategyConfig: Configuration dataclass for strategy parameters
- Position: Trading position representation
- Signal: Trading signal representation
- StrategyManager: Multi-strategy management

Author: AI Assistant
Date: 2024-12-15
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators



class SignalType(Enum):
    """Enumeration of trading signal types.
    
    Attributes:
        BUY: Signal to open a long position
        SELL: Signal to open a short position
        HOLD: Signal to maintain current position
        CLOSE_LONG: Signal to close a long position
        CLOSE_SHORT: Signal to close a short position
    """
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class PositionSide(Enum):
    """Enumeration of position sides.
    
    Attributes:
        LONG: Long position (buy)
        SHORT: Short position (sell)
        FLAT: No position
    """
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class OrderType(Enum):
    """Order types"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Signal:
    """Trading signal with metadata"""
    signal_type: SignalType
    timestamp: datetime
    symbol: str
    price: float
    quantity: Optional[float] = None
    confidence: float = 1.0
    strength: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    order_type: OrderType = OrderType.MARKET
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    def __post_init__(self):
        """Validate signal after initialization"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if not 0 <= self.strength <= 1:
            raise ValueError("Strength must be between 0 and 1")
        if self.price <= 0:
            raise ValueError("Price must be positive")


@dataclass
class Position:
    """Represents a trading position with P&L tracking.
    
    This class encapsulates all information about a trading position,
    including entry details, current status, and profit/loss calculations.
    
    Attributes:
        symbol: Trading symbol/instrument identifier
        side: Position side (LONG or SHORT)
        quantity: Position size (number of shares/contracts)
        entry_price: Price at which position was opened
        entry_time: Timestamp when position was opened
        current_price: Current market price (optional)
        unrealized_pnl: Unrealized profit/loss
        realized_pnl: Realized profit/loss from closed portions
        stop_loss: Stop loss price level (optional)
        take_profit: Take profit price level (optional)
        metadata: Additional position metadata
    """
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    entry_time: datetime
    current_price: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def market_value(self) -> float:
        """Calculate current market value of the position.
        
        Returns:
            Current market value based on current price or entry price
        """
        if self.current_price is None:
            return self.quantity * self.entry_price
        return self.quantity * self.current_price
    
    @property
    def pnl(self) -> float:
        """Calculate total profit and loss.
        
        Returns:
            Sum of realized and unrealized P&L
        """
        return self.realized_pnl + self.unrealized_pnl
    
    def update_price(self, new_price: float) -> None:
        """Update current price and recalculate unrealized P&L.
        
        Args:
            new_price: New market price for the instrument
            
        Raises:
            ValueError: If new_price is not positive
        """
        if new_price <= 0:
            raise ValueError("Price must be positive")
            
        self.current_price = new_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = self.quantity * (new_price - self.entry_price)
        elif self.side == PositionSide.SHORT:
            self.unrealized_pnl = self.quantity * (self.entry_price - new_price)


@dataclass
class StrategyConfig:
    """Base configuration for trading strategies.
    
    This dataclass contains all necessary configuration parameters for
    initializing and running a trading strategy.
    
    Attributes:
        name: Strategy name/identifier
        symbols: List of trading symbols/instruments
        timeframe: Data timeframe (e.g., '1D', '1H', '5m')
        lookback_period: Number of periods to look back for calculations
        max_position_size: Maximum position size as fraction of portfolio
        stop_loss_pct: Stop loss percentage (optional)
        take_profit_pct: Take profit percentage (optional)
        risk_per_trade: Risk per trade as fraction of portfolio
        max_positions: Maximum number of concurrent positions
        rebalance_frequency: How often to rebalance positions
        parameters: Strategy-specific parameters
    """
    name: str
    symbols: List[str]
    timeframe: str = "1D"
    lookback_period: int = 252
    max_position_size: float = 0.1  # As fraction of portfolio
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    risk_per_trade: float = 0.02  # 2% risk per trade
    max_positions: int = 10
    rebalance_frequency: str = "daily"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration"""
        if not 0 < self.max_position_size <= 1:
            raise ValueError("max_position_size must be between 0 and 1")
        if not 0 < self.risk_per_trade <= 1:
            raise ValueError("risk_per_trade must be between 0 and 1")
        if self.max_positions <= 0:
            raise ValueError("max_positions must be positive")


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.
    
    This class provides the foundational structure and common functionality
    for all trading strategies in the system. It implements the core strategy
    lifecycle methods and provides hooks for custom strategy logic.
    
    Attributes:
        config: Strategy configuration parameters
        positions: Dictionary of current positions by symbol
        signals: List of generated trading signals
        performance_metrics: Dictionary of performance metrics
        state: Strategy-specific state variables
        is_initialized: Whether strategy has been initialized
        indicators: Technical indicators instance
    
    Abstract Methods:
        generate_signals: Generate trading signals based on market data
        calculate_position_size: Calculate appropriate position size
    """
    
    def __init__(self, config: StrategyConfig) -> None:
        """Initialize the base strategy.
        
        Args:
            config: Strategy configuration containing parameters and settings
            
        Raises:
            ValueError: If configuration is invalid
        """
        if not isinstance(config, StrategyConfig):
            raise TypeError("config must be a StrategyConfig instance")
            
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.signals: List[Signal] = []
        self.performance_metrics: Dict[str, float] = {}
        self.state: Dict[str, Any] = {}
        self.is_initialized = False
        
        # Initialize technical indicators
        try:
            self.indicators = ConsolidatedIndicators()
        except Exception as e:
            self.indicators = None
            print(f"Warning: Could not initialize indicators: {e}")
        
    @abstractmethod
    def initialize(self, data: pd.DataFrame) -> None:
        """Initialize strategy with historical data.
        
        This method sets up the strategy's initial state using historical
        market data. Should be called before strategy execution begins.
        
        Args:
            data: Historical market data DataFrame with OHLCV columns
            
        Raises:
            ValueError: If data is invalid or insufficient
            NotImplementedError: If not implemented by subclass
        """
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals based on market data.
        
        This method analyzes market data and generates trading signals
        according to the strategy's logic. Must be implemented by subclasses.
        
        Args:
            data: Market data DataFrame with OHLCV columns
            
        Returns:
            List of Signal objects representing trading opportunities
            
        Raises:
            ValueError: If data is invalid or insufficient
            NotImplementedError: If not implemented by subclass
        """
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, portfolio_value: float) -> float:
        """Calculate appropriate position size for a trading signal.
        
        This method determines the optimal position size based on the signal
        strength, risk parameters, and current portfolio state.
        
        Args:
            signal: Trading signal containing type and strength
            portfolio_value: Total portfolio value
            
        Returns:
            Position size (number of shares/contracts)
            
        Raises:
            ValueError: If inputs are invalid
            NotImplementedError: If not implemented by subclass
        """
        pass
    
    def on_bar(self, bar_data: pd.Series) -> List[Signal]:
        """Process new bar data and generate signals"""
        # Convert series to dataframe for compatibility
        df = pd.DataFrame([bar_data])
        return self.generate_signals(df)
    
    def on_trade(self, trade_data: Dict[str, Any]) -> None:
        """Handle trade execution events"""
        symbol = trade_data.get('symbol')
        if symbol in self.positions:
            position = self.positions[symbol]
            # Update position based on trade
            if trade_data.get('side') == 'sell' and position.side == PositionSide.LONG:
                # Closing long position
                position.realized_pnl += trade_data.get('pnl', 0)
                if trade_data.get('quantity', 0) >= position.quantity:
                    del self.positions[symbol]
            elif trade_data.get('side') == 'buy' and position.side == PositionSide.SHORT:
                # Closing short position
                position.realized_pnl += trade_data.get('pnl', 0)
                if trade_data.get('quantity', 0) >= abs(position.quantity):
                    del self.positions[symbol]
    
    def update_positions(self, market_data: Dict[str, float]) -> None:
        """Update all positions with current market prices"""
        for symbol, position in self.positions.items():
            if symbol in market_data:
                position.update_price(market_data[symbol])
    
    def get_portfolio_value(self, market_data: Dict[str, float]) -> float:
        """Calculate total portfolio value"""
        total_value = 0.0
        for position in self.positions.values():
            if position.symbol in market_data:
                position.update_price(market_data[position.symbol])
                total_value += position.market_value
        return total_value
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get performance summary statistics"""
        total_pnl = sum(pos.pnl for pos in self.positions.values())
        total_positions = len(self.positions)
        
        return {
            'total_pnl': total_pnl,
            'total_positions': total_positions,
            'avg_pnl_per_position': total_pnl / max(total_positions, 1),
            **self.performance_metrics
        }
    
    def reset(self) -> None:
        """Reset strategy state"""
        self.positions.clear()
        self.signals.clear()
        self.performance_metrics.clear()
        self.state.clear()
        self.is_initialized = False


class StrategyManager:
    """Manages multiple trading strategies with portfolio allocation.
    
    This class provides functionality to manage multiple trading strategies,
    including capital allocation, performance monitoring, and coordinated
    execution across strategies.
    
    Attributes:
        strategies: Dictionary of strategy instances by name
        allocations: Dictionary of capital allocations by strategy name
        total_portfolio_value: Total value across all strategies
        performance_summary: Aggregated performance metrics
    """
    
    def __init__(self) -> None:
        """Initialize the strategy manager."""
        self.strategies: Dict[str, BaseStrategy] = {}
        self.allocations: Dict[str, float] = {}
        self.total_portfolio_value: float = 0.0
        self.performance_summary: Dict[str, float] = {}
        
    def add_strategy(self, name: str, strategy: BaseStrategy, allocation: float = 1.0) -> None:
        """Add a strategy with specified capital allocation.
        
        Args:
            name: Unique name for the strategy
            strategy: BaseStrategy instance to add
            allocation: Capital allocation as fraction (0.0 to 1.0)
            
        Raises:
            ValueError: If allocation is invalid or strategy name exists
            TypeError: If strategy is not a BaseStrategy instance
        """
        if not isinstance(strategy, BaseStrategy):
            raise TypeError("strategy must be a BaseStrategy instance")
        if not 0 < allocation <= 1:
            raise ValueError("Allocation must be between 0 and 1")
        if name in self.strategies:
            raise ValueError(f"Strategy with name '{name}' already exists")
        
        # Check total allocation doesn't exceed 1.0
        total_allocation = sum(self.allocations.values()) + allocation
        if total_allocation > 1.0:
            raise ValueError(f"Total allocation would exceed 1.0: {total_allocation}")
        
        self.strategies[name] = strategy
        self.allocations[name] = allocation
        
    def remove_strategy(self, name: str) -> Optional[BaseStrategy]:
        """Remove a strategy from management.
        
        Args:
            name: Name of strategy to remove
            
        Returns:
            Removed BaseStrategy instance, or None if not found
        """
        strategy = self.strategies.pop(name, None)
        if strategy:
            self.allocations.pop(name, None)
        return strategy
    
    def generate_all_signals(self, data: pd.DataFrame) -> Dict[str, List[Signal]]:
        """Generate signals from all strategies"""
        all_signals = {}
        for name, strategy in self.strategies.items():
            try:
                signals = strategy.generate_signals(data)
                all_signals[name] = signals
            except Exception as e:
                print(f"Error generating signals for {name}: {e}")
                all_signals[name] = []
        return all_signals
    
    def get_combined_performance(self) -> Dict[str, float]:
        """Get combined performance across all strategies.
        
        Returns:
            Dictionary containing weighted performance metrics across all strategies
        """
        if not self.strategies:
            return {'total_pnl': 0.0, 'total_positions': 0, 'avg_pnl_per_position': 0.0}
            
        combined_metrics = {}
        total_allocation = sum(self.allocations.values())
        
        if total_allocation == 0:
            return {'total_pnl': 0.0, 'total_positions': 0, 'avg_pnl_per_position': 0.0}
        
        for name, strategy in self.strategies.items():
            allocation = self.allocations[name] / total_allocation
            performance = strategy.get_performance_summary()
            
            for metric, value in performance.items():
                if metric not in combined_metrics:
                    combined_metrics[metric] = 0.0
                combined_metrics[metric] += value * allocation
                
        return combined_metrics


# Utility functions
def create_signal(signal_type: SignalType, symbol: str, price: float, 
                 timestamp: Optional[datetime] = None, **kwargs) -> Signal:
    """Convenience function to create a trading signal"""
    if timestamp is None:
        timestamp = datetime.now()
    
    return Signal(
        signal_type=signal_type,
        timestamp=timestamp,
        symbol=symbol,
        price=price,
        **kwargs
    )


def validate_ohlcv_data(data: pd.DataFrame) -> bool:
    """Validate OHLCV data format"""
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    # Check if all required columns exist
    if not all(col in data.columns for col in required_columns):
        return False
    
    # Check for valid price relationships
    if not (data['high'] >= data['low']).all():
        return False
    
    if not (data['high'] >= data['open']).all():
        return False
        
    if not (data['high'] >= data['close']).all():
        return False
        
    if not (data['low'] <= data['open']).all():
        return False
        
    if not (data['low'] <= data['close']).all():
        return False
    
    # Check for positive values
    if not (data[['open', 'high', 'low', 'close', 'volume']] > 0).all().all():
        return False
    
    return True


# Example strategy implementation
class SimpleMovingAverageStrategy(BaseStrategy):
    """Simple moving average crossover strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.short_window = config.parameters.get('short_window', 20)
        self.long_window = config.parameters.get('long_window', 50)
        
    def initialize(self, data: pd.DataFrame) -> None:
        """Initialize with historical data"""
        if len(data) < self.long_window:
            raise ValueError(f"Insufficient data: need at least {self.long_window} bars")
        
        self.is_initialized = True
        
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate signals based on moving average crossover"""
        if not self.is_initialized:
            return []
            
        signals = []
        
        for symbol in self.config.symbols:
            if symbol not in data.columns:
                continue
                
            prices = data[symbol].dropna()
            if len(prices) < self.long_window:
                continue
                
            # Calculate moving averages
            short_ma = prices.rolling(window=self.short_window).mean()
            long_ma = prices.rolling(window=self.long_window).mean()
            
            # Get latest values
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            prev_short = short_ma.iloc[-2] if len(short_ma) > 1 else current_short
            prev_long = long_ma.iloc[-2] if len(long_ma) > 1 else current_long
            
            # Generate signals on crossover
            if prev_short <= prev_long and current_short > current_long:
                # Bullish crossover
                signal = create_signal(
                    SignalType.BUY,
                    symbol,
                    prices.iloc[-1],
                    confidence=0.7,
                    metadata={'short_ma': current_short, 'long_ma': current_long}
                )
                signals.append(signal)
                
            elif prev_short >= prev_long and current_short < current_long:
                # Bearish crossover
                signal = create_signal(
                    SignalType.SELL,
                    symbol,
                    prices.iloc[-1],
                    confidence=0.7,
                    metadata={'short_ma': current_short, 'long_ma': current_long}
                )
                signals.append(signal)
        
        return signals
    
    def calculate_position_size(self, signal: Signal, portfolio_value: float) -> float:
        """Calculate position size based on risk management"""
        risk_amount = portfolio_value * self.config.risk_per_trade
        max_position_value = portfolio_value * self.config.max_position_size
        
        # Simple position sizing - can be enhanced with volatility-based sizing
        position_value = min(risk_amount * 10, max_position_value)  # 10x leverage on risk
        position_size = position_value / signal.price
        
        return position_size