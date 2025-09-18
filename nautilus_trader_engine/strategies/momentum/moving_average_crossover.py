"""
Moving Average Crossover Strategy

This strategy implements a simple moving average crossover system:
- Buy when fast MA crosses above slow MA
- Sell when fast MA crosses below slow MA

The strategy can be used with both backtrader and TradingGym engines.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import backtrader as bt
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
import logging
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators


logger = logging.getLogger(__name__)


class MovingAverageCrossover(bt.Strategy):
    """
    Moving Average Crossover Strategy for Backtrader
    
    Parameters:
    - fast_period: Period for fast moving average (default: 10)
    - slow_period: Period for slow moving average (default: 30)
    - position_size: Position size as fraction of portfolio (default: 0.95)
    """
    
    params = (
        ('fast_period', 10),
        ('slow_period', 30),
        ('position_size', 0.95),
        ('printlog', False),
    )
    
    def __init__(self):
        """Initialize the strategy"""
        # Keep references to data lines
        self.dataclose = self.datas[0].close
        
        # Initialize moving averages
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.fast_period
        )
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.slow_period
        )
        
        # Create crossover signal
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)
        
        # Track orders and trades
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        logger.info(f"MovingAverageCrossover initialized: fast_period={self.params.fast_period}, "
                   f"slow_period={self.params.slow_period}")
    
    def notify_order(self, order):
        """Notification of order status"""
        if order.status in [order.Submitted, order.Accepted]:
            # Order submitted/accepted - no action required
            return
        
        # Check if order is completed
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                        f'Cost: {order.executed.value:.2f}, Comm: {order.executed.comm:.2f}')
            
            self.bar_executed = len(self)
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        
        # Reset order reference
        self.order = None
    
    def notify_trade(self, trade):
        """Notification of trade completion"""
        if not trade.isclosed:
            return
        
        self.trade_count += 1
        pnl = trade.pnl
        
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        self.log(f'OPERATION PROFIT, GROSS: {trade.pnl:.2f}, NET: {trade.pnlcomm:.2f}')
    
    def next(self):
        """Main strategy logic executed on each bar"""
        # Log current price
        self.log(f'Close: {self.dataclose[0]:.2f}, Fast MA: {self.fast_ma[0]:.2f}, '
                f'Slow MA: {self.slow_ma[0]:.2f}')
        
        # Check if we have pending orders
        if self.order:
            return
        
        # Check if we are in the market
        if not self.position:
            # Not in market - check for buy signal
            if self.crossover[0] > 0:  # Fast MA crossed above slow MA
                self.log('BUY CREATE, {:.2f}'.format(self.dataclose[0]))
                
                # Calculate position size
                cash = self.broker.get_cash()
                price = self.dataclose[0]
                size = int((cash * self.params.position_size) / price)
                
                # Create buy order
                self.order = self.buy(size=size)
        
        else:
            # In market - check for sell signal
            if self.crossover[0] < 0:  # Fast MA crossed below slow MA
                self.log('SELL CREATE, {:.2f}'.format(self.dataclose[0]))
                
                # Create sell order
                self.order = self.sell(size=self.position.size)
    
    def log(self, txt, dt=None):
        """Logging function"""
        if self.params.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print(f'{dt.isoformat()}, {txt}')
    
    def stop(self):
        """Called when strategy stops"""
        win_rate = (self.winning_trades / self.trade_count * 100) if self.trade_count > 0 else 0
        
        self.log(f'Strategy completed - Total trades: {self.trade_count}, '
                f'Winning: {self.winning_trades}, Losing: {self.losing_trades}, '
                f'Win rate: {win_rate:.1f}%')
        
        logger.info(f"Strategy completed with {self.trade_count} trades, "
                   f"win rate: {win_rate:.1f}%")


class MovingAverageCrossoverGym:
    """
    Moving Average Crossover Strategy for TradingGym
    
    This is a simplified version that works with TradingGym's environment structure.
    """
    
    def __init__(self, fast_period: int = 10, slow_period: int = 30):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.position = 0  # -1: short, 0: neutral, 1: long
        self.last_action = 0
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.entry_price = None
        
        logger.info(f"MovingAverageCrossoverGym initialized: fast_period={fast_period}, "
                   f"slow_period={slow_period}")
    
    def calculate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Calculate trading signals based on moving average crossover"""
        
        # Calculate moving averages
        fast_ma = data['close'].rolling(window=self.fast_period).mean()
        slow_ma = data['close'].rolling(window=self.slow_period).mean()
        
        # Calculate crossover signals
        signals = pd.Series(0, index=data.index)
        
        # Buy signal: fast MA crosses above slow MA
        buy_signals = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
        signals[buy_signals] = 1
        
        # Sell signal: fast MA crosses below slow MA
        sell_signals = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))
        signals[sell_signals] = -1
        
        return signals
    
    def get_action(self, observation: Dict[str, Any]) -> int:
        """
        Get trading action based on current observation
        
        Args:
            observation: Dictionary containing market data and indicators
            
        Returns:
            int: Action (0: hold, 1: buy, 2: sell)
        """
        
        # Extract price data from observation
        if 'prices' in observation:
            prices = observation['prices']
        elif 'close' in observation:
            prices = [observation['close']]
        else:
            return 0  # Hold if no price data
        
        # Need enough data for moving averages
        if len(prices) < self.slow_period:
            return 0
        
        # Calculate moving averages
        fast_ma = np.mean(prices[-self.fast_period:])
        slow_ma = np.mean(prices[-self.slow_period:])
        
        # Previous moving averages
        if len(prices) > self.slow_period:
            prev_fast_ma = np.mean(prices[-self.fast_period-1:-1])
            prev_slow_ma = np.mean(prices[-self.slow_period-1:-1])
        else:
            return 0
        
        # Determine action based on crossover
        action = 0  # Hold
        
        # Buy signal: fast MA crosses above slow MA
        if fast_ma > slow_ma and prev_fast_ma <= prev_slow_ma:
            if self.position <= 0:  # Not long
                action = 1  # Buy
                self.position = 1
                self.entry_price = prices[-1]
        
        # Sell signal: fast MA crosses below slow MA
        elif fast_ma < slow_ma and prev_fast_ma >= prev_slow_ma:
            if self.position >= 0:  # Not short
                action = 2  # Sell
                
                # Track trade performance
                if self.position == 1 and self.entry_price:
                    pnl = prices[-1] - self.entry_price
                    self.trade_count += 1
                    if pnl > 0:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1
                
                self.position = -1
                self.entry_price = prices[-1]
        
        self.last_action = action
        return action
    
    def reset(self):
        """Reset strategy state"""
        self.position = 0
        self.last_action = 0
        self.trade_count = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.entry_price = None
    
    def get_stats(self) -> Dict[str, float]:
        """Get strategy performance statistics"""
        win_rate = (self.winning_trades / self.trade_count) if self.trade_count > 0 else 0
        
        return {
            'total_trades': self.trade_count,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate
        }


# Factory function to create strategy instances
def create_ma_crossover_strategy(engine_type: str = 'backtrader', **kwargs):
    """
    Factory function to create Moving Average Crossover strategy
    
    Args:
        engine_type: 'backtrader' or 'trading_gym'
        **kwargs: Strategy parameters
        
    Returns:
        Strategy instance appropriate for the specified engine
    """
    
    if engine_type.lower() == 'backtrader':
        # Return class for backtrader (will be instantiated by backtrader)
        return MovingAverageCrossover
    elif engine_type.lower() == 'trading_gym':
        return MovingAverageCrossoverGym(**kwargs)
    else:
        raise ValueError(f"Unsupported engine type: {engine_type}")