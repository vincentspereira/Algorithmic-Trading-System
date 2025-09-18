"""Market Regime Detection Pillar

ML-powered market regime detection using clustering algorithms,
volatility analysis, and correlation patterns for adaptive strategy behavior.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class MarketRegime(Enum):
    """Market regime types"""
    TRENDING_BULL = "trending_bull"
    TRENDING_BEAR = "trending_bear"
    SIDEWAYS_CHOPPY = "sideways_choppy"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"

class RegimeStrength(Enum):
    """Regime strength levels"""
    VERY_WEAK = 0.2
    WEAK = 0.4
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 1.0

@dataclass
class RegimeFeatures:
    """Market regime feature set"""
    volatility: float = 0.0
    trend_strength: float = 0.0
    momentum: float = 0.0
    volume_trend: float = 0.0
    correlation_breakdown: float = 0.0
    vix_level: float = 0.0
    drawdown: float = 0.0
    skewness: float = 0.0
    kurtosis: float = 0.0
    hurst_exponent: float = 0.5
    fractal_dimension: float = 1.5
    
    def to_array(self) -> np.ndarray:
        """Convert features to numpy array"""
        return np.array([
            self.volatility, self.trend_strength, self.momentum,
            self.volume_trend, self.correlation_breakdown, self.vix_level,
            self.drawdown, self.skewness, self.kurtosis,
            self.hurst_exponent, self.fractal_dimension
        ])

@dataclass
class RegimeDetection:
    """Market regime detection result"""
    regime: MarketRegime
    confidence: float
    strength: RegimeStrength
    features: RegimeFeatures
    regime_duration: int = 0  # Days in current regime
    regime_stability: float = 0.0  # How stable the regime is
    transition_probability: Dict[MarketRegime, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_strategy_recommendations(self) -> Dict[str, float]:
        """Get strategy allocation recommendations based on regime"""
        recommendations = {
            "mean_reversion": 0.0,
            "trend_following": 0.0,
            "volatility_breakout": 0.0,
            "market_neutral": 0.0,
            "momentum": 0.0
        }
        
        if self.regime == MarketRegime.TRENDING_BULL:
            recommendations["trend_following"] = 0.4 * self.confidence
            recommendations["momentum"] = 0.3 * self.confidence
            recommendations["volatility_breakout"] = 0.2 * self.confidence
            recommendations["market_neutral"] = 0.1
            
        elif self.regime == MarketRegime.TRENDING_BEAR:
            recommendations["trend_following"] = 0.3 * self.confidence
            recommendations["market_neutral"] = 0.4 * self.confidence
            recommendations["volatility_breakout"] = 0.2 * self.confidence
            recommendations["mean_reversion"] = 0.1 * self.confidence
            
        elif self.regime == MarketRegime.SIDEWAYS_CHOPPY:
            recommendations["mean_reversion"] = 0.5 * self.confidence
            recommendations["market_neutral"] = 0.3 * self.confidence
            recommendations["volatility_breakout"] = 0.1 * self.confidence
            recommendations["trend_following"] = 0.1 * self.confidence
            
        elif self.regime == MarketRegime.HIGH_VOLATILITY:
            recommendations["volatility_breakout"] = 0.4 * self.confidence
            recommendations["market_neutral"] = 0.3 * self.confidence
            recommendations["momentum"] = 0.2 * self.confidence
            recommendations["mean_reversion"] = 0.1 * self.confidence
            
        elif self.regime == MarketRegime.LOW_VOLATILITY:
            recommendations["mean_reversion"] = 0.4 * self.confidence
            recommendations["trend_following"] = 0.3 * self.confidence
            recommendations["market_neutral"] = 0.2 * self.confidence
            recommendations["volatility_breakout"] = 0.1 * self.confidence
            
        elif self.regime == MarketRegime.CRISIS:
            recommendations["market_neutral"] = 0.6 * self.confidence
            recommendations["volatility_breakout"] = 0.2 * self.confidence
            recommendations["trend_following"] = 0.1 * self.confidence
            recommendations["mean_reversion"] = 0.1 * self.confidence
            
        elif self.regime == MarketRegime.RECOVERY:
            recommendations["momentum"] = 0.4 * self.confidence
            recommendations["trend_following"] = 0.3 * self.confidence
            recommendations["volatility_breakout"] = 0.2 * self.confidence
            recommendations["mean_reversion"] = 0.1 * self.confidence
            
        return recommendations

class FeatureExtractor:
    """Extract market regime features from price data"""
    
    @staticmethod
    def calculate_volatility(returns: pd.Series, window: int = 20) -> float:
        """Calculate rolling volatility"""
        return returns.rolling(window).std().iloc[-1] * np.sqrt(252)
    
    @staticmethod
    def calculate_trend_strength(prices: pd.Series, window: int = 50) -> float:
        """Calculate trend strength using linear regression slope"""
        if len(prices) < window:
            return 0.0
            
        recent_prices = prices.tail(window)
        x = np.arange(len(recent_prices))
        slope = np.polyfit(x, recent_prices.values, 1)[0]
        
        # Normalize slope by price level
        normalized_slope = slope / recent_prices.mean()
        return np.tanh(normalized_slope * 100)  # Bounded between -1 and 1
    
    @staticmethod
    def calculate_momentum(returns: pd.Series, window: int = 20) -> float:
        """Calculate momentum using cumulative returns"""
        if len(returns) < window:
            return 0.0
            
        cumulative_return = (1 + returns.tail(window)).prod() - 1
        return np.tanh(cumulative_return * 10)  # Bounded momentum
    
    @staticmethod
    def calculate_volume_trend(volume: pd.Series, window: int = 20) -> float:
        """Calculate volume trend"""
        if len(volume) < window:
            return 0.0
            
        recent_volume = volume.tail(window)
        avg_volume = recent_volume.mean()
        current_volume = recent_volume.iloc[-1]
        
        return (current_volume - avg_volume) / avg_volume
    
    @staticmethod
    def calculate_correlation_breakdown(returns: pd.Series, market_returns: pd.Series, window: int = 60) -> float:
        """Calculate correlation breakdown with market"""
        if len(returns) < window or len(market_returns) < window:
            return 0.0
            
        recent_corr = returns.tail(window).corr(market_returns.tail(window))
        long_term_corr = returns.tail(window * 3).corr(market_returns.tail(window * 3))
        
        return abs(recent_corr - long_term_corr)
    
    @staticmethod
    def calculate_drawdown(prices: pd.Series) -> float:
        """Calculate maximum drawdown"""
        peak = prices.expanding().max()
        drawdown = (prices - peak) / peak
        return abs(drawdown.min())
    
    @staticmethod
    def calculate_hurst_exponent(prices: pd.Series, max_lag: int = 20) -> float:
        """Calculate Hurst exponent for trend persistence"""
        if len(prices) < max_lag * 2:
            return 0.5
            
        lags = range(2, max_lag)
        tau = [np.sqrt(np.std(np.subtract(prices[lag:], prices[:-lag]))) for lag in lags]
        
        try:
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0
        except:
            return 0.5
    
    @staticmethod
    def calculate_fractal_dimension(prices: pd.Series) -> float:
        """Calculate fractal dimension"""
        hurst = FeatureExtractor.calculate_hurst_exponent(prices)
        return 2 - hurst
    
    @staticmethod
    def extract_features(data: pd.DataFrame, market_data: Optional[pd.DataFrame] = None) -> RegimeFeatures:
        """Extract all regime features from price data"""
        if len(data) < 50:
            return RegimeFeatures()
            
        prices = data['close']
        returns = prices.pct_change().dropna()
        volume = data['volume']
        
        features = RegimeFeatures()
        
        try:
            features.volatility = FeatureExtractor.calculate_volatility(returns)
            features.trend_strength = FeatureExtractor.calculate_trend_strength(prices)
            features.momentum = FeatureExtractor.calculate_momentum(returns)
            features.volume_trend = FeatureExtractor.calculate_volume_trend(volume)
            features.drawdown = FeatureExtractor.calculate_drawdown(prices)
            features.skewness = returns.tail(60).skew()
            features.kurtosis = returns.tail(60).kurtosis()
            features.hurst_exponent = FeatureExtractor.calculate_hurst_exponent(prices)
            features.fractal_dimension = FeatureExtractor.calculate_fractal_dimension(prices)
            
            # Market correlation if available
            if market_data is not None and len(market_data) >= len(data):
                market_returns = market_data['close'].pct_change().dropna()
                features.correlation_breakdown = FeatureExtractor.calculate_correlation_breakdown(
                    returns, market_returns
                )
            
            # VIX level (if available in data)
            if 'vix' in data.columns:
                features.vix_level = data['vix'].iloc[-1]
                
        except Exception as e:
            logger.warning(f"Error extracting features: {e}")
            
        return features

class RegimeClassifier:
    """ML-based market regime classifier"""
    
    def __init__(self, n_clusters: int = 7, use_pca: bool = True, pca_components: int = 5):
        self.n_clusters = n_clusters
        self.use_pca = use_pca
        self.pca_components = pca_components
        
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=pca_components) if use_pca else None
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.dbscan = DBSCAN(eps=0.5, min_samples=5)
        
        self.is_fitted = False
        self.regime_mapping = {}
        self.feature_history = []
        
    def fit(self, features_list: List[RegimeFeatures]) -> None:
        """Fit the regime classifier"""
        if len(features_list) < self.n_clusters * 3:
            logger.warning(f"Insufficient data for clustering: {len(features_list)} samples")
            return
            
        # Convert features to array
        X = np.array([f.to_array() for f in features_list])
        
        # Handle NaN values
        X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Apply PCA if enabled
        if self.use_pca:
            X_scaled = self.pca.fit_transform(X_scaled)
            
        # Fit clustering models
        kmeans_labels = self.kmeans.fit_predict(X_scaled)
        
        # Create regime mapping based on cluster characteristics
        self._create_regime_mapping(X, kmeans_labels)
        
        self.is_fitted = True
        self.feature_history = features_list
        
        logger.info(f"Regime classifier fitted with {len(features_list)} samples")
    
    def predict(self, features: RegimeFeatures) -> Tuple[MarketRegime, float]:
        """Predict market regime"""
        if not self.is_fitted:
            return MarketRegime.UNKNOWN, 0.0
            
        try:
            # Prepare features
            X = features.to_array().reshape(1, -1)
            X = np.nan_to_num(X, nan=0.0, posinf=1.0, neginf=-1.0)
            
            # Scale and transform
            X_scaled = self.scaler.transform(X)
            if self.use_pca:
                X_scaled = self.pca.transform(X_scaled)
                
            # Predict cluster
            cluster = self.kmeans.predict(X_scaled)[0]
            
            # Get regime and confidence
            regime = self.regime_mapping.get(cluster, MarketRegime.UNKNOWN)
            
            # Calculate confidence based on distance to cluster center
            distances = self.kmeans.transform(X_scaled)[0]
            min_distance = distances[cluster]
            max_distance = np.max(distances)
            confidence = 1.0 - (min_distance / max_distance) if max_distance > 0 else 0.5
            
            return regime, confidence
            
        except Exception as e:
            logger.error(f"Error predicting regime: {e}")
            return MarketRegime.UNKNOWN, 0.0
    
    def _create_regime_mapping(self, X: np.ndarray, labels: np.ndarray) -> None:
        """Create mapping from clusters to market regimes"""
        self.regime_mapping = {}
        
        for cluster in range(self.n_clusters):
            cluster_mask = labels == cluster
            if not np.any(cluster_mask):
                continue
                
            cluster_features = X[cluster_mask]
            avg_features = np.mean(cluster_features, axis=0)
            
            # Map based on feature characteristics
            volatility = avg_features[0]
            trend_strength = avg_features[1]
            momentum = avg_features[2]
            drawdown = avg_features[6]
            
            # Regime classification logic
            if drawdown > 0.15:  # High drawdown
                regime = MarketRegime.CRISIS
            elif volatility > 0.3:  # High volatility
                if momentum > 0.1:
                    regime = MarketRegime.RECOVERY
                else:
                    regime = MarketRegime.HIGH_VOLATILITY
            elif volatility < 0.1:  # Low volatility
                regime = MarketRegime.LOW_VOLATILITY
            elif abs(trend_strength) > 0.3:  # Strong trend
                if trend_strength > 0:
                    regime = MarketRegime.TRENDING_BULL
                else:
                    regime = MarketRegime.TRENDING_BEAR
            else:  # Sideways market
                regime = MarketRegime.SIDEWAYS_CHOPPY
                
            self.regime_mapping[cluster] = regime
            
        logger.info(f"Created regime mapping: {self.regime_mapping}")

class MarketRegimeDetector:
    """Main market regime detection system"""
    
    def __init__(self, lookback_period: int = 252, update_frequency: int = 5):
        self.lookback_period = lookback_period
        self.update_frequency = update_frequency
        self.feature_extractor = FeatureExtractor()
        self.classifier = RegimeClassifier()
        
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history = []
        self.last_update = None
        self.regime_start_date = None
        
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    async def detect_regime(self, data: pd.DataFrame, market_data: Optional[pd.DataFrame] = None) -> RegimeDetection:
        """Detect current market regime"""
        try:
            # Extract features
            features = await self._extract_features_async(data, market_data)
            
            # Update classifier if needed
            await self._update_classifier_if_needed(data, market_data)
            
            # Predict regime
            regime, confidence = self.classifier.predict(features)
            
            # Calculate regime strength
            strength = self._calculate_regime_strength(confidence)
            
            # Calculate regime duration and stability
            duration = self._calculate_regime_duration(regime)
            stability = self._calculate_regime_stability()
            
            # Calculate transition probabilities
            transition_probs = self._calculate_transition_probabilities()
            
            detection = RegimeDetection(
                regime=regime,
                confidence=confidence,
                strength=strength,
                features=features,
                regime_duration=duration,
                regime_stability=stability,
                transition_probability=transition_probs
            )
            
            # Update history
            self._update_regime_history(detection)
            
            return detection
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return RegimeDetection(
                regime=MarketRegime.UNKNOWN,
                confidence=0.0,
                strength=RegimeStrength.VERY_WEAK,
                features=RegimeFeatures()
            )
    
    async def _extract_features_async(self, data: pd.DataFrame, market_data: Optional[pd.DataFrame]) -> RegimeFeatures:
        """Extract features asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.feature_extractor.extract_features, 
            data, 
            market_data
        )
    
    async def _update_classifier_if_needed(self, data: pd.DataFrame, market_data: Optional[pd.DataFrame]) -> None:
        """Update classifier with new data if needed"""
        current_time = datetime.now(timezone.utc)
        
        # Check if update is needed
        if (self.last_update is None or 
            (current_time - self.last_update).days >= self.update_frequency or
            not self.classifier.is_fitted):
            
            # Extract historical features for training
            if len(data) >= self.lookback_period:
                features_list = []
                
                # Sample data points for training
                sample_indices = np.linspace(0, len(data) - 50, min(100, len(data) // 10), dtype=int)
                
                for i in sample_indices:
                    sample_data = data.iloc[i:i+50]
                    sample_market = market_data.iloc[i:i+50] if market_data is not None else None
                    
                    features = self.feature_extractor.extract_features(sample_data, sample_market)
                    features_list.append(features)
                
                # Fit classifier
                if len(features_list) >= 20:
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor, 
                        self.classifier.fit, 
                        features_list
                    )
                    
                    self.last_update = current_time
                    logger.info("Regime classifier updated")
    
    def _calculate_regime_strength(self, confidence: float) -> RegimeStrength:
        """Calculate regime strength from confidence"""
        if confidence >= 0.9:
            return RegimeStrength.VERY_STRONG
        elif confidence >= 0.7:
            return RegimeStrength.STRONG
        elif confidence >= 0.5:
            return RegimeStrength.MODERATE
        elif confidence >= 0.3:
            return RegimeStrength.WEAK
        else:
            return RegimeStrength.VERY_WEAK
    
    def _calculate_regime_duration(self, regime: MarketRegime) -> int:
        """Calculate how long current regime has been active"""
        if regime != self.current_regime:
            self.current_regime = regime
            self.regime_start_date = datetime.now(timezone.utc)
            return 0
        elif self.regime_start_date:
            return (datetime.now(timezone.utc) - self.regime_start_date).days
        else:
            return 0
    
    def _calculate_regime_stability(self) -> float:
        """Calculate regime stability based on recent history"""
        if len(self.regime_history) < 10:
            return 0.5
            
        recent_regimes = [r.regime for r in self.regime_history[-10:]]
        most_common = max(set(recent_regimes), key=recent_regimes.count)
        stability = recent_regimes.count(most_common) / len(recent_regimes)
        
        return stability
    
    def _calculate_transition_probabilities(self) -> Dict[MarketRegime, float]:
        """Calculate transition probabilities to other regimes"""
        if len(self.regime_history) < 20:
            return {regime: 0.1 for regime in MarketRegime}
            
        # Analyze historical transitions
        transitions = {}
        for i in range(1, len(self.regime_history)):
            prev_regime = self.regime_history[i-1].regime
            curr_regime = self.regime_history[i].regime
            
            if prev_regime not in transitions:
                transitions[prev_regime] = {}
            if curr_regime not in transitions[prev_regime]:
                transitions[prev_regime][curr_regime] = 0
                
            transitions[prev_regime][curr_regime] += 1
        
        # Calculate probabilities for current regime
        current_regime = self.current_regime
        if current_regime in transitions:
            total_transitions = sum(transitions[current_regime].values())
            probs = {}
            for regime, count in transitions[current_regime].items():
                probs[regime] = count / total_transitions
            return probs
        else:
            return {regime: 0.1 for regime in MarketRegime}
    
    def _update_regime_history(self, detection: RegimeDetection) -> None:
        """Update regime history"""
        self.regime_history.append(detection)
        
        # Keep only recent history
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-500:]
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get summary of current regime state"""
        if not self.regime_history:
            return {"status": "No regime data available"}
            
        latest = self.regime_history[-1]
        
        return {
            "current_regime": latest.regime.value,
            "confidence": latest.confidence,
            "strength": latest.strength.value,
            "duration_days": latest.regime_duration,
            "stability": latest.regime_stability,
            "strategy_recommendations": latest.get_strategy_recommendations(),
            "last_updated": latest.timestamp.isoformat()
        }