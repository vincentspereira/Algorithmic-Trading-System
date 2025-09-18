import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
from datetime import datetime

# Import the configuration classes from portfolio_management
from .portfolio_management import OptimizationConfig, OptimizationMethod, RiskMeasure

# PyPortfolioOpt imports
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    from pypfopt.hierarchical_portfolio import HRPOpt
    from pypfopt.black_litterman import BlackLittermanModel
    from pypfopt.risk_models import CovarianceShrinkage
    from pypfopt.expected_returns import mean_historical_return
    from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
    from pypfopt.objective_functions import L2_reg
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False

# Riskfolio-Lib imports
try:
    import riskfolio as rp
    RISKFOLIO_AVAILABLE = True
except ImportError:
    RISKFOLIO_AVAILABLE = False

# Additional optimization libraries
try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False

try:
    import scipy.optimize as sco
    from scipy import stats
    from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
    from scipy.spatial.distance import squareform
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

logger = logging.getLogger(__name__)

class PyPortfolioOptEngine:
    """PyPortfolioOpt optimization engine with advanced features"""
    
    def __init__(self):
        """Initialize PyPortfolioOpt engine"""
        if not PYPFOPT_AVAILABLE:
            raise ImportError("PyPortfolioOpt is required but not available")
        
        logger.info("PyPortfolioOpt engine initialized")
    
    def optimize(self, 
                 returns_data: pd.DataFrame, 
                 config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """
        Optimize portfolio using PyPortfolioOpt
        
        Args:
            returns_data: Historical returns data
            config: Optimization configuration
            
        Returns:
            Dictionary with optimization results
        """
        try:
            # Calculate expected returns and covariance matrix
            mu = expected_returns.mean_historical_return(returns_data.T, frequency=252)
            
            # Use different covariance estimation methods
            if config.risk_measure == RiskMeasure.VARIANCE:
                S = risk_models.sample_cov(returns_data.T, frequency=252)
            else:
                # Use shrinkage for more robust estimation
                S = CovarianceShrinkage(returns_data.T).ledoit_wolf()
            
            # Route to specific optimization method
            if config.method == OptimizationMethod.MEAN_VARIANCE:
                return self._mean_variance_optimization(mu, S, config)
            elif config.method == OptimizationMethod.BLACK_LITTERMAN:
                return self._black_litterman_optimization(returns_data, mu, S, config)
            elif config.method == OptimizationMethod.HIERARCHICAL_RISK_PARITY:
                return self._hierarchical_risk_parity(returns_data, config)
            elif config.method == OptimizationMethod.MINIMUM_VARIANCE:
                return self._minimum_variance_optimization(S, config)
            elif config.method == OptimizationMethod.MAXIMUM_SHARPE:
                return self._maximum_sharpe_optimization(mu, S, config)
            elif config.method == OptimizationMethod.MAXIMUM_QUADRATIC_UTILITY:
                return self._maximum_quadratic_utility(mu, S, config)
            else:
                raise ValueError(f"Optimization method {config.method} not supported by PyPortfolioOpt engine")
                
        except Exception as e:
            logger.error(f"PyPortfolioOpt optimization failed: {str(e)}")
            return {
                'weights': pd.Series(1.0/len(returns_data.columns), index=returns_data.columns),
                'method': config.method.value,
                'optimization_status': 'failed',
                'error': str(e)
            }
    
    def _mean_variance_optimization(self, 
                                  mu: pd.Series, 
                                  S: pd.DataFrame, 
                                  config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Mean-variance optimization"""
        ef = EfficientFrontier(mu, S)
        
        # Add constraints
        ef.add_constraint(lambda w: w >= config.min_weight)
        ef.add_constraint(lambda w: w <= config.max_weight)
        
        # Add L2 regularization to prevent extreme weights
        ef.add_objective(L2_reg, gamma=0.1)
        
        if config.target_return is not None:
            # Optimize for target return
            weights = ef.efficient_return(config.target_return)
        else:
            # Optimize for maximum Sharpe ratio
            weights = ef.max_sharpe(risk_free_rate=config.risk_free_rate)
        
        # Clean weights (remove tiny positions)
        cleaned_weights = ef.clean_weights(cutoff=0.001)
        
        # Calculate performance
        performance = ef.portfolio_performance(risk_free_rate=config.risk_free_rate, verbose=False)
        
        return {
            'weights': pd.Series(cleaned_weights),
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': performance[0],
            'volatility': performance[1],
            'sharpe_ratio': performance[2],
            'raw_weights': pd.Series(weights),
            'efficient_frontier': ef
        }
    
    def _black_litterman_optimization(self, 
                                    returns_data: pd.DataFrame,
                                    mu: pd.Series, 
                                    S: pd.DataFrame, 
                                    config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Black-Litterman optimization"""
        # Market capitalization weights (equal weight as proxy)
        market_caps = pd.Series(1.0, index=returns_data.columns)
        
        # Create Black-Litterman model
        bl = BlackLittermanModel(S, pi=mu, market_caps=market_caps)
        
        # Add views if provided
        if config.black_litterman_views and config.black_litterman_confidence:
            views_matrix = []
            views_returns = []
            confidences = []
            
            for asset, view_return in config.black_litterman_views.items():
                if asset in returns_data.columns:
                    view_vector = [0] * len(returns_data.columns)
                    view_vector[returns_data.columns.get_loc(asset)] = 1
                    views_matrix.append(view_vector)
                    views_returns.append(view_return)
                    confidences.append(config.black_litterman_confidence.get(asset, 0.5))
            
            if views_matrix:
                P = np.array(views_matrix)
                Q = np.array(views_returns)
                omega = np.diag(1.0 / np.array(confidences))
                
                bl.bl_views(P, Q, omega)
        
        # Get posterior estimates
        ret_bl = bl.bl_returns()
        S_bl = bl.bl_cov()
        
        # Optimize using Black-Litterman estimates
        ef = EfficientFrontier(ret_bl, S_bl)
        ef.add_constraint(lambda w: w >= config.min_weight)
        ef.add_constraint(lambda w: w <= config.max_weight)
        
        weights = ef.max_sharpe(risk_free_rate=config.risk_free_rate)
        cleaned_weights = ef.clean_weights(cutoff=0.001)
        
        performance = ef.portfolio_performance(risk_free_rate=config.risk_free_rate, verbose=False)
        
        return {
            'weights': pd.Series(cleaned_weights),
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': performance[0],
            'volatility': performance[1],
            'sharpe_ratio': performance[2],
            'bl_returns': ret_bl,
            'bl_cov': S_bl,
            'views_applied': len(config.black_litterman_views) if config.black_litterman_views else 0
        }
    
    def _hierarchical_risk_parity(self, 
                                returns_data: pd.DataFrame, 
                                config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Hierarchical Risk Parity optimization"""
        hrp = HRPOpt(returns_data.T)
        weights = hrp.optimize()
        
        # Calculate performance metrics
        portfolio_return = (returns_data * pd.Series(weights)).sum(axis=1).mean() * 252
        portfolio_vol = (returns_data * pd.Series(weights)).sum(axis=1).std() * np.sqrt(252)
        sharpe_ratio = (portfolio_return - config.risk_free_rate) / portfolio_vol if portfolio_vol > 0 else 0
        
        return {
            'weights': pd.Series(weights),
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': portfolio_return,
            'volatility': portfolio_vol,
            'sharpe_ratio': sharpe_ratio,
            'clustering_info': hrp.clusters
        }
    
    def _minimum_variance_optimization(self, 
                                     S: pd.DataFrame, 
                                     config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Minimum variance optimization"""
        ef = EfficientFrontier(None, S, weight_bounds=(config.min_weight, config.max_weight))
        weights = ef.min_volatility()
        cleaned_weights = ef.clean_weights(cutoff=0.001)
        
        # Calculate performance (without expected returns)
        portfolio_vol = np.sqrt(np.dot(pd.Series(weights), np.dot(S, pd.Series(weights))))
        
        return {
            'weights': pd.Series(cleaned_weights),
            'method': config.method.value,
            'optimization_status': 'completed',
            'volatility': portfolio_vol,
            'raw_weights': pd.Series(weights)
        }
    
    def _maximum_sharpe_optimization(self, 
                                   mu: pd.Series, 
                                   S: pd.DataFrame, 
                                   config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Maximum Sharpe ratio optimization"""
        ef = EfficientFrontier(mu, S, weight_bounds=(config.min_weight, config.max_weight))
        weights = ef.max_sharpe(risk_free_rate=config.risk_free_rate)
        cleaned_weights = ef.clean_weights(cutoff=0.001)
        
        performance = ef.portfolio_performance(risk_free_rate=config.risk_free_rate, verbose=False)
        
        return {
            'weights': pd.Series(cleaned_weights),
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': performance[0],
            'volatility': performance[1],
            'sharpe_ratio': performance[2]
        }
    
    def _maximum_quadratic_utility(self, 
                                 mu: pd.Series, 
                                 S: pd.DataFrame, 
                                 config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Maximum quadratic utility optimization"""
        ef = EfficientFrontier(mu, S, weight_bounds=(config.min_weight, config.max_weight))
        weights = ef.max_quadratic_utility(risk_aversion=config.gamma)
        cleaned_weights = ef.clean_weights(cutoff=0.001)
        
        performance = ef.portfolio_performance(risk_free_rate=config.risk_free_rate, verbose=False)
        
        return {
            'weights': pd.Series(cleaned_weights),
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': performance[0],
            'volatility': performance[1],
            'sharpe_ratio': performance[2],
            'risk_aversion': config.gamma
        }

class RiskfolioEngine:
    """Riskfolio-Lib optimization engine for advanced risk management"""
    
    def __init__(self):
        """Initialize Riskfolio engine"""
        if not RISKFOLIO_AVAILABLE:
            raise ImportError("Riskfolio-Lib is required but not available")
        
        logger.info("Riskfolio-Lib engine initialized")
    
    def optimize(self, 
                 returns_data: pd.DataFrame, 
                 config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """
        Optimize portfolio using Riskfolio-Lib
        
        Args:
            returns_data: Historical returns data
            config: Optimization configuration
            
        Returns:
            Dictionary with optimization results
        """
        try:
            # Create portfolio object
            port = rp.Portfolio(returns=returns_data)
            
            # Calculate assets statistics
            port.assets_stats(method_mu='hist', method_cov='hist')
            
            # Route to specific optimization method
            if config.method == OptimizationMethod.CVAR_OPTIMIZATION:
                return self._cvar_optimization(port, config)
            elif config.method == OptimizationMethod.WORST_CASE_OPTIMIZATION:
                return self._worst_case_optimization(port, config)
            elif config.method == OptimizationMethod.HIERARCHICAL_CLUSTERING:
                return self._hierarchical_clustering_optimization(port, config)
            elif config.method == OptimizationMethod.RISK_PARITY:
                return self._risk_parity_optimization(port, config)
            else:
                # Fallback to mean-variance with Riskfolio
                return self._riskfolio_mean_variance(port, config)
                
        except Exception as e:
            logger.error(f"Riskfolio optimization failed: {str(e)}")
            return {
                'weights': pd.Series(1.0/len(returns_data.columns), index=returns_data.columns),
                'method': config.method.value,
                'optimization_status': 'failed',
                'error': str(e)
            }
    
    def _cvar_optimization(self, 
                          port: 'rp.Portfolio', 
                          config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """CVaR optimization using Riskfolio-Lib"""
        # Set portfolio constraints
        port.lowerret = config.target_return if config.target_return else port.mu.mean().iloc[0]
        port.upperret = float('inf')
        
        # Optimize portfolio
        weights = port.optimization(
            model='Classic',
            rm=config.risk_measure.value,
            obj='MinRisk',
            rf=config.risk_free_rate,
            l=0,  # No regularization
            hist=True
        )
        
        if weights is None:
            raise ValueError("CVaR optimization failed to converge")
        
        # Calculate performance metrics
        ret = port.mu @ weights
        risk = rp.RiskFunctions.CVaR_Hist(port.returns, weights, alpha=config.alpha)
        
        return {
            'weights': weights.iloc[:, 0],
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': ret.iloc[0, 0] * 252,
            'cvar': risk,
            'alpha': config.alpha
        }
    
    def _worst_case_optimization(self, 
                               port: 'rp.Portfolio', 
                               config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Worst-case optimization"""
        weights = port.optimization(
            model='Classic',
            rm='WR',  # Worst Realization
            obj='MinRisk',
            rf=config.risk_free_rate,
            l=0,
            hist=True
        )
        
        if weights is None:
            raise ValueError("Worst-case optimization failed to converge")
        
        ret = port.mu @ weights
        worst_case = port.returns @ weights
        worst_return = worst_case.min()
        
        return {
            'weights': weights.iloc[:, 0],
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': ret.iloc[0, 0] * 252,
            'worst_case_return': worst_return.iloc[0],
            'worst_case_annual': worst_return.iloc[0] * 252
        }
    
    def _hierarchical_clustering_optimization(self, 
                                            port: 'rp.Portfolio', 
                                            config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Hierarchical clustering optimization"""
        # Use Hierarchical Risk Parity with clustering
        weights = port.optimization(
            model='HRP',
            codependence='pearson',
            rm='MV',  # Mean Variance for risk measure
            rf=config.risk_free_rate,
            linkage='ward',
            max_k=10,
            leaf_order=True
        )
        
        if weights is None:
            raise ValueError("Hierarchical clustering optimization failed")
        
        ret = port.mu @ weights
        vol = np.sqrt(weights.T @ port.cov @ weights)
        
        return {
            'weights': weights.iloc[:, 0],
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': ret.iloc[0, 0] * 252,
            'volatility': vol.iloc[0, 0] * np.sqrt(252),
            'clustering_method': 'hierarchical_risk_parity'
        }
    
    def _risk_parity_optimization(self, 
                                port: 'rp.Portfolio', 
                                config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Risk parity optimization"""
        weights = port.optimization(
            model='Classic',
            rm='MV',
            obj='ERC',  # Equal Risk Contribution
            rf=config.risk_free_rate,
            l=0,
            hist=True
        )
        
        if weights is None:
            raise ValueError("Risk parity optimization failed to converge")
        
        ret = port.mu @ weights
        vol = np.sqrt(weights.T @ port.cov @ weights)
        
        # Calculate risk contributions
        risk_contributions = rp.RiskFunctions.Risk_Contribution(
            weights, port.cov, rm='MV'
        )
        
        return {
            'weights': weights.iloc[:, 0],
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': ret.iloc[0, 0] * 252,
            'volatility': vol.iloc[0, 0] * np.sqrt(252),
            'risk_contributions': risk_contributions.iloc[:, 0]
        }
    
    def _riskfolio_mean_variance(self, 
                               port: 'rp.Portfolio', 
                               config: OptimizationConfig) -> Dict[str, Union[pd.Series, Dict, Any]]:
        """Mean-variance optimization using Riskfolio-Lib"""
        if config.target_return:
            # Optimize for target return
            port.lowerret = config.target_return
            obj = 'MinRisk'
        else:
            # Optimize for maximum Sharpe ratio
            obj = 'Sharpe'
        
        weights = port.optimization(
            model='Classic',
            rm='MV',
            obj=obj,
            rf=config.risk_free_rate,
            l=0,
            hist=True
        )
        
        if weights is None:
            raise ValueError("Mean-variance optimization failed to converge")
        
        ret = port.mu @ weights
        vol = np.sqrt(weights.T @ port.cov @ weights)
        sharpe = (ret.iloc[0, 0] - config.risk_free_rate/252) / vol.iloc[0, 0]
        
        return {
            'weights': weights.iloc[:, 0],
            'method': config.method.value,
            'optimization_status': 'completed',
            'expected_return': ret.iloc[0, 0] * 252,
            'volatility': vol.iloc[0, 0] * np.sqrt(252),
            'sharpe_ratio': sharpe * np.sqrt(252)
        }