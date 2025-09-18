"""Performance Analysis Module

This module provides comprehensive performance analysis for backtesting results
including returns analysis, risk metrics, benchmark comparison, and attribution.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    # Return metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    cumulative_return: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    downside_volatility: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Distribution metrics
    skewness: float = 0.0
    kurtosis: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    
    # Trade metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Consistency metrics
    monthly_win_rate: float = 0.0
    best_month: float = 0.0
    worst_month: float = 0.0
    
    # Benchmark comparison
    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    
    # Additional metrics
    recovery_factor: float = 0.0
    payoff_ratio: float = 0.0
    expectancy: float = 0.0

@dataclass
class RollingMetrics:
    """Rolling performance metrics"""
    window: int = 252
    rolling_returns: pd.Series = field(default_factory=pd.Series)
    rolling_volatility: pd.Series = field(default_factory=pd.Series)
    rolling_sharpe: pd.Series = field(default_factory=pd.Series)
    rolling_max_drawdown: pd.Series = field(default_factory=pd.Series)
    rolling_beta: pd.Series = field(default_factory=pd.Series)

@dataclass
class BenchmarkComparison:
    """Benchmark comparison metrics"""
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0
    r_squared: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    up_capture: float = 0.0
    down_capture: float = 0.0
    correlation: float = 0.0

@dataclass
class PerformanceReport:
    """Comprehensive performance report"""
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    benchmark_comparison: Optional[BenchmarkComparison] = None
    rolling_metrics: Optional[RollingMetrics] = None
    monthly_returns: pd.Series = field(default_factory=pd.Series)
    yearly_returns: pd.Series = field(default_factory=pd.Series)
    drawdown_periods: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'metrics': self.metrics.__dict__,
            'benchmark_comparison': self.benchmark_comparison.__dict__ if self.benchmark_comparison else None,
            'monthly_returns': self.monthly_returns.to_dict() if not self.monthly_returns.empty else {},
            'yearly_returns': self.yearly_returns.to_dict() if not self.yearly_returns.empty else {},
            'drawdown_periods': self.drawdown_periods
        }

class PerformanceAnalyzer:
    """Comprehensive performance analyzer
    
    Calculates various performance metrics, risk measures, and benchmark comparisons
    for backtesting results.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize performance analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.risk_free_rate = self.config.get('risk_free_rate', 0.02)
        self.confidence_level = self.config.get('confidence_level', 0.95)
        self.rolling_window = self.config.get('rolling_window', 252)
        
        logger.info("Initialized performance analyzer")
    
    def analyze_performance(
        self,
        portfolio_values: pd.Series,
        benchmark_values: Optional[pd.Series] = None,
        trades: Optional[List[Any]] = None
    ) -> PerformanceReport:
        """Analyze portfolio performance
        
        Args:
            portfolio_values: Time series of portfolio values
            benchmark_values: Optional benchmark values for comparison
            trades: Optional list of trades for trade analysis
            
        Returns:
            Comprehensive performance report
        """
        try:
            # Calculate returns
            returns = portfolio_values.pct_change().dropna()
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(returns, portfolio_values, trades)
            
            # Calculate benchmark comparison if provided
            benchmark_comparison = None
            if benchmark_values is not None:
                benchmark_comparison = self._calculate_benchmark_comparison(returns, benchmark_values)
            
            # Calculate rolling metrics
            rolling_metrics = self._calculate_rolling_metrics(returns, benchmark_values)
            
            # Calculate period returns
            monthly_returns = self._calculate_monthly_returns(returns)
            yearly_returns = self._calculate_yearly_returns(returns)
            
            # Analyze drawdown periods
            drawdown_periods = self._analyze_drawdown_periods(portfolio_values)
            
            # Create report
            report = PerformanceReport(
                metrics=metrics,
                benchmark_comparison=benchmark_comparison,
                rolling_metrics=rolling_metrics,
                monthly_returns=monthly_returns,
                yearly_returns=yearly_returns,
                drawdown_periods=drawdown_periods
            )
            
            logger.info(f"Performance analysis completed - Sharpe: {metrics.sharpe_ratio:.3f}, Max DD: {metrics.max_drawdown:.2%}")
            return report
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            raise
    
    def _calculate_performance_metrics(
        self,
        returns: pd.Series,
        portfolio_values: pd.Series,
        trades: Optional[List[Any]] = None
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        try:
            metrics = PerformanceMetrics()
            
            # Return metrics
            metrics.total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
            metrics.cumulative_return = metrics.total_return
            
            # Annualized return
            years = len(returns) / 252
            metrics.annualized_return = (1 + metrics.total_return) ** (1 / years) - 1 if years > 0 else 0
            
            # Risk metrics
            metrics.volatility = returns.std() * np.sqrt(252)
            
            # Downside volatility (Sortino denominator)
            downside_returns = returns[returns < 0]
            metrics.downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
            
            # Drawdown analysis
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            metrics.max_drawdown = drawdown.min()
            
            # Max drawdown duration
            drawdown_duration = self._calculate_drawdown_duration(drawdown)
            metrics.max_drawdown_duration = drawdown_duration
            
            # Risk-adjusted returns
            excess_returns = returns - self.risk_free_rate / 252
            metrics.sharpe_ratio = excess_returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            
            if metrics.downside_volatility > 0:
                metrics.sortino_ratio = (metrics.annualized_return - self.risk_free_rate) / metrics.downside_volatility
            
            if abs(metrics.max_drawdown) > 0:
                metrics.calmar_ratio = metrics.annualized_return / abs(metrics.max_drawdown)
            
            # Omega ratio
            metrics.omega_ratio = self._calculate_omega_ratio(returns)
            
            # Distribution metrics
            metrics.skewness = returns.skew()
            metrics.kurtosis = returns.kurtosis()
            
            # VaR and CVaR
            metrics.var_95 = returns.quantile(1 - self.confidence_level)
            tail_returns = returns[returns <= metrics.var_95]
            metrics.cvar_95 = tail_returns.mean() if len(tail_returns) > 0 else 0
            
            # Trade metrics (if trades provided)
            if trades:
                metrics = self._calculate_trade_metrics(metrics, trades)
            
            # Consistency metrics
            monthly_returns = self._calculate_monthly_returns(returns)
            if not monthly_returns.empty:
                metrics.monthly_win_rate = (monthly_returns > 0).mean()
                metrics.best_month = monthly_returns.max()
                metrics.worst_month = monthly_returns.min()
            
            # Recovery factor
            if abs(metrics.max_drawdown) > 0:
                metrics.recovery_factor = metrics.total_return / abs(metrics.max_drawdown)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics()
    
    def _calculate_trade_metrics(self, metrics: PerformanceMetrics, trades: List[Any]) -> PerformanceMetrics:
        """Calculate trade-specific metrics"""
        try:
            if not trades:
                return metrics
            
            # Extract trade PnL
            trade_pnl = [getattr(trade, 'pnl', 0) for trade in trades if hasattr(trade, 'pnl')]
            
            if not trade_pnl:
                return metrics
            
            winning_trades = [pnl for pnl in trade_pnl if pnl > 0]
            losing_trades = [pnl for pnl in trade_pnl if pnl < 0]
            
            # Win rate
            metrics.win_rate = len(winning_trades) / len(trade_pnl) if trade_pnl else 0
            
            # Profit factor
            total_wins = sum(winning_trades) if winning_trades else 0
            total_losses = abs(sum(losing_trades)) if losing_trades else 0
            metrics.profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
            
            # Average win/loss
            metrics.avg_win = np.mean(winning_trades) if winning_trades else 0
            metrics.avg_loss = np.mean(losing_trades) if losing_trades else 0
            
            # Largest win/loss
            metrics.largest_win = max(winning_trades) if winning_trades else 0
            metrics.largest_loss = min(losing_trades) if losing_trades else 0
            
            # Payoff ratio
            metrics.payoff_ratio = abs(metrics.avg_win / metrics.avg_loss) if metrics.avg_loss != 0 else 0
            
            # Expectancy
            metrics.expectancy = (metrics.win_rate * metrics.avg_win) + ((1 - metrics.win_rate) * metrics.avg_loss)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating trade metrics: {e}")
            return metrics
    
    def _calculate_benchmark_comparison(
        self,
        returns: pd.Series,
        benchmark_values: pd.Series
    ) -> BenchmarkComparison:
        """Calculate benchmark comparison metrics"""
        try:
            # Align data
            benchmark_returns = benchmark_values.pct_change().dropna()
            aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
            
            if len(aligned_returns) == 0:
                return BenchmarkComparison()
            
            comparison = BenchmarkComparison()
            
            # Basic metrics
            comparison.benchmark_return = (benchmark_values.iloc[-1] / benchmark_values.iloc[0]) - 1
            portfolio_return = (aligned_returns + 1).prod() - 1
            comparison.excess_return = portfolio_return - comparison.benchmark_return
            
            # Regression analysis (CAPM)
            if len(aligned_returns) > 1 and aligned_benchmark.std() > 0:
                slope, intercept, r_value, p_value, std_err = stats.linregress(aligned_benchmark, aligned_returns)
                
                comparison.beta = slope
                comparison.alpha = intercept * 252  # Annualized
                comparison.r_squared = r_value ** 2
                comparison.correlation = r_value
            
            # Information ratio and tracking error
            excess_returns = aligned_returns - aligned_benchmark
            comparison.tracking_error = excess_returns.std() * np.sqrt(252)
            
            if comparison.tracking_error > 0:
                comparison.information_ratio = excess_returns.mean() * 252 / comparison.tracking_error
            
            # Up/Down capture ratios
            up_market = aligned_benchmark > 0
            down_market = aligned_benchmark < 0
            
            if up_market.sum() > 0:
                up_portfolio = aligned_returns[up_market].mean()
                up_benchmark = aligned_benchmark[up_market].mean()
                comparison.up_capture = up_portfolio / up_benchmark if up_benchmark != 0 else 0
            
            if down_market.sum() > 0:
                down_portfolio = aligned_returns[down_market].mean()
                down_benchmark = aligned_benchmark[down_market].mean()
                comparison.down_capture = down_portfolio / down_benchmark if down_benchmark != 0 else 0
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error calculating benchmark comparison: {e}")
            return BenchmarkComparison()
    
    def _calculate_rolling_metrics(
        self,
        returns: pd.Series,
        benchmark_values: Optional[pd.Series] = None
    ) -> RollingMetrics:
        """Calculate rolling performance metrics"""
        try:
            rolling = RollingMetrics(window=self.rolling_window)
            
            if len(returns) < self.rolling_window:
                return rolling
            
            # Rolling returns (annualized)
            rolling.rolling_returns = returns.rolling(self.rolling_window).apply(
                lambda x: (1 + x).prod() ** (252 / len(x)) - 1
            )
            
            # Rolling volatility (annualized)
            rolling.rolling_volatility = returns.rolling(self.rolling_window).std() * np.sqrt(252)
            
            # Rolling Sharpe ratio
            rolling_excess = returns.rolling(self.rolling_window).apply(
                lambda x: x.mean() - self.risk_free_rate / 252
            )
            rolling_vol = returns.rolling(self.rolling_window).std()
            rolling.rolling_sharpe = (rolling_excess / rolling_vol) * np.sqrt(252)
            
            # Rolling max drawdown
            cumulative = (1 + returns).cumprod()
            rolling.rolling_max_drawdown = cumulative.rolling(self.rolling_window).apply(
                lambda x: ((x - x.expanding().max()) / x.expanding().max()).min()
            )
            
            # Rolling beta (if benchmark provided)
            if benchmark_values is not None:
                benchmark_returns = benchmark_values.pct_change().dropna()
                aligned_returns, aligned_benchmark = returns.align(benchmark_returns, join='inner')
                
                if len(aligned_returns) >= self.rolling_window:
                    rolling.rolling_beta = aligned_returns.rolling(self.rolling_window).apply(
                        lambda x: stats.linregress(aligned_benchmark.loc[x.index], x)[0]
                        if len(x) == self.rolling_window else np.nan
                    )
            
            return rolling
            
        except Exception as e:
            logger.error(f"Error calculating rolling metrics: {e}")
            return RollingMetrics()
    
    def _calculate_monthly_returns(self, returns: pd.Series) -> pd.Series:
        """Calculate monthly returns"""
        try:
            if returns.empty:
                return pd.Series()
            
            monthly = (1 + returns).resample('M').prod() - 1
            return monthly
            
        except Exception as e:
            logger.error(f"Error calculating monthly returns: {e}")
            return pd.Series()
    
    def _calculate_yearly_returns(self, returns: pd.Series) -> pd.Series:
        """Calculate yearly returns"""
        try:
            if returns.empty:
                return pd.Series()
            
            yearly = (1 + returns).resample('Y').prod() - 1
            return yearly
            
        except Exception as e:
            logger.error(f"Error calculating yearly returns: {e}")
            return pd.Series()
    
    def _analyze_drawdown_periods(self, portfolio_values: pd.Series) -> List[Dict[str, Any]]:
        """Analyze drawdown periods"""
        try:
            returns = portfolio_values.pct_change().dropna()
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            
            # Find drawdown periods
            in_drawdown = drawdown < 0
            drawdown_periods = []
            
            start_idx = None
            for i, is_dd in enumerate(in_drawdown):
                if is_dd and start_idx is None:
                    start_idx = i
                elif not is_dd and start_idx is not None:
                    end_idx = i - 1
                    period_drawdown = drawdown.iloc[start_idx:end_idx+1]
                    
                    drawdown_periods.append({
                        'start_date': drawdown.index[start_idx],
                        'end_date': drawdown.index[end_idx],
                        'duration_days': (drawdown.index[end_idx] - drawdown.index[start_idx]).days,
                        'max_drawdown': period_drawdown.min(),
                        'recovery_date': drawdown.index[i] if i < len(drawdown) else None
                    })
                    
                    start_idx = None
            
            # Handle ongoing drawdown
            if start_idx is not None:
                period_drawdown = drawdown.iloc[start_idx:]
                drawdown_periods.append({
                    'start_date': drawdown.index[start_idx],
                    'end_date': drawdown.index[-1],
                    'duration_days': (drawdown.index[-1] - drawdown.index[start_idx]).days,
                    'max_drawdown': period_drawdown.min(),
                    'recovery_date': None  # Ongoing
                })
            
            return drawdown_periods
            
        except Exception as e:
            logger.error(f"Error analyzing drawdown periods: {e}")
            return []
    
    def _calculate_drawdown_duration(self, drawdown: pd.Series) -> int:
        """Calculate maximum drawdown duration in days"""
        try:
            in_drawdown = drawdown < 0
            max_duration = 0
            current_duration = 0
            
            for is_dd in in_drawdown:
                if is_dd:
                    current_duration += 1
                    max_duration = max(max_duration, current_duration)
                else:
                    current_duration = 0
            
            return max_duration
            
        except Exception as e:
            logger.error(f"Error calculating drawdown duration: {e}")
            return 0
    
    def _calculate_omega_ratio(self, returns: pd.Series, threshold: float = 0.0) -> float:
        """Calculate Omega ratio"""
        try:
            excess_returns = returns - threshold
            positive_returns = excess_returns[excess_returns > 0].sum()
            negative_returns = abs(excess_returns[excess_returns < 0].sum())
            
            if negative_returns == 0:
                return float('inf') if positive_returns > 0 else 0
            
            return positive_returns / negative_returns
            
        except Exception as e:
            logger.error(f"Error calculating Omega ratio: {e}")
            return 0.0
    
    def generate_performance_summary(self, report: PerformanceReport) -> str:
        """Generate human-readable performance summary"""
        try:
            metrics = report.metrics
            
            summary = f"""
PERFORMANCE SUMMARY
==================

Return Metrics:
- Total Return: {metrics.total_return:.2%}
- Annualized Return: {metrics.annualized_return:.2%}
- Volatility: {metrics.volatility:.2%}

Risk Metrics:
- Sharpe Ratio: {metrics.sharpe_ratio:.3f}
- Sortino Ratio: {metrics.sortino_ratio:.3f}
- Max Drawdown: {metrics.max_drawdown:.2%}
- Max DD Duration: {metrics.max_drawdown_duration} days

Trade Metrics:
- Win Rate: {metrics.win_rate:.2%}
- Profit Factor: {metrics.profit_factor:.2f}
- Average Win: {metrics.avg_win:.2f}
- Average Loss: {metrics.avg_loss:.2f}

Distribution:
- Skewness: {metrics.skewness:.3f}
- Kurtosis: {metrics.kurtosis:.3f}
- VaR (95%): {metrics.var_95:.2%}
- CVaR (95%): {metrics.cvar_95:.2%}
"""
            
            if report.benchmark_comparison:
                bc = report.benchmark_comparison
                summary += f"""
Benchmark Comparison:
- Alpha: {bc.alpha:.2%}
- Beta: {bc.beta:.3f}
- Information Ratio: {bc.information_ratio:.3f}
- Tracking Error: {bc.tracking_error:.2%}
- Correlation: {bc.correlation:.3f}
"""
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating performance summary: {e}")
            return "Error generating summary"