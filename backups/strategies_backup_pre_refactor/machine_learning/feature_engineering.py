#!/usr/bin/env python3
"""
Feature Engineering for Machine Learning Strategies

Comprehensive feature extraction and engineering system for machine learning-based
trading strategies. Generates technical, fundamental, and market microstructure
features for predictive modeling.

Key Features:
- Technical Indicators (50+ indicators with multiple timeframes)
- Market Microstructure Features (order flow, volatility patterns)
- Price Action Features (candlestick patterns, support/resistance)
- Volume Analysis Features (volume profile, flow analysis)
- Volatility Features (realized, implied, term structure)
- Momentum Features (trend strength, momentum persistence)
- Mean Reversion Features (deviation metrics, reversion signals)
- Cross-Asset Features (correlation, relative strength)
- Macroeconomic Features (economic indicators, sentiment)
- Feature Selection and Dimensionality Reduction
- Real-time Feature Updates
- Feature Importance Analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from sklearn.feature_selection import (
    SelectKBest, SelectPercentile, RFE, RFECV,
    mutual_info_regression, f_regression
)
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.decomposition import PCA, FastICA
from sklearn.ensemble import RandomForestRegressor
import talib
from scipy import stats
from scipy.signal import find_peaks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress warnings
warnings.filterwarnings('ignore')


class FeatureType(Enum):
    """Types of features."""
    TECHNICAL = "technical"
    PRICE_ACTION = "price_action"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    MICROSTRUCTURE = "microstructure"
    CROSS_ASSET = "cross_asset"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    MACRO = "macro"


class ScalingMethod(Enum):
    """Feature scaling methods."""
    STANDARD = "standard"
    MINMAX = "minmax"
    ROBUST = "robust"
    NONE = "none"


@dataclass
class FeatureConfig:
    """Feature engineering configuration."""
    lookback_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 50, 100])
    include_technical: bool = True
    include_price_action: bool = True
    include_volume: bool = True
    include_volatility: bool = True
    include_momentum: bool = True
    include_mean_reversion: bool = True
    include_microstructure: bool = False
    include_cross_asset: bool = False
    include_fundamental: bool = False
    include_sentiment: bool = False
    include_macro: bool = False
    scaling_method: ScalingMethod = ScalingMethod.STANDARD
    feature_selection: bool = True
    max_features: Optional[int] = None
    correlation_threshold: float = 0.95
    variance_threshold: float = 0.01


@dataclass
class FeatureImportance:
    """Feature importance result."""
    feature_name: str
    importance_score: float
    feature_type: FeatureType
    rank: int
    p_value: Optional[float] = None
    confidence_interval: Optional[Tuple[float, float]] = None


class TechnicalFeatures:
    """Technical indicator feature extraction."""
    
    def __init__(self, lookback_periods: List[int] = None):
        self.lookback_periods = lookback_periods or [5, 10, 20, 50, 100]
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract technical indicator features.
        
        Args:
            data: OHLCV data
            
        Returns:
            DataFrame with technical features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            # Price data
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            volume = data['volume'].values
            
            # Typical price
            typical_price = (high + low + close) / 3
            
            # Moving averages
            for period in self.lookback_periods:
                if len(close) >= period:
                    # Simple moving average
                    features[f'sma_{period}'] = talib.SMA(close, timeperiod=period)
                    
                    # Exponential moving average
                    features[f'ema_{period}'] = talib.EMA(close, timeperiod=period)
                    
                    # Weighted moving average
                    features[f'wma_{period}'] = talib.WMA(close, timeperiod=period)
                    
                    # Hull moving average
                    if period >= 2:
                        half_period = max(1, period // 2)
                        sqrt_period = max(1, int(np.sqrt(period)))
                        if len(close) >= period:
                            wma_half = talib.WMA(close, timeperiod=half_period)
                            wma_full = talib.WMA(close, timeperiod=period)
                            hull_ma = talib.WMA(2 * wma_half - wma_full, timeperiod=sqrt_period)
                            features[f'hull_ma_{period}'] = hull_ma
                    
                    # Price relative to moving averages
                    sma_val = talib.SMA(close, timeperiod=period)
                    features[f'price_sma_ratio_{period}'] = close / sma_val
                    features[f'price_sma_diff_{period}'] = (close - sma_val) / sma_val
            
            # Momentum indicators
            if len(close) >= 14:
                # RSI
                features['rsi_14'] = talib.RSI(close, timeperiod=14)
                
                # Stochastic
                slowk, slowd = talib.STOCH(high, low, close, fastk_period=14, slowk_period=3, slowd_period=3)
                features['stoch_k'] = slowk
                features['stoch_d'] = slowd
                
                # Williams %R
                features['williams_r'] = talib.WILLR(high, low, close, timeperiod=14)
                
                # CCI
                features['cci'] = talib.CCI(high, low, close, timeperiod=14)
            
            # MACD
            if len(close) >= 26:
                macd, macdsignal, macdhist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
                features['macd'] = macd
                features['macd_signal'] = macdsignal
                features['macd_histogram'] = macdhist
            
            # Bollinger Bands
            if len(close) >= 20:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(close, timeperiod=20, nbdevup=2, nbdevdn=2)
                features['bb_upper'] = bb_upper
                features['bb_middle'] = bb_middle
                features['bb_lower'] = bb_lower
                features['bb_width'] = (bb_upper - bb_lower) / bb_middle
                features['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower)
            
            # Average True Range
            if len(close) >= 14:
                features['atr'] = talib.ATR(high, low, close, timeperiod=14)
                features['atr_pct'] = features['atr'] / close
            
            # Volume indicators
            if len(volume) >= 20:
                # On Balance Volume
                features['obv'] = talib.OBV(close, volume)
                
                # Accumulation/Distribution Line
                features['ad_line'] = talib.AD(high, low, close, volume)
                
                # Chaikin Money Flow
                if len(close) >= 20:
                    features['cmf'] = talib.ADOSC(high, low, close, volume, fastperiod=3, slowperiod=10)
                
                # Money Flow Index
                if len(close) >= 14:
                    features['mfi'] = talib.MFI(high, low, close, volume, timeperiod=14)
            
            # Trend indicators
            if len(close) >= 25:
                # Parabolic SAR
                features['sar'] = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
                
                # ADX
                features['adx'] = talib.ADX(high, low, close, timeperiod=14)
                features['plus_di'] = talib.PLUS_DI(high, low, close, timeperiod=14)
                features['minus_di'] = talib.MINUS_DI(high, low, close, timeperiod=14)
            
            # Price patterns
            if len(close) >= 5:
                # Rate of Change
                for period in [1, 5, 10, 20]:
                    if len(close) >= period:
                        features[f'roc_{period}'] = talib.ROC(close, timeperiod=period)
                
                # Momentum
                for period in [5, 10, 20]:
                    if len(close) >= period:
                        features[f'momentum_{period}'] = talib.MOM(close, timeperiod=period)
            
            # Volatility indicators
            if len(close) >= 10:
                # Standard deviation
                for period in [5, 10, 20]:
                    if len(close) >= period:
                        features[f'stddev_{period}'] = talib.STDDEV(close, timeperiod=period)
                        features[f'var_{period}'] = talib.VAR(close, timeperiod=period)
            
            # Custom indicators
            self._add_custom_indicators(features, data)
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting technical features: {e}")
            return pd.DataFrame(index=data.index)
    
    def _add_custom_indicators(self, features: pd.DataFrame, data: pd.DataFrame) -> None:
        """Add custom technical indicators.
        
        Args:
            features: Features DataFrame to update
            data: OHLCV data
        """
        try:
            close = data['close'].values
            high = data['high'].values
            low = data['low'].values
            volume = data['volume'].values
            
            # Price momentum
            if len(close) >= 20:
                # Price acceleration
                returns = pd.Series(close).pct_change()
                features['price_acceleration'] = returns.diff()
                
                # Trend strength
                for period in [10, 20]:
                    if len(close) >= period:
                        trend_up = (close > np.roll(close, period)).astype(int)
                        features[f'trend_strength_{period}'] = pd.Series(trend_up).rolling(period).mean()
            
            # Volatility clustering
            if len(close) >= 30:
                returns = pd.Series(close).pct_change()
                vol_10 = returns.rolling(10).std()
                vol_30 = returns.rolling(30).std()
                features['vol_clustering'] = vol_10 / vol_30
            
            # Support and resistance levels
            if len(close) >= 50:
                # Recent highs and lows
                high_20 = pd.Series(high).rolling(20).max()
                low_20 = pd.Series(low).rolling(20).min()
                features['distance_to_high'] = (high_20 - close) / close
                features['distance_to_low'] = (close - low_20) / close
            
        except Exception as e:
            logger.warning(f"Error adding custom indicators: {e}")


class PriceActionFeatures:
    """Price action and candlestick pattern features."""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract price action features.
        
        Args:
            data: OHLCV data
            
        Returns:
            DataFrame with price action features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            open_price = data['open'].values
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            
            # Basic price action
            features['body_size'] = np.abs(close - open_price) / open_price
            features['upper_shadow'] = (high - np.maximum(open_price, close)) / open_price
            features['lower_shadow'] = (np.minimum(open_price, close) - low) / open_price
            features['total_range'] = (high - low) / open_price
            
            # Candlestick patterns (TA-Lib)
            if len(close) >= 5:
                # Single candlestick patterns
                features['doji'] = talib.CDLDOJI(open_price, high, low, close)
                features['hammer'] = talib.CDLHAMMER(open_price, high, low, close)
                features['hanging_man'] = talib.CDLHANGINGMAN(open_price, high, low, close)
                features['shooting_star'] = talib.CDLSHOOTINGSTAR(open_price, high, low, close)
                features['marubozu'] = talib.CDLMARUBOZU(open_price, high, low, close)
                features['spinning_top'] = talib.CDLSPINNINGTOP(open_price, high, low, close)
                
                # Multi-candlestick patterns
                features['engulfing'] = talib.CDLENGULFING(open_price, high, low, close)
                features['harami'] = talib.CDLHARAMI(open_price, high, low, close)
                features['piercing'] = talib.CDLPIERCING(open_price, high, low, close)
                features['dark_cloud'] = talib.CDLDARKCLOUDCOVER(open_price, high, low, close)
                features['morning_star'] = talib.CDLMORNINGSTAR(open_price, high, low, close)
                features['evening_star'] = talib.CDLEVENINGSTAR(open_price, high, low, close)
            
            # Price gaps
            if len(close) >= 2:
                prev_close = np.roll(close, 1)
                features['gap_up'] = np.maximum(0, (open_price - prev_close) / prev_close)
                features['gap_down'] = np.maximum(0, (prev_close - open_price) / prev_close)
                features['gap_filled'] = ((low <= prev_close) & (open_price > prev_close)).astype(int)
            
            # Price levels
            if len(close) >= 20:
                # Pivot points
                pivot = (high + low + close) / 3
                features['pivot_point'] = pivot
                features['resistance_1'] = 2 * pivot - low
                features['support_1'] = 2 * pivot - high
                
                # Distance to pivot levels
                features['distance_to_pivot'] = (close - pivot) / close
                features['distance_to_r1'] = (features['resistance_1'] - close) / close
                features['distance_to_s1'] = (close - features['support_1']) / close
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting price action features: {e}")
            return pd.DataFrame(index=data.index)


class VolumeFeatures:
    """Volume-based feature extraction."""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract volume features.
        
        Args:
            data: OHLCV data
            
        Returns:
            DataFrame with volume features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            close = data['close'].values
            volume = data['volume'].values
            high = data['high'].values
            low = data['low'].values
            
            # Volume statistics
            for period in [5, 10, 20]:
                if len(volume) >= period:
                    vol_ma = pd.Series(volume).rolling(period).mean()
                    features[f'volume_ma_{period}'] = vol_ma
                    features[f'volume_ratio_{period}'] = volume / vol_ma
                    features[f'volume_std_{period}'] = pd.Series(volume).rolling(period).std()
            
            # Volume-price relationship
            if len(close) >= 2:
                price_change = pd.Series(close).pct_change()
                volume_change = pd.Series(volume).pct_change()
                
                # Volume confirmation
                features['volume_price_trend'] = np.sign(price_change) * np.sign(volume_change)
                
                # Volume momentum
                for period in [5, 10]:
                    if len(volume) >= period:
                        vol_momentum = pd.Series(volume).rolling(period).apply(
                            lambda x: stats.linregress(range(len(x)), x)[0] if len(x) > 1 else 0
                        )
                        features[f'volume_momentum_{period}'] = vol_momentum
            
            # VWAP and volume profile
            if len(close) >= 20:
                typical_price = (high + low + close) / 3
                
                # VWAP
                for period in [10, 20]:
                    if len(close) >= period:
                        vwap = (pd.Series(typical_price * volume).rolling(period).sum() / 
                               pd.Series(volume).rolling(period).sum())
                        features[f'vwap_{period}'] = vwap
                        features[f'price_vwap_ratio_{period}'] = close / vwap
            
            # Volume spikes
            if len(volume) >= 20:
                vol_ma_20 = pd.Series(volume).rolling(20).mean()
                vol_std_20 = pd.Series(volume).rolling(20).std()
                features['volume_spike'] = (volume > vol_ma_20 + 2 * vol_std_20).astype(int)
                features['volume_dry_up'] = (volume < vol_ma_20 - vol_std_20).astype(int)
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting volume features: {e}")
            return pd.DataFrame(index=data.index)


class VolatilityFeatures:
    """Volatility-based feature extraction."""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract volatility features.
        
        Args:
            data: OHLCV data
            
        Returns:
            DataFrame with volatility features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            close = data['close'].values
            high = data['high'].values
            low = data['low'].values
            
            # Realized volatility
            returns = pd.Series(close).pct_change()
            
            for period in [5, 10, 20, 50]:
                if len(returns) >= period:
                    # Historical volatility
                    hist_vol = returns.rolling(period).std() * np.sqrt(252)
                    features[f'hist_vol_{period}'] = hist_vol
                    
                    # Volatility of volatility
                    if period >= 10:
                        vol_of_vol = hist_vol.rolling(period//2).std()
                        features[f'vol_of_vol_{period}'] = vol_of_vol
            
            # Parkinson volatility (high-low)
            if len(close) >= 20:
                parkinson_vol = np.sqrt(
                    pd.Series(np.log(high/low)**2).rolling(20).mean() / (4 * np.log(2))
                ) * np.sqrt(252)
                features['parkinson_vol'] = parkinson_vol
            
            # Garman-Klass volatility
            if len(close) >= 20:
                open_price = data['open'].values
                gk_vol = np.sqrt(
                    pd.Series(
                        0.5 * np.log(high/low)**2 - 
                        (2*np.log(2) - 1) * np.log(close/open_price)**2
                    ).rolling(20).mean()
                ) * np.sqrt(252)
                features['gk_vol'] = gk_vol
            
            # Volatility regimes
            if len(returns) >= 50:
                vol_20 = returns.rolling(20).std()
                vol_50 = returns.rolling(50).std()
                features['vol_regime'] = (vol_20 > vol_50).astype(int)
                
                # Volatility percentile
                vol_percentile = vol_20.rolling(252).rank(pct=True)
                features['vol_percentile'] = vol_percentile
            
            # True Range based features
            if len(close) >= 14:
                tr = talib.TRANGE(high, low, close)
                atr = talib.ATR(high, low, close, timeperiod=14)
                
                features['true_range'] = tr
                features['atr_14'] = atr
                features['tr_atr_ratio'] = tr / atr
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting volatility features: {e}")
            return pd.DataFrame(index=data.index)


class MarketMicrostructureFeatures:
    """Market microstructure feature extraction."""
    
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract market microstructure features.
        
        Args:
            data: OHLCV data with additional microstructure data if available
            
        Returns:
            DataFrame with microstructure features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            close = data['close'].values
            high = data['high'].values
            low = data['low'].values
            volume = data['volume'].values
            
            # Bid-ask spread proxy (using high-low)
            spread_proxy = (high - low) / close
            features['spread_proxy'] = spread_proxy
            
            # Price impact
            if len(close) >= 2:
                returns = pd.Series(close).pct_change()
                vol_change = pd.Series(volume).pct_change()
                
                # Kyle's lambda (price impact)
                for period in [10, 20]:
                    if len(returns) >= period:
                        # Rolling correlation between returns and volume
                        price_impact = returns.rolling(period).corr(vol_change)
                        features[f'price_impact_{period}'] = price_impact
            
            # Order flow imbalance proxy
            if len(close) >= 5:
                # Using close relative to high-low range as proxy
                close_position = (close - low) / (high - low)
                features['close_position'] = close_position
                
                # Order flow momentum
                for period in [5, 10]:
                    if len(close_position) >= period:
                        flow_momentum = pd.Series(close_position).rolling(period).mean()
                        features[f'flow_momentum_{period}'] = flow_momentum
            
            # Tick direction (using price changes)
            if len(close) >= 2:
                tick_direction = np.sign(pd.Series(close).diff())
                features['tick_direction'] = tick_direction
                
                # Tick imbalance
                for period in [10, 20]:
                    if len(tick_direction) >= period:
                        tick_imbalance = tick_direction.rolling(period).mean()
                        features[f'tick_imbalance_{period}'] = tick_imbalance
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting microstructure features: {e}")
            return pd.DataFrame(index=data.index)


class MacroeconomicFeatures:
    """Macroeconomic feature extraction."""
    
    def extract_features(self, data: pd.DataFrame, macro_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Extract macroeconomic features.
        
        Args:
            data: OHLCV data
            macro_data: Optional macroeconomic data
            
        Returns:
            DataFrame with macro features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            if macro_data is not None:
                # Interest rates
                if 'interest_rate' in macro_data.columns:
                    features['interest_rate'] = macro_data['interest_rate']
                    features['interest_rate_change'] = macro_data['interest_rate'].diff()
                
                # Economic indicators
                for col in ['gdp_growth', 'inflation', 'unemployment', 'vix']:
                    if col in macro_data.columns:
                        features[col] = macro_data[col]
                        features[f'{col}_change'] = macro_data[col].diff()
            
            # Market-based macro proxies
            close = data['close'].values
            
            # Trend strength as economic sentiment proxy
            if len(close) >= 50:
                long_trend = pd.Series(close).rolling(50).apply(
                    lambda x: stats.linregress(range(len(x)), x)[0] if len(x) > 1 else 0
                )
                features['long_term_trend'] = long_trend
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting macro features: {e}")
            return pd.DataFrame(index=data.index)


class SentimentFeatures:
    """Sentiment-based feature extraction."""
    
    def extract_features(self, data: pd.DataFrame, sentiment_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Extract sentiment features.
        
        Args:
            data: OHLCV data
            sentiment_data: Optional sentiment data
            
        Returns:
            DataFrame with sentiment features
        """
        try:
            features = pd.DataFrame(index=data.index)
            
            if sentiment_data is not None:
                # News sentiment
                for col in ['news_sentiment', 'social_sentiment', 'analyst_sentiment']:
                    if col in sentiment_data.columns:
                        features[col] = sentiment_data[col]
                        features[f'{col}_ma_5'] = sentiment_data[col].rolling(5).mean()
            
            # Market-based sentiment proxies
            close = data['close'].values
            volume = data['volume'].values
            
            # Fear and greed proxy using volatility and volume
            if len(close) >= 20:
                returns = pd.Series(close).pct_change()
                vol = returns.rolling(20).std()
                vol_ma = pd.Series(volume).rolling(20).mean()
                
                # High volatility + high volume = fear
                # Low volatility + low volume = complacency
                fear_greed = -(vol * vol_ma)  # Negative because high vol/volume = fear
                features['fear_greed_proxy'] = fear_greed
            
            return features
        
        except Exception as e:
            logger.warning(f"Error extracting sentiment features: {e}")
            return pd.DataFrame(index=data.index)


