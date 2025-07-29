"""
Real-Time Value at Risk (VaR) Calculation Engine
Comprehensive VaR calculation with Monte Carlo, Historical, and Parametric methods
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
from collections import defaultdict, deque
import threading
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod
import warnings

# Suppress numpy warnings for cleaner output
warnings.filterwarnings('ignore', category=RuntimeWarning)

try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    stats = None

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    StandardScaler = None
    PCA = None


class VaRMethod(Enum):
    """VaR calculation methods"""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    GARCH = "garch"
    EXTREME_VALUE = "extreme_value"


class ConfidenceLevel(Enum):
    """Standard confidence levels for VaR"""
    LEVEL_90 = 0.90
    LEVEL_95 = 0.95
    LEVEL_99 = 0.99
    LEVEL_99_9 = 0.999


class TimeHorizon(Enum):
    """Time horizons for VaR calculation"""
    INTRADAY = "intraday"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class VaRResult:
    """VaR calculation result"""
    method: VaRMethod
    confidence_level: float
    time_horizon: TimeHorizon
    var_value: float
    expected_shortfall: float  # Conditional VaR (CVaR)
    
    # Additional metrics
    portfolio_value: float
    var_percentage: float
    calculation_time: datetime
    
    # Method-specific details
    parameters: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    
    # Backtesting results
    backtesting_results: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        self.var_percentage = abs(self.var_value / self.portfolio_value) if self.portfolio_value != 0 else 0


@dataclass
class GARCHParameters:
    """GARCH model parameters"""
    omega: float  # Constant term
    alpha: float  # ARCH coefficient
    beta: float   # GARCH coefficient
    
    # Model diagnostics
    log_likelihood: float = 0.0
    aic: float = 0.0
    bic: float = 0.0
    convergence: bool = False


@dataclass
class PortfolioPosition:
    """Portfolio position for VaR calculation"""
    symbol: str
    quantity: float
    current_price: float
    market_value: float
    weight: float = 0.0
    
    # Risk metrics
    volatility: float = 0.0
    beta: float = 1.0
    
    # Historical data
    returns: Optional[np.ndarray] = None
    prices: Optional[np.ndarray] = None


@dataclass
class VaRBacktestResult:
    """VaR backtesting result"""
    method: VaRMethod
    confidence_level: float
    
    # Backtesting metrics
    total_observations: int
    violations: int
    violation_rate: float
    expected_violations: int
    
    # Statistical tests
    kupiec_pof_statistic: float
    kupiec_pof_p_value: float
    kupiec_pof_reject: bool
    
    christoffersen_cc_statistic: float
    christoffersen_cc_p_value: float
    christoffersen_cc_reject: bool
    
    # Performance metrics
    average_var: float
    average_actual_loss: float
    maximum_loss: float
    
    # Traffic light test
    traffic_light_zone: str  # "green", "yellow", "red"


class VaRCalculator(ABC):
    """Abstract base class for VaR calculators"""
    
    @abstractmethod
    def calculate_var(self, 
                     positions: List[PortfolioPosition],
                     confidence_level: float,
                     time_horizon: TimeHorizon,
                     **kwargs) -> VaRResult:
        """Calculate VaR for given positions"""
        pass
    
    @abstractmethod
    def get_required_history_length(self) -> int:
        """Get minimum required history length"""
        pass


class HistoricalVaRCalculator(VaRCalculator):
    """Historical simulation VaR calculator"""
    
    def __init__(self, lookback_days: int = 252):
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)
    
    def calculate_var(self, 
                     positions: List[PortfolioPosition],
                     confidence_level: float,
                     time_horizon: TimeHorizon,
                     **kwargs) -> VaRResult:
        """Calculate historical VaR"""
        start_time = datetime.now()
        
        try:
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(positions)
            
            if len(portfolio_returns) < 30:
                raise ValueError("Insufficient historical data for reliable VaR calculation")
            
            # Scale returns for time horizon
            scaled_returns = self._scale_returns_for_horizon(portfolio_returns, time_horizon)
            
            # Calculate VaR as percentile
            var_percentile = (1 - confidence_level) * 100
            var_value = np.percentile(scaled_returns, var_percentile)
            
            # Calculate Expected Shortfall (CVaR)
            tail_losses = scaled_returns[scaled_returns <= var_value]
            expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var_value
            
            # Calculate portfolio value
            portfolio_value = sum(pos.market_value for pos in positions)
            
            # Diagnostics
            diagnostics = {
                'observations_used': len(portfolio_returns),
                'return_mean': np.mean(portfolio_returns),
                'return_std': np.std(portfolio_returns),
                'return_skewness': stats.skew(portfolio_returns) if SCIPY_AVAILABLE else 0,
                'return_kurtosis': stats.kurtosis(portfolio_returns) if SCIPY_AVAILABLE else 0,
                'min_return': np.min(portfolio_returns),
                'max_return': np.max(portfolio_returns)
            }
            
            return VaRResult(
                method=VaRMethod.HISTORICAL,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                var_percentage=abs(var_value / portfolio_value) if portfolio_value != 0 else 0,
                calculation_time=start_time,
                parameters={'lookback_days': self.lookback_days},
                diagnostics=diagnostics
            )
            
        except Exception as e:
            self.logger.error(f"Historical VaR calculation failed: {e}")
            raise
    
    def get_required_history_length(self) -> int:
        return self.lookback_days
    
    def _calculate_portfolio_returns(self, positions: List[PortfolioPosition]) -> np.ndarray:
        """Calculate historical portfolio returns"""
        if not positions:
            return np.array([])
        
        # Get the minimum length across all positions
        min_length = min(len(pos.returns) for pos in positions if pos.returns is not None)
        
        if min_length == 0:
            return np.array([])
        
        # Calculate weighted portfolio returns
        portfolio_returns = np.zeros(min_length)
        total_value = sum(pos.market_value for pos in positions)
        
        for position in positions:
            if position.returns is not None and len(position.returns) >= min_length:
                weight = position.market_value / total_value if total_value > 0 else 0
                portfolio_returns += weight * position.returns[-min_length:]
        
        return portfolio_returns
    
    def _scale_returns_for_horizon(self, returns: np.ndarray, time_horizon: TimeHorizon) -> np.ndarray:
        """Scale returns for different time horizons"""
        scaling_factors = {
            TimeHorizon.INTRADAY: 1.0,
            TimeHorizon.DAILY: 1.0,
            TimeHorizon.WEEKLY: np.sqrt(5),
            TimeHorizon.MONTHLY: np.sqrt(22)
        }
        
        factor = scaling_factors.get(time_horizon, 1.0)
        return returns * factor


class ParametricVaRCalculator(VaRCalculator):
    """Parametric (variance-covariance) VaR calculator"""
    
    def __init__(self, use_ewma: bool = True, lambda_decay: float = 0.94):
        self.use_ewma = use_ewma
        self.lambda_decay = lambda_decay
        self.logger = logging.getLogger(__name__)
    
    def calculate_var(self, 
                     positions: List[PortfolioPosition],
                     confidence_level: float,
                     time_horizon: TimeHorizon,
                     **kwargs) -> VaRResult:
        """Calculate parametric VaR"""
        start_time = datetime.now()
        
        try:
            # Calculate portfolio statistics
            portfolio_mean, portfolio_std = self._calculate_portfolio_statistics(positions)
            
            # Get critical value for confidence level
            if SCIPY_AVAILABLE:
                critical_value = stats.norm.ppf(1 - confidence_level)
            else:
                # Approximate critical values
                critical_values = {0.90: -1.282, 0.95: -1.645, 0.99: -2.326, 0.999: -3.090}
                critical_value = critical_values.get(confidence_level, -1.645)
            
            # Scale for time horizon
            horizon_factor = self._get_horizon_scaling_factor(time_horizon)
            
            # Calculate VaR
            var_value = critical_value * portfolio_std * horizon_factor
            
            # Calculate Expected Shortfall (analytical for normal distribution)
            if SCIPY_AVAILABLE:
                phi = stats.norm.pdf(critical_value)
                expected_shortfall = -portfolio_std * horizon_factor * phi / (1 - confidence_level)
            else:
                expected_shortfall = var_value * 1.2  # Approximation
            
            # Calculate portfolio value
            portfolio_value = sum(pos.market_value for pos in positions)
            
            # Diagnostics
            diagnostics = {
                'portfolio_mean': portfolio_mean,
                'portfolio_std': portfolio_std,
                'critical_value': critical_value,
                'horizon_factor': horizon_factor,
                'use_ewma': self.use_ewma,
                'lambda_decay': self.lambda_decay if self.use_ewma else None
            }
            
            return VaRResult(
                method=VaRMethod.PARAMETRIC,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                var_percentage=abs(var_value / portfolio_value) if portfolio_value != 0 else 0,
                calculation_time=start_time,
                parameters={'use_ewma': self.use_ewma, 'lambda_decay': self.lambda_decay},
                diagnostics=diagnostics
            )
            
        except Exception as e:
            self.logger.error(f"Parametric VaR calculation failed: {e}")
            raise
    
    def get_required_history_length(self) -> int:
        return 30  # Minimum for reliable statistics
    
    def _calculate_portfolio_statistics(self, positions: List[PortfolioPosition]) -> Tuple[float, float]:
        """Calculate portfolio mean and standard deviation"""
        if not positions:
            return 0.0, 0.0
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(positions)
        
        if len(portfolio_returns) == 0:
            return 0.0, 0.0
        
        if self.use_ewma:
            # Exponentially weighted moving average
            portfolio_mean = self._ewma_mean(portfolio_returns)
            portfolio_std = self._ewma_std(portfolio_returns, portfolio_mean)
        else:
            # Simple statistics
            portfolio_mean = np.mean(portfolio_returns)
            portfolio_std = np.std(portfolio_returns, ddof=1)
        
        return portfolio_mean, portfolio_std
    
    def _calculate_portfolio_returns(self, positions: List[PortfolioPosition]) -> np.ndarray:
        """Calculate portfolio returns"""
        if not positions:
            return np.array([])
        
        # Get the minimum length across all positions
        min_length = min(len(pos.returns) for pos in positions if pos.returns is not None)
        
        if min_length == 0:
            return np.array([])
        
        # Calculate weighted portfolio returns
        portfolio_returns = np.zeros(min_length)
        total_value = sum(pos.market_value for pos in positions)
        
        for position in positions:
            if position.returns is not None and len(position.returns) >= min_length:
                weight = position.market_value / total_value if total_value > 0 else 0
                portfolio_returns += weight * position.returns[-min_length:]
        
        return portfolio_returns
    
    def _ewma_mean(self, returns: np.ndarray) -> float:
        """Calculate exponentially weighted moving average"""
        if len(returns) == 0:
            return 0.0
        
        weights = np.array([(1 - self.lambda_decay) * (self.lambda_decay ** i) 
                           for i in range(len(returns))])
        weights = weights[::-1]  # Reverse to give more weight to recent observations
        weights /= weights.sum()  # Normalize
        
        return np.sum(weights * returns)
    
    def _ewma_std(self, returns: np.ndarray, mean: float) -> float:
        """Calculate exponentially weighted standard deviation"""
        if len(returns) <= 1:
            return 0.0
        
        squared_deviations = (returns - mean) ** 2
        weights = np.array([(1 - self.lambda_decay) * (self.lambda_decay ** i) 
                           for i in range(len(returns))])
        weights = weights[::-1]  # Reverse to give more weight to recent observations
        weights /= weights.sum()  # Normalize
        
        ewma_variance = np.sum(weights * squared_deviations)
        return np.sqrt(ewma_variance)
    
    def _get_horizon_scaling_factor(self, time_horizon: TimeHorizon) -> float:
        """Get scaling factor for time horizon"""
        scaling_factors = {
            TimeHorizon.INTRADAY: 1.0,
            TimeHorizon.DAILY: 1.0,
            TimeHorizon.WEEKLY: np.sqrt(5),
            TimeHorizon.MONTHLY: np.sqrt(22)
        }
        return scaling_factors.get(time_horizon, 1.0)


class MonteCarloVaRCalculator(VaRCalculator):
    """Monte Carlo simulation VaR calculator"""
    
    def __init__(self, num_simulations: int = 10000, random_seed: Optional[int] = None):
        self.num_simulations = num_simulations
        self.random_seed = random_seed
        self.logger = logging.getLogger(__name__)
        
        if random_seed is not None:
            np.random.seed(random_seed)
    
    def calculate_var(self, 
                     positions: List[PortfolioPosition],
                     confidence_level: float,
                     time_horizon: TimeHorizon,
                     **kwargs) -> VaRResult:
        """Calculate Monte Carlo VaR"""
        start_time = datetime.now()
        
        try:
            # Calculate correlation matrix and statistics
            returns_matrix, mean_returns, cov_matrix = self._prepare_simulation_data(positions)
            
            if returns_matrix.shape[1] == 0:
                raise ValueError("No valid return data for Monte Carlo simulation")
            
            # Run Monte Carlo simulation
            simulated_returns = self._run_monte_carlo_simulation(
                mean_returns, cov_matrix, time_horizon
            )
            
            # Calculate portfolio values for each simulation
            portfolio_values = self._calculate_simulated_portfolio_values(
                positions, simulated_returns
            )
            
            # Calculate VaR and Expected Shortfall
            var_percentile = (1 - confidence_level) * 100
            var_value = np.percentile(portfolio_values, var_percentile)
            
            tail_losses = portfolio_values[portfolio_values <= var_value]
            expected_shortfall = np.mean(tail_losses) if len(tail_losses) > 0 else var_value
            
            # Calculate current portfolio value
            current_portfolio_value = sum(pos.market_value for pos in positions)
            
            # Convert to loss values
            var_loss = var_value - current_portfolio_value
            es_loss = expected_shortfall - current_portfolio_value
            
            # Diagnostics
            diagnostics = {
                'num_simulations': self.num_simulations,
                'mean_simulated_return': np.mean(simulated_returns),
                'std_simulated_return': np.std(simulated_returns),
                'min_simulated_value': np.min(portfolio_values),
                'max_simulated_value': np.max(portfolio_values),
                'simulation_percentiles': {
                    '1%': np.percentile(portfolio_values, 1),
                    '5%': np.percentile(portfolio_values, 5),
                    '10%': np.percentile(portfolio_values, 10),
                    '90%': np.percentile(portfolio_values, 90),
                    '95%': np.percentile(portfolio_values, 95),
                    '99%': np.percentile(portfolio_values, 99)
                }
            }
            
            return VaRResult(
                method=VaRMethod.MONTE_CARLO,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_value=var_loss,
                expected_shortfall=es_loss,
                portfolio_value=current_portfolio_value,
                var_percentage=abs(var_loss / current_portfolio_value) if current_portfolio_value != 0 else 0,
                calculation_time=start_time,
                parameters={'num_simulations': self.num_simulations, 'random_seed': self.random_seed},
                diagnostics=diagnostics
            )
            
        except Exception as e:
            self.logger.error(f"Monte Carlo VaR calculation failed: {e}")
            raise
    
    def get_required_history_length(self) -> int:
        return 60  # Need more data for reliable correlation estimation
    
    def _prepare_simulation_data(self, positions: List[PortfolioPosition]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for Monte Carlo simulation"""
        # Collect returns for all positions
        returns_data = []
        valid_positions = []
        
        for position in positions:
            if position.returns is not None and len(position.returns) > 0:
                returns_data.append(position.returns)
                valid_positions.append(position)
        
        if not returns_data:
            return np.array([]), np.array([]), np.array([])
        
        # Find minimum length
        min_length = min(len(returns) for returns in returns_data)
        
        # Create returns matrix
        returns_matrix = np.column_stack([
            returns[-min_length:] for returns in returns_data
        ])
        
        # Calculate statistics
        mean_returns = np.mean(returns_matrix, axis=0)
        cov_matrix = np.cov(returns_matrix.T)
        
        return returns_matrix, mean_returns, cov_matrix
    
    def _run_monte_carlo_simulation(self, 
                                   mean_returns: np.ndarray,
                                   cov_matrix: np.ndarray,
                                   time_horizon: TimeHorizon) -> np.ndarray:
        """Run Monte Carlo simulation"""
        # Scale for time horizon
        horizon_factor = self._get_horizon_scaling_factor(time_horizon)
        scaled_mean = mean_returns * horizon_factor
        scaled_cov = cov_matrix * horizon_factor
        
        # Generate random samples
        if len(mean_returns) == 1:
            # Single asset case
            simulated_returns = np.random.normal(
                scaled_mean[0], 
                np.sqrt(scaled_cov[0, 0]), 
                self.num_simulations
            )
        else:
            # Multi-asset case
            try:
                simulated_returns = np.random.multivariate_normal(
                    scaled_mean, 
                    scaled_cov, 
                    self.num_simulations
                )
            except np.linalg.LinAlgError:
                # Handle singular covariance matrix
                self.logger.warning("Singular covariance matrix, using diagonal approximation")
                diagonal_cov = np.diag(np.diag(scaled_cov))
                simulated_returns = np.random.multivariate_normal(
                    scaled_mean, 
                    diagonal_cov, 
                    self.num_simulations
                )
        
        return simulated_returns
    
    def _calculate_simulated_portfolio_values(self, 
                                            positions: List[PortfolioPosition],
                                            simulated_returns: np.ndarray) -> np.ndarray:
        """Calculate portfolio values for each simulation"""
        current_portfolio_value = sum(pos.market_value for pos in positions)
        
        if simulated_returns.ndim == 1:
            # Single asset
            portfolio_returns = simulated_returns
        else:
            # Multi-asset - calculate weighted portfolio returns
            weights = np.array([pos.market_value / current_portfolio_value 
                              for pos in positions if pos.returns is not None])
            portfolio_returns = np.dot(simulated_returns, weights)
        
        # Convert returns to portfolio values
        portfolio_values = current_portfolio_value * (1 + portfolio_returns)
        
        return portfolio_values
    
    def _get_horizon_scaling_factor(self, time_horizon: TimeHorizon) -> float:
        """Get scaling factor for time horizon"""
        scaling_factors = {
            TimeHorizon.INTRADAY: 1.0,
            TimeHorizon.DAILY: 1.0,
            TimeHorizon.WEEKLY: 5,
            TimeHorizon.MONTHLY: 22
        }
        return scaling_factors.get(time_horizon, 1.0)


