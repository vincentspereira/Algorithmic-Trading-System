"""Machine Learning Model Training Module for Trading Strategies"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import joblib
import json
from pathlib import Path
from abc import ABC, abstractmethod

from sklearn.model_selection import TimeSeriesSplit, GridSearchCV, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.svm import SVR
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

from nautilus_trader_engine.ml.feature_engineering import FeatureEngineeringPipeline, FeatureConfig


class ModelType(Enum):
    """Types of ML models"""
    LINEAR_REGRESSION = "linear_regression"
    RIDGE_REGRESSION = "ridge_regression"
    LASSO_REGRESSION = "lasso_regression"
    ELASTIC_NET = "elastic_net"
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    SVM = "svm"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"


class PredictionHorizon(Enum):
    """Prediction time horizons"""
    INTRADAY_1MIN = "1min"
    INTRADAY_5MIN = "5min"
    INTRADAY_15MIN = "15min"
    INTRADAY_1HOUR = "1hour"
    DAILY = "1day"
    WEEKLY = "1week"
    MONTHLY = "1month"


class ObjectiveType(Enum):
    """ML objective types"""
    REGRESSION = "regression"
    CLASSIFICATION = "classification"
    RANKING = "ranking"


@dataclass
class ModelConfig:
    """Configuration for ML model training"""
    model_type: ModelType
    objective: ObjectiveType = ObjectiveType.REGRESSION
    prediction_horizon: PredictionHorizon = PredictionHorizon.DAILY
    target_variable: str = "future_return"
    
    # Training parameters
    test_size: float = 0.2
    validation_size: float = 0.2
    cv_folds: int = 5
    random_state: int = 42
    
    # Model-specific hyperparameters
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    
    # Hyperparameter tuning
    tune_hyperparameters: bool = True
    tuning_method: str = "grid_search"  # 'grid_search', 'random_search'
    tuning_iterations: int = 100
    
    # Feature selection
    feature_selection: bool = True
    max_features: Optional[int] = None
    
    # Model persistence
    save_model: bool = True
    model_path: str = "models/ml_models"
    
    # Performance thresholds
    min_r2_score: float = 0.1
    max_mse_threshold: float = 1.0


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_id: str
    model_type: ModelType
    training_date: datetime
    
    # Training metrics
    train_r2: float
    train_mse: float
    train_mae: float
    
    # Validation metrics
    val_r2: float
    val_mse: float
    val_mae: float
    
    # Test metrics
    test_r2: float
    test_mse: float
    test_mae: float
    
    # Additional metrics
    feature_count: int
    training_samples: int
    training_time: float
    
    # Model stability
    cv_r2_mean: float
    cv_r2_std: float
    
    # Feature importance (top 10)
    top_features: List[Tuple[str, float]]


@dataclass
class PredictionResult:
    """ML model prediction result"""
    model_id: str
    prediction_time: datetime
    symbol: str
    prediction_horizon: PredictionHorizon
    
    # Predictions
    predicted_value: float
    prediction_confidence: float
    
    # Model metadata
    model_version: str
    feature_count: int
    
    # Additional info
    market_regime: Optional[str] = None
    volatility_regime: Optional[str] = None


class BaseMLModel(ABC):
    """Base class for ML models"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        self.performance = None
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def _create_model(self) -> Any:
        """Create the underlying ML model"""
        pass
    
    @abstractmethod
    def _get_hyperparameter_grid(self) -> Dict[str, List]:
        """Get hyperparameter grid for tuning"""
        pass
    
    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'BaseMLModel':
        """Train the model"""
        self.feature_names = list(X.columns)
        
        # Scale features if needed
        if self._needs_scaling():
            self.scaler = StandardScaler()
            X_scaled = pd.DataFrame(
                self.scaler.fit_transform(X),
                columns=X.columns,
                index=X.index
            )
        else:
            X_scaled = X
        
        # Create and train model
        self.model = self._create_model()
        self.model.fit(X_scaled, y)
        
        self.is_trained = True
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions"""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Scale features if scaler was used during training
        if self.scaler is not None:
            X_scaled = pd.DataFrame(
                self.scaler.transform(X),
                columns=X.columns,
                index=X.index
            )
        else:
            X_scaled = X
        
        return self.model.predict(X_scaled)
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        if not self.is_trained:
            return {}
        
        if hasattr(self.model, 'feature_importances_'):
            importance_scores = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importance_scores = np.abs(self.model.coef_)
        else:
            return {}
        
        return dict(zip(self.feature_names, importance_scores))
    
    def _needs_scaling(self) -> bool:
        """Check if model needs feature scaling"""
        scaling_models = [ModelType.SVM, ModelType.NEURAL_NETWORK, ModelType.LINEAR_REGRESSION,
                         ModelType.RIDGE_REGRESSION, ModelType.LASSO_REGRESSION, ModelType.ELASTIC_NET]
        return self.config.model_type in scaling_models


class LinearRegressionModel(BaseMLModel):
    """Linear Regression model"""
    
    def _create_model(self):
        return LinearRegression(**self.config.hyperparameters)
    
    def _get_hyperparameter_grid(self):
        return {'fit_intercept': [True, False]}


class RidgeRegressionModel(BaseMLModel):
    """Ridge Regression model"""
    
    def _create_model(self):
        return Ridge(**self.config.hyperparameters)
    
    def _get_hyperparameter_grid(self):
        return {
            'alpha': [0.1, 1.0, 10.0, 100.0],
            'fit_intercept': [True, False]
        }


class RandomForestModel(BaseMLModel):
    """Random Forest model"""
    
    def _create_model(self):
        default_params = {
            'n_estimators': 100,
            'max_depth': None,
            'min_samples_split': 2,
            'min_samples_leaf': 1,
            'random_state': self.config.random_state
        }
        default_params.update(self.config.hyperparameters)
        return RandomForestRegressor(**default_params)
    
    def _get_hyperparameter_grid(self):
        return {
            'n_estimators': [50, 100, 200],
            'max_depth': [None, 10, 20, 30],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }


class XGBoostModel(BaseMLModel):
    """XGBoost model"""
    
    def _create_model(self):
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost not available. Install with: pip install xgboost")
        
        default_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'random_state': self.config.random_state
        }
        default_params.update(self.config.hyperparameters)
        return xgb.XGBRegressor(**default_params)
    
    def _get_hyperparameter_grid(self):
        return {
            'n_estimators': [50, 100, 200],
            'max_depth': [3, 6, 9],
            'learning_rate': [0.01, 0.1, 0.2],
            'subsample': [0.8, 0.9, 1.0]
        }


class NeuralNetworkModel(BaseMLModel):
    """Neural Network model"""
    
    def _create_model(self):
        default_params = {
            'hidden_layer_sizes': (100, 50),
            'activation': 'relu',
            'solver': 'adam',
            'max_iter': 1000,
            'random_state': self.config.random_state
        }
        default_params.update(self.config.hyperparameters)
        return MLPRegressor(**default_params)
    
    def _get_hyperparameter_grid(self):
        return {
            'hidden_layer_sizes': [(50,), (100,), (100, 50), (100, 50, 25)],
            'activation': ['relu', 'tanh'],
            'learning_rate': ['constant', 'adaptive'],
            'alpha': [0.0001, 0.001, 0.01]
        }


class MLModelTrainer:
    """Main class for training ML models"""
    
    def __init__(self, feature_pipeline: FeatureEngineeringPipeline):
        self.feature_pipeline = feature_pipeline
        self.models = {}
        self.performance_history = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Model registry
        self.model_classes = {
            ModelType.LINEAR_REGRESSION: LinearRegressionModel,
            ModelType.RIDGE_REGRESSION: RidgeRegressionModel,
            ModelType.RANDOM_FOREST: RandomForestModel,
            ModelType.NEURAL_NETWORK: NeuralNetworkModel
        }
        
        if XGBOOST_AVAILABLE:
            self.model_classes[ModelType.XGBOOST] = XGBoostModel
    
    def prepare_training_data(self, data: pd.DataFrame, config: ModelConfig) -> Tuple[pd.DataFrame, pd.Series]:
        """Prepare data for training"""
        # Extract features
        features = self.feature_pipeline.fit_transform(
            data, 
            target=self._create_target_variable(data, config)
        )
        
        # Create target variable
        target = self._create_target_variable(data, config)
        
        # Align features and target
        common_index = features.index.intersection(target.index)
        features = features.loc[common_index]
        target = target.loc[common_index]
        
        # Remove any remaining NaN values
        mask = ~(features.isna().any(axis=1) | target.isna())
        features = features[mask]
        target = target[mask]
        
        return features, target
    
    def _create_target_variable(self, data: pd.DataFrame, config: ModelConfig) -> pd.Series:
        """Create target variable based on prediction horizon"""
        if config.target_variable == "future_return":
            # Calculate future returns based on prediction horizon
            horizon_map = {
                PredictionHorizon.INTRADAY_1MIN: 1,
                PredictionHorizon.INTRADAY_5MIN: 5,
                PredictionHorizon.INTRADAY_15MIN: 15,
                PredictionHorizon.INTRADAY_1HOUR: 60,
                PredictionHorizon.DAILY: 1,
                PredictionHorizon.WEEKLY: 5,
                PredictionHorizon.MONTHLY: 20
            }
            
            periods = horizon_map.get(config.prediction_horizon, 1)
            target = data['close'].pct_change(periods).shift(-periods)
            
        elif config.target_variable in data.columns:
            target = data[config.target_variable]
        else:
            raise ValueError(f"Target variable '{config.target_variable}' not found in data")
        
        return target.dropna()
    
    def train_model(self, data: pd.DataFrame, config: ModelConfig) -> str:
        """Train a single model"""
        start_time = datetime.now()
        
        # Prepare data
        features, target = self.prepare_training_data(data, config)
        
        if len(features) == 0:
            raise ValueError("No valid training data after preprocessing")
        
        # Split data
        train_features, val_features, test_features, train_target, val_target, test_target = \
            self._split_time_series_data(features, target, config)
        
        # Create model
        if config.model_type not in self.model_classes:
            raise ValueError(f"Model type {config.model_type} not supported")
        
        model_class = self.model_classes[config.model_type]
        
        # Hyperparameter tuning
        if config.tune_hyperparameters:
            best_params = self._tune_hyperparameters(
                model_class, train_features, train_target, val_features, val_target, config
            )
            config.hyperparameters.update(best_params)
        
        # Train final model
        model = model_class(config)
        model.fit(train_features, train_target)
        
        # Evaluate model
        performance = self._evaluate_model(
            model, train_features, train_target, val_features, val_target, 
            test_features, test_target, config, start_time
        )
        
        # Generate model ID
        model_id = f"{config.model_type.value}_{config.prediction_horizon.value}_{int(start_time.timestamp())}"
        
        # Store model
        self.models[model_id] = {
            'model': model,
            'config': config,
            'performance': performance,
            'training_date': start_time
        }
        
        # Save model if configured
        if config.save_model:
            self._save_model(model_id, model, config)
        
        # Store performance
        self.performance_history.append(performance)
        
        self.logger.info(f"Model {model_id} trained successfully. R² Score: {performance.test_r2:.4f}")
        
        return model_id
    
    def _split_time_series_data(self, features: pd.DataFrame, target: pd.Series, config: ModelConfig) -> Tuple:
        """Split time series data maintaining temporal order"""
        n_samples = len(features)
        
        # Calculate split indices
        test_start = int(n_samples * (1 - config.test_size))
        val_start = int(test_start * (1 - config.validation_size))
        
        # Split data
        train_features = features.iloc[:val_start]
        val_features = features.iloc[val_start:test_start]
        test_features = features.iloc[test_start:]
        
        train_target = target.iloc[:val_start]
        val_target = target.iloc[val_start:test_start]
        test_target = target.iloc[test_start:]
        
        return train_features, val_features, test_features, train_target, val_target, test_target
    
    def _tune_hyperparameters(self, model_class, train_features: pd.DataFrame, train_target: pd.Series,
                             val_features: pd.DataFrame, val_target: pd.Series, config: ModelConfig) -> Dict:
        """Tune model hyperparameters"""
        # Create base model for parameter grid
        base_model = model_class(config)
        param_grid = base_model._get_hyperparameter_grid()
        
        if not param_grid:
            return {}
        
        # Combine training and validation for cross-validation
        X_tune = pd.concat([train_features, val_features])
        y_tune = pd.concat([train_target, val_target])
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=config.cv_folds)
        
        # Choose search method
        if config.tuning_method == "grid_search":
            search = GridSearchCV(
                base_model._create_model(),
                param_grid,
                cv=tscv,
                scoring='r2',
                n_jobs=-1
            )
        else:  # random_search
            search = RandomizedSearchCV(
                base_model._create_model(),
                param_grid,
                n_iter=config.tuning_iterations,
                cv=tscv,
                scoring='r2',
                n_jobs=-1,
                random_state=config.random_state
            )
        
        # Perform search
        search.fit(X_tune, y_tune)
        
        self.logger.info(f"Best hyperparameters: {search.best_params_}")
        self.logger.info(f"Best CV score: {search.best_score_:.4f}")
        
        return search.best_params_
    
    def _evaluate_model(self, model: BaseMLModel, train_features: pd.DataFrame, train_target: pd.Series,
                       val_features: pd.DataFrame, val_target: pd.Series,
                       test_features: pd.DataFrame, test_target: pd.Series,
                       config: ModelConfig, start_time: datetime) -> ModelPerformance:
        """Evaluate model performance"""
        # Training predictions
        train_pred = model.predict(train_features)
        train_r2 = r2_score(train_target, train_pred)
        train_mse = mean_squared_error(train_target, train_pred)
        train_mae = mean_absolute_error(train_target, train_pred)
        
        # Validation predictions
        val_pred = model.predict(val_features)
        val_r2 = r2_score(val_target, val_pred)
        val_mse = mean_squared_error(val_target, val_pred)
        val_mae = mean_absolute_error(val_target, val_pred)
        
        # Test predictions
        test_pred = model.predict(test_features)
        test_r2 = r2_score(test_target, test_pred)
        test_mse = mean_squared_error(test_target, test_pred)
        test_mae = mean_absolute_error(test_target, test_pred)
        
        # Cross-validation scores
        cv_scores = self._cross_validate_model(model, train_features, train_target, config)
        
        # Feature importance
        feature_importance = model.get_feature_importance()
        top_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Training time
        training_time = (datetime.now() - start_time).total_seconds()
        
        # Generate model ID
        model_id = f"{config.model_type.value}_{config.prediction_horizon.value}_{int(start_time.timestamp())}"
        
        return ModelPerformance(
            model_id=model_id,
            model_type=config.model_type,
            training_date=start_time,
            train_r2=train_r2,
            train_mse=train_mse,
            train_mae=train_mae,
            val_r2=val_r2,
            val_mse=val_mse,
            val_mae=val_mae,
            test_r2=test_r2,
            test_mse=test_mse,
            test_mae=test_mae,
            feature_count=len(train_features.columns),
            training_samples=len(train_features),
            training_time=training_time,
            cv_r2_mean=np.mean(cv_scores),
            cv_r2_std=np.std(cv_scores),
            top_features=top_features
        )
    
    def _cross_validate_model(self, model: BaseMLModel, features: pd.DataFrame, target: pd.Series, config: ModelConfig) -> List[float]:
        """Perform cross-validation"""
        tscv = TimeSeriesSplit(n_splits=config.cv_folds)
        cv_scores = []
        
        for train_idx, val_idx in tscv.split(features):
            # Split data
            X_train, X_val = features.iloc[train_idx], features.iloc[val_idx]
            y_train, y_val = target.iloc[train_idx], target.iloc[val_idx]
            
            # Create and train model
            cv_model = model.__class__(config)
            cv_model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = cv_model.predict(X_val)
            score = r2_score(y_val, y_pred)
            cv_scores.append(score)
        
        return cv_scores
    
    def _save_model(self, model_id: str, model: BaseMLModel, config: ModelConfig) -> None:
        """Save model to disk"""
        model_dir = Path(config.model_path)
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_file = model_dir / f"{model_id}.joblib"
        joblib.dump(model, model_file)
        
        # Save config
        config_file = model_dir / f"{model_id}_config.json"
        config_dict = {
            'model_type': config.model_type.value,
            'objective': config.objective.value,
            'prediction_horizon': config.prediction_horizon.value,
            'target_variable': config.target_variable,
            'hyperparameters': config.hyperparameters
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_dict, f, indent=2)
        
        self.logger.info(f"Model {model_id} saved to {model_file}")
    
    def load_model(self, model_id: str, model_path: Optional[str] = None) -> BaseMLModel:
        """Load model from disk"""
        if model_path is None:
            model_path = "models/ml_models"
        
        model_dir = Path(model_path)
        model_file = model_dir / f"{model_id}.joblib"
        
        if not model_file.exists():
            raise FileNotFoundError(f"Model file {model_file} not found")
        
        model = joblib.load(model_file)
        self.models[model_id] = {
            'model': model,
            'loading_date': datetime.now()
        }
        
        return model
    
    def predict(self, model_id: str, data: pd.DataFrame, symbol: str) -> PredictionResult:
        """Make prediction using trained model"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")
        
        model_info = self.models[model_id]
        model = model_info['model']
        config = model_info.get('config')
        
        # Extract features
        features = self.feature_pipeline.transform(data)
        
        # Make prediction
        prediction = model.predict(features.tail(1))[0]
        
        # Calculate confidence (simplified)
        confidence = min(0.95, max(0.05, model_info.get('performance', ModelPerformance(
            model_id='', model_type=ModelType.LINEAR_REGRESSION, training_date=datetime.now(),
            train_r2=0, train_mse=0, train_mae=0, val_r2=0, val_mse=0, val_mae=0,
            test_r2=0, test_mse=0, test_mae=0, feature_count=0, training_samples=0,
            training_time=0, cv_r2_mean=0, cv_r2_std=0, top_features=[]
        )).test_r2))
        
        return PredictionResult(
            model_id=model_id,
            prediction_time=datetime.now(),
            symbol=symbol,
            prediction_horizon=config.prediction_horizon if config else PredictionHorizon.DAILY,
            predicted_value=prediction,
            prediction_confidence=confidence,
            model_version="1.0",
            feature_count=len(features.columns)
        )
    
    def get_model_performance_summary(self) -> pd.DataFrame:
        """Get summary of all model performances"""
        if not self.performance_history:
            return pd.DataFrame()
        
        summary_data = []
        for perf in self.performance_history:
            summary_data.append({
                'model_id': perf.model_id,
                'model_type': perf.model_type.value,
                'training_date': perf.training_date,
                'test_r2': perf.test_r2,
                'test_mse': perf.test_mse,
                'cv_r2_mean': perf.cv_r2_mean,
                'cv_r2_std': perf.cv_r2_std,
                'feature_count': perf.feature_count,
                'training_samples': perf.training_samples,
                'training_time': perf.training_time
            })
        
        return pd.DataFrame(summary_data).sort_values('test_r2', ascending=False)
    
    def get_best_model(self, metric: str = 'test_r2') -> Optional[str]:
        """Get the best performing model ID"""
        if not self.performance_history:
            return None
        
        best_perf = max(self.performance_history, key=lambda x: getattr(x, metric))
        return best_perf.model_id


# Global model trainer instance
_model_trainer = None


def get_model_trainer(feature_pipeline: Optional[FeatureEngineeringPipeline] = None) -> MLModelTrainer:
    """Get global model trainer instance"""
    global _model_trainer
    if _model_trainer is None:
        if feature_pipeline is None:
            from nautilus_trader_engine.ml.feature_engineering import get_feature_pipeline
            feature_pipeline = get_feature_pipeline()
        _model_trainer = MLModelTrainer(feature_pipeline)
    return _model_trainer


def initialize_model_trainer(feature_pipeline: FeatureEngineeringPipeline) -> MLModelTrainer:
    """Initialize global model trainer"""
    global _model_trainer
    _model_trainer = MLModelTrainer(feature_pipeline)
    return _model_trainer