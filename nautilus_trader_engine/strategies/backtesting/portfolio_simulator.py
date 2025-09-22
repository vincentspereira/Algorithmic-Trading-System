#!/usr/bin/env python3
"""
Portfolio Simulator Module

Simulates portfolio behavior during backtesting, including:
- Position tracking and management
- Cash flow simulation
- Margin and leverage calculations
- Transaction cost modeling
- Performance attribution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict

from .config import TransactionCosts
from .results import Trade, Position, PortfolioSnapshot
from ...indicators.consolidated_indicators import ConsolidatedIndicators



class OrderType(Enum):
    """Order types."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status."""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trading order."""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    price: Optional[float] = None
    stop_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    order_id: str = field(default_factory=lambda: f"order_{datetime.now().timestamp()}")
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: Optional[float] = None
    commission: float = 0.0
    
    @property
    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL
    
    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED
    
    @property
    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity


@dataclass
class PortfolioState:
    """Current state of the portfolio."""
    cash: float
    positions: Dict[str, Position]
    pending_orders: List[Order]
    total_value: float
    timestamp: datetime
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol."""
        return self.positions.get(symbol)
    
    def get_position_value(self, symbol: str, current_price: float) -> float:
        """Get current value of a position."""
        position = self.get_position(symbol)
        if position:
            return position.quantity * current_price
        return 0.0
    
    def get_total_position_value(self, current_prices: Dict[str, float]) -> float:
        """Get total value of all positions."""
        total = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total += position.quantity * current_prices[symbol]
        return total


