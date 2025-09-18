"""Advanced Risk Management Factory

Institutional-grade risk management with enhanced Kelly Criterion, advanced position sizing,
and sophisticated risk calculations for professional trading systems.

Author: Vincent S. Pereira
Version: 2.0.0
"""

import logging
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import deque
import math
from scipy import stats
from scipy.optimize import minimize_scalar

logger = logging.getLogger(__name__)


class AdvancedPositionSizingMethod(Enum):
    """Advanced position sizing methods"""
    KELLY_CRITERION = "kelly_criterion"
    OPTIMAL_F = "optimal_f"
    FIXED_FRACTIONAL = "fixed_fractional"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    RISK_PARITY = "risk_parity"
    SHARPE_OPTIMAL = "sharpe_optimal"
    DRAWDOWN_ADJUSTED = "drawdown_adjusted"
    MONTE_CARLO = "monte_carlo"
    ENSEMBLE = "ensemble"


class RiskMetricType(Enum):
    """Types of risk metrics"""
    VAR = "value_at_risk"
    CVAR = "conditional_var"
    MAX_DRAWDOWN = "max_drawdown"
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    OMEGA_RATIO = "omega_ratio"
    TAIL_RATIO = "tail_ratio"


@dataclass
class AdvancedRiskConfig:
    """Configuration for advanced risk management"""
    # Base risk parameters
    base_risk_per_trade: float = 0.02  # 2% of portfolio per trade
    max_portfolio_risk: float = 0.10   # 10% max portfolio risk
    max_position_size: float = 0.05    # 5% max position size
    
    # Position sizing
    position_sizing_method: AdvancedPositionSizingMethod = AdvancedPositionSizingMethod.KELLY_CRITERION
    kelly_lookback_periods: int = 252  # 1 year for Kelly calculation
    kelly_fractional: float = 0.25     # Use 25% of full Kelly
    
    # Risk metrics
    var_confidence: float = 0.05       # 95% VaR
    cvar_confidence: float = 0.05      # 95% CVaR
    lookback_periods: int = 252        # Risk calculation lookback
    
    # Advanced features
    enable_regime_adjustment: bool = True
    enable_correlation_adjustment: bool = True
    enable_drawdown_protection: bool = True
    enable_monte_carlo: bool = True
    
    # Monte Carlo parameters
    mc_simulations: int = 10000
    mc_time_horizon: int = 21  # 21 days
    
    # Ensemble parameters
    ensemble_methods: List[AdvancedPositionSizingMethod] = field(default_factory=lambda: [
        AdvancedPositionSizingMethod.KELLY_CRITERION,
        AdvancedPositionSizingMethod.VOLATILITY_ADJUSTED,
        AdvancedPositionSizingMethod.RISK_PARITY
    ])
    ensemble_weights: List[float] = field(default_factory=lambda: [0.5, 0.3, 0.2])


@dataclass
class AdvancedRiskMetrics:
    """Comprehensive advanced risk metrics"""
    # Position sizing
    position_size: float = 0.0
    kelly_fraction: float = 0.0
    optimal_f: float = 0.0
    
    # Risk measures
    var_95: float = 0.0
    cvar_95: float = 0.0
    max_drawdown: float = 0.0
    expected_shortfall: float = 0.0
    
    # Performance ratios
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    omega_ratio: float = 0.0
    
    # Advanced metrics
    tail_ratio: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    
    # Monte Carlo results
    mc_var: float = 0.0
    mc_expected_return: float = 0.0
    mc_probability_of_loss: float = 0.0
    
    # Regime and correlation adjustments
    regime_multiplier: float = 1.0
    correlation_adjustment: float = 1.0
    
    # Metadata
    calculation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_level: float = 0.95


