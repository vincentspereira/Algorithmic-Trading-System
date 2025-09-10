#!/usr/bin/env python3
"""
Feature Engineering Module for ML Trading Strategies

This module provides comprehensive feature engineering capabilities for machine learning
trading strategies, including technical indicators, market microstructure features,
sentiment analysis, and feature selection/preprocessing.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from abc import ABC, abstractmethod

# Technical analysis imports
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False

from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.feature_selection import SelectKBest, f_regression, mutual_info_regression
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestRegressor


class FeatureType(Enum):
    """Types of features that can be extracted"""
    TECHNICAL = "technical"
    MICROSTRUCTURE = "microstructure"
    SENTIMENT = "sentiment"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    CROSS_ASSET = "cross_asset"
    REGIME = "regime"
    VOLATILITY = "volatility"


class ScalingMethod(Enum):
    """Feature scaling methods"""
    STANDARD = "standard"
    MINMAX = "minmax"
    ROBUST = "robust"
    NONE = "none"


@dataclass
class FeatureConfig:
    """Configuration for feature engineering"""
    # Feature types to extract
    feature_types: List[FeatureType] = field(default_factory=lambda: [FeatureType.TECHNICAL])
    
    # Technical indicator parameters
    technical_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 50])
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bollinger_period: int = 20
    bollinger_std: float = 2.0
    
    # Microstructure parameters
    volume_periods: List[int] = field(default_factory=lambda: [5, 10, 20])
    spread_periods: List[int] = field(default_factory=lambda: [5, 10])
    
    # Feature selection
    feature_selection: bool = True
    max_features: Optional[int] = 50
    selection_method: str = "mutual_info"  # 'f_regression', 'mutual_info', 'random_forest'
    
    # Scaling
    scaling_method: ScalingMethod = ScalingMethod.STANDARD
    
    # Lag features
    create_lags: bool = True
    max_lags: int = 5
    
    # Rolling window features
    rolling_windows: List[int] = field(default_factory=lambda: [5, 10, 20])
    
    # Target encoding
    target_encoding: bool = False
    

@dataclass
class FeatureImportance:
    """Feature importance information"""
    feature_name: str
    importance_score: float
    feature_type: FeatureType
    description: str
    

class BaseFeatureExtractor(ABC):
    """Base class for feature extractors"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features from market data"""
        pass
    
    @abstractmethod
    def get_feature_names(self) -> List[str]:
        """Get list of feature names this extractor produces"""
        pass


