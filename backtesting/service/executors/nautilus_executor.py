
#!/usr/bin/env python3
"""
Nautilus Executor for Backtesting
Provides backtesting execution capabilities using NautilusTrader.
"""

import asyncio
import pandas as pd
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from unittest.mock import Mock, AsyncMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BacktestExecutor:
    """Executor for running backtests with NautilusTrader integration."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.data_cache = {}
        self.results = {}
        self.strategies = {}
        self.portfolio = {
            "cash": Decimal('100000.00'),
            "positions": {},
            "orders": [],
            "trades": []
        }
        self.is_running = False

    def run_backtest(self, config: dict, data: pd.DataFrame) -> dict:
        """
        Run backtest with given configuration and data.
        """
        logger.info(f"Starting backtest for symbol: {config.get('symbol', 'UNKNOWN')}")
        
        try:
            # Prepare data
            prepared_data = self.prepare_data(data)
            
            # Initialize strategy
            strategy = self._initialize_strategy(config)
            
            # Run simulation
            results = self._run_simulation(strategy, prepared_data)
            
            logger.info(f"Backtest completed for {config.get('symbol', 'UNKNOWN')}")
            return results

        except Exception as e:
            logger.error(f"Backtest error for symbol {config.get('symbol', 'UNKNOWN')}: {str(e)}")
            return {'error': str(e)}

    def prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare data for backtesting.
        """
        logger.info("Preparing data for backtest...")
        
        # Ensure required columns exist
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Required column '{col}' not found in data")
        
        # Convert timestamp to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
            data['timestamp'] = pd.to_datetime(data['timestamp'])
        
        # Sort by timestamp
        data = data.sort_values('timestamp').reset_index(drop=True)
        
        logger.info("Data preparation complete.")
        return data

    def _initialize_strategy(self, config: dict) -> dict:
        """
        Initialize strategy configuration.
        """
        return {
            'symbol': config.get('symbol', 'UNKNOWN'),
            'fast_ma': config.get('fast_ma', 10),
            'slow_ma': config.get('slow_ma', 20),
            'trade_size': Decimal(str(config.get('trade_size', 100)))
        }

    def _run_simulation(self, strategy: Dict[str, Any], data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run trading simulation.
        """
        logger.info("Running trading simulation...")
        
        trades = []
        portfolio_value = []
        current_cash = self.portfolio['cash']
        positions = {}
        
        # Calculate moving averages
        data['fast_ma'] = data['close'].rolling(window=strategy['fast_ma']).mean()
        data['slow_ma'] = data['close'].rolling(window=strategy['slow_ma']).mean()
        
        for index, row in data.iterrows():
            # Skip if we don't have enough data for moving averages
            if pd.isna(row['fast_ma']) or pd.isna(row['slow_ma']):
                continue
                
            # Generate signals
            signals = self._generate_signals(row, strategy)
            
            # Execute trades
            for signal in signals:
                trade = self._execute_trade_sync(signal, row, current_cash, positions)
                if trade:
                    trades.append(trade)
                    current_cash = trade['remaining_cash']
                    positions = trade['positions']
                    
            # Calculate portfolio value
            portfolio_val = self._calculate_portfolio_value(current_cash, positions, row['close'])
            portfolio_value.append({
                'timestamp': row['timestamp'],
                'value': portfolio_val
            })
                
        return {
            'trades': trades,
            'portfolio_value': portfolio_value,
            'final_portfolio_value': portfolio_value[-1]['value'] if portfolio_value else float(current_cash),
            'final_cash': float(current_cash),
            'final_positions': positions,
            'performance': self._calculate_performance({'portfolio_value': portfolio_value, 'trades': trades})
        }

    def _generate_signals(self, row: pd.Series, strategy: dict) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on moving average crossover.
        """
        signals = []
        
        # Simple MA crossover strategy
        if row['fast_ma'] > row['slow_ma']:
            # Buy signal
            signals.append({
                'type': 'buy',
                'symbol': strategy['symbol'],
                'quantity': strategy['trade_size'],
                'price': row['close'],
                'timestamp': row['timestamp'],
                'reason': 'MA crossover buy signal'
            })
        
        return signals

    def _execute_trade_sync(self, signal: Dict[str, Any], row: pd.Series, cash: Decimal, positions: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Synchronous version of trade execution.
        """
        symbol = signal['symbol']
        quantity = signal['quantity']
        price = Decimal(str(signal['price']))
        trade_value = quantity * price
        
        if signal['type'] == 'buy' and cash >= trade_value:
            new_cash = cash - trade_value
            new_positions = positions.copy()
            new_positions[symbol] = new_positions.get(symbol, 0) + quantity
            
            return {
                'type': 'buy',
                'symbol': symbol,
                'quantity': quantity,
                'price': float(price),
                'value': float(trade_value),
                'timestamp': signal['timestamp'],
                'remaining_cash': new_cash,
                'positions': new_positions,
                'reason': signal['reason']
            }
                
        return None

    def _calculate_portfolio_value(self, cash: Decimal, positions: Dict[str, Any], current_price: float) -> float:
        """
        Calculate total portfolio value.
        """
        total_value = float(cash)
        
        for symbol, quantity in positions.items():
            total_value += quantity * current_price
            
        return total_value

    def _calculate_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate performance metrics.
        """
        portfolio_values = [pv['value'] for pv in results['portfolio_value']]
        
        if len(portfolio_values) < 2:
            return {'total_return': 0.0, 'max_drawdown': 0.0, 'sharpe_ratio': 0.0}
        
        initial_value = portfolio_values[0]
        final_value = portfolio_values[-1]
        total_return = (final_value - initial_value) / initial_value
        
        # Calculate max drawdown
        peak = portfolio_values[0]
        max_drawdown = 0.0
        
        for value in portfolio_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        return {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': 0.0,  # Simplified for now
            'win_rate': len([t for t in results['trades'] if 'pnl' in t and t['pnl'] > 0]) / max(len(results['trades']), 1)
        }

    def get_results(self, result_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get backtest results.
        """
        if result_id:
            return self.results.get(result_id, {})
        return self.results
        
    def cleanup(self):
        """
        Cleanup resources.
        """
        self.data_cache.clear()
        self.results.clear()
        self.strategies.clear()
        logger.info("BacktestExecutor cleanup completed")
