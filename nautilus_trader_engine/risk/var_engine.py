"""
Real-Time VaR Calculation Engine
Provides comprehensive Value at Risk calculation with multiple methodologies,
GARCH volatility forecasting, backtesting, and model validation.
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

try:
    from scipy import stats
    from scipy.optimize import minimize
    import arch
    SCIPY_AVAILABLE = True
except ImportError:
    stats = None
    minimize = None
    arch = None
    SCIPY_AVAILABLE = False

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

@dataclass
class VaRResult:
    """VaR calculation result"""
    method: VaRMethod
    confidence_level: float
    var_value: float
    expected_shortfall: float
    portfolio_value: float
    calculation_time: datetime
    horizon_days: int = 1
    currency: str = "USD"
    components: Dict[str, float] = field(default_factory=dict)
    model_parameters: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def var_percentage(self) -> float:
        """VaR as percentage of portfolio value"""
        return (self.var_value / self.portfolio_value) * 100 if self.portfolio_value != 0 else 0

@dataclass
class BacktestResult:
    """VaR backtesting result"""
    method: VaRMethod
    confidence_level: float
    total_observations: int
    violations: int
    violation_rate: float
    expected_violations: int
    kupiec_pof_statistic: float
    kupiec_p_value: float
    is_model_valid: bool
    traffic_light: str  # Green, Yellow, Red
    
class GARCHModel:
    """GARCH model for volatility forecasting"""
    
    def __init__(self, p: int = 1, q: int = 1):
        self.p = p  # ARCH terms
        self.q = q  # GARCH terms
        self.model = None
        self.fitted_model = None
        self.logger = logging.getLogger(__name__)
    
    def fit(self, returns: pd.Series) -> Dict[str, Any]:
        """Fit GARCH model to return series"""
        try:
            if not SCIPY_AVAILABLE:
                raise ImportError("ARCH package required for GARCH modeling")
            
            # Remove any NaN values
            returns = returns.dropna()
            
            # Convert to percentage returns for better numerical stability
            returns_pct = returns * 100
            
            # Create GARCH model
            self.model = arch.arch_model(
                returns_pct, 
                vol='GARCH', 
                p=self.p, 
                q=self.q,
                dist='normal'
            )
            
            # Fit the model
            self.fitted_model = self.model.fit(disp='off')
            
            # Extract parameters
            params = {
                'omega': self.fitted_model.params['omega'],
                'alpha': [self.fitted_model.params[f'alpha[{i+1}]'] for i in range(self.p)],
                'beta': [self.fitted_model.params[f'beta[{i+1}]'] for i in range(self.q)],
                'aic': self.fitted_model.aic,
                'bic': self.fitted_model.bic,
                'log_likelihood': self.fitted_model.loglikelihood
            }
            
            self.logger.info(f"GARCH({self.p},{self.q}) model fitted successfully")
            return params
            
        except Exception as e:
            self.logger.error(f"Error fitting GARCH model: {e}")
            return {}
    
    def forecast_volatility(self, horizon: int = 1) -> float:
        """Forecast volatility for given horizon"""
        try:
            if self.fitted_model is None:
                raise ValueError("Model must be fitted before forecasting")
            
            # Get volatility forecast
            forecast = self.fitted_model.forecast(horizon=horizon)
            
            # Extract forecasted variance and convert to volatility
            forecasted_variance = forecast.variance.iloc[-1, 0]
            forecasted_volatility = np.sqrt(forecasted_variance) / 100  # Convert back from percentage
            
            return forecasted_volatility
            
        except Exception as e:
            self.logger.error(f"Error forecasting volatility: {e}")
            return 0.0

class VaREngine:
    """Real-time VaR calculation engine"""
    
    def __init__(self, 
                 default_confidence_level: float = 0.95,
                 default_horizon: int = 1,
                 max_workers: int = 4):
        self.default_confidence_level = default_confidence_level
        self.default_horizon = default_horizon
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(__name__)
        
        # Cache for model parameters and results
        self.model_cache: Dict[str, Any] = {}
        self.result_cache: Dict[str, VaRResult] = {}
        
        # Historical data storage
        self.price_history: Dict[str, pd.Series] = {}
        self.return_history: Dict[str, pd.Series] = {}
    
    def add_price_data(self, symbol: str, prices: pd.Series):
        """Add price data for a symbol"""
        self.price_history[symbol] = prices
        
        # Calculate returns
        returns = prices.pct_change().dropna()
        self.return_history[symbol] = returns
        
        self.logger.debug(f"Added {len(prices)} price points for {symbol}")
    
    def calculate_historical_var(self, 
                                returns: pd.Series,
                                confidence_level: float = None,
                                portfolio_value: float = 1000000) -> VaRResult:
        """Calculate VaR using historical simulation method"""
        confidence_level = confidence_level or self.default_confidence_level
        
        try:
            # Remove NaN values
            returns = returns.dropna()
            
            if len(returns) < 30:
                raise ValueError("Insufficient data for historical VaR calculation")
            
            # Calculate VaR as percentile
            var_percentile = (1 - confidence_level) * 100
            var_return = np.percentile(returns, var_percentile)
            var_value = abs(var_return * portfolio_value)
            
            # Calculate Expected Shortfall (Conditional VaR)
            tail_returns = returns[returns <= var_return]
            expected_shortfall = abs(tail_returns.mean() * portfolio_value) if len(tail_returns) > 0 else var_value
            
            return VaRResult(
                method=VaRMethod.HISTORICAL,
                confidence_level=confidence_level,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                calculation_time=datetime.now(),
                model_parameters={
                    'sample_size': len(returns),
                    'var_return': var_return,
                    'tail_observations': len(tail_returns)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating historical VaR: {e}")
            raise
    
    def calculate_parametric_var(self,
                                returns: pd.Series,
                                confidence_level: float = None,
                                portfolio_value: float = 1000000) -> VaRResult:
        """Calculate VaR using parametric (normal distribution) method"""
        confidence_level = confidence_level or self.default_confidence_level
        
        try:
            # Remove NaN values
            returns = returns.dropna()
            
            if len(returns) < 30:
                raise ValueError("Insufficient data for parametric VaR calculation")
            
            # Calculate mean and standard deviation
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Calculate VaR using normal distribution
            if SCIPY_AVAILABLE:
                z_score = stats.norm.ppf(1 - confidence_level)
            else:
                # Approximate z-scores for common confidence levels
                z_scores = {0.90: -1.282, 0.95: -1.645, 0.99: -2.326, 0.999: -3.090}
                z_score = z_scores.get(confidence_level, -1.645)
            
            var_return = mean_return + z_score * std_return
            var_value = abs(var_return * portfolio_value)
            
            # Calculate Expected Shortfall for normal distribution
            if SCIPY_AVAILABLE:
                phi_z = stats.norm.pdf(z_score)
                expected_shortfall_return = mean_return - (phi_z / (1 - confidence_level)) * std_return
            else:
                # Approximation for expected shortfall
                expected_shortfall_return = var_return * 1.2
            
            expected_shortfall = abs(expected_shortfall_return * portfolio_value)
            
            return VaRResult(
                method=VaRMethod.PARAMETRIC,
                confidence_level=confidence_level,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                calculation_time=datetime.now(),
                model_parameters={
                    'mean_return': mean_return,
                    'std_return': std_return,
                    'z_score': z_score,
                    'sample_size': len(returns)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating parametric VaR: {e}")
            raise
    
    def calculate_monte_carlo_var(self,
                                 returns: pd.Series,
                                 confidence_level: float = None,
                                 portfolio_value: float = 1000000,
                                 num_simulations: int = 10000) -> VaRResult:
        """Calculate VaR using Monte Carlo simulation"""
        confidence_level = confidence_level or self.default_confidence_level
        
        try:
            # Remove NaN values
            returns = returns.dropna()
            
            if len(returns) < 30:
                raise ValueError("Insufficient data for Monte Carlo VaR calculation")
            
            # Calculate parameters from historical data
            mean_return = returns.mean()
            std_return = returns.std()
            
            # Generate random scenarios
            np.random.seed(42)  # For reproducibility
            simulated_returns = np.random.normal(mean_return, std_return, num_simulations)
            
            # Calculate VaR from simulated returns
            var_percentile = (1 - confidence_level) * 100
            var_return = np.percentile(simulated_returns, var_percentile)
            var_value = abs(var_return * portfolio_value)
            
            # Calculate Expected Shortfall
            tail_returns = simulated_returns[simulated_returns <= var_return]
            expected_shortfall = abs(tail_returns.mean() * portfolio_value) if len(tail_returns) > 0 else var_value
            
            return VaRResult(
                method=VaRMethod.MONTE_CARLO,
                confidence_level=confidence_level,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                calculation_time=datetime.now(),
                model_parameters={
                    'num_simulations': num_simulations,
                    'mean_return': mean_return,
                    'std_return': std_return,
                    'var_return': var_return
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating Monte Carlo VaR: {e}")
            raise
    
    def calculate_garch_var(self,
                           returns: pd.Series,
                           confidence_level: float = None,
                           portfolio_value: float = 1000000,
                           horizon: int = 1) -> VaRResult:
        """Calculate VaR using GARCH volatility forecasting"""
        confidence_level = confidence_level or self.default_confidence_level
        
        try:
            # Remove NaN values
            returns = returns.dropna()
            
            if len(returns) < 100:
                raise ValueError("Insufficient data for GARCH VaR calculation (minimum 100 observations)")
            
            # Fit GARCH model
            garch_model = GARCHModel(p=1, q=1)
            model_params = garch_model.fit(returns)
            
            if not model_params:
                # Fallback to parametric method if GARCH fails
                self.logger.warning("GARCH model fitting failed, falling back to parametric method")
                return self.calculate_parametric_var(returns, confidence_level, portfolio_value)
            
            # Forecast volatility
            forecasted_volatility = garch_model.forecast_volatility(horizon)
            
            # Calculate mean return
            mean_return = returns.mean()
            
            # Calculate VaR using forecasted volatility
            if SCIPY_AVAILABLE:
                z_score = stats.norm.ppf(1 - confidence_level)
            else:
                z_scores = {0.90: -1.282, 0.95: -1.645, 0.99: -2.326, 0.999: -3.090}
                z_score = z_scores.get(confidence_level, -1.645)
            
            # Adjust for horizon
            horizon_adjustment = np.sqrt(horizon)
            var_return = mean_return * horizon + z_score * forecasted_volatility * horizon_adjustment
            var_value = abs(var_return * portfolio_value)
            
            # Calculate Expected Shortfall
            if SCIPY_AVAILABLE:
                phi_z = stats.norm.pdf(z_score)
                expected_shortfall_return = (mean_return * horizon - 
                                           (phi_z / (1 - confidence_level)) * forecasted_volatility * horizon_adjustment)
            else:
                expected_shortfall_return = var_return * 1.2
            
            expected_shortfall = abs(expected_shortfall_return * portfolio_value)
            
            # Combine model parameters
            combined_params = {
                'forecasted_volatility': forecasted_volatility,
                'mean_return': mean_return,
                'horizon': horizon,
                'z_score': z_score,
                **model_params
            }
            
            return VaRResult(
                method=VaRMethod.GARCH,
                confidence_level=confidence_level,
                var_value=var_value,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_value,
                calculation_time=datetime.now(),
                horizon_days=horizon,
                model_parameters=combined_params
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating GARCH VaR: {e}")
            # Fallback to parametric method
            return self.calculate_parametric_var(returns, confidence_level, portfolio_value)
    
    async def calculate_var_async(self,
                                 returns: pd.Series,
                                 method: VaRMethod = VaRMethod.HISTORICAL,
                                 confidence_level: float = None,
                                 portfolio_value: float = 1000000,
                                 **kwargs) -> VaRResult:
        """Calculate VaR asynchronously"""
        loop = asyncio.get_event_loop()
        
        # Map methods to functions
        method_map = {
            VaRMethod.HISTORICAL: self.calculate_historical_var,
            VaRMethod.PARAMETRIC: self.calculate_parametric_var,
            VaRMethod.MONTE_CARLO: self.calculate_monte_carlo_var,
            VaRMethod.GARCH: self.calculate_garch_var
        }
        
        if method not in method_map:
            raise ValueError(f"Unsupported VaR method: {method}")
        
        # Execute calculation in thread pool
        func = method_map[method]
        result = await loop.run_in_executor(
            self.executor,
            lambda: func(returns, confidence_level, portfolio_value, **kwargs)
        )
        
        return result
    
    def calculate_portfolio_var(self,
                               portfolio_returns: Dict[str, pd.Series],
                               weights: Dict[str, float],
                               method: VaRMethod = VaRMethod.HISTORICAL,
                               confidence_level: float = None,
                               portfolio_value: float = 1000000) -> VaRResult:
        """Calculate portfolio VaR considering correlations"""
        confidence_level = confidence_level or self.default_confidence_level
        
        try:
            # Align all return series
            returns_df = pd.DataFrame(portfolio_returns).dropna()
            
            if returns_df.empty:
                raise ValueError("No valid return data for portfolio VaR calculation")
            
            # Calculate weighted portfolio returns
            weights_array = np.array([weights.get(symbol, 0) for symbol in returns_df.columns])
            weights_array = weights_array / weights_array.sum()  # Normalize weights
            
            portfolio_returns_series = (returns_df * weights_array).sum(axis=1)
            
            # Calculate VaR using specified method
            var_result = self.calculate_var_async(
                portfolio_returns_series, 
                method, 
                confidence_level, 
                portfolio_value
            )
            
            # Add component VaR analysis
            components = {}
            for symbol in returns_df.columns:
                weight = weights.get(symbol, 0)
                symbol_returns = returns_df[symbol]
                
                # Calculate marginal VaR contribution
                correlation = portfolio_returns_series.corr(symbol_returns)
                symbol_var = self.calculate_historical_var(
                    symbol_returns, 
                    confidence_level, 
                    portfolio_value * weight
                ).var_value
                
                # Component VaR = Weight * Marginal VaR * Correlation
                component_var = weight * symbol_var * correlation
                components[symbol] = component_var
            
            # Update result with components
            if hasattr(var_result, 'components'):
                var_result.components = components
            
            return var_result
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio VaR: {e}")
            raise
    
    def backtest_var_model(self,
                          returns: pd.Series,
                          var_results: List[VaRResult],
                          actual_returns: pd.Series) -> BacktestResult:
        """Backtest VaR model using Kupiec POF test"""
        try:
            if len(var_results) != len(actual_returns):
                raise ValueError("VaR results and actual returns must have same length")
            
            if not var_results:
                raise ValueError("No VaR results provided for backtesting")
            
            # Get method and confidence level from first result
            method = var_results[0].method
            confidence_level = var_results[0].confidence_level
            
            # Count violations
            violations = 0
            total_observations = len(var_results)
            
            for i, (var_result, actual_return) in enumerate(zip(var_results, actual_returns)):
                # Convert VaR to return space
                portfolio_value = var_result.portfolio_value
                var_return = -var_result.var_value / portfolio_value
                
                # Check if actual return exceeds VaR
                if actual_return < var_return:
                    violations += 1
            
            violation_rate = violations / total_observations
            expected_violations = int(total_observations * (1 - confidence_level))
            
            # Kupiec Proportion of Failures (POF) test
            if SCIPY_AVAILABLE and violations > 0:
                # Calculate likelihood ratio statistic
                p = 1 - confidence_level  # Expected violation rate
                lr_stat = 2 * (violations * np.log(violation_rate / p) + 
                              (total_observations - violations) * np.log((1 - violation_rate) / (1 - p)))
                
                # P-value from chi-square distribution with 1 degree of freedom
                p_value = 1 - stats.chi2.cdf(lr_stat, df=1)
            else:
                lr_stat = 0.0
                p_value = 1.0
            
            # Model validation (5% significance level)
            is_model_valid = p_value > 0.05
            
            # Traffic light approach (Basel Committee)
            if violation_rate <= (1 - confidence_level):
                traffic_light = "Green"
            elif violation_rate <= (1 - confidence_level) * 1.5:
                traffic_light = "Yellow"
            else:
                traffic_light = "Red"
            
            return BacktestResult(
                method=method,
                confidence_level=confidence_level,
                total_observations=total_observations,
                violations=violations,
                violation_rate=violation_rate,
                expected_violations=expected_violations,
                kupiec_pof_statistic=lr_stat,
                kupiec_p_value=p_value,
                is_model_valid=is_model_valid,
                traffic_light=traffic_light
            )
            
        except Exception as e:
            self.logger.error(f"Error backtesting VaR model: {e}")
            raise
    
    def get_var_summary(self, 
                       returns: pd.Series,
                       portfolio_value: float = 1000000,
                       confidence_levels: List[float] = None) -> Dict[str, VaRResult]:
        """Get VaR summary using multiple methods and confidence levels"""
        confidence_levels = confidence_levels or [0.95, 0.99]
        
        results = {}
        methods = [VaRMethod.HISTORICAL, VaRMethod.PARAMETRIC, VaRMethod.MONTE_CARLO]
        
        # Add GARCH if sufficient data
        if len(returns.dropna()) >= 100:
            methods.append(VaRMethod.GARCH)
        
        for method in methods:
            for confidence_level in confidence_levels:
                try:
                    if method == VaRMethod.HISTORICAL:
                        result = self.calculate_historical_var(returns, confidence_level, portfolio_value)
                    elif method == VaRMethod.PARAMETRIC:
                        result = self.calculate_parametric_var(returns, confidence_level, portfolio_value)
                    elif method == VaRMethod.MONTE_CARLO:
                        result = self.calculate_monte_carlo_var(returns, confidence_level, portfolio_value)
                    elif method == VaRMethod.GARCH:
                        result = self.calculate_garch_var(returns, confidence_level, portfolio_value)
                    
                    key = f"{method.value}_{int(confidence_level*100)}"
                    results[key] = result
                    
                except Exception as e:
                    self.logger.warning(f"Failed to calculate {method.value} VaR at {confidence_level}: {e}")
        
        return results
    
    def __del__(self):
        """Cleanup thread pool executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

