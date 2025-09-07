"""
AI Prediction Engine
Advanced market prediction using multiple ML models and ensemble methods
"""

import asyncio
import time
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
import logging
import json

from .model_manager import ModelManager, ModelType, ModelPurpose
from .inference_engine import InferenceEngine, InferencePriority
from .pattern_recognition import PatternRecognitionEngine as PatternRecognizer, PatternMatch as MarketPattern
from .sentiment_analyzer import MarketSentimentAnalyzer, SentimentScore


class PredictionType(Enum):
    """Types of market predictions"""
    PRICE_DIRECTION = "price_direction"
    PRICE_TARGET = "price_target"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    TREND_CONTINUATION = "trend_continuation"
    REVERSAL_PROBABILITY = "reversal_probability"
    SUPPORT_RESISTANCE = "support_resistance"
    BREAKOUT_PROBABILITY = "breakout_probability"


class PredictionHorizon(Enum):
    """Prediction time horizons"""
    INTRADAY = "intraday"          # Minutes to hours
    SHORT_TERM = "short_term"      # Days to weeks
    MEDIUM_TERM = "medium_term"    # Weeks to months
    LONG_TERM = "long_term"        # Months to years


class PredictionConfidence(Enum):
    """Prediction confidence levels"""
    VERY_HIGH = 0.9
    HIGH = 0.75
    MEDIUM = 0.6
    LOW = 0.4
    VERY_LOW = 0.2


