"""Portfolio management module for the algorithmic trading system.

This module provides portfolio management functionality including
position tracking, performance calculation, and portfolio analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np
import pandas as pd

from .data_types import Position, Trade, Order, OrderSide, PositionSide
from .events import Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    max_drawdown: float = 0.0
    calmar_ratio: Optional[float] = None
    win_rate: float = 0.0
    profit_factor: Optional[float] = None
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    average_win: float = 0.0
    average_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "volatility": self.volatility,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "max_drawdown": self.max_drawdown,
            "calmar_ratio": self.calmar_ratio,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "average_win": self.average_win,
            "average_loss": self.average_loss,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss
        }


class Portfolio:
    """Portfolio management system.
    
    Manages positions, tracks performance, and provides portfolio analytics.
    """
    
    def __init__(self, initial_capital: float = 1000000.0, name: str = "Default Portfolio"):
        self.name = name
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        self.orders: List[Order] = []
        
        # Performance tracking
        self.equity_curve: List[Tuple[datetime, float]] = [(datetime.utcnow(), initial_capital)]
        self.daily_returns: List[Tuple[datetime, float]] = []
        self.high_water_mark = initial_capital
        self.max_drawdown = 0.0
        
        # Statistics
        self.total_commission = 0.0
        self.total_fees = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        logger.info(f"Portfolio '{name}' initialized with capital: ${initial_capital:,.2f}")
    
    @property
    def total_value(self) -> float:
        """Calculate total portfolio value."""
        position_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + position_value
    
    @property
    def total_pnl(self) -> float:
        """Calculate total PnL (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
    
    @property
    def total_return(self) -> float:
        """Calculate total return percentage."""
        return (self.total_value - self.initial_capital) / self.initial_capital
    
    @property
    def leverage(self) -> float:
        """Calculate portfolio leverage."""
        total_exposure = sum(abs(pos.market_value) for pos in self.positions.values())
        return total_exposure / self.total_value if self.total_value > 0 else 0.0
    
    def add_trade(self, trade: Trade) -> Event:
        """Add a trade to the portfolio and update positions."""
        try:
            # Add trade to history
            self.trades.append(trade)
            
            # Update position
            if trade.symbol not in self.positions:
                self.positions[trade.symbol] = Position(
                    symbol=trade.symbol,
                    side=PositionSide.FLAT,
                    quantity=0.0
                )
            
            position = self.positions[trade.symbol]
            old_quantity = position.quantity
            
            # Add trade to position
            position.add_trade(trade)
            
            # Update cash based on trade
            if trade.is_buy:
                self.cash -= trade.value + trade.commission + trade.fees
            else:
                self.cash += trade.value - trade.commission - trade.fees
            
            # Update totals
            self.total_commission += trade.commission
            self.total_fees += trade.fees
            
            # If position was closed, add to realized PnL
            if old_quantity != 0 and position.quantity == 0:
                self.realized_pnl += position.realized_pnl
            
            # Update equity curve
            self._update_equity_curve(trade.timestamp)
            
            logger.info(f"Trade added: {trade.symbol} {trade.side.value} {trade.quantity}@{trade.price}")
            
            # Create portfolio update event
            return Event(
                event_type=EventType.PORTFOLIO_UPDATED,
                timestamp=trade.timestamp,
                data={
                    "symbol": trade.symbol,
                    "trade_id": trade.trade_id,
                    "portfolio_value": self.total_value,
                    "cash": self.cash,
                    "position_quantity": position.quantity,
                    "position_value": position.market_value
                }
            )
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
            return Event(
                event_type=EventType.ERROR,
                data={"error": str(e), "trade": trade.to_dict()}
            )
    
    def update_market_prices(self, prices: Dict[str, float], timestamp: Optional[datetime] = None) -> List[Event]:
        """Update market prices for all positions."""
        events = []
        timestamp = timestamp or datetime.utcnow()
        
        # Update unrealized PnL
        self.unrealized_pnl = 0.0
        
        for symbol, price in prices.items():
            if symbol in self.positions:
                position = self.positions[symbol]
                old_unrealized = position.unrealized_pnl
                
                position.update_market_price(price, timestamp)
                self.unrealized_pnl += position.unrealized_pnl
                
                # Create event if significant change
                if abs(position.unrealized_pnl - old_unrealized) > 100:  # $100 threshold
                    events.append(Event(
                        event_type=EventType.POSITION_MODIFIED,
                        timestamp=timestamp,
                        data={
                            "symbol": symbol,
                            "price": price,
                            "unrealized_pnl": position.unrealized_pnl,
                            "market_value": position.market_value
                        }
                    ))
        
        # Update equity curve
        self._update_equity_curve(timestamp)
        
        return events
    
    def _update_equity_curve(self, timestamp: datetime):
        """Update equity curve and performance metrics."""
        current_value = self.total_value
        
        # Add to equity curve
        self.equity_curve.append((timestamp, current_value))
        
        # Calculate daily return
        if len(self.equity_curve) > 1:
            previous_value = self.equity_curve[-2][1]
            daily_return = (current_value - previous_value) / previous_value
            self.daily_returns.append((timestamp, daily_return))
        
        # Update high water mark and drawdown
        if current_value > self.high_water_mark:
            self.high_water_mark = current_value
        
        current_drawdown = (self.high_water_mark - current_value) / self.high_water_mark
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
        
        # Keep only last 10000 entries to manage memory
        if len(self.equity_curve) > 10000:
            self.equity_curve = self.equity_curve[-10000:]
        if len(self.daily_returns) > 10000:
            self.daily_returns = self.daily_returns[-10000:]
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return self.positions.get(symbol)
    
    def get_open_positions(self) -> Dict[str, Position]:
        """Get all open positions."""
        return {symbol: pos for symbol, pos in self.positions.items() if not pos.is_flat}
    
    def close_position(self, symbol: str, price: float, timestamp: Optional[datetime] = None) -> Optional[Trade]:
        """Close a position by creating an offsetting trade."""
        position = self.positions.get(symbol)
        if not position or position.is_flat:
            logger.warning(f"No open position to close for {symbol}")
            return None
        
        # Create offsetting trade
        side = OrderSide.SELL if position.is_long else OrderSide.BUY
        quantity = abs(position.quantity)
        
        trade = Trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            timestamp=timestamp or datetime.utcnow()
        )
        
        # Add trade to portfolio
        self.add_trade(trade)
        
        logger.info(f"Position closed: {symbol} {quantity} shares at ${price}")
        return trade
    
    def close_all_positions(self, prices: Dict[str, float], timestamp: Optional[datetime] = None) -> List[Trade]:
        """Close all open positions."""
        trades = []
        
        for symbol, position in self.get_open_positions().items():
            if symbol in prices:
                trade = self.close_position(symbol, prices[symbol], timestamp)
                if trade:
                    trades.append(trade)
        
        return trades
    
    def calculate_performance_metrics(self, risk_free_rate: float = 0.02) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        if len(self.daily_returns) < 2:
            return PerformanceMetrics()
        
        # Convert to numpy arrays for calculations
        returns = np.array([ret for _, ret in self.daily_returns])
        
        # Basic metrics
        total_return = self.total_return
        
        # Annualized return (assuming 252 trading days)
        days = len(returns)
        if days > 0:
            annualized_return = (1 + total_return) ** (252 / days) - 1
        else:
            annualized_return = 0.0
        
        # Volatility (annualized)
        volatility = np.std(returns) * np.sqrt(252) if len(returns) > 1 else 0.0
        
        # Sharpe ratio
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else None
        
        # Sortino ratio (using downside deviation)
        downside_returns = returns[returns < 0]
        downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 1 else 0.0
        sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else None
        
        # Calmar ratio
        calmar_ratio = annualized_return / self.max_drawdown if self.max_drawdown > 0 else None
        
        # Trade statistics
        closed_trades = [trade for trade in self.trades if self._is_closing_trade(trade)]
        trade_pnls = [self._calculate_trade_pnl(trade) for trade in closed_trades]
        
        total_trades = len(trade_pnls)
        winning_trades = len([pnl for pnl in trade_pnls if pnl > 0])
        losing_trades = len([pnl for pnl in trade_pnls if pnl < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Profit factor
        gross_profit = sum([pnl for pnl in trade_pnls if pnl > 0])
        gross_loss = abs(sum([pnl for pnl in trade_pnls if pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        
        # Average win/loss
        wins = [pnl for pnl in trade_pnls if pnl > 0]
        losses = [pnl for pnl in trade_pnls if pnl < 0]
        
        average_win = np.mean(wins) if wins else 0.0
        average_loss = np.mean(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=self.max_drawdown,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss
        )
    
    def _is_closing_trade(self, trade: Trade) -> bool:
        """Determine if a trade closes a position."""
        # This is a simplified implementation
        # In practice, you'd need more sophisticated logic
        return True
    
    def _calculate_trade_pnl(self, trade: Trade) -> float:
        """Calculate PnL for a trade."""
        # This is a simplified implementation
        # In practice, you'd need to match opening and closing trades
        return trade.net_value if trade.is_sell else -trade.net_value
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary."""
        performance = self.calculate_performance_metrics()
        
        return {
            "name": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "total_value": self.total_value,
            "total_pnl": self.total_pnl,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "total_return": self.total_return,
            "leverage": self.leverage,
            "total_commission": self.total_commission,
            "total_fees": self.total_fees,
            "open_positions": len(self.get_open_positions()),
            "total_trades": len(self.trades),
            "performance_metrics": performance.to_dict(),
            "positions": {
                symbol: position.to_dict() 
                for symbol, position in self.positions.items() 
                if not position.is_flat
            }
        }
    
    def get_equity_curve_data(self, start_date: Optional[datetime] = None, 
                             end_date: Optional[datetime] = None) -> List[Tuple[datetime, float]]:
        """Get equity curve data for a date range."""
        if not start_date and not end_date:
            return self.equity_curve
        
        filtered_data = []
        for timestamp, value in self.equity_curve:
            if start_date and timestamp < start_date:
                continue
            if end_date and timestamp > end_date:
                continue
            filtered_data.append((timestamp, value))
        
        return filtered_data
    
    def reset(self, new_capital: Optional[float] = None):
        """Reset portfolio to initial state."""
        if new_capital:
            self.initial_capital = new_capital
        
        self.cash = self.initial_capital
        self.positions.clear()
        self.trades.clear()
        self.orders.clear()
        
        self.equity_curve = [(datetime.utcnow(), self.initial_capital)]
        self.daily_returns.clear()
        self.high_water_mark = self.initial_capital
        self.max_drawdown = 0.0
        
        self.total_commission = 0.0
        self.total_fees = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        logger.info(f"Portfolio '{self.name}' reset with capital: ${self.initial_capital:,.2f}")