# Factory function for easy initialization
def create_var_engine(confidence_level: float = 0.95, 
                     horizon: int = 1,
                     max_workers: int = 4) -> VaREngine:
    """Create VaR calculation engine"""
    return VaREngine(
        default_confidence_level=confidence_level,
        default_horizon=horizon,
        max_workers=max_workers
    )

# Example usage and testing
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    returns = pd.Series(np.random.normal(0.001, 0.02, 500), index=dates)
    
    # Create VaR engine
    var_engine = create_var_engine()
    
    print("🧮 VaR Calculation Engine Test")
    print("=" * 40)
    
    # Test different methods
    portfolio_value = 1000000
    
    try:
        # Historical VaR
        hist_var = var_engine.calculate_historical_var(returns, 0.95, portfolio_value)
        print(f"Historical VaR (95%): ${hist_var.var_value:,.2f}")
        print(f"Expected Shortfall: ${hist_var.expected_shortfall:,.2f}")
        
        # Parametric VaR
        param_var = var_engine.calculate_parametric_var(returns, 0.95, portfolio_value)
        print(f"Parametric VaR (95%): ${param_var.var_value:,.2f}")
        
        # Monte Carlo VaR
        mc_var = var_engine.calculate_monte_carlo_var(returns, 0.95, portfolio_value)
        print(f"Monte Carlo VaR (95%): ${mc_var.var_value:,.2f}")
        
        # GARCH VaR (if available)
        try:
            garch_var = var_engine.calculate_garch_var(returns, 0.95, portfolio_value)
            print(f"GARCH VaR (95%): ${garch_var.var_value:,.2f}")
        except Exception as e:
            print(f"GARCH VaR not available: {e}")
        
        print("\n✅ VaR Engine test completed successfully!")
        
    except Exception as e:
        print(f"❌ VaR Engine test failed: {e}")