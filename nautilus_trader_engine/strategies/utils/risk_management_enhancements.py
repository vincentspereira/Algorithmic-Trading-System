#!/usr/bin/env python3
"""
Risk Management Enhancements for Pairs Trading

This module implements advanced risk management features including:
- Dynamic Hedging: Continuous hedge ratio recalibration
- Regime Detection: Adapt strategies to changing market conditions
- Monte Carlo Stress Testing: Comprehensive scenario analysis
- Real-time Correlation Monitoring: Early warning system for relationship breakdown

Author: Algorithmic Trading System
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
from scipy import stats
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# Advanced libraries
try:
    from sklearn.mixture import GaussianMixture
    from sklearn.preprocessing import StandardScaler
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Some regime detection features will be limited.")

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    logging.warning("Plotting libraries not available. Visualization features disabled.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime types"""
    NORMAL = "normal"
    HIGH_VOLATILITY = "high_volatility"
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    CRISIS = "crisis"
    UNKNOWN = "unknown"

class RiskLevel(Enum):
    """Risk level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RiskMetrics:
    """Comprehensive risk metrics"""
    var_1d: float  # 1-day Value at Risk
    var_5d: float  # 5-day Value at Risk
    expected_shortfall: float  # Conditional VaR
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    correlation_breakdown_risk: float
    regime_stability: float
    portfolio_beta: float
    concentration_risk: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class RegimeState:
    """Market regime state information"""
    current_regime: MarketRegime
    regime_probability: float
    regime_duration: int  # Days in current regime
    transition_probability: Dict[MarketRegime, float]
    regime_characteristics: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class StressTestResult:
    """Monte Carlo stress test results"""
    scenarios_tested: int
    worst_case_loss: float
    percentile_losses: Dict[int, float]  # 95th, 99th, 99.9th percentiles
    probability_of_ruin: float
    expected_loss: float
    stress_scenarios: List[Dict[str, float]]
    recovery_time_estimate: float

@dataclass
class CorrelationAlert:
    """Correlation monitoring alert"""
    asset_pair: Tuple[str, str]
    current_correlation: float
    historical_correlation: float
    correlation_change: float
    significance_level: float
    alert_level: RiskLevel
    timestamp: datetime = field(default_factory=datetime.now)
    recommended_action: str = ""

class DynamicHedgingManager:
    """Dynamic hedging with continuous recalibration"""
    
    def __init__(self, recalibration_frequency: int = 5, confidence_threshold: float = 0.95):
        self.recalibration_frequency = recalibration_frequency  # Days
        self.confidence_threshold = confidence_threshold
        self.hedge_history = []
        self.last_recalibration = None
        self.current_hedge_ratio = 1.0
        self.hedge_effectiveness = 0.0
        
    def calculate_optimal_hedge_ratio(self, returns1: pd.Series, returns2: pd.Series, 
                                    method: str = 'ols') -> Tuple[float, float, Dict[str, float]]:
        """Calculate optimal hedge ratio using various methods"""
        
        if len(returns1) != len(returns2) or len(returns1) < 30:
            return 1.0, 0.1, {'r_squared': 0.0, 'effectiveness': 0.0}
        
        # Align data
        aligned_data = pd.DataFrame({'asset1': returns1, 'asset2': returns2}).dropna()
        
        if len(aligned_data) < 30:
            return 1.0, 0.1, {'r_squared': 0.0, 'effectiveness': 0.0}
        
        x = aligned_data['asset2'].values
        y = aligned_data['asset1'].values
        
        if method == 'ols':
            # Ordinary Least Squares
            hedge_ratio = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 1.0
            
            # Calculate R-squared
            y_pred = hedge_ratio * x
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
        elif method == 'variance_minimizing':
            # Minimize portfolio variance
            def portfolio_variance(h):
                portfolio_returns = y - h * x
                return np.var(portfolio_returns)
            
            result = minimize(portfolio_variance, x0=1.0, method='BFGS')
            hedge_ratio = result.x[0]
            
            # Calculate effectiveness
            unhedged_var = np.var(y)
            hedged_var = portfolio_variance(hedge_ratio)
            r_squared = 1 - (hedged_var / unhedged_var) if unhedged_var > 0 else 0
            
        elif method == 'error_correction':
            # Error correction model (simplified)
            # First, estimate cointegration relationship
            hedge_ratio = np.cov(x, y)[0, 1] / np.var(x) if np.var(x) > 0 else 1.0
            
            # Calculate error correction term
            spread = y - hedge_ratio * x
            lagged_spread = np.roll(spread, 1)[1:]
            spread_changes = np.diff(spread)
            
            if len(spread_changes) > 10:
                # Simple error correction coefficient
                ec_coeff = np.cov(spread_changes, lagged_spread)[0, 1] / np.var(lagged_spread) if np.var(lagged_spread) > 0 else 0
                
                # Adjust hedge ratio based on error correction
                hedge_ratio *= (1 + 0.1 * ec_coeff)  # Small adjustment
            
            # Calculate R-squared
            y_pred = hedge_ratio * x
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        else:
            raise ValueError(f"Unknown hedging method: {method}")
        
        # Calculate hedge effectiveness
        unhedged_returns = y
        hedged_returns = y - hedge_ratio * x
        
        unhedged_vol = np.std(unhedged_returns)
        hedged_vol = np.std(hedged_returns)
        
        effectiveness = 1 - (hedged_vol / unhedged_vol) if unhedged_vol > 0 else 0
        
        # Confidence interval for hedge ratio (approximate)
        n = len(aligned_data)
        se_hedge_ratio = np.sqrt((1 - r_squared) / (n - 2)) * np.sqrt(np.var(y) / np.var(x)) if n > 2 and np.var(x) > 0 else 0.1
        
        metrics = {
            'r_squared': r_squared,
            'effectiveness': effectiveness,
            'standard_error': se_hedge_ratio,
            'n_observations': n
        }
        
        return hedge_ratio, se_hedge_ratio, metrics
    
    def should_recalibrate(self, current_date: datetime, force_recalibrate: bool = False) -> bool:
        """Determine if hedge ratio should be recalibrated"""
        if force_recalibrate:
            return True
        
        if self.last_recalibration is None:
            return True
        
        days_since_recalibration = (current_date - self.last_recalibration).days
        return days_since_recalibration >= self.recalibration_frequency
    
    def update_hedge_ratio(self, returns1: pd.Series, returns2: pd.Series, 
                          current_date: datetime, method: str = 'ols') -> Dict[str, Any]:
        """Update hedge ratio if recalibration is needed"""
        
        if not self.should_recalibrate(current_date):
            return {
                'hedge_ratio': self.current_hedge_ratio,
                'recalibrated': False,
                'effectiveness': self.hedge_effectiveness
            }
        
        # Recalibrate
        new_hedge_ratio, std_error, metrics = self.calculate_optimal_hedge_ratio(returns1, returns2, method)
        
        # Update if significantly different and effective
        if metrics['effectiveness'] > 0.1:  # Minimum effectiveness threshold
            self.current_hedge_ratio = new_hedge_ratio
            self.hedge_effectiveness = metrics['effectiveness']
            self.last_recalibration = current_date
            
            # Store in history
            self.hedge_history.append({
                'date': current_date,
                'hedge_ratio': new_hedge_ratio,
                'std_error': std_error,
                'effectiveness': metrics['effectiveness'],
                'r_squared': metrics['r_squared']
            })
            
            return {
                'hedge_ratio': new_hedge_ratio,
                'recalibrated': True,
                'effectiveness': metrics['effectiveness'],
                'confidence_interval': 1.96 * std_error,
                'metrics': metrics
            }
        
        return {
            'hedge_ratio': self.current_hedge_ratio,
            'recalibrated': False,
            'effectiveness': self.hedge_effectiveness,
            'reason': 'Low effectiveness'
        }

class RegimeDetectionEngine:
    """Market regime detection and adaptation"""
    
    def __init__(self, lookback_window: int = 252, n_regimes: int = 3):
        self.lookback_window = lookback_window
        self.n_regimes = n_regimes
        self.regime_model = None
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history = []
        self.regime_probabilities = {}
        
    def extract_regime_features(self, returns1: pd.Series, returns2: pd.Series, 
                               market_data: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Extract features for regime detection"""
        
        # Basic return features
        vol1 = returns1.rolling(20).std()
        vol2 = returns2.rolling(20).std()
        corr = returns1.rolling(20).corr(returns2)
        
        # Spread features
        spread = returns1 - returns2
        spread_vol = spread.rolling(20).std()
        spread_mean = spread.rolling(20).mean()
        
        # Market stress indicators
        joint_vol = np.sqrt(vol1**2 + vol2**2)
        vol_ratio = vol1 / vol2
        
        # Momentum features
        momentum1 = returns1.rolling(10).sum()
        momentum2 = returns2.rolling(10).sum()
        
        # Skewness and kurtosis (rolling)
        skew1 = returns1.rolling(20).skew()
        skew2 = returns2.rolling(20).skew()
        kurt1 = returns1.rolling(20).kurt()
        kurt2 = returns2.rolling(20).kurt()
        
        # Combine features
        features_df = pd.DataFrame({
            'vol1': vol1,
            'vol2': vol2,
            'correlation': corr,
            'spread_vol': spread_vol,
            'spread_mean': spread_mean,
            'joint_vol': joint_vol,
            'vol_ratio': vol_ratio,
            'momentum1': momentum1,
            'momentum2': momentum2,
            'skew1': skew1,
            'skew2': skew2,
            'kurt1': kurt1,
            'kurt2': kurt2
        }).dropna()
        
        return features_df.values
    
    def fit_regime_model(self, returns1: pd.Series, returns2: pd.Series) -> bool:
        """Fit regime detection model"""
        
        try:
            # Extract features
            features = self.extract_regime_features(returns1, returns2)
            
            if len(features) < 50:  # Minimum data requirement
                logger.warning("Insufficient data for regime detection")
                return False
            
            if SKLEARN_AVAILABLE:
                # Use Gaussian Mixture Model for regime detection
                scaler = StandardScaler()
                features_scaled = scaler.fit_transform(features)
                
                self.regime_model = GaussianMixture(
                    n_components=self.n_regimes,
                    covariance_type='full',
                    random_state=42
                )
                
                self.regime_model.fit(features_scaled)
                self.scaler = scaler
                
                # Predict regimes for historical data
                regime_labels = self.regime_model.predict(features_scaled)
                regime_probs = self.regime_model.predict_proba(features_scaled)
                
                # Analyze regime characteristics
                self._analyze_regime_characteristics(features, regime_labels)
                
                logger.info(f"Regime model fitted with {self.n_regimes} regimes")
                return True
            
            else:
                # Simple clustering fallback
                return self._fit_simple_regime_model(features)
                
        except Exception as e:
            logger.error(f"Regime model fitting failed: {e}")
            return False
    
    def _fit_simple_regime_model(self, features: np.ndarray) -> bool:
        """Simple regime detection without sklearn"""
        try:
            # Use simple volatility-based regime detection
            vol_feature = features[:, 0] + features[:, 1]  # Combined volatility
            
            # Define regimes based on volatility percentiles
            low_vol_threshold = np.percentile(vol_feature, 33)
            high_vol_threshold = np.percentile(vol_feature, 67)
            
            self.regime_thresholds = {
                'low_vol': low_vol_threshold,
                'high_vol': high_vol_threshold
            }
            
            logger.info("Simple regime model fitted")
            return True
            
        except Exception as e:
            logger.error(f"Simple regime model fitting failed: {e}")
            return False
    
    def _analyze_regime_characteristics(self, features: np.ndarray, regime_labels: np.ndarray):
        """Analyze characteristics of each regime"""
        self.regime_characteristics = {}
        
        for regime in range(self.n_regimes):
            regime_mask = regime_labels == regime
            regime_features = features[regime_mask]
            
            if len(regime_features) > 0:
                characteristics = {
                    'avg_volatility': np.mean(regime_features[:, 0] + regime_features[:, 1]),
                    'avg_correlation': np.mean(regime_features[:, 2]),
                    'avg_spread_vol': np.mean(regime_features[:, 3]),
                    'frequency': np.sum(regime_mask) / len(regime_labels)
                }
                
                # Classify regime type
                if characteristics['avg_volatility'] > np.percentile(features[:, 0] + features[:, 1], 80):
                    regime_type = MarketRegime.HIGH_VOLATILITY
                elif characteristics['avg_correlation'] < 0.3:
                    regime_type = MarketRegime.CRISIS
                elif characteristics['avg_spread_vol'] < np.percentile(features[:, 3], 30):
                    regime_type = MarketRegime.MEAN_REVERTING
                else:
                    regime_type = MarketRegime.NORMAL
                
                self.regime_characteristics[regime] = {
                    'type': regime_type,
                    'characteristics': characteristics
                }
    
    def detect_current_regime(self, recent_returns1: pd.Series, recent_returns2: pd.Series) -> RegimeState:
        """Detect current market regime"""
        
        if self.regime_model is None:
            return RegimeState(
                current_regime=MarketRegime.UNKNOWN,
                regime_probability=0.0,
                regime_duration=0,
                transition_probability={},
                regime_characteristics={}
            )
        
        try:
            # Extract recent features
            recent_features = self.extract_regime_features(recent_returns1, recent_returns2)
            
            if len(recent_features) == 0:
                return RegimeState(
                    current_regime=self.current_regime,
                    regime_probability=0.5,
                    regime_duration=0,
                    transition_probability={},
                    regime_characteristics={}
                )
            
            if SKLEARN_AVAILABLE and hasattr(self, 'scaler'):
                # Use trained model
                recent_features_scaled = self.scaler.transform(recent_features[-1:])  # Latest observation
                regime_probs = self.regime_model.predict_proba(recent_features_scaled)[0]
                predicted_regime = np.argmax(regime_probs)
                
                # Map to regime type
                regime_type = self.regime_characteristics.get(predicted_regime, {}).get('type', MarketRegime.UNKNOWN)
                
                # Calculate transition probabilities (simplified)
                transition_probs = {regime: prob for regime, prob in 
                                  zip([MarketRegime.NORMAL, MarketRegime.HIGH_VOLATILITY, MarketRegime.CRISIS], 
                                      regime_probs)}
                
                return RegimeState(
                    current_regime=regime_type,
                    regime_probability=regime_probs[predicted_regime],
                    regime_duration=self._calculate_regime_duration(regime_type),
                    transition_probability=transition_probs,
                    regime_characteristics=self.regime_characteristics.get(predicted_regime, {})
                )
            
            else:
                # Simple regime detection
                return self._detect_simple_regime(recent_features)
                
        except Exception as e:
            logger.error(f"Regime detection failed: {e}")
            return RegimeState(
                current_regime=MarketRegime.UNKNOWN,
                regime_probability=0.0,
                regime_duration=0,
                transition_probability={},
                regime_characteristics={}
            )
    
    def _detect_simple_regime(self, features: np.ndarray) -> RegimeState:
        """Simple regime detection fallback"""
        if len(features) == 0:
            return RegimeState(
                current_regime=MarketRegime.UNKNOWN,
                regime_probability=0.0,
                regime_duration=0,
                transition_probability={},
                regime_characteristics={}
            )
        
        # Use volatility-based classification
        current_vol = features[-1, 0] + features[-1, 1]  # Combined volatility
        
        if hasattr(self, 'regime_thresholds'):
            if current_vol > self.regime_thresholds['high_vol']:
                regime = MarketRegime.HIGH_VOLATILITY
                prob = 0.8
            elif current_vol < self.regime_thresholds['low_vol']:
                regime = MarketRegime.MEAN_REVERTING
                prob = 0.7
            else:
                regime = MarketRegime.NORMAL
                prob = 0.6
        else:
            regime = MarketRegime.NORMAL
            prob = 0.5
        
        return RegimeState(
            current_regime=regime,
            regime_probability=prob,
            regime_duration=self._calculate_regime_duration(regime),
            transition_probability={},
            regime_characteristics={}
        )
    
    def _calculate_regime_duration(self, current_regime: MarketRegime) -> int:
        """Calculate how long we've been in current regime"""
        if not self.regime_history:
            return 1
        
        duration = 1
        for i in range(len(self.regime_history) - 1, -1, -1):
            if self.regime_history[i]['regime'] == current_regime:
                duration += 1
            else:
                break
        
        return duration

