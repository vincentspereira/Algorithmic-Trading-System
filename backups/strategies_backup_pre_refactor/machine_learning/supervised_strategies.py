#!/usr/bin/env python3
"""
Supervised Machine Learning Trading Strategies

Implements supervised learning strategies using Random Forest, XGBoost, and other
classifiers for trading signal generation. Includes comprehensive model management,
feature engineering integration, and performance monitoring.

Key Features:
- Random Forest Strategy (classification and regression)
- XGBoost Strategy (gradient boosting)
- Support Vector Machine Strategy
- Neural Network Strategy (MLP)
- Ensemble Strategy (combining multiple models)
- Model Management (training, validation, deployment)
- Feature Engineering Integration
- Real-time Prediction Pipeline
- Model Performance Monitoring
- Hyperparameter Optimization
- Cross-validation and Walk-forward Analysis
- Model Interpretability (SHAP values)
- Risk-adjusted Position Sizing
- Dynamic Model Selection
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
import joblib
import json
from pathlib import Path

# Machine Learning imports
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.svm import SVC, SVR
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.model_selection import (
    TimeSeriesSplit, GridSearchCV, RandomizedSearchCV,
    cross_val_score, validation_curve
)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score,
    classification_report, confusion_matrix
)
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight

# XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logging.warning("XGBoost not available. Install with: pip install xgboost")

# SHAP for model interpretability
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available. Install with: pip install shap")

# Feature engineering
from .feature_engineering import FeatureEngineer, FeatureConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')


class ModelType(Enum):
    """Types of ML models."""
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    SVM = "svm"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"


class PredictionType(Enum):
    """Types of predictions."""
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class SignalType(Enum):
    """Trading signal types."""
    BUY = 1
    SELL = -1
    HOLD = 0


class ModelStatus(Enum):
    """Model status."""
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    RETRAINING = "retraining"
    FAILED = "failed"


@dataclass
class ModelConfig:
    """Model configuration."""
    model_type: ModelType
    prediction_type: PredictionType
    target_column: str = "target"
    lookback_periods: List[int] = field(default_factory=lambda: [5, 10, 20])
    prediction_horizon: int = 1
    min_training_samples: int = 1000
    retrain_frequency: int = 100  # Retrain every N samples
    validation_split: float = 0.2
    hyperparameter_tuning: bool = True
    cross_validation_folds: int = 5
    feature_importance_threshold: float = 0.01
    class_weight: str = "balanced"
    random_state: int = 42


@dataclass
class PredictionResult:
    """Model prediction result."""
    timestamp: datetime
    prediction: Union[int, float]
    probability: Optional[Dict[str, float]] = None
    confidence: float = 0.0
    feature_importance: Optional[Dict[str, float]] = None
    model_version: str = "1.0"
    signal_strength: float = 0.0


@dataclass
class ModelPerformance:
    """Model performance metrics."""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    mse: Optional[float] = None
    mae: Optional[float] = None
    r2_score: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    total_trades: int = 0
    profitable_trades: int = 0


class BaseMLStrategy(ABC):
    """Base class for ML trading strategies."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.feature_engineer = FeatureEngineer()
        self.label_encoder = LabelEncoder() if config.prediction_type == PredictionType.CLASSIFICATION else None
        self.status = ModelStatus.TRAINING
        self.model_version = "1.0"
        self.training_history = []
        self.performance_history = []
        self.feature_names = []
        self.last_retrain = None
        self.prediction_cache = {}
        
        # SHAP explainer for interpretability
        self.shap_explainer = None
        
        # Performance tracking
        self.predictions_made = 0
        self.correct_predictions = 0
        self.total_return = 0.0
        self.trades = []
    
    @abstractmethod
    def _create_model(self) -> Any:
        """Create the ML model instance."""
        pass
    
    @abstractmethod
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Get hyperparameter grid for tuning."""
        pass
    
    def prepare_data(self, data: pd.DataFrame, target_column: str = None) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare features and target for training.
        
        Args:
            data: OHLCV data
            target_column: Target column name
            
        Returns:
            Tuple of (features, target)
        """
        try:
            # Extract features
            features = self.feature_engineer.extract_all_features(data)
            
            # Create target if not provided
            if target_column is None or target_column not in data.columns:
                target = self._create_target(data)
            else:
                target = data[target_column]
            
            # Align features and target
            common_index = features.index.intersection(target.index)
            features_aligned = features.loc[common_index]
            target_aligned = target.loc[common_index]
            
            # Remove NaN values
            mask = ~(features_aligned.isna().any(axis=1) | target_aligned.isna())
            features_clean = features_aligned[mask]
            target_clean = target_aligned[mask]
            
            # Store feature names
            self.feature_names = features_clean.columns.tolist()
            
            return features_clean, target_clean
        
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return pd.DataFrame(), pd.Series()
    
    def _create_target(self, data: pd.DataFrame) -> pd.Series:
        """Create target variable from price data.
        
        Args:
            data: OHLCV data
            
        Returns:
            Target series
        """
        try:
            close = data['close']
            
            # Calculate future returns
            future_returns = close.shift(-self.config.prediction_horizon) / close - 1
            
            if self.config.prediction_type == PredictionType.CLASSIFICATION:
                # Create classification labels
                # Buy: return > 0.5%, Sell: return < -0.5%, Hold: otherwise
                target = pd.Series(SignalType.HOLD.value, index=data.index)
                target[future_returns > 0.005] = SignalType.BUY.value
                target[future_returns < -0.005] = SignalType.SELL.value
            else:
                # Use raw returns for regression
                target = future_returns
            
            return target
        
        except Exception as e:
            logger.error(f"Error creating target: {e}")
            return pd.Series()
    
    def train(self, data: pd.DataFrame, target_column: str = None) -> bool:
        """Train the ML model.
        
        Args:
            data: Training data
            target_column: Target column name
            
        Returns:
            True if training successful
        """
        try:
            self.status = ModelStatus.TRAINING
            
            # Prepare data
            X, y = self.prepare_data(data, target_column)
            
            if len(X) < self.config.min_training_samples:
                logger.warning(f"Insufficient training samples: {len(X)} < {self.config.min_training_samples}")
                self.status = ModelStatus.FAILED
                return False
            
            # Encode labels for classification
            if self.config.prediction_type == PredictionType.CLASSIFICATION and self.label_encoder:
                y_encoded = self.label_encoder.fit_transform(y)
            else:
                y_encoded = y
            
            # Split data
            split_idx = int(len(X) * (1 - self.config.validation_split))
            X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
            y_train, y_val = y_encoded[:split_idx], y_encoded[split_idx:]
            
            # Create model
            self.model = self._create_model()
            
            # Hyperparameter tuning
            if self.config.hyperparameter_tuning:
                self.model = self._tune_hyperparameters(X_train, y_train)
            
            # Train model
            self.model.fit(X_train, y_train)
            
            # Validate model
            performance = self._validate_model(X_val, y_val)
            self.performance_history.append(performance)
            
            # Initialize SHAP explainer
            if SHAP_AVAILABLE:
                try:
                    if self.config.model_type == ModelType.RANDOM_FOREST:
                        self.shap_explainer = shap.TreeExplainer(self.model)
                    else:
                        # Use a sample for other models to avoid memory issues
                        sample_size = min(100, len(X_train))
                        sample_X = X_train.sample(n=sample_size, random_state=42)
                        self.shap_explainer = shap.KernelExplainer(self.model.predict, sample_X)
                except Exception as e:
                    logger.warning(f"Could not initialize SHAP explainer: {e}")
            
            self.status = ModelStatus.TRAINED
            self.last_retrain = datetime.now()
            
            # Log training results
            logger.info(f"Model trained successfully. Performance: {performance}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error training model: {e}")
            self.status = ModelStatus.FAILED
            return False
    
    def _tune_hyperparameters(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """Tune model hyperparameters.
        
        Args:
            X: Features
            y: Target
            
        Returns:
            Tuned model
        """
        try:
            param_grid = self._get_hyperparameter_grid()
            base_model = self._create_model()
            
            # Use TimeSeriesSplit for time series data
            tscv = TimeSeriesSplit(n_splits=self.config.cross_validation_folds)
            
            # Grid search
            grid_search = GridSearchCV(
                base_model,
                param_grid,
                cv=tscv,
                scoring='accuracy' if self.config.prediction_type == PredictionType.CLASSIFICATION else 'neg_mean_squared_error',
                n_jobs=-1,
                verbose=0
            )
            
            grid_search.fit(X, y)
            
            logger.info(f"Best parameters: {grid_search.best_params_}")
            logger.info(f"Best score: {grid_search.best_score_}")
            
            return grid_search.best_estimator_
        
        except Exception as e:
            logger.warning(f"Hyperparameter tuning failed: {e}. Using default parameters.")
            return self._create_model()
    
    def _validate_model(self, X_val: pd.DataFrame, y_val: pd.Series) -> ModelPerformance:
        """Validate model performance.
        
        Args:
            X_val: Validation features
            y_val: Validation target
            
        Returns:
            ModelPerformance object
        """
        try:
            predictions = self.model.predict(X_val)
            
            performance = ModelPerformance()
            
            if self.config.prediction_type == PredictionType.CLASSIFICATION:
                performance.accuracy = accuracy_score(y_val, predictions)
                performance.precision = precision_score(y_val, predictions, average='weighted', zero_division=0)
                performance.recall = recall_score(y_val, predictions, average='weighted', zero_division=0)
                performance.f1_score = f1_score(y_val, predictions, average='weighted', zero_division=0)
            else:
                performance.mse = mean_squared_error(y_val, predictions)
                performance.mae = mean_absolute_error(y_val, predictions)
                performance.r2_score = r2_score(y_val, predictions)
            
            return performance
        
        except Exception as e:
            logger.error(f"Error validating model: {e}")
            return ModelPerformance()
    
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        """Make prediction on new data.
        
        Args:
            data: Input data
            
        Returns:
            PredictionResult object
        """
        try:
            if self.model is None or self.status != ModelStatus.TRAINED:
                logger.warning("Model not trained")
                return PredictionResult(
                    timestamp=datetime.now(),
                    prediction=SignalType.HOLD.value,
                    confidence=0.0
                )
            
            # Extract features for the latest data point
            features = self.feature_engineer.extract_all_features(data)
            
            if len(features) == 0:
                return PredictionResult(
                    timestamp=datetime.now(),
                    prediction=SignalType.HOLD.value,
                    confidence=0.0
                )
            
            # Get the latest feature vector
            latest_features = features.iloc[-1:]
            
            # Check for missing features
            available_features = [f for f in self.feature_names if f in latest_features.columns]
            if len(available_features) < len(self.feature_names) * 0.8:  # At least 80% features available
                logger.warning(f"Missing features: {len(available_features)}/{len(self.feature_names)}")
                return PredictionResult(
                    timestamp=datetime.now(),
                    prediction=SignalType.HOLD.value,
                    confidence=0.0
                )
            
            # Select available features
            X = latest_features[available_features].fillna(0)
            
            # Make prediction
            prediction = self.model.predict(X)[0]
            
            # Get prediction probabilities if available
            probabilities = None
            confidence = 0.0
            
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[0]
                if self.label_encoder:
                    classes = self.label_encoder.classes_
                    probabilities = dict(zip(classes.astype(str), proba))
                confidence = max(proba)
            
            # Decode prediction if classification
            if self.config.prediction_type == PredictionType.CLASSIFICATION and self.label_encoder:
                prediction = self.label_encoder.inverse_transform([prediction])[0]
            
            # Calculate feature importance for this prediction
            feature_importance = None
            if SHAP_AVAILABLE and self.shap_explainer:
                try:
                    shap_values = self.shap_explainer.shap_values(X)
                    if isinstance(shap_values, list):  # Multi-class
                        shap_values = shap_values[0]  # Use first class
                    feature_importance = dict(zip(available_features, shap_values[0]))
                except Exception as e:
                    logger.warning(f"Could not calculate SHAP values: {e}")
            
            # Calculate signal strength
            signal_strength = self._calculate_signal_strength(prediction, confidence)
            
            result = PredictionResult(
                timestamp=datetime.now(),
                prediction=prediction,
                probability=probabilities,
                confidence=confidence,
                feature_importance=feature_importance,
                model_version=self.model_version,
                signal_strength=signal_strength
            )
            
            self.predictions_made += 1
            
            return result
        
        except Exception as e:
            logger.error(f"Error making prediction: {e}")
            return PredictionResult(
                timestamp=datetime.now(),
                prediction=SignalType.HOLD.value,
                confidence=0.0
            )
    
    def _calculate_signal_strength(self, prediction: Union[int, float], confidence: float) -> float:
        """Calculate signal strength based on prediction and confidence.
        
        Args:
            prediction: Model prediction
            confidence: Prediction confidence
            
        Returns:
            Signal strength (0-1)
        """
        try:
            if self.config.prediction_type == PredictionType.CLASSIFICATION:
                # For classification, use confidence directly
                if prediction == SignalType.HOLD.value:
                    return 0.0
                else:
                    return confidence
            else:
                # For regression, normalize prediction to 0-1 range
                return min(1.0, abs(prediction) * 10)  # Assuming returns are typically < 10%
        
        except Exception as e:
            logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained.
        
        Returns:
            True if retraining is needed
        """
        try:
            # Check if enough new samples have been processed
            if self.predictions_made >= self.config.retrain_frequency:
                return True
            
            # Check if performance has degraded
            if len(self.performance_history) >= 2:
                recent_performance = self.performance_history[-1]
                previous_performance = self.performance_history[-2]
                
                if self.config.prediction_type == PredictionType.CLASSIFICATION:
                    if (recent_performance.accuracy and previous_performance.accuracy and
                        recent_performance.accuracy < previous_performance.accuracy * 0.9):
                        return True
                else:
                    if (recent_performance.mse and previous_performance.mse and
                        recent_performance.mse > previous_performance.mse * 1.1):
                        return True
            
            return False
        
        except Exception as e:
            logger.error(f"Error checking retrain condition: {e}")
            return False
    
    def save_model(self, filepath: str) -> bool:
        """Save model to disk.
        
        Args:
            filepath: Path to save model
            
        Returns:
            True if successful
        """
        try:
            model_data = {
                'model': self.model,
                'config': self.config,
                'feature_names': self.feature_names,
                'label_encoder': self.label_encoder,
                'model_version': self.model_version,
                'performance_history': self.performance_history
            }
            
            joblib.dump(model_data, filepath)
            logger.info(f"Model saved to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """Load model from disk.
        
        Args:
            filepath: Path to load model from
            
        Returns:
            True if successful
        """
        try:
            model_data = joblib.load(filepath)
            
            self.model = model_data['model']
            self.config = model_data['config']
            self.feature_names = model_data['feature_names']
            self.label_encoder = model_data['label_encoder']
            self.model_version = model_data['model_version']
            self.performance_history = model_data['performance_history']
            
            self.status = ModelStatus.TRAINED
            logger.info(f"Model loaded from {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model.
        
        Returns:
            Dictionary of feature importance scores
        """
        try:
            if self.model is None:
                return {}
            
            if hasattr(self.model, 'feature_importances_'):
                importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))
                # Sort by importance
                return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            else:
                logger.warning("Model does not support feature importance")
                return {}
        
        except Exception as e:
            logger.error(f"Error getting feature importance: {e}")
            return {}


