"""Shared Utility Functions for Trading Strategies

This module provides common utility functions that can be used across all trading strategies
to enhance code reusability and maintain consistency.

Author: AI Assistant
Date: 2024-12-15
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for position sizing"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class PositionSizeResult:
    """Result of position sizing calculation"""
    shares: int
    dollar_amount: float
    risk_amount: float
    risk_percentage: float
    max_loss: float


@dataclass
class RiskMetrics:
    """Risk metrics for a strategy or position"""
    var_95: float
    var_99: float
    expected_shortfall: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float


class StrategyUtilities:
    """Collection of utility functions for trading strategies"""
    
    @staticmethod
    def calculate_position_size(
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        risk_percentage: float = 0.02,
        max_position_size: Optional[float] = None
    ) -> PositionSizeResult:
        """
        Calculate position size based on risk management rules.
        
        Args:
            account_balance: Total account balance
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            risk_percentage: Percentage of account to risk (default 2%)
            max_position_size: Maximum position size limit
            
        Returns:
            PositionSizeResult with calculated position details
        """
        try:
            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_loss_price)
            
            if risk_per_share == 0:
                logger.warning("Risk per share is zero, using minimum position size")
                return PositionSizeResult(
                    shares=1,
                    dollar_amount=entry_price,
                    risk_amount=0,
                    risk_percentage=0,
                    max_loss=0
                )
            
            # Calculate maximum risk amount
            max_risk_amount = account_balance * risk_percentage
            
            # Calculate shares based on risk
            shares = int(max_risk_amount / risk_per_share)
            
            # Apply maximum position size limit if specified
            if max_position_size:
                max_shares = int(max_position_size / entry_price)
                shares = min(shares, max_shares)
            
            # Ensure minimum of 1 share
            shares = max(1, shares)
            
            # Calculate actual amounts
            dollar_amount = shares * entry_price
            actual_risk_amount = shares * risk_per_share
            actual_risk_percentage = actual_risk_amount / account_balance
            
            return PositionSizeResult(
                shares=shares,
                dollar_amount=dollar_amount,
                risk_amount=actual_risk_amount,
                risk_percentage=actual_risk_percentage,
                max_loss=actual_risk_amount
            )
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return PositionSizeResult(
                shares=1,
                dollar_amount=entry_price,
                risk_amount=0,
                risk_percentage=0,
                max_loss=0
            )
    
    @staticmethod
    def calculate_stop_loss(
        entry_price: float,
        atr: float,
        multiplier: float = 2.0,
        position_side: str = "long"
    ) -> float:
        """
        Calculate stop loss price based on ATR.
        
        Args:
            entry_price: Entry price for the position
            atr: Average True Range value
            multiplier: ATR multiplier for stop loss distance
            position_side: "long" or "short"
            
        Returns:
            Stop loss price
        """
        try:
            stop_distance = atr * multiplier
            
            if position_side.lower() == "long":
                return entry_price - stop_distance
            else:
                return entry_price + stop_distance
                
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            return entry_price * 0.95 if position_side.lower() == "long" else entry_price * 1.05
    
    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        stop_loss_price: float,
        risk_reward_ratio: float = 2.0,
        position_side: str = "long"
    ) -> float:
        """
        Calculate take profit price based on risk-reward ratio.
        
        Args:
            entry_price: Entry price for the position
            stop_loss_price: Stop loss price
            risk_reward_ratio: Risk to reward ratio
            position_side: "long" or "short"
            
        Returns:
            Take profit price
        """
        try:
            risk_amount = abs(entry_price - stop_loss_price)
            reward_amount = risk_amount * risk_reward_ratio
            
            if position_side.lower() == "long":
                return entry_price + reward_amount
            else:
                return entry_price - reward_amount
                
        except Exception as e:
            logger.error(f"Error calculating take profit: {e}")
            return entry_price * 1.04 if position_side.lower() == "long" else entry_price * 0.96
    
    @staticmethod
    def calculate_risk_metrics(
        returns: pd.Series,
        risk_free_rate: float = 0.02
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics for a return series.
        
        Args:
            returns: Series of returns
            risk_free_rate: Risk-free rate for Sharpe ratio calculation
            
        Returns:
            RiskMetrics object with calculated metrics
        """
        try:
            if len(returns) == 0:
                return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
            
            # VaR calculations
            var_95 = np.percentile(returns, 5)
            var_99 = np.percentile(returns, 1)
            
            # Expected Shortfall (Conditional VaR)
            expected_shortfall = returns[returns <= var_95].mean()
            
            # Maximum Drawdown
            cumulative_returns = (1 + returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdown.min()
            
            # Sharpe Ratio
            excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
            
            # Sortino Ratio
            downside_returns = returns[returns < 0]
            downside_std = downside_returns.std() if len(downside_returns) > 0 else 0
            sortino_ratio = excess_returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
            
            # Calmar Ratio
            annual_return = returns.mean() * 252
            calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            return RiskMetrics(
                var_95=var_95,
                var_99=var_99,
                expected_shortfall=expected_shortfall,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                sortino_ratio=sortino_ratio,
                calmar_ratio=calmar_ratio
            )
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(0, 0, 0, 0, 0, 0, 0)
    
    @staticmethod
    def normalize_price_data(
        data: pd.DataFrame,
        method: str = "z_score"
    ) -> pd.DataFrame:
        """
        Normalize price data using various methods.
        
        Args:
            data: DataFrame with price data
            method: Normalization method ("z_score", "min_max", "robust")
            
        Returns:
            Normalized DataFrame
        """
        try:
            if method == "z_score":
                return (data - data.mean()) / data.std()
            elif method == "min_max":
                return (data - data.min()) / (data.max() - data.min())
            elif method == "robust":
                median = data.median()
                mad = (data - median).abs().median()
                return (data - median) / mad
            else:
                logger.warning(f"Unknown normalization method: {method}")
                return data
                
        except Exception as e:
            logger.error(f"Error normalizing data: {e}")
            return data
    
    @staticmethod
    def detect_outliers(
        data: pd.Series,
        method: str = "iqr",
        threshold: float = 1.5
    ) -> pd.Series:
        """
        Detect outliers in a data series.
        
        Args:
            data: Data series to analyze
            method: Detection method ("iqr", "z_score", "modified_z_score")
            threshold: Threshold for outlier detection
            
        Returns:
            Boolean series indicating outliers
        """
        try:
            if method == "iqr":
                Q1 = data.quantile(0.25)
                Q3 = data.quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - threshold * IQR
                upper_bound = Q3 + threshold * IQR
                return (data < lower_bound) | (data > upper_bound)
                
            elif method == "z_score":
                z_scores = np.abs((data - data.mean()) / data.std())
                return z_scores > threshold
                
            elif method == "modified_z_score":
                median = data.median()
                mad = (data - median).abs().median()
                modified_z_scores = 0.6745 * (data - median) / mad
                return np.abs(modified_z_scores) > threshold
                
            else:
                logger.warning(f"Unknown outlier detection method: {method}")
                return pd.Series([False] * len(data), index=data.index)
                
        except Exception as e:
            logger.error(f"Error detecting outliers: {e}")
            return pd.Series([False] * len(data), index=data.index)
    
    @staticmethod
    def calculate_correlation_matrix(
        data: pd.DataFrame,
        method: str = "pearson"
    ) -> pd.DataFrame:
        """
        Calculate correlation matrix for multiple assets.
        
        Args:
            data: DataFrame with asset price data
            method: Correlation method ("pearson", "spearman", "kendall")
            
        Returns:
            Correlation matrix
        """
        try:
            return data.corr(method=method)
        except Exception as e:
            logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def format_currency(amount: float, currency: str = "USD") -> str:
        """
        Format amount as currency string.
        
        Args:
            amount: Amount to format
            currency: Currency code
            
        Returns:
            Formatted currency string
        """
        try:
            if currency == "USD":
                return f"${amount:,.2f}"
            else:
                return f"{amount:,.2f} {currency}"
        except Exception as e:
            logger.error(f"Error formatting currency: {e}")
            return str(amount)
    
    @staticmethod
    def calculate_portfolio_weights(
        returns: pd.DataFrame,
        method: str = "equal_weight"
    ) -> pd.Series:
        """
        Calculate portfolio weights using various methods.
        
        Args:
            returns: DataFrame of asset returns
            method: Weighting method ("equal_weight", "inverse_volatility", "risk_parity")
            
        Returns:
            Series of portfolio weights
        """
        try:
            n_assets = len(returns.columns)
            
            if method == "equal_weight":
                return pd.Series([1.0 / n_assets] * n_assets, index=returns.columns)
                
            elif method == "inverse_volatility":
                volatilities = returns.std()
                inv_vol = 1 / volatilities
                weights = inv_vol / inv_vol.sum()
                return weights
                
            elif method == "risk_parity":
                # Simplified risk parity (equal risk contribution)
                volatilities = returns.std()
                inv_vol = 1 / volatilities
                weights = inv_vol / inv_vol.sum()
                return weights
                
            else:
                logger.warning(f"Unknown weighting method: {method}")
                return pd.Series([1.0 / n_assets] * n_assets, index=returns.columns)
                
        except Exception as e:
            logger.error(f"Error calculating portfolio weights: {e}")
            return pd.Series([1.0 / len(returns.columns)] * len(returns.columns), index=returns.columns)


class DataValidation:
    """Data validation utilities for strategies"""
    
    @staticmethod
    def validate_price_data(data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Validate price data for common issues.
        
        Args:
            data: DataFrame with price data
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Check for missing data
            if data.isnull().any().any():
                issues.append("Missing data detected")
            
            # Check for negative prices
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            if (data[numeric_cols] < 0).any().any():
                issues.append("Negative prices detected")
            
            # Check for zero prices
            if (data[numeric_cols] == 0).any().any():
                issues.append("Zero prices detected")
            
            # Check for extreme price movements (>50% in one period)
            for col in numeric_cols:
                pct_change = data[col].pct_change().abs()
                if (pct_change > 0.5).any():
                    issues.append(f"Extreme price movement detected in {col}")
            
            # Check data frequency consistency
            if hasattr(data.index, 'freq') and data.index.freq is None:
                time_diffs = data.index.to_series().diff().dropna()
                if time_diffs.nunique() > 1:
                    issues.append("Inconsistent data frequency detected")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Error validating price data: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    @staticmethod
    def validate_strategy_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate strategy configuration parameters.
        
        Args:
            config: Strategy configuration dictionary
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Required fields
            required_fields = ['symbol', 'timeframe', 'risk_percentage']
            for field in required_fields:
                if field not in config:
                    issues.append(f"Missing required field: {field}")
            
            # Validate risk percentage
            if 'risk_percentage' in config:
                risk_pct = config['risk_percentage']
                if not isinstance(risk_pct, (int, float)) or risk_pct <= 0 or risk_pct > 1:
                    issues.append("Risk percentage must be between 0 and 1")
            
            # Validate timeframe
            if 'timeframe' in config:
                valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
                if config['timeframe'] not in valid_timeframes:
                    issues.append(f"Invalid timeframe. Must be one of: {valid_timeframes}")
            
            return len(issues) == 0, issues
            
        except Exception as e:
            logger.error(f"Error validating strategy config: {e}")
            return False, [f"Validation error: {str(e)}"]


# Export main classes and functions
__all__ = [
    'StrategyUtilities',
    'DataValidation',
    'RiskLevel',
    'PositionSizeResult',
    'RiskMetrics'
]