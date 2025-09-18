"""Common utility functions for strategy operations.

This module provides shared utility functions that can be used across
multiple trading strategies to improve code reuse and maintainability.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def validate_ohlcv_data(data: pd.DataFrame) -> bool:
    """Validate OHLCV data format and completeness.
    
    Args:
        data: DataFrame with OHLCV columns
        
    Returns:
        bool: True if data is valid, False otherwise
    """
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    
    if not all(col in data.columns for col in required_columns):
        logger.error(f"Missing required columns. Expected: {required_columns}")
        return False
        
    if data.empty:
        logger.error("Data is empty")
        return False
        
    # Check for NaN values
    if data[required_columns].isnull().any().any():
        logger.warning("Data contains NaN values")
        
    # Validate price relationships
    invalid_rows = (
        (data['high'] < data['low']) |
        (data['high'] < data['open']) |
        (data['high'] < data['close']) |
        (data['low'] > data['open']) |
        (data['low'] > data['close'])
    )
    
    if invalid_rows.any():
        logger.error(f"Invalid price relationships found in {invalid_rows.sum()} rows")
        return False
        
    return True


def calculate_returns(prices: pd.Series, method: str = 'simple') -> pd.Series:
    """Calculate returns from price series.
    
    Args:
        prices: Price series
        method: 'simple' or 'log' returns
        
    Returns:
        pd.Series: Calculated returns
    """
    if method == 'simple':
        return prices.pct_change()
    elif method == 'log':
        return np.log(prices / prices.shift(1))
    else:
        raise ValueError("Method must be 'simple' or 'log'")


def calculate_volatility(returns: pd.Series, window: int = 20, annualize: bool = True) -> pd.Series:
    """Calculate rolling volatility.
    
    Args:
        returns: Return series
        window: Rolling window size
        annualize: Whether to annualize volatility
        
    Returns:
        pd.Series: Rolling volatility
    """
    vol = returns.rolling(window=window).std()
    
    if annualize:
        # Assume 252 trading days per year
        vol = vol * np.sqrt(252)
        
    return vol


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02, 
                          periods_per_year: int = 252) -> float:
    """Calculate Sharpe ratio.
    
    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year
        
    Returns:
        float: Sharpe ratio
    """
    excess_returns = returns - (risk_free_rate / periods_per_year)
    return excess_returns.mean() / excess_returns.std() * np.sqrt(periods_per_year)


def calculate_max_drawdown(prices: pd.Series) -> Tuple[float, datetime, datetime]:
    """Calculate maximum drawdown.
    
    Args:
        prices: Price series
        
    Returns:
        Tuple: (max_drawdown, start_date, end_date)
    """
    cumulative = (1 + prices.pct_change()).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    
    max_dd = drawdown.min()
    end_date = drawdown.idxmin()
    
    # Find start of drawdown period
    start_date = running_max.loc[:end_date].idxmax()
    
    return max_dd, start_date, end_date


def normalize_data(data: pd.Series, method: str = 'zscore') -> pd.Series:
    """Normalize data series.
    
    Args:
        data: Data series to normalize
        method: 'zscore', 'minmax', or 'robust'
        
    Returns:
        pd.Series: Normalized data
    """
    if method == 'zscore':
        return (data - data.mean()) / data.std()
    elif method == 'minmax':
        return (data - data.min()) / (data.max() - data.min())
    elif method == 'robust':
        median = data.median()
        mad = (data - median).abs().median()
        return (data - median) / mad
    else:
        raise ValueError("Method must be 'zscore', 'minmax', or 'robust'")


def resample_data(data: pd.DataFrame, timeframe: str, 
                 agg_methods: Optional[Dict[str, str]] = None) -> pd.DataFrame:
    """Resample OHLCV data to different timeframe.
    
    Args:
        data: OHLCV DataFrame
        timeframe: Target timeframe (e.g., '1H', '1D')
        agg_methods: Custom aggregation methods for columns
        
    Returns:
        pd.DataFrame: Resampled data
    """
    if agg_methods is None:
        agg_methods = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
    
    return data.resample(timeframe).agg(agg_methods)


def detect_outliers(data: pd.Series, method: str = 'iqr', 
                   threshold: float = 1.5) -> pd.Series:
    """Detect outliers in data series.
    
    Args:
        data: Data series
        method: 'iqr' or 'zscore'
        threshold: Threshold for outlier detection
        
    Returns:
        pd.Series: Boolean series indicating outliers
    """
    if method == 'iqr':
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - threshold * IQR
        upper_bound = Q3 + threshold * IQR
        return (data < lower_bound) | (data > upper_bound)
    elif method == 'zscore':
        z_scores = np.abs((data - data.mean()) / data.std())
        return z_scores > threshold
    else:
        raise ValueError("Method must be 'iqr' or 'zscore'")


def calculate_correlation_matrix(data: pd.DataFrame, method: str = 'pearson') -> pd.DataFrame:
    """Calculate correlation matrix.
    
    Args:
        data: DataFrame with multiple series
        method: 'pearson', 'spearman', or 'kendall'
        
    Returns:
        pd.DataFrame: Correlation matrix
    """
    return data.corr(method=method)


def format_performance_metrics(metrics: Dict[str, float]) -> str:
    """Format performance metrics for display.
    
    Args:
        metrics: Dictionary of performance metrics
        
    Returns:
        str: Formatted metrics string
    """
    formatted = []
    for key, value in metrics.items():
        if isinstance(value, float):
            if 'ratio' in key.lower() or 'return' in key.lower():
                formatted.append(f"{key}: {value:.4f}")
            elif 'drawdown' in key.lower():
                formatted.append(f"{key}: {value:.2%}")
            else:
                formatted.append(f"{key}: {value:.2f}")
        else:
            formatted.append(f"{key}: {value}")
    
    return "\n".join(formatted)