class FeatureSelector:
    """Feature selection and dimensionality reduction."""
    
    def __init__(self, method: str = 'mutual_info', max_features: Optional[int] = None):
        self.method = method
        self.max_features = max_features
        self.selector = None
        self.selected_features = []
        self.feature_scores = {}
    
    def fit_select(self, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        """Fit selector and select features.
        
        Args:
            X: Feature matrix
            y: Target variable
            
        Returns:
            Selected features DataFrame
        """
        try:
            if len(X) == 0 or len(y) == 0:
                return X
            
            # Remove constant features
            X_clean = X.loc[:, X.var() > 0.001]
            
            # Remove highly correlated features
            corr_matrix = X_clean.corr().abs()
            upper_triangle = corr_matrix.where(
                np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
            )
            to_drop = [column for column in upper_triangle.columns if any(upper_triangle[column] > 0.95)]
            X_clean = X_clean.drop(columns=to_drop)
            
            if len(X_clean.columns) == 0:
                return X_clean
            
            # Align X and y
            common_index = X_clean.index.intersection(y.index)
            X_aligned = X_clean.loc[common_index]
            y_aligned = y.loc[common_index]
            
            # Remove NaN values
            mask = ~(X_aligned.isna().any(axis=1) | y_aligned.isna())
            X_final = X_aligned[mask]
            y_final = y_aligned[mask]
            
            if len(X_final) == 0:
                return X_clean
            
            # Feature selection
            if self.method == 'mutual_info':
                scores = mutual_info_regression(X_final, y_final, random_state=42)
                self.feature_scores = dict(zip(X_final.columns, scores))
                
                if self.max_features:
                    k = min(self.max_features, len(X_final.columns))
                    self.selector = SelectKBest(mutual_info_regression, k=k)
                else:
                    self.selector = SelectPercentile(mutual_info_regression, percentile=50)
            
            elif self.method == 'f_regression':
                if self.max_features:
                    k = min(self.max_features, len(X_final.columns))
                    self.selector = SelectKBest(f_regression, k=k)
                else:
                    self.selector = SelectPercentile(f_regression, percentile=50)
            
            elif self.method == 'rfe':
                estimator = RandomForestRegressor(n_estimators=50, random_state=42)
                n_features = self.max_features or max(1, len(X_final.columns) // 2)
                self.selector = RFE(estimator, n_features_to_select=n_features)
            
            # Fit and transform
            X_selected = self.selector.fit_transform(X_final, y_final)
            
            # Get selected feature names
            if hasattr(self.selector, 'get_support'):
                selected_mask = self.selector.get_support()
                self.selected_features = X_final.columns[selected_mask].tolist()
            else:
                self.selected_features = X_final.columns.tolist()
            
            # Create result DataFrame
            result = pd.DataFrame(X_selected, index=X_final.index, columns=self.selected_features)
            
            # Extend to original index with NaN
            result = result.reindex(X.index)
            
            return result
        
        except Exception as e:
            logger.warning(f"Error in feature selection: {e}")
            return X
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """Transform new data using fitted selector.
        
        Args:
            X: Feature matrix
            
        Returns:
            Transformed features DataFrame
        """
        try:
            if self.selector is None or not self.selected_features:
                return X
            
            # Select only the features that were selected during fit
            available_features = [f for f in self.selected_features if f in X.columns]
            
            if not available_features:
                return pd.DataFrame(index=X.index)
            
            return X[available_features]
        
        except Exception as e:
            logger.warning(f"Error transforming features: {e}")
            return X
    
    def get_feature_importance(self) -> List[FeatureImportance]:
        """Get feature importance scores.
        
        Returns:
            List of FeatureImportance objects
        """
        try:
            importance_list = []
            
            for i, (feature, score) in enumerate(self.feature_scores.items()):
                importance = FeatureImportance(
                    feature_name=feature,
                    importance_score=score,
                    feature_type=self._get_feature_type(feature),
                    rank=i + 1
                )
                importance_list.append(importance)
            
            # Sort by importance score
            importance_list.sort(key=lambda x: x.importance_score, reverse=True)
            
            # Update ranks
            for i, importance in enumerate(importance_list):
                importance.rank = i + 1
            
            return importance_list
        
        except Exception as e:
            logger.warning(f"Error getting feature importance: {e}")
            return []
    
    def _get_feature_type(self, feature_name: str) -> FeatureType:
        """Determine feature type from feature name.
        
        Args:
            feature_name: Name of the feature
            
        Returns:
            FeatureType enum
        """
        feature_lower = feature_name.lower()
        
        if any(x in feature_lower for x in ['sma', 'ema', 'wma', 'rsi', 'macd', 'bb_', 'atr']):
            return FeatureType.TECHNICAL
        elif any(x in feature_lower for x in ['body_size', 'shadow', 'doji', 'hammer']):
            return FeatureType.PRICE_ACTION
        elif any(x in feature_lower for x in ['volume', 'obv', 'mfi', 'vwap']):
            return FeatureType.VOLUME
        elif any(x in feature_lower for x in ['vol', 'volatility', 'parkinson', 'gk_']):
            return FeatureType.VOLATILITY
        elif any(x in feature_lower for x in ['momentum', 'roc', 'trend']):
            return FeatureType.MOMENTUM
        elif any(x in feature_lower for x in ['mean_reversion', 'distance_to']):
            return FeatureType.MEAN_REVERSION
        elif any(x in feature_lower for x in ['spread', 'impact', 'flow', 'tick']):
            return FeatureType.MICROSTRUCTURE
        elif any(x in feature_lower for x in ['interest', 'gdp', 'inflation']):
            return FeatureType.MACRO
        elif any(x in feature_lower for x in ['sentiment', 'fear', 'greed']):
            return FeatureType.SENTIMENT
        else:
            return FeatureType.TECHNICAL


class FeatureEngineer:
    """Main feature engineering orchestrator."""
    
    def __init__(self, config: FeatureConfig = None):
        self.config = config or FeatureConfig()
        self.technical_features = TechnicalFeatures(self.config.lookback_periods)
        self.price_action_features = PriceActionFeatures()
        self.volume_features = VolumeFeatures()
        self.volatility_features = VolatilityFeatures()
        self.microstructure_features = MarketMicrostructureFeatures()
        self.macro_features = MacroeconomicFeatures()
        self.sentiment_features = SentimentFeatures()
        self.feature_selector = FeatureSelector(max_features=self.config.max_features)
        self.scaler = None
        self.feature_names = []
    
    def extract_all_features(self,
                           data: pd.DataFrame,
                           macro_data: Optional[pd.DataFrame] = None,
                           sentiment_data: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """Extract all configured features.
        
        Args:
            data: OHLCV data
            macro_data: Optional macroeconomic data
            sentiment_data: Optional sentiment data
            
        Returns:
            DataFrame with all features
        """
        try:
            all_features = pd.DataFrame(index=data.index)
            
            # Technical indicators
            if self.config.include_technical:
                tech_features = self.technical_features.extract_features(data)
                all_features = pd.concat([all_features, tech_features], axis=1)
            
            # Price action
            if self.config.include_price_action:
                price_features = self.price_action_features.extract_features(data)
                all_features = pd.concat([all_features, price_features], axis=1)
            
            # Volume
            if self.config.include_volume:
                vol_features = self.volume_features.extract_features(data)
                all_features = pd.concat([all_features, vol_features], axis=1)
            
            # Volatility
            if self.config.include_volatility:
                volatility_feats = self.volatility_features.extract_features(data)
                all_features = pd.concat([all_features, volatility_feats], axis=1)
            
            # Market microstructure
            if self.config.include_microstructure:
                micro_features = self.microstructure_features.extract_features(data)
                all_features = pd.concat([all_features, micro_features], axis=1)
            
            # Macroeconomic
            if self.config.include_macro:
                macro_feats = self.macro_features.extract_features(data, macro_data)
                all_features = pd.concat([all_features, macro_feats], axis=1)
            
            # Sentiment
            if self.config.include_sentiment:
                sentiment_feats = self.sentiment_features.extract_features(data, sentiment_data)
                all_features = pd.concat([all_features, sentiment_feats], axis=1)
            
            # Remove duplicate columns
            all_features = all_features.loc[:, ~all_features.columns.duplicated()]
            
            # Store feature names
            self.feature_names = all_features.columns.tolist()
            
            return all_features
        
        except Exception as e:
            logger.warning(f"Error extracting all features: {e}")
            return pd.DataFrame(index=data.index)
    
    def prepare_features(self,
                       data: pd.DataFrame,
                       target: Optional[pd.Series] = None,
                       macro_data: Optional[pd.DataFrame] = None,
                       sentiment_data: Optional[pd.DataFrame] = None,
                       fit_selector: bool = True) -> pd.DataFrame:
        """Extract, select, and scale features.
        
        Args:
            data: OHLCV data
            target: Target variable for feature selection
            macro_data: Optional macroeconomic data
            sentiment_data: Optional sentiment data
            fit_selector: Whether to fit feature selector
            
        Returns:
            Prepared features DataFrame
        """
        try:
            # Extract all features
            features = self.extract_all_features(data, macro_data, sentiment_data)
            
            if len(features) == 0:
                return features
            
            # Feature selection
            if self.config.feature_selection and target is not None and fit_selector:
                features = self.feature_selector.fit_select(features, target)
            elif self.config.feature_selection and not fit_selector:
                features = self.feature_selector.transform(features)
            
            # Scaling
            if self.config.scaling_method != ScalingMethod.NONE:
                features = self._scale_features(features, fit_scaler=fit_selector)
            
            return features
        
        except Exception as e:
            logger.warning(f"Error preparing features: {e}")
            return pd.DataFrame(index=data.index)
    
    def _scale_features(self, features: pd.DataFrame, fit_scaler: bool = True) -> pd.DataFrame:
        """Scale features using configured method.
        
        Args:
            features: Features DataFrame
            fit_scaler: Whether to fit scaler
            
        Returns:
            Scaled features DataFrame
        """
        try:
            if len(features) == 0:
                return features
            
            if fit_scaler:
                if self.config.scaling_method == ScalingMethod.STANDARD:
                    self.scaler = StandardScaler()
                elif self.config.scaling_method == ScalingMethod.MINMAX:
                    self.scaler = MinMaxScaler()
                elif self.config.scaling_method == ScalingMethod.ROBUST:
                    self.scaler = RobustScaler()
                
                # Fit scaler on non-NaN data
                valid_data = features.dropna()
                if len(valid_data) > 0:
                    self.scaler.fit(valid_data)
            
            if self.scaler is not None:
                # Transform all data (NaN will remain NaN)
                scaled_data = features.copy()
                valid_mask = ~features.isna().any(axis=1)
                
                if valid_mask.sum() > 0:
                    scaled_data.loc[valid_mask] = self.scaler.transform(features.loc[valid_mask])
                
                return scaled_data
            
            return features
        
        except Exception as e:
            logger.warning(f"Error scaling features: {e}")
            return features
    
    def get_feature_importance(self) -> List[FeatureImportance]:
        """Get feature importance from selector.
        
        Returns:
            List of FeatureImportance objects
        """
        return self.feature_selector.get_feature_importance()