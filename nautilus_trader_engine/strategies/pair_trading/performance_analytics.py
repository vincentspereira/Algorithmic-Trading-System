#!/usr/bin/env python3
"""
Pairs Trading Performance Analytics

Comprehensive performance analysis and reporting system for pairs trading strategies.
Provides detailed metrics, attribution analysis, and performance visualization capabilities.

Key Features:
- Trade-level performance analysis
- Portfolio-level performance metrics
- Risk-adjusted return calculations
- Performance attribution by strategy/pair/time period
- Benchmark comparison and relative performance
- Rolling performance analysis
- Drawdown analysis and recovery metrics
- Performance persistence and consistency metrics
- Monte Carlo performance simulation
- Performance reporting and visualization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PerformancePeriod(Enum):
    """Performance analysis periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    INCEPTION = "inception"


class AttributionType(Enum):
    """Performance attribution types."""
    STRATEGY = "strategy"
    PAIR = "pair"
    SECTOR = "sector"
    TIME_PERIOD = "time_period"
    MARKET_REGIME = "market_regime"


@dataclass
class TradeResult:
    """Individual trade result."""
    trade_id: str
    pair_id: str
    symbol1: str
    symbol2: str
    strategy_type: str
    entry_time: datetime
    exit_time: datetime
    entry_price_1: float
    entry_price_2: float
    exit_price_1: float
    exit_price_2: float
    quantity_1: float
    quantity_2: float
    hedge_ratio: float
    pnl: float
    pnl_pct: float
    duration_hours: float
    max_favorable_excursion: float
    max_adverse_excursion: float
    commission: float = 0.0
    slippage: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    # Return metrics
    total_return: float
    annualized_return: float
    cumulative_return: float
    
    # Risk metrics
    volatility: float
    max_drawdown: float
    calmar_ratio: float
    
    # Risk-adjusted returns
    sharpe_ratio: float
    sortino_ratio: float
    information_ratio: float
    
    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    
    # Advanced metrics
    skewness: float
    kurtosis: float
    var_95: float
    expected_shortfall: float
    
    # Consistency metrics
    hit_ratio: float
    up_capture: float
    down_capture: float
    
    # Time-based metrics
    avg_trade_duration: float
    trades_per_year: float
    
    # Attribution
    alpha: float
    beta: float
    tracking_error: float
    
    # Period information
    start_date: datetime
    end_date: datetime
    period_days: int
    
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AttributionResult:
    """Performance attribution result."""
    attribution_type: AttributionType
    category: str
    contribution: float
    weight: float
    return_contribution: float
    risk_contribution: float
    information_ratio: float
    trades_count: int
    metadata: Dict = field(default_factory=dict)


