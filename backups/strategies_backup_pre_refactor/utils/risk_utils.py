"""Risk management utility functions for trading strategies.

This module provides comprehensive risk management utilities including
position sizing, portfolio risk metrics, and risk-adjusted returns.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_position_size(account_balance: float, risk_per_trade: float, 
                          entry_price: float, stop_loss: float, 
                          max_position_size: Optional[float] = None) -> float:
    """Calculate position size based on risk management rules.
    
    Args:
        account_balance: Total account balance
        risk_per_trade: Risk per trade as percentage (e.g., 0.02 for 2%)
        entry_price: Entry price for the position
        stop_loss: Stop loss price
        max_position_size: Maximum position size as percentage of balance
        
    Returns:
        float: Position size in shares/units
    """
    if stop_loss == entry_price:
        logger.warning("Stop loss equals entry price, cannot calculate position size")
        return 0.0
    
    # Calculate risk per share
    risk_per_share = abs(entry_price - stop_loss)
    
    # Calculate maximum risk amount
    max_risk_amount = account_balance * risk_per_trade
    
    # Calculate position size
    position_size = max_risk_amount / risk_per_share
    
    # Apply maximum position size constraint if specified
    if max_position_size:
        max_shares = (account_balance * max_position_size) / entry_price
        position_size = min(position_size, max_shares)
    
    return max(0, position_size)


def calculate_portfolio_var(returns: pd.DataFrame, confidence_level: float = 0.05, 
                           method: str = 'historical') -> Dict[str, float]:
    """Calculate Value at Risk (VaR) for portfolio.
    
    Args:
        returns: DataFrame of asset returns
        confidence_level: Confidence level (e.g., 0.05 for 95% VaR)
        method: 'historical', 'parametric', or 'monte_carlo'
        
    Returns:
        Dict: VaR metrics
    """
    portfolio_returns = returns.sum(axis=1)
    
    if method == 'historical':
        var = np.percentile(portfolio_returns, confidence_level * 100)
    elif method == 'parametric':
        mean = portfolio_returns.mean()
        std = portfolio_returns.std()
        var = mean + std * np.percentile(np.random.normal(0, 1, 10000), confidence_level * 100)
    else:
        raise ValueError("Method must be 'historical' or 'parametric'")
    
    # Calculate Expected Shortfall (Conditional VaR)
    es = portfolio_returns[portfolio_returns <= var].mean()
    
    return {
        'VaR': var,
        'Expected_Shortfall': es,
        'Confidence_Level': 1 - confidence_level
    }


def calculate_beta(asset_returns: pd.Series, market_returns: pd.Series) -> float:
    """Calculate beta coefficient.
    
    Args:
        asset_returns: Asset return series
        market_returns: Market return series
        
    Returns:
        float: Beta coefficient
    """
    covariance = np.cov(asset_returns.dropna(), market_returns.dropna())[0, 1]
    market_variance = np.var(market_returns.dropna())
    
    return covariance / market_variance if market_variance != 0 else 0.0


def calculate_tracking_error(portfolio_returns: pd.Series, 
                           benchmark_returns: pd.Series) -> float:
    """Calculate tracking error.
    
    Args:
        portfolio_returns: Portfolio return series
        benchmark_returns: Benchmark return series
        
    Returns:
        float: Annualized tracking error
    """
    excess_returns = portfolio_returns - benchmark_returns
    return excess_returns.std() * np.sqrt(252)


def calculate_information_ratio(portfolio_returns: pd.Series, 
                              benchmark_returns: pd.Series) -> float:
    """Calculate information ratio.
    
    Args:
        portfolio_returns: Portfolio return series
        benchmark_returns: Benchmark return series
        
    Returns:
        float: Information ratio
    """
    excess_returns = portfolio_returns - benchmark_returns
    tracking_error = calculate_tracking_error(portfolio_returns, benchmark_returns)
    
    return (excess_returns.mean() * 252) / tracking_error if tracking_error != 0 else 0.0


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02, 
                          periods_per_year: int = 252) -> float:
    """Calculate Sortino ratio.
    
    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year
        
    Returns:
        float: Sortino ratio
    """
    excess_returns = returns - (risk_free_rate / periods_per_year)
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return np.inf
    
    downside_deviation = downside_returns.std() * np.sqrt(periods_per_year)
    
    return (excess_returns.mean() * periods_per_year) / downside_deviation


def calculate_calmar_ratio(returns: pd.Series) -> float:
    """Calculate Calmar ratio.
    
    Args:
        returns: Return series
        
    Returns:
        float: Calmar ratio
    """
    from .common_functions import calculate_max_drawdown
    
    annual_return = (1 + returns.mean()) ** 252 - 1
    max_dd, _, _ = calculate_max_drawdown(returns)
    
    return annual_return / abs(max_dd) if max_dd != 0 else np.inf


def calculate_portfolio_weights(returns: pd.DataFrame, method: str = 'equal_weight', 
                              **kwargs) -> pd.Series:
    """Calculate portfolio weights.
    
    Args:
        returns: DataFrame of asset returns
        method: 'equal_weight', 'market_cap', 'min_variance', 'max_sharpe'
        **kwargs: Additional parameters for optimization methods
        
    Returns:
        pd.Series: Portfolio weights
    """
    n_assets = len(returns.columns)
    
    if method == 'equal_weight':
        return pd.Series(1/n_assets, index=returns.columns)
    
    elif method == 'min_variance':
        # Simple minimum variance optimization
        cov_matrix = returns.cov()
        inv_cov = np.linalg.pinv(cov_matrix)
        ones = np.ones((n_assets, 1))
        
        weights = inv_cov @ ones
        weights = weights / weights.sum()
        
        return pd.Series(weights.flatten(), index=returns.columns)
    
    elif method == 'max_sharpe':
        # Simple maximum Sharpe ratio optimization
        mean_returns = returns.mean()
        cov_matrix = returns.cov()
        
        # Use inverse volatility weighting as approximation
        inv_vol = 1 / np.sqrt(np.diag(cov_matrix))
        weights = inv_vol / inv_vol.sum()
        
        return pd.Series(weights, index=returns.columns)
    
    else:
        raise ValueError("Method must be 'equal_weight', 'min_variance', or 'max_sharpe'")


def calculate_risk_metrics(returns: pd.Series, benchmark_returns: Optional[pd.Series] = None) -> Dict[str, float]:
    """Calculate comprehensive risk metrics.
    
    Args:
        returns: Return series
        benchmark_returns: Optional benchmark return series
        
    Returns:
        Dict: Risk metrics
    """
    from .common_functions import calculate_sharpe_ratio, calculate_max_drawdown
    
    metrics = {
        'Volatility': returns.std() * np.sqrt(252),
        'Sharpe_Ratio': calculate_sharpe_ratio(returns),
        'Sortino_Ratio': calculate_sortino_ratio(returns),
        'Calmar_Ratio': calculate_calmar_ratio(returns),
        'Skewness': returns.skew(),
        'Kurtosis': returns.kurtosis(),
    }
    
    max_dd, _, _ = calculate_max_drawdown(returns)
    metrics['Max_Drawdown'] = max_dd
    
    if benchmark_returns is not None:
        metrics['Beta'] = calculate_beta(returns, benchmark_returns)
        metrics['Tracking_Error'] = calculate_tracking_error(returns, benchmark_returns)
        metrics['Information_Ratio'] = calculate_information_ratio(returns, benchmark_returns)
    
    return metrics


def check_risk_limits(position_size: float, account_balance: float, 
                     current_positions: Dict[str, float], 
                     risk_limits: Dict[str, float]) -> Tuple[bool, List[str]]:
    """Check if position violates risk limits.
    
    Args:
        position_size: Proposed position size
        account_balance: Current account balance
        current_positions: Dictionary of current positions
        risk_limits: Dictionary of risk limits
        
    Returns:
        Tuple: (is_valid, list_of_violations)
    """
    violations = []
    
    # Check maximum position size
    if 'max_position_pct' in risk_limits:
        max_position_value = account_balance * risk_limits['max_position_pct']
        if position_size > max_position_value:
            violations.append(f"Position size exceeds maximum ({risk_limits['max_position_pct']:.1%})")
    
    # Check maximum portfolio exposure
    if 'max_portfolio_exposure' in risk_limits:
        total_exposure = sum(abs(pos) for pos in current_positions.values()) + abs(position_size)
        max_exposure = account_balance * risk_limits['max_portfolio_exposure']
        if total_exposure > max_exposure:
            violations.append(f"Total exposure exceeds limit ({risk_limits['max_portfolio_exposure']:.1%})")
    
    # Check maximum number of positions
    if 'max_positions' in risk_limits:
        if len(current_positions) >= risk_limits['max_positions']:
            violations.append(f"Maximum number of positions reached ({risk_limits['max_positions']})")
    
    return len(violations) == 0, violations


def calculate_correlation_risk(returns: pd.DataFrame, threshold: float = 0.7) -> Dict[str, List[str]]:
    """Identify highly correlated assets.
    
    Args:
        returns: DataFrame of asset returns
        threshold: Correlation threshold
        
    Returns:
        Dict: Highly correlated asset pairs
    """
    corr_matrix = returns.corr()
    high_corr_pairs = {}
    
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            asset1 = corr_matrix.columns[i]
            asset2 = corr_matrix.columns[j]
            correlation = corr_matrix.iloc[i, j]
            
            if abs(correlation) > threshold:
                if asset1 not in high_corr_pairs:
                    high_corr_pairs[asset1] = []
                high_corr_pairs[asset1].append(f"{asset2} ({correlation:.3f})")
    
    return high_corr_pairs