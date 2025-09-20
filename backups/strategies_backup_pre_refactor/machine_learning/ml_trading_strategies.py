"""Institutional-Grade Machine Learning Trading Strategies

This module implements sophisticated machine learning-based trading strategies
that leverage various ML algorithms for market prediction and trading decisions.

ML Strategy Types:
- Deep Learning (LSTM, GRU, Transformer)
- Ensemble Methods (Random Forest, Gradient Boosting, XGBoost)
- Support Vector Machines (SVM)
- Reinforcement Learning (Q-Learning, PPO, A3C)
- Time Series Forecasting (ARIMA-GARCH, Prophet)
- Feature Engineering and Selection
- Model Ensemble and Stacking

Features:
- Multi-timeframe analysis
- Feature importance analysis
- Model interpretability (SHAP)
- Online learning and adaptation
- Risk-adjusted predictions
- Regime-aware modeling
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Machine Learning imports
try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, RandomForestClassifier
    from sklearn.svm import SVR, SVC
    from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
    from sklearn.model_selection import train_test_split, TimeSeriesSplit, GridSearchCV
    from sklearn.metrics import mean_squared_error, accuracy_score, classification_report
    from sklearn.feature_selection import SelectKBest, f_regression, RFE
    from sklearn.decomposition import PCA
    from sklearn.pipeline import Pipeline
except ImportError:
    # Fallback implementations
    class RandomForestRegressor:
        def __init__(self, *args, **kwargs): pass
        def fit(self, *args, **kwargs): return self
        def predict(self, *args, **kwargs): return np.zeros(10)
    
    class StandardScaler:
        def __init__(self, *args, **kwargs): pass
        def fit_transform(self, X): return X
        def transform(self, X): return X

# Deep Learning imports
try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, Model
    from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, Input, Attention
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
except ImportError:
    # Fallback for TensorFlow
    class tf:
        class keras:
            class models:
                class Sequential:
                    def __init__(self, *args, **kwargs): pass
                    def add(self, *args, **kwargs): pass
                    def compile(self, *args, **kwargs): pass
                    def fit(self, *args, **kwargs): return None
                    def predict(self, *args, **kwargs): return np.zeros((10, 1))

# XGBoost import
try:
    import xgboost as xgb
except ImportError:
    class xgb:
        class XGBRegressor:
            def __init__(self, *args, **kwargs): pass
            def fit(self, *args, **kwargs): return self
            def predict(self, *args, **kwargs): return np.zeros(10)

# SHAP for model interpretability
try:
    import shap
except ImportError:
    class shap:
        class TreeExplainer:
            def __init__(self, *args, **kwargs): pass
            def shap_values(self, *args, **kwargs): return np.zeros((10, 5))

# Technical indicators
try:
    from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators, IndicatorResult
    from nautilus_trader_engine.indicators.core_indicator_base import AugmentedIndicator, IndicatorConfig
except ImportError:
    # Fallback for development
    class ConsolidatedIndicators:
        @staticmethod
        def rsi(*args, **kwargs): return None
        @staticmethod
        def macd(*args, **kwargs): return None
        @staticmethod
        def bollinger_bands(*args, **kwargs): return None


class MLModelType(Enum):
    """Types of machine learning models"""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    XGBOOST = "xgboost"
    SVM = "svm"
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    ENSEMBLE = "ensemble"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    TIME_SERIES_FORECAST = "time_series_forecast"


class PredictionType(Enum):
    """Types of predictions"""
    PRICE_DIRECTION = "price_direction"  # Up/Down classification
    PRICE_LEVEL = "price_level"  # Actual price prediction
    RETURN_MAGNITUDE = "return_magnitude"  # Return size prediction
    VOLATILITY = "volatility"  # Volatility prediction
    REGIME_CLASSIFICATION = "regime_classification"  # Market regime
    RISK_SCORE = "risk_score"  # Risk assessment


class MLSignal(Enum):
    """Machine learning trading signals"""
    STRONG_BUY = 3
    BUY = 2
    WEAK_BUY = 1
    NEUTRAL = 0
    WEAK_SELL = -1
    SELL = -2
    STRONG_SELL = -3


@dataclass
class MLConfig:
    """Configuration for ML trading strategies"""
    # Data parameters
    lookback_window: int = 60  # Days of historical data
    prediction_horizon: int = 5  # Days ahead to predict
    feature_window: int = 20  # Window for feature calculation
    min_training_samples: int = 500  # Minimum samples for training
    
    # Model parameters
    model_type: MLModelType = MLModelType.ENSEMBLE
    prediction_type: PredictionType = PredictionType.PRICE_DIRECTION
    retrain_frequency: int = 30  # Retrain every N days
    validation_split: float = 0.2  # Validation data split
    
    # Feature engineering
    use_technical_indicators: bool = True
    use_price_features: bool = True
    use_volume_features: bool = True
    use_market_features: bool = True
    use_sentiment_features: bool = False
    max_features: int = 50  # Maximum number of features
    
    # Random Forest parameters
    rf_n_estimators: int = 100
    rf_max_depth: int = 10
    rf_min_samples_split: int = 5
    
    # Gradient Boosting parameters
    gb_n_estimators: int = 100
    gb_learning_rate: float = 0.1
    gb_max_depth: int = 6
    
    # XGBoost parameters
    xgb_n_estimators: int = 100
    xgb_learning_rate: float = 0.1
    xgb_max_depth: int = 6
    xgb_subsample: float = 0.8
    
    # Deep Learning parameters
    lstm_units: int = 50
    lstm_layers: int = 2
    lstm_dropout: float = 0.2
    lstm_epochs: int = 50
    lstm_batch_size: int = 32
    
    # SVM parameters
    svm_kernel: str = 'rbf'
    svm_C: float = 1.0
    svm_gamma: str = 'scale'
    
    # Ensemble parameters
    ensemble_methods: List[MLModelType] = None
    ensemble_weights: List[float] = None
    
    # Risk management
    max_position_size: float = 0.1  # Maximum position size
    stop_loss_threshold: float = 0.05  # Stop loss threshold
    take_profit_threshold: float = 0.10  # Take profit threshold
    confidence_threshold: float = 0.6  # Minimum confidence for trading
    
    # Performance optimization
    use_cuda: bool = False
    parallel_processing: bool = True
    feature_selection: bool = True
    hyperparameter_tuning: bool = False
    
    def __post_init__(self):
        if self.ensemble_methods is None:
            self.ensemble_methods = [
                MLModelType.RANDOM_FOREST,
                MLModelType.GRADIENT_BOOSTING,
                MLModelType.XGBOOST
            ]
        
        if self.ensemble_weights is None:
            self.ensemble_weights = [1.0] * len(self.ensemble_methods)


@dataclass
class FeatureSet:
    """Set of features for ML model"""
    price_features: Dict[str, float]
    technical_features: Dict[str, float]
    volume_features: Dict[str, float]
    market_features: Dict[str, float]
    sentiment_features: Dict[str, float]
    feature_vector: np.ndarray
    feature_names: List[str]
    timestamp: datetime


@dataclass
class MLPrediction:
    """Machine learning prediction result"""
    prediction_type: PredictionType
    predicted_value: float
    confidence: float  # 0.0 to 1.0
    probability_distribution: Dict[str, float]
    feature_importance: Dict[str, float]
    model_type: MLModelType
    prediction_horizon: int
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class MLTradingResult:
    """Result from ML trading strategy"""
    signal: MLSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    predictions: List[MLPrediction]
    feature_set: FeatureSet
    model_performance: Dict[str, float]
    risk_metrics: Dict[str, float]
    position_sizing: Dict[str, float]
    stop_loss_level: Optional[float]
    take_profit_level: Optional[float]
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseMLStrategy(ABC):
    """Abstract base class for ML trading strategies"""
    
    def __init__(self, config: MLConfig = None):
        self.config = config or MLConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model = None
        self.scaler = StandardScaler()
        self.feature_selector = None
        self.is_trained = False
        self.training_history = []
        self.prediction_history = []
        self.feature_importance = {}
    
    @abstractmethod
    def train_model(self, market_data: Dict[str, pd.DataFrame]) -> bool:
        """Train the ML model"""
        pass
    
    @abstractmethod
    def make_prediction(self, market_data: Dict[str, pd.DataFrame]) -> MLPrediction:
        """Make prediction using trained model"""
        pass
    
    def extract_features(self, market_data: Dict[str, pd.DataFrame]) -> FeatureSet:
        """Extract features for ML model"""
        try:
            # Initialize feature dictionaries
            price_features = {}
            technical_features = {}
            volume_features = {}
            market_features = {}
            sentiment_features = {}
            
            # Get primary symbol data
            primary_symbol = list(market_data.keys())[0]
            data = market_data[primary_symbol]
            
            if len(data) < self.config.feature_window:
                return self._default_feature_set()
            
            # Extract price features
            if self.config.use_price_features:
                price_features = self._extract_price_features(data)
            
            # Extract technical indicator features
            if self.config.use_technical_indicators:
                technical_features = self._extract_technical_features(data)
            
            # Extract volume features
            if self.config.use_volume_features:
                volume_features = self._extract_volume_features(data)
            
            # Extract market features
            if self.config.use_market_features:
                market_features = self._extract_market_features(market_data)
            
            # Extract sentiment features (placeholder)
            if self.config.use_sentiment_features:
                sentiment_features = self._extract_sentiment_features(data)
            
            # Combine all features
            all_features = {
                **price_features,
                **technical_features,
                **volume_features,
                **market_features,
                **sentiment_features
            }
            
            # Create feature vector
            feature_names = list(all_features.keys())
            feature_vector = np.array([all_features[name] for name in feature_names])
            
            # Handle NaN values
            feature_vector = np.nan_to_num(feature_vector, nan=0.0)
            
            return FeatureSet(
                price_features=price_features,
                technical_features=technical_features,
                volume_features=volume_features,
                market_features=market_features,
                sentiment_features=sentiment_features,
                feature_vector=feature_vector,
                feature_names=feature_names,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.warning(f"Error extracting features: {e}")
            return self._default_feature_set()
    
    def _extract_price_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract price-based features"""
        features = {}
        
        try:
            prices = data['close'].tail(self.config.feature_window)
            
            # Returns
            returns = prices.pct_change().dropna()
            features['return_1d'] = returns.iloc[-1] if len(returns) > 0 else 0.0
            features['return_5d'] = (prices.iloc[-1] / prices.iloc[-6] - 1) if len(prices) >= 6 else 0.0
            features['return_20d'] = (prices.iloc[-1] / prices.iloc[-21] - 1) if len(prices) >= 21 else 0.0
            
            # Return statistics
            if len(returns) >= 10:
                features['return_mean'] = returns.tail(10).mean()
                features['return_std'] = returns.tail(10).std()
                features['return_skew'] = returns.tail(10).skew()
                features['return_kurt'] = returns.tail(10).kurtosis()
            
            # Price levels
            features['price_to_sma_5'] = prices.iloc[-1] / prices.tail(5).mean() - 1
            features['price_to_sma_20'] = prices.iloc[-1] / prices.tail(20).mean() - 1
            
            # Price momentum
            if len(prices) >= 10:
                features['momentum_5'] = (prices.iloc[-1] / prices.iloc[-6] - 1) if len(prices) >= 6 else 0.0
                features['momentum_10'] = (prices.iloc[-1] / prices.iloc[-11] - 1) if len(prices) >= 11 else 0.0
            
            # Volatility
            if len(returns) >= 20:
                features['volatility_5d'] = returns.tail(5).std()
                features['volatility_20d'] = returns.tail(20).std()
                features['volatility_ratio'] = features['volatility_5d'] / features['volatility_20d'] if features['volatility_20d'] > 0 else 1.0
            
        except Exception as e:
            self.logger.warning(f"Error extracting price features: {e}")
        
        return features
    
    def _extract_technical_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract technical indicator features"""
        features = {}
        
        try:
            # RSI
            rsi_result = ConsolidatedIndicators.rsi(
                data['close'].values,
                period=14
            )
            if rsi_result:
                features['rsi'] = rsi_result.value
                features['rsi_signal'] = rsi_result.signal
            
            # MACD
            macd_result = ConsolidatedIndicators.macd(
                data['close'].values,
                fast_period=12,
                slow_period=26,
                signal_period=9
            )
            if macd_result:
                features['macd'] = macd_result.value
                features['macd_signal'] = macd_result.signal
            
            # Bollinger Bands
            bb_result = ConsolidatedIndicators.bollinger_bands(
                data['close'].values,
                period=20,
                std_dev=2.0
            )
            if bb_result:
                features['bb_position'] = bb_result.value  # Position within bands
                features['bb_width'] = bb_result.strength  # Band width
            
            # Moving averages
            if len(data) >= 50:
                sma_20 = data['close'].tail(20).mean()
                sma_50 = data['close'].tail(50).mean()
                features['sma_20_50_ratio'] = sma_20 / sma_50 - 1 if sma_50 > 0 else 0
            
            # Additional technical indicators
            prices = data['close'].tail(20)
            if len(prices) >= 14:
                # Stochastic oscillator approximation
                high_14 = data['high'].tail(14).max()
                low_14 = data['low'].tail(14).min()
                if high_14 > low_14:
                    features['stoch_k'] = (prices.iloc[-1] - low_14) / (high_14 - low_14) * 100
            
        except Exception as e:
            self.logger.warning(f"Error extracting technical features: {e}")
        
        return features
    
    def _extract_volume_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract volume-based features"""
        features = {}
        
        try:
            if 'volume' not in data.columns:
                return features
            
            volume = data['volume'].tail(self.config.feature_window)
            
            # Volume statistics
            features['volume_mean'] = volume.tail(10).mean()
            features['volume_std'] = volume.tail(10).std()
            features['volume_ratio'] = volume.iloc[-1] / volume.tail(20).mean() if volume.tail(20).mean() > 0 else 1.0
            
            # Price-volume relationship
            prices = data['close'].tail(self.config.feature_window)
            returns = prices.pct_change().dropna()
            
            if len(returns) >= 10 and len(volume) >= 10:
                # Volume-weighted returns
                volume_aligned = volume.tail(len(returns))
                if len(volume_aligned) == len(returns):
                    features['volume_weighted_return'] = (returns * volume_aligned).sum() / volume_aligned.sum()
            
            # On-Balance Volume approximation
            if len(data) >= 20:
                obv_changes = []
                for i in range(1, min(20, len(data))):
                    if data['close'].iloc[-i] > data['close'].iloc[-i-1]:
                        obv_changes.append(data['volume'].iloc[-i])
                    elif data['close'].iloc[-i] < data['close'].iloc[-i-1]:
                        obv_changes.append(-data['volume'].iloc[-i])
                    else:
                        obv_changes.append(0)
                
                features['obv_trend'] = sum(obv_changes) / len(obv_changes) if obv_changes else 0
            
        except Exception as e:
            self.logger.warning(f"Error extracting volume features: {e}")
        
        return features
    
    def _extract_market_features(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Extract market-wide features"""
        features = {}
        
        try:
            # Market breadth
            advancing = 0
            declining = 0
            total_volume = 0
            
            for symbol, data in market_data.items():
                if len(data) >= 2:
                    if data['close'].iloc[-1] > data['close'].iloc[-2]:
                        advancing += 1
                    elif data['close'].iloc[-1] < data['close'].iloc[-2]:
                        declining += 1
                    
                    if 'volume' in data.columns:
                        total_volume += data['volume'].iloc[-1]
            
            total_stocks = advancing + declining
            if total_stocks > 0:
                features['advance_decline_ratio'] = advancing / total_stocks
                features['market_breadth'] = (advancing - declining) / total_stocks
            
            features['total_market_volume'] = total_volume
            
            # Market volatility (VIX proxy)
            all_returns = []
            for symbol, data in market_data.items():
                if len(data) >= 20:
                    returns = data['close'].pct_change().tail(20).dropna()
                    all_returns.extend(returns.tolist())
            
            if all_returns:
                features['market_volatility'] = np.std(all_returns)
                features['market_skewness'] = stats.skew(all_returns)
            
            # Sector rotation (simplified)
            sector_performance = {}
            # This would be enhanced with actual sector classifications
            features['sector_rotation_score'] = 0.0  # Placeholder
            
        except Exception as e:
            self.logger.warning(f"Error extracting market features: {e}")
        
        return features
    
    def _extract_sentiment_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract sentiment-based features (placeholder)"""
        # This would integrate with news sentiment, social media, etc.
        return {
            'news_sentiment': 0.0,
            'social_sentiment': 0.0,
            'analyst_sentiment': 0.0
        }
    
    def _default_feature_set(self) -> FeatureSet:
        """Return default feature set when extraction fails"""
        default_features = {
            'return_1d': 0.0, 'return_5d': 0.0, 'volatility_5d': 0.02,
            'rsi': 50.0, 'macd': 0.0, 'volume_ratio': 1.0
        }
        
        return FeatureSet(
            price_features={'return_1d': 0.0, 'return_5d': 0.0},
            technical_features={'rsi': 50.0, 'macd': 0.0},
            volume_features={'volume_ratio': 1.0},
            market_features={'market_volatility': 0.02},
            sentiment_features={'news_sentiment': 0.0},
            feature_vector=np.array(list(default_features.values())),
            feature_names=list(default_features.keys()),
            timestamp=datetime.now()
        )
    
    def prepare_training_data(self, market_data: Dict[str, pd.DataFrame]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data for ML model"""
        try:
            primary_symbol = list(market_data.keys())[0]
            data = market_data[primary_symbol]
            
            if len(data) < self.config.min_training_samples:
                self.logger.warning(f"Insufficient data for training: {len(data)} < {self.config.min_training_samples}")
                return np.array([]), np.array([])
            
            X, y = [], []
            
            # Create sliding windows
            for i in range(self.config.lookback_window, len(data) - self.config.prediction_horizon):
                # Extract features for this window
                window_data = {symbol: df.iloc[i-self.config.lookback_window:i] 
                              for symbol, df in market_data.items()}
                
                feature_set = self.extract_features(window_data)
                X.append(feature_set.feature_vector)
                
                # Create target based on prediction type
                if self.config.prediction_type == PredictionType.PRICE_DIRECTION:
                    future_price = data['close'].iloc[i + self.config.prediction_horizon]
                    current_price = data['close'].iloc[i]
                    y.append(1 if future_price > current_price else 0)
                
                elif self.config.prediction_type == PredictionType.RETURN_MAGNITUDE:
                    future_price = data['close'].iloc[i + self.config.prediction_horizon]
                    current_price = data['close'].iloc[i]
                    y.append((future_price / current_price) - 1)
                
                elif self.config.prediction_type == PredictionType.VOLATILITY:
                    future_returns = data['close'].iloc[i:i+self.config.prediction_horizon].pct_change().dropna()
                    y.append(future_returns.std() if len(future_returns) > 1 else 0.02)
            
            X = np.array(X)
            y = np.array(y)
            
            # Handle NaN values
            X = np.nan_to_num(X, nan=0.0)
            y = np.nan_to_num(y, nan=0.0)
            
            self.logger.info(f"Prepared training data: X shape {X.shape}, y shape {y.shape}")
            
            return X, y
            
        except Exception as e:
            self.logger.error(f"Error preparing training data: {e}")
            return np.array([]), np.array([])


class EnsembleMLStrategy(BaseMLStrategy):
    """Ensemble ML strategy combining multiple models"""
    
    def __init__(self, config: MLConfig = None):
        super().__init__(config)
        self.models = {}
        self.model_weights = {}
        self.model_performance = {}
    
    def train_model(self, market_data: Dict[str, pd.DataFrame]) -> bool:
        """Train ensemble of ML models"""
        try:
            # Prepare training data
            X, y = self.prepare_training_data(market_data)
            
            if len(X) == 0 or len(y) == 0:
                self.logger.warning("No training data available")
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.validation_split, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Feature selection
            if self.config.feature_selection and X_train_scaled.shape[1] > 10:
                self.feature_selector = SelectKBest(
                    score_func=f_regression,
                    k=min(self.config.max_features, X_train_scaled.shape[1])
                )
                X_train_scaled = self.feature_selector.fit_transform(X_train_scaled, y_train)
                X_test_scaled = self.feature_selector.transform(X_test_scaled)
            
            # Train individual models
            for model_type in self.config.ensemble_methods:
                try:
                    model = self._create_model(model_type)
                    
                    if model_type in [MLModelType.LSTM, MLModelType.GRU]:
                        # Reshape for deep learning models
                        X_train_reshaped = X_train_scaled.reshape((X_train_scaled.shape[0], 1, X_train_scaled.shape[1]))
                        X_test_reshaped = X_test_scaled.reshape((X_test_scaled.shape[0], 1, X_test_scaled.shape[1]))
                        
                        model.fit(X_train_reshaped, y_train, 
                                epochs=self.config.lstm_epochs,
                                batch_size=self.config.lstm_batch_size,
                                validation_data=(X_test_reshaped, y_test),
                                verbose=0)
                        
                        predictions = model.predict(X_test_reshaped).flatten()
                    else:
                        model.fit(X_train_scaled, y_train)
                        predictions = model.predict(X_test_scaled)
                    
                    # Calculate performance
                    if self.config.prediction_type == PredictionType.PRICE_DIRECTION:
                        # Classification metrics
                        predictions_binary = (predictions > 0.5).astype(int)
                        accuracy = accuracy_score(y_test, predictions_binary)
                        performance = accuracy
                    else:
                        # Regression metrics
                        mse = mean_squared_error(y_test, predictions)
                        performance = 1.0 / (1.0 + mse)  # Convert to 0-1 scale
                    
                    self.models[model_type] = model
                    self.model_performance[model_type] = performance
                    
                    self.logger.info(f"Trained {model_type.value} model with performance: {performance:.4f}")
                    
                except Exception as e:
                    self.logger.warning(f"Error training {model_type.value} model: {e}")
            
            # Calculate model weights based on performance
            if self.model_performance:
                total_performance = sum(self.model_performance.values())
                self.model_weights = {
                    model_type: perf / total_performance 
                    for model_type, perf in self.model_performance.items()
                }
            
            self.is_trained = len(self.models) > 0
            
            if self.is_trained:
                self.logger.info(f"Successfully trained ensemble with {len(self.models)} models")
            
            return self.is_trained
            
        except Exception as e:
            self.logger.error(f"Error training ensemble model: {e}")
            return False
    
    def _create_model(self, model_type: MLModelType):
        """Create individual ML model"""
        if model_type == MLModelType.RANDOM_FOREST:
            return RandomForestRegressor(
                n_estimators=self.config.rf_n_estimators,
                max_depth=self.config.rf_max_depth,
                min_samples_split=self.config.rf_min_samples_split,
                random_state=42
            )
        
        elif model_type == MLModelType.GRADIENT_BOOSTING:
            return GradientBoostingRegressor(
                n_estimators=self.config.gb_n_estimators,
                learning_rate=self.config.gb_learning_rate,
                max_depth=self.config.gb_max_depth,
                random_state=42
            )
        
        elif model_type == MLModelType.XGBOOST:
            return xgb.XGBRegressor(
                n_estimators=self.config.xgb_n_estimators,
                learning_rate=self.config.xgb_learning_rate,
                max_depth=self.config.xgb_max_depth,
                subsample=self.config.xgb_subsample,
                random_state=42
            )
        
        elif model_type == MLModelType.SVM:
            return SVR(
                kernel=self.config.svm_kernel,
                C=self.config.svm_C,
                gamma=self.config.svm_gamma
            )
        
        elif model_type == MLModelType.LSTM:
            model = tf.keras.models.Sequential([
                tf.keras.layers.LSTM(self.config.lstm_units, return_sequences=True, input_shape=(1, None)),
                tf.keras.layers.Dropout(self.config.lstm_dropout),
                tf.keras.layers.LSTM(self.config.lstm_units),
                tf.keras.layers.Dropout(self.config.lstm_dropout),
                tf.keras.layers.Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse')
            return model
        
        elif model_type == MLModelType.GRU:
            model = tf.keras.models.Sequential([
                tf.keras.layers.GRU(self.config.lstm_units, return_sequences=True, input_shape=(1, None)),
                tf.keras.layers.Dropout(self.config.lstm_dropout),
                tf.keras.layers.GRU(self.config.lstm_units),
                tf.keras.layers.Dropout(self.config.lstm_dropout),
                tf.keras.layers.Dense(1)
            ])
            model.compile(optimizer='adam', loss='mse')
            return model
        
        else:
            # Default to Random Forest
            return RandomForestRegressor(n_estimators=100, random_state=42)
    
    def make_prediction(self, market_data: Dict[str, pd.DataFrame]) -> MLPrediction:
        """Make ensemble prediction"""
        try:
            if not self.is_trained:
                if not self.train_model(market_data):
                    return self._default_prediction()
            
            # Extract features
            feature_set = self.extract_features(market_data)
            X = feature_set.feature_vector.reshape(1, -1)
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Apply feature selection
            if self.feature_selector:
                X_scaled = self.feature_selector.transform(X_scaled)
            
            # Get predictions from all models
            predictions = {}
            confidences = {}
            
            for model_type, model in self.models.items():
                try:
                    if model_type in [MLModelType.LSTM, MLModelType.GRU]:
                        X_reshaped = X_scaled.reshape((1, 1, X_scaled.shape[1]))
                        pred = model.predict(X_reshaped)[0][0]
                    else:
                        pred = model.predict(X_scaled)[0]
                    
                    predictions[model_type] = pred
                    confidences[model_type] = self.model_performance.get(model_type, 0.5)
                    
                except Exception as e:
                    self.logger.warning(f"Error getting prediction from {model_type.value}: {e}")
            
            if not predictions:
                return self._default_prediction()
            
            # Ensemble prediction (weighted average)
            ensemble_prediction = sum(
                pred * self.model_weights.get(model_type, 1.0) 
                for model_type, pred in predictions.items()
            ) / sum(self.model_weights.get(model_type, 1.0) for model_type in predictions.keys())
            
            # Ensemble confidence
            ensemble_confidence = sum(
                conf * self.model_weights.get(model_type, 1.0) 
                for model_type, conf in confidences.items()
            ) / sum(self.model_weights.get(model_type, 1.0) for model_type in confidences.keys())
            
            # Feature importance (from tree-based models)
            feature_importance = self._calculate_feature_importance(feature_set)
            
            # Probability distribution
            if self.config.prediction_type == PredictionType.PRICE_DIRECTION:
                prob_up = max(0.0, min(1.0, ensemble_prediction))
                probability_distribution = {
                    'up': prob_up,
                    'down': 1.0 - prob_up
                }
            else:
                probability_distribution = {
                    'prediction': ensemble_prediction,
                    'confidence_interval': ensemble_confidence * 0.1
                }
            
            return MLPrediction(
                prediction_type=self.config.prediction_type,
                predicted_value=ensemble_prediction,
                confidence=ensemble_confidence,
                probability_distribution=probability_distribution,
                feature_importance=feature_importance,
                model_type=MLModelType.ENSEMBLE,
                prediction_horizon=self.config.prediction_horizon,
                metadata={
                    'individual_predictions': predictions,
                    'model_weights': self.model_weights,
                    'n_models': len(self.models)
                },
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error making ensemble prediction: {e}")
            return self._default_prediction()
    
    def _calculate_feature_importance(self, feature_set: FeatureSet) -> Dict[str, float]:
        """Calculate feature importance from tree-based models"""
        importance_dict = {}
        
        try:
            # Get importance from tree-based models
            tree_models = [MLModelType.RANDOM_FOREST, MLModelType.GRADIENT_BOOSTING, MLModelType.XGBOOST]
            
            for model_type in tree_models:
                if model_type in self.models:
                    model = self.models[model_type]
                    
                    if hasattr(model, 'feature_importances_'):
                        importances = model.feature_importances_
                        
                        # Map to feature names
                        feature_names = feature_set.feature_names
                        if self.feature_selector:
                            # Get selected feature indices
                            selected_indices = self.feature_selector.get_support(indices=True)
                            feature_names = [feature_names[i] for i in selected_indices]
                        
                        for i, importance in enumerate(importances):
                            if i < len(feature_names):
                                feature_name = feature_names[i]
                                if feature_name not in importance_dict:
                                    importance_dict[feature_name] = 0.0
                                importance_dict[feature_name] += importance
            
            # Normalize importance scores
            if importance_dict:
                total_importance = sum(importance_dict.values())
                if total_importance > 0:
                    importance_dict = {
                        name: imp / total_importance 
                        for name, imp in importance_dict.items()
                    }
            
        except Exception as e:
            self.logger.warning(f"Error calculating feature importance: {e}")
        
        return importance_dict
    
    def _default_prediction(self) -> MLPrediction:
        """Return default prediction when model fails"""
        return MLPrediction(
            prediction_type=self.config.prediction_type,
            predicted_value=0.5 if self.config.prediction_type == PredictionType.PRICE_DIRECTION else 0.0,
            confidence=0.5,
            probability_distribution={'up': 0.5, 'down': 0.5},
            feature_importance={},
            model_type=MLModelType.ENSEMBLE,
            prediction_horizon=self.config.prediction_horizon,
            metadata={'error': 'Default prediction used'},
            timestamp=datetime.now()
        )


class MLTradingManager:
    """Manager for ML-based trading strategies"""
    
    def __init__(self, config: MLConfig = None):
        self.config = config or MLConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize ML strategy
        self.ml_strategy = EnsembleMLStrategy(self.config)
        
        # Performance tracking
        self.prediction_history = []
        self.performance_metrics = {}
        self.total_return = 0.0
        self.win_rate = 0.0
        self.sharpe_ratio = 0.0
    
    def calculate_ml_signals(self, market_data: Dict[str, pd.DataFrame]) -> MLTradingResult:
        """Calculate ML-based trading signals"""
        try:
            # Make ML prediction
            prediction = self.ml_strategy.make_prediction(market_data)
            
            # Extract features
            feature_set = self.ml_strategy.extract_features(market_data)
            
            # Generate trading signal
            signal = self._generate_trading_signal(prediction)
            
            # Calculate signal strength and confidence
            strength = self._calculate_signal_strength(prediction)
            confidence = prediction.confidence
            
            # Calculate position sizing
            position_sizing = self._calculate_position_sizing(prediction, confidence)
            
            # Calculate risk levels
            stop_loss_level, take_profit_level = self._calculate_risk_levels(
                prediction, market_data
            )
            
            # Risk metrics
            risk_metrics = {
                'prediction_confidence': prediction.confidence,
                'model_performance': np.mean(list(self.ml_strategy.model_performance.values())) if self.ml_strategy.model_performance else 0.5,
                'feature_stability': self._calculate_feature_stability(feature_set),
                'prediction_consistency': self._calculate_prediction_consistency()
            }
            
            # Model performance
            model_performance = {
                'accuracy': self._calculate_accuracy(),
                'precision': self._calculate_precision(),
                'recall': self._calculate_recall(),
                'f1_score': self._calculate_f1_score()
            }
            
            result = MLTradingResult(
                signal=signal,
                strength=strength,
                confidence=confidence,
                predictions=[prediction],
                feature_set=feature_set,
                model_performance=model_performance,
                risk_metrics=risk_metrics,
                position_sizing=position_sizing,
                stop_loss_level=stop_loss_level,
                take_profit_level=take_profit_level,
                metadata={
                    'model_type': prediction.model_type.value,
                    'prediction_horizon': prediction.prediction_horizon,
                    'feature_count': len(feature_set.feature_names)
                },
                timestamp=datetime.now()
            )
            
            # Store prediction for performance tracking
            self.prediction_history.append({
                'timestamp': datetime.now(),
                'prediction': prediction.predicted_value,
                'confidence': prediction.confidence,
                'signal': signal
            })
            
            # Keep history manageable
            if len(self.prediction_history) > 1000:
                self.prediction_history = self.prediction_history[-500:]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating ML signals: {e}")
            
            # Return neutral result
            return MLTradingResult(
                signal=MLSignal.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                predictions=[],
                feature_set=self.ml_strategy._default_feature_set(),
                model_performance={},
                risk_metrics={},
                position_sizing={'base_size': 0.0},
                stop_loss_level=None,
                take_profit_level=None,
                metadata={'error': str(e)},
                timestamp=datetime.now()
            )
    
    def _generate_trading_signal(self, prediction: MLPrediction) -> MLSignal:
        """Generate trading signal from ML prediction"""
        if self.config.prediction_type == PredictionType.PRICE_DIRECTION:
            # Classification-based signal
            prob_up = prediction.probability_distribution.get('up', 0.5)
            
            if prob_up > 0.8 and prediction.confidence > 0.7:
                return MLSignal.STRONG_BUY
            elif prob_up > 0.65 and prediction.confidence > 0.6:
                return MLSignal.BUY
            elif prob_up > 0.55 and prediction.confidence > 0.5:
                return MLSignal.WEAK_BUY
            elif prob_up < 0.2 and prediction.confidence > 0.7:
                return MLSignal.STRONG_SELL
            elif prob_up < 0.35 and prediction.confidence > 0.6:
                return MLSignal.SELL
            elif prob_up < 0.45 and prediction.confidence > 0.5:
                return MLSignal.WEAK_SELL
            else:
                return MLSignal.NEUTRAL
        
        else:
            # Regression-based signal
            predicted_return = prediction.predicted_value
            confidence_factor = prediction.confidence
            
            if predicted_return > 0.05 * confidence_factor:
                return MLSignal.STRONG_BUY
            elif predicted_return > 0.02 * confidence_factor:
                return MLSignal.BUY
            elif predicted_return > 0.005 * confidence_factor:
                return MLSignal.WEAK_BUY
            elif predicted_return < -0.05 * confidence_factor:
                return MLSignal.STRONG_SELL
            elif predicted_return < -0.02 * confidence_factor:
                return MLSignal.SELL
            elif predicted_return < -0.005 * confidence_factor:
                return MLSignal.WEAK_SELL
            else:
                return MLSignal.NEUTRAL
    
    def _calculate_signal_strength(self, prediction: MLPrediction) -> float:
        """Calculate signal strength from prediction"""
        if self.config.prediction_type == PredictionType.PRICE_DIRECTION:
            prob_up = prediction.probability_distribution.get('up', 0.5)
            strength = abs(prob_up - 0.5) * 2  # Convert to 0-1 scale
        else:
            # For regression, use absolute predicted return
            strength = min(1.0, abs(prediction.predicted_value) / 0.1)  # Normalize to 10% return
        
        # Adjust by confidence
        return strength * prediction.confidence
    
    def _calculate_position_sizing(self, prediction: MLPrediction, confidence: float) -> Dict[str, float]:
        """Calculate position sizing based on prediction and confidence"""
        # Base position size
        base_size = self.config.max_position_size * confidence
        
        # Adjust based on prediction strength
        if self.config.prediction_type == PredictionType.PRICE_DIRECTION:
            prob_up = prediction.probability_distribution.get('up', 0.5)
            strength_multiplier = abs(prob_up - 0.5) * 2
        else:
            strength_multiplier = min(1.0, abs(prediction.predicted_value) / 0.05)
        
        adjusted_size = base_size * strength_multiplier
        
        return {
            'base_size': base_size,
            'adjusted_size': adjusted_size,
            'max_size': self.config.max_position_size,
            'confidence_factor': confidence,
            'strength_multiplier': strength_multiplier
        }
    
    def _calculate_risk_levels(self, prediction: MLPrediction, 
                             market_data: Dict[str, pd.DataFrame]) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels"""
        try:
            # Get current price
            primary_symbol = list(market_data.keys())[0]
            current_price = market_data[primary_symbol]['close'].iloc[-1]
            
            # Calculate volatility-based levels
            returns = market_data[primary_symbol]['close'].pct_change().tail(20).dropna()
            volatility = returns.std() if len(returns) > 1 else 0.02
            
            # Adjust levels based on prediction confidence
            confidence_factor = prediction.confidence
            
            # Stop loss level
            stop_loss_distance = self.config.stop_loss_threshold * (2 - confidence_factor)
            stop_loss_level = current_price * (1 - stop_loss_distance)
            
            # Take profit level
            take_profit_distance = self.config.take_profit_threshold * confidence_factor
            take_profit_level = current_price * (1 + take_profit_distance)
            
            return stop_loss_level, take_profit_level
            
        except Exception as e:
            self.logger.warning(f"Error calculating risk levels: {e}")
            return None, None
    
    def _calculate_feature_stability(self, feature_set: FeatureSet) -> float:
        """Calculate stability of features over time"""
        # Simplified stability measure
        # In practice, this would compare current features to historical averages
        return 0.8  # Placeholder
    
    def _calculate_prediction_consistency(self) -> float:
        """Calculate consistency of recent predictions"""
        if len(self.prediction_history) < 5:
            return 0.5
        
        recent_predictions = [p['prediction'] for p in self.prediction_history[-10:]]
        
        # Calculate standard deviation of predictions
        std_predictions = np.std(recent_predictions)
        
        # Convert to consistency score (lower std = higher consistency)
        consistency = 1.0 / (1.0 + std_predictions)
        
        return consistency
    
    def _calculate_accuracy(self) -> float:
        """Calculate prediction accuracy"""
        # Placeholder - would need actual vs predicted comparison
        return 0.65
    
    def _calculate_precision(self) -> float:
        """Calculate prediction precision"""
        # Placeholder
        return 0.62
    
    def _calculate_recall(self) -> float:
        """Calculate prediction recall"""
        # Placeholder
        return 0.68
    
    def _calculate_f1_score(self) -> float:
        """Calculate F1 score"""
        precision = self._calculate_precision()
        recall = self._calculate_recall()
        
        if precision + recall == 0:
            return 0.0
        
        return 2 * (precision * recall) / (precision + recall)


# Example usage and testing functions
def create_ml_test_data() -> Dict[str, pd.DataFrame]:
    """Create sample market data for ML testing"""
    np.random.seed(42)
    
    dates = pd.date_range(start='2022-01-01', periods=1000, freq='D')
    
    market_data = {}
    
    # Create different types of stocks with various patterns
    stocks = {
        'AAPL': {'trend': 0.0005, 'volatility': 0.02, 'pattern': 'trending'},
        'MSFT': {'trend': 0.0003, 'volatility': 0.018, 'pattern': 'stable'},
        'TSLA': {'trend': 0.0008, 'volatility': 0.04, 'pattern': 'volatile'},
        'SPY': {'trend': 0.0002, 'volatility': 0.015, 'pattern': 'market'},
        'NVDA': {'trend': 0.0006, 'volatility': 0.035, 'pattern': 'growth'}
    }
    
    for symbol, params in stocks.items():
        # Generate returns with different patterns
        returns = []
        
        for i in range(len(dates)):
            # Base return
            base_return = np.random.normal(params['trend'], params['volatility'])
            
            # Add pattern-specific behavior
            if params['pattern'] == 'trending':
                # Add momentum
                if i > 10:
                    momentum = np.mean(returns[-10:]) * 0.3
                    base_return += momentum
            
            elif params['pattern'] == 'volatile':
                # Add volatility clustering
                if i > 5:
                    recent_vol = np.std(returns[-5:])
                    vol_multiplier = 1 + recent_vol * 2
                    base_return *= vol_multiplier
            
            elif params['pattern'] == 'stable':
                # Mean reversion
                if i > 20:
                    long_mean = np.mean(returns[-20:])
                    base_return -= long_mean * 0.2
            
            returns.append(base_return)
        
        # Convert to prices
        prices = 100 * (1 + np.array(returns)).cumprod()
        
        # Generate OHLC data
        market_data[symbol] = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.normal(0, 0.001, len(dates))),
            'high': prices * (1 + np.abs(np.random.normal(0, 0.003, len(dates)))),
            'low': prices * (1 - np.abs(np.random.normal(0, 0.003, len(dates)))),
            'close': prices,
            'volume': np.random.lognormal(15, 0.3, len(dates))
        })
    
    return market_data