class PortfolioSimulator:
    """Simulates portfolio behavior during backtesting."""
    
    def __init__(
        self,
        initial_capital: float,
        transaction_costs: Optional[TransactionCosts] = None,
        margin_requirement: float = 1.0,
        max_leverage: float = 1.0
    ):
        self.initial_capital = initial_capital
        self.transaction_costs = transaction_costs or TransactionCosts()
        self.margin_requirement = margin_requirement
        self.max_leverage = max_leverage
        
        # Portfolio state
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.pending_orders: List[Order] = []
        self.order_history: List[Order] = []
        self.trade_history: List[Trade] = []
        self.portfolio_history: List[PortfolioSnapshot] = []
        
        # Performance tracking
        self.total_commission_paid = 0.0
        self.total_slippage = 0.0
        self.peak_portfolio_value = initial_capital
        self.max_drawdown = 0.0
        
        # Risk tracking
        self.current_leverage = 0.0
        self.margin_used = 0.0
        
        logging.info(f"Portfolio simulator initialized with ${initial_capital:,.2f}")
    
    def submit_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        stop_price: Optional[float] = None
    ) -> str:
        """Submit a trading order.
        
        Args:
            symbol: Symbol to trade
            side: Buy or sell
            quantity: Quantity to trade
            order_type: Type of order
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            
        Returns:
            Order ID
        """
        order = Order(
            symbol=symbol,
            side=side,
            quantity=abs(quantity),  # Ensure positive quantity
            order_type=order_type,
            price=price,
            stop_price=stop_price
        )
        
        # Validate order
        if not self._validate_order(order):
            order.status = OrderStatus.REJECTED
            logging.warning(f"Order rejected: {order}")
            return order.order_id
        
        self.pending_orders.append(order)
        logging.info(f"Order submitted: {order.symbol} {order.side.value} {order.quantity}")
        
        return order.order_id
    
    def _validate_order(self, order: Order) -> bool:
        """Validate an order before submission."""
        # Check for valid quantity
        if order.quantity <= 0:
            return False
        
        # Check buying power for buy orders
        if order.is_buy:
            estimated_cost = order.quantity * (order.price or 0)
            if estimated_cost > self.cash:
                logging.warning(f"Insufficient cash for order: ${estimated_cost:,.2f} required, ${self.cash:,.2f} available")
                return False
        
        # Check position for sell orders
        elif order.is_sell:
            current_position = self.positions.get(order.symbol)
            if not current_position or current_position.quantity < order.quantity:
                available = current_position.quantity if current_position else 0
                logging.warning(f"Insufficient position for sell order: {order.quantity} required, {available} available")
                return False
        
        return True
    
    def process_market_data(
        self,
        timestamp: datetime,
        market_data: Dict[str, Dict[str, float]]
    ) -> List[Trade]:
        """Process market data and execute pending orders.
        
        Args:
            timestamp: Current timestamp
            market_data: Market data dict {symbol: {price_type: value}}
            
        Returns:
            List of executed trades
        """
        executed_trades = []
        
        # Process pending orders
        orders_to_remove = []
        for order in self.pending_orders:
            if order.symbol in market_data:
                trade = self._try_execute_order(order, market_data[order.symbol], timestamp)
                if trade:
                    executed_trades.append(trade)
                    orders_to_remove.append(order)
        
        # Remove executed orders
        for order in orders_to_remove:
            self.pending_orders.remove(order)
            self.order_history.append(order)
        
        # Update portfolio value
        current_prices = {symbol: data.get('close', data.get('price', 0)) 
                         for symbol, data in market_data.items()}
        self._update_portfolio_value(timestamp, current_prices)
        
        return executed_trades
    
    def _try_execute_order(
        self,
        order: Order,
        price_data: Dict[str, float],
        timestamp: datetime
    ) -> Optional[Trade]:
        """Try to execute a pending order."""
        execution_price = None
        
        if order.order_type == OrderType.MARKET:
            # Execute at current price (with slippage)
            execution_price = price_data.get('close', price_data.get('price'))
            if execution_price:
                execution_price = self._apply_slippage(execution_price, order)
        
        elif order.order_type == OrderType.LIMIT:
            current_price = price_data.get('close', price_data.get('price'))
            if current_price and order.price:
                if (order.is_buy and current_price <= order.price) or \
                   (order.is_sell and current_price >= order.price):
                    execution_price = order.price
        
        # Add other order types as needed
        
        if execution_price:
            return self._execute_order(order, execution_price, timestamp)
        
        return None
    
    def _execute_order(self, order: Order, execution_price: float, timestamp: datetime) -> Trade:
        """Execute an order at the given price."""
        # Calculate commission
        commission = self._calculate_commission(order, execution_price)
        
        # Update order
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = execution_price
        order.commission = commission
        
        # Update positions and cash
        if order.is_buy:
            self._add_position(order.symbol, order.quantity, execution_price)
            self.cash -= (order.quantity * execution_price + commission)
        else:
            self._reduce_position(order.symbol, order.quantity, execution_price)
            self.cash += (order.quantity * execution_price - commission)
        
        # Track commission
        self.total_commission_paid += commission
        
        # Create trade record
        trade = Trade(
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            entry_price=execution_price,
            exit_price=execution_price,  # Will be updated when position is closed
            entry_time=timestamp,
            exit_time=timestamp,  # Will be updated when position is closed
            pnl=0.0,  # Will be calculated when position is closed
            commission=commission
        )
        
        self.trade_history.append(trade)
        
        logging.info(
            f"Order executed: {order.symbol} {order.side.value} {order.quantity} @ ${execution_price:.2f} "
            f"(commission: ${commission:.2f})"
        )
        
        return trade
    
    def _add_position(self, symbol: str, quantity: float, price: float):
        """Add to or create a position."""
        if symbol in self.positions:
            # Update existing position (weighted average price)
            existing = self.positions[symbol]
            total_quantity = existing.quantity + quantity
            avg_price = ((existing.quantity * existing.avg_price) + (quantity * price)) / total_quantity
            
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=total_quantity,
                avg_price=avg_price,
                market_value=total_quantity * price,
                unrealized_pnl=(price - avg_price) * total_quantity
            )
        else:
            # Create new position
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=price,
                market_value=quantity * price,
                unrealized_pnl=0.0
            )
    
    def _reduce_position(self, symbol: str, quantity: float, price: float):
        """Reduce or close a position."""
        if symbol not in self.positions:
            logging.error(f"Trying to reduce non-existent position: {symbol}")
            return
        
        position = self.positions[symbol]
        
        if quantity >= position.quantity:
            # Close entire position
            realized_pnl = (price - position.avg_price) * position.quantity
            del self.positions[symbol]
            logging.info(f"Position closed: {symbol}, realized P&L: ${realized_pnl:.2f}")
        else:
            # Partial close
            realized_pnl = (price - position.avg_price) * quantity
            remaining_quantity = position.quantity - quantity
            
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=remaining_quantity,
                avg_price=position.avg_price,
                market_value=remaining_quantity * price,
                unrealized_pnl=(price - position.avg_price) * remaining_quantity
            )
            
            logging.info(f"Position reduced: {symbol}, realized P&L: ${realized_pnl:.2f}")
    
    def _calculate_commission(self, order: Order, execution_price: float) -> float:
        """Calculate commission for an order."""
        commission = 0.0
        
        # Per-share commission
        if hasattr(self.transaction_costs, 'commission_per_share'):
            commission += self.transaction_costs.commission_per_share * order.quantity
        
        # Percentage commission
        if hasattr(self.transaction_costs, 'commission_percent'):
            commission += self.transaction_costs.commission_percent * order.quantity * execution_price
        
        # Minimum commission
        if hasattr(self.transaction_costs, 'min_commission'):
            commission = max(commission, self.transaction_costs.min_commission)
        
        return commission
    
    def _apply_slippage(self, price: float, order: Order) -> float:
        """Apply slippage to execution price."""
        if not hasattr(self.transaction_costs, 'slippage_percent'):
            return price
        
        slippage_factor = self.transaction_costs.slippage_percent
        
        if order.is_buy:
            # Buy orders get worse price (higher)
            slipped_price = price * (1 + slippage_factor)
        else:
            # Sell orders get worse price (lower)
            slipped_price = price * (1 - slippage_factor)
        
        slippage_cost = abs(slipped_price - price) * order.quantity
        self.total_slippage += slippage_cost
        
        return slipped_price
    
    def _update_portfolio_value(self, timestamp: datetime, current_prices: Dict[str, float]):
        """Update portfolio value and metrics."""
        # Calculate position values
        position_value = 0.0
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                position.market_value = position.quantity * current_price
                position.unrealized_pnl = (current_price - position.avg_price) * position.quantity
                position_value += position.market_value
        
        # Total portfolio value
        total_value = self.cash + position_value
        
        # Update peak and drawdown
        if total_value > self.peak_portfolio_value:
            self.peak_portfolio_value = total_value
        
        current_drawdown = (self.peak_portfolio_value - total_value) / self.peak_portfolio_value
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        # Calculate leverage
        if total_value > 0:
            self.current_leverage = position_value / total_value
        
        # Create portfolio snapshot
        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            cash=self.cash,
            positions=dict(self.positions),
            total_value=total_value,
            unrealized_pnl=sum(pos.unrealized_pnl for pos in self.positions.values()),
            realized_pnl=sum(trade.pnl for trade in self.trade_history)
        )
        
        self.portfolio_history.append(snapshot)
    
    def get_current_state(self) -> PortfolioState:
        """Get current portfolio state."""
        return PortfolioState(
            cash=self.cash,
            positions=dict(self.positions),
            pending_orders=list(self.pending_orders),
            total_value=self.get_total_value(),
            timestamp=datetime.now()
        )
    
    def get_total_value(self, current_prices: Optional[Dict[str, float]] = None) -> float:
        """Get total portfolio value."""
        position_value = 0.0
        
        if current_prices:
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    position_value += position.quantity * current_prices[symbol]
        else:
            position_value = sum(pos.market_value for pos in self.positions.values())
        
        return self.cash + position_value
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        current_value = self.get_total_value()
        total_return = (current_value - self.initial_capital) / self.initial_capital
        
        return {
            'initial_capital': self.initial_capital,
            'current_value': current_value,
            'total_return': total_return,
            'total_pnl': current_value - self.initial_capital,
            'cash': self.cash,
            'position_count': len(self.positions),
            'total_trades': len(self.trade_history),
            'total_commission': self.total_commission_paid,
            'total_slippage': self.total_slippage,
            'max_drawdown': self.max_drawdown,
            'current_leverage': self.current_leverage
        }
    
    def close_all_positions(self, current_prices: Dict[str, float], timestamp: datetime) -> List[Trade]:
        """Close all open positions."""
        trades = []
        
        for symbol in list(self.positions.keys()):
            if symbol in current_prices:
                position = self.positions[symbol]
                order_id = self.submit_order(
                    symbol=symbol,
                    side=OrderSide.SELL,
                    quantity=position.quantity,
                    order_type=OrderType.MARKET
                )
                
                # Process the order immediately
                market_data = {symbol: {'close': current_prices[symbol]}}
                executed_trades = self.process_market_data(timestamp, market_data)
                trades.extend(executed_trades)
        
        return trades
    
    def reset(self):
        """Reset portfolio to initial state."""
        self.cash = self.initial_capital
        self.positions.clear()
        self.pending_orders.clear()
        self.order_history.clear()
        self.trade_history.clear()
        self.portfolio_history.clear()
        
        self.total_commission_paid = 0.0
        self.total_slippage = 0.0
        self.peak_portfolio_value = self.initial_capital
        self.max_drawdown = 0.0
        self.current_leverage = 0.0
        self.margin_used = 0.0
        
        logging.info("Portfolio simulator reset")


