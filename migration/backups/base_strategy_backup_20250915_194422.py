"""Base strategy classes and components for the trading system"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal


class SignalType(Enum):
    """Types of trading signals"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"


class PositionSide(Enum):
    """Position sides"""
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
    """Trading position"""
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
        """Current market value of position"""
        if self.current_price is None:
            return self.quantity * self.entry_price
        return self.quantity * self.current_price
    
    @property
    def pnl(self) -> float:
        """Total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl
    
    def update_price(self, new_price: float) -> None:
        """Update current price and unrealized P&L"""
        self.current_price = new_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = self.quantity * (new_price - self.entry_price)
        elif self.side == PositionSide.SHORT:
            self.unrealized_pnl = self.quantity * (self.entry_price - new_price)


@dataclass
class StrategyConfig:
    """Base configuration for trading strategies"""
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
    """Abstract base class for all trading strategies"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.positions: Dict[str, Position] = {}
        self.signals: List[Signal] = []
        self.performance_metrics: Dict[str, float] = {}
        self.state: Dict[str, Any] = {}
        self.is_initialized = False
        
    @abstractmethod
    def initialize(self, data: pd.DataFrame) -> None:
        """Initialize strategy with historical data"""
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals based on current market data"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: Signal, portfolio_value: float) -> float:
        """Calculate position size for a given signal"""
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
    """Manages multiple trading strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.allocations: Dict[str, float] = {}
        
    def add_strategy(self, name: str, strategy: BaseStrategy, allocation: float = 1.0) -> None:
        """Add a strategy with capital allocation"""
        if not 0 < allocation <= 1:
            raise ValueError("Allocation must be between 0 and 1")
        
        self.strategies[name] = strategy
        self.allocations[name] = allocation
        
    def remove_strategy(self, name: str) -> None:
        """Remove a strategy"""
        if name in self.strategies:
            del self.strategies[name]
            del self.allocations[name]
    
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
        """Get combined performance across all strategies"""
        combined_metrics = {}
        total_allocation = sum(self.allocations.values())
        
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