"""
TradingGym Engine Implementation

This module provides a wrapper around the TradingGym library
to standardize backtesting operations and results.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

try:
    import gym
    from trading_gym import TradingEnv
    TRADING_GYM_AVAILABLE = True
except ImportError:
    TRADING_GYM_AVAILABLE = False
    logging.warning("TradingGym not available. Install with: pip install trading-gym")

from .base import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


class TradingGymEngine(BacktestEngine):
    """TradingGym-based backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000.0):
        super().__init__(initial_capital)
        
        if not TRADING_GYM_AVAILABLE:
            raise ImportError("TradingGym is not available. Install with: pip install trading-gym")
        
        # Initialize environment
        self.env = None
        self.data = None
        self.symbol = None
        self.strategy = None
        
        # Tracking variables
        self.portfolio_values = []
        self.trades = []
        self.positions = []
        
        logger.info(f"TradingGymEngine initialized with capital: ${initial_capital:,.2f}")
    
    def add_strategy(self, strategy: Any, **kwargs) -> None:
        """Add a trading strategy to the engine"""
        self.strategy = strategy
        
        # If it's a class, instantiate it
        if hasattr(strategy, '__call__') and not hasattr(strategy, 'get_action'):
            self.strategy = strategy(**kwargs)
        
        logger.info(f"Added strategy: {type(self.strategy).__name__}")
    
    def add_data(self, data: pd.DataFrame, symbol: str) -> None:
        """Add market data to the engine"""
        
        # Ensure required columns exist
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            # Try to map common column variations
            column_mapping = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume',
                'OPEN': 'open', 'HIGH': 'high', 'LOW': 'low', 'CLOSE': 'close', 'VOLUME': 'volume'
            }
            
            data_copy = data.copy()
            for old_col, new_col in column_mapping.items():
                if old_col in data_copy.columns:
                    data_copy[new_col] = data_copy[old_col]
            
            # Check again for missing columns
            missing_columns = [col for col in required_columns if col not in data_copy.columns]
            if missing_columns:
                # Fill missing columns with close price or default values
                for col in missing_columns:
                    if col == 'volume':
                        data_copy[col] = 1000000  # Default volume
                    else:
                        data_copy[col] = data_copy['close'] if 'close' in data_copy.columns else 0
            
            data = data_copy
        
        # Ensure datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'date' in data.columns:
                data = data.set_index('date')
            elif 'Date' in data.columns:
                data = data.set_index('Date')
            else:
                data.index = pd.to_datetime(data.index)
        
        self.data = data
        self.symbol = symbol
        
        # Create TradingGym environment
        self._create_environment()
        
        logger.info(f"Added data for {symbol}: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    
    def _create_environment(self):
        """Create TradingGym environment from data"""
        if self.data is None:
            return
        
        # Create a simple trading environment
        # Note: This is a simplified implementation as TradingGym API may vary
        try:
            # Convert data to format expected by TradingGym
            env_data = self.data[['open', 'high', 'low', 'close', 'volume']].values
            
            # Create environment configuration
            config = {
                'data': env_data,
                'initial_balance': self.initial_capital,
                'commission': 0.001,  # 0.1% commission
                'window_size': 30,    # Lookback window
            }
            
            # This is a placeholder - actual TradingGym initialization may differ
            self.env = self._create_simple_env(config)
            
        except Exception as e:
            logger.warning(f"Failed to create TradingGym environment: {e}")
            # Fallback to simple custom environment
            self.env = self._create_simple_env({
                'data': self.data,
                'initial_balance': self.initial_capital,
                'commission': 0.001
            })
    
    def _create_simple_env(self, config):
        """Create a simple trading environment as fallback"""
        return SimpleTradingEnv(config)
    
    def run(self, **kwargs) -> BacktestResult:
        """Run the backtest and return results"""
        
        if not self.strategy:
            raise ValueError("No strategy added to engine")
        
        if not self.data is not None:
            raise ValueError("No data added to engine")
        
        logger.info("Starting TradingGym backtest...")
        
        # Reset environment and strategy
        observation = self.env.reset()
        if hasattr(self.strategy, 'reset'):
            self.strategy.reset()
        
        # Initialize tracking
        self.portfolio_values = [self.initial_capital]
        self.trades = []
        self.positions = []
        
        done = False
        step = 0
        current_position = 0
        entry_price = 0
        
        while not done:
            # Get action from strategy
            if hasattr(self.strategy, 'get_action'):
                action = self.strategy.get_action(observation)
            else:
                # Fallback for simple strategies
                action = 0  # Hold
            
            # Execute action in environment
            observation, reward, done, info = self.env.step(action)
            
            # Track portfolio value
            portfolio_value = info.get('portfolio_value', self.initial_capital)
            self.portfolio_values.append(portfolio_value)
            
            # Track trades
            if action != 0:  # Not hold
                if action == 1 and current_position <= 0:  # Buy
                    if current_position < 0:  # Close short position
                        trade_pnl = entry_price - observation.get('close', 0)
                        self.trades.append({
                            'entry_date': step - 1,
                            'exit_date': step,
                            'entry_price': entry_price,
                            'exit_price': observation.get('close', 0),
                            'pnl': trade_pnl,
                            'size': -current_position,
                            'type': 'short'
                        })
                    
                    current_position = 1
                    entry_price = observation.get('close', 0)
                    
                elif action == 2 and current_position >= 0:  # Sell
                    if current_position > 0:  # Close long position
                        trade_pnl = observation.get('close', 0) - entry_price
                        self.trades.append({
                            'entry_date': step - 1,
                            'exit_date': step,
                            'entry_price': entry_price,
                            'exit_price': observation.get('close', 0),
                            'pnl': trade_pnl,
                            'size': current_position,
                            'type': 'long'
                        })
                    
                    current_position = -1
                    entry_price = observation.get('close', 0)
            
            # Track position
            self.positions.append({
                'date': step,
                'position': current_position,
                'price': observation.get('close', 0)
            })
            
            step += 1
        
        # Convert tracking data to pandas
        portfolio_series = pd.Series(
            self.portfolio_values,
            index=self.data.index[:len(self.portfolio_values)]
        )
        
        trades_df = pd.DataFrame(self.trades)
        
        # Calculate metrics
        metrics = self.calculate_metrics(portfolio_series, trades_df)
        
        # Create result object
        self.results = BacktestResult(
            total_return=metrics['total_return'],
            annual_return=metrics['annual_return'],
            sharpe_ratio=metrics['sharpe_ratio'],
            max_drawdown=metrics['max_drawdown'],
            volatility=metrics['volatility'],
            total_trades=metrics['total_trades'],
            winning_trades=metrics['winning_trades'],
            losing_trades=metrics['losing_trades'],
            win_rate=metrics['win_rate'],
            avg_win=metrics['avg_win'],
            avg_loss=metrics['avg_loss'],
            profit_factor=metrics['profit_factor'],
            initial_capital=metrics['initial_capital'],
            final_capital=metrics['final_capital'],
            peak_capital=metrics['peak_capital'],
            calmar_ratio=metrics['calmar_ratio'],
            sortino_ratio=metrics['sortino_ratio'],
            strategy_name=type(self.strategy).__name__ if self.strategy else "Unknown",
            symbol=self.symbol or "Unknown",
            start_date=self.data.index[0] if self.data is not None else None,
            end_date=self.data.index[-1] if self.data is not None else None,
            engine="trading_gym",
            portfolio_values=portfolio_series,
            trades=trades_df
        )
        
        logger.info(f"TradingGym backtest completed. Total return: {metrics['total_return']:.2%}, "
                   f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}, "
                   f"Max drawdown: {metrics['max_drawdown']:.2%}")
        
        return self.results
    
    def get_portfolio_values(self) -> pd.Series:
        """Get portfolio value time series"""
        if not self.portfolio_values:
            return pd.Series()
        
        return pd.Series(
            self.portfolio_values,
            index=self.data.index[:len(self.portfolio_values)] if self.data is not None else range(len(self.portfolio_values))
        )
    
    def get_trades(self) -> pd.DataFrame:
        """Get trade history"""
        return pd.DataFrame(self.trades)