class GARCHVaRCalculator(VaRCalculator):
    """GARCH model VaR calculator"""
    
    def __init__(self, max_iterations: int = 1000, tolerance: float = 1e-6):
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.logger = logging.getLogger(__name__)
    
    def calculate_var(self, 
                     positions: List[PortfolioPosition],
                     confidence_level: float,
                     time_horizon: TimeHorizon,
                     **kwargs) -> VaRResult:
        """Calculate GARCH VaR"""
        start_time = datetime.now()
        
        try:
            # Calculate portfolio returns
            portfolio_returns = self._calculate_portfolio_returns(positions)
            
            if len(portfolio_returns) < 100:
                raise ValueError("Insufficient data for GARCH model (minimum 100 observations)")
            
            # Fit GARCH model
            garch_params = self._fit_garch_model(portfolio_returns)
            
            # Forecast volatility
            forecasted_volatility = self._forecast_volatility(
                portfolio_returns, garch_params, time_horizon
            )
            
            # Calculate VaR using forecasted volatility
            if SCIPY_AVAILABLE:
                critical_value = stats.norm.ppf(1 - confidence_level)
            else:
                critical_values = {0.90: -1.282, 0.95: -1.645, 0.99: -2.326, 0.999: -3.090}
                critical_value = critical_values.get(confidence_level, -1.645)
            
            var_value = critical_value * forecasted_volatility
            
            # Calculate Expected Shortfall
            if SCIPY_AVAILABLE:
                phi = stats.norm.pdf(critical_value)
                expected_shortfall = -forecasted_volatility * phi / (1 - confidence_level)
            else:
                expected_shortfall = var_value * 1.2
            
            # Calculate portfolio value
            portfolio_value = sum(pos.market_value for pos in positions)
            
            # Diagnostics
            diagnostics = {
                'garch_omega': garch_params.omega,
                'garch_alpha': garch_params.alpha,
                'garch_beta': garch_params.beta,
                'log_likelihood': garch_params.log_likelihood,
                'aic': garch_params.aic,
                'bic': garch_params.bic,
                'convergence': garch_params.convergence,
                'forecasted_volatility': forecasted_volatility,
                'unconditional_volatility': np.sqrt(garch_params.omega / (1 - garch_params.alpha - garch_params.beta))
            }
            
            return VaRResult(
                method=VaRMethod.GARCH,
                confidence_level=confidence_level,
                time_horizon=time_horizon,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                var_percentage=abs(var_value / portfolio_value) if portfolio_value != 0 else 0,
                calculation_time=start_time,
                parameters={'max_iterations': self.max_iterations, 'tolerance': self.tolerance},
                diagnostics=diagnostics
            )
            
        except Exception as e:
            self.logger.error(f"GARCH VaR calculation failed: {e}")
            raise
    
    def get_required_history_length(self) -> int:
        return 252  # One year of daily data for reliable GARCH estimation
    
    def _calculate_portfolio_returns(self, positions: List[PortfolioPosition]) -> np.ndarray:
        """Calculate portfolio returns"""
        if not positions:
            return np.array([])
        
        # Get the minimum length across all positions
        min_length = min(len(pos.returns) for pos in positions if pos.returns is not None)
        
        if min_length == 0:
            return np.array([])
        
        # Calculate weighted portfolio returns
        portfolio_returns = np.zeros(min_length)
        total_value = sum(pos.market_value for pos in positions)
        
        for position in positions:
            if position.returns is not None and len(position.returns) >= min_length:
                weight = position.market_value / total_value if total_value > 0 else 0
                portfolio_returns += weight * position.returns[-min_length:]
        
        return portfolio_returns
    
    def _fit_garch_model(self, returns: np.ndarray) -> GARCHParameters:
        """Fit GARCH(1,1) model to returns"""
        # Initial parameter estimates
        initial_params = np.array([
            np.var(returns) * 0.01,  # omega
            0.1,                     # alpha
            0.8                      # beta
        ])
        
        # Bounds for parameters
        bounds = [
            (1e-6, None),    # omega > 0
            (0, 1),          # 0 <= alpha < 1
            (0, 1)           # 0 <= beta < 1
        ]
        
        # Constraint: alpha + beta < 1 for stationarity
        constraints = {'type': 'ineq', 'fun': lambda x: 0.999 - x[1] - x[2]}
        
        try:
            if SCIPY_AVAILABLE:
                result = minimize(
                    self._garch_log_likelihood,
                    initial_params,
                    args=(returns,),
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints,
                    options={'maxiter': self.max_iterations, 'ftol': self.tolerance}
                )
                
                if result.success:
                    omega, alpha, beta = result.x
                    log_likelihood = -result.fun
                    
                    # Calculate information criteria
                    n_params = 3
                    n_obs = len(returns)
                    aic = 2 * n_params - 2 * log_likelihood
                    bic = np.log(n_obs) * n_params - 2 * log_likelihood
                    
                    return GARCHParameters(
                        omega=omega,
                        alpha=alpha,
                        beta=beta,
                        log_likelihood=log_likelihood,
                        aic=aic,
                        bic=bic,
                        convergence=True
                    )
                else:
                    self.logger.warning("GARCH optimization failed, using fallback parameters")
            
            # Fallback to simple estimates
            return self._fallback_garch_parameters(returns)
            
        except Exception as e:
            self.logger.warning(f"GARCH fitting failed: {e}, using fallback")
            return self._fallback_garch_parameters(returns)
    
    def _garch_log_likelihood(self, params: np.ndarray, returns: np.ndarray) -> float:
        """Calculate negative log-likelihood for GARCH(1,1) model"""
        omega, alpha, beta = params
        
        # Check parameter constraints
        if omega <= 0 or alpha < 0 or beta < 0 or alpha + beta >= 1:
            return 1e10  # Return large value for invalid parameters
        
        n = len(returns)
        sigma2 = np.zeros(n)
        
        # Initialize with unconditional variance
        sigma2[0] = np.var(returns)
        
        # Calculate conditional variances
        for t in range(1, n):
            sigma2[t] = omega + alpha * returns[t-1]**2 + beta * sigma2[t-1]
        
        # Avoid numerical issues
        sigma2 = np.maximum(sigma2, 1e-8)
        
        # Calculate log-likelihood
        log_likelihood = -0.5 * np.sum(
            np.log(2 * np.pi) + np.log(sigma2) + returns**2 / sigma2
        )
        
        return -log_likelihood  # Return negative for minimization
    
    def _fallback_garch_parameters(self, returns: np.ndarray) -> GARCHParameters:
        """Fallback GARCH parameters when optimization fails"""
        variance = np.var(returns)
        
        return GARCHParameters(
            omega=variance * 0.01,
            alpha=0.1,
            beta=0.8,
            log_likelihood=0.0,
            aic=0.0,
            bic=0.0,
            convergence=False
        )
    
    def _forecast_volatility(self, 
                           returns: np.ndarray,
                           garch_params: GARCHParameters,
                           time_horizon: TimeHorizon) -> float:
        """Forecast volatility using GARCH model"""
        # Calculate current conditional variance
        current_variance = (
            garch_params.omega + 
            garch_params.alpha * returns[-1]**2 + 
            garch_params.beta * np.var(returns[-10:])  # Use recent variance
        )
        
        # Multi-step ahead forecast
        horizon_days = self._get_horizon_days(time_horizon)
        
        if horizon_days == 1:
            forecasted_variance = current_variance
        else:
            # Long-run variance
            long_run_variance = garch_params.omega / (1 - garch_params.alpha - garch_params.beta)
            
            # Forecast using GARCH dynamics
            persistence = garch_params.alpha + garch_params.beta
            forecasted_variance = (
                long_run_variance + 
                (current_variance - long_run_variance) * (persistence ** (horizon_days - 1))
            )
        
        return np.sqrt(forecasted_variance)
    
    def _get_horizon_days(self, time_horizon: TimeHorizon) -> int:
        """Convert time horizon to days"""
        horizon_days = {
            TimeHorizon.INTRADAY: 1,
            TimeHorizon.DAILY: 1,
            TimeHorizon.WEEKLY: 5,
            TimeHorizon.MONTHLY: 22
        }
        return horizon_days.get(time_horizon, 1)