class AdvancedRiskFactory:
    """Advanced Risk Management Factory
    
    Provides institutional-grade risk management with:
    - Enhanced Kelly Criterion with regime awareness
    - Optimal F position sizing
    - Monte Carlo risk simulation
    - Multi-method ensemble sizing
    - Advanced risk metrics (VaR, CVaR, etc.)
    - Correlation and regime adjustments
    """
    
    def __init__(self, config: AdvancedRiskConfig = None):
        self.config = config or AdvancedRiskConfig()
        self.logger = logging.getLogger(__name__)
        
        # Historical data storage
        self.returns_history: deque = deque(maxlen=self.config.lookback_periods * 2)
        self.portfolio_values: deque = deque(maxlen=self.config.lookback_periods)
        self.drawdown_history: deque = deque(maxlen=self.config.lookback_periods)
        
        # Performance tracking
        self.win_rate_history: deque = deque(maxlen=100)
        self.win_loss_ratios: deque = deque(maxlen=100)
        
        # Risk metrics cache
        self.risk_metrics_cache: Dict[str, AdvancedRiskMetrics] = {}
        self.last_calculation_time: Optional[datetime] = None
        
        # Monte Carlo engine
        self.mc_engine: Optional['MonteCarloEngine'] = None
        if self.config.enable_monte_carlo:
            self.mc_engine = MonteCarloEngine(self.config)
    
    def calculate_kelly_criterion(
        self,
        returns: np.ndarray = None,
        win_rate: float = None,
        avg_win: float = None,
        avg_loss: float = None,
        regime_factor: float = 1.0
    ) -> float:
        """Calculate Kelly Criterion with regime awareness
        
        Enhanced Kelly formula: f* = (bp - q) / b
        where b = avg_win/avg_loss, p = win_rate, q = 1-p
        """
        try:
            # Use provided parameters or calculate from returns
            if returns is not None and len(returns) > 10:
                wins = returns[returns > 0]
                losses = returns[returns < 0]
                
                if len(wins) > 0 and len(losses) > 0:
                    win_rate = len(wins) / len(returns)
                    avg_win = np.mean(wins)
                    avg_loss = abs(np.mean(losses))
                else:
                    return 0.0
            
            # Default values if not provided
            if win_rate is None:
                win_rate = 0.55
            if avg_win is None:
                avg_win = 0.02
            if avg_loss is None:
                avg_loss = 0.01
            
            # Calculate Kelly fraction
            if avg_loss > 0:
                b = avg_win / avg_loss  # Win/loss ratio
                kelly_fraction = (b * win_rate - (1 - win_rate)) / b
            else:
                kelly_fraction = 0.0
            
            # Apply regime adjustment
            kelly_fraction *= regime_factor
            
            # Apply fractional Kelly (reduce risk)
            kelly_fraction *= self.config.kelly_fractional
            
            # Bound the result
            kelly_fraction = np.clip(kelly_fraction, 0.0, 0.5)  # Max 50% of capital
            
            return float(kelly_fraction)
            
        except Exception as e:
            self.logger.error(f"Error calculating Kelly Criterion: {e}")
            return 0.02  # Default 2%
    
    def calculate_optimal_f(
        self,
        returns: np.ndarray,
        max_iterations: int = 100
    ) -> float:
        """Calculate Optimal F using Ralph Vince's method"""
        try:
            if len(returns) < 10:
                return 0.02
            
            # Convert returns to P&L
            pnl = returns * 100  # Scale for numerical stability
            
            # Find the largest loss
            largest_loss = abs(np.min(pnl)) if np.min(pnl) < 0 else 1.0
            
            def objective_function(f):
                """Objective function to maximize geometric mean"""
                if f <= 0 or f >= 1:
                    return -np.inf
                
                # Calculate HPR (Holding Period Return) for each trade
                hpr = 1 + (pnl * f / largest_loss)
                
                # Avoid negative HPR
                hpr = np.maximum(hpr, 0.001)
                
                # Calculate geometric mean
                try:
                    geom_mean = np.exp(np.mean(np.log(hpr)))
                    return geom_mean
                except:
                    return 0.001
            
            # Optimize f to maximize geometric mean
            result = minimize_scalar(
                lambda f: -objective_function(f),
                bounds=(0.001, 0.5),
                method='bounded'
            )
            
            optimal_f = result.x if result.success else 0.02
            return float(np.clip(optimal_f, 0.001, 0.5))
            
        except Exception as e:
            self.logger.error(f"Error calculating Optimal F: {e}")
            return 0.02
    
    def calculate_var_cvar(
        self,
        returns: np.ndarray,
        confidence: float = 0.05
    ) -> Tuple[float, float]:
        """Calculate Value at Risk and Conditional VaR"""
        try:
            if len(returns) < 10:
                return 0.0, 0.0
            
            # Sort returns in ascending order
            sorted_returns = np.sort(returns)
            
            # Calculate VaR (percentile)
            var_index = int(confidence * len(sorted_returns))
            var = abs(sorted_returns[var_index]) if var_index < len(sorted_returns) else 0.0
            
            # Calculate CVaR (expected shortfall)
            tail_returns = sorted_returns[:var_index] if var_index > 0 else sorted_returns[:1]
            cvar = abs(np.mean(tail_returns)) if len(tail_returns) > 0 else 0.0
            
            return float(var), float(cvar)
            
        except Exception as e:
            self.logger.error(f"Error calculating VaR/CVaR: {e}")
            return 0.0, 0.0
    
    def calculate_advanced_position_size(
        self,
        signal_strength: float,
        portfolio_value: float,
        asset_price: float,
        volatility: float = None,
        returns_history: np.ndarray = None,
        regime_factor: float = 1.0,
        correlation_matrix: np.ndarray = None
    ) -> AdvancedRiskMetrics:
        """Calculate position size using advanced methods"""
        
        try:
            # Initialize metrics
            metrics = AdvancedRiskMetrics()
            
            # Use historical returns or generate synthetic
            if returns_history is None:
                returns_history = np.array(list(self.returns_history)[-self.config.kelly_lookback_periods:])
            
            if len(returns_history) < 10:
                # Generate synthetic returns for initial calculation
                returns_history = np.random.normal(0.001, 0.02, 50)
            
            # Calculate Kelly Criterion
            metrics.kelly_fraction = self.calculate_kelly_criterion(
                returns=returns_history,
                regime_factor=regime_factor
            )
            
            # Calculate Optimal F
            metrics.optimal_f = self.calculate_optimal_f(returns_history)
            
            # Calculate VaR and CVaR
            metrics.var_95, metrics.cvar_95 = self.calculate_var_cvar(
                returns_history,
                self.config.var_confidence
            )
            
            # Calculate performance ratios
            if len(returns_history) > 20:
                metrics.sharpe_ratio = self._calculate_sharpe_ratio(returns_history)
                metrics.sortino_ratio = self._calculate_sortino_ratio(returns_history)
                metrics.calmar_ratio = self._calculate_calmar_ratio(returns_history)
                metrics.skewness = float(stats.skew(returns_history))
                metrics.kurtosis = float(stats.kurtosis(returns_history))
            
            # Position sizing based on selected method
            base_risk_amount = portfolio_value * self.config.base_risk_per_trade
            
            if self.config.position_sizing_method == AdvancedPositionSizingMethod.KELLY_CRITERION:
                position_size = (portfolio_value * metrics.kelly_fraction) / asset_price
                
            elif self.config.position_sizing_method == AdvancedPositionSizingMethod.OPTIMAL_F:
                position_size = (portfolio_value * metrics.optimal_f) / asset_price
                
            elif self.config.position_sizing_method == AdvancedPositionSizingMethod.VOLATILITY_ADJUSTED:
                vol_adj = (0.02 / (volatility or 0.02))  # Target 2% volatility
                position_size = (base_risk_amount * vol_adj) / asset_price
                
            elif self.config.position_sizing_method == AdvancedPositionSizingMethod.RISK_PARITY:
                # Equal risk contribution
                target_risk = portfolio_value * 0.01  # 1% risk per position
                position_size = target_risk / (asset_price * (volatility or 0.02))
                
            elif self.config.position_sizing_method == AdvancedPositionSizingMethod.ENSEMBLE:
                # Ensemble of methods
                sizes = []
                weights = self.config.ensemble_weights
                
                # Kelly
                kelly_size = (portfolio_value * metrics.kelly_fraction) / asset_price
                sizes.append(kelly_size)
                
                # Volatility adjusted
                vol_adj = (0.02 / (volatility or 0.02))
                vol_size = (base_risk_amount * vol_adj) / asset_price
                sizes.append(vol_size)
                
                # Risk parity
                rp_size = (portfolio_value * 0.01) / (asset_price * (volatility or 0.02))
                sizes.append(rp_size)
                
                # Weighted average
                position_size = np.average(sizes[:len(weights)], weights=weights[:len(sizes)])
                
            else:
                # Default to fixed fractional
                position_size = base_risk_amount / asset_price
            
            # Apply signal strength
            position_size *= abs(signal_strength)
            
            # Apply regime and correlation adjustments
            metrics.regime_multiplier = regime_factor
            if correlation_matrix is not None:
                metrics.correlation_adjustment = self._calculate_correlation_adjustment(correlation_matrix)
                position_size *= metrics.correlation_adjustment
            
            # Apply maximum position size limit
            max_position_value = portfolio_value * self.config.max_position_size
            max_position_units = max_position_value / asset_price
            position_size = min(position_size, max_position_units)
            
            # Monte Carlo simulation if enabled
            if self.config.enable_monte_carlo and self.mc_engine:
                mc_results = self.mc_engine.simulate_position(
                    position_size=position_size,
                    asset_price=asset_price,
                    volatility=volatility or 0.02,
                    returns_history=returns_history
                )
                metrics.mc_var = mc_results.get('var', 0.0)
                metrics.mc_expected_return = mc_results.get('expected_return', 0.0)
                metrics.mc_probability_of_loss = mc_results.get('prob_loss', 0.0)
            
            metrics.position_size = float(max(0, position_size))
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating advanced position size: {e}")
            # Return safe default
            metrics = AdvancedRiskMetrics()
            metrics.position_size = (portfolio_value * 0.01) / asset_price  # 1% default
            return metrics
    
    def update_performance_history(
        self,
        trade_return: float,
        portfolio_value: float
    ) -> None:
        """Update performance history for risk calculations"""
        
        self.returns_history.append(trade_return)
        self.portfolio_values.append(portfolio_value)
        
        # Calculate drawdown
        if len(self.portfolio_values) > 1:
            peak = max(self.portfolio_values)
            current_dd = (peak - portfolio_value) / peak
            self.drawdown_history.append(current_dd)
    
    def _calculate_sharpe_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio"""
        try:
            excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
            return float(np.mean(excess_returns) / (np.std(excess_returns) + 1e-6))
        except:
            return 0.0
    
    def _calculate_sortino_ratio(self, returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio"""
        try:
            excess_returns = returns - (risk_free_rate / 252)
            downside_returns = excess_returns[excess_returns < 0]
            downside_std = np.std(downside_returns) if len(downside_returns) > 0 else 1e-6
            return float(np.mean(excess_returns) / downside_std)
        except:
            return 0.0
    
    def _calculate_calmar_ratio(self, returns: np.ndarray) -> float:
        """Calculate Calmar ratio"""
        try:
            annual_return = np.mean(returns) * 252
            max_dd = self._calculate_max_drawdown(returns)
            return float(annual_return / (max_dd + 1e-6))
        except:
            return 0.0
    
    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown"""
        try:
            cumulative = np.cumprod(1 + returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            return float(abs(np.min(drawdown)))
        except:
            return 0.0
    
    def _calculate_correlation_adjustment(self, correlation_matrix: np.ndarray) -> float:
        """Calculate position size adjustment based on correlations"""
        try:
            # Simple correlation adjustment - reduce size if high correlation
            avg_correlation = np.mean(np.abs(correlation_matrix))
            adjustment = 1.0 - (avg_correlation * 0.5)  # Reduce up to 50%
            return float(np.clip(adjustment, 0.5, 1.0))
        except:
            return 1.0


class MonteCarloEngine:
    """Monte Carlo simulation engine for risk analysis"""
    
    def __init__(self, config: AdvancedRiskConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def simulate_position(
        self,
        position_size: float,
        asset_price: float,
        volatility: float,
        returns_history: np.ndarray = None
    ) -> Dict[str, float]:
        """Simulate position outcomes using Monte Carlo"""
        
        try:
            # Generate random returns based on historical distribution
            if returns_history is not None and len(returns_history) > 10:
                mu = np.mean(returns_history)
                sigma = np.std(returns_history)
            else:
                mu = 0.0005  # Default daily return
                sigma = 0.02   # Default daily volatility
            
            # Run simulations
            final_values = []
            
            for _ in range(self.config.mc_simulations):
                # Generate random path
                random_returns = np.random.normal(
                    mu, sigma, self.config.mc_time_horizon
                )
                
                # Calculate final position value
                cumulative_return = np.prod(1 + random_returns) - 1
                final_value = position_size * asset_price * (1 + cumulative_return)
                final_values.append(final_value)
            
            final_values = np.array(final_values)
            initial_value = position_size * asset_price
            
            # Calculate metrics
            returns = (final_values - initial_value) / initial_value
            
            results = {
                'expected_return': float(np.mean(returns)),
                'var': float(np.percentile(returns, 5)),  # 5% VaR
                'prob_loss': float(np.mean(returns < 0)),
                'expected_shortfall': float(np.mean(returns[returns < np.percentile(returns, 5)]))
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Monte Carlo simulation error: {e}")
            return {
                'expected_return': 0.0,
                'var': 0.0,
                'prob_loss': 0.5,
                'expected_shortfall': 0.0
            }


# Factory function
def create_advanced_risk_factory(
    position_sizing_method: AdvancedPositionSizingMethod = AdvancedPositionSizingMethod.KELLY_CRITERION,
    base_risk_per_trade: float = 0.02,
    enable_monte_carlo: bool = True,
    **kwargs
) -> AdvancedRiskFactory:
    """Create an advanced risk factory with specified configuration"""
    
    config = AdvancedRiskConfig(
        position_sizing_method=position_sizing_method,
        base_risk_per_trade=base_risk_per_trade,
        enable_monte_carlo=enable_monte_carlo,
        **kwargs
    )
    
    return AdvancedRiskFactory(config)


# Example usage
if __name__ == "__main__":
    # Create advanced risk factory
    risk_factory = create_advanced_risk_factory(
        position_sizing_method=AdvancedPositionSizingMethod.ENSEMBLE,
        base_risk_per_trade=0.015,
        enable_monte_carlo=True
    )
    
    # Generate sample returns
    sample_returns = np.random.normal(0.001, 0.02, 252)
    
    # Calculate advanced position size
    metrics = risk_factory.calculate_advanced_position_size(
        signal_strength=0.8,
        portfolio_value=100000,
        asset_price=150.0,
        volatility=0.025,
        returns_history=sample_returns,
        regime_factor=1.1
    )
    
    print(f"Position Size: {metrics.position_size:.2f} units")
    print(f"Kelly Fraction: {metrics.kelly_fraction:.3f}")
    print(f"Optimal F: {metrics.optimal_f:.3f}")
    print(f"VaR (95%): {metrics.var_95:.3f}")
    print(f"CVaR (95%): {metrics.cvar_95:.3f}")
    print(f"Sharpe Ratio: {metrics.sharpe_ratio:.3f}")
    print(f"Monte Carlo VaR: {metrics.mc_var:.3f}")
    print(f"MC Probability of Loss: {metrics.mc_probability_of_loss:.3f}")