def create_portfolio_simulator(
    initial_capital: float,
    commission_per_share: float = 0.01,
    commission_percent: float = 0.0,
    slippage_percent: float = 0.001,
    margin_requirement: float = 1.0,
    max_leverage: float = 1.0
) -> PortfolioSimulator:
    """Factory function to create a PortfolioSimulator.
    
    Args:
        initial_capital: Starting capital
        commission_per_share: Commission per share
        commission_percent: Commission as percentage of trade value
        slippage_percent: Slippage as percentage of price
        margin_requirement: Margin requirement (1.0 = 100%)
        max_leverage: Maximum allowed leverage
        
    Returns:
        PortfolioSimulator instance
    """
    transaction_costs = TransactionCosts(
        commission_per_share=commission_per_share,
        commission_percent=commission_percent
    )
    
    # Add slippage if the TransactionCosts class supports it
    if hasattr(transaction_costs, 'slippage_percent'):
        transaction_costs.slippage_percent = slippage_percent
    
    return PortfolioSimulator(
        initial_capital=initial_capital,
        transaction_costs=transaction_costs,
        margin_requirement=margin_requirement,
        max_leverage=max_leverage
    )


# Example usage
if __name__ == "__main__":
    # Create portfolio simulator
    simulator = create_portfolio_simulator(
        initial_capital=100000,
        commission_per_share=0.01,
        slippage_percent=0.001
    )
    
    # Submit some orders
    simulator.submit_order('AAPL', OrderSide.BUY, 100, OrderType.MARKET)
    simulator.submit_order('GOOGL', OrderSide.BUY, 50, OrderType.LIMIT, price=2500.0)
    
    # Simulate market data
    market_data = {
        'AAPL': {'close': 150.0},
        'GOOGL': {'close': 2480.0}  # Below limit price, should execute
    }
    
    trades = simulator.process_market_data(datetime.now(), market_data)
    
    print(f"Executed {len(trades)} trades")
    print(f"Portfolio summary: {simulator.get_performance_summary()}")