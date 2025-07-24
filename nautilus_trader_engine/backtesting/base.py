"""
Base classes for backtesting engines

This module defines the abstract base classes and data structures
used by all backtesting engines in the system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd


@dataclass
class BacktestResult:
    """Standardized backtest result structure"""
    
    # Performance metrics
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Portfolio metrics
    initial_capital: float
    final_capital: float
    peak_capital: float
    
    # Additional metrics
    calmar_ratio: float
    sortino_ratio: float
    beta: Optional[float] = None
    alpha: Optional[float] = None
    
    # Metadata
    strategy_name: str = ""
    symbol: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    engine: str = ""
    
    # Raw data
    portfolio_values: Optional[pd.Series] = None
    trades: Optional[pd.DataFrame] = None
    positions: Optional[pd.DataFrame] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization"""
        return {
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'initial_capital': self.initial_capital,
            'final_capital': self.final_capital,
            'peak_capital': self.peak_capital,
            'calmar_ratio': self.calmar_ratio,
            'sortino_ratio': self.sortino_ratio,
            'beta': self.beta,
            'alpha': self.alpha,
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'engine': self.engine
        }


class BacktestEngine(ABC):
    """Abstract base class for backtesting engines"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.results: Optional[BacktestResult] = None
    
    @abstractmethod
    def add_strategy(self, strategy: Any, **kwargs) -> None:
        """Add a trading strategy to the engine"""
        pass
    
    @abstractmethod
    def add_data(self, data: pd.DataFrame, symbol: str) -> None:
        """Add market data to the engine"""
        pass
    
    @abstractmethod
    def run(self, **kwargs) -> BacktestResult:
        """Run the backtest and return results"""
        pass
    
    @abstractmethod
    def get_portfolio_values(self) -> pd.Series:
        """Get portfolio value time series"""
        pass
    
    @abstractmethod
    def get_trades(self) -> pd.DataFrame:
        """Get trade history"""
        pass
    
    def calculate_metrics(self, portfolio_values: pd.Series, 
                         trades: pd.DataFrame) -> Dict[str, float]:
        """Calculate standard performance metrics"""
        
        if portfolio_values.empty:
            return self._empty_metrics()
        
        # Calculate returns
        returns = portfolio_values.pct_change().dropna()
        
        if returns.empty or len(returns) < 2:
            return self._empty_metrics()
        
        # Basic metrics
        total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        volatility = returns.std() * (252 ** 0.5)
        
        # Sharpe ratio
        risk_free_rate = 0.02  # Assume 2% risk-free rate
        excess_returns = returns - (risk_free_rate / 252)
        sharpe_ratio = excess_returns.mean() / returns.std() * (252 ** 0.5) if returns.std() > 0 else 0
        
        # Max drawdown
        peak = portfolio_values.expanding().max()
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = drawdown.min()
        
        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * (252 ** 0.5) if len(downside_returns) > 0 else 0
        sortino_ratio = excess_returns.mean() / downside_std * (252 ** 0.5) if downside_std > 0 else 0
        
        # Calmar ratio
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Trade statistics
        if not trades.empty:
            total_trades = len(trades)
            winning_trades = len(trades[trades['pnl'] > 0]) if 'pnl' in trades.columns else 0
            losing_trades = len(trades[trades['pnl'] < 0]) if 'pnl' in trades.columns else 0
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            if 'pnl' in trades.columns:
                wins = trades[trades['pnl'] > 0]['pnl']
                losses = trades[trades['pnl'] < 0]['pnl']
                avg_win = wins.mean() if len(wins) > 0 else 0
                avg_loss = losses.mean() if len(losses) > 0 else 0
                profit_factor = abs(wins.sum() / losses.sum()) if losses.sum() != 0 else 0
            else:
                avg_win = avg_loss = profit_factor = 0
        else:
            total_trades = winning_trades = losing_trades = 0
            win_rate = avg_win = avg_loss = profit_factor = 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio,
            'initial_capital': self.initial_capital,
            'final_capital': portfolio_values.iloc[-1] if not portfolio_values.empty else self.initial_capital,
            'peak_capital': portfolio_values.max() if not portfolio_values.empty else self.initial_capital
        }
    
    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics when calculation fails"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'calmar_ratio': 0.0,
            'sortino_ratio': 0.0,
            'initial_capital': self.initial_capital,
            'final_capital': self.initial_capital,
            'peak_capital': self.initial_capital
        }