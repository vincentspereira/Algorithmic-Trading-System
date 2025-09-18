"""Performance Tracking Utilities for Trading Strategies

This module provides comprehensive performance tracking and analysis utilities
for trading strategies, including real-time metrics calculation and reporting.

Author: AI Assistant
Date: 2024-12-15
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from collections import defaultdict, deque

# Configure logging
logger = logging.getLogger(__name__)


class PerformancePeriod(Enum):
    """Performance calculation periods"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION = "inception"


@dataclass
class TradeMetrics:
    """Metrics for individual trades"""
    trade_id: str
    symbol: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    side: str = "long"  # "long" or "short"
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    commission: float = 0.0
    duration: Optional[timedelta] = None
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.exit_time and self.entry_time:
            self.duration = self.exit_time - self.entry_time


@dataclass
class PerformanceSnapshot:
    """Performance snapshot at a point in time"""
    timestamp: datetime
    total_pnl: float
    unrealized_pnl: float
    realized_pnl: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    portfolio_value: float


class PerformanceTracker:
    """Comprehensive performance tracking for trading strategies"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades: List[TradeMetrics] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.daily_returns: pd.Series = pd.Series(dtype=float)
        self.positions: Dict[str, Dict] = {}
        self.performance_history: List[PerformanceSnapshot] = []
        self.benchmark_returns: Optional[pd.Series] = None
        
        # Real-time tracking
        self.current_drawdown = 0.0
        self.max_drawdown = 0.0
        self.peak_value = initial_capital
        self.consecutive_wins = 0
        self.consecutive_losses = 0
        self.max_consecutive_wins = 0
        self.max_consecutive_losses = 0
        
        # Performance cache
        self._performance_cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration = timedelta(minutes=5)  # Cache for 5 minutes
    
    def add_trade(self, trade: TradeMetrics) -> None:
        """
        Add a completed trade to the performance tracker.
        
        Args:
            trade: TradeMetrics object representing the completed trade
        """
        try:
            self.trades.append(trade)
            
            # Update capital
            self.current_capital += trade.pnl - trade.commission
            
            # Update equity curve
            if trade.exit_time:
                self.equity_curve.append((trade.exit_time, self.current_capital))
            
            # Update consecutive wins/losses
            if trade.pnl > 0:
                self.consecutive_wins += 1
                self.consecutive_losses = 0
                self.max_consecutive_wins = max(self.max_consecutive_wins, self.consecutive_wins)
            elif trade.pnl < 0:
                self.consecutive_losses += 1
                self.consecutive_wins = 0
                self.max_consecutive_losses = max(self.max_consecutive_losses, self.consecutive_losses)
            
            # Update drawdown
            if self.current_capital > self.peak_value:
                self.peak_value = self.current_capital
                self.current_drawdown = 0.0
            else:
                self.current_drawdown = (self.peak_value - self.current_capital) / self.peak_value
                self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
            
            # Clear cache
            self._clear_cache()
            
            logger.debug(f"Added trade: {trade.trade_id}, P&L: {trade.pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}")
    
    def update_position(self, symbol: str, quantity: float, current_price: float) -> None:
        """
        Update current position for unrealized P&L calculation.
        
        Args:
            symbol: Trading symbol
            quantity: Current position quantity (positive for long, negative for short)
            current_price: Current market price
        """
        try:
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'quantity': 0,
                    'avg_price': 0,
                    'unrealized_pnl': 0
                }
            
            position = self.positions[symbol]
            
            # Update position
            if quantity == 0:
                # Position closed
                position['quantity'] = 0
                position['avg_price'] = 0
                position['unrealized_pnl'] = 0
            else:
                # Calculate unrealized P&L
                if position['quantity'] != 0:
                    if quantity > 0:  # Long position
                        position['unrealized_pnl'] = quantity * (current_price - position['avg_price'])
                    else:  # Short position
                        position['unrealized_pnl'] = abs(quantity) * (position['avg_price'] - current_price)
                
                position['quantity'] = quantity
            
            # Clear cache
            self._clear_cache()
            
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {e}")
    
    def calculate_metrics(self, period: PerformancePeriod = PerformancePeriod.INCEPTION) -> Dict[str, float]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            period: Time period for calculation
            
        Returns:
            Dictionary of performance metrics
        """
        try:
            # Check cache
            cache_key = f"metrics_{period.value}"
            if self._is_cache_valid() and cache_key in self._performance_cache:
                return self._performance_cache[cache_key]
            
            if not self.trades:
                return self._get_empty_metrics()
            
            # Filter trades by period
            filtered_trades = self._filter_trades_by_period(period)
            
            if not filtered_trades:
                return self._get_empty_metrics()
            
            # Basic metrics
            total_trades = len(filtered_trades)
            winning_trades = [t for t in filtered_trades if t.pnl > 0]
            losing_trades = [t for t in filtered_trades if t.pnl < 0]
            
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            
            # P&L metrics
            total_pnl = sum(t.pnl for t in filtered_trades)
            total_commission = sum(t.commission for t in filtered_trades)
            net_pnl = total_pnl - total_commission
            
            gross_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
            gross_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
            
            # Ratios and percentages
            win_rate = win_count / total_trades if total_trades > 0 else 0
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
            
            average_win = gross_profit / win_count if win_count > 0 else 0
            average_loss = gross_loss / loss_count if loss_count > 0 else 0
            
            largest_win = max((t.pnl for t in winning_trades), default=0)
            largest_loss = min((t.pnl for t in losing_trades), default=0)
            
            # Return metrics
            total_return = net_pnl / self.initial_capital
            
            # Risk metrics
            returns = pd.Series([t.pnl / self.initial_capital for t in filtered_trades])
            
            sharpe_ratio = 0
            if len(returns) > 1 and returns.std() > 0:
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)  # Annualized
            
            # Drawdown (use current max drawdown for inception period)
            max_dd = self.max_drawdown if period == PerformancePeriod.INCEPTION else self._calculate_period_drawdown(filtered_trades)
            
            # Unrealized P&L
            unrealized_pnl = sum(pos['unrealized_pnl'] for pos in self.positions.values())
            
            metrics = {
                'total_trades': total_trades,
                'winning_trades': win_count,
                'losing_trades': loss_count,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'net_pnl': net_pnl,
                'unrealized_pnl': unrealized_pnl,
                'total_return': total_return,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'profit_factor': profit_factor,
                'average_win': average_win,
                'average_loss': average_loss,
                'largest_win': largest_win,
                'largest_loss': largest_loss,
                'max_drawdown': max_dd,
                'sharpe_ratio': sharpe_ratio,
                'total_commission': total_commission,
                'current_capital': self.current_capital,
                'consecutive_wins': self.consecutive_wins,
                'consecutive_losses': self.consecutive_losses,
                'max_consecutive_wins': self.max_consecutive_wins,
                'max_consecutive_losses': self.max_consecutive_losses
            }
            
            # Cache results
            self._performance_cache[cache_key] = metrics
            self._cache_timestamp = datetime.now()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return self._get_empty_metrics()
    
    def get_equity_curve(self) -> pd.Series:
        """
        Get equity curve as a pandas Series.
        
        Returns:
            Series with timestamps as index and portfolio values
        """
        try:
            if not self.equity_curve:
                return pd.Series(dtype=float)
            
            timestamps, values = zip(*self.equity_curve)
            return pd.Series(values, index=timestamps)
            
        except Exception as e:
            logger.error(f"Error getting equity curve: {e}")
            return pd.Series(dtype=float)
    
    def get_monthly_returns(self) -> pd.Series:
        """
        Calculate monthly returns.
        
        Returns:
            Series of monthly returns
        """
        try:
            equity_curve = self.get_equity_curve()
            if equity_curve.empty:
                return pd.Series(dtype=float)
            
            # Resample to monthly and calculate returns
            monthly_equity = equity_curve.resample('M').last()
            monthly_returns = monthly_equity.pct_change().dropna()
            
            return monthly_returns
            
        except Exception as e:
            logger.error(f"Error calculating monthly returns: {e}")
            return pd.Series(dtype=float)
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report.
        
        Returns:
            Dictionary containing detailed performance analysis
        """
        try:
            report = {
                'summary': self.calculate_metrics(),
                'trade_analysis': self._analyze_trades(),
                'risk_analysis': self._analyze_risk(),
                'time_analysis': self._analyze_time_performance(),
                'symbol_analysis': self._analyze_symbol_performance()
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating performance report: {e}")
            return {}
    
    def set_benchmark(self, benchmark_returns: pd.Series) -> None:
        """
        Set benchmark returns for comparison.
        
        Args:
            benchmark_returns: Series of benchmark returns
        """
        self.benchmark_returns = benchmark_returns
        self._clear_cache()
    
    def calculate_alpha_beta(self) -> Tuple[float, float]:
        """
        Calculate alpha and beta relative to benchmark.
        
        Returns:
            Tuple of (alpha, beta)
        """
        try:
            if self.benchmark_returns is None or len(self.trades) < 2:
                return 0.0, 0.0
            
            # Get strategy returns
            strategy_returns = pd.Series([t.pnl / self.initial_capital for t in self.trades])
            
            # Align with benchmark
            aligned_data = pd.concat([strategy_returns, self.benchmark_returns], axis=1).dropna()
            
            if len(aligned_data) < 2:
                return 0.0, 0.0
            
            strategy_ret = aligned_data.iloc[:, 0]
            benchmark_ret = aligned_data.iloc[:, 1]
            
            # Calculate beta
            covariance = np.cov(strategy_ret, benchmark_ret)[0, 1]
            benchmark_variance = np.var(benchmark_ret)
            
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
            
            # Calculate alpha
            strategy_mean = strategy_ret.mean()
            benchmark_mean = benchmark_ret.mean()
            alpha = strategy_mean - beta * benchmark_mean
            
            return alpha, beta
            
        except Exception as e:
            logger.error(f"Error calculating alpha/beta: {e}")
            return 0.0, 0.0
    
    def _filter_trades_by_period(self, period: PerformancePeriod) -> List[TradeMetrics]:
        """Filter trades by time period"""
        if period == PerformancePeriod.INCEPTION:
            return self.trades
        
        now = datetime.now()
        
        if period == PerformancePeriod.DAILY:
            cutoff = now - timedelta(days=1)
        elif period == PerformancePeriod.WEEKLY:
            cutoff = now - timedelta(weeks=1)
        elif period == PerformancePeriod.MONTHLY:
            cutoff = now - timedelta(days=30)
        elif period == PerformancePeriod.QUARTERLY:
            cutoff = now - timedelta(days=90)
        elif period == PerformancePeriod.YEARLY:
            cutoff = now - timedelta(days=365)
        else:
            return self.trades
        
        return [t for t in self.trades if t.exit_time and t.exit_time >= cutoff]
    
    def _calculate_period_drawdown(self, trades: List[TradeMetrics]) -> float:
        """Calculate maximum drawdown for a specific period"""
        if not trades:
            return 0.0
        
        # Build equity curve for the period
        capital = self.initial_capital
        peak = capital
        max_dd = 0.0
        
        for trade in sorted(trades, key=lambda t: t.exit_time or datetime.min):
            capital += trade.pnl - trade.commission
            
            if capital > peak:
                peak = capital
            else:
                drawdown = (peak - capital) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _analyze_trades(self) -> Dict[str, Any]:
        """Analyze trade patterns and characteristics"""
        if not self.trades:
            return {}
        
        # Trade duration analysis
        durations = [t.duration.total_seconds() / 3600 for t in self.trades if t.duration]  # Hours
        
        # P&L distribution
        pnls = [t.pnl for t in self.trades]
        
        return {
            'average_duration_hours': np.mean(durations) if durations else 0,
            'median_duration_hours': np.median(durations) if durations else 0,
            'pnl_std': np.std(pnls),
            'pnl_skewness': pd.Series(pnls).skew(),
            'pnl_kurtosis': pd.Series(pnls).kurtosis(),
            'trade_frequency_per_day': len(self.trades) / max(1, (datetime.now() - self.trades[0].entry_time).days)
        }
    
    def _analyze_risk(self) -> Dict[str, Any]:
        """Analyze risk metrics"""
        if not self.trades:
            return {}
        
        returns = pd.Series([t.pnl / self.initial_capital for t in self.trades])
        
        return {
            'var_95': np.percentile(returns, 5),
            'var_99': np.percentile(returns, 1),
            'expected_shortfall': returns[returns <= np.percentile(returns, 5)].mean(),
            'volatility': returns.std(),
            'downside_deviation': returns[returns < 0].std()
        }
    
    def _analyze_time_performance(self) -> Dict[str, Any]:
        """Analyze performance by time periods"""
        if not self.trades:
            return {}
        
        # Group trades by hour, day of week, month
        trades_df = pd.DataFrame([
            {
                'hour': t.entry_time.hour,
                'day_of_week': t.entry_time.weekday(),
                'month': t.entry_time.month,
                'pnl': t.pnl
            }
            for t in self.trades if t.entry_time
        ])
        
        if trades_df.empty:
            return {}
        
        return {
            'best_hour': trades_df.groupby('hour')['pnl'].mean().idxmax(),
            'best_day_of_week': trades_df.groupby('day_of_week')['pnl'].mean().idxmax(),
            'best_month': trades_df.groupby('month')['pnl'].mean().idxmax(),
            'hourly_performance': trades_df.groupby('hour')['pnl'].mean().to_dict(),
            'daily_performance': trades_df.groupby('day_of_week')['pnl'].mean().to_dict(),
            'monthly_performance': trades_df.groupby('month')['pnl'].mean().to_dict()
        }
    
    def _analyze_symbol_performance(self) -> Dict[str, Any]:
        """Analyze performance by trading symbol"""
        if not self.trades:
            return {}
        
        symbol_stats = defaultdict(lambda: {'trades': 0, 'pnl': 0, 'wins': 0})
        
        for trade in self.trades:
            stats = symbol_stats[trade.symbol]
            stats['trades'] += 1
            stats['pnl'] += trade.pnl
            if trade.pnl > 0:
                stats['wins'] += 1
        
        # Convert to regular dict and add win rates
        result = {}
        for symbol, stats in symbol_stats.items():
            result[symbol] = {
                'total_trades': stats['trades'],
                'total_pnl': stats['pnl'],
                'win_rate': stats['wins'] / stats['trades'] if stats['trades'] > 0 else 0,
                'avg_pnl_per_trade': stats['pnl'] / stats['trades'] if stats['trades'] > 0 else 0
            }
        
        return result
    
    def _get_empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics dictionary"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'net_pnl': 0,
            'unrealized_pnl': 0,
            'total_return': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'profit_factor': 0,
            'average_win': 0,
            'average_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'total_commission': 0,
            'current_capital': self.current_capital,
            'consecutive_wins': 0,
            'consecutive_losses': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0
        }
    
    def _is_cache_valid(self) -> bool:
        """Check if performance cache is still valid"""
        if self._cache_timestamp is None:
            return False
        return datetime.now() - self._cache_timestamp < self._cache_duration
    
    def _clear_cache(self) -> None:
        """Clear performance cache"""
        self._performance_cache.clear()
        self._cache_timestamp = None


# Export main classes
__all__ = [
    'PerformanceTracker',
    'TradeMetrics',
    'PerformanceSnapshot',
    'PerformancePeriod'
]