class RandomForestStrategy(BaseMLStrategy):
    """Random Forest trading strategy."""
    
    def _create_model(self) -> RandomForestClassifier:
        """Create Random Forest model."""
        if self.config.prediction_type == PredictionType.CLASSIFICATION:
            return RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight=self.config.class_weight,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        else:
            return RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=self.config.random_state,
                n_jobs=-1
            )
    
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Get hyperparameter grid for Random Forest."""
        return {
            'n_estimators': [50, 100, 200],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }


class XGBoostStrategy(BaseMLStrategy):
    """XGBoost trading strategy."""
    
    def _create_model(self) -> Any:
        """Create XGBoost model."""
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not available. Install with: pip install xgboost")
        
        if self.config.prediction_type == PredictionType.CLASSIFICATION:
            return xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=self.config.random_state,
                n_jobs=-1
            )
        else:
            return xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=self.config.random_state,
                n_jobs=-1
            )
    
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Get hyperparameter grid for XGBoost."""
        return {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 6, 9],
            'learning_rate': [0.01, 0.1, 0.2],
            'subsample': [0.8, 0.9, 1.0],
            'colsample_bytree': [0.8, 0.9, 1.0]
        }


class SVMStrategy(BaseMLStrategy):
    """Support Vector Machine trading strategy."""
    
    def _create_model(self) -> Any:
        """Create SVM model."""
        if self.config.prediction_type == PredictionType.CLASSIFICATION:
            return SVC(
                kernel='rbf',
                C=1.0,
                gamma='scale',
                class_weight=self.config.class_weight,
                probability=True,
                random_state=self.config.random_state
            )
        else:
            return SVR(
                kernel='rbf',
                C=1.0,
                gamma='scale'
            )
    
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Get hyperparameter grid for SVM."""
        return {
            'C': [0.1, 1.0, 10.0],
            'gamma': ['scale', 'auto', 0.001, 0.01, 0.1],
            'kernel': ['rbf', 'poly', 'sigmoid']
        }


class NeuralNetworkStrategy(BaseMLStrategy):
    """Neural Network (MLP) trading strategy."""
    
    def _create_model(self) -> Any:
        """Create Neural Network model."""
        if self.config.prediction_type == PredictionType.CLASSIFICATION:
            return MLPClassifier(
                hidden_layer_sizes=(100, 50),
                activation='relu',
                solver='adam',
                alpha=0.001,
                learning_rate='adaptive',
                max_iter=500,
                random_state=self.config.random_state
            )
        else:
            return MLPRegressor(
                hidden_layer_sizes=(100, 50),
                activation='relu',
                solver='adam',
                alpha=0.001,
                learning_rate='adaptive',
                max_iter=500,
                random_state=self.config.random_state
            )
    
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Get hyperparameter grid for Neural Network."""
        return {
            'hidden_layer_sizes': [(50,), (100,), (100, 50), (100, 100)],
            'activation': ['relu', 'tanh'],
            'alpha': [0.0001, 0.001, 0.01],
            'learning_rate': ['constant', 'adaptive']
        }


