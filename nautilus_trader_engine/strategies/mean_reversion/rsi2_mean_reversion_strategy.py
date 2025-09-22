"""RSI(2) Mean Reversion Strategy with Multi-Timeframe Confirmation and ML Clustering

This strategy implements the classic RSI(2) mean reversion approach enhanced with:
1. Multi-timeframe confirmation using higher timeframe trend analysis
2. Machine learning clustering for market regime adaptation
3. Volume-weighted RSI calculations for improved signal quality
4. Dynamic position sizing based on market volatility
5. Advanced risk management with regime-aware stop losses

Based on Larry Connors' RSI(2) strategy with modern enhancements.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

# NautilusTrader imports
try:
    from nautilus_trader.model.data import Bar, BarType
    from nautilus_trader.model.enums import OrderSide, TimeInForce
    from nautilus_trader.model.identifiers import InstrumentId
    from nautilus_trader.model.instruments import Instrument
    from nautilus_trader.model.orders import MarketOrder, LimitOrder
    from nautilus_trader.trading.strategy import Strategy
    from nautilus_trader.core.message import Event
    from nautilus_trader.model.events import OrderFilled
    from nautilus_trader.model.position import Position
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    logging.warning("NautilusTrader not available, using mock classes for testing")
    # Create mock classes for testing
    class Strategy:
        pass
    class Bar:
        pass
    class BarType:
        pass
    class OrderSide:
        pass
    class TimeInForce:
        pass
    class InstrumentId:
        pass
    class Instrument:
        pass
    class MarketOrder:
        pass
    class LimitOrder:
        pass
    class Event:
        pass
    class OrderFilled:
        pass
    class Position:
        pass

# Technical Analysis imports
try:
    import talib
    from ...indicators.consolidated_indicators import ConsolidatedIndicators
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    logging.warning("TA-Lib not available, using pandas-based calculations")

logger = logging.getLogger(__name__)

# ===========================================
# ENUMS AND TYPES
# ===========================================

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    MEAN_REVERTING = "mean_reverting"
    VOLATILE = "volatile"
    LOW_VOLATILITY = "low_volatility"
    UNKNOWN = "unknown"

class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_WEAK = 1
    WEAK = 2
    MODERATE = 3
    STRONG = 4
    VERY_STRONG = 5

class TimeframeConfirmation(Enum):
    """Multi-timeframe confirmation status"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    CONFLICTING = "conflicting"

# ===========================================
# DATA CLASSES
# ===========================================

@dataclass
class RSI2Signal:
    """RSI(2) trading signal"""
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    strength: SignalStrength
    rsi2_value: float
    rsi14_value: float
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: float
    regime: MarketRegime
    timeframe_confirmation: TimeframeConfirmation
    volume_confirmation: bool
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RegimeFeatures:
    """Features for market regime classification"""
    volatility_20d: float
    trend_strength: float
    volume_trend: float
    price_momentum: float
    rsi_divergence: float
    bollinger_position: float
    atr_normalized: float
    correlation_spy: float

@dataclass
class StrategyConfig:
    """Configuration for RSI(2) strategy"""
    # RSI Parameters
    rsi_short_period: int = 2
    rsi_long_period: int = 14
    rsi_oversold: float = 10.0
    rsi_overbought: float = 90.0
    
    # Multi-timeframe settings
    primary_timeframe: str = "1-HOUR"
    confirmation_timeframe: str = "4-HOUR"
    trend_timeframe: str = "1-DAY"
    
    # ML Clustering
    n_clusters: int = 5
    lookback_period: int = 252  # 1 year of daily data
    retrain_frequency: int = 21  # Retrain every 21 days
    
    # Risk Management
    max_position_size: float = 0.02  # 2% of portfolio
    base_stop_loss_pct: float = 0.02  # 2% stop loss
    regime_stop_multiplier: Dict[MarketRegime, float] = field(default_factory=lambda: {
        MarketRegime.TRENDING_UP: 0.8,
        MarketRegime.TRENDING_DOWN: 0.8,
        MarketRegime.MEAN_REVERTING: 1.0,
        MarketRegime.VOLATILE: 1.5,
        MarketRegime.LOW_VOLATILITY: 0.6,
        MarketRegime.UNKNOWN: 1.2
    })
    
    # Volume confirmation
    volume_ma_period: int = 20
    volume_threshold: float = 1.2  # 20% above average
    
    # Position management
    max_holding_period: int = 10  # Maximum days to hold position
    profit_target_multiplier: float = 2.0  # Risk:Reward ratio

# ===========================================
# TECHNICAL INDICATORS
# ===========================================

class TechnicalIndicators:
    """Technical indicator calculations with volume weighting"""
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14, volume: Optional[pd.Series] = None) -> pd.Series:
        """Calculate RSI with optional volume weighting"""
        if TALIB_AVAILABLE and volume is None:
            return pd.Series(ConsolidatedIndicators.rsi(prices.values, timeperiod=period), index=prices.index)
        
        # Volume-weighted RSI calculation
        if volume is not None:
            # Calculate volume-weighted price changes
            price_changes = prices.diff()
            volume_weights = volume / volume.rolling(period).mean()
            weighted_changes = price_changes * volume_weights
            
            gains = weighted_changes.where(weighted_changes > 0, 0)
            losses = -weighted_changes.where(weighted_changes < 0, 0)
        else:
            # Standard RSI calculation
            price_changes = prices.diff()
            gains = price_changes.where(price_changes > 0, 0)
            losses = -price_changes.where(price_changes < 0, 0)
        
        # Calculate exponential moving averages
        alpha = 1.0 / period
        avg_gains = gains.ewm(alpha=alpha, adjust=False).mean()
        avg_losses = losses.ewm(alpha=alpha, adjust=False).mean()
        
        # Calculate RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.fillna(50)
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        if TALIB_AVAILABLE:
            return pd.Series(talib.ATR(high.values, low.values, close.values, timeperiod=period), index=close.index)
        
        # Manual ATR calculation
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr.bfill()
    
    @staticmethod
    def volume_sma(volume: pd.Series, period: int = 20) -> pd.Series:
        """Calculate volume simple moving average"""
        return volume.rolling(period).mean()
    
    @staticmethod
    def trend_strength(prices: pd.Series, period: int = 20) -> pd.Series:
        """Calculate trend strength using linear regression slope"""
        def calculate_slope(y):
            if len(y) < 2:
                return 0
            x = np.arange(len(y))
            slope = np.polyfit(x, y, 1)[0]
            return slope
        
        trend = prices.rolling(period).apply(calculate_slope, raw=False)
        return trend.fillna(0)