class TechnicalFeatureExtractor(BaseFeatureExtractor):
    """Extract technical analysis features"""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract technical indicators"""
        features = pd.DataFrame(index=data.index)
        
        # Price-based features
        features['returns'] = data['close'].pct_change()
        features['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        
        # Moving averages
        for period in self.config.technical_periods:
            features[f'sma_{period}'] = data['close'].rolling(period).mean()
            features[f'ema_{period}'] = data['close'].ewm(span=period).mean()
            features[f'price_to_sma_{period}'] = data['close'] / features[f'sma_{period}']
            
        # Volatility features
        for period in self.config.technical_periods:
            features[f'volatility_{period}'] = features['returns'].rolling(period).std()
            features[f'realized_vol_{period}'] = np.sqrt(252) * features[f'volatility_{period}']
            
        # RSI
        if TALIB_AVAILABLE:
            features['rsi'] = talib.RSI(data['close'].values, timeperiod=self.config.rsi_period)
        else:
            features['rsi'] = self._calculate_rsi(data['close'], self.config.rsi_period)
            
        # MACD
        if TALIB_AVAILABLE:
            macd, macd_signal, macd_hist = talib.MACD(
                data['close'].values,
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow,
                signalperiod=self.config.macd_signal
            )
            features['macd'] = macd
            features['macd_signal'] = macd_signal
            features['macd_histogram'] = macd_hist
        else:
            macd_data = self._calculate_macd(data['close'])
            features = pd.concat([features, macd_data], axis=1)
            
        # Bollinger Bands
        bb_data = self._calculate_bollinger_bands(data['close'])
        features = pd.concat([features, bb_data], axis=1)
        
        # Volume features
        if 'volume' in data.columns:
            features['volume_sma_20'] = data['volume'].rolling(20).mean()
            features['volume_ratio'] = data['volume'] / features['volume_sma_20']
            features['price_volume'] = data['close'] * data['volume']
            
        # High-Low features
        if all(col in data.columns for col in ['high', 'low']):
            features['high_low_ratio'] = data['high'] / data['low']
            features['price_position'] = (data['close'] - data['low']) / (data['high'] - data['low'])
            
        return features
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI manually if talib not available"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> pd.DataFrame:
        """Calculate MACD manually if talib not available"""
        ema_fast = prices.ewm(span=self.config.macd_fast).mean()
        ema_slow = prices.ewm(span=self.config.macd_slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=self.config.macd_signal).mean()
        macd_histogram = macd - macd_signal
        
        return pd.DataFrame({
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram
        })
    
    def _calculate_bollinger_bands(self, prices: pd.Series) -> pd.DataFrame:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(self.config.bollinger_period).mean()
        std = prices.rolling(self.config.bollinger_period).std()
        
        upper_band = sma + (std * self.config.bollinger_std)
        lower_band = sma - (std * self.config.bollinger_std)
        
        return pd.DataFrame({
            'bb_upper': upper_band,
            'bb_lower': lower_band,
            'bb_middle': sma,
            'bb_width': (upper_band - lower_band) / sma,
            'bb_position': (prices - lower_band) / (upper_band - lower_band)
        })
    
    def get_feature_names(self) -> List[str]:
        """Get list of technical feature names"""
        names = ['returns', 'log_returns', 'rsi', 'macd', 'macd_signal', 'macd_histogram']
        
        for period in self.config.technical_periods:
            names.extend([
                f'sma_{period}', f'ema_{period}', f'price_to_sma_{period}',
                f'volatility_{period}', f'realized_vol_{period}'
            ])
            
        names.extend(['bb_upper', 'bb_lower', 'bb_middle', 'bb_width', 'bb_position'])
        names.extend(['volume_sma_20', 'volume_ratio', 'price_volume'])
        names.extend(['high_low_ratio', 'price_position'])
        
        return names


class MicrostructureFeatureExtractor(BaseFeatureExtractor):
    """Extract market microstructure features"""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract microstructure features"""
        features = pd.DataFrame(index=data.index)
        
        # Spread features (if bid/ask available)
        if all(col in data.columns for col in ['bid', 'ask']):
            features['bid_ask_spread'] = data['ask'] - data['bid']
            features['relative_spread'] = features['bid_ask_spread'] / ((data['bid'] + data['ask']) / 2)
            features['mid_price'] = (data['bid'] + data['ask']) / 2
            features['price_to_mid'] = data['close'] / features['mid_price']
            
        # Volume-based features
        if 'volume' in data.columns:
            for period in self.config.volume_periods:
                features[f'volume_ma_{period}'] = data['volume'].rolling(period).mean()
                features[f'volume_std_{period}'] = data['volume'].rolling(period).std()
                features[f'volume_zscore_{period}'] = (
                    (data['volume'] - features[f'volume_ma_{period}']) / features[f'volume_std_{period}']
                )
                
        # Price impact features
        if all(col in data.columns for col in ['volume', 'close']):
            features['vwap'] = (data['close'] * data['volume']).rolling(20).sum() / data['volume'].rolling(20).sum()
            features['price_to_vwap'] = data['close'] / features['vwap']
            
        # Tick-based features (if tick data available)
        if 'tick_direction' in data.columns:
            features['tick_imbalance'] = data['tick_direction'].rolling(10).mean()
            
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of microstructure feature names"""
        names = ['bid_ask_spread', 'relative_spread', 'mid_price', 'price_to_mid']
        
        for period in self.config.volume_periods:
            names.extend([
                f'volume_ma_{period}', f'volume_std_{period}', f'volume_zscore_{period}'
            ])
            
        names.extend(['vwap', 'price_to_vwap', 'tick_imbalance'])
        return names


class SentimentFeatureExtractor(BaseFeatureExtractor):
    """Extract sentiment-based features"""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract sentiment features"""
        features = pd.DataFrame(index=data.index)
        
        # VIX-based features (if available)
        if 'vix' in data.columns:
            features['vix'] = data['vix']
            features['vix_ma_20'] = data['vix'].rolling(20).mean()
            features['vix_zscore'] = (data['vix'] - features['vix_ma_20']) / data['vix'].rolling(20).std()
            
        # Put/Call ratio (if available)
        if 'put_call_ratio' in data.columns:
            features['put_call_ratio'] = data['put_call_ratio']
            features['put_call_ma'] = data['put_call_ratio'].rolling(10).mean()
            
        return features
    
    def get_feature_names(self) -> List[str]:
        """Get list of sentiment feature names"""
        return ['vix', 'vix_ma_20', 'vix_zscore', 'put_call_ratio', 'put_call_ma']