@dataclass
class MarketPrediction:
    """Market prediction result"""
    symbol: str
    prediction_type: PredictionType
    horizon: PredictionHorizon
    
    # Prediction values
    predicted_value: Union[float, str]  # Numeric value or direction ('up', 'down', 'sideways')
    confidence: float  # 0.0 to 1.0
    probability: Optional[float] = None  # For probabilistic predictions
    
    # Range predictions
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    
    # Model information
    model_id: Optional[str] = None
    model_ensemble: Optional[List[str]] = None
    
    # Supporting data
    features_used: List[str] = field(default_factory=list)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Context
    current_price: Optional[float] = None
    market_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    timestamp: float = field(default_factory=time.time)
    expiry_time: Optional[float] = None
    prediction_id: str = field(default_factory=lambda: f"pred_{int(time.time() * 1000)}")
    
    # Validation
    actual_value: Optional[float] = None
    accuracy_score: Optional[float] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if prediction has expired"""
        if self.expiry_time is None:
            return False
        return time.time() > self.expiry_time
    
    @property
    def confidence_label(self) -> str:
        """Get human-readable confidence label"""
        if self.confidence >= PredictionConfidence.VERY_HIGH.value:
            return "Very High"
        elif self.confidence >= PredictionConfidence.HIGH.value:
            return "High"
        elif self.confidence >= PredictionConfidence.MEDIUM.value:
            return "Medium"
        elif self.confidence >= PredictionConfidence.LOW.value:
            return "Low"
        else:
            return "Very Low"


class FeatureEngineer:
    """Feature engineering for ML predictions"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_technical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Create technical analysis features"""
        features = data.copy()
        
        try:
            # Price-based features
            features['returns'] = features['close'].pct_change()
            features['log_returns'] = np.log(features['close'] / features['close'].shift(1))
            
            # Moving averages
            for window in [5, 10, 20, 50]:
                features[f'sma_{window}'] = features['close'].rolling(window).mean()
                features[f'ema_{window}'] = features['close'].ewm(span=window).mean()
                features[f'price_to_sma_{window}'] = features['close'] / features[f'sma_{window}']
            
            # Volatility features
            features['volatility_5'] = features['returns'].rolling(5).std()
            features['volatility_20'] = features['returns'].rolling(20).std()
            
            # Volume features
            features['volume_sma_10'] = features['volume'].rolling(10).mean()
            features['volume_ratio'] = features['volume'] / features['volume_sma_10']
            
            # Price range features
            features['high_low_ratio'] = features['high'] / features['low']
            features['close_to_high'] = features['close'] / features['high']
            features['close_to_low'] = features['close'] / features['low']
            
            # Momentum features
            for period in [5, 10, 20]:
                features[f'momentum_{period}'] = features['close'] / features['close'].shift(period)
                features[f'roc_{period}'] = features['close'].pct_change(period)
            
            # Bollinger Bands
            # Bollinger Bands
            bb_window = 20
            bb_std = 2
            bb_sma = features['close'].rolling(bb_window).mean()
            bb_std_dev = features['close'].rolling(bb_window).std()
            bb_upper = bb_sma + (bb_std_dev * bb_std)
            bb_lower = bb_sma - (bb_std_dev * bb_std)
            features['bb_upper'] = bb_upper
            features['bb_lower'] = bb_lower
            features['bb_position'] = (features['close'] - bb_lower) / (bb_upper - bb_lower)
            
            # RSI
            delta = features['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            ema_12 = features['close'].ewm(span=12).mean()
            ema_26 = features['close'].ewm(span=26).mean()
            features['macd'] = ema_12 - ema_26
            features['macd_signal'] = features['macd'].ewm(span=9).mean()
            features['macd_histogram'] = features['macd'] - features['macd_signal']
            
        except Exception as e:
            self.logger.error(f"Error creating technical features: {e}")
        
        return features
    
    def create_pattern_features(self, patterns: List[MarketPattern]) -> Dict[str, float]:
        """Create features from detected patterns"""
        features = {}
        
        try:
            # Pattern counts by type
            pattern_counts = {}
            for pattern in patterns:
                pattern_type = pattern.pattern_type.value
                pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
            
            # Add pattern count features
            for pattern_type, count in pattern_counts.items():
                features[f'pattern_count_{pattern_type}'] = count
            
            # Pattern strength features
            if patterns:
                features['max_pattern_confidence'] = max(p.confidence for p in patterns)
                features['avg_pattern_confidence'] = sum(p.confidence for p in patterns) / len(patterns)
                features['pattern_diversity'] = len(set(p.pattern_type for p in patterns))
            else:
                features['max_pattern_confidence'] = 0.0
                features['avg_pattern_confidence'] = 0.0
                features['pattern_diversity'] = 0.0
        
        except Exception as e:
            self.logger.error(f"Error creating pattern features: {e}")
        
        return features
    
    def create_sentiment_features(self, sentiment: Optional[SentimentScore]) -> Dict[str, float]:
        """Create features from sentiment analysis"""
        features = {}
        
        try:
            if sentiment:
                features['sentiment_polarity'] = sentiment.polarity
                features['sentiment_confidence'] = sentiment.confidence
                features['sentiment_magnitude'] = sentiment.magnitude
                features['sentiment_significant'] = 1.0 if sentiment.is_significant else 0.0
            else:
                features['sentiment_polarity'] = 0.0
                features['sentiment_confidence'] = 0.0
                features['sentiment_magnitude'] = 0.0
                features['sentiment_significant'] = 0.0
        
        except Exception as e:
            self.logger.error(f"Error creating sentiment features: {e}")
        
        return features
    
    def create_market_regime_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Create market regime features"""
        features = {}
        
        try:
            if len(data) < 50:
                return features
            
            # Trend strength
            returns = data['close'].pct_change().dropna()
            if len(returns) > 0:
                features['trend_strength'] = abs(returns.mean()) / returns.std() if returns.std() > 0 else 0
                features['trend_direction'] = 1.0 if returns.mean() > 0 else -1.0
            
            # Volatility regime
            volatility = returns.rolling(20).std()
            if len(volatility.dropna()) > 0:
                current_vol = volatility.iloc[-1]
                avg_vol = volatility.mean()
                features['volatility_regime'] = current_vol / avg_vol if avg_vol > 0 else 1.0
            
            # Market efficiency (autocorrelation)
            if len(returns) > 10:
                autocorr = returns.autocorr(lag=1)
                features['market_efficiency'] = 1.0 - abs(autocorr) if not np.isnan(autocorr) else 1.0
        
        except Exception as e:
            self.logger.error(f"Error creating market regime features: {e}")
        
        return features


class PredictionEngine:
    """
    Advanced prediction engine using ensemble methods
    
    Features:
    - Multiple ML model integration
    - Ensemble predictions
    - Feature engineering
    - Pattern and sentiment integration
    - Prediction validation and tracking
    """
    
    def __init__(self,
                 model_manager: ModelManager,
                 inference_engine: InferenceEngine,
                 pattern_recognizer: Optional[PatternRecognizer] = None,
                 sentiment_analyzer: Optional[MarketSentimentAnalyzer] = None):
        
        self.model_manager = model_manager
        self.inference_engine = inference_engine
        self.pattern_recognizer = pattern_recognizer
        self.sentiment_analyzer = sentiment_analyzer
        
        self.feature_engineer = FeatureEngineer()
        
        # Prediction storage
        self.predictions: Dict[str, MarketPrediction] = {}
        self.prediction_history: List[MarketPrediction] = []
        
        # Model registry for different prediction types
        self.model_registry: Dict[PredictionType, List[str]] = {}
        
        # Performance tracking
        self.accuracy_metrics = {
            'total_predictions': 0,
            'correct_predictions': 0,
            'accuracy_by_type': {},
            'accuracy_by_horizon': {},
            'accuracy_by_confidence': {}
        }
        
        self.logger = logging.getLogger(__name__)
    
    async def predict_price_direction(self,
                                    symbol: str,
                                    data: pd.DataFrame,
                                    horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM) -> MarketPrediction:
        """
        Predict price direction (up/down/sideways)
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            horizon: Prediction time horizon
            
        Returns:
            Price direction prediction
        """
        try:
            # Feature engineering
            features = await self._prepare_features(symbol, data)
            
            # Get relevant models
            models = self._get_models_for_prediction(PredictionType.PRICE_DIRECTION)
            
            if not models:
                # Fallback to simple technical analysis
                return await self._fallback_direction_prediction(symbol, data, horizon)
            
            # Ensemble prediction
            predictions = []
            confidences = []
            
            for model_id in models:
                try:
                    result = await self.inference_engine.predict(
                        model_id=model_id,
                        input_data=features,
                        priority=InferencePriority.HIGH
                    )
                    
                    if result.success:
                        predictions.append(result.prediction)
                        confidences.append(result.confidence or 0.5)
                
                except Exception as e:
                    self.logger.warning(f"Model {model_id} prediction failed: {e}")
            
            # Aggregate predictions
            if predictions:
                # Weighted voting
                weights = np.array(confidences)
                weights = weights / weights.sum()
                
                # Convert predictions to numeric (assuming 0=down, 1=sideways, 2=up)
                numeric_predictions = np.array(predictions)
                weighted_prediction = np.average(numeric_predictions, weights=weights)
                
                # Convert back to direction
                if weighted_prediction < 0.33:
                    direction = "down"
                elif weighted_prediction > 0.67:
                    direction = "up"
                else:
                    direction = "sideways"
                
                confidence = np.mean(confidences)
            else:
                # Fallback
                return await self._fallback_direction_prediction(symbol, data, horizon)
            
            # Create prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_DIRECTION,
                horizon=horizon,
                predicted_value=direction,
                confidence=confidence,
                model_ensemble=models,
                features_used=list(features.keys()) if isinstance(features, dict) else [],
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Store prediction
            self._store_prediction(prediction)
            
            return prediction
        
        except Exception as e:
            self.logger.error(f"Error predicting price direction for {symbol}: {e}")
            return await self._fallback_direction_prediction(symbol, data, horizon)
    
    async def predict_price_target(self,
                                 symbol: str,
                                 data: pd.DataFrame,
                                 horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM) -> MarketPrediction:
        """
        Predict specific price target
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            horizon: Prediction time horizon
            
        Returns:
            Price target prediction
        """
        try:
            # Feature engineering
            features = await self._prepare_features(symbol, data)
            
            # Get relevant models
            models = self._get_models_for_prediction(PredictionType.PRICE_TARGET)
            
            current_price = data['close'].iloc[-1] if len(data) > 0 else None
            
            if not models or current_price is None:
                # Fallback to technical analysis
                return await self._fallback_price_target(symbol, data, horizon)
            
            # Ensemble prediction
            predictions = []
            confidences = []
            
            for model_id in models:
                try:
                    result = await self.inference_engine.predict(
                        model_id=model_id,
                        input_data=features,
                        priority=InferencePriority.HIGH
                    )
                    
                    if result.success:
                        predictions.append(result.prediction)
                        confidences.append(result.confidence or 0.5)
                
                except Exception as e:
                    self.logger.warning(f"Model {model_id} prediction failed: {e}")
            
            # Aggregate predictions
            if predictions:
                weights = np.array(confidences)
                weights = weights / weights.sum()
                
                predicted_price = np.average(predictions, weights=weights)
                confidence = np.mean(confidences)
                
                # Calculate bounds (confidence interval)
                std_dev = np.std(predictions)
                lower_bound = predicted_price - (1.96 * std_dev)  # 95% CI
                upper_bound = predicted_price + (1.96 * std_dev)
            else:
                return await self._fallback_price_target(symbol, data, horizon)
            
            # Create prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_TARGET,
                horizon=horizon,
                predicted_value=predicted_price,
                confidence=confidence,
                lower_bound=lower_bound,
                upper_bound=upper_bound,
                model_ensemble=models,
                features_used=list(features.keys()) if isinstance(features, dict) else [],
                current_price=current_price,
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Store prediction
            self._store_prediction(prediction)
            
            return prediction
        
        except Exception as e:
            self.logger.error(f"Error predicting price target for {symbol}: {e}")
            return await self._fallback_price_target(symbol, data, horizon)
    
    async def predict_volatility(self,
                               symbol: str,
                               data: pd.DataFrame,
                               horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM) -> MarketPrediction:
        """
        Predict future volatility
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            horizon: Prediction time horizon
            
        Returns:
            Volatility prediction
        """
        try:
            # Calculate current volatility
            returns = data['close'].pct_change().dropna()
            current_volatility = returns.rolling(20).std().iloc[-1] if len(returns) >= 20 else returns.std()
            
            # Feature engineering
            features = await self._prepare_features(symbol, data)
            
            # Add volatility-specific features
            if len(returns) >= 5:
                features['current_volatility'] = current_volatility
                features['volatility_trend'] = returns.rolling(5).std().iloc[-1] / current_volatility if current_volatility > 0 else 1.0
            
            # Get relevant models
            models = self._get_models_for_prediction(PredictionType.VOLATILITY)
            
            if not models:
                # Fallback to GARCH-like prediction
                return await self._fallback_volatility_prediction(symbol, data, horizon, current_volatility)
            
            # Ensemble prediction
            predictions = []
            confidences = []
            
            for model_id in models:
                try:
                    result = await self.inference_engine.predict(
                        model_id=model_id,
                        input_data=features,
                        priority=InferencePriority.NORMAL
                    )
                    
                    if result.success:
                        predictions.append(result.prediction)
                        confidences.append(result.confidence or 0.5)
                
                except Exception as e:
                    self.logger.warning(f"Model {model_id} prediction failed: {e}")
            
            # Aggregate predictions
            if predictions:
                weights = np.array(confidences)
                weights = weights / weights.sum()
                
                predicted_volatility = np.average(predictions, weights=weights)
                confidence = np.mean(confidences)
            else:
                return await self._fallback_volatility_prediction(symbol, data, horizon, current_volatility)
            
            # Create prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.VOLATILITY,
                horizon=horizon,
                predicted_value=predicted_volatility,
                confidence=confidence,
                model_ensemble=models,
                features_used=list(features.keys()) if isinstance(features, dict) else [],
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                market_conditions={'current_volatility': current_volatility},
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Store prediction
            self._store_prediction(prediction)
            
            return prediction
        
        except Exception as e:
            self.logger.error(f"Error predicting volatility for {symbol}: {e}")
            return await self._fallback_volatility_prediction(symbol, data, horizon, 0.02)
    
    async def _prepare_features(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Prepare features for prediction"""
        features = {}
        
        try:
            # Technical features
            technical_data = self.feature_engineer.create_technical_features(data)
            
            # Get latest values (last row)
            if len(technical_data) > 0:
                latest_row = technical_data.iloc[-1]
                for col in technical_data.columns:
                    if not pd.isna(latest_row[col]) and col not in ['open', 'high', 'low', 'close', 'volume']:
                        features[col] = float(latest_row[col])
            
            # Pattern features
            if self.pattern_recognizer:
                patterns = self.pattern_recognizer.detect_patterns(data)
                pattern_features = self.feature_engineer.create_pattern_features(patterns)
                features.update(pattern_features)
            
            # Sentiment features
            if self.sentiment_analyzer:
                sentiment = await self.sentiment_analyzer.get_symbol_sentiment(symbol, 24)
                sentiment_features = self.feature_engineer.create_sentiment_features(sentiment)
                features.update(sentiment_features)
            
            # Market regime features
            regime_features = self.feature_engineer.create_market_regime_features(data)
            features.update(regime_features)
        
        except Exception as e:
            self.logger.error(f"Error preparing features: {e}")
        
        return features
    
    def _get_models_for_prediction(self, prediction_type: PredictionType) -> List[str]:
        """Get models suitable for prediction type"""
        return self.model_registry.get(prediction_type, [])
    
    def register_model(self, model_id: str, prediction_types: List[PredictionType]):
        """Register a model for specific prediction types"""
        for pred_type in prediction_types:
            if pred_type not in self.model_registry:
                self.model_registry[pred_type] = []
            
            if model_id not in self.model_registry[pred_type]:
                self.model_registry[pred_type].append(model_id)
        
        self.logger.info(f"Registered model {model_id} for prediction types: {[pt.value for pt in prediction_types]}")
    
    def _calculate_expiry_time(self, horizon: PredictionHorizon) -> float:
        """Calculate prediction expiry time"""
        current_time = time.time()
        
        if horizon == PredictionHorizon.INTRADAY:
            return current_time + (4 * 3600)  # 4 hours
        elif horizon == PredictionHorizon.SHORT_TERM:
            return current_time + (7 * 24 * 3600)  # 1 week
        elif horizon == PredictionHorizon.MEDIUM_TERM:
            return current_time + (30 * 24 * 3600)  # 1 month
        else:  # LONG_TERM
            return current_time + (90 * 24 * 3600)  # 3 months
    
    def _store_prediction(self, prediction: MarketPrediction):
        """Store prediction for tracking"""
        self.predictions[prediction.prediction_id] = prediction
        self.prediction_history.append(prediction)
        
        # Limit history size
        if len(self.prediction_history) > 10000:
            self.prediction_history = self.prediction_history[-10000:]
        
        # Update metrics
        self.accuracy_metrics['total_predictions'] += 1
    
    async def _fallback_direction_prediction(self, symbol: str, data: pd.DataFrame, horizon: PredictionHorizon) -> MarketPrediction:
        """Fallback direction prediction using technical analysis"""
        try:
            if len(data) < 20:
                direction = "sideways"
                confidence = 0.3
            else:
                # Simple trend analysis
                sma_5 = data['close'].rolling(5).mean().iloc[-1]
                sma_20 = data['close'].rolling(20).mean().iloc[-1]
                current_price = data['close'].iloc[-1]
                
                if current_price > sma_5 > sma_20:
                    direction = "up"
                    confidence = 0.6
                elif current_price < sma_5 < sma_20:
                    direction = "down"
                    confidence = 0.6
                else:
                    direction = "sideways"
                    confidence = 0.4
            
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_DIRECTION,
                horizon=horizon,
                predicted_value=direction,
                confidence=confidence,
                features_used=['sma_5', 'sma_20', 'current_price'],
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                expiry_time=self._calculate_expiry_time(horizon)
            )
        
        except Exception as e:
            self.logger.error(f"Fallback direction prediction failed: {e}")
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_DIRECTION,
                horizon=horizon,
                predicted_value="sideways",
                confidence=0.2,
                expiry_time=self._calculate_expiry_time(horizon)
            )
    
    async def _fallback_price_target(self, symbol: str, data: pd.DataFrame, horizon: PredictionHorizon) -> MarketPrediction:
        """Fallback price target using technical levels"""
        try:
            current_price = data['close'].iloc[-1] if len(data) > 0 else 100.0
            
            if len(data) >= 20:
                # Use support/resistance levels
                highs = data['high'].rolling(20).max().iloc[-1]
                lows = data['low'].rolling(20).min().iloc[-1]
                
                # Simple target based on range
                if current_price > (highs + lows) / 2:
                    target = highs * 1.02  # 2% above resistance
                else:
                    target = lows * 0.98   # 2% below support
                
                confidence = 0.5
            else:
                # Default to current price
                target = current_price
                confidence = 0.3
            
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_TARGET,
                horizon=horizon,
                predicted_value=target,
                confidence=confidence,
                current_price=current_price,
                expiry_time=self._calculate_expiry_time(horizon)
            )
        
        except Exception as e:
            self.logger.error(f"Fallback price target failed: {e}")
            current_price = data['close'].iloc[-1] if len(data) > 0 else 100.0
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.PRICE_TARGET,
                horizon=horizon,
                predicted_value=current_price,
                confidence=0.2,
                current_price=current_price,
                expiry_time=self._calculate_expiry_time(horizon)
            )
    
    async def _fallback_volatility_prediction(self, symbol: str, data: pd.DataFrame, horizon: PredictionHorizon, current_vol: float) -> MarketPrediction:
        """Fallback volatility prediction using historical analysis"""
        try:
            if len(data) >= 20:
                returns = data['close'].pct_change().dropna()
                historical_vol = returns.rolling(20).std()
                
                # Simple mean reversion assumption
                mean_vol = historical_vol.mean()
                predicted_vol = (current_vol + mean_vol) / 2  # Mean reversion
                confidence = 0.5
            else:
                predicted_vol = current_vol * 1.1  # Slight increase assumption
                confidence = 0.3
            
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.VOLATILITY,
                horizon=horizon,
                predicted_value=predicted_vol,
                confidence=confidence,
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                market_conditions={'current_volatility': current_vol},
                expiry_time=self._calculate_expiry_time(horizon)
            )
        
        except Exception as e:
            self.logger.error(f"Fallback volatility prediction failed: {e}")
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.VOLATILITY,
                horizon=horizon,
                predicted_value=current_vol,
                confidence=0.2,
                expiry_time=self._calculate_expiry_time(horizon)
            )
    
    async def predict_breakout_probability(self,
                                         symbol: str,
                                         data: pd.DataFrame,
                                         horizon: PredictionHorizon = PredictionHorizon.INTRADAY) -> MarketPrediction:
        """
        Predict probability of price breakout
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            horizon: Prediction time horizon
            
        Returns:
            Breakout probability prediction
        """
        try:
            # Feature engineering for breakout detection
            features = await self._prepare_features(symbol, data)
            
            # Add breakout-specific features
            if len(data) >= 20:
                # Bollinger Band squeeze
                bb_window = 20
                bb_sma = data['close'].rolling(bb_window).mean()
                bb_std = data['close'].rolling(bb_window).std()
                bb_width = (bb_std * 2) / bb_sma
                features['bb_squeeze'] = 1.0 if bb_width.iloc[-1] < bb_width.rolling(50).mean().iloc[-1] else 0.0
                
                # Volume analysis
                volume_sma = data['volume'].rolling(20).mean()
                features['volume_breakout_signal'] = data['volume'].iloc[-1] / volume_sma.iloc[-1] if volume_sma.iloc[-1] > 0 else 1.0
                
                # Price consolidation
                high_20 = data['high'].rolling(20).max()
                low_20 = data['low'].rolling(20).min()
                consolidation_range = (high_20 - low_20) / data['close']
                features['consolidation_tightness'] = 1.0 / consolidation_range.iloc[-1] if consolidation_range.iloc[-1] > 0 else 0.0
            
            # Get relevant models
            models = self._get_models_for_prediction(PredictionType.BREAKOUT_PROBABILITY)
            
            if not models:
                # Fallback to technical analysis
                return await self._fallback_breakout_prediction(symbol, data, horizon, features)
            
            # Ensemble prediction
            predictions = []
            confidences = []
            
            for model_id in models:
                try:
                    result = await self.inference_engine.predict(
                        model_id=model_id,
                        input_data=features,
                        priority=InferencePriority.HIGH
                    )
                    
                    if result.success:
                        predictions.append(result.prediction)
                        confidences.append(result.confidence or 0.5)
                
                except Exception as e:
                    self.logger.warning(f"Model {model_id} prediction failed: {e}")
            
            # Aggregate predictions
            if predictions:
                weights = np.array(confidences)
                weights = weights / weights.sum()
                
                breakout_probability = np.average(predictions, weights=weights)
                confidence = np.mean(confidences)
            else:
                return await self._fallback_breakout_prediction(symbol, data, horizon, features)
            
            # Create prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.BREAKOUT_PROBABILITY,
                horizon=horizon,
                predicted_value=breakout_probability,
                probability=breakout_probability,
                confidence=confidence,
                model_ensemble=models,
                features_used=list(features.keys()),
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Store prediction
            self._store_prediction(prediction)
            
            return prediction
        
        except Exception as e:
            self.logger.error(f"Error predicting breakout probability for {symbol}: {e}")
            return await self._fallback_breakout_prediction(symbol, data, horizon, {})
    
    async def _fallback_breakout_prediction(self, symbol: str, data: pd.DataFrame, horizon: PredictionHorizon, features: Dict[str, Any]) -> MarketPrediction:
        """Fallback breakout prediction using technical indicators"""
        try:
            breakout_probability = 0.3  # Default neutral probability
            confidence = 0.4
            
            if len(data) >= 20:
                # Simple breakout indicators
                current_price = data['close'].iloc[-1]
                
                # Bollinger Bands
                bb_sma = data['close'].rolling(20).mean().iloc[-1]
                bb_std = data['close'].rolling(20).std().iloc[-1]
                bb_upper = bb_sma + (2 * bb_std)
                bb_lower = bb_sma - (2 * bb_std)
                
                # Volume
                volume_ratio = features.get('volume_breakout_signal', 1.0)
                
                # Calculate probability based on position and volume
                if current_price > bb_upper * 0.98 and volume_ratio > 1.5:
                    breakout_probability = 0.7  # High probability of upward breakout
                    confidence = 0.6
                elif current_price < bb_lower * 1.02 and volume_ratio > 1.5:
                    breakout_probability = 0.7  # High probability of downward breakout
                    confidence = 0.6
                elif features.get('bb_squeeze', 0.0) > 0.5:
                    breakout_probability = 0.6  # Squeeze indicates potential breakout
                    confidence = 0.5
            
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.BREAKOUT_PROBABILITY,
                horizon=horizon,
                predicted_value=breakout_probability,
                probability=breakout_probability,
                confidence=confidence,
                features_used=['bb_bands', 'volume_ratio', 'bb_squeeze'],
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                expiry_time=self._calculate_expiry_time(horizon)
            )
        
        except Exception as e:
            self.logger.error(f"Fallback breakout prediction failed: {e}")
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.BREAKOUT_PROBABILITY,
                horizon=horizon,
                predicted_value=0.3,
                probability=0.3,
                confidence=0.2,
                expiry_time=self._calculate_expiry_time(horizon)
            )
    
    async def predict_support_resistance(self,
                                       symbol: str,
                                       data: pd.DataFrame,
                                       horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM) -> MarketPrediction:
        """
        Predict support and resistance levels
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            horizon: Prediction time horizon
            
        Returns:
            Support/resistance prediction
        """
        try:
            # Calculate support and resistance levels
            levels = self._calculate_support_resistance_levels(data)
            
            # Feature engineering
            features = await self._prepare_features(symbol, data)
            
            # Add S/R specific features
            current_price = data['close'].iloc[-1] if len(data) > 0 else None
            if current_price and levels:
                features['distance_to_support'] = min(abs(current_price - level) for level in levels['support'])
                features['distance_to_resistance'] = min(abs(current_price - level) for level in levels['resistance'])
                features['support_strength'] = len(levels['support'])
                features['resistance_strength'] = len(levels['resistance'])
            
            # Get relevant models
            models = self._get_models_for_prediction(PredictionType.SUPPORT_RESISTANCE)
            
            if not models or not levels:
                # Use calculated levels directly
                prediction_value = levels if levels else {'support': [], 'resistance': []}
                confidence = 0.6 if levels else 0.3
            else:
                # ML enhancement of levels
                predictions = []
                confidences = []
                
                for model_id in models:
                    try:
                        result = await self.inference_engine.predict(
                            model_id=model_id,
                            input_data=features,
                            priority=InferencePriority.NORMAL
                        )
                        
                        if result.success:
                            predictions.append(result.prediction)
                            confidences.append(result.confidence or 0.5)
                    
                    except Exception as e:
                        self.logger.warning(f"Model {model_id} prediction failed: {e}")
                
                if predictions:
                    # Enhance levels with ML predictions
                    confidence = np.mean(confidences)
                    prediction_value = levels  # Use technical levels, enhanced by ML confidence
                else:
                    prediction_value = levels
                    confidence = 0.5
            
            # Create prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.SUPPORT_RESISTANCE,
                horizon=horizon,
                predicted_value=prediction_value,
                confidence=confidence,
                model_ensemble=models if models else None,
                features_used=list(features.keys()),
                current_price=current_price,
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Store prediction
            self._store_prediction(prediction)
            
            return prediction
        
        except Exception as e:
            self.logger.error(f"Error predicting support/resistance for {symbol}: {e}")
            return MarketPrediction(
                symbol=symbol,
                prediction_type=PredictionType.SUPPORT_RESISTANCE,
                horizon=horizon,
                predicted_value={'support': [], 'resistance': []},
                confidence=0.2,
                expiry_time=self._calculate_expiry_time(horizon)
            )
    
    def _calculate_support_resistance_levels(self, data: pd.DataFrame, lookback: int = 50) -> Dict[str, List[float]]:
        """Calculate support and resistance levels using pivot points"""
        try:
            if len(data) < lookback:
                return {'support': [], 'resistance': []}
            
            # Use recent data
            recent_data = data.tail(lookback)
            
            # Find pivot highs and lows
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            
            # Simple pivot detection (local maxima/minima)
            resistance_levels = []
            support_levels = []
            
            window = 5  # Look for pivots in 5-period windows
            
            for i in range(window, len(highs) - window):
                # Resistance (pivot high)
                if all(highs[i] >= highs[i-j] for j in range(1, window+1)) and \
                   all(highs[i] >= highs[i+j] for j in range(1, window+1)):
                    resistance_levels.append(highs[i])
                
                # Support (pivot low)
                if all(lows[i] <= lows[i-j] for j in range(1, window+1)) and \
                   all(lows[i] <= lows[i+j] for j in range(1, window+1)):
                    support_levels.append(lows[i])
            
            # Remove duplicates and sort
            resistance_levels = sorted(list(set(resistance_levels)), reverse=True)
            support_levels = sorted(list(set(support_levels)))
            
            # Keep only the most significant levels (top 5 each)
            resistance_levels = resistance_levels[:5]
            support_levels = support_levels[-5:]  # Take the highest support levels
            
            return {
                'support': support_levels,
                'resistance': resistance_levels
            }
        
        except Exception as e:
            self.logger.error(f"Error calculating support/resistance levels: {e}")
            return {'support': [], 'resistance': []}
    
    async def get_ensemble_prediction(self,
                                    symbol: str,
                                    data: pd.DataFrame,
                                    prediction_types: List[PredictionType],
                                    horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM) -> Dict[PredictionType, MarketPrediction]:
        """
        Get ensemble predictions for multiple prediction types
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            prediction_types: List of prediction types to generate
            horizon: Prediction time horizon
            
        Returns:
            Dictionary of predictions by type
        """
        predictions = {}
        
        # Generate predictions concurrently
        tasks = []
        for pred_type in prediction_types:
            if pred_type == PredictionType.PRICE_DIRECTION:
                task = self.predict_price_direction(symbol, data, horizon)
            elif pred_type == PredictionType.PRICE_TARGET:
                task = self.predict_price_target(symbol, data, horizon)
            elif pred_type == PredictionType.VOLATILITY:
                task = self.predict_volatility(symbol, data, horizon)
            elif pred_type == PredictionType.BREAKOUT_PROBABILITY:
                task = self.predict_breakout_probability(symbol, data, horizon)
            elif pred_type == PredictionType.SUPPORT_RESISTANCE:
                task = self.predict_support_resistance(symbol, data, horizon)
            else:
                continue  # Skip unsupported types
            
            tasks.append((pred_type, task))
        
        # Execute all predictions
        for pred_type, task in tasks:
            try:
                prediction = await task
                predictions[pred_type] = prediction
            except Exception as e:
                self.logger.error(f"Error generating {pred_type.value} prediction: {e}")
        
        return predictions
    
    def validate_prediction(self, prediction_id: str, actual_value: float) -> Optional[float]:
        """
        Validate a prediction against actual outcome
        
        Args:
            prediction_id: ID of the prediction to validate
            actual_value: Actual observed value
            
        Returns:
            Accuracy score (0.0 to 1.0) or None if prediction not found
        """
        try:
            if prediction_id not in self.predictions:
                return None
            
            prediction = self.predictions[prediction_id]
            prediction.actual_value = actual_value
            
            # Calculate accuracy based on prediction type
            if prediction.prediction_type == PredictionType.PRICE_DIRECTION:
                # Direction accuracy
                predicted_direction = prediction.predicted_value
                current_price = prediction.current_price or 0
                
                if current_price > 0:
                    actual_direction = "up" if actual_value > current_price else "down" if actual_value < current_price else "sideways"
                    accuracy = 1.0 if predicted_direction == actual_direction else 0.0
                else:
                    accuracy = 0.0
            
            elif prediction.prediction_type == PredictionType.PRICE_TARGET:
                # Price target accuracy (inverse of relative error)
                predicted_price = prediction.predicted_value
                relative_error = abs(actual_value - predicted_price) / max(actual_value, predicted_price)
                accuracy = max(0.0, 1.0 - relative_error)
            
            elif prediction.prediction_type == PredictionType.VOLATILITY:
                # Volatility accuracy
                predicted_vol = prediction.predicted_value
                relative_error = abs(actual_value - predicted_vol) / max(actual_value, predicted_vol)
                accuracy = max(0.0, 1.0 - relative_error)
            
            else:
                # Generic accuracy for other types
                if isinstance(prediction.predicted_value, (int, float)):
                    relative_error = abs(actual_value - prediction.predicted_value) / max(actual_value, abs(prediction.predicted_value), 1e-6)
                    accuracy = max(0.0, 1.0 - relative_error)
                else:
                    accuracy = 0.5  # Default for non-numeric predictions
            
            prediction.accuracy_score = accuracy
            
            # Update global metrics
            self._update_accuracy_metrics(prediction, accuracy)
            
            return accuracy
        
        except Exception as e:
            self.logger.error(f"Error validating prediction {prediction_id}: {e}")
            return None
    
    def _update_accuracy_metrics(self, prediction: MarketPrediction, accuracy: float):
        """Update accuracy tracking metrics"""
        try:
            # Overall accuracy
            if accuracy >= 0.7:  # Consider 70%+ as "correct"
                self.accuracy_metrics['correct_predictions'] += 1
            
            # Accuracy by type
            pred_type = prediction.prediction_type.value
            if pred_type not in self.accuracy_metrics['accuracy_by_type']:
                self.accuracy_metrics['accuracy_by_type'][pred_type] = {'total': 0, 'sum': 0.0}
            
            self.accuracy_metrics['accuracy_by_type'][pred_type]['total'] += 1
            self.accuracy_metrics['accuracy_by_type'][pred_type]['sum'] += accuracy
            
            # Accuracy by horizon
            horizon = prediction.horizon.value
            if horizon not in self.accuracy_metrics['accuracy_by_horizon']:
                self.accuracy_metrics['accuracy_by_horizon'][horizon] = {'total': 0, 'sum': 0.0}
            
            self.accuracy_metrics['accuracy_by_horizon'][horizon]['total'] += 1
            self.accuracy_metrics['accuracy_by_horizon'][horizon]['sum'] += accuracy
            
            # Accuracy by confidence level
            conf_level = "high" if prediction.confidence >= 0.7 else "medium" if prediction.confidence >= 0.5 else "low"
            if conf_level not in self.accuracy_metrics['accuracy_by_confidence']:
                self.accuracy_metrics['accuracy_by_confidence'][conf_level] = {'total': 0, 'sum': 0.0}
            
            self.accuracy_metrics['accuracy_by_confidence'][conf_level]['total'] += 1
            self.accuracy_metrics['accuracy_by_confidence'][conf_level]['sum'] += accuracy
        
        except Exception as e:
            self.logger.error(f"Error updating accuracy metrics: {e}")
    
    def get_prediction_performance(self) -> Dict[str, Any]:
        """Get prediction performance metrics"""
        try:
            total_predictions = self.accuracy_metrics['total_predictions']
            correct_predictions = self.accuracy_metrics['correct_predictions']
            
            performance = {
                'total_predictions': total_predictions,
                'correct_predictions': correct_predictions,
                'overall_accuracy': correct_predictions / max(1, total_predictions),
                'accuracy_by_type': {},
                'accuracy_by_horizon': {},
                'accuracy_by_confidence': {}
            }
            
            # Calculate averages by category
            for category in ['accuracy_by_type', 'accuracy_by_horizon', 'accuracy_by_confidence']:
                for key, data in self.accuracy_metrics[category].items():
                    if data['total'] > 0:
                        performance[category][key] = {
                            'accuracy': data['sum'] / data['total'],
                            'count': data['total']
                        }
            
            return performance
        
        except Exception as e:
            self.logger.error(f"Error getting prediction performance: {e}")
            return {'total_predictions': 0, 'overall_accuracy': 0.0}
    
    def get_active_predictions(self, symbol: Optional[str] = None) -> List[MarketPrediction]:
        """Get active (non-expired) predictions"""
        try:
            active_predictions = []
            current_time = time.time()
            
            for prediction in self.predictions.values():
                if not prediction.is_expired and (symbol is None or prediction.symbol == symbol):
                    active_predictions.append(prediction)
            
            return sorted(active_predictions, key=lambda p: p.timestamp, reverse=True)
        
        except Exception as e:
            self.logger.error(f"Error getting active predictions: {e}")
            return []
    
    def cleanup_expired_predictions(self):
        """Remove expired predictions to free memory"""
        try:
            current_time = time.time()
            expired_ids = []
            
            for pred_id, prediction in self.predictions.items():
                if prediction.is_expired:
                    expired_ids.append(pred_id)
            
            for pred_id in expired_ids:
                del self.predictions[pred_id]
            
            if expired_ids:
                self.logger.info(f"Cleaned up {len(expired_ids)} expired predictions")
        
        except Exception as e:
            self.logger.error(f"Error cleaning up expired predictions: {e}")