# ===========================================
# MARKET REGIME CLASSIFIER
# ===========================================

class MarketRegimeClassifier:
    """Enhanced ML-based market regime classification with advanced features"""
    
    def __init__(self, config: StrategyConfig):
        self.strategy_config = config
        self.scaler = StandardScaler()
        self.kmeans = KMeans(n_clusters=self.strategy_config.n_clusters, random_state=42, n_init=10)
        self.is_trained = False
        self.last_training_date = None
        self.regime_mapping = {}  # Maps cluster labels to regime types
        self.regime_history = []  # Track regime changes
        self.feature_importance = {}  # Track which features are most predictive
        self.silhouette_score = 0.0  # Model quality metric
        self.regime_stability = 0.8  # How stable current regime is
        
    def extract_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract enhanced features for regime classification"""
        features = pd.DataFrame(index=data.index)
        
        # Price-based features
        returns = data['close'].pct_change()
        features['volatility_5d'] = returns.rolling(5).std() * np.sqrt(252)
        features['volatility_20d'] = returns.rolling(20).std() * np.sqrt(252)
        features['volatility_60d'] = returns.rolling(60).std() * np.sqrt(252)
        features['trend_strength'] = TechnicalIndicators.trend_strength(data['close'], 20)
        features['price_momentum_5d'] = data['close'].pct_change(5)
        features['price_momentum_10d'] = data['close'].pct_change(10)
        features['price_momentum_20d'] = data['close'].pct_change(20)
        
        # Multi-timeframe momentum
        features['momentum_consistency'] = (
            np.sign(features['price_momentum_5d']) + 
            np.sign(features['price_momentum_10d']) + 
            np.sign(features['price_momentum_20d'])
        ) / 3.0
        
        # Volume features
        if 'volume' in data.columns:
            features['volume_trend'] = TechnicalIndicators.trend_strength(data['volume'], 10)
            volume_sma_20 = TechnicalIndicators.volume_sma(data['volume'], 20)
            volume_sma_5 = TechnicalIndicators.volume_sma(data['volume'], 5)
            features['volume_ratio'] = data['volume'] / volume_sma_20
            features['volume_acceleration'] = volume_sma_5 / volume_sma_20
            
            # Volume-price relationship
            price_change = data['close'].pct_change()
            volume_change = data['volume'].pct_change()
            features['volume_price_correlation'] = price_change.rolling(20).corr(volume_change)
        else:
            features['volume_trend'] = 0
            features['volume_ratio'] = 1
            features['volume_acceleration'] = 1
            features['volume_price_correlation'] = 0
        
        # Technical indicator features
        rsi14 = TechnicalIndicators.rsi(data['close'], 14)
        rsi2 = TechnicalIndicators.rsi(data['close'], 2)
        features['rsi_divergence'] = abs(rsi14 - 50) / 50
        features['rsi_momentum'] = rsi14.diff(5)
        features['rsi_extreme_frequency'] = ((rsi2 < 20) | (rsi2 > 80)).rolling(20).mean()
        
        # Bollinger Band features
        if len(data) >= 20:
            upper, middle, lower = TechnicalIndicators.bollinger_bands(data['close'], 20)
            bb_width = (upper - lower) / middle
            bb_position = (data['close'] - lower) / (upper - lower)
            features['bollinger_position'] = bb_position.fillna(0.5)
            features['bollinger_width'] = bb_width.fillna(0.02)
            features['bollinger_squeeze'] = (bb_width < bb_width.rolling(20).quantile(0.2)).astype(float)
        else:
            features['bollinger_position'] = 0.5
            features['bollinger_width'] = 0.02
            features['bollinger_squeeze'] = 0
        
        # ATR and volatility features
        if len(data) >= 14 and all(col in data.columns for col in ['high', 'low']):
            atr = TechnicalIndicators.atr(data['high'], data['low'], data['close'], 14)
            features['atr_normalized'] = atr / data['close']
            features['atr_trend'] = atr.pct_change(5)
            
            # True Range expansion/contraction
            tr = pd.concat([
                data['high'] - data['low'],
                abs(data['high'] - data['close'].shift(1)),
                abs(data['low'] - data['close'].shift(1))
            ], axis=1).max(axis=1)
            features['tr_expansion'] = (tr > tr.rolling(20).quantile(0.8)).astype(float)
        else:
            features['atr_normalized'] = 0.02
            features['atr_trend'] = 0
            features['tr_expansion'] = 0
        
        # Market structure features
        if len(data) >= 50:
            # Higher highs and lower lows
            rolling_max = data['high'].rolling(20).max()
            rolling_min = data['low'].rolling(20).min()
            features['higher_highs'] = (data['high'] > rolling_max.shift(1)).astype(float)
            features['lower_lows'] = (data['low'] < rolling_min.shift(1)).astype(float)
            
            # Price range analysis
            daily_range = (data['high'] - data['low']) / data['close']
            features['range_expansion'] = daily_range / daily_range.rolling(20).mean()
        else:
            features['higher_highs'] = 0
            features['lower_lows'] = 0
            features['range_expansion'] = 1
        
        # Gap analysis
        if len(data) >= 2:
            gaps = abs(data['open'] - data['close'].shift(1)) / data['close'].shift(1)
            features['gap_frequency'] = (gaps > 0.01).rolling(20).mean()  # 1% gaps
            features['gap_magnitude'] = gaps.rolling(5).mean()
        else:
            features['gap_frequency'] = 0
            features['gap_magnitude'] = 0
        
        # Fill any remaining NaN values
        features = features.bfill().fillna(0)
        
        return features
    
    def train(self, data: pd.DataFrame) -> bool:
        """Train the enhanced regime classifier with model validation"""
        try:
            if len(data) < self.strategy_config.lookback_period:
                logger.warning(f"Insufficient data for training: {len(data)} < {self.strategy_config.lookback_period}")
                return False
            
            # Extract features
            features_df = self.extract_features(data)
            
            # Remove any rows with NaN or infinite values
            features_df = features_df.replace([np.inf, -np.inf], np.nan).dropna()
            
            if len(features_df) < 100:  # Increased minimum samples for better clustering
                logger.warning("Insufficient clean data for training")
                return False
            
            # Feature selection - remove highly correlated features
            correlation_matrix = features_df.corr().abs()
            upper_triangle = correlation_matrix.where(
                np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
            )
            
            # Find features with correlation > 0.95
            high_corr_features = [column for column in upper_triangle.columns 
                                if any(upper_triangle[column] > 0.95)]
            
            # Remove highly correlated features
            features_cleaned = features_df.drop(columns=high_corr_features)
            
            # Scale features
            features_scaled = self.scaler.fit_transform(features_cleaned)
            
            # Optimize number of clusters using silhouette score
            best_score = -1
            best_n_clusters = self.strategy_config.n_clusters
            
            for n_clusters in range(max(2, self.strategy_config.n_clusters - 2),
                                   min(10, self.strategy_config.n_clusters + 3)):
                try:
                    kmeans_test = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
                    labels_test = kmeans_test.fit_predict(features_scaled)
                    
                    if len(np.unique(labels_test)) > 1:  # Need at least 2 clusters
                        score = silhouette_score(features_scaled, labels_test)
                        if score > best_score:
                            best_score = score
                            best_n_clusters = n_clusters
                except:
                    continue
            
            # Train final model with optimal clusters
            self.kmeans = KMeans(n_clusters=best_n_clusters, random_state=42, n_init=10)
            labels = self.kmeans.fit_predict(features_scaled)
            self.silhouette_score = best_score
            
            # Create regime mapping based on cluster characteristics
            self._create_regime_mapping(features_cleaned, labels)
            
            # Calculate feature importance (variance within vs between clusters)
            self._calculate_feature_importance(features_cleaned, labels)
            
            self.is_trained = True
            self.last_training_date = data.index[-1] if hasattr(data.index[-1], 'date') else datetime.now().date()
            
            logger.info(f"Regime classifier trained successfully:")
            logger.info(f"  - Samples: {len(features_cleaned)}")
            logger.info(f"  - Features: {len(features_cleaned.columns)}")
            logger.info(f"  - Clusters: {best_n_clusters}")
            logger.info(f"  - Silhouette Score: {best_score:.3f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error training regime classifier: {e}")
            return False
    
    def _create_regime_mapping(self, features: pd.DataFrame, labels: np.ndarray):
        """Create enhanced mapping from cluster labels to market regimes"""
        cluster_stats = {}
        n_clusters = len(np.unique(labels))
        
        for cluster in range(n_clusters):
            mask = labels == cluster
            if np.sum(mask) == 0:
                continue
                
            cluster_features = features[mask]
            
            stats = {
                'volatility_20d': cluster_features['volatility_20d'].mean(),
                'volatility_5d': cluster_features['volatility_5d'].mean() if 'volatility_5d' in cluster_features else 0,
                'trend_strength': cluster_features['trend_strength'].mean(),
                'momentum_consistency': cluster_features['momentum_consistency'].mean() if 'momentum_consistency' in cluster_features else 0,
                'volume_ratio': cluster_features['volume_ratio'].mean() if 'volume_ratio' in cluster_features else 1.0,
                'atr_normalized': cluster_features['atr_normalized'].mean(),
                'rsi_extreme_frequency': cluster_features['rsi_extreme_frequency'].mean() if 'rsi_extreme_frequency' in cluster_features else 0,
                'bollinger_squeeze': cluster_features['bollinger_squeeze'].mean() if 'bollinger_squeeze' in cluster_features else 0,
                'range_expansion': cluster_features['range_expansion'].mean() if 'range_expansion' in cluster_features else 1,
                'sample_count': np.sum(mask)
            }
            
            cluster_stats[cluster] = stats
        
        # Enhanced regime mapping with multiple criteria
        for cluster, stats in cluster_stats.items():
            volatility = stats['volatility_20d']
            short_vol = stats['volatility_5d']
            trend_strength = abs(stats['trend_strength'])
            momentum_consistency = abs(stats['momentum_consistency'])
            rsi_extremes = stats['rsi_extreme_frequency']
            bb_squeeze = stats['bollinger_squeeze']
            
            # Multi-criteria regime classification
            if volatility > 0.35 or short_vol > 0.5:  # High volatility
                regime = MarketRegime.VOLATILE
            elif volatility < 0.08 and bb_squeeze > 0.3:  # Low volatility with compression
                regime = MarketRegime.LOW_VOLATILITY
            elif (trend_strength > 0.015 and momentum_consistency > 0.4):  # Strong consistent trend
                # Determine trend direction
                recent_trend = stats['trend_strength']
                if recent_trend > 0:
                    regime = MarketRegime.TRENDING_UP
                else:
                    regime = MarketRegime.TRENDING_DOWN
            elif rsi_extremes > 0.3:  # High mean reversion activity
                regime = MarketRegime.MEAN_REVERTING
            else:  # Default to mean reverting for unclear cases
                regime = MarketRegime.MEAN_REVERTING
            
            self.regime_mapping[cluster] = regime
            
            logger.debug(f"Cluster {cluster} -> {regime.value}:")
            logger.debug(f"  Vol: {volatility:.3f}, Trend: {trend_strength:.3f}, Momentum: {momentum_consistency:.3f}")
    
    def _calculate_feature_importance(self, features: pd.DataFrame, labels: np.ndarray):
        """Calculate feature importance for regime classification"""
        try:
            feature_importance = {}
            
            for feature in features.columns:
                # Calculate between-cluster variance vs within-cluster variance
                feature_values = features[feature].values
                
                # Between-cluster variance
                cluster_means = []
                for cluster in np.unique(labels):
                    mask = labels == cluster
                    if np.sum(mask) > 0:
                        cluster_means.append(feature_values[mask].mean())
                
                between_var = np.var(cluster_means) if len(cluster_means) > 1 else 0
                
                # Within-cluster variance
                within_vars = []
                for cluster in np.unique(labels):
                    mask = labels == cluster
                    if np.sum(mask) > 1:
                        within_vars.append(np.var(feature_values[mask]))
                
                within_var = np.mean(within_vars) if within_vars else 1
                
                # F-ratio as importance measure
                importance = between_var / max(within_var, 1e-8)
                feature_importance[feature] = importance
            
            # Normalize importance scores
            max_importance = max(feature_importance.values()) if feature_importance else 1
            self.feature_importance = {k: v / max_importance for k, v in feature_importance.items()}
            
        except Exception as e:
            logger.warning(f"Could not calculate feature importance: {e}")
            self.feature_importance = {}
    
    def predict_regime(self, data: pd.DataFrame) -> Tuple[MarketRegime, float]:
        """Predict current market regime with enhanced stability tracking"""
        if not self.is_trained:
            return MarketRegime.UNKNOWN, 0.5
        
        try:
            # Extract features for the latest data point
            features_df = self.extract_features(data)
            
            if len(features_df) == 0:
                return MarketRegime.UNKNOWN, 0.5
            
            # Get latest features (use last 5 points for stability)
            recent_features = features_df.tail(min(5, len(features_df)))
            
            # Handle any NaN or infinite values
            recent_features = recent_features.replace([np.inf, -np.inf], np.nan).fillna(0)
            
            # Scale features
            features_scaled = self.scaler.transform(recent_features)
            
            # Predict clusters for recent points
            clusters = self.kmeans.predict(features_scaled)
            latest_cluster = clusters[-1]
            
            # Calculate regime stability (consistency of recent predictions)
            if len(clusters) > 1:
                stability = np.mean(clusters == latest_cluster)
                self.regime_stability = 0.7 * self.regime_stability + 0.3 * stability
            else:
                stability = 1.0
            
            # Map to regime
            regime = self.regime_mapping.get(latest_cluster, MarketRegime.UNKNOWN)
            
            # Track regime changes
            if len(self.regime_history) == 0 or self.regime_history[-1] != regime:
                self.regime_history.append(regime)
                # Keep only last 20 regime changes
                if len(self.regime_history) > 20:
                    self.regime_history = self.regime_history[-20:]
            
            # Enhanced confidence calculation
            distances = self.kmeans.transform(features_scaled[-1:])[0]
            min_distance = np.min(distances)
            max_distance = np.max(distances)
            
            # Calculate relative distance confidence
            if max_distance > min_distance:
                base_confidence = 1.0 - (min_distance / max_distance)
            else:
                base_confidence = 0.8
            
            # Combine cluster confidence with regime stability
            stability_bonus = self.regime_stability * 0.3  # Up to 30% bonus for stability
            confidence = min(0.95, base_confidence + stability_bonus)
            confidence = max(0.1, confidence)  # Minimum confidence
            
            # Additional confidence boost for high-quality features
            if hasattr(self, 'silhouette_score') and self.silhouette_score > 0.3:
                confidence *= (1.0 + self.silhouette_score * 0.2)
                confidence = min(0.95, confidence)
            
            return regime, confidence
            
        except Exception as e:
            logger.error(f"Error predicting regime: {e}")
            return MarketRegime.UNKNOWN, 0.5
    
    def needs_retraining(self) -> bool:
        """Enhanced retraining logic with performance-based triggers"""
        if not self.is_trained or self.last_training_date is None:
            return True
        
        current_date = datetime.now().date()
        days_since_training = (current_date - self.last_training_date).days
        
        # Time-based retraining
        time_trigger = days_since_training >= self.strategy_config.retrain_frequency
        
        # Performance-based retraining triggers
        performance_trigger = False
        
        # Low regime stability suggests model degradation
        if self.regime_stability < 0.4:
            performance_trigger = True
            logger.info(f"Retraining triggered by low regime stability: {self.regime_stability:.3f}")
        
        # Poor model quality (if available)
        if hasattr(self, 'silhouette_score') and self.silhouette_score < 0.1:
            performance_trigger = True
            logger.info(f"Retraining triggered by poor silhouette score: {self.silhouette_score:.3f}")
        
        # Frequent regime changes suggest market shift
        if len(self.regime_history) >= 10:
            recent_changes = len(set(self.regime_history[-10:]))
            if recent_changes >= 6:  # More than 6 different regimes in last 10 observations
                performance_trigger = True
                logger.info(f"Retraining triggered by frequent regime changes: {recent_changes}/10")
        
        return time_trigger or performance_trigger
    
    def get_regime_statistics(self) -> dict:
        """Get comprehensive regime classification statistics"""
        stats = {
            'is_trained': self.is_trained,
            'regime_stability': self.regime_stability,
            'silhouette_score': getattr(self, 'silhouette_score', 0.0),
            'last_training_date': self.last_training_date,
            'regime_history_length': len(self.regime_history),
            'recent_regimes': list(set(self.regime_history[-5:])) if self.regime_history else [],
            'feature_count': len(self.feature_importance) if hasattr(self, 'feature_importance') else 0
        }
        
        # Add top important features
        if hasattr(self, 'feature_importance') and self.feature_importance:
            sorted_features = sorted(self.feature_importance.items(), 
                                   key=lambda x: x[1], reverse=True)
            stats['top_features'] = dict(sorted_features[:5])
        
        return stats

# ===========================================
# RSI(2) MEAN REVERSION STRATEGY
# ===========================================

class RSI2MeanReversionStrategy(Strategy):
    """RSI(2) Mean Reversion Strategy with ML Regime Adaptation"""
    
    def __init__(self, config: Optional[StrategyConfig] = None):
        super().__init__()
        
        self.strategy_config = config or StrategyConfig()
        self.regime_classifier = MarketRegimeClassifier(self.strategy_config)
        
        # Data storage
        self.bars_data = pd.DataFrame()
        self.signals_history = []
        
        # Strategy state
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.5
        self.last_signal_time = None
        self.position_entry_time = None
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        logger.info("RSI(2) Mean Reversion Strategy initialized")
    
    def on_start(self):
        """Called when the strategy starts"""
        logger.info("RSI(2) Mean Reversion Strategy started")
        
        # Subscribe to bars for primary timeframe
        # This would be configured based on the specific instrument
        # For now, we'll use a placeholder
        pass
    
    def on_bar(self, bar: Bar):
        """Process new bar data"""
        try:
            # Update data storage
            self._update_data_storage(bar)
            
            # Check if we have enough data
            if len(self.bars_data) < max(self.strategy_config.rsi_long_period, self.strategy_config.lookback_period // 10):
                return
            
            # Retrain regime classifier if needed
            if self.regime_classifier.needs_retraining() and len(self.bars_data) >= self.strategy_config.lookback_period:
                self.regime_classifier.train(self.bars_data)
            
            # Predict current market regime
            self.current_regime, self.regime_confidence = self.regime_classifier.predict_regime(self.bars_data)
            
            # Generate trading signal
            signal = self._generate_signal()
            
            if signal:
                self.signals_history.append(signal)
                self._execute_signal(signal)
            
            # Manage existing positions
            self._manage_positions()
            
        except Exception as e:
            logger.error(f"Error processing bar: {e}")
    
    def _update_data_storage(self, bar: Bar):
        """Update internal data storage with new bar"""
        bar_data = {
            'timestamp': bar.ts_init,
            'open': float(bar.open),
            'high': float(bar.high),
            'low': float(bar.low),
            'close': float(bar.close),
            'volume': float(bar.volume)
        }
        
        # Convert to DataFrame row
        new_row = pd.DataFrame([bar_data])
        new_row.set_index('timestamp', inplace=True)
        
        # Append to existing data
        if self.bars_data.empty:
            self.bars_data = new_row
        else:
            self.bars_data = pd.concat([self.bars_data, new_row])
        
        # Keep only recent data to manage memory
        max_bars = max(self.strategy_config.lookback_period, 1000)
        if len(self.bars_data) > max_bars:
            self.bars_data = self.bars_data.tail(max_bars)
    
    def _generate_signal(self) -> Optional[RSI2Signal]:
        """Enhanced RSI(2) trading signal generation with multi-factor analysis"""
        try:
            if len(self.bars_data) < max(self.strategy_config.rsi_long_period, 20):
                return None
            
            # Calculate RSI indicators
            rsi2 = TechnicalIndicators.rsi(self.bars_data['close'], self.strategy_config.rsi_short_period, self.bars_data['volume'])
            rsi14 = TechnicalIndicators.rsi(self.bars_data['close'], self.strategy_config.rsi_long_period)
            
            current_rsi2 = rsi2.iloc[-1]
            current_rsi14 = rsi14.iloc[-1]
            current_price = self.bars_data['close'].iloc[-1]
            
            # Multi-timeframe confirmation
            timeframe_confirmation = self._get_timeframe_confirmation()
            
            # Volume confirmation
            volume_confirmation = self._check_volume_confirmation()
            
            # Additional technical confirmations
            bollinger_confirmation = self._check_bollinger_confirmation()
            momentum_confirmation = self._check_momentum_confirmation()
            
            # Enhanced signal generation logic
            signal_type = "HOLD"
            base_strength = 0.0
            
            # Regime-adjusted thresholds
            oversold_threshold = self.strategy_config.rsi_oversold
            overbought_threshold = self.strategy_config.rsi_overbought
            
            if self.current_regime == MarketRegime.VOLATILE:
                # More conservative in volatile markets
                oversold_threshold = max(5, oversold_threshold - 5)
                overbought_threshold = min(95, overbought_threshold + 5)
            elif self.current_regime == MarketRegime.MEAN_REVERTING:
                # More aggressive in mean-reverting markets
                oversold_threshold = min(15, oversold_threshold + 5)
                overbought_threshold = max(85, overbought_threshold - 5)
            
            # RSI(2) oversold conditions
            if current_rsi2 <= oversold_threshold:
                # Calculate oversold strength
                oversold_strength = (oversold_threshold - current_rsi2) / oversold_threshold
                
                # Check regime suitability for mean reversion
                regime_suitable = self.current_regime in [
                    MarketRegime.MEAN_REVERTING, 
                    MarketRegime.LOW_VOLATILITY,
                    MarketRegime.TRENDING_DOWN
                ]
                
                # Multi-factor confirmation for buy signal
                confirmations = 0
                total_factors = 5
                
                if timeframe_confirmation in [TimeframeConfirmation.BULLISH, TimeframeConfirmation.NEUTRAL]:
                    confirmations += 1
                if volume_confirmation:
                    confirmations += 1
                if bollinger_confirmation == 'oversold':
                    confirmations += 1
                if momentum_confirmation >= 0:
                    confirmations += 1
                if regime_suitable and self.regime_confidence > 0.6:
                    confirmations += 1
                
                # Require at least 3 out of 5 confirmations
                if confirmations >= 3:
                    signal_type = "BUY"
                    base_strength = oversold_strength * (confirmations / total_factors)
            
            # RSI(2) overbought conditions
            elif current_rsi2 >= overbought_threshold:
                # Calculate overbought strength
                overbought_strength = (current_rsi2 - overbought_threshold) / (100 - overbought_threshold)
                
                # Check regime suitability
                regime_suitable = self.current_regime in [
                    MarketRegime.MEAN_REVERTING, 
                    MarketRegime.LOW_VOLATILITY,
                    MarketRegime.TRENDING_UP
                ]
                
                # Multi-factor confirmation for sell signal
                confirmations = 0
                total_factors = 5
                
                if timeframe_confirmation in [TimeframeConfirmation.BEARISH, TimeframeConfirmation.NEUTRAL]:
                    confirmations += 1
                if volume_confirmation:
                    confirmations += 1
                if bollinger_confirmation == 'overbought':
                    confirmations += 1
                if momentum_confirmation <= 0:
                    confirmations += 1
                if regime_suitable and self.regime_confidence > 0.6:
                    confirmations += 1
                
                # Require at least 3 out of 5 confirmations
                if confirmations >= 3:
                    signal_type = "SELL"
                    base_strength = overbought_strength * (confirmations / total_factors)
            
            # Only generate signal if we have a valid signal type
            if signal_type != "HOLD":
                # Enhanced signal strength calculation
                strength = self._calculate_enhanced_signal_strength(
                    current_rsi2, current_rsi14, signal_type, base_strength
                )
                
                # Enhanced confidence calculation
                confidence = self._calculate_enhanced_confidence(
                    current_rsi2, current_rsi14, volume_confirmation, 
                    timeframe_confirmation, bollinger_confirmation
                )
                
                # Only proceed if confidence is above threshold
                if confidence >= 0.6:
                    # Calculate stop loss and take profit
                    stop_loss, take_profit = self._calculate_levels(current_price, signal_type)
                    
                    signal = RSI2Signal(
                        signal_type=signal_type,
                        strength=strength,
                        rsi2_value=current_rsi2,
                        rsi14_value=current_rsi14,
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        confidence=confidence,
                        regime=self.current_regime,
                        timeframe_confirmation=timeframe_confirmation,
                        volume_confirmation=volume_confirmation,
                        timestamp=datetime.now(),
                        metadata={
                            'regime_confidence': self.regime_confidence,
                            'oversold_threshold': oversold_threshold,
                            'overbought_threshold': overbought_threshold,
                            'bollinger_confirmation': bollinger_confirmation,
                            'momentum_confirmation': momentum_confirmation
                        }
                    )
                    
                    return signal
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def _get_timeframe_confirmation(self) -> TimeframeConfirmation:
        """Get multi-timeframe confirmation (simplified)"""
        try:
            if len(self.bars_data) < 50:
                return TimeframeConfirmation.NEUTRAL
            
            # Calculate trend on higher timeframe (using longer period as proxy)
            long_term_sma = self.bars_data['close'].rolling(50).mean()
            medium_term_sma = self.bars_data['close'].rolling(20).mean()
            
            current_price = self.bars_data['close'].iloc[-1]
            long_sma = long_term_sma.iloc[-1]
            medium_sma = medium_term_sma.iloc[-1]
            
            if current_price > medium_sma > long_sma:
                return TimeframeConfirmation.BULLISH
            elif current_price < medium_sma < long_sma:
                return TimeframeConfirmation.BEARISH
            else:
                return TimeframeConfirmation.NEUTRAL
                
        except Exception:
            return TimeframeConfirmation.NEUTRAL
    
    def _check_volume_confirmation(self) -> bool:
        """Check if current volume supports the signal"""
        try:
            if len(self.bars_data) < self.strategy_config.volume_ma_period:
                return True  # Default to True if insufficient data
            
            volume_sma = TechnicalIndicators.volume_sma(self.bars_data['volume'], self.strategy_config.volume_ma_period)
            current_volume = self.bars_data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            return current_volume >= (avg_volume * self.strategy_config.volume_threshold)
            
        except Exception:
            return True
    
    def _check_bollinger_confirmation(self) -> str:
        """Check Bollinger Band position for additional confirmation"""
        try:
            if len(self.bars_data) < 20:
                return 'neutral'
            
            upper, middle, lower = TechnicalIndicators.bollinger_bands(self.bars_data['close'], 20)
            current_price = self.bars_data['close'].iloc[-1]
            current_upper = upper.iloc[-1]
            current_lower = lower.iloc[-1]
            
            if current_price <= current_lower:
                return 'oversold'
            elif current_price >= current_upper:
                return 'overbought'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def _check_momentum_confirmation(self) -> float:
        """Check price momentum for additional confirmation"""
        try:
            if len(self.bars_data) < 10:
                return 0.0
            
            # Calculate 5-period price momentum
            current_price = self.bars_data['close'].iloc[-1]
            past_price = self.bars_data['close'].iloc[-6]  # 5 periods ago
            
            momentum = (current_price - past_price) / past_price
            return momentum
            
        except Exception:
            return 0.0
    
    def _calculate_enhanced_signal_strength(
        self, rsi2: float, rsi14: float, signal_type: str, base_strength: float
    ) -> SignalStrength:
        """Enhanced signal strength calculation with multiple factors"""
        
        # Base strength from RSI extremes
        strength_score = base_strength
        
        # RSI divergence factor (RSI2 vs RSI14)
        if signal_type == "BUY":
            # Stronger if both RSI2 and RSI14 are oversold
            if rsi14 < 30:
                strength_score += 0.2
            # RSI2 more extreme than RSI14 is good
            if rsi2 < rsi14:
                strength_score += 0.1
        else:  # SELL
            # Stronger if both RSI2 and RSI14 are overbought
            if rsi14 > 70:
                strength_score += 0.2
            # RSI2 more extreme than RSI14 is good
            if rsi2 > rsi14:
                strength_score += 0.1
        
        # Regime-based strength adjustment
        if self.current_regime == MarketRegime.MEAN_REVERTING:
            strength_score += 0.15  # Best regime for mean reversion
        elif self.current_regime == MarketRegime.LOW_VOLATILITY:
            strength_score += 0.1   # Good regime for mean reversion
        elif self.current_regime == MarketRegime.VOLATILE:
            strength_score -= 0.1   # Risky for mean reversion
        
        # Convert to enum
        if strength_score >= 0.8:
            return SignalStrength.VERY_STRONG
        elif strength_score >= 0.6:
            return SignalStrength.STRONG
        elif strength_score >= 0.4:
            return SignalStrength.MODERATE
        elif strength_score >= 0.2:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK
    
    def _calculate_enhanced_confidence(
        self, rsi2: float, rsi14: float, volume_confirmation: bool,
        timeframe_confirmation: TimeframeConfirmation, bollinger_confirmation: str
    ) -> float:
        """Enhanced confidence calculation with multiple confirmation factors"""
        base_confidence = 0.4
        
        # RSI extreme level confidence (more extreme = higher confidence)
        rsi_extreme_factor = 0
        if rsi2 <= 5 or rsi2 >= 95:
            rsi_extreme_factor = 0.25
        elif rsi2 <= 10 or rsi2 >= 90:
            rsi_extreme_factor = 0.2
        elif rsi2 <= 15 or rsi2 >= 85:
            rsi_extreme_factor = 0.15
        elif rsi2 <= 20 or rsi2 >= 80:
            rsi_extreme_factor = 0.1
        
        base_confidence += rsi_extreme_factor
        
        # RSI consistency (RSI2 and RSI14 alignment)
        if (rsi2 < 30 and rsi14 < 40) or (rsi2 > 70 and rsi14 > 60):
            base_confidence += 0.1
        
        # Volume confirmation
        if volume_confirmation:
            base_confidence += 0.15
        
        # Timeframe confirmation
        if timeframe_confirmation in [TimeframeConfirmation.BULLISH, TimeframeConfirmation.BEARISH]:
            base_confidence += 0.1
        # Neutral adds nothing but doesn't penalize
        
        # Bollinger Band confirmation
        if bollinger_confirmation in ['oversold', 'overbought']:
            base_confidence += 0.1
        
        # Regime confidence (weighted)
        base_confidence += self.regime_confidence * 0.2
        
        return min(0.95, max(0.15, base_confidence))
    
    def _calculate_levels(self, entry_price: float, signal_type: str) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit levels"""
        try:
            # Calculate ATR for dynamic levels
            if len(self.bars_data) >= 14:
                atr = TechnicalIndicators.atr(
                    self.bars_data['high'], 
                    self.bars_data['low'], 
                    self.bars_data['close'], 
                    14
                ).iloc[-1]
            else:
                atr = entry_price * 0.02  # 2% fallback
            
            # Regime-adjusted stop loss
            stop_multiplier = self.strategy_config.regime_stop_multiplier.get(self.current_regime, 1.0)
            stop_distance = atr * stop_multiplier
            
            if signal_type == "BUY":
                stop_loss = entry_price - stop_distance
                take_profit = entry_price + (stop_distance * self.strategy_config.profit_target_multiplier)
            else:  # SELL
                stop_loss = entry_price + stop_distance
                take_profit = entry_price - (stop_distance * self.strategy_config.profit_target_multiplier)
            
            return stop_loss, take_profit
            
        except Exception as e:
            logger.error(f"Error calculating levels: {e}")
            # Fallback to percentage-based levels
            stop_pct = self.strategy_config.base_stop_loss_pct
            if signal_type == "BUY":
                return entry_price * (1 - stop_pct), entry_price * (1 + stop_pct * 2)
            else:
                return entry_price * (1 + stop_pct), entry_price * (1 - stop_pct * 2)
    
    def _execute_signal(self, signal: RSI2Signal):
        """Execute trading signal"""
        try:
            # Check if we already have a position
            if self.portfolio.is_flat():
                # Calculate position size
                position_size = self._calculate_position_size(signal)
                
                if position_size > 0:
                    # Create and submit order
                    if signal.signal_type == "BUY":
                        order = self._create_market_order(OrderSide.BUY, position_size)
                    else:
                        order = self._create_market_order(OrderSide.SELL, position_size)
                    
                    self.submit_order(order)
                    self.position_entry_time = datetime.now()
                    
                    logger.info(f"Executed {signal.signal_type} signal: {signal.strength.name} strength, {signal.confidence:.2f} confidence")
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
    
    def _calculate_position_size(self, signal: RSI2Signal) -> float:
        """Calculate position size based on risk management rules"""
        try:
            # Base position size
            portfolio_value = float(self.portfolio.base_currency_balance())
            base_size = portfolio_value * self.strategy_config.max_position_size
            
            # Adjust based on signal strength and confidence
            strength_multiplier = signal.strength.value / 5.0  # 0.2 to 1.0
            confidence_multiplier = signal.confidence
            
            adjusted_size = base_size * strength_multiplier * confidence_multiplier
            
            # Regime-based adjustment
            if self.current_regime == MarketRegime.VOLATILE:
                adjusted_size *= 0.7  # Reduce size in volatile markets
            elif self.current_regime == MarketRegime.LOW_VOLATILITY:
                adjusted_size *= 1.2  # Increase size in low volatility
            
            return max(0, adjusted_size)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    def _create_market_order(self, side: OrderSide, quantity: float) -> MarketOrder:
        """Create market order"""
        # This would need to be adapted based on the specific instrument
        # For now, using placeholder values
        instrument_id = InstrumentId.from_str("AAPL.NASDAQ")  # Placeholder
        
        return MarketOrder(
            trader_id=self.trader_id,
            strategy_id=self.id,
            instrument_id=instrument_id,
            order_side=side,
            quantity=quantity,
            time_in_force=TimeInForce.GTC,
            reduce_only=False
        )
    
    def _manage_positions(self):
        """Enhanced position management with dynamic risk controls"""
        try:
            if not self.portfolio.is_flat() and self.position_entry_time:
                # Check maximum holding period
                holding_time = datetime.now() - self.position_entry_time
                if holding_time.days >= self.strategy_config.max_holding_period:
                    self._close_all_positions("Max holding period reached")
                
                # Check for regime change
                if (self.current_regime in [MarketRegime.VOLATILE, MarketRegime.UNKNOWN] and 
                    self.regime_confidence > 0.7):
                    self._close_all_positions("Unfavorable regime detected")
                
                # Dynamic stop loss adjustment based on regime
                self._adjust_stop_losses()
                
                # Check for profit taking opportunities
                self._check_profit_taking()
            
        except Exception as e:
            logger.error(f"Error managing positions: {e}")
    
    def _adjust_stop_losses(self):
        """Dynamically adjust stop losses based on current market conditions"""
        try:
            # This would be implemented based on the specific trading platform
            # For now, we'll log the intention
            if self.current_regime == MarketRegime.VOLATILE:
                logger.info("Considering tighter stops due to volatile regime")
            elif self.current_regime == MarketRegime.LOW_VOLATILITY:
                logger.info("Considering wider stops due to low volatility regime")
        except Exception as e:
            logger.error(f"Error adjusting stop losses: {e}")
    
    def _check_profit_taking(self):
        """Check for profit taking opportunities based on RSI levels"""
        try:
            if len(self.bars_data) < self.strategy_config.rsi_short_period:
                return
            
            rsi2 = TechnicalIndicators.rsi(self.bars_data['close'], self.strategy_config.rsi_short_period)
            current_rsi2 = rsi2.iloc[-1]
            
            # If RSI2 has moved to opposite extreme, consider profit taking
            for position in self.portfolio.positions_open():
                if (position.side == OrderSide.BUY and current_rsi2 >= 80) or \
                   (position.side == OrderSide.SELL and current_rsi2 <= 20):
                    logger.info(f"RSI2 at opposite extreme ({current_rsi2:.1f}), considering profit taking")
                    
        except Exception as e:
            logger.error(f"Error checking profit taking: {e}")
    
    def _close_all_positions(self, reason: str):
        """Close all open positions"""
        try:
            for position in self.portfolio.positions_open():
                # Create closing order
                close_side = OrderSide.SELL if position.side == OrderSide.BUY else OrderSide.BUY
                close_order = MarketOrder(
                    trader_id=self.trader_id,
                    strategy_id=self.id,
                    instrument_id=position.instrument_id,
                    order_side=close_side,
                    quantity=abs(position.quantity),
                    time_in_force=TimeInForce.GTC,
                    reduce_only=True
                )
                
                self.submit_order(close_order)
                logger.info(f"Closed position: {reason}")
            
            self.position_entry_time = None
            
        except Exception as e:
            logger.error(f"Error closing positions: {e}")
    
    def on_order_filled(self, event: OrderFilled):
        """Handle order filled events"""
        self.total_trades += 1
        
        # Update P&L tracking
        if hasattr(event, 'last_px') and hasattr(event, 'last_qty'):
            trade_value = float(event.last_px) * float(event.last_qty)
            
            # This is simplified - in practice, you'd track entry/exit prices
            if event.order_side == OrderSide.SELL:
                self.total_pnl += trade_value
            else:
                self.total_pnl -= trade_value
        
        logger.info(f"Order filled: {event.order_side} {event.last_qty} @ {event.last_px}")
    
    def on_stop(self):
        """Called when strategy stops"""
        logger.info(f"RSI(2) Strategy stopped. Total trades: {self.total_trades}, Total P&L: {self.total_pnl:.2f}")
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get comprehensive strategy performance statistics"""
        win_rate = (self.winning_trades / max(1, self.total_trades)) * 100
        
        # Calculate additional performance metrics
        avg_pnl_per_trade = self.total_pnl / max(1, self.total_trades)
        
        # Signal quality metrics
        signal_stats = self._calculate_signal_statistics()
        
        # Regime statistics
        regime_stats = self.regime_classifier.get_regime_statistics()
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'avg_pnl_per_trade': avg_pnl_per_trade,
            'current_regime': self.current_regime.value,
            'regime_confidence': self.regime_confidence,
            'signals_generated': len(self.signals_history),
            'last_signal': self.signals_history[-1].__dict__ if self.signals_history else None,
            'signal_quality': signal_stats,
            'regime_classifier': regime_stats,
            'data_points': len(self.bars_data),
            'last_update': datetime.now().isoformat()
        }
    
    def _calculate_signal_statistics(self) -> Dict[str, Any]:
        """Calculate signal quality statistics"""
        if not self.signals_history:
            return {'avg_confidence': 0, 'signal_distribution': {}, 'regime_distribution': {}}
        
        # Average confidence
        avg_confidence = sum(s.confidence for s in self.signals_history) / len(self.signals_history)
        
        # Signal type distribution
        signal_types = [s.signal_type for s in self.signals_history]
        signal_distribution = {}
        for signal_type in set(signal_types):
            signal_distribution[signal_type] = signal_types.count(signal_type)
        
        # Regime distribution when signals were generated
        regime_types = [s.regime.value for s in self.signals_history]
        regime_distribution = {}
        for regime in set(regime_types):
            regime_distribution[regime] = regime_types.count(regime)
        
        return {
            'avg_confidence': avg_confidence,
            'signal_distribution': signal_distribution,
            'regime_distribution': regime_distribution,
            'total_signals': len(self.signals_history)
        }
    
    def _pre_execution_risk_check(self, signal: RSI2Signal) -> bool:
        """Pre-execution risk checks"""
        try:
            # Check if we already have a position in the same direction
            current_positions = self.portfolio.positions_open()
            for position in current_positions:
                if ((signal.signal_type == 'BUY' and position.side == OrderSide.BUY) or
                    (signal.signal_type == 'SELL' and position.side == OrderSide.SELL)):
                    logger.warning(f"Already have position in {signal.signal_type} direction")
                    return False
            
            # Check confidence threshold
            if signal.confidence < 0.6:
                logger.warning(f"Signal confidence {signal.confidence:.2f} below threshold")
                return False
            
            # Check regime suitability
            if (signal.regime == MarketRegime.VOLATILE and signal.regime_confidence > 0.8):
                logger.warning("High confidence volatile regime - skipping mean reversion")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in pre-execution risk check: {e}")
            return False
    
    def _update_execution_stats(self, signal: RSI2Signal, position_size: int):
        """Update execution statistics"""
        try:
            # Track signal execution metrics
            if not hasattr(self, 'execution_stats'):
                self.execution_stats = {
                    'signals_executed': 0,
                    'avg_position_size': 0,
                    'regime_execution_count': {},
                    'strength_execution_count': {}
                }
            
            self.execution_stats['signals_executed'] += 1
            
            # Update average position size
            prev_avg = self.execution_stats['avg_position_size']
            count = self.execution_stats['signals_executed']
            self.execution_stats['avg_position_size'] = ((prev_avg * (count - 1)) + position_size) / count
            
            # Track regime execution
            regime_key = signal.regime.value
            self.execution_stats['regime_execution_count'][regime_key] = \
                self.execution_stats['regime_execution_count'].get(regime_key, 0) + 1
            
            # Track strength execution
            strength_key = signal.signal_strength.value
            self.execution_stats['strength_execution_count'][strength_key] = \
                self.execution_stats['strength_execution_count'].get(strength_key, 0) + 1
            
        except Exception as e:
            logger.error(f"Error updating execution stats: {e}")

# ===========================================
# FACTORY FUNCTION
# ===========================================

def create_rsi2_strategy(config: Optional[StrategyConfig] = None) -> RSI2MeanReversionStrategy:
    """Factory function to create RSI(2) strategy"""
    if config is None:
        config = StrategyConfig()
    
    strategy = RSI2MeanReversionStrategy(config)
    logger.info("RSI(2) Mean Reversion Strategy created successfully")
    
    return strategy

# Example usage and testing
if __name__ == "__main__":
    # Create strategy with custom configuration
    config = StrategyConfig(
        rsi_oversold=8.0,
        rsi_overbought=92.0,
        max_position_size=0.03,
        n_clusters=4,
        retrain_frequency=14  # More frequent retraining
    )
    
    strategy = create_rsi2_strategy(config)
    
    # Display enhanced configuration
    print("Enhanced RSI(2) Mean Reversion Strategy Configuration:")
    print(f"RSI Short Period: {config.rsi_short_period}")
    print(f"RSI Long Period: {config.rsi_long_period}")
    print(f"Oversold Threshold: {config.rsi_oversold}")
    print(f"Overbought Threshold: {config.rsi_overbought}")
    print(f"Max Position Size: {config.max_position_size * 100}%")
    print(f"ML Clusters: {config.n_clusters}")
    print(f"Retrain Frequency: {config.retrain_frequency} days")
    print(f"Volume Threshold: {config.volume_threshold}")
    print(f"Max Holding Period: {config.max_holding_period} days")
    print(f"Profit Target Multiplier: {config.profit_target_multiplier}")
    
    # Display regime-specific stop loss multipliers
    print("\nRegime-Specific Stop Loss Multipliers:")
    for regime, multiplier in config.regime_stop_multiplier.items():
        print(f"  {regime.value}: {multiplier}x")
    
    print("\nStrategy Features:")
    print("- Multi-timeframe confirmation")
    print("- ML-based market regime classification")
    print("- Volume-weighted RSI calculations")
    print("- Dynamic position sizing")
    print("- Regime-aware risk management")
    print("- Enhanced signal filtering")
    print("- Comprehensive performance tracking")