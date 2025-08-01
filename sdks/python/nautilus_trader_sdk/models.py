"""
Nautilus Trader SDK Models

Data models for the Nautilus Trader Python SDK.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import json

class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "buy"
    SELL = "sell"

class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TimeInForce(Enum):
    """Time in force enumeration"""
    DAY = "DAY"
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill

class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"

class StrategyStatus(Enum):
    """Strategy status enumeration"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"

@dataclass
class Order:
    """Order model"""
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    status: OrderStatus
    created_at: datetime
    price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    time_in_force: TimeInForce = TimeInForce.DAY
    updated_at: Optional[datetime] = None
    commission: float = 0.0
    tags: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create Order from dictionary"""
        return cls(
            id=data['id'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            quantity=float(data['quantity']),
            order_type=OrderType(data['order_type']),
            status=OrderStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            price=float(data['price']) if data.get('price') else None,
            stop_price=float(data['stop_price']) if data.get('stop_price') else None,
            filled_quantity=float(data.get('filled_quantity', 0)),
            average_price=float(data['average_price']) if data.get('average_price') else None,
            time_in_force=TimeInForce(data.get('time_in_force', 'DAY')),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            commission=float(data.get('commission', 0)),
            tags=data.get('tags', {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Order to dictionary"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'side': self.side.value,
            'quantity': self.quantity,
            'order_type': self.order_type.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'price': self.price,
            'stop_price': self.stop_price,
            'filled_quantity': self.filled_quantity,
            'average_price': self.average_price,
            'time_in_force': self.time_in_force.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'commission': self.commission,
            'tags': self.tags
        }
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """Check if order is active (can be filled)"""
        return self.status in [OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def remaining_quantity(self) -> float:
        """Get remaining quantity to be filled"""
        return self.quantity - self.filled_quantity

@dataclass
class Position:
    """Position model"""
    symbol: str
    quantity: float
    average_price: float
    market_price: float
    side: PositionSide
    unrealized_pnl: float
    realized_pnl: float = 0.0
    commission: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create Position from dictionary"""
        return cls(
            symbol=data['symbol'],
            quantity=float(data['quantity']),
            average_price=float(data['average_price']),
            market_price=float(data['market_price']),
            side=PositionSide(data['side']),
            unrealized_pnl=float(data['unrealized_pnl']),
            realized_pnl=float(data.get('realized_pnl', 0)),
            commission=float(data.get('commission', 0)),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            tags=data.get('tags', {})
        )
    
    @property
    def market_value(self) -> float:
        """Get current market value"""
        return abs(self.quantity) * self.market_price
    
    @property
    def percentage_change(self) -> float:
        """Get percentage change from average price"""
        if self.average_price == 0:
            return 0.0
        return ((self.market_price - self.average_price) / self.average_price) * 100
    
    @property
    def is_long(self) -> bool:
        """Check if position is long"""
        return self.side == PositionSide.LONG
    
    @property
    def is_short(self) -> bool:
        """Check if position is short"""
        return self.side == PositionSide.SHORT

