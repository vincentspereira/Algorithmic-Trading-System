"""
Forecasting Models Infrastructure for AI Assistant
Provides base classes and utilities for stock price prediction models

This module serves as the foundation for all forecasting models in the AI Assistant,
providing common interfaces, data preprocessing, and integration with the Feast feature store.

Author: Kilo Code
Version: 1.0.0
"""

import os
import logging
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
import joblib

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported forecasting model types"""
    LSTM = "lstm"
    ARIMA = "arima"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    PROPHET = "prophet"
    ENSEMBLE = "ensemble"


class PredictionHorizon(Enum):
    """Supported prediction horizons"""
    ONE_DAY = 1
    SEVEN_DAYS = 7
    THIRTY_DAYS = 30


@dataclass
class ModelConfig:
    """Configuration for forecasting models"""
    model_type: ModelType
    prediction_horizon: PredictionHorizon
    lookback_window: int = 60  # Number of historical days to use
    features: List[str] = field(default_factory=list)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    scaling_method: str = "standard"  # "standard", "minmax", or "none"
    target_column: str = "closing_price"
    
    def __post_init__(self):
        if not self.features:
            self.features = [
                "closing_price", "daily_volume", "daily_high", "daily_low",
                "sma_20", "sma_50", "rsi_14", "macd_line", "volatility_20d"
            ]


@dataclass
class PredictionResult:
    """Result of a forecasting prediction"""
    ticker: str
    model_type: ModelType
    prediction_horizon: PredictionHorizon
    predictions: np.ndarray
    confidence_intervals: Optional[Tuple[np.ndarray, np.ndarray]] = None
    prediction_dates: Optional[List[datetime]] = None
    model_confidence: float = 0.0
    feature_importance: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert prediction result to dictionary"""
        return {
            "ticker": self.ticker,
            "model_type": self.model_type.value,
            "prediction_horizon": self.prediction_horizon.value,
            "predictions": self.predictions.tolist() if isinstance(self.predictions, np.ndarray) else self.predictions,
            "confidence_intervals": {
                "lower": self.confidence_intervals[0].tolist() if self.confidence_intervals else None,
                "upper": self.confidence_intervals[1].tolist() if self.confidence_intervals else None
            } if self.confidence_intervals else None,
            "prediction_dates": [d.isoformat() for d in self.prediction_dates] if self.prediction_dates else None,
            "model_confidence": self.model_confidence,
            "feature_importance": self.feature_importance,
            "metadata": self.metadata
        }


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    mae: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0
    directional_accuracy: float = 0.0
    r2_score: float = 0.0
    sharpe_ratio: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert performance metrics to dictionary"""
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "directional_accuracy": self.directional_accuracy,
            "r2_score": self.r2_score,
            "sharpe_ratio": self.sharpe_ratio
        }


class BaseForecastingModel(ABC):
    """Abstract base class for all forecasting models"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.scaler = None
        self.is_trained = False
        self.feature_columns = None
        self.model_path = None
        
        # Initialize scaler based on config
        if config.scaling_method == "standard":
            self.scaler = StandardScaler()
        elif config.scaling_method == "minmax":
            self.scaler = MinMaxScaler()
        elif config.scaling_method == "none":
            self.scaler = None
        else:
            raise ValueError(f"Unknown scaling method: {config.scaling_method}")
    
    @abstractmethod
    def _build_model(self) -> Any:
        """Build the specific model architecture"""
        pass
    
    @abstractmethod
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the specific model"""
        pass
    
    @abstractmethod
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with the specific model"""
        pass
    
    def preprocess_data(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Preprocess data for training/prediction
        
        Args:
            data: Raw market data DataFrame
            
        Returns:
            Tuple of (features, targets)
        """
        # Ensure data is sorted by date
        if 'event_timestamp' in data.columns:
            data = data.sort_values('event_timestamp')
        
        # Select features
        available_features = [col for col in self.config.features if col in data.columns]
        if not available_features:
            raise ValueError(f"No features found in data. Available columns: {data.columns.tolist()}")
        
        self.feature_columns = available_features
        feature_data = data[available_features].copy()
        
        # Handle missing values
        feature_data = feature_data.fillna(method='ffill').fillna(method='bfill')
        
        # Create sequences for time series models
        X, y = self._create_sequences(feature_data)
        
        # Scale features if scaler is configured
        if self.scaler is not None:
            X_reshaped = X.reshape(-1, X.shape[-1])
            X_scaled = self.scaler.fit_transform(X_reshaped)
            X = X_scaled.reshape(X.shape)
        
        return X, y
    
    def _create_sequences(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for time series prediction
        
        Args:
            data: Feature data DataFrame
            
        Returns:
            Tuple of (X, y) sequences
        """
        target_col_idx = data.columns.get_loc(self.config.target_column)
        
        X, y = [], []
        for i in range(self.config.lookback_window, len(data) - self.config.prediction_horizon.value + 1):
            # Features: lookback_window of historical data
            X.append(data.iloc[i-self.config.lookback_window:i].values)
            
            # Target: future values based on prediction horizon
            if self.config.prediction_horizon.value == 1:
                y.append(data.iloc[i, target_col_idx])
            else:
                y.append(data.iloc[i:i+self.config.prediction_horizon.value, target_col_idx].values)
        
        return np.array(X), np.array(y)
    
    def train(self, data: pd.DataFrame) -> ModelPerformance:
        """
        Train the forecasting model
        
        Args:
            data: Training data DataFrame
            
        Returns:
            Model performance metrics
        """
        logger.info(f"Training {self.config.model_type.value} model for {self.config.prediction_horizon.value}-day prediction")
        
        # Preprocess data
        X, y = self.preprocess_data(data)
        
        if len(X) == 0:
            raise ValueError("No training sequences created. Check data length and lookback window.")
        
        # Build model
        self.model = self._build_model()
        
        # Train model
        self._train_model(X, y)
        self.is_trained = True
        
        # Calculate performance metrics
        predictions = self._predict_model(X)
        performance = self._calculate_performance(y, predictions)
        
        logger.info(f"Model training completed. RMSE: {performance.rmse:.4f}, MAE: {performance.mae:.4f}")
        return performance
    
    def predict(self, data: pd.DataFrame, ticker: str) -> PredictionResult:
        """
        Make predictions with the trained model
        
        Args:
            data: Input data for prediction
            ticker: Stock ticker symbol
            
        Returns:
            Prediction result
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Preprocess data
        X, _ = self.preprocess_data(data)
        
        if len(X) == 0:
            raise ValueError("No prediction sequences created from input data")
        
        # Use the last sequence for prediction
        X_pred = X[-1:] if len(X.shape) == 3 else X[-1].reshape(1, -1)
        
        # Make prediction
        predictions = self._predict_model(X_pred)
        
        # Generate prediction dates
        last_date = data.index[-1] if hasattr(data.index, 'date') else datetime.now()
        prediction_dates = [
            last_date + timedelta(days=i+1) 
            for i in range(self.config.prediction_horizon.value)
        ]
        
        # Calculate confidence intervals (model-specific implementation)
        confidence_intervals = self._calculate_confidence_intervals(X_pred, predictions)
        
        # Get feature importance (if supported)
        feature_importance = self._get_feature_importance()
        
        return PredictionResult(
            ticker=ticker,
            model_type=self.config.model_type,
            prediction_horizon=self.config.prediction_horizon,
            predictions=predictions.flatten() if predictions.ndim > 1 else predictions,
            confidence_intervals=confidence_intervals,
            prediction_dates=prediction_dates,
            model_confidence=self._calculate_model_confidence(),
            feature_importance=feature_importance,
            metadata={
                "lookback_window": self.config.lookback_window,
                "features_used": self.feature_columns,
                "scaling_method": self.config.scaling_method
            }
        )
    
    def _calculate_performance(self, y_true: np.ndarray, y_pred: np.ndarray) -> ModelPerformance:
        """Calculate model performance metrics"""
        # Handle multi-dimensional predictions
        if y_true.ndim > 1:
            y_true = y_true.flatten()
        if y_pred.ndim > 1:
            y_pred = y_pred.flatten()
        
        # Ensure same length
        min_len = min(len(y_true), len(y_pred))
        y_true = y_true[:min_len]
        y_pred = y_pred[:min_len]
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mape = mean_absolute_percentage_error(y_true, y_pred) * 100
        
        # Directional accuracy
        if len(y_true) > 1:
            true_direction = np.diff(y_true) > 0
            pred_direction = np.diff(y_pred) > 0
            directional_accuracy = np.mean(true_direction == pred_direction) * 100
        else:
            directional_accuracy = 0.0
        
        # R² score
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2_score = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        
        # Sharpe ratio (simplified)
        returns = np.diff(y_pred) / y_pred[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) != 0 else 0.0
        
        return ModelPerformance(
            mae=mae,
            rmse=rmse,
            mape=mape,
            directional_accuracy=directional_accuracy,
            r2_score=r2_score,
            sharpe_ratio=sharpe_ratio
        )
    
    def _calculate_confidence_intervals(self, X: np.ndarray, predictions: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Calculate confidence intervals (default implementation)"""
        # Simple confidence intervals based on prediction variance
        # Subclasses can override for more sophisticated methods
        std_dev = np.std(predictions) if len(predictions) > 1 else 0.1 * np.mean(predictions)
        lower = predictions - 1.96 * std_dev
        upper = predictions + 1.96 * std_dev
        return (lower, upper)
    
    def _get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance (default implementation)"""
        # Default implementation returns None
        # Subclasses can override for models that support feature importance
        return None
    
    def _calculate_model_confidence(self) -> float:
        """Calculate model confidence score"""
        # Default implementation returns 0.5
        # Subclasses can override with model-specific confidence calculations
        return 0.5
    
    def save_model(self, filepath: str) -> None:
        """Save the trained model to disk"""
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'config': self.config,
            'feature_columns': self.feature_columns,
            'is_trained': self.is_trained
        }
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(model_data, filepath)
        self.model_path = filepath
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """Load a trained model from disk"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        model_data = joblib.load(filepath)
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.config = model_data['config']
        self.feature_columns = model_data['feature_columns']
        self.is_trained = model_data['is_trained']
        self.model_path = filepath
        logger.info(f"Model loaded from {filepath}")


class ForecastingModelFactory:
    """Factory class for creating forecasting models"""
    
    @staticmethod
    def create_model(model_type: ModelType, config: ModelConfig) -> BaseForecastingModel:
        """
        Create a forecasting model instance
        
        Args:
            model_type: Type of model to create
            config: Model configuration
            
        Returns:
            Forecasting model instance
        """
        if model_type == ModelType.LSTM:
            from .lstm_predictor import LSTMPredictor
            return LSTMPredictor(config)
        elif model_type == ModelType.ARIMA:
            from .stock_prediction_models import ARIMAModel
            return ARIMAModel(config)
        elif model_type == ModelType.RANDOM_FOREST:
            from .stock_prediction_models import RandomForestModel
            return RandomForestModel(config)
        elif model_type == ModelType.XGBOOST:
            from .stock_prediction_models import XGBoostModel
            return XGBoostModel(config)
        elif model_type == ModelType.PROPHET:
            from .stock_prediction_models import ProphetModel
            return ProphetModel(config)
        elif model_type == ModelType.ENSEMBLE:
            from .stock_prediction_models import EnsembleModel
            return EnsembleModel(config)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")


class FeastDataLoader:
    """Data loader for Feast feature store integration"""
    
    def __init__(self, feature_store_path: str = "ai_assistant/feature_repo"):
        self.feature_store_path = feature_store_path
        self._feast_store = None
    
    @property
    def feast_store(self):
        """Lazy load Feast store"""
        if self._feast_store is None:
            try:
                from feast import FeatureStore
                self._feast_store = FeatureStore(repo_path=self.feature_store_path)
            except ImportError:
                logger.warning("Feast not available. Using mock data loader.")
                self._feast_store = None
        return self._feast_store
    
    def load_historical_data(
        self, 
        ticker: str, 
        start_date: datetime, 
        end_date: datetime,
        features: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Load historical market data from Feast feature store
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for data
            end_date: End date for data
            features: List of features to load
            
        Returns:
            Historical market data DataFrame
        """
        if self.feast_store is None:
            return self._load_mock_data(ticker, start_date, end_date, features)
        
        try:
            # Define entity DataFrame
            entity_df = pd.DataFrame({
                "ticker": [ticker],
                "event_timestamp": [end_date]
            })
            
            # Get historical features
            feature_service_name = "ai_market_analysis_v1"
            historical_features = self.feast_store.get_historical_features(
                entity_df=entity_df,
                features=[feature_service_name],
                full_feature_names=True
            ).to_df()
            
            # Filter by date range
            historical_features = historical_features[
                (historical_features['event_timestamp'] >= start_date) &
                (historical_features['event_timestamp'] <= end_date)
            ]
            
            return historical_features
            
        except Exception as e:
            logger.warning(f"Failed to load data from Feast: {e}. Using mock data.")
            return self._load_mock_data(ticker, start_date, end_date, features)
    
    def _load_mock_data(
        self, 
        ticker: str, 
        start_date: datetime, 
        end_date: datetime,
        features: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Load mock market data for testing"""
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate synthetic market data
        np.random.seed(42)  # For reproducible results
        n_days = len(date_range)
        
        # Base price with trend and noise
        base_price = 100.0
        trend = np.linspace(0, 20, n_days)
        noise = np.random.normal(0, 2, n_days)
        prices = base_price + trend + noise
        
        # Ensure positive prices
        prices = np.maximum(prices, 1.0)
        
        data = {
            'event_timestamp': date_range,
            'ticker': ticker,
            'closing_price': prices,
            'opening_price': prices * (1 + np.random.normal(0, 0.01, n_days)),
            'daily_high': prices * (1 + np.abs(np.random.normal(0, 0.02, n_days))),
            'daily_low': prices * (1 - np.abs(np.random.normal(0, 0.02, n_days))),
            'daily_volume': np.random.randint(1000000, 10000000, n_days),
            'sma_20': prices,  # Simplified
            'sma_50': prices,  # Simplified
            'rsi_14': np.random.uniform(20, 80, n_days),
            'macd_line': np.random.normal(0, 1, n_days),
            'volatility_20d': np.random.uniform(0.1, 0.5, n_days)
        }
        
        df = pd.DataFrame(data)
        df.set_index('event_timestamp', inplace=True)
        
        # Filter features if specified
        if features:
            available_features = [col for col in features if col in df.columns]
            df = df[['ticker'] + available_features]
        
        return df


# Utility functions
def validate_data_quality(data: pd.DataFrame, required_columns: List[str]) -> Dict[str, Any]:
    """
    Validate data quality for forecasting
    
    Args:
        data: Input data DataFrame
        required_columns: List of required columns
        
    Returns:
        Data quality report
    """
    report = {
        "is_valid": True,
        "issues": [],
        "statistics": {}
    }
    
    # Check required columns
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        report["is_valid"] = False
        report["issues"].append(f"Missing columns: {missing_columns}")
    
    # Check data length
    if len(data) < 100:
        report["issues"].append(f"Insufficient data: {len(data)} rows (minimum 100 recommended)")
    
    # Check for missing values
    missing_values = data.isnull().sum()
    if missing_values.sum() > 0:
        report["issues"].append(f"Missing values found: {missing_values.to_dict()}")
    
    # Calculate basic statistics
    numeric_columns = data.select_dtypes(include=[np.number]).columns
    if len(numeric_columns) > 0:
        report["statistics"] = {
            "mean": data[numeric_columns].mean().to_dict(),
            "std": data[numeric_columns].std().to_dict(),
            "min": data[numeric_columns].min().to_dict(),
            "max": data[numeric_columns].max().to_dict()
        }
    
    return report


def calculate_prediction_metrics(predictions: List[PredictionResult]) -> Dict[str, Any]:
    """
    Calculate aggregate metrics across multiple predictions
    
    Args:
        predictions: List of prediction results
        
    Returns:
        Aggregate metrics
    """
    if not predictions:
        return {}
    
    metrics = {
        "total_predictions": len(predictions),
        "model_types": list(set(p.model_type.value for p in predictions)),
        "average_confidence": np.mean([p.model_confidence for p in predictions]),
        "prediction_horizons": list(set(p.prediction_horizon.value for p in predictions))
    }
    
    return metrics


# Export main classes and functions
__all__ = [
    "ModelType",
    "PredictionHorizon", 
    "ModelConfig",
    "PredictionResult",
    "ModelPerformance",
    "BaseForecastingModel",
    "ForecastingModelFactory",
    "FeastDataLoader",
    "validate_data_quality",
    "calculate_prediction_metrics"
]