class SimpleTradingEnv:
    """
    Simple trading environment as fallback when TradingGym is not available
    or fails to initialize properly.
    """
    
    def __init__(self, config):
        self.data = config['data']
        self.initial_balance = config['initial_balance']
        self.commission = config.get('commission', 0.001)
        
        # State variables
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        
        if isinstance(self.data, pd.DataFrame):
            self.prices = self.data['close'].values
        else:
            self.prices = self.data[:, 3]  # Assume close is 4th column
    
    def reset(self):
        """Reset environment to initial state"""
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        
        return self._get_observation()
    
    def step(self, action):
        """Execute one step in the environment"""
        if self.current_step >= len(self.prices) - 1:
            return self._get_observation(), 0, True, self._get_info()
        
        current_price = self.prices[self.current_step]
        reward = 0
        
        # Execute action
        if action == 1:  # Buy
            if self.position <= 0:
                # Close short position if any
                if self.position < 0:
                    profit = (self.entry_price - current_price) * abs(self.position)
                    self.balance += profit - (abs(self.position) * current_price * self.commission)
                
                # Open long position
                shares = int(self.balance * 0.95 / current_price)  # Use 95% of balance
                if shares > 0:
                    self.position = shares
                    self.entry_price = current_price
                    self.balance -= shares * current_price * (1 + self.commission)
        
        elif action == 2:  # Sell
            if self.position >= 0:
                # Close long position if any
                if self.position > 0:
                    profit = (current_price - self.entry_price) * self.position
                    self.balance += self.position * current_price * (1 - self.commission)
                    self.position = 0
                
                # Open short position (simplified)
                shares = int(self.balance * 0.95 / current_price)
                if shares > 0:
                    self.position = -shares
                    self.entry_price = current_price
        
        # Calculate reward (portfolio value change)
        portfolio_value = self._calculate_portfolio_value()
        reward = portfolio_value - self.initial_balance
        
        self.current_step += 1
        done = self.current_step >= len(self.prices) - 1
        
        return self._get_observation(), reward, done, self._get_info()
    
    def _get_observation(self):
        """Get current observation"""
        if self.current_step >= len(self.prices):
            return {'close': self.prices[-1], 'prices': self.prices[-30:].tolist()}
        
        return {
            'close': self.prices[self.current_step],
            'prices': self.prices[max(0, self.current_step-29):self.current_step+1].tolist()
        }
    
    def _get_info(self):
        """Get additional info"""
        return {
            'portfolio_value': self._calculate_portfolio_value(),
            'balance': self.balance,
            'position': self.position,
            'step': self.current_step
        }
    
    def _calculate_portfolio_value(self):
        """Calculate current portfolio value"""
        if self.current_step >= len(self.prices):
            current_price = self.prices[-1]
        else:
            current_price = self.prices[self.current_step]
        
        return self.balance + (self.position * current_price)