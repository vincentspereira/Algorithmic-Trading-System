"""
Backtrader Engine Implementation

This module provides a wrapper around the backtrader library
to standardize backtesting operations and results.
"""

# Optional backtrader import to avoid collection-time failures
try:
    import backtrader as bt  # type: ignore
    BACKTRADER_AVAILABLE = True
except Exception:
    bt = None  # type: ignore
    BACKTRADER_AVAILABLE = False

import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .base import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


class BacktraderEngine(BacktestEngine):
    """Backtrader-based backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000.0):
        super().__init__(initial_capital)
        
        # Initialize cerebro
        self.cerebro = bt.Cerebro()
        
        # Set initial capital
        self.cerebro.broker.setcash(initial_capital)
        
        # Set commission (0.1% per trade)
        self.cerebro.broker.setcommission(commission=0.001)
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='timereturn')
        
        # Store data and strategy references
        self.data_feeds = {}
        self.strategy_class = None
        self.strategy_params = {}
        
        logger.info(f"BacktraderEngine initialized with capital: ${initial_capital:,.2f}")
    
    def add_strategy(self, strategy_class: Any, **kwargs) -> None:
        """Add a trading strategy to the engine"""
        self.strategy_class = strategy_class
        self.strategy_params = kwargs
        
        # Add strategy to cerebro
        self.cerebro.addstrategy(strategy_class, **kwargs)
        
        logger.info(f"Added strategy: {strategy_class.__name__} with params: {kwargs}")
    
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
                # Assume index is already datetime-like
                data.index = pd.to_datetime(data.index)
        
        # Create backtrader data feed
        bt_data = bt.feeds.PandasData(
            dataname=data,
            datetime=None,  # Use index
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=None
        )
        
        # Add data to cerebro
        self.cerebro.adddata(bt_data, name=symbol)
        self.data_feeds[symbol] = data
        
        logger.info(f"Added data for {symbol}: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
    
    def run(self, **kwargs) -> BacktestResult:
        """Run the backtest and return results"""
        
        if not self.strategy_class:
            raise ValueError("No strategy added to engine")
        
        if not self.data_feeds:
            raise ValueError("No data added to engine")
        
        logger.info("Starting backtest...")
        
        # Run the backtest
        results = self.cerebro.run()
        
        if not results:
            raise RuntimeError("Backtest failed to produce results")
        
        # Get the first (and typically only) strategy result
        strategy_result = results[0]
        
        # Extract analyzer results
        analyzers = {}
        for analyzer_name in ['trades', 'sharpe', 'drawdown', 'returns', 'timereturn']:
            if hasattr(strategy_result, analyzer_name):
                analyzer = getattr(strategy_result, analyzer_name)
                analyzers[analyzer_name] = analyzer.get_analysis()
        
        # Get portfolio values
        portfolio_values = self.get_portfolio_values()
        
        # Get trade history
        trades = self.get_trades()
        
        # Calculate metrics
        metrics = self.calculate_metrics(portfolio_values, trades)
        
        # Create result object
        symbol = list(self.data_feeds.keys())[0] if self.data_feeds else "Unknown"
        data = list(self.data_feeds.values())[0] if self.data_feeds else pd.DataFrame()
        
        self.results = BacktestResult(
            total_return=metrics['total_return'],
            annual_return=metrics['annual_return'],
            sharpe_ratio=analyzers.get('sharpe', {}).get('sharperatio', metrics['sharpe_ratio']),
            max_drawdown=analyzers.get('drawdown', {}).get('max', {}).get('drawdown', metrics['max_drawdown']),
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
            strategy_name=self.strategy_class.__name__ if self.strategy_class else "Unknown",
            symbol=symbol,
            start_date=data.index[0] if not data.empty else None,
            end_date=data.index[-1] if not data.empty else None,
            engine="backtrader",
            portfolio_values=portfolio_values,
            trades=trades
        )
        
        logger.info(f"Backtest completed. Total return: {metrics['total_return']:.2%}, "
                   f"Sharpe ratio: {self.results.sharpe_ratio:.2f}, "
                   f"Max drawdown: {self.results.max_drawdown:.2%}")
        
        return self.results
    
    def get_portfolio_values(self) -> pd.Series:
        """Get portfolio value time series"""
        
        if not hasattr(self, 'cerebro') or not self.data_feeds:
            return pd.Series()
        
        # Get the time return analyzer results
        results = self.cerebro.run()
        if results and hasattr(results[0], 'timereturn'):
            timereturn_analysis = results[0].timereturn.get_analysis()
            
            # Convert to pandas Series
            dates = list(timereturn_analysis.keys())
            values = [self.initial_capital * (1 + ret) for ret in timereturn_analysis.values()]
            
            return pd.Series(values, index=dates)
        
        # Fallback: create simple portfolio value series
        data = list(self.data_feeds.values())[0]
        return pd.Series([self.initial_capital] * len(data), index=data.index)
    
    def get_trades(self) -> pd.DataFrame:
        """Get trade history"""
        
        if not hasattr(self, 'cerebro'):
            return pd.DataFrame()
        
        # Run cerebro to get results if not already run
        results = self.cerebro.run()
        
        if not results or not hasattr(results[0], 'trades'):
            return pd.DataFrame()
        
        trades_analysis = results[0].trades.get_analysis()
        
        # Extract trade information
        trades_data = []
        
        if 'total' in trades_analysis and 'closed' in trades_analysis['total']:
            total_trades = trades_analysis['total']['closed']
            
            # Create basic trade records
            for i in range(total_trades):
                trades_data.append({
                    'trade_id': i + 1,
                    'pnl': 0,  # Will be calculated from other metrics
                    'size': 0,
                    'entry_price': 0,
                    'exit_price': 0,
                    'entry_date': None,
                    'exit_date': None
                })
        
        return pd.DataFrame(trades_data)
    
    def plot(self, **kwargs):
        """Plot backtest results"""
        return self.cerebro.plot(**kwargs)
    
    def get_broker_value(self) -> float:
        """Get current broker portfolio value"""
        return self.cerebro.broker.getvalue()
    
    def get_cash(self) -> float:
        """Get current cash balance"""
        return self.cerebro.broker.getcash()