@dataclass
class Trade:
    """Trade model"""
    id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    timestamp: datetime
    commission: float = 0.0
    pnl: Optional[float] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """Create Trade from dictionary"""
        return cls(
            id=data['id'],
            order_id=data['order_id'],
            symbol=data['symbol'],
            side=OrderSide(data['side']),
            quantity=float(data['quantity']),
            price=float(data['price']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            commission=float(data.get('commission', 0)),
            pnl=float(data['pnl']) if data.get('pnl') is not None else None,
            tags=data.get('tags', {})
        )
    
    @property
    def notional_value(self) -> float:
        """Get notional value of trade"""
        return self.quantity * self.price

@dataclass
class Portfolio:
    """Portfolio model"""
    total_value: float
    cash_balance: float
    invested_value: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    positions: List[Position] = field(default_factory=list)
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Portfolio':
        """Create Portfolio from dictionary"""
        positions = [Position.from_dict(pos) for pos in data.get('positions', [])]
        return cls(
            total_value=float(data['total_value']),
            cash_balance=float(data['cash_balance']),
            invested_value=float(data['invested_value']),
            unrealized_pnl=float(data['unrealized_pnl']),
            realized_pnl=float(data['realized_pnl']),
            daily_pnl=float(data.get('daily_pnl', 0)),
            positions=positions,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )
    
    @property
    def total_pnl(self) -> float:
        """Get total P&L"""
        return self.unrealized_pnl + self.realized_pnl
    
    @property
    def positions_count(self) -> int:
        """Get number of positions"""
        return len(self.positions)
    
    @property
    def long_positions(self) -> List[Position]:
        """Get long positions"""
        return [pos for pos in self.positions if pos.is_long]
    
    @property
    def short_positions(self) -> List[Position]:
        """Get short positions"""
        return [pos for pos in self.positions if pos.is_short]

@dataclass
class MarketData:
    """Market data model"""
    symbol: str
    last_price: float
    bid_price: Optional[float]
    ask_price: Optional[float]
    volume: Optional[int]
    change: Optional[float]
    change_percent: Optional[float]
    high: Optional[float]
    low: Optional[float]
    timestamp: datetime
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MarketData':
        """Create MarketData from dictionary"""
        return cls(
            symbol=data['symbol'],
            last_price=float(data['last_price']),
            bid_price=float(data['bid_price']) if data.get('bid_price') else None,
            ask_price=float(data['ask_price']) if data.get('ask_price') else None,
            volume=int(data['volume']) if data.get('volume') else None,
            change=float(data['change']) if data.get('change') else None,
            change_percent=float(data['change_percent']) if data.get('change_percent') else None,
            high=float(data['high']) if data.get('high') else None,
            low=float(data['low']) if data.get('low') else None,
            timestamp=datetime.fromisoformat(data['timestamp'])
        )
    
    @property
    def spread(self) -> Optional[float]:
        """Get bid-ask spread"""
        if self.bid_price and self.ask_price:
            return self.ask_price - self.bid_price
        return None
    
    @property
    def mid_price(self) -> Optional[float]:
        """Get mid price"""
        if self.bid_price and self.ask_price:
            return (self.bid_price + self.ask_price) / 2
        return None

@dataclass
class Strategy:
    """Strategy model"""
    id: str
    name: str
    description: str
    status: StrategyStatus
    config: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None
    performance: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Strategy':
        """Create Strategy from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            status=StrategyStatus(data['status']),
            config=data['config'],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            performance=data.get('performance')
        )
    
    @property
    def is_running(self) -> bool:
        """Check if strategy is running"""
        return self.status == StrategyStatus.RUNNING

@dataclass
class Backtest:
    """Backtest model"""
    id: str
    name: str
    strategy_config: Dict[str, Any]
    start_date: datetime
    end_date: datetime
    status: str
    results: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Backtest':
        """Create Backtest from dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            strategy_config=data['strategy_config'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            status=data['status'],
            results=data.get('results'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None
        )
    
    @property
    def is_completed(self) -> bool:
        """Check if backtest is completed"""
        return self.status == 'completed'
    
    @property
    def total_return(self) -> Optional[float]:
        """Get total return from results"""
        if self.results:
            return self.results.get('total_return')
        return None

@dataclass
class RiskMetrics:
    """Risk metrics model"""
    var_95: Optional[float]
    var_99: Optional[float]
    expected_shortfall: Optional[float]
    beta: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    volatility: Optional[float]
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RiskMetrics':
        """Create RiskMetrics from dictionary"""
        correlation_matrix = None
        if data.get('correlation_matrix'):
            if isinstance(data['correlation_matrix'], str):
                correlation_matrix = json.loads(data['correlation_matrix'])
            else:
                correlation_matrix = data['correlation_matrix']
        
        return cls(
            var_95=float(data['var_95']) if data.get('var_95') else None,
            var_99=float(data['var_99']) if data.get('var_99') else None,
            expected_shortfall=float(data['expected_shortfall']) if data.get('expected_shortfall') else None,
            beta=float(data['beta']) if data.get('beta') else None,
            sharpe_ratio=float(data['sharpe_ratio']) if data.get('sharpe_ratio') else None,
            max_drawdown=float(data['max_drawdown']) if data.get('max_drawdown') else None,
            volatility=float(data['volatility']) if data.get('volatility') else None,
            correlation_matrix=correlation_matrix,
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )

@dataclass
class Analytics:
    """Analytics model"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    updated_at: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Analytics':
        """Create Analytics from dictionary"""
        return cls(
            total_trades=int(data['total_trades']),
            winning_trades=int(data['winning_trades']),
            losing_trades=int(data['losing_trades']),
            win_rate=float(data['win_rate']),
            average_win=float(data['average_win']),
            average_loss=float(data['average_loss']),
            profit_factor=float(data['profit_factor']),
            max_consecutive_wins=int(data['max_consecutive_wins']),
            max_consecutive_losses=int(data['max_consecutive_losses']),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None
        )

# Utility functions for model conversion
def parse_orders(data: List[Dict[str, Any]]) -> List[Order]:
    """Parse list of orders from API response"""
    return [Order.from_dict(order_data) for order_data in data]

def parse_positions(data: List[Dict[str, Any]]) -> List[Position]:
    """Parse list of positions from API response"""
    return [Position.from_dict(pos_data) for pos_data in data]

def parse_trades(data: List[Dict[str, Any]]) -> List[Trade]:
    """Parse list of trades from API response"""
    return [Trade.from_dict(trade_data) for trade_data in data]

def parse_strategies(data: List[Dict[str, Any]]) -> List[Strategy]:
    """Parse list of strategies from API response"""
    return [Strategy.from_dict(strategy_data) for strategy_data in data]

def parse_backtests(data: List[Dict[str, Any]]) -> List[Backtest]:
    """Parse list of backtests from API response"""
    return [Backtest.from_dict(backtest_data) for backtest_data in data]