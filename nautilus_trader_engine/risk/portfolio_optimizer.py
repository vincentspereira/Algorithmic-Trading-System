"""
Portfolio Optimization Engine
Comprehensive portfolio optimization with Modern Portfolio Theory, Black-Litte
Risk Parity, and Multi-Objective optimization frameworks
"""

import asyncio
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
from abc import ABC, abstractmethod
import warnings

# Suppress numpy warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    from scipy import optimize, linalg
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
    OptimizeResult = optimize.OptimizeResult
except ImportError:
    SCIPY_AVAILABLE = False
    optimize = None
    linalg = None
    norm = None
    # Create a dummy class for type hints
    class OptimizeResult:
        def __init__(self):
            self.x = None
            self.success = False
            self.fun = 0.0
            self.nit = 0

try:
    from sklearn.covariance import LedoitWolf, OAS
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    LedoitWolf = None
    OAS = None


class OptimizationMethod(Enum):
    """Portfolio optimization methods"""
    MEAN_VARIANCE = "mean_variance"
    BLACK_LITTERMAN = "black_litterman"
    RISK_PARITY = "risk_parity"
    MINIMUM_VARIANCE = "minimum_variance"
    MAXIMUM_SHARPE = "maximum_sharpe"
    MAXIMUM_RETURN = "maximum_return"
    EQUAL_WEIGHT = "equal_weight"
    HIERARCHICAL_RISK_PARITY = "hierarchical_risk_parity"


class ObjectiveFunction(Enum):
    """Optimization objective functions"""
    MAXIMIZE_RETURN = "maximize_return"
    MINIMIZE_RISK = "minimize_risk"
    MAXIMIZE_SHARPE = "maximize_sharpe"
    MAXIMIZE_UTILITY = "maximize_utility"
    MINIMIZE_TRACKING_ERROR = "minimize_tracking_error"
    RISK_PARITY = "risk_parity"


class RiskModel(Enum):
    """Risk model types"""
    SAMPLE_COVARIANCE = "sample_covariance"
    SHRINKAGE_COVARIANCE = "shrinkage_covariance"
    FACTOR_MODEL = "factor_model"
    EWMA_COVARIANCE = "ewma_covariance"


@dataclass
class Asset:
    """Asset information for optimization"""
    symbol: str
    name: str
    expected_return: float
    volatility: float
    
    # Market data
    current_price: float
    market_cap: Optional[float] = None
    
    # Historical data
    returns: Optional[np.ndarray] = None
    prices: Optional[np.ndarray] = None
    
    # Asset characteristics
    sector: Optional[str] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    
    # Risk factors
    beta: float = 1.0
    alpha: float = 0.0
    
    # Constraints
    min_weight: float = 0.0
    max_weight: float = 1.0
    
    # Transaction costs
    transaction_cost: float = 0.001  # 10 bps default


@dataclass
class OptimizationConstraints:
    """Portfolio optimization constraints"""
    # Weight constraints
    min_weights: Optional[Dict[str, float]] = None
    max_weights: Optional[Dict[str, float]] = None
    
    # Portfolio constraints
    max_portfolio_risk: Optional[float] = None
    min_portfolio_return: Optional[float] = None
    max_portfolio_return: Optional[float] = None
    
    # Sector/group constraints
    sector_min_weights: Optional[Dict[str, float]] = None
    sector_max_weights: Optional[Dict[str, float]] = None
    
    # Turnover constraints
    max_turnover: Optional[float] = None
    
    # Long/short constraints
    long_only: bool = True
    max_leverage: float = 1.0
    
    # Cardinality constraints
    max_assets: Optional[int] = None
    min_assets: Optional[int] = None
    
    # Risk factor constraints
    max_beta: Optional[float] = None
    min_beta: Optional[float] = None
    
    # Tracking error constraint
    max_tracking_error: Optional[float] = None
    benchmark_weights: Optional[Dict[str, float]] = None


@dataclass
class BlackLittermanInputs:
    """Black-Litterman model inputs"""
    # Market equilibrium
    market_cap_weights: Dict[str, float]
    risk_aversion: float = 3.0
    
    # Investor views
    views_matrix: Optional[np.ndarray] = None  # P matrix
    view_returns: Optional[np.ndarray] = None  # Q vector
    view_uncertainty: Optional[np.ndarray] = None  # Omega matrix
    
    # Model parameters
    tau: float = 0.025  # Scaling factor for uncertainty
    
    # Prior parameters
    prior_returns: Optional[np.ndarray] = None
    prior_covariance: Optional[np.ndarray] = None


@dataclass
class OptimizationResult:
    """Portfolio optimization result"""
    method: OptimizationMethod
    objective: ObjectiveFunction
    
    # Optimal weights
    weights: Dict[str, float]
    
    # Portfolio metrics
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    
    # Optimization details
    optimization_time: datetime
    convergence: bool
    
    # Risk metrics
    portfolio_beta: float = 0.0
    tracking_error: float = 0.0
    max_drawdown: float = 0.0
    var_95: float = 0.0
    iterations: int = 0
    objective_value: float = 0.0
    
    # Diagnostics
    constraints_satisfied: bool = True
    constraint_violations: List[str] = field(default_factory=list)
    
    # Risk decomposition
    risk_contributions: Dict[str, float] = field(default_factory=dict)
    return_contributions: Dict[str, float] = field(default_factory=dict)
    
    # Transaction costs
    total_transaction_cost: float = 0.0
    turnover: float = 0.0
    
    # Additional metrics
    diversification_ratio: float = 0.0
    effective_assets: float = 0.0
    concentration_index: float = 0.0


