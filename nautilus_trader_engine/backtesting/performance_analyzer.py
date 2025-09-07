"""
Performance Analyzer for Backtesting

This module provides comprehensive performance analysis functionality for backtesting,
including return metrics, risk metrics, risk-adjusted metrics, and benchmark comparisons.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from scipy import stats


class PerformanceAnalyzer:
    """Performance analysis system for backtesting"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Performance Analyzer.
        
        Args:
            config: Configuration dictionary with analysis parameters
        """
        self.config = config
        self.benchmark_symbol = config.get('benchmark_symbol', 'SPY')
        self.risk_free_rate = config.get('risk_free_rate', 0.02)
        self.confidence_levels = config.get('confidence_levels', [0.95, 0.99])
        self.rolling_window_days = config.get('rolling_window_days', [30, 90, 252])
        self.attribution_analysis = config.get('attribution_analysis', True)
    
    def analyze_performance(self, returns: pd.Series, 
                          benchmark_returns: pd.Series = None) -> Dict[str, Any]:
        """
        Perform comprehensive performance analysis.
        
        Args:
            returns: Series of portfolio returns
            benchmark_returns: Series of benchmark returns (optional)
            
        Returns:
            Dictionary with comprehensive performance analysis
        """
        if returns.empty:
            return self._empty_analysis()
        
        # Calculate return metrics
        return_metrics = self._calculate_return_metrics(returns)
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(returns)
        
        # Calculate risk-adjusted metrics
        risk_adjusted_metrics = self._calculate_risk_adjusted_metrics(
            returns, risk_metrics['volatility'])
        
        # Calculate drawdown analysis
        drawdown_analysis = self._calculate_drawdown_analysis(returns)
        
        # Calculate benchmark comparison if benchmark provided
        if benchmark_returns is not None and not benchmark_returns.empty:
            benchmark_comparison = self._calculate_benchmark_comparison(
                returns, benchmark_returns)
        else:
            benchmark_comparison = self._empty_benchmark_comparison()
        
        return {
            'return_metrics': return_metrics,
            'risk_metrics': risk_metrics,
            'risk_adjusted_metrics': risk_adjusted_metrics,
            'drawdown_analysis': drawdown_analysis,
            'benchmark_comparison': benchmark_comparison
        }
    
    def _calculate_return_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate return-based performance metrics."""
        total_return = (1 + returns).prod() - 1
        
        # Annualized return (assuming daily returns)
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        # Geometric and arithmetic means
        geometric_mean = (1 + returns).prod() ** (1 / len(returns)) - 1
        arithmetic_mean = returns.mean()
        
        # CAGR
        cagr = (1 + total_return) ** (252 / len(returns)) - 1
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'geometric_mean': geometric_mean,
            'arithmetic_mean': arithmetic_mean,
            'compound_annual_growth_rate': cagr
        }
    
    def _calculate_risk_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """Calculate risk-based metrics."""
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)
        
        # Downside deviation
        negative_returns = returns[returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        
        # Semi-variance
        semi_variance = negative_returns.var() * 252 if len(negative_returns) > 0 else 0
        
        # VaR calculations
        var_95 = np.percentile(returns, 5)
        var_99 = np.percentile(returns, 1)
        
        # CVaR calculations
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else 0
        cvar_99 = returns[returns <= var_99].mean() if len(returns[returns <= var_99]) > 0 else 0
        
        return {
            'volatility': volatility,
            'downside_deviation': downside_deviation,
            'semi_variance': semi_variance,
            'var_95': abs(var_95),
            'var_99': abs(var_99),
            'cvar_95': abs(cvar_95),
            'cvar_99': abs(cvar_99)
        }
    
    def _calculate_risk_adjusted_metrics(self, returns: pd.Series, volatility: float) -> Dict[str, float]:
        """Calculate risk-adjusted performance metrics."""
        # Sharpe ratio
        excess_returns = returns - (self.risk_free_rate / 252)
        sharpe_ratio = (excess_returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        
        # Sortino ratio
        negative_returns = returns[returns < 0]
        downside_std = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
        sortino_ratio = (excess_returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar ratio
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = drawdown.min()
        annual_return = (1 + returns.mean()) ** 252 - 1
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Omega ratio (simplified)
        threshold = 0  # Risk-free rate could be used
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns <= threshold].sum())
        omega_ratio = gains / losses if losses != 0 else 0
        
        # Treynor ratio (requires beta, simplified here)
        treynor_ratio = annual_return / 1.0 if 1.0 != 0 else 0  # Using beta=1 as placeholder
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'omega_ratio': omega_ratio,
            'treynor_ratio': treynor_ratio
        }
    
    def _calculate_drawdown_analysis(self, returns: pd.Series) -> Dict[str, Any]:
        """Calculate drawdown analysis metrics."""
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - peak) / peak
        
        max_drawdown = drawdown.min()
        
        # Calculate drawdown duration
        drawdown_duration = 0
        max_drawdown_duration = 0
        
        # Simplified drawdown periods calculation
        drawdown_periods = len(drawdown[drawdown < 0])
        
        return {
            'max_drawdown': abs(max_drawdown),
            'max_drawdown_duration': max_drawdown_duration,
            'avg_drawdown': abs(drawdown.mean()),
            'recovery_time': 0,  # Simplified
            'drawdown_periods': drawdown_periods
        }
    
    def _calculate_benchmark_comparison(self, returns: pd.Series, 
                                      benchmark_returns: pd.Series) -> Dict[str, float]:
        """Calculate benchmark comparison metrics."""
        # Align series
        aligned_data = pd.concat([returns, benchmark_returns], axis=1).dropna()
        if aligned_data.empty:
            return self._empty_benchmark_comparison()
        
        strategy_returns = aligned_data.iloc[:, 0]
        bench_returns = aligned_data.iloc[:, 1]
        
        # Alpha and Beta
        if len(strategy_returns) > 1 and strategy_returns.std() > 0:
            beta, alpha = self._regression(bench_returns, strategy_returns)
            alpha = alpha * 252  # Annualize alpha
        else:
            beta, alpha = 0, 0
        
        # Correlation
        correlation = strategy_returns.corr(bench_returns)
        
        # Tracking error
        tracking_error = (strategy_returns - bench_returns).std() * np.sqrt(252)
        
        # Information ratio
        information_ratio = (strategy_returns.mean() - bench_returns.mean()) / (strategy_returns - bench_returns).std() * np.sqrt(252) if (strategy_returns - bench_returns).std() > 0 else 0
        
        # Up/Down capture ratios
        up_capture = 0  # Simplified
        down_capture = 0  # Simplified
        
        return {
            'alpha': alpha,
            'beta': beta,
            'correlation': correlation,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'up_capture': up_capture,
            'down_capture': down_capture
        }
    
    def _regression(self, x: pd.Series, y: pd.Series) -> Tuple[float, float]:
        """Perform linear regression to calculate alpha and beta."""
        if len(x) < 2:
            return 0, 0
        
        # Calculate beta and alpha
        covariance = np.cov(x, y)[0, 1]
        variance = np.var(x)
        beta = covariance / variance if variance != 0 else 0
        alpha = y.mean() - beta * x.mean()
        
        return beta, alpha
    
    def _empty_analysis(self) -> Dict[str, Dict[str, float]]:
        """Return empty analysis when calculation fails."""
        return {
            'return_metrics': self._empty_return_metrics(),
            'risk_metrics': self._empty_risk_metrics(),
            'risk_adjusted_metrics': self._empty_risk_adjusted_metrics(),
            'drawdown_analysis': self._empty_drawdown_analysis(),
            'benchmark_comparison': self._empty_benchmark_comparison()
        }
    
    def _empty_return_metrics(self) -> Dict[str, float]:
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'geometric_mean': 0.0,
            'arithmetic_mean': 0.0,
            'compound_annual_growth_rate': 0.0
        }
    
    def _empty_risk_metrics(self) -> Dict[str, float]:
        return {
            'volatility': 0.0,
            'downside_deviation': 0.0,
            'semi_variance': 0.0,
            'var_95': 0.0,
            'var_99': 0.0,
            'cvar_95': 0.0,
            'cvar_99': 0.0
        }
    
    def _empty_risk_adjusted_metrics(self) -> Dict[str, float]:
        return {
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'omega_ratio': 0.0,
            'treynor_ratio': 0.0
        }
    
    def _empty_drawdown_analysis(self) -> Dict[str, Any]:
        return {
            'max_drawdown': 0.0,
            'max_drawdown_duration': 0,
            'avg_drawdown': 0.0,
            'recovery_time': 0,
            'drawdown_periods': 0
        }
    
    def _empty_benchmark_comparison(self) -> Dict[str, float]:
        return {
            'alpha': 0.0,
            'beta': 0.0,
            'correlation': 0.0,
            'tracking_error': 0.0,
            'information_ratio': 0.0,
            'up_capture': 0.0,
            'down_capture': 0.0
        }
    
    def rolling_analysis(self, returns: pd.Series) -> Dict[str, Any]:
        """
        Perform rolling window performance analysis.
        
        Args:
            returns: Series of portfolio returns
            
        Returns:
            Dictionary with rolling analysis results
        """
        if returns.empty:
            return {}
        
        results = {}
        
        for window_days in self.rolling_window_days:
            window_key = f"{window_days}_day"
            
            # Calculate rolling metrics
            rolling_sharpe = []
            rolling_volatility = []
            rolling_returns = []
            
            # Simplified rolling calculations
            if len(returns) >= window_days:
                for i in range(window_days, len(returns) + 1):
                    window_returns = returns.iloc[i-window_days:i]
                    if not window_returns.empty:
                        volatility = window_returns.std() * np.sqrt(252)
                        excess_returns = window_returns - (self.risk_free_rate / 252)
                        sharpe = (excess_returns.mean() / window_returns.std()) * np.sqrt(252) if window_returns.std() > 0 else 0
                        total_return = (1 + window_returns).prod() - 1
                        
                        rolling_sharpe.append(sharpe)
                        rolling_volatility.append(volatility)
                        rolling_returns.append(total_return)
            
            results[window_key] = {
                'rolling_sharpe': pd.Series(rolling_sharpe),
                'rolling_volatility': pd.Series(rolling_volatility),
                'rolling_returns': pd.Series(rolling_returns)
            }
        
        return results