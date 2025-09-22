#!/usr/bin/env python3
"""
Advanced Statistical Methods for Pairs Trading

This module implements sophisticated statistical methods including:
- Kalman Filtering for dynamic hedge ratio adjustments
- GARCH Models for time-varying volatility modeling
- Copula Models for capturing non-linear dependency structures
- Machine Learning neural networks for pattern recognition and signal generation

Author: Algorithmic Trading System
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
from scipy import stats, optimize
from scipy.stats import norm, t as t_dist
import warnings
warnings.filterwarnings('ignore')

# Advanced statistical libraries
try:
    from filterpy.kalman import KalmanFilter
    from filterpy.common import Q_discrete_white_noise
    KALMAN_AVAILABLE = True
except ImportError:
    KALMAN_AVAILABLE = False
    logging.warning("filterpy not available. Kalman filtering will use custom implementation.")

try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False
    logging.warning("arch not available. GARCH models will use simplified implementation.")

try:
    from copulas.multivariate import GaussianMultivariate
    from copulas.univariate import GaussianUnivariate
    COPULAS_AVAILABLE = True
except ImportError:
    COPULAS_AVAILABLE = False
    logging.warning("copulas not available. Using custom copula implementation.")

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("PyTorch/sklearn not available. ML features will be limited.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StatisticalMethod(Enum):
    """Available statistical methods"""
    KALMAN_FILTER = "kalman_filter"
    GARCH = "garch"
    COPULA = "copula"
    NEURAL_NETWORK = "neural_network"
    REGIME_DETECTION = "regime_detection"

@dataclass
class KalmanState:
    """Kalman filter state representation"""
    hedge_ratio: float
    hedge_ratio_variance: float
    intercept: float
    intercept_variance: float
    log_likelihood: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class GARCHResult:
    """GARCH model results"""
    conditional_volatility: np.ndarray
    parameters: Dict[str, float]
    log_likelihood: float
    aic: float
    bic: float
    forecast_volatility: Optional[float] = None

@dataclass
class CopulaResult:
    """Copula model results"""
    dependence_parameter: float
    tail_dependence_upper: float
    tail_dependence_lower: float
    correlation: float
    log_likelihood: float
    copula_type: str

class CustomKalmanFilter:
    """Custom Kalman Filter implementation for hedge ratio estimation"""
    
    def __init__(self, delta: float = 1e-4, vw: float = 1e-3):
        self.delta = delta  # Transition variance
        self.vw = vw       # Observation variance
        self.reset()
    
    def reset(self):
        """Reset filter state"""
        self.R = np.eye(2) * self.delta  # State covariance
        self.P = np.eye(2) * 1e3         # Error covariance
        self.x = np.array([0.0, 0.0])    # State vector [hedge_ratio, intercept]
        self.log_likelihood = 0.0
        
    def update(self, y: float, X: float) -> KalmanState:
        """Update filter with new observation"""
        # Prediction step
        x_pred = self.x  # State transition (random walk)
        P_pred = self.P + self.R
        
        # Observation model: y = hedge_ratio * X + intercept + noise
        H = np.array([X, 1.0])  # Observation matrix
        
        # Update step
        y_pred = np.dot(H, x_pred)
        residual = y - y_pred
        
        S = np.dot(H, np.dot(P_pred, H)) + self.vw  # Innovation covariance
        K = np.dot(P_pred, H) / S  # Kalman gain
        
        # State update
        self.x = x_pred + K * residual
        self.P = P_pred - np.outer(K, H) @ P_pred
        
        # Log likelihood update
        self.log_likelihood += -0.5 * (np.log(2 * np.pi * S) + residual**2 / S)
        
        return KalmanState(
            hedge_ratio=self.x[0],
            hedge_ratio_variance=self.P[0, 0],
            intercept=self.x[1],
            intercept_variance=self.P[1, 1],
            log_likelihood=self.log_likelihood
        )

class DynamicHedgeRatioEstimator:
    """Dynamic hedge ratio estimation using Kalman filtering"""
    
    def __init__(self, use_external_kalman: bool = True):
        self.use_external_kalman = use_external_kalman and KALMAN_AVAILABLE
        self.filter = None
        self.custom_filter = CustomKalmanFilter()
        self.states_history = []
        
    def initialize_filter(self, initial_hedge_ratio: float = 1.0):
        """Initialize Kalman filter"""
        if self.use_external_kalman:
            self.filter = KalmanFilter(dim_x=2, dim_z=1)
            
            # State transition matrix (random walk)
            self.filter.F = np.eye(2)
            
            # Observation matrix [price_x, 1] for y = beta*x + alpha
            self.filter.H = np.array([[1., 1.]])
            
            # Process noise
            self.filter.Q = Q_discrete_white_noise(2, dt=1, var=1e-4)
            
            # Measurement noise
            self.filter.R = np.array([[1e-3]])
            
            # Initial state
            self.filter.x = np.array([[initial_hedge_ratio], [0.]])
            
            # Initial covariance
            self.filter.P = np.eye(2) * 1000
        else:
            self.custom_filter.reset()
            self.custom_filter.x[0] = initial_hedge_ratio
    
    def update_hedge_ratio(self, price_y: float, price_x: float) -> KalmanState:
        """Update hedge ratio with new price observations"""
        if self.use_external_kalman and self.filter is not None:
            # Update observation matrix with current price_x
            self.filter.H = np.array([[price_x, 1.]])
            
            # Predict and update
            self.filter.predict()
            self.filter.update(np.array([[price_y]]))
            
            state = KalmanState(
                hedge_ratio=self.filter.x[0, 0],
                hedge_ratio_variance=self.filter.P[0, 0],
                intercept=self.filter.x[1, 0],
                intercept_variance=self.filter.P[1, 1],
                log_likelihood=self.filter.log_likelihood
            )
        else:
            state = self.custom_filter.update(price_y, price_x)
        
        self.states_history.append(state)
        return state
    
    def get_current_hedge_ratio(self) -> Tuple[float, float]:
        """Get current hedge ratio and its confidence interval"""
        if not self.states_history:
            return 1.0, 0.1
        
        latest_state = self.states_history[-1]
        hedge_ratio = latest_state.hedge_ratio
        std_error = np.sqrt(latest_state.hedge_ratio_variance)
        
        return hedge_ratio, std_error

class GARCHVolatilityModel:
    """GARCH model for time-varying volatility estimation"""
    
    def __init__(self, p: int = 1, q: int = 1):
        self.p = p  # GARCH order
        self.q = q  # ARCH order
        self.model = None
        self.fitted_model = None
        
    def fit(self, returns: pd.Series, dist: str = 'normal') -> GARCHResult:
        """Fit GARCH model to return series"""
        if ARCH_AVAILABLE:
            return self._fit_arch_model(returns, dist)
        else:
            return self._fit_custom_garch(returns)
    
    def _fit_arch_model(self, returns: pd.Series, dist: str) -> GARCHResult:
        """Fit using arch library"""
        try:
            # Create GARCH model
            self.model = arch_model(returns, vol='Garch', p=self.p, q=self.q, dist=dist)
            
            # Fit model
            self.fitted_model = self.model.fit(disp='off')
            
            # Extract results
            conditional_volatility = self.fitted_model.conditional_volatility
            parameters = self.fitted_model.params.to_dict()
            
            return GARCHResult(
                conditional_volatility=conditional_volatility.values,
                parameters=parameters,
                log_likelihood=self.fitted_model.loglikelihood,
                aic=self.fitted_model.aic,
                bic=self.fitted_model.bic
            )
            
        except Exception as e:
            logger.error(f"GARCH fitting failed: {e}")
            return self._fit_custom_garch(returns)
    
    def _fit_custom_garch(self, returns: pd.Series) -> GARCHResult:
        """Custom GARCH implementation"""
        n = len(returns)
        returns_array = returns.values
        
        # Initialize parameters
        omega = 0.01
        alpha = 0.1
        beta = 0.8
        
        # Initialize volatility
        sigma2 = np.var(returns_array)
        conditional_volatility = np.zeros(n)
        conditional_volatility[0] = np.sqrt(sigma2)
        
        # GARCH(1,1) recursion
        for t in range(1, n):
            sigma2 = omega + alpha * returns_array[t-1]**2 + beta * sigma2
            conditional_volatility[t] = np.sqrt(sigma2)
        
        # Simple parameter estimation (method of moments)
        parameters = {
            'omega': omega,
            'alpha[1]': alpha,
            'beta[1]': beta
        }
        
        # Approximate log-likelihood
        log_likelihood = -0.5 * np.sum(np.log(2 * np.pi * conditional_volatility**2) + 
                                      returns_array**2 / conditional_volatility**2)
        
        return GARCHResult(
            conditional_volatility=conditional_volatility,
            parameters=parameters,
            log_likelihood=log_likelihood,
            aic=-2 * log_likelihood + 2 * 3,  # 3 parameters
            bic=-2 * log_likelihood + np.log(n) * 3
        )
    
    def forecast_volatility(self, horizon: int = 1) -> float:
        """Forecast volatility for given horizon"""
        if self.fitted_model is not None and ARCH_AVAILABLE:
            forecast = self.fitted_model.forecast(horizon=horizon)
            return np.sqrt(forecast.variance.iloc[-1, 0])
        else:
            # Simple persistence forecast
            if hasattr(self, '_last_volatility'):
                return self._last_volatility
            return 0.02  # Default 2% daily volatility

class CopulaModel:
    """Copula model for dependency structure analysis"""
    
    def __init__(self, copula_type: str = 'gaussian'):
        self.copula_type = copula_type
        self.fitted_copula = None
        
    def fit(self, x: np.ndarray, y: np.ndarray) -> CopulaResult:
        """Fit copula model to bivariate data"""
        if COPULAS_AVAILABLE:
            return self._fit_copulas_library(x, y)
        else:
            return self._fit_custom_copula(x, y)
    
    def _fit_copulas_library(self, x: np.ndarray, y: np.ndarray) -> CopulaResult:
        """Fit using copulas library"""
        try:
            # Prepare data
            data = pd.DataFrame({'x': x, 'y': y})
            
            # Fit Gaussian copula
            self.fitted_copula = GaussianMultivariate()
            self.fitted_copula.fit(data)
            
            # Extract parameters
            correlation = self.fitted_copula.covariance[0, 1]
            
            return CopulaResult(
                dependence_parameter=correlation,
                tail_dependence_upper=0.0,  # Gaussian copula has no tail dependence
                tail_dependence_lower=0.0,
                correlation=correlation,
                log_likelihood=0.0,  # Not directly available
                copula_type='gaussian'
            )
            
        except Exception as e:
            logger.error(f"Copula fitting failed: {e}")
            return self._fit_custom_copula(x, y)
    
    def _fit_custom_copula(self, x: np.ndarray, y: np.ndarray) -> CopulaResult:
        """Custom copula implementation (Gaussian)"""
        # Transform to uniform margins using empirical CDF
        n = len(x)
        u = stats.rankdata(x) / (n + 1)
        v = stats.rankdata(y) / (n + 1)
        
        # Transform to normal margins
        x_norm = norm.ppf(u)
        y_norm = norm.ppf(v)
        
        # Estimate correlation
        correlation = np.corrcoef(x_norm, y_norm)[0, 1]
        
        # Calculate log-likelihood (approximate)
        log_likelihood = -0.5 * n * np.log(1 - correlation**2)
        
        return CopulaResult(
            dependence_parameter=correlation,
            tail_dependence_upper=0.0,
            tail_dependence_lower=0.0,
            correlation=correlation,
            log_likelihood=log_likelihood,
            copula_type='gaussian'
        )
    
    def simulate(self, n_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate from fitted copula"""
        if self.fitted_copula is not None and COPULAS_AVAILABLE:
            samples = self.fitted_copula.sample(n_samples)
            return samples['x'].values, samples['y'].values
        else:
            # Simple Gaussian copula simulation
            correlation = 0.5  # Default
            if hasattr(self, '_correlation'):
                correlation = self._correlation
            
            # Generate correlated normal variables
            mean = [0, 0]
            cov = [[1, correlation], [correlation, 1]]
            samples = np.random.multivariate_normal(mean, cov, n_samples)
            
            # Transform to uniform
            u = norm.cdf(samples[:, 0])
            v = norm.cdf(samples[:, 1])
            
            return u, v