class EnsembleStrategy(BaseMLStrategy):
    """Ensemble strategy combining multiple models."""
    
    def __init__(self, config: ModelConfig, models: List[BaseMLStrategy] = None):
        super().__init__(config)
        self.models = models or []
        self.model_weights = {}
    
    def _create_model(self) -> Any:
        """Ensemble doesn't use a single model."""
        return None
    
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Ensemble doesn't use hyperparameter tuning."""
        return {}
    
    def add_model(self, model: BaseMLStrategy, weight: float = 1.0) -> None:
        """Add model to ensemble.
        
        Args:
            model: ML strategy to add
            weight: Model weight in ensemble
        """
        self.models.append(model)
        self.model_weights[len(self.models) - 1] = weight
    
    def train(self, data: pd.DataFrame, target_column: str = None) -> bool:
        """Train all models in ensemble.
        
        Args:
            data: Training data
            target_column: Target column name
            
        Returns:
            True if at least one model trained successfully
        """
        success_count = 0
        
        for model in self.models:
            if model.train(data, target_column):
                success_count += 1
        
        if success_count > 0:
            self.status = ModelStatus.TRAINED
            return True
        else:
            self.status = ModelStatus.FAILED
            return False
    
    def predict(self, data: pd.DataFrame) -> PredictionResult:
        """Make ensemble prediction.
        
        Args:
            data: Input data
            
        Returns:
            Ensemble prediction result
        """
        try:
            if not self.models:
                return PredictionResult(
                    timestamp=datetime.now(),
                    prediction=SignalType.HOLD.value,
                    confidence=0.0
                )
            
            predictions = []
            confidences = []
            weights = []
            
            for i, model in enumerate(self.models):
                if model.status == ModelStatus.TRAINED:
                    result = model.predict(data)
                    predictions.append(result.prediction)
                    confidences.append(result.confidence)
                    weights.append(self.model_weights.get(i, 1.0))
            
            if not predictions:
                return PredictionResult(
                    timestamp=datetime.now(),
                    prediction=SignalType.HOLD.value,
                    confidence=0.0
                )
            
            # Weighted average prediction
            if self.config.prediction_type == PredictionType.CLASSIFICATION:
                # Majority voting with weights
                vote_counts = {}
                for pred, weight in zip(predictions, weights):
                    vote_counts[pred] = vote_counts.get(pred, 0) + weight
                
                ensemble_prediction = max(vote_counts, key=vote_counts.get)
            else:
                # Weighted average for regression
                total_weight = sum(weights)
                ensemble_prediction = sum(p * w for p, w in zip(predictions, weights)) / total_weight
            
            # Average confidence
            ensemble_confidence = sum(c * w for c, w in zip(confidences, weights)) / sum(weights)
            
            return PredictionResult(
                timestamp=datetime.now(),
                prediction=ensemble_prediction,
                confidence=ensemble_confidence,
                model_version=f"ensemble_{len(self.models)}"
            )
        
        except Exception as e:
            logger.error(f"Error making ensemble prediction: {e}")
            return PredictionResult(
                timestamp=datetime.now(),
                prediction=SignalType.HOLD.value,
                confidence=0.0
            )