class PerformanceCalculator:
    """Core performance calculation engine."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate
    
    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate return series from price series.
        
        Args:
            prices: Price series
            
        Returns:
            Return series
        """
        try:
            if len(prices) < 2:
                return pd.Series(dtype=float)
            
            returns = prices.pct_change().dropna()
            return returns
        
        except Exception as e:
            logger.warning(f"Error calculating returns: {e}")
            return pd.Series(dtype=float)
    
    def calculate_cumulative_returns(self, returns: pd.Series) -> pd.Series:
        """Calculate cumulative returns.
        
        Args:
            returns: Return series
            
        Returns:
            Cumulative return series
        """
        try:
            if len(returns) == 0:
                return pd.Series(dtype=float)
            
            cumulative = (1 + returns).cumprod() - 1
            return cumulative
        
        except Exception as e:
            logger.warning(f"Error calculating cumulative returns: {e}")
            return pd.Series(dtype=float)
    
    def calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: Optional[float] = None) -> float:
        """Calculate Sharpe ratio.
        
        Args:
            returns: Return series
            risk_free_rate: Risk-free rate (annualized)
            
        Returns:
            Sharpe ratio
        """
        try:
            if len(returns) < 2:
                return 0.0
            
            rf_rate = risk_free_rate or self.risk_free_rate
            excess_returns = returns - rf_rate / 252  # Daily risk-free rate
            
            if excess_returns.std() == 0:
                return 0.0
            
            sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
            return sharpe
        
        except Exception as e:
            logger.warning(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def calculate_sortino_ratio(self, returns: pd.Series, risk_free_rate: Optional[float] = None) -> float:
        """Calculate Sortino ratio.
        
        Args:
            returns: Return series
            risk_free_rate: Risk-free rate (annualized)
            
        Returns:
            Sortino ratio
        """
        try:
            if len(returns) < 2:
                return 0.0
            
            rf_rate = risk_free_rate or self.risk_free_rate
            excess_returns = returns - rf_rate / 252
            
            # Downside deviation (only negative returns)
            downside_returns = excess_returns[excess_returns < 0]
            if len(downside_returns) == 0:
                return float('inf') if excess_returns.mean() > 0 else 0.0
            
            downside_deviation = downside_returns.std()
            if downside_deviation == 0:
                return 0.0
            
            sortino = excess_returns.mean() / downside_deviation * np.sqrt(252)
            return sortino
        
        except Exception as e:
            logger.warning(f"Error calculating Sortino ratio: {e}")
            return 0.0
    
    def calculate_calmar_ratio(self, returns: pd.Series) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown).
        
        Args:
            returns: Return series
            
        Returns:
            Calmar ratio
        """
        try:
            if len(returns) < 2:
                return 0.0
            
            annualized_return = returns.mean() * 252
            max_dd = self.calculate_max_drawdown(returns)
            
            if max_dd == 0:
                return float('inf') if annualized_return > 0 else 0.0
            
            calmar = annualized_return / abs(max_dd)
            return calmar
        
        except Exception as e:
            logger.warning(f"Error calculating Calmar ratio: {e}")
            return 0.0
    
    def calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown.
        
        Args:
            returns: Return series
            
        Returns:
            Maximum drawdown (negative value)
        """
        try:
            if len(returns) < 2:
                return 0.0
            
            cumulative = self.calculate_cumulative_returns(returns)
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / (1 + running_max)
            
            max_drawdown = drawdown.min()
            return max_drawdown
        
        except Exception as e:
            logger.warning(f"Error calculating max drawdown: {e}")
            return 0.0
    
    def calculate_var(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk.
        
        Args:
            returns: Return series
            confidence_level: Confidence level
            
        Returns:
            VaR value
        """
        try:
            if len(returns) < 10:
                return 0.0
            
            var = -np.percentile(returns, (1 - confidence_level) * 100)
            return var
        
        except Exception as e:
            logger.warning(f"Error calculating VaR: {e}")
            return 0.0
    
    def calculate_expected_shortfall(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """Calculate Expected Shortfall (Conditional VaR).
        
        Args:
            returns: Return series
            confidence_level: Confidence level
            
        Returns:
            Expected Shortfall value
        """
        try:
            if len(returns) < 10:
                return 0.0
            
            var_threshold = -np.percentile(returns, (1 - confidence_level) * 100)
            tail_returns = returns[returns <= -var_threshold]
            
            if len(tail_returns) > 0:
                es = -tail_returns.mean()
            else:
                es = var_threshold
            
            return es
        
        except Exception as e:
            logger.warning(f"Error calculating Expected Shortfall: {e}")
            return 0.0
    
    def calculate_information_ratio(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate Information Ratio.
        
        Args:
            returns: Strategy return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Information ratio
        """
        try:
            if len(returns) < 2 or len(benchmark_returns) < 2:
                return 0.0
            
            # Align series
            aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
            if len(aligned) < 2:
                return 0.0
            
            strategy_ret = aligned.iloc[:, 0]
            benchmark_ret = aligned.iloc[:, 1]
            
            excess_returns = strategy_ret - benchmark_ret
            tracking_error = excess_returns.std()
            
            if tracking_error == 0:
                return 0.0
            
            info_ratio = excess_returns.mean() / tracking_error * np.sqrt(252)
            return info_ratio
        
        except Exception as e:
            logger.warning(f"Error calculating Information Ratio: {e}")
            return 0.0
    
    def calculate_beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate beta relative to benchmark.
        
        Args:
            returns: Strategy return series
            benchmark_returns: Benchmark return series
            
        Returns:
            Beta value
        """
        try:
            if len(returns) < 10 or len(benchmark_returns) < 10:
                return 0.0
            
            # Align series
            aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
            if len(aligned) < 10:
                return 0.0
            
            strategy_ret = aligned.iloc[:, 0]
            benchmark_ret = aligned.iloc[:, 1]
            
            if benchmark_ret.var() == 0:
                return 0.0
            
            beta = strategy_ret.cov(benchmark_ret) / benchmark_ret.var()
            return beta
        
        except Exception as e:
            logger.warning(f"Error calculating beta: {e}")
            return 0.0
    
    def calculate_alpha(self, returns: pd.Series, benchmark_returns: pd.Series, 
                      risk_free_rate: Optional[float] = None) -> float:
        """Calculate alpha (Jensen's alpha).
        
        Args:
            returns: Strategy return series
            benchmark_returns: Benchmark return series
            risk_free_rate: Risk-free rate
            
        Returns:
            Alpha value (annualized)
        """
        try:
            if len(returns) < 10 or len(benchmark_returns) < 10:
                return 0.0
            
            rf_rate = risk_free_rate or self.risk_free_rate
            beta = self.calculate_beta(returns, benchmark_returns)
            
            # Align series
            aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
            if len(aligned) < 10:
                return 0.0
            
            strategy_ret = aligned.iloc[:, 0]
            benchmark_ret = aligned.iloc[:, 1]
            
            # Calculate alpha using CAPM
            strategy_excess = strategy_ret.mean() * 252 - rf_rate
            benchmark_excess = benchmark_ret.mean() * 252 - rf_rate
            
            alpha = strategy_excess - beta * benchmark_excess
            return alpha
        
        except Exception as e:
            logger.warning(f"Error calculating alpha: {e}")
            return 0.0


class TradeAnalyzer:
    """Analyze individual trade performance."""
    
    def __init__(self):
        self.trades: List[TradeResult] = []
    
    def add_trade(self, trade: TradeResult) -> None:
        """Add a completed trade for analysis.
        
        Args:
            trade: TradeResult object
        """
        self.trades.append(trade)
    
    def calculate_trade_statistics(self) -> Dict[str, float]:
        """Calculate comprehensive trade statistics.
        
        Returns:
            Dictionary of trade statistics
        """
        try:
            if not self.trades:
                return {}
            
            # Basic statistics
            total_trades = len(self.trades)
            winning_trades = sum(1 for trade in self.trades if trade.pnl > 0)
            losing_trades = sum(1 for trade in self.trades if trade.pnl < 0)
            breakeven_trades = total_trades - winning_trades - losing_trades
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # P&L statistics
            total_pnl = sum(trade.pnl for trade in self.trades)
            winning_pnl = sum(trade.pnl for trade in self.trades if trade.pnl > 0)
            losing_pnl = sum(trade.pnl for trade in self.trades if trade.pnl < 0)
            
            avg_win = winning_pnl / winning_trades if winning_trades > 0 else 0.0
            avg_loss = losing_pnl / losing_trades if losing_trades > 0 else 0.0
            
            profit_factor = abs(winning_pnl / losing_pnl) if losing_pnl != 0 else float('inf')
            
            # Duration statistics
            durations = [trade.duration_hours for trade in self.trades]
            avg_duration = np.mean(durations) if durations else 0.0
            
            # Excursion statistics
            mfe_values = [trade.max_favorable_excursion for trade in self.trades]
            mae_values = [trade.max_adverse_excursion for trade in self.trades]
            
            avg_mfe = np.mean(mfe_values) if mfe_values else 0.0
            avg_mae = np.mean(mae_values) if mae_values else 0.0
            
            # Return statistics
            returns = [trade.pnl_pct for trade in self.trades]
            avg_return = np.mean(returns) if returns else 0.0
            return_std = np.std(returns) if len(returns) > 1 else 0.0
            
            # Consecutive statistics
            consecutive_wins, consecutive_losses = self._calculate_consecutive_stats()
            
            statistics = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'breakeven_trades': breakeven_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'avg_duration_hours': avg_duration,
                'avg_mfe': avg_mfe,
                'avg_mae': avg_mae,
                'avg_return_pct': avg_return,
                'return_std': return_std,
                'max_consecutive_wins': consecutive_wins,
                'max_consecutive_losses': consecutive_losses,
                'largest_win': max(returns) if returns else 0.0,
                'largest_loss': min(returns) if returns else 0.0
            }
            
            return statistics
        
        except Exception as e:
            logger.warning(f"Error calculating trade statistics: {e}")
            return {}
    
    def _calculate_consecutive_stats(self) -> Tuple[int, int]:
        """Calculate maximum consecutive wins and losses.
        
        Returns:
            Tuple of (max_consecutive_wins, max_consecutive_losses)
        """
        try:
            if not self.trades:
                return 0, 0
            
            max_wins = 0
            max_losses = 0
            current_wins = 0
            current_losses = 0
            
            for trade in self.trades:
                if trade.pnl > 0:
                    current_wins += 1
                    current_losses = 0
                    max_wins = max(max_wins, current_wins)
                elif trade.pnl < 0:
                    current_losses += 1
                    current_wins = 0
                    max_losses = max(max_losses, current_losses)
                else:
                    current_wins = 0
                    current_losses = 0
            
            return max_wins, max_losses
        
        except Exception as e:
            logger.warning(f"Error calculating consecutive stats: {e}")
            return 0, 0
    
    def analyze_by_strategy(self) -> Dict[str, Dict[str, float]]:
        """Analyze performance by strategy type.
        
        Returns:
            Dictionary of statistics by strategy
        """
        try:
            strategy_trades = defaultdict(list)
            
            for trade in self.trades:
                strategy_trades[trade.strategy_type].append(trade)
            
            strategy_stats = {}
            for strategy, trades in strategy_trades.items():
                # Temporarily set trades for analysis
                original_trades = self.trades
                self.trades = trades
                stats = self.calculate_trade_statistics()
                self.trades = original_trades
                
                strategy_stats[strategy] = stats
            
            return strategy_stats
        
        except Exception as e:
            logger.warning(f"Error analyzing by strategy: {e}")
            return {}
    
    def analyze_by_pair(self) -> Dict[str, Dict[str, float]]:
        """Analyze performance by trading pair.
        
        Returns:
            Dictionary of statistics by pair
        """
        try:
            pair_trades = defaultdict(list)
            
            for trade in self.trades:
                pair_trades[trade.pair_id].append(trade)
            
            pair_stats = {}
            for pair_id, trades in pair_trades.items():
                # Temporarily set trades for analysis
                original_trades = self.trades
                self.trades = trades
                stats = self.calculate_trade_statistics()
                self.trades = original_trades
                
                pair_stats[pair_id] = stats
            
            return pair_stats
        
        except Exception as e:
            logger.warning(f"Error analyzing by pair: {e}")
            return {}


class PerformanceAnalyzer:
    """Main performance analysis engine."""
    
    def __init__(self, risk_free_rate: float = 0.02):
        self.calculator = PerformanceCalculator(risk_free_rate)
        self.trade_analyzer = TradeAnalyzer()
        self.performance_history: List[PerformanceMetrics] = []
    
    def calculate_performance_metrics(self,
                                    returns: pd.Series,
                                    benchmark_returns: Optional[pd.Series] = None,
                                    trades: Optional[List[TradeResult]] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics.
        
        Args:
            returns: Strategy return series
            benchmark_returns: Optional benchmark return series
            trades: Optional list of trades for trade-level analysis
            
        Returns:
            PerformanceMetrics object
        """
        try:
            if len(returns) < 2:
                return self._empty_metrics()
            
            # Basic return metrics
            total_return = (1 + returns).prod() - 1
            annualized_return = returns.mean() * 252
            cumulative_returns = self.calculator.calculate_cumulative_returns(returns)
            cumulative_return = cumulative_returns.iloc[-1] if len(cumulative_returns) > 0 else 0.0
            
            # Risk metrics
            volatility = returns.std() * np.sqrt(252)
            max_drawdown = self.calculator.calculate_max_drawdown(returns)
            
            # Risk-adjusted returns
            sharpe_ratio = self.calculator.calculate_sharpe_ratio(returns)
            sortino_ratio = self.calculator.calculate_sortino_ratio(returns)
            calmar_ratio = self.calculator.calculate_calmar_ratio(returns)
            
            # Advanced risk metrics
            var_95 = self.calculator.calculate_var(returns, 0.95)
            expected_shortfall = self.calculator.calculate_expected_shortfall(returns, 0.95)
            skewness = returns.skew() if len(returns) > 2 else 0.0
            kurtosis = returns.kurtosis() if len(returns) > 3 else 0.0
            
            # Benchmark-relative metrics
            information_ratio = 0.0
            alpha = 0.0
            beta = 0.0
            tracking_error = 0.0
            up_capture = 0.0
            down_capture = 0.0
            
            if benchmark_returns is not None and len(benchmark_returns) > 0:
                information_ratio = self.calculator.calculate_information_ratio(returns, benchmark_returns)
                alpha = self.calculator.calculate_alpha(returns, benchmark_returns)
                beta = self.calculator.calculate_beta(returns, benchmark_returns)
                
                # Calculate tracking error
                aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
                if len(aligned) > 1:
                    excess_returns = aligned.iloc[:, 0] - aligned.iloc[:, 1]
                    tracking_error = excess_returns.std() * np.sqrt(252)
                    
                    # Calculate up/down capture ratios
                    up_periods = aligned[aligned.iloc[:, 1] > 0]
                    down_periods = aligned[aligned.iloc[:, 1] < 0]
                    
                    if len(up_periods) > 0:
                        up_capture = up_periods.iloc[:, 0].mean() / up_periods.iloc[:, 1].mean()
                    if len(down_periods) > 0:
                        down_capture = down_periods.iloc[:, 0].mean() / down_periods.iloc[:, 1].mean()
            
            # Trade-level metrics
            total_trades = 0
            winning_trades = 0
            losing_trades = 0
            win_rate = 0.0
            avg_win = 0.0
            avg_loss = 0.0
            profit_factor = 0.0
            avg_trade_duration = 0.0
            trades_per_year = 0.0
            hit_ratio = 0.0
            
            if trades:
                # Temporarily set trades for analysis
                original_trades = self.trade_analyzer.trades
                self.trade_analyzer.trades = trades
                trade_stats = self.trade_analyzer.calculate_trade_statistics()
                self.trade_analyzer.trades = original_trades
                
                total_trades = trade_stats.get('total_trades', 0)
                winning_trades = trade_stats.get('winning_trades', 0)
                losing_trades = trade_stats.get('losing_trades', 0)
                win_rate = trade_stats.get('win_rate', 0.0)
                avg_win = trade_stats.get('avg_win', 0.0)
                avg_loss = trade_stats.get('avg_loss', 0.0)
                profit_factor = trade_stats.get('profit_factor', 0.0)
                avg_trade_duration = trade_stats.get('avg_duration_hours', 0.0)
                
                # Calculate trades per year
                if len(returns) > 0:
                    period_years = len(returns) / 252
                    trades_per_year = total_trades / period_years if period_years > 0 else 0.0
                
                # Hit ratio (percentage of positive return periods)
                positive_periods = (returns > 0).sum()
                hit_ratio = positive_periods / len(returns) if len(returns) > 0 else 0.0
            
            # Create metrics object
            metrics = PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                cumulative_return=cumulative_return,
                volatility=volatility,
                max_drawdown=max_drawdown,
                calmar_ratio=calmar_ratio,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                information_ratio=information_ratio,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                avg_win=avg_win,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                skewness=skewness,
                kurtosis=kurtosis,
                var_95=var_95,
                expected_shortfall=expected_shortfall,
                hit_ratio=hit_ratio,
                up_capture=up_capture,
                down_capture=down_capture,
                avg_trade_duration=avg_trade_duration,
                trades_per_year=trades_per_year,
                alpha=alpha,
                beta=beta,
                tracking_error=tracking_error,
                start_date=returns.index[0] if len(returns) > 0 else datetime.now(),
                end_date=returns.index[-1] if len(returns) > 0 else datetime.now(),
                period_days=len(returns)
            )
            
            return metrics
        
        except Exception as e:
            logger.warning(f"Error calculating performance metrics: {e}")
            return self._empty_metrics()
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Create empty performance metrics object."""
        return PerformanceMetrics(
            total_return=0.0, annualized_return=0.0, cumulative_return=0.0,
            volatility=0.0, max_drawdown=0.0, calmar_ratio=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, information_ratio=0.0,
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, avg_win=0.0, avg_loss=0.0, profit_factor=0.0,
            skewness=0.0, kurtosis=0.0, var_95=0.0, expected_shortfall=0.0,
            hit_ratio=0.0, up_capture=0.0, down_capture=0.0,
            avg_trade_duration=0.0, trades_per_year=0.0,
            alpha=0.0, beta=0.0, tracking_error=0.0,
            start_date=datetime.now(), end_date=datetime.now(), period_days=0
        )
    
    def calculate_rolling_metrics(self,
                                returns: pd.Series,
                                window: int = 252,
                                metrics: List[str] = None) -> pd.DataFrame:
        """Calculate rolling performance metrics.
        
        Args:
            returns: Return series
            window: Rolling window size (default: 252 days)
            metrics: List of metrics to calculate
            
        Returns:
            DataFrame with rolling metrics
        """
        try:
            if len(returns) < window:
                return pd.DataFrame()
            
            if metrics is None:
                metrics = ['sharpe_ratio', 'volatility', 'max_drawdown', 'calmar_ratio']
            
            rolling_data = {}
            
            for i in range(window, len(returns) + 1):
                window_returns = returns.iloc[i-window:i]
                window_metrics = self.calculate_performance_metrics(window_returns)
                
                date = returns.index[i-1]
                for metric in metrics:
                    if metric not in rolling_data:
                        rolling_data[metric] = []
                    
                    value = getattr(window_metrics, metric, 0.0)
                    rolling_data[metric].append(value)
            
            # Create DataFrame
            rolling_df = pd.DataFrame(rolling_data)
            rolling_df.index = returns.index[window-1:]
            
            return rolling_df
        
        except Exception as e:
            logger.warning(f"Error calculating rolling metrics: {e}")
            return pd.DataFrame()
    
    def perform_attribution_analysis(self,
                                   trades: List[TradeResult],
                                   attribution_type: AttributionType) -> List[AttributionResult]:
        """Perform performance attribution analysis.
        
        Args:
            trades: List of completed trades
            attribution_type: Type of attribution to perform
            
        Returns:
            List of attribution results
        """
        try:
            attribution_results = []
            
            if not trades:
                return attribution_results
            
            # Group trades by attribution category
            grouped_trades = defaultdict(list)
            
            for trade in trades:
                if attribution_type == AttributionType.STRATEGY:
                    category = trade.strategy_type
                elif attribution_type == AttributionType.PAIR:
                    category = trade.pair_id
                elif attribution_type == AttributionType.SECTOR:
                    category = trade.metadata.get('sector', 'Unknown')
                elif attribution_type == AttributionType.TIME_PERIOD:
                    # Group by month
                    category = trade.entry_time.strftime('%Y-%m')
                elif attribution_type == AttributionType.MARKET_REGIME:
                    category = trade.metadata.get('market_regime', 'Unknown')
                else:
                    category = 'Unknown'
                
                grouped_trades[category].append(trade)
            
            # Calculate attribution for each category
            total_pnl = sum(trade.pnl for trade in trades)
            total_trades = len(trades)
            
            for category, category_trades in grouped_trades.items():
                category_pnl = sum(trade.pnl for trade in category_trades)
                category_count = len(category_trades)
                
                # Calculate metrics
                contribution = category_pnl / total_pnl if total_pnl != 0 else 0.0
                weight = category_count / total_trades if total_trades > 0 else 0.0
                
                # Calculate return contribution
                avg_return = category_pnl / category_count if category_count > 0 else 0.0
                return_contribution = avg_return * weight
                
                # Calculate risk contribution (simplified)
                returns = [trade.pnl_pct for trade in category_trades]
                risk_contribution = np.std(returns) if len(returns) > 1 else 0.0
                
                # Information ratio for category
                if len(returns) > 1 and np.std(returns) > 0:
                    info_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)
                else:
                    info_ratio = 0.0
                
                attribution_result = AttributionResult(
                    attribution_type=attribution_type,
                    category=category,
                    contribution=contribution,
                    weight=weight,
                    return_contribution=return_contribution,
                    risk_contribution=risk_contribution,
                    information_ratio=info_ratio,
                    trades_count=category_count,
                    metadata={
                        'total_pnl': category_pnl,
                        'avg_pnl': avg_return,
                        'win_rate': sum(1 for t in category_trades if t.pnl > 0) / category_count
                    }
                )
                
                attribution_results.append(attribution_result)
            
            # Sort by contribution (descending)
            attribution_results.sort(key=lambda x: abs(x.contribution), reverse=True)
            
            return attribution_results
        
        except Exception as e:
            logger.warning(f"Error performing attribution analysis: {e}")
            return []
    
    def generate_performance_report(self,
                                  returns: pd.Series,
                                  benchmark_returns: Optional[pd.Series] = None,
                                  trades: Optional[List[TradeResult]] = None) -> Dict:
        """Generate comprehensive performance report.
        
        Args:
            returns: Strategy return series
            benchmark_returns: Optional benchmark return series
            trades: Optional list of trades
            
        Returns:
            Comprehensive performance report dictionary
        """
        try:
            # Calculate main metrics
            metrics = self.calculate_performance_metrics(returns, benchmark_returns, trades)
            
            # Calculate rolling metrics
            rolling_metrics = self.calculate_rolling_metrics(returns)
            
            # Trade analysis
            trade_stats = {}
            strategy_analysis = {}
            pair_analysis = {}
            attribution_results = {}
            
            if trades:
                # Overall trade statistics
                original_trades = self.trade_analyzer.trades
                self.trade_analyzer.trades = trades
                trade_stats = self.trade_analyzer.calculate_trade_statistics()
                
                # Strategy and pair analysis
                strategy_analysis = self.trade_analyzer.analyze_by_strategy()
                pair_analysis = self.trade_analyzer.analyze_by_pair()
                
                # Attribution analysis
                attribution_results = {
                    'by_strategy': self.perform_attribution_analysis(trades, AttributionType.STRATEGY),
                    'by_pair': self.perform_attribution_analysis(trades, AttributionType.PAIR),
                    'by_time_period': self.perform_attribution_analysis(trades, AttributionType.TIME_PERIOD)
                }
                
                self.trade_analyzer.trades = original_trades
            
            # Compile report
            report = {
                'timestamp': datetime.now(),
                'summary_metrics': metrics,
                'rolling_metrics': rolling_metrics,
                'trade_statistics': trade_stats,
                'strategy_analysis': strategy_analysis,
                'pair_analysis': pair_analysis,
                'attribution_analysis': attribution_results,
                'period_summary': {
                    'start_date': metrics.start_date,
                    'end_date': metrics.end_date,
                    'total_days': metrics.period_days,
                    'trading_days': len(returns),
                    'years': len(returns) / 252 if len(returns) > 0 else 0
                },
                'risk_summary': {
                    'max_drawdown': metrics.max_drawdown,
                    'volatility': metrics.volatility,
                    'var_95': metrics.var_95,
                    'expected_shortfall': metrics.expected_shortfall,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'sortino_ratio': metrics.sortino_ratio
                }
            }
            
            return report
        
        except Exception as e:
            logger.warning(f"Error generating performance report: {e}")
            return {'error': str(e), 'timestamp': datetime.now()}