class MonteCarloStressTester:
    """Monte Carlo stress testing for comprehensive scenario analysis"""
    
    def __init__(self, n_simulations: int = 10000, time_horizon: int = 252):
        self.n_simulations = n_simulations
        self.time_horizon = time_horizon
        self.stress_scenarios = []
        
    def generate_stress_scenarios(self, returns1: pd.Series, returns2: pd.Series, 
                                correlation_shocks: List[float] = [-0.5, -0.3, 0.3, 0.5],
                                volatility_multipliers: List[float] = [1.5, 2.0, 3.0]) -> List[Dict[str, Any]]:
        """Generate stress test scenarios"""
        
        scenarios = []
        
        # Base case parameters
        mu1, mu2 = returns1.mean(), returns2.mean()
        sigma1, sigma2 = returns1.std(), returns2.std()
        base_corr = returns1.corr(returns2)
        
        # Scenario 1: Correlation breakdown
        for corr_shock in correlation_shocks:
            scenarios.append({
                'name': f'Correlation Shock {corr_shock:+.1f}',
                'mu1': mu1, 'mu2': mu2,
                'sigma1': sigma1, 'sigma2': sigma2,
                'correlation': base_corr + corr_shock,
                'type': 'correlation_shock'
            })
        
        # Scenario 2: Volatility shocks
        for vol_mult in volatility_multipliers:
            scenarios.append({
                'name': f'Volatility Shock {vol_mult}x',
                'mu1': mu1, 'mu2': mu2,
                'sigma1': sigma1 * vol_mult, 'sigma2': sigma2 * vol_mult,
                'correlation': base_corr,
                'type': 'volatility_shock'
            })
        
        # Scenario 3: Market crash (negative drift + high volatility)
        scenarios.append({
            'name': 'Market Crash',
            'mu1': mu1 - 3 * sigma1, 'mu2': mu2 - 3 * sigma2,
            'sigma1': sigma1 * 2, 'sigma2': sigma2 * 2,
            'correlation': max(-0.9, base_corr - 0.5),
            'type': 'market_crash'
        })
        
        # Scenario 4: Divergence (assets move in opposite directions)
        scenarios.append({
            'name': 'Asset Divergence',
            'mu1': mu1 + 2 * sigma1, 'mu2': mu2 - 2 * sigma2,
            'sigma1': sigma1 * 1.5, 'sigma2': sigma2 * 1.5,
            'correlation': -0.5,
            'type': 'divergence'
        })
        
        self.stress_scenarios = scenarios
        return scenarios
    
    def run_monte_carlo_simulation(self, scenario: Dict[str, Any], 
                                 initial_position_size: float = 1.0,
                                 hedge_ratio: float = 1.0) -> Dict[str, Any]:
        """Run Monte Carlo simulation for a specific scenario"""
        
        # Extract scenario parameters
        mu1, mu2 = scenario['mu1'], scenario['mu2']
        sigma1, sigma2 = scenario['sigma1'], scenario['sigma2']
        correlation = np.clip(scenario['correlation'], -0.99, 0.99)
        
        # Generate correlated random returns
        np.random.seed(42)  # For reproducibility
        
        # Correlation matrix
        corr_matrix = np.array([[1.0, correlation], [correlation, 1.0]])
        
        # Simulate paths
        portfolio_values = []
        
        for sim in range(self.n_simulations):
            # Generate correlated normal random variables
            random_normals = np.random.multivariate_normal([0, 0], corr_matrix, self.time_horizon)
            
            # Convert to returns
            returns1_sim = mu1 + sigma1 * random_normals[:, 0]
            returns2_sim = mu2 + sigma2 * random_normals[:, 1]
            
            # Calculate portfolio returns (long asset1, short hedge_ratio * asset2)
            portfolio_returns = returns1_sim - hedge_ratio * returns2_sim
            
            # Calculate cumulative portfolio value
            portfolio_value = initial_position_size * np.prod(1 + portfolio_returns)
            portfolio_values.append(portfolio_value)
        
        portfolio_values = np.array(portfolio_values)
        
        # Calculate statistics
        losses = initial_position_size - portfolio_values
        losses = losses[losses > 0]  # Only actual losses
        
        results = {
            'scenario_name': scenario['name'],
            'final_values': portfolio_values,
            'worst_case_loss': np.max(initial_position_size - portfolio_values),
            'expected_final_value': np.mean(portfolio_values),
            'probability_of_loss': np.sum(portfolio_values < initial_position_size) / self.n_simulations,
            'percentile_losses': {
                95: np.percentile(initial_position_size - portfolio_values, 95),
                99: np.percentile(initial_position_size - portfolio_values, 99),
                99.9: np.percentile(initial_position_size - portfolio_values, 99.9)
            },
            'expected_loss': np.mean(losses) if len(losses) > 0 else 0.0,
            'volatility': np.std(portfolio_values)
        }
        
        return results
    
    def comprehensive_stress_test(self, returns1: pd.Series, returns2: pd.Series,
                                hedge_ratio: float = 1.0, position_size: float = 1.0) -> StressTestResult:
        """Run comprehensive stress test across all scenarios"""
        
        # Generate scenarios
        scenarios = self.generate_stress_scenarios(returns1, returns2)
        
        # Run simulations for each scenario
        all_results = []
        worst_case_overall = 0.0
        
        for scenario in scenarios:
            result = self.run_monte_carlo_simulation(scenario, position_size, hedge_ratio)
            all_results.append(result)
            
            if result['worst_case_loss'] > worst_case_overall:
                worst_case_overall = result['worst_case_loss']
        
        # Aggregate results
        all_losses_95 = [r['percentile_losses'][95] for r in all_results]
        all_losses_99 = [r['percentile_losses'][99] for r in all_results]
        all_losses_999 = [r['percentile_losses'][99.9] for r in all_results]
        
        # Calculate probability of ruin (loss > 50% of capital)
        ruin_threshold = position_size * 0.5
        prob_of_ruin = np.mean([r['worst_case_loss'] > ruin_threshold for r in all_results])
        
        # Estimate recovery time (simplified)
        expected_return = (returns1.mean() - hedge_ratio * returns2.mean()) * 252  # Annualized
        recovery_time = (worst_case_overall / abs(expected_return)) if expected_return != 0 else float('inf')
        
        return StressTestResult(
            scenarios_tested=len(scenarios),
            worst_case_loss=worst_case_overall,
            percentile_losses={
                95: np.max(all_losses_95),
                99: np.max(all_losses_99),
                99.9: np.max(all_losses_999)
            },
            probability_of_ruin=prob_of_ruin,
            expected_loss=np.mean([r['expected_loss'] for r in all_results]),
            stress_scenarios=scenarios,
            recovery_time_estimate=recovery_time
        )