class ModelManager:
    """Manages multiple ML models and their lifecycle."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True)
        self.models = {}
        self.active_model = None
    
    def create_model(self, model_type: ModelType, config: ModelConfig, name: str) -> BaseMLStrategy:
        """Create a new ML model.
        
        Args:
            model_type: Type of model to create
            config: Model configuration
            name: Model name
            
        Returns:
            Created model instance
        """
        try:
            if model_type == ModelType.RANDOM_FOREST:
                model = RandomForestStrategy(config)
            elif model_type == ModelType.XGBOOST:
                model = XGBoostStrategy(config)
            elif model_type == ModelType.SVM:
                model = SVMStrategy(config)
            elif model_type == ModelType.NEURAL_NETWORK:
                model = NeuralNetworkStrategy(config)
            elif model_type == ModelType.ENSEMBLE:
                model = EnsembleStrategy(config)
            else:
                raise ValueError(f"Unknown model type: {model_type}")
            
            self.models[name] = model
            
            if self.active_model is None:
                self.active_model = name
            
            logger.info(f"Created {model_type.value} model: {name}")
            return model
        
        except Exception as e:
            logger.error(f"Error creating model: {e}")
            raise
    
    def train_model(self, name: str, data: pd.DataFrame, target_column: str = None) -> bool:
        """Train a specific model.
        
        Args:
            name: Model name
            data: Training data
            target_column: Target column name
            
        Returns:
            True if training successful
        """
        if name not in self.models:
            logger.error(f"Model {name} not found")
            return False
        
        return self.models[name].train(data, target_column)
    
    def predict(self, name: str, data: pd.DataFrame) -> PredictionResult:
        """Make prediction with specific model.
        
        Args:
            name: Model name
            data: Input data
            
        Returns:
            Prediction result
        """
        if name not in self.models:
            logger.error(f"Model {name} not found")
            return PredictionResult(
                timestamp=datetime.now(),
                prediction=SignalType.HOLD.value,
                confidence=0.0
            )
        
        return self.models[name].predict(data)
    
    def predict_active(self, data: pd.DataFrame) -> PredictionResult:
        """Make prediction with active model.
        
        Args:
            data: Input data
            
        Returns:
            Prediction result
        """
        if self.active_model is None:
            logger.error("No active model")
            return PredictionResult(
                timestamp=datetime.now(),
                prediction=SignalType.HOLD.value,
                confidence=0.0
            )
        
        return self.predict(self.active_model, data)
    
    def set_active_model(self, name: str) -> bool:
        """Set active model.
        
        Args:
            name: Model name
            
        Returns:
            True if successful
        """
        if name not in self.models:
            logger.error(f"Model {name} not found")
            return False
        
        self.active_model = name
        logger.info(f"Active model set to: {name}")
        return True
    
    def save_model(self, name: str) -> bool:
        """Save model to disk.
        
        Args:
            name: Model name
            
        Returns:
            True if successful
        """
        if name not in self.models:
            logger.error(f"Model {name} not found")
            return False
        
        filepath = self.models_dir / f"{name}.joblib"
        return self.models[name].save_model(str(filepath))
    
    def load_model(self, name: str, model_type: ModelType, config: ModelConfig) -> bool:
        """Load model from disk.
        
        Args:
            name: Model name
            model_type: Type of model
            config: Model configuration
            
        Returns:
            True if successful
        """
        try:
            filepath = self.models_dir / f"{name}.joblib"
            
            if not filepath.exists():
                logger.error(f"Model file not found: {filepath}")
                return False
            
            # Create model instance
            model = self.create_model(model_type, config, name)
            
            # Load saved state
            return model.load_model(str(filepath))
        
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_model_performance(self, name: str) -> Optional[ModelPerformance]:
        """Get model performance metrics.
        
        Args:
            name: Model name
            
        Returns:
            Latest performance metrics
        """
        if name not in self.models:
            return None
        
        model = self.models[name]
        if model.performance_history:
            return model.performance_history[-1]
        
        return None
    
    def list_models(self) -> Dict[str, Dict[str, Any]]:
        """List all models and their status.
        
        Returns:
            Dictionary of model information
        """
        model_info = {}
        
        for name, model in self.models.items():
            model_info[name] = {
                'type': model.config.model_type.value,
                'status': model.status.value,
                'predictions_made': model.predictions_made,
                'last_retrain': model.last_retrain,
                'is_active': name == self.active_model
            }
        
        return model_info