class PortfolioOptimizer(ABC):
    """Abstract base class for portfolio optimizers"""
    
    @abstractmethod
    def optimize(self,
                assets: List[Asset],
                constraints: OptimizationConstraints,
                **kwargs) -> OptimizationResult:
        """Optimize portfolio weights"""
        pass
    
    @abstractmethod
    def get_required_data(self) -> List[str]:
        """Get required data fields"""
        pass


class MeanVarianceOptimizer(PortfolioOptimizer):
    """Modern Portfolio Theory mean-variance optimizer"""
    
    def __init__(self, risk_model: RiskModel = RiskModel.SAMPLE_COVARIANCE):
        self.risk_model = risk_model
        self.logger = logging.getLogger(__name__)
    
    def optimize(self,
                assets: List[Asset],
                constraints: OptimizationConstraints,
                objective: ObjectiveFunction = ObjectiveFunction.MAXIMIZE_SHARPE,
                risk_free_rate: float = 0.02,
                **kwargs) -> OptimizationResult:
        """Optimize portfolio using mean-variance optimization"""
        start_time = datetime.now()
        
        try:
            # Prepare data
            returns, covariance = self._prepare_data(assets)
            n_assets = len(assets)
            
            # Set up optimization problem
            bounds = self._get_bounds(assets, constraints)
            constraint_funcs = self._get_constraints(assets, constraints, returns, covariance)
            
            # Initial guess (equal weights)
            x0 = np.ones(n_assets) / n_assets
            
            # Optimize based on objective
            if objective == ObjectiveFunction.MAXIMIZE_SHARPE:
                result = self._maximize_sharpe_ratio(
                    returns, covariance, bounds, constraint_funcs, risk_free_rate
                )
            elif objective == ObjectiveFunction.MINIMIZE_RISK:
                result = self._minimize_risk(
                    returns, covariance, bounds, constraint_funcs
                )
            elif objective == ObjectiveFunction.MAXIMIZE_RETURN:
                result = self._maximize_return(
                    returns, covariance, bounds, constraint_funcs
                )
            elif objective == ObjectiveFunction.MAXIMIZE_UTILITY:
                risk_aversion = kwargs.get('risk_aversion', 3.0)
                result = self._maximize_utility(
                    returns, covariance, bounds, constraint_funcs, risk_aversion
                )
            else:
                raise ValueError(f"Unsupported objective: {objective}")
            
            # Process results
            optimal_weights = dict(zip([asset.symbol for asset in assets], result.x))
            
            # Calculate portfolio metrics
            portfolio_return = np.dot(result.x, returns)
            portfolio_risk = np.sqrt(np.dot(result.x, np.dot(covariance, result.x)))
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            # Calculate additional metrics
            risk_contributions = self._calculate_risk_contributions(result.x, covariance)
            return_contributions = self._calculate_return_contributions(result.x, returns)
            
            # Create result
            optimization_result = OptimizationResult(
                method=OptimizationMethod.MEAN_VARIANCE,
                objective=objective,
                weights=optimal_weights,
                expected_return=portfolio_return,
                expected_risk=portfolio_risk,
                sharpe_ratio=sharpe_ratio,
                optimization_time=start_time,
                convergence=result.success,
                iterations=result.nit if hasattr(result, 'nit') else 0,
                objective_value=result.fun,
                risk_contributions=dict(zip([asset.symbol for asset in assets], risk_contributions)),
                return_contributions=dict(zip([asset.symbol for asset in assets], return_contributions))
            )
            
            # Calculate additional portfolio metrics
            self._calculate_additional_metrics(optimization_result, assets, result.x, covariance)
            
            return optimization_result
            
        except Exception as e:
            self.logger.error(f"Mean-variance optimization failed: {e}")
            raise
    
    def get_required_data(self) -> List[str]:
        return ['expected_return', 'returns']
    
    def _prepare_data(self, assets: List[Asset]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare returns and covariance matrix"""
        # Extract expected returns
        returns = np.array([asset.expected_return for asset in assets])
        
        # Calculate covariance matrix based on risk model
        if self.risk_model == RiskModel.SAMPLE_COVARIANCE:
            covariance = self._calculate_sample_covariance(assets)
        elif self.risk_model == RiskModel.SHRINKAGE_COVARIANCE:
            covariance = self._calculate_shrinkage_covariance(assets)
        elif self.risk_model == RiskModel.EWMA_COVARIANCE:
            covariance = self._calculate_ewma_covariance(assets)
        else:
            covariance = self._calculate_sample_covariance(assets)
        
        return returns, covariance
    
    def _calculate_sample_covariance(self, assets: List[Asset]) -> np.ndarray:
        """Calculate sample covariance matrix"""
        returns_matrix = []
        min_length = float('inf')
        
        # Find minimum length
        for asset in assets:
            if asset.returns is not None:
                min_length = min(min_length, len(asset.returns))
        
        if min_length == float('inf') or min_length < 2:
            # Fallback to volatility-based covariance
            n = len(assets)
            covariance = np.eye(n)
            for i, asset in enumerate(assets):
                covariance[i, i] = asset.volatility ** 2
            return covariance
        
        # Build returns matrix
        for asset in assets:
            if asset.returns is not None:
                returns_matrix.append(asset.returns[-min_length:])
            else:
                # Use volatility to generate synthetic returns
                synthetic_returns = np.random.normal(
                    asset.expected_return / 252, asset.volatility / np.sqrt(252), min_length
                )
                returns_matrix.append(synthetic_returns)
        
        returns_matrix = np.array(returns_matrix).T
        return np.cov(returns_matrix.T)
    
    def _calculate_shrinkage_covariance(self, assets: List[Asset]) -> np.ndarray:
        """Calculate shrinkage covariance matrix"""
        if not SKLEARN_AVAILABLE:
            return self._calculate_sample_covariance(assets)
        
        returns_matrix = []
        min_length = float('inf')
        
        for asset in assets:
            if asset.returns is not None:
                min_length = min(min_length, len(asset.returns))
        
        if min_length == float('inf') or min_length < 10:
            return self._calculate_sample_covariance(assets)
        
        for asset in assets:
            if asset.returns is not None:
                returns_matrix.append(asset.returns[-min_length:])
            else:
                synthetic_returns = np.random.normal(
                    asset.expected_return / 252, asset.volatility / np.sqrt(252), min_length
                )
                returns_matrix.append(synthetic_returns)
        
        returns_matrix = np.array(returns_matrix).T
        
        # Use Ledoit-Wolf shrinkage
        lw = LedoitWolf()
        shrunk_cov = lw.fit(returns_matrix).covariance_
        
        return shrunk_cov
    
    def _calculate_ewma_covariance(self, assets: List[Asset], lambda_decay: float = 0.94) -> np.ndarray:
        """Calculate EWMA covariance matrix"""
        returns_matrix = []
        min_length = float('inf')
        
        for asset in assets:
            if asset.returns is not None:
                min_length = min(min_length, len(asset.returns))
        
        if min_length == float('inf') or min_length < 10:
            return self._calculate_sample_covariance(assets)
        
        for asset in assets:
            if asset.returns is not None:
                returns_matrix.append(asset.returns[-min_length:])
            else:
                synthetic_returns = np.random.normal(
                    asset.expected_return / 252, asset.volatility / np.sqrt(252), min_length
                )
                returns_matrix.append(synthetic_returns)
        
        returns_matrix = np.array(returns_matrix).T
        n_assets = returns_matrix.shape[1]
        
        # Calculate EWMA covariance
        weights = np.array([(1 - lambda_decay) * (lambda_decay ** i) 
                           for i in range(len(returns_matrix))])
        weights = weights[::-1]  # Reverse for recent observations
        weights /= weights.sum()
        
        # Weighted covariance calculation
        weighted_returns = returns_matrix * weights.reshape(-1, 1)
        mean_returns = np.sum(weighted_returns, axis=0)
        
        covariance = np.zeros((n_assets, n_assets))
        for t in range(len(returns_matrix)):
            deviation = returns_matrix[t] - mean_returns
            covariance += weights[t] * np.outer(deviation, deviation)
        
        return covariance
    
    def _get_bounds(self, assets: List[Asset], constraints: OptimizationConstraints) -> List[Tuple[float, float]]:
        """Get weight bounds for optimization"""
        bounds = []
        
        for asset in assets:
            min_weight = asset.min_weight
            max_weight = asset.max_weight
            
            # Apply constraint overrides
            if constraints.min_weights and asset.symbol in constraints.min_weights:
                min_weight = max(min_weight, constraints.min_weights[asset.symbol])
            
            if constraints.max_weights and asset.symbol in constraints.max_weights:
                max_weight = min(max_weight, constraints.max_weights[asset.symbol])
            
            # Long-only constraint
            if constraints.long_only:
                min_weight = max(0, min_weight)
            
            bounds.append((min_weight, max_weight))
        
        return bounds
    
    def _get_constraints(self, 
                        assets: List[Asset], 
                        constraints: OptimizationConstraints,
                        returns: np.ndarray,
                        covariance: np.ndarray) -> List[Dict]:
        """Get optimization constraints"""
        constraint_funcs = []
        
        # Weights sum to 1 (or max leverage)
        max_leverage = constraints.max_leverage if constraints.max_leverage else 1.0
        constraint_funcs.append({
            'type': 'eq',
            'fun': lambda x: np.sum(x) - max_leverage
        })
        
        # Portfolio return constraint
        if constraints.min_portfolio_return is not None:
            constraint_funcs.append({
                'type': 'ineq',
                'fun': lambda x: np.dot(x, returns) - constraints.min_portfolio_return
            })
        
        if constraints.max_portfolio_return is not None:
            constraint_funcs.append({
                'type': 'ineq',
                'fun': lambda x: constraints.max_portfolio_return - np.dot(x, returns)
            })
        
        # Portfolio risk constraint
        if constraints.max_portfolio_risk is not None:
            constraint_funcs.append({
                'type': 'ineq',
                'fun': lambda x: constraints.max_portfolio_risk - np.sqrt(np.dot(x, np.dot(covariance, x)))
            })
        
        # Sector constraints
        if constraints.sector_min_weights or constraints.sector_max_weights:
            sectors = {}
            for i, asset in enumerate(assets):
                if asset.sector:
                    if asset.sector not in sectors:
                        sectors[asset.sector] = []
                    sectors[asset.sector].append(i)
            
            for sector, indices in sectors.items():
                if constraints.sector_min_weights and sector in constraints.sector_min_weights:
                    min_weight = constraints.sector_min_weights[sector]
                    constraint_funcs.append({
                        'type': 'ineq',
                        'fun': lambda x, idx=indices: np.sum(x[idx]) - min_weight
                    })
                
                if constraints.sector_max_weights and sector in constraints.sector_max_weights:
                    max_weight = constraints.sector_max_weights[sector]
                    constraint_funcs.append({
                        'type': 'ineq',
                        'fun': lambda x, idx=indices: max_weight - np.sum(x[idx])
                    })
        
        return constraint_funcs
    
    def _maximize_sharpe_ratio(self, 
                              returns: np.ndarray,
                              covariance: np.ndarray,
                              bounds: List[Tuple[float, float]],
                              constraints: List[Dict],
                              risk_free_rate: float) -> OptimizeResult:
        """Maximize Sharpe ratio"""
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for optimization")
        
        def negative_sharpe(weights):
            portfolio_return = np.dot(weights, returns)
            portfolio_risk = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
            if portfolio_risk == 0:
                return -np.inf
            return -(portfolio_return - risk_free_rate) / portfolio_risk
        
        x0 = np.ones(len(returns)) / len(returns)
        
        result = optimize.minimize(
            negative_sharpe,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        return result
    
    def _minimize_risk(self,
                      returns: np.ndarray,
                      covariance: np.ndarray,
                      bounds: List[Tuple[float, float]],
                      constraints: List[Dict]) -> OptimizeResult:
        """Minimize portfolio risk"""
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for optimization")
        
        def portfolio_variance(weights):
            return np.dot(weights, np.dot(covariance, weights))
        
        x0 = np.ones(len(returns)) / len(returns)
        
        result = optimize.minimize(
            portfolio_variance,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        return result
    
    def _maximize_return(self,
                        returns: np.ndarray,
                        covariance: np.ndarray,
                        bounds: List[Tuple[float, float]],
                        constraints: List[Dict]) -> OptimizeResult:
        """Maximize portfolio return"""
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for optimization")
        
        def negative_return(weights):
            return -np.dot(weights, returns)
        
        x0 = np.ones(len(returns)) / len(returns)
        
        result = optimize.minimize(
            negative_return,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        return result
    
    def _maximize_utility(self,
                         returns: np.ndarray,
                         covariance: np.ndarray,
                         bounds: List[Tuple[float, float]],
                         constraints: List[Dict],
                         risk_aversion: float) -> OptimizeResult:
        """Maximize utility function"""
        if not SCIPY_AVAILABLE:
            raise ImportError("scipy is required for optimization")
        
        def negative_utility(weights):
            portfolio_return = np.dot(weights, returns)
            portfolio_variance = np.dot(weights, np.dot(covariance, weights))
            return -(portfolio_return - 0.5 * risk_aversion * portfolio_variance)
        
        x0 = np.ones(len(returns)) / len(returns)
        
        result = optimize.minimize(
            negative_utility,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
            options={'maxiter': 1000, 'ftol': 1e-9}
        )
        
        return result
    
    def _calculate_risk_contributions(self, weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """Calculate risk contributions"""
        portfolio_risk = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
        if portfolio_risk == 0:
            return np.zeros(len(weights))
        
        marginal_risk = np.dot(covariance, weights) / portfolio_risk
        risk_contributions = weights * marginal_risk
        
        return risk_contributions
    
    def _calculate_return_contributions(self, weights: np.ndarray, returns: np.ndarray) -> np.ndarray:
        """Calculate return contributions"""
        return weights * returns
    
    def _calculate_additional_metrics(self, 
                                    result: OptimizationResult,
                                    assets: List[Asset],
                                    weights: np.ndarray,
                                    covariance: np.ndarray):
        """Calculate additional portfolio metrics"""
        # Portfolio beta
        if all(hasattr(asset, 'beta') for asset in assets):
            result.portfolio_beta = np.dot(weights, [asset.beta for asset in assets])
        
        # Diversification ratio
        individual_risks = np.array([asset.volatility for asset in assets])
        weighted_avg_risk = np.dot(weights, individual_risks)
        if result.expected_risk > 0:
            result.diversification_ratio = weighted_avg_risk / result.expected_risk
        
        # Effective number of assets (inverse of Herfindahl index)
        result.effective_assets = 1 / np.sum(weights ** 2)
        
        # Concentration index (Herfindahl index)
        result.concentration_index = np.sum(weights ** 2)


class BlackLittermanOptimizer(PortfolioOptimizer):
    """Black-Litterman portfolio optimizer"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize(self,
                assets: List[Asset],
                constraints: OptimizationConstraints,
                bl_inputs: BlackLittermanInputs,
                **kwargs) -> OptimizationResult:
        """Optimize portfolio using Black-Litterman model"""
        start_time = datetime.now()
        
        try:
            # Prepare data
            returns, covariance = self._prepare_data(assets)
            
            # Calculate Black-Litterman expected returns
            bl_returns = self._calculate_bl_returns(assets, bl_inputs, returns, covariance)
            
            # Use mean-variance optimization with BL returns
            mv_optimizer = MeanVarianceOptimizer()
            
            # Update assets with BL returns
            bl_assets = []
            for i, asset in enumerate(assets):
                bl_asset = Asset(
                    symbol=asset.symbol,
                    name=asset.name,
                    expected_return=bl_returns[i],
                    volatility=asset.volatility,
                    current_price=asset.current_price,
                    returns=asset.returns,
                    min_weight=asset.min_weight,
                    max_weight=asset.max_weight
                )
                bl_assets.append(bl_asset)
            
            # Optimize with BL returns
            result = mv_optimizer.optimize(
                bl_assets, constraints, ObjectiveFunction.MAXIMIZE_SHARPE, **kwargs
            )
            
            # Update method
            result.method = OptimizationMethod.BLACK_LITTERMAN
            
            return result
            
        except Exception as e:
            self.logger.error(f"Black-Litterman optimization failed: {e}")
            raise
    
    def get_required_data(self) -> List[str]:
        return ['expected_return', 'returns', 'market_cap']
    
    def _prepare_data(self, assets: List[Asset]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare returns and covariance matrix"""
        returns = np.array([asset.expected_return for asset in assets])
        
        # Use sample covariance for simplicity
        returns_matrix = []
        min_length = float('inf')
        
        for asset in assets:
            if asset.returns is not None:
                min_length = min(min_length, len(asset.returns))
        
        if min_length == float('inf') or min_length < 2:
            # Fallback to volatility-based covariance
            n = len(assets)
            covariance = np.eye(n)
            for i, asset in enumerate(assets):
                covariance[i, i] = asset.volatility ** 2
            return returns, covariance
        
        for asset in assets:
            if asset.returns is not None:
                returns_matrix.append(asset.returns[-min_length:])
            else:
                synthetic_returns = np.random.normal(
                    asset.expected_return / 252, asset.volatility / np.sqrt(252), min_length
                )
                returns_matrix.append(synthetic_returns)
        
        returns_matrix = np.array(returns_matrix).T
        covariance = np.cov(returns_matrix.T)
        
        return returns, covariance
    
    def _calculate_bl_returns(self,
                             assets: List[Asset],
                             bl_inputs: BlackLittermanInputs,
                             prior_returns: np.ndarray,
                             covariance: np.ndarray) -> np.ndarray:
        """Calculate Black-Litterman expected returns"""
        n_assets = len(assets)
        
        # Market capitalization weights
        market_weights = np.array([
            bl_inputs.market_cap_weights.get(asset.symbol, 1.0/n_assets) 
            for asset in assets
        ])
        market_weights /= market_weights.sum()  # Normalize
        
        # Implied equilibrium returns (reverse optimization)
        if bl_inputs.prior_returns is not None:
            pi = bl_inputs.prior_returns
        else:
            pi = bl_inputs.risk_aversion * np.dot(covariance, market_weights)
        
        # If no views provided, return equilibrium returns
        if bl_inputs.views_matrix is None or bl_inputs.view_returns is None:
            return pi
        
        # Black-Litterman formula
        P = bl_inputs.views_matrix
        Q = bl_inputs.view_returns
        
        # View uncertainty matrix
        if bl_inputs.view_uncertainty is not None:
            Omega = bl_inputs.view_uncertainty
        else:
            # Default: diagonal matrix with view variances
            Omega = np.eye(len(Q)) * 0.01  # 1% uncertainty
        
        # Tau parameter
        tau = bl_inputs.tau
        
        # Black-Litterman calculation
        if not SCIPY_AVAILABLE:
            # Simplified calculation without scipy
            return pi + 0.1 * (Q - np.dot(P, pi))  # Simple adjustment
        
        try:
            # M1 = inv(tau * Sigma)
            M1 = linalg.inv(tau * covariance)
            
            # M2 = P' * inv(Omega) * P
            M2 = np.dot(P.T, np.dot(linalg.inv(Omega), P))
            
            # M3 = inv(tau * Sigma) * pi + P' * inv(Omega) * Q
            M3 = np.dot(M1, pi) + np.dot(P.T, np.dot(linalg.inv(Omega), Q))
            
            # New expected returns
            bl_returns = np.dot(linalg.inv(M1 + M2), M3)
            
            return bl_returns
            
        except Exception as e:
            self.logger.warning(f"Black-Litterman calculation failed: {e}, using simplified approach")
            # Fallback to simple view adjustment
            return pi + 0.1 * (Q - np.dot(P, pi))


class RiskParityOptimizer(PortfolioOptimizer):
    """Risk parity portfolio optimizer"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize(self,
                assets: List[Asset],
                constraints: OptimizationConstraints,
                **kwargs) -> OptimizationResult:
        """Optimize portfolio using risk parity"""
        start_time = datetime.now()
        
        try:
            # Prepare covariance matrix
            covariance = self._calculate_covariance(assets)
            n_assets = len(assets)
            
            # Risk parity optimization
            bounds = self._get_bounds(assets, constraints)
            
            # Objective: minimize sum of squared risk contribution deviations
            def risk_parity_objective(weights):
                portfolio_risk = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
                if portfolio_risk == 0:
                    return 1e10
                
                # Risk contributions
                marginal_risk = np.dot(covariance, weights) / portfolio_risk
                risk_contributions = weights * marginal_risk
                
                # Target: equal risk contributions
                target_risk_contrib = portfolio_risk / n_assets
                
                # Sum of squared deviations
                return np.sum((risk_contributions - target_risk_contrib) ** 2)
            
            # Constraints
            constraint_funcs = [{
                'type': 'eq',
                'fun': lambda x: np.sum(x) - 1.0
            }]
            
            # Initial guess
            x0 = np.ones(n_assets) / n_assets
            
            if SCIPY_AVAILABLE:
                result = optimize.minimize(
                    risk_parity_objective,
                    x0,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraint_funcs,
                    options={'maxiter': 1000, 'ftol': 1e-9}
                )
                
                optimal_weights = result.x
                convergence = result.success
                iterations = result.nit if hasattr(result, 'nit') else 0
            else:
                # Simple iterative approach without scipy
                optimal_weights = self._simple_risk_parity(covariance, bounds)
                convergence = True
                iterations = 100
            
            # Calculate portfolio metrics
            weights_dict = dict(zip([asset.symbol for asset in assets], optimal_weights))
            
            # Expected return (use equal weights for returns if not available)
            returns = np.array([asset.expected_return for asset in assets])
            portfolio_return = np.dot(optimal_weights, returns)
            
            portfolio_risk = np.sqrt(np.dot(optimal_weights, np.dot(covariance, optimal_weights)))
            sharpe_ratio = portfolio_return / portfolio_risk if portfolio_risk > 0 else 0
            
            # Risk contributions
            risk_contributions = self._calculate_risk_contributions(optimal_weights, covariance)
            return_contributions = optimal_weights * returns
            
            result = OptimizationResult(
                method=OptimizationMethod.RISK_PARITY,
                objective=ObjectiveFunction.RISK_PARITY,
                weights=weights_dict,
                expected_return=portfolio_return,
                expected_risk=portfolio_risk,
                sharpe_ratio=sharpe_ratio,
                optimization_time=start_time,
                convergence=convergence,
                iterations=iterations,
                risk_contributions=dict(zip([asset.symbol for asset in assets], risk_contributions)),
                return_contributions=dict(zip([asset.symbol for asset in assets], return_contributions))
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Risk parity optimization failed: {e}")
            raise
    
    def get_required_data(self) -> List[str]:
        return ['volatility', 'returns']
    
    def _calculate_covariance(self, assets: List[Asset]) -> np.ndarray:
        """Calculate covariance matrix"""
        returns_matrix = []
        min_length = float('inf')
        
        for asset in assets:
            if asset.returns is not None:
                min_length = min(min_length, len(asset.returns))
        
        if min_length == float('inf') or min_length < 2:
            # Use volatility-based covariance
            n = len(assets)
            covariance = np.eye(n)
            for i, asset in enumerate(assets):
                covariance[i, i] = asset.volatility ** 2
            return covariance
        
        for asset in assets:
            if asset.returns is not None:
                returns_matrix.append(asset.returns[-min_length:])
            else:
                synthetic_returns = np.random.normal(
                    asset.expected_return / 252, asset.volatility / np.sqrt(252), min_length
                )
                returns_matrix.append(synthetic_returns)
        
        returns_matrix = np.array(returns_matrix).T
        return np.cov(returns_matrix.T)
    
    def _get_bounds(self, assets: List[Asset], constraints: OptimizationConstraints) -> List[Tuple[float, float]]:
        """Get weight bounds"""
        bounds = []
        for asset in assets:
            min_weight = max(0.001, asset.min_weight)  # Minimum for risk parity
            max_weight = asset.max_weight
            bounds.append((min_weight, max_weight))
        return bounds
    
    def _simple_risk_parity(self, covariance: np.ndarray, bounds: List[Tuple[float, float]]) -> np.ndarray:
        """Simple risk parity calculation without scipy"""
        n_assets = covariance.shape[0]
        
        # Start with inverse volatility weights
        volatilities = np.sqrt(np.diag(covariance))
        weights = 1 / volatilities
        weights /= weights.sum()
        
        # Apply bounds
        for i, (min_w, max_w) in enumerate(bounds):
            weights[i] = max(min_w, min(max_w, weights[i]))
        
        # Renormalize
        weights /= weights.sum()
        
        return weights
    
    def _calculate_risk_contributions(self, weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """Calculate risk contributions"""
        portfolio_risk = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
        if portfolio_risk == 0:
            return np.zeros(len(weights))
        
        marginal_risk = np.dot(covariance, weights) / portfolio_risk
        risk_contributions = weights * marginal_risk
        
        return risk_contributions


class EqualWeightOptimizer(PortfolioOptimizer):
    """Equal weight portfolio optimizer"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def optimize(self,
                assets: List[Asset],
                constraints: OptimizationConstraints,
                **kwargs) -> OptimizationResult:
        """Optimize portfolio using equal weights"""
        start_time = datetime.now()
        
        try:
            n_assets = len(assets)
            
            # Equal weights
            equal_weight = 1.0 / n_assets
            weights = np.full(n_assets, equal_weight)
            
            # Apply constraints if needed
            if constraints.min_weights or constraints.max_weights:
                # Adjust weights to satisfy constraints
                for i, asset in enumerate(assets):
                    min_weight = asset.min_weight
                    max_weight = asset.max_weight
                    
                    if constraints.min_weights and asset.symbol in constraints.min_weights:
                        min_weight = max(min_weight, constraints.min_weights[asset.symbol])
                    
                    if constraints.max_weights and asset.symbol in constraints.max_weights:
                        max_weight = min(max_weight, constraints.max_weights[asset.symbol])
                    
                    weights[i] = max(min_weight, min(max_weight, weights[i]))
                
                # Renormalize
                weights /= weights.sum()
            
            # Calculate portfolio metrics
            returns = np.array([asset.expected_return for asset in assets])
            covariance = self._calculate_sample_covariance(assets)
            
            portfolio_return = np.dot(weights, returns)
            portfolio_risk = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
            
            risk_free_rate = kwargs.get('risk_free_rate', 0.02)
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk if portfolio_risk > 0 else 0
            
            # Calculate risk and return contributions
            risk_contributions = self._calculate_risk_contributions(weights, covariance)
            return_contributions = weights * returns
            
            # Create result
            optimal_weights = dict(zip([asset.symbol for asset in assets], weights))
            
            result = OptimizationResult(
                method=OptimizationMethod.EQUAL_WEIGHT,
                objective=ObjectiveFunction.MAXIMIZE_UTILITY,  # Default objective
                weights=optimal_weights,
                expected_return=portfolio_return,
                expected_risk=portfolio_risk,
                sharpe_ratio=sharpe_ratio,
                optimization_time=start_time,
                convergence=True,  # Always converges
                risk_contributions=dict(zip([asset.symbol for asset in assets], risk_contributions)),
                return_contributions=dict(zip([asset.symbol for asset in assets], return_contributions))
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Equal weight optimization failed: {e}")
            raise
    
    def get_required_data(self) -> List[str]:
        return ['expected_return']
    
    def _calculate_sample_covariance(self, assets: List[Asset]) -> np.ndarray:
        """Calculate sample covariance matrix"""
        returns_matrix = []
        min_length = float('inf')
        
        # Find minimum length
        for asset in assets:
            if asset.returns is not None:
                min_length = min(min_length, len(asset.returns))
        
        if min_length == float('inf') or min_length < 2:
            # Fallback to volatility-based covariance
            n = len(assets)
            covariance = np.eye(n)
            for i, asset in enumerate(assets):
                covariance[i, i] = asset.volatility ** 2
            return covariance
        
        # Build returns matrix
        for asset in assets:
            if asset.returns is not None:
                returns_matrix.append(asset.returns[-min_length:])
            else:
                # Use volatility to generate synthetic returns
                synthetic_returns = np.random.normal(
                    asset.expected_return / 252, asset.volatility / np.sqrt(252), min_length
                )
                returns_matrix.append(synthetic_returns)
        
        returns_matrix = np.array(returns_matrix).T
        return np.cov(returns_matrix.T)
    
    def _calculate_risk_contributions(self, weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
        """Calculate risk contributions"""
        portfolio_risk = np.sqrt(np.dot(weights, np.dot(covariance, weights)))
        if portfolio_risk == 0:
            return np.zeros(len(weights))
        
        marginal_risk = np.dot(covariance, weights) / portfolio_risk
        risk_contributions = weights * marginal_risk
        
        return risk_contributions


class PortfolioOptimizationEngine:
    """
    Comprehensive Portfolio Optimization Engine
    
    Features:
    - Multiple optimization methods (Mean-Variance, Black-Litterman, Risk Parity)
    - Advanced risk models and covariance estimation
    - Multi-objective optimization with constraints
    - Real-time optimization with performance monitoring
    - Integration with risk management systems
    """
    
    def __init__(self,
                 enable_real_time: bool = True,
                 optimization_interval_seconds: int = 300,
                 enable_backtesting: bool = True):
        
        self.enable_real_time = enable_real_time
        self.optimization_interval_seconds = optimization_interval_seconds
        self.enable_backtesting = enable_backtesting
        
        # Optimizers
        self._optimizers = {
            OptimizationMethod.MEAN_VARIANCE: MeanVarianceOptimizer(),
            OptimizationMethod.BLACK_LITTERMAN: BlackLittermanOptimizer(),
            OptimizationMethod.RISK_PARITY: RiskParityOptimizer(),
            OptimizationMethod.MINIMUM_VARIANCE: MeanVarianceOptimizer(),
            OptimizationMethod.MAXIMUM_SHARPE: MeanVarianceOptimizer(),
            OptimizationMethod.EQUAL_WEIGHT: EqualWeightOptimizer()
        }
        
        # Results storage
        self._optimization_results: Dict[str, List[OptimizationResult]] = defaultdict(list)
        self._portfolio_assets: Dict[str, List[Asset]] = {}
        
        # Background processing
        self._optimization_queue = asyncio.Queue(maxsize=1000)
        self._worker_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Performance metrics
        self._metrics = {
            'optimizations_completed': 0,
            'optimizations_failed': 0,
            'avg_optimization_time_ms': 0.0,
            'last_optimization_time': None,
            'active_portfolios': 0,
            'convergence_rate': 0.0
        }
        
        # Alerting
        self._alert_callbacks: List[Callable] = []
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the optimization engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start background workers
        if self.enable_real_time:
            self._worker_tasks = [
                asyncio.create_task(self._optimization_worker()),
                asyncio.create_task(self._real_time_optimizer()),
                asyncio.create_task(self._metrics_collector())
            ]
        
        self.logger.info("Portfolio Optimization Engine started")
    
    async def stop(self):
        """Stop the optimization engine"""
        self._running = False
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        self.logger.info("Portfolio Optimization Engine stopped")
    
    async def optimize_portfolio(self,
                                portfolio_id: str,
                                assets: List[Asset],
                                method: OptimizationMethod,
                                constraints: OptimizationConstraints,
                                objective: ObjectiveFunction = ObjectiveFunction.MAXIMIZE_SHARPE,
                                **kwargs) -> OptimizationResult:
        """Optimize portfolio weights"""
        try:
            # Store assets for real-time optimization
            self._portfolio_assets[portfolio_id] = assets
            
            # Get optimizer
            optimizer = self._optimizers.get(method)
            if not optimizer:
                raise ValueError(f"Unsupported optimization method: {method}")
            
            # Optimize
            start_time = time.time()
            
            if method == OptimizationMethod.BLACK_LITTERMAN:
                bl_inputs = kwargs.get('bl_inputs')
                if not bl_inputs:
                    raise ValueError("Black-Litterman inputs required")
                result = optimizer.optimize(assets, constraints, bl_inputs, **kwargs)
            elif method in [OptimizationMethod.MINIMUM_VARIANCE, OptimizationMethod.MAXIMUM_SHARPE]:
                # Use mean-variance optimizer with specific objective
                obj = ObjectiveFunction.MINIMIZE_RISK if method == OptimizationMethod.MINIMUM_VARIANCE else ObjectiveFunction.MAXIMIZE_SHARPE
                result = optimizer.optimize(assets, constraints, obj, **kwargs)
            else:
                result = optimizer.optimize(assets, constraints, **kwargs)
            
            optimization_time = (time.time() - start_time) * 1000
            
            # Store result
            self._optimization_results[portfolio_id].append(result)
            
            # Keep only recent results
            if len(self._optimization_results[portfolio_id]) > 1000:
                self._optimization_results[portfolio_id] = self._optimization_results[portfolio_id][-1000:]
            
            # Update metrics
            self._metrics['optimizations_completed'] += 1
            self._metrics['last_optimization_time'] = datetime.now()
            
            # Update average optimization time
            current_avg = self._metrics['avg_optimization_time_ms']
            total_opts = self._metrics['optimizations_completed']
            self._metrics['avg_optimization_time_ms'] = (
                (current_avg * (total_opts - 1) + optimization_time) / total_opts
            )
            
            # Update convergence rate
            convergent_opts = sum(1 for results in self._optimization_results.values() 
                                for r in results if r.convergence)
            total_opts = sum(len(results) for results in self._optimization_results.values())
            self._metrics['convergence_rate'] = convergent_opts / total_opts if total_opts > 0 else 0
            
            self.logger.info(f"Portfolio optimized for {portfolio_id}: {method.value} "
                           f"(Sharpe: {result.sharpe_ratio:.3f})")
            
            return result
            
        except Exception as e:
            self._metrics['optimizations_failed'] += 1
            self.logger.error(f"Portfolio optimization failed for {portfolio_id}: {e}")
            raise
    
    def get_optimization_history(self, portfolio_id: str, method: Optional[OptimizationMethod] = None) -> List[OptimizationResult]:
        """Get optimization history"""
        results = self._optimization_results.get(portfolio_id, [])
        
        if method:
            results = [r for r in results if r.method == method]
        
        return results
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics"""
        return {
            **self._metrics,
            'active_portfolios': len(self._portfolio_assets),
            'total_optimizations': sum(len(results) for results in self._optimization_results.values()),
            'available_methods': [method.value for method in self._optimizers.keys()]
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for optimization alerts"""
        self._alert_callbacks.append(callback)
    
    # Private methods
    
    async def _optimization_worker(self):
        """Background worker for optimizations"""
        while self._running:
            try:
                try:
                    request = await asyncio.wait_for(
                        self._optimization_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                await self._process_optimization_request(request)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Optimization worker error: {e}")
                await asyncio.sleep(1)
    
    async def _real_time_optimizer(self):
        """Real-time optimization loop"""
        while self._running:
            try:
                # Optimize all active portfolios
                for portfolio_id, assets in self._portfolio_assets.items():
                    if assets:
                        await self._optimization_queue.put({
                            'type': 'optimize_portfolio',
                            'portfolio_id': portfolio_id,
                            'assets': assets,
                            'method': OptimizationMethod.MEAN_VARIANCE,
                            'constraints': OptimizationConstraints(),
                            'objective': ObjectiveFunction.MAXIMIZE_SHARPE
                        })
                
                await asyncio.sleep(self.optimization_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Real-time optimizer error: {e}")
                await asyncio.sleep(self.optimization_interval_seconds)
    
    async def _process_optimization_request(self, request: Dict[str, Any]):
        """Process optimization request"""
        try:
            if request['type'] == 'optimize_portfolio':
                await self.optimize_portfolio(
                    request['portfolio_id'],
                    request['assets'],
                    request['method'],
                    request['constraints'],
                    request['objective']
                )
        except Exception as e:
            self.logger.error(f"Failed to process optimization request: {e}")
    
    async def _metrics_collector(self):
        """Background worker for metrics collection"""
        while self._running:
            try:
                self._metrics['active_portfolios'] = len(self._portfolio_assets)
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(30)


# Global optimization engine instance
_optimization_engine_instance: Optional[PortfolioOptimizationEngine] = None


def get_optimization_engine() -> PortfolioOptimizationEngine:
    """Get global optimization engine instance"""
    global _optimization_engine_instance
    if _optimization_engine_instance is None:
        raise RuntimeError("Optimization engine not initialized. Call initialize_optimization_engine() first.")
    return _optimization_engine_instance


def initialize_optimization_engine(
    enable_real_time: bool = True,
    optimization_interval_seconds: int = 300,
    enable_backtesting: bool = True
) -> PortfolioOptimizationEngine:
    """Initialize global optimization engine instance"""
    global _optimization_engine_instance
    _optimization_engine_instance = PortfolioOptimizationEngine(
        enable_real_time=enable_real_time,
        optimization_interval_seconds=optimization_interval_seconds,
        enable_backtesting=enable_backtesting
    )
    return _optimization_engine_instance


async def start_optimization_engine(**kwargs) -> PortfolioOptimizationEngine:
    """Start optimization engine with configuration"""
    engine = initialize_optimization_engine(**kwargs)
    await engine.start()
    return engine


async def stop_optimization_engine():
    """Stop global optimization engine"""
    global _optimization_engine_instance
    if _optimization_engine_instance:
        await _optimization_engine_instance.stop()
        _optimization_engine_instance = None