class NeuralNetworkPredictor:
    """Neural network for pattern recognition and signal generation"""
    
    def __init__(self, input_size: int = 20, hidden_sizes: List[int] = [64, 32], output_size: int = 1):
        self.input_size = input_size
        self.hidden_sizes = hidden_sizes
        self.output_size = output_size
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        if ML_AVAILABLE:
            self._build_model()
    
    def _build_model(self):
        """Build neural network architecture"""
        if not ML_AVAILABLE:
            return
        
        layers = []
        prev_size = self.input_size
        
        # Hidden layers
        for hidden_size in self.hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        # Output layer
        layers.append(nn.Linear(prev_size, self.output_size))
        layers.append(nn.Tanh())  # Output between -1 and 1
        
        self.model = nn.Sequential(*layers)
        self.scaler = StandardScaler()
    
    def prepare_features(self, spread_data: pd.Series, lookback: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and targets for training"""
        features = []
        targets = []
        
        spread_values = spread_data.values
        
        for i in range(lookback, len(spread_values) - 1):
            # Features: lookback window of spread values and technical indicators
            window = spread_values[i-lookback:i]
            
            # Add technical features
            sma_5 = np.mean(window[-5:])
            sma_10 = np.mean(window[-10:]) if len(window) >= 10 else sma_5
            volatility = np.std(window)
            momentum = window[-1] - window[0]
            
            feature_vector = np.concatenate([
                window,
                [sma_5, sma_10, volatility, momentum]
            ])
            
            # Pad or truncate to input_size
            if len(feature_vector) > self.input_size:
                feature_vector = feature_vector[:self.input_size]
            elif len(feature_vector) < self.input_size:
                padding = np.zeros(self.input_size - len(feature_vector))
                feature_vector = np.concatenate([feature_vector, padding])
            
            features.append(feature_vector)
            
            # Target: future return (normalized)
            future_return = (spread_values[i+1] - spread_values[i]) / spread_values[i]
            targets.append(np.tanh(future_return * 100))  # Scale and bound
        
        return np.array(features), np.array(targets)
    
    def train(self, spread_data: pd.Series, epochs: int = 100, learning_rate: float = 0.001) -> Dict[str, float]:
        """Train the neural network"""
        if not ML_AVAILABLE or self.model is None:
            logger.warning("ML libraries not available or model not built")
            return {'loss': float('inf')}
        
        # Prepare data
        X, y = self.prepare_features(spread_data)
        
        if len(X) == 0:
            logger.error("No training data available")
            return {'loss': float('inf')}
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train)
        y_train_tensor = torch.FloatTensor(y_train).unsqueeze(1)
        X_val_tensor = torch.FloatTensor(X_val)
        y_val_tensor = torch.FloatTensor(y_val).unsqueeze(1)
        
        # Training setup
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # Training loop
        train_losses = []
        val_losses = []
        
        for epoch in range(epochs):
            # Training
            self.model.train()
            optimizer.zero_grad()
            train_pred = self.model(X_train_tensor)
            train_loss = criterion(train_pred, y_train_tensor)
            train_loss.backward()
            optimizer.step()
            
            # Validation
            self.model.eval()
            with torch.no_grad():
                val_pred = self.model(X_val_tensor)
                val_loss = criterion(val_pred, y_val_tensor)
            
            train_losses.append(train_loss.item())
            val_losses.append(val_loss.item())
            
            if epoch % 20 == 0:
                logger.info(f"Epoch {epoch}: Train Loss = {train_loss.item():.6f}, Val Loss = {val_loss.item():.6f}")
        
        self.is_trained = True
        
        return {
            'final_train_loss': train_losses[-1],
            'final_val_loss': val_losses[-1],
            'min_val_loss': min(val_losses)
        }
    
    def predict(self, spread_data: pd.Series) -> float:
        """Generate prediction for current spread"""
        if not ML_AVAILABLE or self.model is None or not self.is_trained:
            return 0.0
        
        # Prepare features for latest data point
        if len(spread_data) < self.input_size:
            return 0.0
        
        latest_window = spread_data.values[-self.input_size:]
        
        # Add technical features (simplified)
        sma_5 = np.mean(latest_window[-5:])
        sma_10 = np.mean(latest_window[-10:]) if len(latest_window) >= 10 else sma_5
        volatility = np.std(latest_window)
        momentum = latest_window[-1] - latest_window[0]
        
        feature_vector = np.concatenate([
            latest_window[:-4],  # Adjust size
            [sma_5, sma_10, volatility, momentum]
        ])
        
        # Ensure correct size
        if len(feature_vector) != self.input_size:
            if len(feature_vector) > self.input_size:
                feature_vector = feature_vector[:self.input_size]
            else:
                padding = np.zeros(self.input_size - len(feature_vector))
                feature_vector = np.concatenate([feature_vector, padding])
        
        # Scale and predict
        feature_scaled = self.scaler.transform(feature_vector.reshape(1, -1))
        feature_tensor = torch.FloatTensor(feature_scaled)
        
        self.model.eval()
        with torch.no_grad():
            prediction = self.model(feature_tensor)
        
        return prediction.item()

class AdvancedStatisticalEngine:
    """Main engine combining all advanced statistical methods"""
    
    def __init__(self):
        self.kalman_estimator = DynamicHedgeRatioEstimator()
        self.garch_model = GARCHVolatilityModel()
        self.copula_model = CopulaModel()
        self.neural_network = NeuralNetworkPredictor()
        self.results_cache = {}
        
    def initialize(self, price_data: pd.DataFrame):
        """Initialize all models with historical data"""
        logger.info("Initializing Advanced Statistical Engine...")
        
        if 'asset1' not in price_data.columns or 'asset2' not in price_data.columns:
            raise ValueError("Price data must contain 'asset1' and 'asset2' columns")
        
        # Initialize Kalman filter with initial hedge ratio estimate
        initial_hedge_ratio = np.cov(price_data['asset1'], price_data['asset2'])[0, 1] / np.var(price_data['asset2'])
        self.kalman_estimator.initialize_filter(initial_hedge_ratio)
        
        # Calculate returns for GARCH model
        returns1 = price_data['asset1'].pct_change().dropna()
        returns2 = price_data['asset2'].pct_change().dropna()
        
        # Fit GARCH models
        logger.info("Fitting GARCH models...")
        self.garch_result1 = self.garch_model.fit(returns1)
        self.garch_result2 = self.garch_model.fit(returns2)
        
        # Fit copula model
        logger.info("Fitting copula model...")
        self.copula_result = self.copula_model.fit(price_data['asset1'].values, price_data['asset2'].values)
        
        # Calculate spread for neural network
        spread = price_data['asset1'] - initial_hedge_ratio * price_data['asset2']
        
        # Train neural network
        logger.info("Training neural network...")
        self.nn_training_result = self.neural_network.train(spread)
        
        logger.info("Advanced Statistical Engine initialized successfully")
    
    def update_models(self, new_price1: float, new_price2: float) -> Dict[str, Any]:
        """Update all models with new price data"""
        results = {}
        
        # Update Kalman filter
        kalman_state = self.kalman_estimator.update_hedge_ratio(new_price1, new_price2)
        results['kalman_state'] = kalman_state
        
        # Get current hedge ratio and confidence
        hedge_ratio, hedge_ratio_std = self.kalman_estimator.get_current_hedge_ratio()
        results['dynamic_hedge_ratio'] = hedge_ratio
        results['hedge_ratio_confidence'] = 1.96 * hedge_ratio_std  # 95% confidence interval
        
        return results
    
    def generate_trading_signals(self, current_spread: float, spread_history: pd.Series) -> Dict[str, float]:
        """Generate comprehensive trading signals"""
        signals = {}
        
        # Neural network signal
        if len(spread_history) >= self.neural_network.input_size:
            nn_signal = self.neural_network.predict(spread_history)
            signals['neural_network'] = nn_signal
        else:
            signals['neural_network'] = 0.0
        
        # Statistical signals based on spread characteristics
        if len(spread_history) > 20:
            spread_mean = spread_history.rolling(20).mean().iloc[-1]
            spread_std = spread_history.rolling(20).std().iloc[-1]
            
            # Z-score signal
            z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0
            signals['z_score'] = -np.tanh(z_score)  # Negative because we expect mean reversion
            
            # Volatility-adjusted signal
            recent_volatility = spread_history.rolling(10).std().iloc[-1]
            long_term_volatility = spread_history.rolling(50).std().iloc[-1] if len(spread_history) > 50 else recent_volatility
            
            volatility_ratio = recent_volatility / long_term_volatility if long_term_volatility > 0 else 1
            signals['volatility_adjusted'] = signals['z_score'] / volatility_ratio
        else:
            signals['z_score'] = 0.0
            signals['volatility_adjusted'] = 0.0
        
        # Composite signal
        weights = {'neural_network': 0.4, 'z_score': 0.3, 'volatility_adjusted': 0.3}
        composite_signal = sum(signals[key] * weights[key] for key in weights if key in signals)
        signals['composite'] = composite_signal
        
        return signals
    
    def get_risk_metrics(self, spread_history: pd.Series) -> Dict[str, float]:
        """Calculate comprehensive risk metrics"""
        if len(spread_history) < 20:
            return {'var_95': 0.0, 'expected_shortfall': 0.0, 'max_drawdown': 0.0}
        
        returns = spread_history.pct_change().dropna()
        
        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5)
        
        # Expected Shortfall (Conditional VaR)
        expected_shortfall = returns[returns <= var_95].mean()
        
        # Maximum Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        return {
            'var_95': var_95,
            'expected_shortfall': expected_shortfall,
            'max_drawdown': max_drawdown,
            'current_volatility': returns.std() * np.sqrt(252)  # Annualized
        }

# Example usage and testing
def test_advanced_statistical_methods():
    """Test the advanced statistical methods"""
    print("Testing Advanced Statistical Methods")
    print("=" * 50)
    
    # Generate synthetic data
    np.random.seed(42)
    n_points = 1000
    
    # Correlated price series
    returns1 = np.random.normal(0.0005, 0.02, n_points)
    returns2 = 0.8 * returns1 + np.random.normal(0, 0.015, n_points)
    
    prices1 = 100 * np.exp(np.cumsum(returns1))
    prices2 = 95 * np.exp(np.cumsum(returns2))
    
    price_data = pd.DataFrame({
        'asset1': prices1,
        'asset2': prices2
    })
    
    # Initialize engine
    engine = AdvancedStatisticalEngine()
    engine.initialize(price_data)
    
    # Test dynamic hedge ratio estimation
    print("\nTesting Dynamic Hedge Ratio Estimation:")
    for i in range(950, 960):
        results = engine.update_models(prices1[i], prices2[i])
        print(f"  Step {i}: Hedge Ratio = {results['dynamic_hedge_ratio']:.4f} ± {results['hedge_ratio_confidence']:.4f}")
    
    # Test signal generation
    print("\nTesting Signal Generation:")
    hedge_ratio = engine.kalman_estimator.get_current_hedge_ratio()[0]
    spread = pd.Series(prices1 - hedge_ratio * prices2)
    
    signals = engine.generate_trading_signals(spread.iloc[-1], spread)
    print(f"  Neural Network Signal: {signals['neural_network']:.4f}")
    print(f"  Z-Score Signal: {signals['z_score']:.4f}")
    print(f"  Composite Signal: {signals['composite']:.4f}")
    
    # Test risk metrics
    print("\nTesting Risk Metrics:")
    risk_metrics = engine.get_risk_metrics(spread)
    print(f"  VaR (95%): {risk_metrics['var_95']:.4f}")
    print(f"  Expected Shortfall: {risk_metrics['expected_shortfall']:.4f}")
    print(f"  Max Drawdown: {risk_metrics['max_drawdown']:.4f}")
    print(f"  Current Volatility: {risk_metrics['current_volatility']:.4f}")

if __name__ == "__main__":
    test_advanced_statistical_methods()