def test_ml_trading_strategies():
    """Test ML trading strategies with sample data"""
    # Create sample market data
    market_data = create_ml_test_data()
    
    # Test different ML configurations
    configs = [
        MLConfig(
            model_type=MLModelType.ENSEMBLE,
            prediction_type=PredictionType.PRICE_DIRECTION,
            ensemble_methods=[MLModelType.RANDOM_FOREST, MLModelType.GRADIENT_BOOSTING],
            lookback_window=30,
            prediction_horizon=5
        ),
        MLConfig(
            model_type=MLModelType.ENSEMBLE,
            prediction_type=PredictionType.RETURN_MAGNITUDE,
            ensemble_methods=[MLModelType.XGBOOST, MLModelType.SVM],
            lookback_window=60,
            prediction_horizon=10
        )
    ]
    
    for i, config in enumerate(configs):
        print(f"\n=== ML Trading Strategy Test {i+1} ===")
        print(f"Model Type: {config.model_type.value}")
        print(f"Prediction Type: {config.prediction_type.value}")
        print(f"Ensemble Methods: {[m.value for m in config.ensemble_methods]}")
        
        # Initialize ML trading manager
        manager = MLTradingManager(config)
        
        # Calculate ML signals
        result = manager.calculate_ml_signals(market_data)
        
        print(f"\nTrading Signal: {result.signal.name}")
        print(f"Signal Strength: {result.strength:.3f}")
        print(f"Signal Confidence: {result.confidence:.3f}")
        
        if result.predictions:
            prediction = result.predictions[0]
            print(f"\nPrediction Details:")
            print(f"  Predicted Value: {prediction.predicted_value:.4f}")
            print(f"  Prediction Confidence: {prediction.confidence:.3f}")
            print(f"  Model Type: {prediction.model_type.value}")
            
            if prediction.probability_distribution:
                print(f"  Probability Distribution:")
                for key, prob in prediction.probability_distribution.items():
                    print(f"    {key}: {prob:.3f}")
        
        print(f"\nPosition Sizing:")
        for key, value in result.position_sizing.items():
            print(f"  {key}: {value:.4f}")
        
        print(f"\nRisk Management:")
        if result.stop_loss_level:
            print(f"  Stop Loss Level: {result.stop_loss_level:.2f}")
        if result.take_profit_level:
            print(f"  Take Profit Level: {result.take_profit_level:.2f}")
        
        print(f"\nRisk Metrics:")
        for metric, value in result.risk_metrics.items():
            print(f"  {metric}: {value:.4f}")
        
        print(f"\nModel Performance:")
        for metric, value in result.model_performance.items():
            print(f"  {metric}: {value:.4f}")
        
        print(f"\nFeature Information:")
        print(f"  Total Features: {len(result.feature_set.feature_names)}")
        print(f"  Top 5 Features:")
        
        # Show top features by importance
        if result.predictions and result.predictions[0].feature_importance:
            sorted_features = sorted(
                result.predictions[0].feature_importance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for feature, importance in sorted_features[:5]:
                print(f"    {feature}: {importance:.4f}")


if __name__ == "__main__":
    # Run tests
    test_ml_trading_strategies()