class CorrelationMonitor:
    """Real-time correlation monitoring and early warning system"""
    
    def __init__(self, lookback_window: int = 60, alert_threshold: float = 0.2):
        self.lookback_window = lookback_window
        self.alert_threshold = alert_threshold
        self.correlation_history = []
        self.alerts = []
        
    def calculate_rolling_correlation(self, returns1: pd.Series, returns2: pd.Series, 
                                    window: int = None) -> pd.Series:
        """Calculate rolling correlation"""
        if window is None:
            window = self.lookback_window
        
        return returns1.rolling(window=window, min_periods=window//2).corr(returns2)
    
    def detect_correlation_breakdown(self, returns1: pd.Series, returns2: pd.Series,
                                   asset_names: Tuple[str, str] = ('Asset1', 'Asset2')) -> List[CorrelationAlert]:
        """Detect correlation breakdown and generate alerts"""
        
        alerts = []
        
        # Calculate correlations
        short_corr = self.calculate_rolling_correlation(returns1, returns2, window=20)
        long_corr = self.calculate_rolling_correlation(returns1, returns2, window=self.lookback_window)
        
        if len(short_corr.dropna()) == 0 or len(long_corr.dropna()) == 0:
            return alerts
        
        # Get latest values
        current_short_corr = short_corr.dropna().iloc[-1]
        current_long_corr = long_corr.dropna().iloc[-1]
        
        # Calculate correlation change
        correlation_change = abs(current_short_corr - current_long_corr)
        
        # Determine alert level
        if correlation_change > self.alert_threshold * 2:
            alert_level = RiskLevel.CRITICAL
            recommended_action = "Immediate position review required. Consider reducing exposure."
        elif correlation_change > self.alert_threshold * 1.5:
            alert_level = RiskLevel.HIGH
            recommended_action = "Monitor closely. Consider hedge ratio adjustment."
        elif correlation_change > self.alert_threshold:
            alert_level = RiskLevel.MEDIUM
            recommended_action = "Increased monitoring recommended."
        else:
            alert_level = RiskLevel.LOW
            recommended_action = "Normal correlation levels."
        
        # Statistical significance test
        n = min(len(returns1), len(returns2))
        if n > 30:
            # Fisher's z-transformation for correlation comparison
            z1 = 0.5 * np.log((1 + current_short_corr) / (1 - current_short_corr))
            z2 = 0.5 * np.log((1 + current_long_corr) / (1 - current_long_corr))
            
            se = np.sqrt(1/(20-3) + 1/(self.lookback_window-3))
            z_stat = abs(z1 - z2) / se
            p_value = 2 * (1 - stats.norm.cdf(abs(z_stat)))
            
            significance_level = p_value
        else:
            significance_level = 1.0  # Not enough data for significance test
        
        # Create alert if significant
        if correlation_change > self.alert_threshold or significance_level < 0.05:
            alert = CorrelationAlert(
                asset_pair=asset_names,
                current_correlation=current_short_corr,
                historical_correlation=current_long_corr,
                correlation_change=correlation_change,
                significance_level=significance_level,
                alert_level=alert_level,
                recommended_action=recommended_action
            )
            
            alerts.append(alert)
            self.alerts.append(alert)
        
        return alerts
    
    def get_correlation_stability_score(self, returns1: pd.Series, returns2: pd.Series) -> float:
        """Calculate correlation stability score (0-1, higher is more stable)"""
        
        rolling_corr = self.calculate_rolling_correlation(returns1, returns2, window=30)
        
        if len(rolling_corr.dropna()) < 10:
            return 0.5  # Neutral score for insufficient data
        
        # Calculate coefficient of variation of correlations
        corr_values = rolling_corr.dropna()
        corr_std = corr_values.std()
        corr_mean = abs(corr_values.mean())
        
        if corr_mean == 0:
            return 0.0
        
        cv = corr_std / corr_mean
        
        # Convert to stability score (lower CV = higher stability)
        stability_score = 1 / (1 + cv)
        
        return np.clip(stability_score, 0.0, 1.0)

class RiskManagementEngine:
    """Main risk management engine combining all components"""
    
    def __init__(self):
        self.hedging_manager = DynamicHedgingManager()
        self.regime_detector = RegimeDetectionEngine()
        self.stress_tester = MonteCarloStressTester()
        self.correlation_monitor = CorrelationMonitor()
        self.risk_history = []
        
    def initialize(self, returns1: pd.Series, returns2: pd.Series) -> bool:
        """Initialize all risk management components"""
        logger.info("Initializing Risk Management Engine...")
        
        try:
            # Fit regime detection model
            regime_success = self.regime_detector.fit_regime_model(returns1, returns2)
            
            logger.info(f"Risk Management Engine initialized - Regime Detection: {regime_success}")
            return True
            
        except Exception as e:
            logger.error(f"Risk Management Engine initialization failed: {e}")
            return False
    
    def comprehensive_risk_assessment(self, returns1: pd.Series, returns2: pd.Series,
                                    current_position_size: float = 1.0,
                                    asset_names: Tuple[str, str] = ('Asset1', 'Asset2')) -> Dict[str, Any]:
        """Perform comprehensive risk assessment"""
        
        assessment = {
            'timestamp': datetime.now(),
            'asset_pair': asset_names
        }
        
        # 1. Dynamic hedging analysis
        hedge_update = self.hedging_manager.update_hedge_ratio(returns1, returns2, datetime.now())
        assessment['hedging'] = hedge_update
        
        # 2. Regime detection
        current_regime = self.regime_detector.detect_current_regime(returns1, returns2)
        assessment['regime'] = current_regime
        
        # 3. Correlation monitoring
        correlation_alerts = self.correlation_monitor.detect_correlation_breakdown(returns1, returns2, asset_names)
        correlation_stability = self.correlation_monitor.get_correlation_stability_score(returns1, returns2)
        assessment['correlation'] = {
            'alerts': correlation_alerts,
            'stability_score': correlation_stability
        }
        
        # 4. Stress testing
        stress_results = self.stress_tester.comprehensive_stress_test(
            returns1, returns2, 
            hedge_ratio=hedge_update['hedge_ratio'],
            position_size=current_position_size
        )
        assessment['stress_test'] = stress_results
        
        # 5. Calculate comprehensive risk metrics
        risk_metrics = self._calculate_risk_metrics(returns1, returns2, current_position_size, hedge_update['hedge_ratio'])
        assessment['risk_metrics'] = risk_metrics
        
        # 6. Generate risk recommendations
        recommendations = self._generate_risk_recommendations(assessment)
        assessment['recommendations'] = recommendations
        
        # Store in history
        self.risk_history.append(assessment)
        
        return assessment
    
    def _calculate_risk_metrics(self, returns1: pd.Series, returns2: pd.Series, 
                              position_size: float, hedge_ratio: float) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        
        # Portfolio returns
        portfolio_returns = returns1 - hedge_ratio * returns2
        
        if len(portfolio_returns) < 30:
            return RiskMetrics(
                var_1d=0.0, var_5d=0.0, expected_shortfall=0.0,
                max_drawdown=0.0, sharpe_ratio=0.0, sortino_ratio=0.0,
                correlation_breakdown_risk=0.5, regime_stability=0.5,
                portfolio_beta=1.0, concentration_risk=0.5
            )
        
        # VaR calculations
        var_1d = np.percentile(portfolio_returns, 5) * position_size
        var_5d = np.percentile(portfolio_returns, 5) * np.sqrt(5) * position_size
        
        # Expected Shortfall
        expected_shortfall = portfolio_returns[portfolio_returns <= np.percentile(portfolio_returns, 5)].mean() * position_size
        
        # Maximum Drawdown
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Sharpe Ratio
        excess_returns = portfolio_returns - 0.02/252  # Assume 2% risk-free rate
        sharpe_ratio = excess_returns.mean() / portfolio_returns.std() * np.sqrt(252) if portfolio_returns.std() > 0 else 0
        
        # Sortino Ratio
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else portfolio_returns.std()
        sortino_ratio = excess_returns.mean() / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Correlation breakdown risk
        correlation_stability = self.correlation_monitor.get_correlation_stability_score(returns1, returns2)
        correlation_breakdown_risk = 1 - correlation_stability
        
        # Regime stability (simplified)
        regime_stability = 0.7  # Placeholder
        
        # Portfolio beta (relative to market - simplified)
        market_proxy = (returns1 + returns2) / 2  # Simple market proxy
        portfolio_beta = np.cov(portfolio_returns, market_proxy)[0, 1] / np.var(market_proxy) if np.var(market_proxy) > 0 else 1.0
        
        # Concentration risk (simplified - based on hedge ratio deviation from 1)
        concentration_risk = min(1.0, abs(hedge_ratio - 1.0))
        
        return RiskMetrics(
            var_1d=var_1d,
            var_5d=var_5d,
            expected_shortfall=expected_shortfall,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            correlation_breakdown_risk=correlation_breakdown_risk,
            regime_stability=regime_stability,
            portfolio_beta=portfolio_beta,
            concentration_risk=concentration_risk
        )
    
    def _generate_risk_recommendations(self, assessment: Dict[str, Any]) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        # Hedging recommendations
        if assessment['hedging']['recalibrated']:
            recommendations.append(f"Hedge ratio updated to {assessment['hedging']['hedge_ratio']:.4f}")
        
        if assessment['hedging']['effectiveness'] < 0.3:
            recommendations.append("Low hedge effectiveness detected. Consider alternative hedging strategies.")
        
        # Regime-based recommendations
        regime = assessment['regime']['current_regime']
        if regime == MarketRegime.HIGH_VOLATILITY:
            recommendations.append("High volatility regime detected. Consider reducing position size.")
        elif regime == MarketRegime.CRISIS:
            recommendations.append("Crisis regime detected. Implement defensive positioning.")
        
        # Correlation recommendations
        if assessment['correlation']['alerts']:
            recommendations.append("Correlation breakdown detected. Monitor positions closely.")
        
        if assessment['correlation']['stability_score'] < 0.5:
            recommendations.append("Low correlation stability. Consider more frequent rebalancing.")
        
        # Stress test recommendations
        stress_results = assessment['stress_test']
        if stress_results.probability_of_ruin > 0.1:
            recommendations.append(f"High probability of significant loss ({stress_results.probability_of_ruin:.1%}). Consider risk reduction.")
        
        # Risk metrics recommendations
        risk_metrics = assessment['risk_metrics']
        if risk_metrics.max_drawdown < -0.2:
            recommendations.append("High maximum drawdown detected. Review position sizing.")
        
        if risk_metrics.sharpe_ratio < 0.5:
            recommendations.append("Low risk-adjusted returns. Consider strategy optimization.")
        
        return recommendations

# Example usage and testing
def test_risk_management_enhancements():
    """Test the risk management enhancements"""
    print("Testing Risk Management Enhancements")
    print("=" * 50)
    
    # Generate synthetic data
    np.random.seed(42)
    n_points = 500
    
    # Correlated return series with regime changes
    base_corr = 0.7
    returns1 = np.random.normal(0.0005, 0.02, n_points)
    
    # Introduce regime change at midpoint
    returns2 = np.zeros(n_points)
    returns2[:n_points//2] = base_corr * returns1[:n_points//2] + np.random.normal(0, 0.015, n_points//2)
    returns2[n_points//2:] = 0.2 * returns1[n_points//2:] + np.random.normal(0, 0.025, n_points//2)  # Correlation breakdown
    
    returns1_series = pd.Series(returns1)
    returns2_series = pd.Series(returns2)
    
    # Initialize risk management engine
    risk_engine = RiskManagementEngine()
    risk_engine.initialize(returns1_series, returns2_series)
    
    # Perform comprehensive risk assessment
    print("\nPerforming Comprehensive Risk Assessment:")
    assessment = risk_engine.comprehensive_risk_assessment(
        returns1_series, returns2_series, 
        current_position_size=100000,
        asset_names=('AAPL', 'GOOGL')
    )
    
    # Display results
    print(f"\nHedging Analysis:")
    print(f"  Current Hedge Ratio: {assessment['hedging']['hedge_ratio']:.4f}")
    print(f"  Hedge Effectiveness: {assessment['hedging']['effectiveness']:.3f}")
    print(f"  Recalibrated: {assessment['hedging']['recalibrated']}")
    
    print(f"\nRegime Detection:")
    print(f"  Current Regime: {assessment['regime']['current_regime'].value}")
    print(f"  Regime Probability: {assessment['regime']['regime_probability']:.3f}")
    print(f"  Regime Duration: {assessment['regime']['regime_duration']} periods")
    
    print(f"\nCorrelation Monitoring:")
    print(f"  Stability Score: {assessment['correlation']['stability_score']:.3f}")
    print(f"  Active Alerts: {len(assessment['correlation']['alerts'])}")
    
    print(f"\nStress Test Results:")
    print(f"  Worst Case Loss: ${assessment['stress_test'].worst_case_loss:,.2f}")
    print(f"  99th Percentile Loss: ${assessment['stress_test'].percentile_losses[99]:,.2f}")
    print(f"  Probability of Ruin: {assessment['stress_test'].probability_of_ruin:.1%}")
    
    print(f"\nRisk Metrics:")
    print(f"  1-Day VaR: ${assessment['risk_metrics'].var_1d:,.2f}")
    print(f"  Sharpe Ratio: {assessment['risk_metrics'].sharpe_ratio:.3f}")
    print(f"  Max Drawdown: {assessment['risk_metrics'].max_drawdown:.1%}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(assessment['recommendations'], 1):
        print(f"  {i}. {rec}")

if __name__ == "__main__":
    test_risk_management_enhancements()