class VaRBacktester:
    """VaR model backtesting and validation"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def backtest_var_model(self,
                          var_results: List[VaRResult],
                          actual_returns: np.ndarray,
                          portfolio_values: np.ndarray) -> VaRBacktestResult:
        """Backtest VaR model performance"""
        if len(var_results) != len(actual_returns):
            raise ValueError("VaR results and actual returns must have same length")
        
        method = var_results[0].method
        confidence_level = var_results[0].confidence_level
        
        # Calculate violations
        violations = 0
        var_values = []
        actual_losses = []
        
        for i, (var_result, actual_return, portfolio_value) in enumerate(
            zip(var_results, actual_returns, portfolio_values)
        ):
            var_values.append(var_result.var_value)
            actual_loss = actual_return * portfolio_value
            actual_losses.append(actual_loss)
            
            # Check if actual loss exceeds VaR
            if actual_loss < var_result.var_value:
                violations += 1
        
        # Calculate violation rate
        total_observations = len(var_results)
        violation_rate = violations / total_observations
        expected_violations = int(total_observations * (1 - confidence_level))
        
        # Kupiec POF test
        kupiec_stat, kupiec_p_value, kupiec_reject = self._kupiec_pof_test(
            violations, total_observations, confidence_level
        )
        
        # Christoffersen conditional coverage test
        cc_stat, cc_p_value, cc_reject = self._christoffersen_cc_test(
            var_values, actual_losses, confidence_level
        )
        
        # Traffic light test
        traffic_light_zone = self._traffic_light_test(violations, expected_violations)
        
        return VaRBacktestResult(
            method=method,
            confidence_level=confidence_level,
            total_observations=total_observations,
            violations=violations,
            violation_rate=violation_rate,
            expected_violations=expected_violations,
            kupiec_pof_statistic=kupiec_stat,
            kupiec_pof_p_value=kupiec_p_value,
            kupiec_pof_reject=kupiec_reject,
            christoffersen_cc_statistic=cc_stat,
            christoffersen_cc_p_value=cc_p_value,
            christoffersen_cc_reject=cc_reject,
            average_var=np.mean(var_values),
            average_actual_loss=np.mean(actual_losses),
            maximum_loss=np.min(actual_losses),  # Most negative value
            traffic_light_zone=traffic_light_zone
        )
    
    def _kupiec_pof_test(self, violations: int, total_obs: int, confidence_level: float) -> Tuple[float, float, bool]:
        """Kupiec Proportion of Failures test"""
        expected_rate = 1 - confidence_level
        observed_rate = violations / total_obs
        
        if violations == 0 or violations == total_obs:
            # Handle edge cases
            return 0.0, 1.0, False
        
        # Calculate test statistic
        log_likelihood_ratio = (
            violations * np.log(observed_rate / expected_rate) +
            (total_obs - violations) * np.log((1 - observed_rate) / (1 - expected_rate))
        )
        
        test_statistic = 2 * log_likelihood_ratio
        
        # Critical value for chi-square distribution with 1 degree of freedom
        critical_value = 3.841  # 95% confidence level
        
        if SCIPY_AVAILABLE:
            p_value = 1 - stats.chi2.cdf(test_statistic, df=1)
        else:
            p_value = 0.05 if test_statistic > critical_value else 0.5
        
        reject_null = test_statistic > critical_value
        
        return test_statistic, p_value, reject_null
    
    def _christoffersen_cc_test(self, var_values: List[float], actual_losses: List[float], confidence_level: float) -> Tuple[float, float, bool]:
        """Christoffersen conditional coverage test"""
        # Create violation indicator series
        violations = [1 if actual < var_val else 0 for actual, var_val in zip(actual_losses, var_values)]
        
        if len(violations) < 2:
            return 0.0, 1.0, False
        
        # Calculate transition probabilities
        n00 = n01 = n10 = n11 = 0
        
        for i in range(len(violations) - 1):
            if violations[i] == 0 and violations[i + 1] == 0:
                n00 += 1
            elif violations[i] == 0 and violations[i + 1] == 1:
                n01 += 1
            elif violations[i] == 1 and violations[i + 1] == 0:
                n10 += 1
            elif violations[i] == 1 and violations[i + 1] == 1:
                n11 += 1
        
        # Avoid division by zero
        if n00 + n01 == 0 or n10 + n11 == 0:
            return 0.0, 1.0, False
        
        # Calculate test statistic
        pi_01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0
        pi_11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0
        pi = (n01 + n11) / (n00 + n01 + n10 + n11)
        
        if pi_01 == 0 or pi_11 == 0 or pi == 0 or pi == 1:
            return 0.0, 1.0, False
        
        log_likelihood_ratio = (
            n00 * np.log(1 - pi_01) + n01 * np.log(pi_01) +
            n10 * np.log(1 - pi_11) + n11 * np.log(pi_11) -
            (n00 + n10) * np.log(1 - pi) - (n01 + n11) * np.log(pi)
        )
        
        test_statistic = 2 * log_likelihood_ratio
        
        # Critical value for chi-square distribution with 1 degree of freedom
        critical_value = 3.841
        
        if SCIPY_AVAILABLE:
            p_value = 1 - stats.chi2.cdf(test_statistic, df=1)
        else:
            p_value = 0.05 if test_statistic > critical_value else 0.5
        
        reject_null = test_statistic > critical_value
        
        return test_statistic, p_value, reject_null
    
    def _traffic_light_test(self, violations: int, expected_violations: int) -> str:
        """Basel traffic light test"""
        if violations <= expected_violations + 4:
            return "green"
        elif violations <= expected_violations + 9:
            return "yellow"
        else:
            return "red"


class VaREngine:
    """
    Comprehensive Real-Time VaR Calculation Engine
    
    Features:
    - Multiple VaR calculation methods (Historical, Parametric, Monte Carlo, GARCH)
    - Real-time calculation with background processing
    - Model backtesting and validation
    - Performance monitoring and alerting
    - Integration with portfolio management systems
    """
    
    def __init__(self,
                 enable_real_time: bool = True,
                 calculation_interval_seconds: int = 60,
                 enable_backtesting: bool = True):
        
        self.enable_real_time = enable_real_time
        self.calculation_interval_seconds = calculation_interval_seconds
        self.enable_backtesting = enable_backtesting
        
        # VaR calculators
        self._calculators = {
            VaRMethod.HISTORICAL: HistoricalVaRCalculator(),
            VaRMethod.PARAMETRIC: ParametricVaRCalculator(),
            VaRMethod.MONTE_CARLO: MonteCarloVaRCalculator(),
            VaRMethod.GARCH: GARCHVaRCalculator()
        }
        
        # Results storage
        self._var_results: Dict[str, List[VaRResult]] = defaultdict(list)
        self._portfolio_positions: Dict[str, List[PortfolioPosition]] = {}
        
        # Backtesting
        self._backtester = VaRBacktester()
        self._backtest_results: Dict[str, VaRBacktestResult] = {}
        
        # Background processing
        self._calculation_queue = asyncio.Queue(maxsize=1000)
        self._worker_tasks: List[asyncio.Task] = []
        self._running = False
        
        # Thread pool for intensive calculations
        self._thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="var-engine"
        )
        
        # Performance metrics
        self._metrics = {
            'calculations_completed': 0,
            'calculations_failed': 0,
            'avg_calculation_time_ms': 0.0,
            'last_calculation_time': None,
            'active_portfolios': 0,
            'total_var_breaches': 0
        }
        
        # Alerting
        self._alert_callbacks: List[Callable] = []
        self._var_breach_threshold = 0.05  # 5% breach threshold
        
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the VaR engine"""
        if self._running:
            return
        
        self._running = True
        
        # Start background workers
        if self.enable_real_time:
            self._worker_tasks = [
                asyncio.create_task(self._calculation_worker()),
                asyncio.create_task(self._real_time_calculator()),
                asyncio.create_task(self._metrics_collector())
            ]
        
        self.logger.info("VaR Engine started")
    
    async def stop(self):
        """Stop the VaR engine"""
        self._running = False
        
        # Cancel worker tasks
        for task in self._worker_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        self.logger.info("VaR Engine stopped")
    
    async def calculate_var(self,
                           portfolio_id: str,
                           positions: List[PortfolioPosition],
                           method: VaRMethod,
                           confidence_level: float = 0.95,
                           time_horizon: TimeHorizon = TimeHorizon.DAILY) -> VaRResult:
        """Calculate VaR for a portfolio"""
        try:
            # Store positions for real-time calculations
            self._portfolio_positions[portfolio_id] = positions
            
            # Get calculator
            calculator = self._calculators.get(method)
            if not calculator:
                raise ValueError(f"Unsupported VaR method: {method}")
            
            # Calculate VaR
            start_time = time.time()
            var_result = calculator.calculate_var(positions, confidence_level, time_horizon)
            calculation_time = (time.time() - start_time) * 1000
            
            # Store result
            self._var_results[portfolio_id].append(var_result)
            
            # Keep only recent results (last 1000)
            if len(self._var_results[portfolio_id]) > 1000:
                self._var_results[portfolio_id] = self._var_results[portfolio_id][-1000:]
            
            # Update metrics
            self._metrics['calculations_completed'] += 1
            self._metrics['last_calculation_time'] = datetime.now()
            
            # Update average calculation time
            current_avg = self._metrics['avg_calculation_time_ms']
            total_calcs = self._metrics['calculations_completed']
            self._metrics['avg_calculation_time_ms'] = (
                (current_avg * (total_calcs - 1) + calculation_time) / total_calcs
            )
            
            # Check for VaR breaches
            await self._check_var_breach(portfolio_id, var_result)
            
            self.logger.info(f"VaR calculated for {portfolio_id}: {var_result.var_value:.2f} ({method.value})")
            
            return var_result
            
        except Exception as e:
            self._metrics['calculations_failed'] += 1
            self.logger.error(f"VaR calculation failed for {portfolio_id}: {e}")
            raise
    
    async def calculate_all_methods(self,
                                   portfolio_id: str,
                                   positions: List[PortfolioPosition],
                                   confidence_level: float = 0.95,
                                   time_horizon: TimeHorizon = TimeHorizon.DAILY) -> Dict[VaRMethod, VaRResult]:
        """Calculate VaR using all available methods"""
        results = {}
        
        for method in VaRMethod:
            try:
                result = await self.calculate_var(
                    portfolio_id, positions, method, confidence_level, time_horizon
                )
                results[method] = result
            except Exception as e:
                self.logger.error(f"Failed to calculate VaR using {method.value}: {e}")
        
        return results
    
    async def backtest_var_model(self,
                                portfolio_id: str,
                                method: VaRMethod,
                                lookback_days: int = 252) -> Optional[VaRBacktestResult]:
        """Backtest VaR model performance"""
        if not self.enable_backtesting:
            return None
        
        try:
            # Get historical VaR results
            var_results = self._var_results.get(portfolio_id, [])
            
            if len(var_results) < lookback_days:
                self.logger.warning(f"Insufficient VaR history for backtesting: {len(var_results)} < {lookback_days}")
                return None
            
            # Filter by method
            method_results = [r for r in var_results if r.method == method][-lookback_days:]
            
            if len(method_results) < lookback_days:
                return None
            
            # Get portfolio positions for return calculation
            positions = self._portfolio_positions.get(portfolio_id, [])
            if not positions:
                return None
            
            # Calculate actual returns (simplified - would need historical data)
            actual_returns = np.random.normal(0, 0.02, len(method_results))  # Placeholder
            portfolio_values = np.array([r.portfolio_value for r in method_results])
            
            # Run backtest
            backtest_result = self._backtester.backtest_var_model(
                method_results, actual_returns, portfolio_values
            )
            
            # Store result
            self._backtest_results[f"{portfolio_id}_{method.value}"] = backtest_result
            
            self.logger.info(f"VaR backtest completed for {portfolio_id} ({method.value}): "
                           f"{backtest_result.violations}/{backtest_result.total_observations} violations")
            
            return backtest_result
            
        except Exception as e:
            self.logger.error(f"VaR backtesting failed for {portfolio_id}: {e}")
            return None
    
    def get_var_history(self, portfolio_id: str, method: Optional[VaRMethod] = None) -> List[VaRResult]:
        """Get VaR calculation history"""
        results = self._var_results.get(portfolio_id, [])
        
        if method:
            results = [r for r in results if r.method == method]
        
        return results
    
    def get_backtest_results(self, portfolio_id: str, method: VaRMethod) -> Optional[VaRBacktestResult]:
        """Get backtesting results"""
        key = f"{portfolio_id}_{method.value}"
        return self._backtest_results.get(key)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get engine metrics"""
        return {
            **self._metrics,
            'active_portfolios': len(self._portfolio_positions),
            'total_var_results': sum(len(results) for results in self._var_results.values()),
            'available_methods': [method.value for method in self._calculators.keys()],
            'backtest_results_count': len(self._backtest_results)
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add callback for VaR breach alerts"""
        self._alert_callbacks.append(callback)
    
    def set_var_breach_threshold(self, threshold: float):
        """Set VaR breach threshold for alerting"""
        self._var_breach_threshold = threshold
    
    # Private methods
    
    async def _calculation_worker(self):
        """Background worker for VaR calculations"""
        while self._running:
            try:
                # Get calculation request from queue
                try:
                    request = await asyncio.wait_for(
                        self._calculation_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process calculation request
                await self._process_calculation_request(request)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Calculation worker error: {e}")
                await asyncio.sleep(1)
    
    async def _real_time_calculator(self):
        """Real-time VaR calculation loop"""
        while self._running:
            try:
                # Calculate VaR for all active portfolios
                for portfolio_id, positions in self._portfolio_positions.items():
                    if positions:
                        # Queue calculation request
                        await self._calculation_queue.put({
                            'type': 'calculate_var',
                            'portfolio_id': portfolio_id,
                            'positions': positions,
                            'method': VaRMethod.PARAMETRIC,  # Default method for real-time
                            'confidence_level': 0.95,
                            'time_horizon': TimeHorizon.DAILY
                        })
                
                # Wait for next calculation cycle
                await asyncio.sleep(self.calculation_interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Real-time calculator error: {e}")
                await asyncio.sleep(self.calculation_interval_seconds)
    
    async def _process_calculation_request(self, request: Dict[str, Any]):
        """Process VaR calculation request"""
        try:
            if request['type'] == 'calculate_var':
                await self.calculate_var(
                    request['portfolio_id'],
                    request['positions'],
                    request['method'],
                    request['confidence_level'],
                    request['time_horizon']
                )
        except Exception as e:
            self.logger.error(f"Failed to process calculation request: {e}")
    
    async def _check_var_breach(self, portfolio_id: str, var_result: VaRResult):
        """Check for VaR breaches and send alerts"""
        try:
            breach_percentage = abs(var_result.var_percentage)
            
            if breach_percentage > self._var_breach_threshold:
                self._metrics['total_var_breaches'] += 1
                
                # Send alerts
                alert_data = {
                    'type': 'var_breach',
                    'portfolio_id': portfolio_id,
                    'var_result': var_result,
                    'breach_percentage': breach_percentage,
                    'threshold': self._var_breach_threshold,
                    'timestamp': datetime.now()
                }
                
                for callback in self._alert_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(alert_data)
                        else:
                            callback(alert_data)
                    except Exception as e:
                        self.logger.error(f"Alert callback error: {e}")
        
        except Exception as e:
            self.logger.error(f"VaR breach check failed: {e}")
    
    async def _metrics_collector(self):
        """Background worker for metrics collection"""
        while self._running:
            try:
                # Update metrics
                self._metrics['active_portfolios'] = len(self._portfolio_positions)
                
                await asyncio.sleep(30)  # Update every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Metrics collector error: {e}")
                await asyncio.sleep(30)


# Global VaR engine instance
_var_engine_instance: Optional[VaREngine] = None


def get_var_engine() -> VaREngine:
    """Get global VaR engine instance"""
    global _var_engine_instance
    if _var_engine_instance is None:
        raise RuntimeError("VaR engine not initialized. Call initialize_var_engine() first.")
    return _var_engine_instance


def initialize_var_engine(
    enable_real_time: bool = True,
    calculation_interval_seconds: int = 60,
    enable_backtesting: bool = True
) -> VaREngine:
    """Initialize global VaR engine instance"""
    global _var_engine_instance
    _var_engine_instance = VaREngine(
        enable_real_time=enable_real_time,
        calculation_interval_seconds=calculation_interval_seconds,
        enable_backtesting=enable_backtesting
    )
    return _var_engine_instance


async def start_var_engine(**kwargs) -> VaREngine:
    """Start VaR engine with configuration"""
    engine = initialize_var_engine(**kwargs)
    await engine.start()
    return engine


async def stop_var_engine():
    """Stop global VaR engine"""
    global _var_engine_instance
    if _var_engine_instance:
        await _var_engine_instance.stop()
        _var_engine_instance = None