class EnsemblePredictionEngine(PredictionEngine):
    """
    Enhanced prediction engine with advanced ensemble methods
    
    Features:
    - Multiple ensemble strategies (voting, stacking, blending)
    - Dynamic model weighting based on performance
    - Uncertainty quantification
    - Multi-horizon predictions
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Model performance tracking for dynamic weighting
        self.model_performance: Dict[str, Dict[str, float]] = {}
        
        # Ensemble strategies
        self.ensemble_strategies = {
            'voting': self._voting_ensemble,
            'weighted_voting': self._weighted_voting_ensemble,
            'stacking': self._stacking_ensemble,
            'blending': self._blending_ensemble
        }
        
        # Default ensemble strategy
        self.default_ensemble_strategy = 'weighted_voting'
    
    async def predict_with_uncertainty(self,
                                     symbol: str,
                                     data: pd.DataFrame,
                                     prediction_type: PredictionType,
                                     horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM,
                                     ensemble_strategy: str = None) -> Tuple[MarketPrediction, Dict[str, float]]:
        """
        Generate prediction with uncertainty quantification
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            prediction_type: Type of prediction
            horizon: Prediction time horizon
            ensemble_strategy: Ensemble method to use
            
        Returns:
            Tuple of (prediction, uncertainty_metrics)
        """
        try:
            strategy = ensemble_strategy or self.default_ensemble_strategy
            
            # Get features
            features = await self._prepare_features(symbol, data)
            
            # Get models for this prediction type
            models = self._get_models_for_prediction(prediction_type)
            
            if not models:
                # Fallback to single model prediction
                if prediction_type == PredictionType.PRICE_DIRECTION:
                    prediction = await self.predict_price_direction(symbol, data, horizon)
                elif prediction_type == PredictionType.PRICE_TARGET:
                    prediction = await self.predict_price_target(symbol, data, horizon)
                else:
                    raise ValueError(f"Unsupported prediction type: {prediction_type}")
                
                uncertainty = {'model_disagreement': 0.0, 'prediction_variance': 0.0, 'confidence_spread': 0.0}
                return prediction, uncertainty
            
            # Get predictions from all models
            model_predictions = []
            model_confidences = []
            
            for model_id in models:
                try:
                    result = await self.inference_engine.predict(
                        model_id=model_id,
                        input_data=features,
                        priority=InferencePriority.HIGH
                    )
                    
                    if result.success:
                        model_predictions.append(result.prediction)
                        model_confidences.append(result.confidence or 0.5)
                
                except Exception as e:
                    self.logger.warning(f"Model {model_id} prediction failed: {e}")
            
            if not model_predictions:
                raise ValueError("No successful model predictions")
            
            # Apply ensemble strategy
            ensemble_func = self.ensemble_strategies.get(strategy, self._weighted_voting_ensemble)
            ensemble_result = ensemble_func(models, model_predictions, model_confidences, prediction_type)
            
            # Calculate uncertainty metrics
            uncertainty = self._calculate_uncertainty_metrics(model_predictions, model_confidences)
            
            # Create prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=prediction_type,
                horizon=horizon,
                predicted_value=ensemble_result['prediction'],
                confidence=ensemble_result['confidence'],
                probability=ensemble_result.get('probability'),
                lower_bound=ensemble_result.get('lower_bound'),
                upper_bound=ensemble_result.get('upper_bound'),
                model_ensemble=models,
                features_used=list(features.keys()),
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                market_conditions={'ensemble_strategy': strategy, 'model_count': len(models)},
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Store prediction
            self._store_prediction(prediction)
            
            return prediction, uncertainty
        
        except Exception as e:
            self.logger.error(f"Error generating ensemble prediction: {e}")
            # Fallback to basic prediction
            if prediction_type == PredictionType.PRICE_DIRECTION:
                prediction = await self.predict_price_direction(symbol, data, horizon)
            else:
                prediction = await self.predict_price_target(symbol, data, horizon)
            
            uncertainty = {'model_disagreement': 1.0, 'prediction_variance': 1.0, 'confidence_spread': 1.0}
            return prediction, uncertainty
    
    def _voting_ensemble(self, models: List[str], predictions: List[Any], confidences: List[float], pred_type: PredictionType) -> Dict[str, Any]:
        """Simple majority voting ensemble"""
        try:
            if pred_type == PredictionType.PRICE_DIRECTION:
                # Count votes for each direction
                votes = {}
                for pred in predictions:
                    votes[pred] = votes.get(pred, 0) + 1
                
                # Get majority vote
                majority_vote = max(votes.items(), key=lambda x: x[1])[0]
                confidence = votes[majority_vote] / len(predictions)
                
                return {
                    'prediction': majority_vote,
                    'confidence': confidence
                }
            else:
                # For numeric predictions, use mean
                mean_prediction = np.mean(predictions)
                mean_confidence = np.mean(confidences)
                
                return {
                    'prediction': mean_prediction,
                    'confidence': mean_confidence,
                    'lower_bound': np.percentile(predictions, 25),
                    'upper_bound': np.percentile(predictions, 75)
                }
        
        except Exception as e:
            self.logger.error(f"Voting ensemble failed: {e}")
            return {'prediction': predictions[0] if predictions else 0, 'confidence': 0.3}
    
    def _weighted_voting_ensemble(self, models: List[str], predictions: List[Any], confidences: List[float], pred_type: PredictionType) -> Dict[str, Any]:
        """Weighted voting based on model performance and confidence"""
        try:
            # Get model weights based on historical performance
            weights = []
            for i, model_id in enumerate(models):
                base_weight = confidences[i]
                
                # Adjust weight based on historical performance
                if model_id in self.model_performance:
                    perf_data = self.model_performance[model_id]
                    historical_accuracy = perf_data.get('accuracy', 0.5)
                    performance_weight = base_weight * (0.5 + historical_accuracy)
                else:
                    performance_weight = base_weight
                
                weights.append(performance_weight)
            
            # Normalize weights
            total_weight = sum(weights)
            if total_weight > 0:
                weights = [w / total_weight for w in weights]
            else:
                weights = [1.0 / len(models)] * len(models)
            
            if pred_type == PredictionType.PRICE_DIRECTION:
                # Weighted voting for directions
                direction_weights = {}
                for pred, weight in zip(predictions, weights):
                    direction_weights[pred] = direction_weights.get(pred, 0) + weight
                
                best_direction = max(direction_weights.items(), key=lambda x: x[1])[0]
                confidence = direction_weights[best_direction]
                
                return {
                    'prediction': best_direction,
                    'confidence': confidence
                }
            else:
                # Weighted average for numeric predictions
                weighted_prediction = np.average(predictions, weights=weights)
                weighted_confidence = np.average(confidences, weights=weights)
                
                # Calculate prediction bounds
                std_dev = np.sqrt(np.average((predictions - weighted_prediction)**2, weights=weights))
                
                return {
                    'prediction': weighted_prediction,
                    'confidence': weighted_confidence,
                    'lower_bound': weighted_prediction - (1.96 * std_dev),
                    'upper_bound': weighted_prediction + (1.96 * std_dev)
                }
        
        except Exception as e:
            self.logger.error(f"Weighted voting ensemble failed: {e}")
            return self._voting_ensemble(models, predictions, confidences, pred_type)
    
    def _stacking_ensemble(self, models: List[str], predictions: List[Any], confidences: List[float], pred_type: PredictionType) -> Dict[str, Any]:
        """Stacking ensemble using a meta-learner (simplified version)"""
        try:
            # For now, use weighted voting as a simplified stacking approach
            # In a full implementation, this would train a meta-model
            return self._weighted_voting_ensemble(models, predictions, confidences, pred_type)
        
        except Exception as e:
            self.logger.error(f"Stacking ensemble failed: {e}")
            return self._voting_ensemble(models, predictions, confidences, pred_type)
    
    def _blending_ensemble(self, models: List[str], predictions: List[Any], confidences: List[float], pred_type: PredictionType) -> Dict[str, Any]:
        """Blending ensemble with holdout validation weights"""
        try:
            # Simplified blending - use confidence-based weighting
            return self._weighted_voting_ensemble(models, predictions, confidences, pred_type)
        
        except Exception as e:
            self.logger.error(f"Blending ensemble failed: {e}")
            return self._voting_ensemble(models, predictions, confidences, pred_type)
    
    def _calculate_uncertainty_metrics(self, predictions: List[Any], confidences: List[float]) -> Dict[str, float]:
        """Calculate uncertainty metrics for ensemble predictions"""
        try:
            uncertainty = {}
            
            # Model disagreement (variance in predictions)
            if len(predictions) > 1:
                if all(isinstance(p, (int, float)) for p in predictions):
                    pred_variance = np.var(predictions)
                    uncertainty['prediction_variance'] = float(pred_variance)
                    uncertainty['model_disagreement'] = min(1.0, pred_variance / np.mean(predictions)**2) if np.mean(predictions) != 0 else 0.0
                else:
                    # For categorical predictions, measure disagreement
                    unique_predictions = len(set(predictions))
                    uncertainty['model_disagreement'] = (unique_predictions - 1) / max(1, len(predictions) - 1)
                    uncertainty['prediction_variance'] = uncertainty['model_disagreement']
            else:
                uncertainty['model_disagreement'] = 0.0
                uncertainty['prediction_variance'] = 0.0
            
            # Confidence spread
            if len(confidences) > 1:
                conf_std = np.std(confidences)
                uncertainty['confidence_spread'] = float(conf_std)
            else:
                uncertainty['confidence_spread'] = 0.0
            
            # Overall uncertainty score
            uncertainty['overall_uncertainty'] = (
                uncertainty['model_disagreement'] * 0.4 +
                uncertainty['prediction_variance'] * 0.3 +
                uncertainty['confidence_spread'] * 0.3
            )
            
            return uncertainty
        
        except Exception as e:
            self.logger.error(f"Error calculating uncertainty metrics: {e}")
            return {'model_disagreement': 0.5, 'prediction_variance': 0.5, 'confidence_spread': 0.5, 'overall_uncertainty': 0.5}
    
    def update_model_performance(self, model_id: str, accuracy: float, prediction_type: PredictionType):
        """Update model performance tracking for dynamic weighting"""
        try:
            if model_id not in self.model_performance:
                self.model_performance[model_id] = {
                    'accuracy': accuracy,
                    'prediction_count': 1,
                    'type_performance': {prediction_type.value: accuracy}
                }
            else:
                perf_data = self.model_performance[model_id]
                
                # Update overall accuracy (exponential moving average)
                alpha = 0.1  # Learning rate
                perf_data['accuracy'] = (1 - alpha) * perf_data['accuracy'] + alpha * accuracy
                perf_data['prediction_count'] += 1
                
                # Update type-specific performance
                if prediction_type.value not in perf_data['type_performance']:
                    perf_data['type_performance'][prediction_type.value] = accuracy
                else:
                    perf_data['type_performance'][prediction_type.value] = (
                        (1 - alpha) * perf_data['type_performance'][prediction_type.value] + alpha * accuracy
                    )
        
        except Exception as e:
            self.logger.error(f"Error updating model performance: {e}")
    
    def get_model_rankings(self, prediction_type: Optional[PredictionType] = None) -> List[Tuple[str, float]]:
        """Get model rankings by performance"""
        try:
            rankings = []
            
            for model_id, perf_data in self.model_performance.items():
                if prediction_type:
                    # Type-specific performance
                    score = perf_data['type_performance'].get(prediction_type.value, perf_data['accuracy'])
                else:
                    # Overall performance
                    score = perf_data['accuracy']
                
                rankings.append((model_id, score))
            
            # Sort by performance (descending)
            rankings.sort(key=lambda x: x[1], reverse=True)
            
            return rankings
        
        except Exception as e:
            self.logger.error(f"Error getting model rankings: {e}")
            return []


# Export main classes
__all__ = [
    'PredictionType',
    'PredictionHorizon',
    'PredictionConfidence',
    'MarketPrediction',
    'FeatureEngineer',
    'PredictionEngine',
    'EnsemblePredictionEngine'
]


class EnsemblePredictionEngine(PredictionEngine):
    """
    Enhanced prediction engine with advanced ensemble methods
    
    Features:
    - Multiple ensemble strategies
    - Dynamic model weighting
    - Uncertainty quantification
    - Multi-timeframe predictions
    - Real-time model performance tracking
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Enhanced ensemble configuration
        self.ensemble_strategies = {
            'weighted_average': self._weighted_average_ensemble,
            'stacking': self._stacking_ensemble,
            'bayesian': self._bayesian_ensemble,
            'dynamic_weighting': self._dynamic_weighting_ensemble
        }
        
        # Model performance tracking
        self.model_performance = {}
        self.model_weights = {}
        
        # Advanced features
        self.uncertainty_quantification = True
        self.multi_timeframe_analysis = True
        self.adaptive_learning = True
        
        # Real-time performance metrics
        self.real_time_metrics = {
            'prediction_latency': [],
            'model_response_times': {},
            'ensemble_accuracy': [],
            'uncertainty_calibration': []
        }
    
    async def predict_with_ensemble(self,
                                  symbol: str,
                                  data: pd.DataFrame,
                                  prediction_type: PredictionType,
                                  horizon: PredictionHorizon = PredictionHorizon.SHORT_TERM,
                                  ensemble_strategy: str = 'dynamic_weighting') -> MarketPrediction:
        """
        Make prediction using advanced ensemble methods
        
        Args:
            symbol: Trading symbol
            data: Historical OHLCV data
            prediction_type: Type of prediction to make
            horizon: Prediction time horizon
            ensemble_strategy: Ensemble strategy to use
            
        Returns:
            Enhanced ensemble prediction
        """
        start_time = time.time()
        
        try:
            # Prepare features
            features = await self._prepare_enhanced_features(symbol, data, horizon)
            
            # Get relevant models
            models = self._get_models_for_prediction(prediction_type)
            
            if not models:
                # Fallback to base prediction
                return await self._fallback_prediction(symbol, data, prediction_type, horizon)
            
            # Collect predictions from all models
            model_predictions = await self._collect_model_predictions(models, features, prediction_type)
            
            if not model_predictions:
                return await self._fallback_prediction(symbol, data, prediction_type, horizon)
            
            # Apply ensemble strategy
            ensemble_func = self.ensemble_strategies.get(ensemble_strategy, self._weighted_average_ensemble)
            ensemble_result = await ensemble_func(model_predictions, prediction_type)
            
            # Quantify uncertainty
            uncertainty_metrics = self._quantify_uncertainty(model_predictions, ensemble_result)
            
            # Create enhanced prediction
            prediction = MarketPrediction(
                symbol=symbol,
                prediction_type=prediction_type,
                horizon=horizon,
                predicted_value=ensemble_result['prediction'],
                confidence=ensemble_result['confidence'],
                probability=ensemble_result.get('probability'),
                lower_bound=uncertainty_metrics.get('lower_bound'),
                upper_bound=uncertainty_metrics.get('upper_bound'),
                model_ensemble=models,
                features_used=list(features.keys()) if isinstance(features, dict) else [],
                feature_importance=ensemble_result.get('feature_importance', {}),
                current_price=data['close'].iloc[-1] if len(data) > 0 else None,
                market_conditions=self._analyze_market_conditions(data),
                expiry_time=self._calculate_expiry_time(horizon)
            )
            
            # Add ensemble-specific metadata
            prediction.metadata = {
                'ensemble_strategy': ensemble_strategy,
                'model_count': len(models),
                'uncertainty_metrics': uncertainty_metrics,
                'prediction_latency_ms': (time.time() - start_time) * 1000,
                'model_weights': ensemble_result.get('model_weights', {}),
                'consensus_score': ensemble_result.get('consensus_score', 0.0)
            }
            
            # Store prediction and update metrics
            self._store_prediction(prediction)
            self._update_real_time_metrics(prediction, start_time)
            
            return prediction
        
        except Exception as e:
            self.logger.error(f"Ensemble prediction failed for {symbol}: {e}")
            return await self._fallback_prediction(symbol, data, prediction_type, horizon)
    
    async def _prepare_enhanced_features(self, symbol: str, data: pd.DataFrame, horizon: PredictionHorizon) -> Dict[str, Any]:
        """Prepare enhanced features including multi-timeframe analysis"""
        features = await self._prepare_features(symbol, data)
        
        try:
            # Add horizon-specific features
            features['prediction_horizon'] = horizon.value
            features['horizon_numeric'] = self._horizon_to_numeric(horizon)
            
            # Multi-timeframe features
            if self.multi_timeframe_analysis and len(data) >= 100:
                # Short-term features (5-20 periods)
                short_term_features = self._extract_timeframe_features(data, 'short', [5, 10, 20])
                features.update({f'st_{k}': v for k, v in short_term_features.items()})
                
                # Medium-term features (20-50 periods)
                medium_term_features = self._extract_timeframe_features(data, 'medium', [20, 30, 50])
                features.update({f'mt_{k}': v for k, v in medium_term_features.items()})
                
                # Long-term features (50-200 periods)
                if len(data) >= 200:
                    long_term_features = self._extract_timeframe_features(data, 'long', [50, 100, 200])
                    features.update({f'lt_{k}': v for k, v in long_term_features.items()})
            
            # Market microstructure features
            microstructure_features = self._extract_microstructure_features(data)
            features.update(microstructure_features)
            
            # Regime detection features
            regime_features = self._extract_regime_features(data)
            features.update(regime_features)
            
        except Exception as e:
            self.logger.error(f"Error preparing enhanced features: {e}")
        
        return features
    
    def _extract_timeframe_features(self, data: pd.DataFrame, timeframe: str, windows: List[int]) -> Dict[str, float]:
        """Extract features for specific timeframe"""
        features = {}
        
        try:
            for window in windows:
                if len(data) >= window:
                    # Price momentum
                    price_change = (data['close'].iloc[-1] - data['close'].iloc[-window]) / data['close'].iloc[-window]
                    features[f'{timeframe}_momentum_{window}'] = price_change
                    
                    # Volatility
                    returns = data['close'].pct_change().dropna()
                    if len(returns) >= window:
                        vol = returns.tail(window).std()
                        features[f'{timeframe}_volatility_{window}'] = vol
                    
                    # Volume trend
                    if 'volume' in data.columns:
                        volume_trend = data['volume'].tail(window).mean() / data['volume'].tail(window*2).head(window).mean()
                        features[f'{timeframe}_volume_trend_{window}'] = volume_trend if not np.isnan(volume_trend) else 1.0
        
        except Exception as e:
            self.logger.error(f"Error extracting {timeframe} timeframe features: {e}")
        
        return features
    
    def _extract_microstructure_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract market microstructure features"""
        features = {}
        
        try:
            if len(data) >= 20:
                # Bid-ask spread proxy (high-low range)
                spread_proxy = (data['high'] - data['low']) / data['close']
                features['avg_spread_proxy'] = spread_proxy.tail(20).mean()
                features['spread_volatility'] = spread_proxy.tail(20).std()
                
                # Price impact proxy
                if 'volume' in data.columns:
                    returns = data['close'].pct_change().abs()
                    volume_normalized = data['volume'] / data['volume'].rolling(20).mean()
                    
                    # Correlation between returns and volume
                    if len(returns) >= 20:
                        price_impact = returns.tail(20).corr(volume_normalized.tail(20))
                        features['price_impact_proxy'] = price_impact if not np.isnan(price_impact) else 0.0
                
                # Market efficiency proxy (autocorrelation)
                returns = data['close'].pct_change().dropna()
                if len(returns) >= 20:
                    autocorr = returns.tail(20).autocorr(lag=1)
                    features['market_efficiency'] = 1.0 - abs(autocorr) if not np.isnan(autocorr) else 1.0
        
        except Exception as e:
            self.logger.error(f"Error extracting microstructure features: {e}")
        
        return features
    
    def _extract_regime_features(self, data: pd.DataFrame) -> Dict[str, float]:
        """Extract market regime features"""
        features = {}
        
        try:
            if len(data) >= 50:
                returns = data['close'].pct_change().dropna()
                
                # Volatility regime
                short_vol = returns.tail(10).std()
                long_vol = returns.tail(50).std()
                features['volatility_regime'] = short_vol / long_vol if long_vol > 0 else 1.0
                
                # Trend regime
                short_trend = returns.tail(10).mean()
                long_trend = returns.tail(50).mean()
                features['trend_regime'] = short_trend / long_trend if abs(long_trend) > 1e-6 else 0.0
                
                # Mean reversion regime
                if len(returns) >= 20:
                    # Hurst exponent approximation
                    lags = range(2, min(20, len(returns)//2))
                    tau = [np.sqrt(np.std(np.subtract(returns[lag:], returns[:-lag]))) for lag in lags]
                    
                    if len(tau) > 1:
                        # Simple linear regression for Hurst exponent
                        log_lags = np.log(lags)
                        log_tau = np.log(tau)
                        
                        if len(log_lags) == len(log_tau) and np.std(log_lags) > 0:
                            hurst = np.corrcoef(log_lags, log_tau)[0, 1] if not np.isnan(np.corrcoef(log_lags, log_tau)[0, 1]) else 0.5
                            features['mean_reversion_regime'] = hurst
        
        except Exception as e:
            self.logger.error(f"Error extracting regime features: {e}")
        
        return features
    
    async def _collect_model_predictions(self, models: List[str], features: Dict[str, Any], prediction_type: PredictionType) -> List[Dict[str, Any]]:
        """Collect predictions from all models"""
        predictions = []
        
        # Create prediction tasks
        tasks = []
        for model_id in models:
            task = self._get_model_prediction(model_id, features, prediction_type)
            tasks.append((model_id, task))
        
        # Execute predictions concurrently
        for model_id, task in tasks:
            try:
                result = await task
                if result:
                    predictions.append({
                        'model_id': model_id,
                        'prediction': result['prediction'],
                        'confidence': result['confidence'],
                        'response_time': result.get('response_time', 0),
                        'feature_importance': result.get('feature_importance', {})
                    })
            except Exception as e:
                self.logger.warning(f"Model {model_id} prediction failed: {e}")
        
        return predictions
    
    async def _get_model_prediction(self, model_id: str, features: Dict[str, Any], prediction_type: PredictionType) -> Optional[Dict[str, Any]]:
        """Get prediction from a single model"""
        start_time = time.time()
        
        try:
            result = await self.inference_engine.predict(
                model_id=model_id,
                input_data=features,
                priority=InferencePriority.HIGH
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if result.success:
                return {
                    'prediction': result.prediction,
                    'confidence': result.confidence or 0.5,
                    'response_time': response_time,
                    'feature_importance': result.feature_importance or {}
                }
        
        except Exception as e:
            self.logger.error(f"Model {model_id} prediction error: {e}")
        
        return None
    
    async def _weighted_average_ensemble(self, predictions: List[Dict[str, Any]], prediction_type: PredictionType) -> Dict[str, Any]:
        """Weighted average ensemble method"""
        if not predictions:
            return {'prediction': 0.0, 'confidence': 0.0}
        
        # Use confidence as weights
        weights = np.array([p['confidence'] for p in predictions])
        weights = weights / weights.sum() if weights.sum() > 0 else np.ones(len(weights)) / len(weights)
        
        # Weighted prediction
        pred_values = np.array([p['prediction'] for p in predictions])
        weighted_prediction = np.average(pred_values, weights=weights)
        
        # Weighted confidence
        weighted_confidence = np.average([p['confidence'] for p in predictions], weights=weights)
        
        # Consensus score (agreement between models)
        consensus_score = 1.0 - (np.std(pred_values) / (np.mean(np.abs(pred_values)) + 1e-6))
        consensus_score = max(0.0, min(1.0, consensus_score))
        
        return {
            'prediction': weighted_prediction,
            'confidence': weighted_confidence,
            'consensus_score': consensus_score,
            'model_weights': {p['model_id']: w for p, w in zip(predictions, weights)}
        }
    
    async def _stacking_ensemble(self, predictions: List[Dict[str, Any]], prediction_type: PredictionType) -> Dict[str, Any]:
        """Stacking ensemble method (simplified)"""
        # For now, use weighted average with performance-based weights
        return await self._weighted_average_ensemble(predictions, prediction_type)
    
    async def _bayesian_ensemble(self, predictions: List[Dict[str, Any]], prediction_type: PredictionType) -> Dict[str, Any]:
        """Bayesian ensemble method (simplified)"""
        if not predictions:
            return {'prediction': 0.0, 'confidence': 0.0}
        
        # Use confidence as precision (inverse variance)
        precisions = np.array([p['confidence'] for p in predictions])
        pred_values = np.array([p['prediction'] for p in predictions])
        
        # Bayesian weighted average
        total_precision = np.sum(precisions)
        if total_precision > 0:
            bayesian_mean = np.sum(pred_values * precisions) / total_precision
            bayesian_confidence = min(1.0, total_precision / len(predictions))
        else:
            bayesian_mean = np.mean(pred_values)
            bayesian_confidence = 0.5
        
        return {
            'prediction': bayesian_mean,
            'confidence': bayesian_confidence,
            'consensus_score': 1.0 - (np.std(pred_values) / (np.mean(np.abs(pred_values)) + 1e-6))
        }
    
    async def _dynamic_weighting_ensemble(self, predictions: List[Dict[str, Any]], prediction_type: PredictionType) -> Dict[str, Any]:
        """Dynamic weighting based on recent model performance"""
        if not predictions:
            return {'prediction': 0.0, 'confidence': 0.0}
        
        # Get dynamic weights based on recent performance
        dynamic_weights = []
        for pred in predictions:
            model_id = pred['model_id']
            
            # Get recent performance for this model
            recent_performance = self._get_recent_model_performance(model_id, prediction_type)
            
            # Combine confidence with recent performance
            base_weight = pred['confidence']
            performance_weight = recent_performance.get('accuracy', 0.5)
            
            # Dynamic weight combines current confidence with historical performance
            dynamic_weight = 0.6 * base_weight + 0.4 * performance_weight
            dynamic_weights.append(dynamic_weight)
        
        # Normalize weights
        dynamic_weights = np.array(dynamic_weights)
        dynamic_weights = dynamic_weights / dynamic_weights.sum() if dynamic_weights.sum() > 0 else np.ones(len(dynamic_weights)) / len(dynamic_weights)
        
        # Weighted prediction
        pred_values = np.array([p['prediction'] for p in predictions])
        weighted_prediction = np.average(pred_values, weights=dynamic_weights)
        
        # Weighted confidence
        weighted_confidence = np.average([p['confidence'] for p in predictions], weights=dynamic_weights)
        
        return {
            'prediction': weighted_prediction,
            'confidence': weighted_confidence,
            'consensus_score': 1.0 - (np.std(pred_values) / (np.mean(np.abs(pred_values)) + 1e-6)),
            'model_weights': {p['model_id']: w for p, w in zip(predictions, dynamic_weights)}
        }
    
    def _quantify_uncertainty(self, predictions: List[Dict[str, Any]], ensemble_result: Dict[str, Any]) -> Dict[str, float]:
        """Quantify prediction uncertainty"""
        if not predictions:
            return {'uncertainty': 1.0, 'lower_bound': 0.0, 'upper_bound': 0.0}
        
        pred_values = np.array([p['prediction'] for p in predictions])
        confidences = np.array([p['confidence'] for p in predictions])
        
        # Model disagreement
        disagreement = np.std(pred_values)
        
        # Confidence-weighted uncertainty
        avg_confidence = np.mean(confidences)
        uncertainty = (1.0 - avg_confidence) + (disagreement / (np.mean(np.abs(pred_values)) + 1e-6))
        uncertainty = min(1.0, uncertainty)
        
        # Confidence intervals (simplified)
        ensemble_pred = ensemble_result['prediction']
        margin = disagreement * 1.96  # 95% confidence interval
        
        return {
            'uncertainty': uncertainty,
            'disagreement': disagreement,
            'lower_bound': ensemble_pred - margin,
            'upper_bound': ensemble_pred + margin,
            'confidence_interval_width': 2 * margin
        }
    
    def _analyze_market_conditions(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze current market conditions"""
        conditions = {}
        
        try:
            if len(data) >= 20:
                returns = data['close'].pct_change().dropna()
                
                # Volatility condition
                current_vol = returns.tail(5).std()
                avg_vol = returns.tail(20).std()
                conditions['volatility_regime'] = 'high' if current_vol > avg_vol * 1.5 else 'normal' if current_vol > avg_vol * 0.5 else 'low'
                
                # Trend condition
                sma_5 = data['close'].rolling(5).mean().iloc[-1]
                sma_20 = data['close'].rolling(20).mean().iloc[-1]
                current_price = data['close'].iloc[-1]
                
                if current_price > sma_5 > sma_20:
                    conditions['trend'] = 'uptrend'
                elif current_price < sma_5 < sma_20:
                    conditions['trend'] = 'downtrend'
                else:
                    conditions['trend'] = 'sideways'
                
                # Market efficiency
                if len(returns) >= 10:
                    autocorr = returns.tail(10).autocorr(lag=1)
                    conditions['efficiency'] = 'efficient' if abs(autocorr) < 0.1 else 'inefficient'
        
        except Exception as e:
            self.logger.error(f"Error analyzing market conditions: {e}")
        
        return conditions
    
    def _get_recent_model_performance(self, model_id: str, prediction_type: PredictionType) -> Dict[str, float]:
        """Get recent performance metrics for a model"""
        if model_id not in self.model_performance:
            return {'accuracy': 0.5, 'count': 0}
        
        model_perf = self.model_performance[model_id]
        type_key = prediction_type.value
        
        if type_key in model_perf:
            return model_perf[type_key]
        else:
            return {'accuracy': 0.5, 'count': 0}
    
    def _update_real_time_metrics(self, prediction: MarketPrediction, start_time: float):
        """Update real-time performance metrics"""
        latency = (time.time() - start_time) * 1000
        self.real_time_metrics['prediction_latency'].append(latency)
        
        # Limit metrics history
        if len(self.real_time_metrics['prediction_latency']) > 1000:
            self.real_time_metrics['prediction_latency'] = self.real_time_metrics['prediction_latency'][-1000:]
    
    def _horizon_to_numeric(self, horizon: PredictionHorizon) -> float:
        """Convert horizon to numeric value for features"""
        mapping = {
            PredictionHorizon.INTRADAY: 0.25,
            PredictionHorizon.SHORT_TERM: 1.0,
            PredictionHorizon.MEDIUM_TERM: 4.0,
            PredictionHorizon.LONG_TERM: 12.0
        }
        return mapping.get(horizon, 1.0)
    
    async def _fallback_prediction(self, symbol: str, data: pd.DataFrame, prediction_type: PredictionType, horizon: PredictionHorizon) -> MarketPrediction:
        """Fallback prediction when ensemble fails"""
        if prediction_type == PredictionType.PRICE_DIRECTION:
            return await self._fallback_direction_prediction(symbol, data, horizon)
        elif prediction_type == PredictionType.PRICE_TARGET:
            return await self._fallback_price_target(symbol, data, horizon)
        elif prediction_type == PredictionType.VOLATILITY:
            current_vol = data['close'].pct_change().std() if len(data) > 1 else 0.02
            return await self._fallback_volatility_prediction(symbol, data, horizon, current_vol)
        else:
            # Generic fallback
            return MarketPrediction(
                symbol=symbol,
                prediction_type=prediction_type,
                horizon=horizon,
                predicted_value=0.0,
                confidence=0.2,
                expiry_time=self._calculate_expiry_time(horizon)
            )
    
    def get_ensemble_metrics(self) -> Dict[str, Any]:
        """Get ensemble-specific performance metrics"""
        base_metrics = self.get_accuracy_metrics()
        
        # Add ensemble-specific metrics
        ensemble_metrics = {
            'avg_prediction_latency_ms': np.mean(self.real_time_metrics['prediction_latency']) if self.real_time_metrics['prediction_latency'] else 0,
            'model_count': len(self.model_registry),
            'active_predictions': len(self.get_active_predictions()),
            'ensemble_strategies': list(self.ensemble_strategies.keys())
        }
        
        # Model performance breakdown
        model_performance_summary = {}
        for model_id, perf in self.model_performance.items():
            model_performance_summary[model_id] = {
                'avg_accuracy': np.mean([metrics['accuracy'] for metrics in perf.values()]) if perf else 0.0,
                'prediction_types': list(perf.keys())
            }
        
        return {
            **base_metrics,
            **ensemble_metrics,
            'model_performance': model_performance_summary
        }


# Export classes
__all__ = [
    'PredictionType',
    'PredictionHorizon', 
    'PredictionConfidence',
    'MarketPrediction',
    'FeatureEngineer',
    'PredictionEngine',
    'EnsemblePredictionEngine'
]