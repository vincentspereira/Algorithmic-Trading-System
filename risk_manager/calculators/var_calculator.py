"""Value at Risk (VaR) Calculator

Implements multiple VaR calculation methods including Historical Simulation,
Parametric (Variance-Covariance), Monte Carlo, and Cornish-Fisher expansion.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import asyncio
import math
import warnings
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union, Any
import logging

import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf, EmpiricalCovariance

from ..models.risk_models import (
    VaRMethod, VaRResult, RiskMetricType
)

# Configure logging
logger = logging.getLogger(__name__)

class VaRCalculator:
    """Value at Risk calculator with multiple methodologies"""
    
    def __init__(self, 
                 default_confidence_level: float = 0.95,
                 default_time_horizon: int = 1,
                 lookback_period: int = 252):
        """
        Initialize VaR calculator
        
        Args:
            default_confidence_level: Default confidence level (0.95 = 95%)
            default_time_horizon: Default time horizon in days
            lookback_period: Historical data lookback period in days
        """
        self.default_confidence_level = default_confidence_level
        self.default_time_horizon = default_time_horizon
        self.lookback_period = lookback_period
        
        # Cache for covariance matrices
        self._covariance_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour
        
    async def calculate_var(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        portfolio_weights: Optional[np.ndarray] = None,
        method: VaRMethod = VaRMethod.HISTORICAL,
        confidence_level: Optional[float] = None,
        time_horizon: Optional[int] = None,
        **kwargs
    ) -> VaRResult:
        """
        Calculate Value at Risk using specified method
        
        Args:
            returns: Historical returns (Series for single asset, DataFrame for portfolio)
            portfolio_weights: Portfolio weights (required for DataFrame input)
            method: VaR calculation method
            confidence_level: Confidence level (default: 0.95)
            time_horizon: Time horizon in days (default: 1)
            **kwargs: Additional method-specific parameters
            
        Returns:
            VaRResult object with VaR calculations
        """
        confidence_level = confidence_level or self.default_confidence_level
        time_horizon = time_horizon or self.default_time_horizon
        
        try:
            # Validate inputs
            self._validate_inputs(returns, portfolio_weights, confidence_level)
            
            # Calculate portfolio returns if needed
            if isinstance(returns, pd.DataFrame):
                if portfolio_weights is None:
                    raise ValueError("Portfolio weights required for DataFrame input")
                portfolio_returns = (returns * portfolio_weights).sum(axis=1)
            else:
                portfolio_returns = returns
                
            # Remove NaN values
            portfolio_returns = portfolio_returns.dropna()
            
            if len(portfolio_returns) < 30:
                logger.warning(f"Insufficient data points: {len(portfolio_returns)}")
                
            # Calculate VaR based on method
            if method == VaRMethod.HISTORICAL:
                result = await self._calculate_historical_var(
                    portfolio_returns, confidence_level, time_horizon, **kwargs
                )
            elif method == VaRMethod.PARAMETRIC:
                result = await self._calculate_parametric_var(
                    portfolio_returns, confidence_level, time_horizon, **kwargs
                )
            elif method == VaRMethod.MONTE_CARLO:
                result = await self._calculate_monte_carlo_var(
                    portfolio_returns, confidence_level, time_horizon, **kwargs
                )
            elif method == VaRMethod.CORNISH_FISHER:
                result = await self._calculate_cornish_fisher_var(
                    portfolio_returns, confidence_level, time_horizon, **kwargs
                )
            else:
                raise ValueError(f"Unsupported VaR method: {method}")
                
            # Add correlation matrix if portfolio
            if isinstance(returns, pd.DataFrame) and len(returns.columns) > 1:
                result.correlation_matrix = returns.corr().values
                
            return result
            
        except Exception as e:
            logger.error(f"VaR calculation failed: {str(e)}")
            # Return default result on error
            return VaRResult(
                method=method,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_amount=0.0,
                var_percentage=0.0,
                metadata={"error": str(e)}
            )
    
    async def _calculate_historical_var(
        self,
        returns: pd.Series,
        confidence_level: float,
        time_horizon: int,
        **kwargs
    ) -> VaRResult:
        """Calculate Historical Simulation VaR"""
        
        # Scale returns for time horizon
        scaled_returns = returns * math.sqrt(time_horizon)
        
        # Calculate percentile
        alpha = 1 - confidence_level
        var_percentile = np.percentile(scaled_returns, alpha * 100)
        
        # VaR is the negative of the percentile (loss)
        var_amount = -var_percentile
        
        # Calculate CVaR (Expected Shortfall)
        tail_returns = scaled_returns[scaled_returns <= var_percentile]
        cvar_amount = -tail_returns.mean() if len(tail_returns) > 0 else var_amount
        
        # Calculate percentages (assuming portfolio value of 1)
        var_percentage = var_amount * 100
        cvar_percentage = cvar_amount * 100
        
        return VaRResult(
            method=VaRMethod.HISTORICAL,
            confidence_level=confidence_level,
            time_horizon=time_horizon,
            var_amount=var_amount,
            var_percentage=var_percentage,
            cvar_amount=cvar_amount,
            cvar_percentage=cvar_percentage,
            expected_shortfall=cvar_amount,
            volatility=returns.std(),
            metadata={
                "sample_size": len(returns),
                "percentile_value": var_percentile,
                "tail_observations": len(tail_returns)
            }
        )
    
    async def _calculate_parametric_var(
        self,
        returns: pd.Series,
        confidence_level: float,
        time_horizon: int,
        **kwargs
    ) -> VaRResult:
        """Calculate Parametric (Variance-Covariance) VaR"""
        
        # Calculate mean and standard deviation
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Get z-score for confidence level
        alpha = 1 - confidence_level
        z_score = stats.norm.ppf(alpha)
        
        # Scale for time horizon
        scaled_mean = mean_return * time_horizon
        scaled_std = std_return * math.sqrt(time_horizon)
        
        # Calculate VaR
        var_amount = -(scaled_mean + z_score * scaled_std)
        
        # Calculate CVaR for normal distribution
        phi_z = stats.norm.pdf(z_score)
        cvar_amount = -(scaled_mean - (scaled_std * phi_z / alpha))
        
        # Calculate percentages
        var_percentage = var_amount * 100
        cvar_percentage = cvar_amount * 100
        
        return VaRResult(
            method=VaRMethod.PARAMETRIC,
            confidence_level=confidence_level,
            time_horizon=time_horizon,
            var_amount=var_amount,
            var_percentage=var_percentage,
            cvar_amount=cvar_amount,
            cvar_percentage=cvar_percentage,
            expected_shortfall=cvar_amount,
            volatility=std_return,
            metadata={
                "mean_return": mean_return,
                "std_return": std_return,
                "z_score": z_score,
                "assumption": "normal_distribution"
            }
        )
    
    async def _calculate_monte_carlo_var(
        self,
        returns: pd.Series,
        confidence_level: float,
        time_horizon: int,
        num_simulations: int = 10000,
        **kwargs
    ) -> VaRResult:
        """Calculate Monte Carlo VaR"""
        
        # Estimate parameters from historical data
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Generate random scenarios
        np.random.seed(42)  # For reproducibility
        random_returns = np.random.normal(
            mean_return * time_horizon,
            std_return * math.sqrt(time_horizon),
            num_simulations
        )
        
        # Calculate VaR and CVaR
        alpha = 1 - confidence_level
        var_percentile = np.percentile(random_returns, alpha * 100)
        var_amount = -var_percentile
        
        # CVaR calculation
        tail_returns = random_returns[random_returns <= var_percentile]
        cvar_amount = -tail_returns.mean() if len(tail_returns) > 0 else var_amount
        
        # Calculate percentages
        var_percentage = var_amount * 100
        cvar_percentage = cvar_amount * 100
        
        return VaRResult(
            method=VaRMethod.MONTE_CARLO,
            confidence_level=confidence_level,
            time_horizon=time_horizon,
            var_amount=var_amount,
            var_percentage=var_percentage,
            cvar_amount=cvar_amount,
            cvar_percentage=cvar_percentage,
            expected_shortfall=cvar_amount,
            volatility=std_return,
            metadata={
                "num_simulations": num_simulations,
                "mean_return": mean_return,
                "std_return": std_return,
                "percentile_value": var_percentile
            }
        )
    
    async def _calculate_cornish_fisher_var(
        self,
        returns: pd.Series,
        confidence_level: float,
        time_horizon: int,
        **kwargs
    ) -> VaRResult:
        """Calculate Cornish-Fisher VaR (accounts for skewness and kurtosis)"""
        
        # Calculate moments
        mean_return = returns.mean()
        std_return = returns.std()
        skewness = returns.skew()
        kurtosis = returns.kurtosis()  # Excess kurtosis
        
        # Get standard normal quantile
        alpha = 1 - confidence_level
        z = stats.norm.ppf(alpha)
        
        # Cornish-Fisher expansion
        cf_quantile = (
            z +
            (z**2 - 1) * skewness / 6 +
            (z**3 - 3*z) * kurtosis / 24 -
            (2*z**3 - 5*z) * skewness**2 / 36
        )
        
        # Scale for time horizon
        scaled_mean = mean_return * time_horizon
        scaled_std = std_return * math.sqrt(time_horizon)
        
        # Calculate VaR
        var_amount = -(scaled_mean + cf_quantile * scaled_std)
        
        # Approximate CVaR (using modified Cornish-Fisher)
        # This is a simplified approximation
        cvar_adjustment = 1 + skewness * (1 + z) / 6 + kurtosis * (1 + 2*z) / 24
        cvar_amount = var_amount * cvar_adjustment
        
        # Calculate percentages
        var_percentage = var_amount * 100
        cvar_percentage = cvar_amount * 100
        
        return VaRResult(
            method=VaRMethod.CORNISH_FISHER,
            confidence_level=confidence_level,
            time_horizon=time_horizon,
            var_amount=var_amount,
            var_percentage=var_percentage,
            cvar_amount=cvar_amount,
            cvar_percentage=cvar_percentage,
            expected_shortfall=cvar_amount,
            volatility=std_return,
            metadata={
                "mean_return": mean_return,
                "std_return": std_return,
                "skewness": skewness,
                "kurtosis": kurtosis,
                "z_score": z,
                "cf_quantile": cf_quantile
            }
        )
    
    async def calculate_portfolio_var(
        self,
        returns_df: pd.DataFrame,
        weights: np.ndarray,
        method: VaRMethod = VaRMethod.PARAMETRIC,
        confidence_level: Optional[float] = None,
        time_horizon: Optional[int] = None,
        use_shrinkage: bool = True
    ) -> VaRResult:
        """Calculate portfolio VaR using covariance matrix"""
        
        confidence_level = confidence_level or self.default_confidence_level
        time_horizon = time_horizon or self.default_time_horizon
        
        try:
            # Calculate or retrieve covariance matrix
            if use_shrinkage:
                cov_estimator = LedoitWolf()
                cov_matrix = cov_estimator.fit(returns_df.dropna()).covariance_
            else:
                cov_matrix = returns_df.cov().values
            
            # Calculate portfolio variance
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            portfolio_std = math.sqrt(portfolio_variance)
            
            # Calculate portfolio mean return
            mean_returns = returns_df.mean().values
            portfolio_mean = np.dot(weights, mean_returns)
            
            # Scale for time horizon
            scaled_mean = portfolio_mean * time_horizon
            scaled_std = portfolio_std * math.sqrt(time_horizon)
            
            # Calculate VaR based on method
            if method == VaRMethod.PARAMETRIC:
                alpha = 1 - confidence_level
                z_score = stats.norm.ppf(alpha)
                var_amount = -(scaled_mean + z_score * scaled_std)
                
                # CVaR for normal distribution
                phi_z = stats.norm.pdf(z_score)
                cvar_amount = -(scaled_mean - (scaled_std * phi_z / alpha))
                
            else:
                # For other methods, calculate portfolio returns first
                portfolio_returns = (returns_df * weights).sum(axis=1)
                return await self.calculate_var(
                    portfolio_returns, None, method, confidence_level, time_horizon
                )
            
            var_percentage = var_amount * 100
            cvar_percentage = cvar_amount * 100
            
            return VaRResult(
                method=method,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_amount=var_amount,
                var_percentage=var_percentage,
                cvar_amount=cvar_amount,
                cvar_percentage=cvar_percentage,
                expected_shortfall=cvar_amount,
                volatility=portfolio_std,
                correlation_matrix=returns_df.corr().values,
                metadata={
                    "portfolio_mean": portfolio_mean,
                    "portfolio_std": portfolio_std,
                    "portfolio_variance": portfolio_variance,
                    "weights": weights.tolist(),
                    "use_shrinkage": use_shrinkage
                }
            )
            
        except Exception as e:
            logger.error(f"Portfolio VaR calculation failed: {str(e)}")
            return VaRResult(
                method=method,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_amount=0.0,
                var_percentage=0.0,
                metadata={"error": str(e)}
            )
    
    def _validate_inputs(
        self,
        returns: Union[pd.Series, pd.DataFrame],
        portfolio_weights: Optional[np.ndarray],
        confidence_level: float
    ) -> None:
        """Validate input parameters"""
        
        if confidence_level <= 0 or confidence_level >= 1:
            raise ValueError("Confidence level must be between 0 and 1")
        
        if isinstance(returns, pd.DataFrame) and portfolio_weights is not None:
            if len(portfolio_weights) != len(returns.columns):
                raise ValueError("Portfolio weights length must match number of assets")
            
            if not np.isclose(np.sum(portfolio_weights), 1.0, rtol=1e-3):
                logger.warning("Portfolio weights do not sum to 1.0")
        
        if returns.empty:
            raise ValueError("Returns data cannot be empty")
    
    async def calculate_component_var(
        self,
        returns_df: pd.DataFrame,
        weights: np.ndarray,
        confidence_level: Optional[float] = None
    ) -> Dict[str, float]:
        """Calculate component VaR for each asset in portfolio"""
        
        confidence_level = confidence_level or self.default_confidence_level
        
        # Calculate portfolio VaR
        portfolio_var = await self.calculate_portfolio_var(
            returns_df, weights, VaRMethod.PARAMETRIC, confidence_level
        )
        
        # Calculate marginal VaR for each component
        component_vars = {}
        
        for i, asset in enumerate(returns_df.columns):
            # Small perturbation
            epsilon = 0.001
            perturbed_weights = weights.copy()
            perturbed_weights[i] += epsilon
            
            # Renormalize weights
            perturbed_weights = perturbed_weights / perturbed_weights.sum()
            
            # Calculate perturbed VaR
            perturbed_var = await self.calculate_portfolio_var(
                returns_df, perturbed_weights, VaRMethod.PARAMETRIC, confidence_level
            )
            
            # Marginal VaR
            marginal_var = (perturbed_var.var_amount - portfolio_var.var_amount) / epsilon
            
            # Component VaR
            component_vars[asset] = weights[i] * marginal_var
        
        return component_vars
    
    def get_var_summary(self, var_results: List[VaRResult]) -> Dict[str, Any]:
        """Generate summary statistics from multiple VaR calculations"""
        
        if not var_results:
            return {}
        
        var_amounts = [result.var_amount for result in var_results]
        var_percentages = [result.var_percentage for result in var_results]
        
        return {
            "count": len(var_results),
            "mean_var_amount": np.mean(var_amounts),
            "median_var_amount": np.median(var_amounts),
            "std_var_amount": np.std(var_amounts),
            "min_var_amount": np.min(var_amounts),
            "max_var_amount": np.max(var_amounts),
            "mean_var_percentage": np.mean(var_percentages),
            "methods_used": list(set(result.method for result in var_results)),
            "confidence_levels": list(set(result.confidence_level for result in var_results))
        }