class FeatureEngineeringPipeline:
    """Main feature engineering pipeline"""
    
    def __init__(self, config: FeatureConfig):
        self.config = config
        self.extractors = self._initialize_extractors()
        self.scaler = None
        self.feature_selector = None
        self.selected_features = None
        self.feature_importance_scores = {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _initialize_extractors(self) -> Dict[FeatureType, BaseFeatureExtractor]:
        """Initialize feature extractors based on config"""
        extractors = {}
        
        if FeatureType.TECHNICAL in self.config.feature_types:
            extractors[FeatureType.TECHNICAL] = TechnicalFeatureExtractor(self.config)
            
        if FeatureType.MICROSTRUCTURE in self.config.feature_types:
            extractors[FeatureType.MICROSTRUCTURE] = MicrostructureFeatureExtractor(self.config)
            
        if FeatureType.SENTIMENT in self.config.feature_types:
            extractors[FeatureType.SENTIMENT] = SentimentFeatureExtractor(self.config)
            
        return extractors
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract all configured features"""
        all_features = pd.DataFrame(index=data.index)
        
        # Extract features from each extractor
        for feature_type, extractor in self.extractors.items():
            try:
                features = extractor.extract_features(data)
                # Add prefix to avoid name conflicts
                features = features.add_prefix(f"{feature_type.value}_")
                all_features = pd.concat([all_features, features], axis=1)
                self.logger.info(f"Extracted {len(features.columns)} {feature_type.value} features")
            except Exception as e:
                self.logger.error(f"Error extracting {feature_type.value} features: {e}")
                
        # Create lag features if configured
        if self.config.create_lags:
            lag_features = self._create_lag_features(all_features)
            all_features = pd.concat([all_features, lag_features], axis=1)
            
        # Create rolling window features
        rolling_features = self._create_rolling_features(all_features)
        all_features = pd.concat([all_features, rolling_features], axis=1)
        
        # Remove infinite and NaN values
        all_features = all_features.replace([np.inf, -np.inf], np.nan)
        all_features = all_features.fillna(method='ffill').fillna(0)
        
        self.logger.info(f"Total features extracted: {len(all_features.columns)}")
        return all_features
    
    def _create_lag_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Create lagged versions of features"""
        lag_features = pd.DataFrame(index=features.index)
        
        # Only create lags for a subset of important features to avoid explosion
        important_features = ['technical_returns', 'technical_rsi', 'technical_macd']
        available_features = [col for col in important_features if col in features.columns]
        
        for feature in available_features:
            for lag in range(1, self.config.max_lags + 1):
                lag_features[f"{feature}_lag_{lag}"] = features[feature].shift(lag)
                
        return lag_features
    
    def _create_rolling_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """Create rolling window statistics"""
        rolling_features = pd.DataFrame(index=features.index)
        
        # Select subset of features for rolling calculations
        numeric_features = features.select_dtypes(include=[np.number]).columns[:10]  # Limit to first 10
        
        for window in self.config.rolling_windows:
            for feature in numeric_features:
                rolling_features[f"{feature}_roll_mean_{window}"] = features[feature].rolling(window).mean()
                rolling_features[f"{feature}_roll_std_{window}"] = features[feature].rolling(window).std()
                
        return rolling_features
    
    def preprocess_features(self, features: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        """Preprocess features (scaling, selection)"""
        processed_features = features.copy()
        
        # Feature selection
        if self.config.feature_selection and self.config.max_features:
            if fit:
                processed_features = self._fit_feature_selection(processed_features)
            else:
                processed_features = self._transform_feature_selection(processed_features)
                
        # Scaling
        if self.config.scaling_method != ScalingMethod.NONE:
            if fit:
                processed_features = self._fit_scaling(processed_features)
            else:
                processed_features = self._transform_scaling(processed_features)
                
        return processed_features
    
    def _fit_feature_selection(self, features: pd.DataFrame, target: Optional[pd.Series] = None) -> pd.DataFrame:
        """Fit feature selection"""
        if target is None:
            # Use variance-based selection if no target provided
            variances = features.var()
            self.selected_features = variances.nlargest(self.config.max_features).index.tolist()
        else:
            # Use supervised feature selection
            if self.config.selection_method == "mutual_info":
                selector = SelectKBest(score_func=mutual_info_regression, k=self.config.max_features)
            else:
                selector = SelectKBest(score_func=f_regression, k=self.config.max_features)
                
            selector.fit(features, target)
            self.feature_selector = selector
            self.selected_features = features.columns[selector.get_support()].tolist()
            
        return features[self.selected_features]
    
    def _transform_feature_selection(self, features: pd.DataFrame) -> pd.DataFrame:
        """Transform features using fitted selector"""
        if self.selected_features:
            return features[self.selected_features]
        return features
    
    def _fit_scaling(self, features: pd.DataFrame) -> pd.DataFrame:
        """Fit feature scaling"""
        if self.config.scaling_method == ScalingMethod.STANDARD:
            self.scaler = StandardScaler()
        elif self.config.scaling_method == ScalingMethod.MINMAX:
            self.scaler = MinMaxScaler()
        elif self.config.scaling_method == ScalingMethod.ROBUST:
            self.scaler = RobustScaler()
            
        scaled_features = self.scaler.fit_transform(features)
        return pd.DataFrame(scaled_features, columns=features.columns, index=features.index)
    
    def _transform_scaling(self, features: pd.DataFrame) -> pd.DataFrame:
        """Transform features using fitted scaler"""
        if self.scaler:
            scaled_features = self.scaler.transform(features)
            return pd.DataFrame(scaled_features, columns=features.columns, index=features.index)
        return features
    
    def calculate_feature_importance(self, features: pd.DataFrame, target: pd.Series) -> List[FeatureImportance]:
        """Calculate feature importance using Random Forest"""
        # Use Random Forest to calculate feature importance
        rf = RandomForestRegressor(n_estimators=100, random_state=42)
        rf.fit(features, target)
        
        importance_scores = rf.feature_importances_
        feature_names = features.columns
        
        # Create FeatureImportance objects
        importance_list = []
        for name, score in zip(feature_names, importance_scores):
            # Determine feature type from name prefix
            feature_type = FeatureType.TECHNICAL  # Default
            for ft in FeatureType:
                if name.startswith(ft.value):
                    feature_type = ft
                    break
                    
            importance_list.append(FeatureImportance(
                feature_name=name,
                importance_score=score,
                feature_type=feature_type,
                description=f"Feature importance: {score:.4f}"
            ))
            
        # Sort by importance score
        importance_list.sort(key=lambda x: x.importance_score, reverse=True)
        
        # Store for later use
        self.feature_importance_scores = {fi.feature_name: fi.importance_score for fi in importance_list}
        
        return importance_list
    
    def get_feature_summary(self) -> Dict[str, Any]:
        """Get summary of feature engineering pipeline"""
        return {
            "config": self.config,
            "extractors": list(self.extractors.keys()),
            "selected_features": self.selected_features,
            "scaler_type": type(self.scaler).__name__ if self.scaler else None,
            "feature_count": len(self.selected_features) if self.selected_features else 0
        }


# Global pipeline instance
_feature_pipeline = None


def get_feature_pipeline(config: Optional[FeatureConfig] = None) -> FeatureEngineeringPipeline:
    """Get global feature engineering pipeline instance"""
    global _feature_pipeline
    if _feature_pipeline is None:
        if config is None:
            config = FeatureConfig()
        _feature_pipeline = FeatureEngineeringPipeline(config)
    return _feature_pipeline


def initialize_feature_pipeline(config: FeatureConfig) -> FeatureEngineeringPipeline:
    """Initialize global feature engineering pipeline"""
    global _feature_pipeline
    _feature_pipeline = FeatureEngineeringPipeline(config)
    return _feature_pipeline