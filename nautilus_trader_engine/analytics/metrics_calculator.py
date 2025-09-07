"""Metrics Calculator for Analytics Module
Calculates performance, risk, and execution metrics for trading strategies.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """Performance metrics for trading strategies."""
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    average_trade_return: float


@dataclass
class RiskMetrics:
    """Risk metrics for trading strategies."""
    value_at_risk: float
    conditional_value_at_risk: float
    maximum_drawdown: float
    volatility: float
    beta: float
    alpha: float
    tracking_error: float
    information_ratio: float


class MetricsCalculator:
    """Calculates various metrics for trading performance and risk analysis."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the metrics calculator with configuration.
        
        Args:
            config: Configuration dictionary with calculation parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Extract configuration parameters
        self.metrics_types = config.get('metrics_types', ['performance', 'risk'])
        self.calculation_frequency = config.get('calculation_frequency', 'real_time')
        self.rolling_windows = config.get('rolling_windows', [30, 60, 90, 252])
        self.benchmark_comparison = config.get('benchmark_comparison', True)
        self.risk_free_rate = config.get('risk_free_rate', 0.02)  # 2% annual
    
    def calculate_performance_metrics(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> PerformanceMetrics:
        """Calculate performance metrics from returns data.
        
        Args:
            returns: Series of portfolio returns
            benchmark_returns: Optional benchmark returns for comparison
            
        Returns:
            PerformanceMetrics object with calculated metrics
        """
        try:
            # Remove any NaN values
            returns = returns.dropna()
            
            if len(returns) == 0:
                return PerformanceMetrics(
                    total_return=0.0,
                    annualized_return=0.0,
                    sharpe_ratio=0.0,
                    sortino_ratio=0.0,
                    calmar_ratio=0.0,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    average_trade_return=0.0
                )
            
            # Calculate total return
            total_return = (1 + returns).prod() - 1
            
            # Calculate annualized return (assuming daily returns, 252 trading days)
            annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
            
            # Calculate volatility (standard deviation of returns)
            volatility = returns.std()
            
            # Calculate Sharpe ratio
            excess_returns = returns - (self.risk_free_rate / 252)  # Daily risk-free rate
            sharpe_ratio = excess_returns.mean() / volatility if volatility > 0 else 0.0
            
            # Calculate Sortino ratio (using downside deviation)
            negative_returns = returns[returns < 0]
            downside_deviation = negative_returns.std() if len(negative_returns) > 0 else 0.0
            sortino_ratio = excess_returns.mean() / downside_deviation if downside_deviation > 0 else 0.0
            
            # Calculate maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Calculate Calmar ratio
            calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0.0
            
            # Calculate win rate
            winning_trades = (returns > 0).sum()
            total_trades = len(returns)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
            
            # Calculate profit factor
            gross_profits = returns[returns > 0].sum()
            gross_losses = abs(returns[returns < 0].sum())
            profit_factor = gross_profits / gross_losses if gross_losses > 0 else float('inf')
            
            # Calculate average trade return
            average_trade_return = returns.mean()
            
            return PerformanceMetrics(
                total_return=total_return,
                annualized_return=annualized_return,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                average_trade_return=average_trade_return
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics(
                total_return=0.0,
                annualized_return=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                average_trade_return=0.0
            )
    
    def calculate_risk_metrics(self, returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> RiskMetrics:
        """Calculate risk metrics from returns data.
        
        Args:
            returns: Series of portfolio returns
            benchmark_returns: Optional benchmark returns for comparison
            
        Returns:
            RiskMetrics object with calculated metrics
        """
        try:
            # Remove any NaN values
            returns = returns.dropna()
            
            if len(returns) == 0:
                return RiskMetrics(
                    value_at_risk=0.0,
                    conditional_value_at_risk=0.0,
                    maximum_drawdown=0.0,
                    volatility=0.0,
                    beta=0.0,
                    alpha=0.0,
                    tracking_error=0.0,
                    information_ratio=0.0
                )
            
            # Calculate Value at Risk (VaR) at 95% confidence level
            var_95 = np.percentile(returns, 5)
            
            # Calculate Conditional Value at Risk (CVaR)
            cvar_95 = returns[returns <= var_95].mean()
            
            # Calculate maximum drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Calculate volatility (standard deviation of returns)
            volatility = returns.std()
            
            # Calculate beta and alpha if benchmark data is provided
            beta = 0.0
            alpha = 0.0
            if benchmark_returns is not None and len(benchmark_returns) == len(returns):
                benchmark_returns = benchmark_returns.dropna()
                if len(benchmark_returns) > 0:
                    # Calculate beta using covariance method
                    covariance = np.cov(returns, benchmark_returns)[0, 1]
                    benchmark_variance = np.var(benchmark_returns)
                    beta = covariance / benchmark_variance if benchmark_variance > 0 else 0.0
                    
                    # Calculate alpha
                    benchmark_return = benchmark_returns.mean()
                    portfolio_return = returns.mean()
                    alpha = portfolio_return - (self.risk_free_rate / 252) - beta * (benchmark_return - (self.risk_free_rate / 252))
            
            # Calculate tracking error
            tracking_error = 0.0
            if benchmark_returns is not None and len(benchmark_returns) == len(returns):
                benchmark_returns = benchmark_returns.dropna()
                if len(benchmark_returns) > 0:
                    tracking_error = (returns - benchmark_returns).std()
            
            # Calculate information ratio
            information_ratio = (returns.mean() - (benchmark_returns.mean() if benchmark_returns is not None else 0)) / tracking_error if tracking_error > 0 else 0.0
            
            return RiskMetrics(
                value_at_risk=var_95,
                conditional_value_at_risk=cvar_95,
                maximum_drawdown=max_drawdown,
                volatility=volatility,
                beta=beta,
                alpha=alpha,
                tracking_error=tracking_error,
                information_ratio=information_ratio
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(
                value_at_risk=0.0,
                conditional_value_at_risk=0.0,
                maximum_drawdown=0.0,
                volatility=0.0,
                beta=0.0,
                alpha=0.0,
                tracking_error=0.0,
                information_ratio=0.0
            )