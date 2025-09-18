"""Adaptive Learning System with Performance Feedback Loops

Institutional-grade adaptive learning system that:
- Continuously learns from strategy performance
- Adapts parameters based on market conditions
- Implements reinforcement learning for strategy optimization
- Provides performance feedback loops
- Maintains model versioning and rollback capabilities
- Integrates with regime detection for context-aware learning

Author: Vincent S. Pereira
Version: 2.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import deque, defaultdict
import json
import pickle
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import math
from scipy import optimize, stats
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("PyTorch not available. Neural network features disabled.")

logger = logging.getLogger(__name__)


class LearningMode(Enum):
    """Learning modes for the adaptive system"""
    SUPERVISED = "supervised"
    REINFORCEMENT = "reinforcement"
    UNSUPERVISED = "unsupervised"
    ENSEMBLE = "ensemble"


class OptimizationMethod(Enum):
    """Optimization methods for parameter tuning"""
    GRID_SEARCH = "grid_search"
    RANDOM_SEARCH = "random_search"
    BAYESIAN = "bayesian"
    GENETIC_ALGORITHM = "genetic_algorithm"
    GRADIENT_DESCENT = "gradient_descent"


class PerformanceMetric(Enum):
    """Performance metrics for evaluation"""
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    TOTAL_RETURN = "total_return"
    VOLATILITY = "volatility"
    ALPHA = "alpha"
    BETA = "beta"
    INFORMATION_RATIO = "information_ratio"


@dataclass
class PerformanceRecord:
    """Individual performance record"""
    timestamp: datetime
    strategy_id: str
    parameters: Dict[str, Any]
    returns: List[float]
    metrics: Dict[PerformanceMetric, float]
    market_regime: str
    confidence_score: float
    execution_time: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'strategy_id': self.strategy_id,
            'parameters': self.parameters,
            'returns': self.returns,
            'metrics': {k.value: v for k, v in self.metrics.items()},
            'market_regime': self.market_regime,
            'confidence_score': self.confidence_score,
            'execution_time': self.execution_time
        }


@dataclass
class LearningConfig:
    """Configuration for adaptive learning"""
    learning_mode: LearningMode = LearningMode.ENSEMBLE
    optimization_method: OptimizationMethod = OptimizationMethod.BAYESIAN
    primary_metric: PerformanceMetric = PerformanceMetric.SHARPE_RATIO
    
    # Learning parameters
    learning_rate: float = 0.01
    batch_size: int = 32
    lookback_periods: int = 252  # 1 year of daily data
    min_samples: int = 50
    
    # Adaptation parameters
    adaptation_frequency: int = 10  # Adapt every N periods
    parameter_bounds: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    # Performance thresholds
    min_performance_threshold: float = 0.0
    rollback_threshold: float = -0.1  # Rollback if performance drops by 10%
    
    # Model management
    max_models: int = 10
    model_validation_split: float = 0.2
    cross_validation_folds: int = 5
    
    # Risk management
    max_parameter_change: float = 0.2  # Max 20% parameter change per adaptation
    confidence_threshold: float = 0.7
    


class NeuralNetworkOptimizer:
    """Neural network for parameter optimization"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int] = None):
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch required for neural network optimizer")
        
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims or [64, 32, 16]
        self.model = self._build_model()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        self.scaler = StandardScaler()
        
    def _build_model(self) -> nn.Module:
        """Build neural network model"""
        layers = []
        prev_dim = self.input_dim
        
        for hidden_dim in self.hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, 1))  # Output layer
        
        return nn.Sequential(*layers)
    
    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 100) -> Dict[str, float]:
        """Train the neural network"""
        X_scaled = self.scaler.fit_transform(X)
        X_tensor = torch.FloatTensor(X_scaled)
        y_tensor = torch.FloatTensor(y.reshape(-1, 1))
        
        self.model.train()
        losses = []
        
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            outputs = self.model(X_tensor)
            loss = self.criterion(outputs, y_tensor)
            loss.backward()
            self.optimizer.step()
            losses.append(loss.item())
        
        return {'final_loss': losses[-1], 'avg_loss': np.mean(losses)}
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions"""
        X_scaled = self.scaler.transform(X)
        X_tensor = torch.FloatTensor(X_scaled)
        
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(X_tensor)
        
        return predictions.numpy().flatten()


class AdaptiveLearningSystem:
    """Institutional-Grade Adaptive Learning System
    
    Features:
    - Multi-modal learning (supervised, reinforcement, unsupervised)
    - Dynamic parameter optimization
    - Performance feedback loops
    - Model versioning and rollback
    - Regime-aware adaptation
    - Risk-adjusted learning
    """
    
    def __init__(
        self,
        config: LearningConfig = None,
        model_save_path: str = "./models/adaptive_learning"
    ):
        self.config = config or LearningConfig()
        self.model_save_path = Path(model_save_path)
        self.model_save_path.mkdir(parents=True, exist_ok=True)
        
        # Performance tracking
        self.performance_history: deque = deque(maxlen=self.config.lookback_periods)
        self.parameter_history: deque = deque(maxlen=self.config.lookback_periods)
        self.regime_performance: Dict[str, List[PerformanceRecord]] = defaultdict(list)
        
        # Model management
        self.models: Dict[str, Any] = {}
        self.model_performance: Dict[str, float] = {}
        self.current_model_id: Optional[str] = None
        self.model_versions: Dict[str, int] = {}
        
        # Learning components
        self.rf_regressor = RandomForestRegressor(n_estimators=100, random_state=42)
        self.gb_regressor = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.neural_optimizer: Optional[NeuralNetworkOptimizer] = None
        
        # Optimization state
        self.current_parameters: Dict[str, Any] = {}
        self.best_parameters: Dict[str, Any] = {}
        self.best_performance: float = float('-inf')
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.lock = threading.Lock()
        
        # Adaptation tracking
        self.adaptation_count = 0
        self.last_adaptation: Optional[datetime] = None
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize neural network if available
        if TORCH_AVAILABLE:
            try:
                self.neural_optimizer = NeuralNetworkOptimizer(input_dim=10)  # Will be adjusted based on features
            except Exception as e:
                self.logger.warning(f"Failed to initialize neural network: {e}")
    
    def add_performance_record(
        self,
        strategy_id: str,
        parameters: Dict[str, Any],
        returns: List[float],
        market_regime: str = "unknown",
        execution_time: float = 0.0
    ) -> None:
        """Add performance record for learning"""
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(returns)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(returns, metrics)
        
        # Create performance record
        record = PerformanceRecord(
            timestamp=datetime.now(timezone.utc),
            strategy_id=strategy_id,
            parameters=parameters.copy(),
            returns=returns.copy(),
            metrics=metrics,
            market_regime=market_regime,
            confidence_score=confidence_score,
            execution_time=execution_time
        )
        
        with self.lock:
            self.performance_history.append(record)
            self.parameter_history.append(parameters.copy())
            self.regime_performance[market_regime].append(record)
        
        # Check if adaptation is needed
        if self._should_adapt():
            self.executor.submit(self._adapt_parameters)
    
    def _calculate_performance_metrics(self, returns: List[float]) -> Dict[PerformanceMetric, float]:
        """Calculate comprehensive performance metrics"""
        if not returns:
            return {}
        
        returns_array = np.array(returns)
        metrics = {}
        
        try:
            # Basic metrics
            total_return = np.prod(1 + returns_array) - 1
            volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
            
            metrics[PerformanceMetric.TOTAL_RETURN] = total_return
            metrics[PerformanceMetric.VOLATILITY] = volatility
            
            # Risk-adjusted metrics
            if volatility > 0:
                sharpe_ratio = (np.mean(returns_array) * 252) / volatility
                metrics[PerformanceMetric.SHARPE_RATIO] = sharpe_ratio
            
            # Downside metrics
            negative_returns = returns_array[returns_array < 0]
            if len(negative_returns) > 0:
                downside_deviation = np.std(negative_returns) * np.sqrt(252)
                if downside_deviation > 0:
                    sortino_ratio = (np.mean(returns_array) * 252) / downside_deviation
                    metrics[PerformanceMetric.SORTINO_RATIO] = sortino_ratio
            
            # Drawdown metrics
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdowns)
            metrics[PerformanceMetric.MAX_DRAWDOWN] = max_drawdown
            
            # Calmar ratio
            if max_drawdown < 0:
                calmar_ratio = (np.mean(returns_array) * 252) / abs(max_drawdown)
                metrics[PerformanceMetric.CALMAR_RATIO] = calmar_ratio
            
            # Win rate
            win_rate = len(returns_array[returns_array > 0]) / len(returns_array)
            metrics[PerformanceMetric.WIN_RATE] = win_rate
            
            # Profit factor
            positive_returns = returns_array[returns_array > 0]
            negative_returns = returns_array[returns_array < 0]
            
            if len(positive_returns) > 0 and len(negative_returns) > 0:
                profit_factor = np.sum(positive_returns) / abs(np.sum(negative_returns))
                metrics[PerformanceMetric.PROFIT_FACTOR] = profit_factor
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
        
        return metrics
    
    def _calculate_confidence_score(self, returns: List[float], metrics: Dict[PerformanceMetric, float]) -> float:
        """Calculate confidence score for the performance"""
        if not returns or not metrics:
            return 0.0
        
        confidence = 0.5  # Base confidence
        
        # Adjust based on sample size
        sample_size_factor = min(len(returns) / 100, 1.0)
        confidence += sample_size_factor * 0.2
        
        # Adjust based on Sharpe ratio
        sharpe = metrics.get(PerformanceMetric.SHARPE_RATIO, 0)
        if sharpe > 1.0:
            confidence += 0.2
        elif sharpe > 0.5:
            confidence += 0.1
        
        # Adjust based on consistency (low volatility)
        volatility = metrics.get(PerformanceMetric.VOLATILITY, 1.0)
        if volatility < 0.15:  # Low volatility
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _should_adapt(self) -> bool:
        """Determine if parameters should be adapted"""
        if len(self.performance_history) < self.config.min_samples:
            return False
        
        # Check adaptation frequency
        if self.last_adaptation:
            time_since_adaptation = datetime.now(timezone.utc) - self.last_adaptation
            if time_since_adaptation.days < self.config.adaptation_frequency:
                return False
        
        # Check if performance is declining
        recent_performance = self._get_recent_performance()
        if recent_performance < self.config.rollback_threshold:
            return True
        
        # Regular adaptation schedule
        return len(self.performance_history) % self.config.adaptation_frequency == 0
    
    def _get_recent_performance(self, periods: int = 10) -> float:
        """Get recent performance score"""
        if len(self.performance_history) < periods:
            return 0.0
        
        recent_records = list(self.performance_history)[-periods:]
        primary_metric = self.config.primary_metric
        
        scores = []
        for record in recent_records:
            if primary_metric in record.metrics:
                scores.append(record.metrics[primary_metric])
        
        return np.mean(scores) if scores else 0.0
    
    def _adapt_parameters(self) -> None:
        """Adapt parameters based on performance feedback"""
        try:
            self.logger.info("Starting parameter adaptation...")
            
            # Prepare training data
            X, y = self._prepare_training_data()
            
            if len(X) < self.config.min_samples:
                self.logger.warning(f"Insufficient data for adaptation: {len(X)} samples")
                return
            
            # Train models based on learning mode
            if self.config.learning_mode == LearningMode.SUPERVISED:
                new_parameters = self._supervised_learning(X, y)
            elif self.config.learning_mode == LearningMode.REINFORCEMENT:
                new_parameters = self._reinforcement_learning(X, y)
            elif self.config.learning_mode == LearningMode.ENSEMBLE:
                new_parameters = self._ensemble_learning(X, y)
            else:
                new_parameters = self._random_search_optimization()
            
            # Validate new parameters
            if self._validate_parameters(new_parameters):
                self._update_parameters(new_parameters)
                self.adaptation_count += 1
                self.last_adaptation = datetime.now(timezone.utc)
                
                self.logger.info(f"Parameters adapted successfully. Adaptation count: {self.adaptation_count}")
            else:
                self.logger.warning("Parameter validation failed. Keeping current parameters.")
        
        except Exception as e:
            self.logger.error(f"Error during parameter adaptation: {e}")
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for machine learning"""
        records = list(self.performance_history)
        
        X = []
        y = []
        
        for record in records:
            # Feature engineering
            features = self._extract_features(record)
            target = record.metrics.get(self.config.primary_metric, 0.0)
            
            X.append(features)
            y.append(target)
        
        return np.array(X), np.array(y)
    
    def _extract_features(self, record: PerformanceRecord) -> List[float]:
        """Extract features from performance record"""
        features = []
        
        # Parameter features
        for param_name, param_value in record.parameters.items():
            if isinstance(param_value, (int, float)):
                features.append(float(param_value))
        
        # Performance features
        features.extend([
            record.confidence_score,
            record.execution_time,
            len(record.returns),
            np.mean(record.returns) if record.returns else 0.0,
            np.std(record.returns) if record.returns else 0.0
        ])
        
        # Market regime encoding (simple)
        regime_encoding = {
            'bullish': 1.0,
            'bearish': -1.0,
            'sideways': 0.0,
            'unknown': 0.5
        }
        features.append(regime_encoding.get(record.market_regime, 0.5))
        
        return features
    
    def _supervised_learning(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Supervised learning approach"""
        # Train random forest
        self.rf_regressor.fit(X, y)
        
        # Train gradient boosting
        self.gb_regressor.fit(X, y)
        
        # Ensemble prediction
        rf_pred = self.rf_regressor.predict(X[-1:])  # Latest features
        gb_pred = self.gb_regressor.predict(X[-1:])
        
        # Average predictions
        ensemble_pred = (rf_pred[0] + gb_pred[0]) / 2
        
        # Generate new parameters based on prediction
        return self._generate_parameters_from_prediction(ensemble_pred)
    
    def _reinforcement_learning(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Reinforcement learning approach"""
        # Simple Q-learning inspired approach
        # Use recent performance as reward signal
        
        recent_performance = self._get_recent_performance()
        
        if recent_performance > 0:
            # Positive reward: slightly adjust in same direction
            return self._adjust_parameters(factor=1.1)
        else:
            # Negative reward: try different direction
            return self._adjust_parameters(factor=0.9)
    
    def _ensemble_learning(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Ensemble learning approach"""
        predictions = []
        
        # Random Forest
        self.rf_regressor.fit(X, y)
        rf_pred = self.rf_regressor.predict(X[-1:])[0]
        predictions.append(rf_pred)
        
        # Gradient Boosting
        self.gb_regressor.fit(X, y)
        gb_pred = self.gb_regressor.predict(X[-1:])[0]
        predictions.append(gb_pred)
        
        # Neural Network (if available)
        if self.neural_optimizer and TORCH_AVAILABLE:
            try:
                # Adjust input dimension if needed
                if X.shape[1] != self.neural_optimizer.input_dim:
                    self.neural_optimizer = NeuralNetworkOptimizer(input_dim=X.shape[1])
                
                self.neural_optimizer.train(X, y)
                nn_pred = self.neural_optimizer.predict(X[-1:])[0]
                predictions.append(nn_pred)
            except Exception as e:
                self.logger.warning(f"Neural network prediction failed: {e}")
        
        # Weighted ensemble
        weights = [0.4, 0.4, 0.2] if len(predictions) == 3 else [0.5, 0.5]
        ensemble_pred = np.average(predictions, weights=weights[:len(predictions)])
        
        return self._generate_parameters_from_prediction(ensemble_pred)
    
    def _generate_parameters_from_prediction(self, prediction: float) -> Dict[str, Any]:
        """Generate new parameters based on model prediction"""
        if not self.current_parameters:
            return self._get_default_parameters()
        
        new_parameters = self.current_parameters.copy()
        
        # Adjust parameters based on prediction
        adjustment_factor = 1.0 + (prediction * 0.1)  # Max 10% adjustment
        
        for param_name, param_value in new_parameters.items():
            if isinstance(param_value, (int, float)):
                # Apply bounds if available
                if param_name in self.config.parameter_bounds:
                    min_val, max_val = self.config.parameter_bounds[param_name]
                    new_value = param_value * adjustment_factor
                    new_parameters[param_name] = np.clip(new_value, min_val, max_val)
                else:
                    new_parameters[param_name] = param_value * adjustment_factor
        
        return new_parameters
    
    def _adjust_parameters(self, factor: float) -> Dict[str, Any]:
        """Adjust current parameters by a factor"""
        if not self.current_parameters:
            return self._get_default_parameters()
        
        new_parameters = {}
        
        for param_name, param_value in self.current_parameters.items():
            if isinstance(param_value, (int, float)):
                # Limit adjustment to max_parameter_change
                max_change = self.config.max_parameter_change
                actual_factor = np.clip(factor, 1 - max_change, 1 + max_change)
                
                new_value = param_value * actual_factor
                
                # Apply bounds if available
                if param_name in self.config.parameter_bounds:
                    min_val, max_val = self.config.parameter_bounds[param_name]
                    new_value = np.clip(new_value, min_val, max_val)
                
                new_parameters[param_name] = new_value
            else:
                new_parameters[param_name] = param_value
        
        return new_parameters
    
    def _random_search_optimization(self) -> Dict[str, Any]:
        """Random search optimization"""
        if not self.config.parameter_bounds:
            return self._get_default_parameters()
        
        new_parameters = {}
        
        for param_name, (min_val, max_val) in self.config.parameter_bounds.items():
            new_parameters[param_name] = np.random.uniform(min_val, max_val)
        
        return new_parameters
    
    def _validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate new parameters"""
        if not parameters:
            return False
        
        # Check bounds
        for param_name, param_value in parameters.items():
            if param_name in self.config.parameter_bounds:
                min_val, max_val = self.config.parameter_bounds[param_name]
                if not (min_val <= param_value <= max_val):
                    return False
        
        # Check maximum change constraint
        if self.current_parameters:
            for param_name, new_value in parameters.items():
                if param_name in self.current_parameters:
                    old_value = self.current_parameters[param_name]
                    if isinstance(old_value, (int, float)) and old_value != 0:
                        change_ratio = abs(new_value - old_value) / abs(old_value)
                        if change_ratio > self.config.max_parameter_change:
                            return False
        
        return True
    
    def _update_parameters(self, new_parameters: Dict[str, Any]) -> None:
        """Update current parameters"""
        with self.lock:
            self.current_parameters = new_parameters.copy()
        
        # Save model state
        self._save_model_state()
    
    def _get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters"""
        defaults = {}
        
        for param_name, (min_val, max_val) in self.config.parameter_bounds.items():
            defaults[param_name] = (min_val + max_val) / 2  # Midpoint
        
        return defaults
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current optimized parameters"""
        with self.lock:
            return self.current_parameters.copy()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        if not self.performance_history:
            return {}
        
        records = list(self.performance_history)
        
        # Overall statistics
        total_records = len(records)
        avg_confidence = np.mean([r.confidence_score for r in records])
        
        # Performance by regime
        regime_stats = {}
        for regime, regime_records in self.regime_performance.items():
            if regime_records:
                regime_performance = [r.metrics.get(self.config.primary_metric, 0) for r in regime_records]
                regime_stats[regime] = {
                    'count': len(regime_records),
                    'avg_performance': np.mean(regime_performance),
                    'std_performance': np.std(regime_performance)
                }
        
        # Recent performance trend
        recent_performance = self._get_recent_performance()
        
        return {
            'total_records': total_records,
            'avg_confidence': avg_confidence,
            'adaptation_count': self.adaptation_count,
            'last_adaptation': self.last_adaptation.isoformat() if self.last_adaptation else None,
            'recent_performance': recent_performance,
            'best_performance': self.best_performance,
            'regime_statistics': regime_stats,
            'current_parameters': self.current_parameters
        }
    
    def _save_model_state(self) -> None:
        """Save current model state"""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            model_id = f"adaptive_model_{timestamp}"
            
            state = {
                'model_id': model_id,
                'timestamp': timestamp,
                'parameters': self.current_parameters,
                'performance_history': [r.to_dict() for r in list(self.performance_history)],
                'config': {
                    'learning_mode': self.config.learning_mode.value,
                    'optimization_method': self.config.optimization_method.value,
                    'primary_metric': self.config.primary_metric.value
                }
            }
            
            # Save to file
            save_path = self.model_save_path / f"{model_id}.json"
            with open(save_path, 'w') as f:
                json.dump(state, f, indent=2)
            
            # Update model tracking
            self.models[model_id] = state
            self.current_model_id = model_id
            
            # Cleanup old models
            self._cleanup_old_models()
            
        except Exception as e:
            self.logger.error(f"Error saving model state: {e}")
    
    def _cleanup_old_models(self) -> None:
        """Remove old model files to save space"""
        if len(self.models) <= self.config.max_models:
            return
        
        # Sort by timestamp and remove oldest
        sorted_models = sorted(self.models.items(), key=lambda x: x[1]['timestamp'])
        models_to_remove = sorted_models[:-self.config.max_models]
        
        for model_id, _ in models_to_remove:
            try:
                # Remove file
                model_file = self.model_save_path / f"{model_id}.json"
                if model_file.exists():
                    model_file.unlink()
                
                # Remove from memory
                del self.models[model_id]
                
            except Exception as e:
                self.logger.error(f"Error removing old model {model_id}: {e}")
    
    def load_model_state(self, model_id: str) -> bool:
        """Load a specific model state"""
        try:
            model_file = self.model_save_path / f"{model_id}.json"
            
            if not model_file.exists():
                self.logger.error(f"Model file not found: {model_file}")
                return False
            
            with open(model_file, 'r') as f:
                state = json.load(f)
            
            # Restore parameters
            self.current_parameters = state['parameters']
            self.current_model_id = model_id
            
            self.logger.info(f"Model state loaded successfully: {model_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading model state: {e}")
            return False
    
    def rollback_to_best_model(self) -> bool:
        """Rollback to the best performing model"""
        if not self.models:
            return False
        
        # Find best model based on performance
        best_model_id = None
        best_score = float('-inf')
        
        for model_id, model_data in self.models.items():
            # Calculate average performance for this model
            # This is a simplified approach - in practice, you'd want more sophisticated evaluation
            if 'performance_history' in model_data:
                performances = []
                for record_dict in model_data['performance_history']:
                    if 'metrics' in record_dict:
                        metric_key = self.config.primary_metric.value
                        if metric_key in record_dict['metrics']:
                            performances.append(record_dict['metrics'][metric_key])
                
                if performances:
                    avg_performance = np.mean(performances)
                    if avg_performance > best_score:
                        best_score = avg_performance
                        best_model_id = model_id
        
        if best_model_id:
            return self.load_model_state(best_model_id)
        
        return False
    
    def set_parameter_bounds(self, parameter_bounds: Dict[str, Tuple[float, float]]) -> None:
        """Set parameter bounds for optimization"""
        self.config.parameter_bounds = parameter_bounds.copy()
    
    def shutdown(self) -> None:
        """Shutdown the adaptive learning system"""
        self.executor.shutdown(wait=True)
        self.logger.info("Adaptive learning system shutdown complete")


# Factory function
def create_adaptive_learning_system(
    learning_mode: LearningMode = LearningMode.ENSEMBLE,
    optimization_method: OptimizationMethod = OptimizationMethod.BAYESIAN,
    primary_metric: PerformanceMetric = PerformanceMetric.SHARPE_RATIO,
    model_save_path: str = "./models/adaptive_learning"
) -> AdaptiveLearningSystem:
    """Create adaptive learning system with specified configuration"""
    
    config = LearningConfig(
        learning_mode=learning_mode,
        optimization_method=optimization_method,
        primary_metric=primary_metric
    )
    
    return AdaptiveLearningSystem(config=config, model_save_path=model_save_path)


# Example usage
if __name__ == "__main__":
    # Create adaptive learning system
    learning_system = create_adaptive_learning_system()
    
    # Set parameter bounds
    learning_system.set_parameter_bounds({
        'lookback_period': (10, 100),
        'threshold': (0.01, 0.1),
        'risk_factor': (0.1, 0.5)
    })
    
    # Simulate adding performance records
    for i in range(100):
        returns = np.random.normal(0.001, 0.02, 20)  # Simulate 20 days of returns
        parameters = {
            'lookback_period': 20 + i % 10,
            'threshold': 0.05 + (i % 5) * 0.01,
            'risk_factor': 0.2 + (i % 3) * 0.1
        }
        
        learning_system.add_performance_record(
            strategy_id=f"strategy_{i % 3}",
            parameters=parameters,
            returns=returns.tolist(),
            market_regime="bullish" if i % 3 == 0 else "bearish" if i % 3 == 1 else "sideways"
        )
    
    # Get performance summary
    summary = learning_system.get_performance_summary()
    print("Performance Summary:")
    print(json.dumps(summary, indent=2, default=str))
    
    # Get current optimized parameters
    current_params = learning_system.get_current_parameters()
    print("\nCurrent Optimized Parameters:")
    print(json.dumps(current_params, indent=2))
    
    # Shutdown
    learning_system.shutdown()