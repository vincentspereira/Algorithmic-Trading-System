#!/usr/bin/env python3
"""
Clustering Strategies Module for Algorithmic Trading System

This module implements unsupervised machine learning strategies for market regime detection,
anomaly detection, and pattern recognition. It follows the 5-Pillar Architecture:
1. Data Management: Feature extraction and preprocessing
2. Strategy Logic: Clustering algorithms and regime detection
3. Risk Management: Regime-aware risk controls
4. Execution Management: Adaptive position sizing
5. Performance Analytics: Regime-based performance analysis

Author: Algorithmic Trading System
Version: 1.0.0
Date: 2024
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Core ML libraries
try:
    from sklearn.cluster import KMeans, DBSCAN, GaussianMixture
    from sklearn.preprocessing import StandardScaler, RobustScaler
    from sklearn.decomposition import PCA
    from sklearn.metrics import silhouette_score, calinski_harabasz_score
    from sklearn.ensemble import IsolationForest
    from sklearn.svm import OneClassSVM
    from sklearn.covariance import EllipticEnvelope
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Clustering strategies will use fallback implementations.")

try:
    import scipy.stats as stats
    from scipy.spatial.distance import pdist, squareform
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("SciPy not available. Some statistical functions will be limited.")

# Import feature engineering
from .feature_engineering import FeatureEngineer, FeatureConfig

class RegimeType(Enum):
    """Market regime types"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"

class ClusteringMethod(Enum):
    """Clustering algorithm types"""
    KMEANS = "kmeans"
    GAUSSIAN_MIXTURE = "gaussian_mixture"
    DBSCAN = "dbscan"
    HIERARCHICAL = "hierarchical"
    SPECTRAL = "spectral"

class AnomalyMethod(Enum):
    """Anomaly detection methods"""
    ISOLATION_FOREST = "isolation_forest"
    ONE_CLASS_SVM = "one_class_svm"
    ELLIPTIC_ENVELOPE = "elliptic_envelope"
    LOCAL_OUTLIER_FACTOR = "local_outlier_factor"
    STATISTICAL = "statistical"

@dataclass
class RegimeState:
    """Current market regime state"""
    regime_type: RegimeType
    confidence: float
    duration: int  # Number of periods in current regime
    stability: float  # Regime stability score
    transition_probability: Dict[RegimeType, float] = field(default_factory=dict)
    features: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ClusteringConfig:
    """Configuration for clustering strategies"""
    # Clustering parameters
    n_clusters: int = 4
    clustering_method: ClusteringMethod = ClusteringMethod.KMEANS
    lookback_period: int = 252  # 1 year of daily data
    min_regime_duration: int = 5  # Minimum periods for regime stability
    
    # Feature selection
    use_technical_features: bool = True
    use_volatility_features: bool = True
    use_volume_features: bool = True
    use_macro_features: bool = False
    
    # Preprocessing
    scaler_type: str = "robust"  # "standard", "robust", "minmax"
    use_pca: bool = True
    pca_components: float = 0.95  # Variance to retain
    
    # Regime detection
    regime_smoothing: int = 3  # Periods for regime smoothing
    confidence_threshold: float = 0.6
    
    # Anomaly detection
    anomaly_method: AnomalyMethod = AnomalyMethod.ISOLATION_FOREST
    anomaly_threshold: float = 0.1  # Fraction of outliers
    
    # Performance
    refit_frequency: int = 21  # Refit model every N periods
    parallel_jobs: int = -1

class MarketRegimeDetector:
    """
    Advanced market regime detection using clustering algorithms
    """
    
    def __init__(self, config: ClusteringConfig):
        self.config = config
        self.feature_engineer = FeatureEngineer(FeatureConfig())
        self.scaler = None
        self.pca = None
        self.clustering_model = None
        self.regime_history: List[RegimeState] = []
        self.features_history: List[pd.DataFrame] = []
        self.last_refit = None
        
        # Initialize models
        self._initialize_models()
        
        # Regime mapping
        self.regime_mapping = {
            0: RegimeType.BULL_MARKET,
            1: RegimeType.BEAR_MARKET,
            2: RegimeType.SIDEWAYS,
            3: RegimeType.HIGH_VOLATILITY
        }
        
        logging.info(f"MarketRegimeDetector initialized with {config.clustering_method.value}")
    
    def _initialize_models(self):
        """Initialize clustering and preprocessing models"""
        if not SKLEARN_AVAILABLE:
            logging.warning("scikit-learn not available. Using fallback implementations.")
            return
        
        # Initialize scaler
        if self.config.scaler_type == "standard":
            self.scaler = StandardScaler()
        elif self.config.scaler_type == "robust":
            self.scaler = RobustScaler()
        else:
            self.scaler = StandardScaler()
        
        # Initialize PCA
        if self.config.use_pca:
            self.pca = PCA(n_components=self.config.pca_components)
        
        # Initialize clustering model
        if self.config.clustering_method == ClusteringMethod.KMEANS:
            self.clustering_model = KMeans(
                n_clusters=self.config.n_clusters,
                random_state=42,
                n_init=10
            )
        elif self.config.clustering_method == ClusteringMethod.GAUSSIAN_MIXTURE:
            self.clustering_model = GaussianMixture(
                n_components=self.config.n_clusters,
                random_state=42
            )
        elif self.config.clustering_method == ClusteringMethod.DBSCAN:
            self.clustering_model = DBSCAN(
                eps=0.5,
                min_samples=5
            )
    
    def extract_regime_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features for regime detection"""
        features = pd.DataFrame(index=data.index)
        
        try:
            # Price-based features
            features['returns'] = data['close'].pct_change()
            features['log_returns'] = np.log(data['close'] / data['close'].shift(1))
            features['price_momentum_5'] = data['close'].pct_change(5)
            features['price_momentum_20'] = data['close'].pct_change(20)
            
            # Volatility features
            features['realized_vol_5'] = features['returns'].rolling(5).std()
            features['realized_vol_20'] = features['returns'].rolling(20).std()
            features['vol_ratio'] = features['realized_vol_5'] / features['realized_vol_20']
            
            # Trend features
            features['sma_5'] = data['close'].rolling(5).mean()
            features['sma_20'] = data['close'].rolling(20).mean()
            features['trend_strength'] = (data['close'] - features['sma_20']) / features['sma_20']
            features['price_position'] = (data['close'] - data['low'].rolling(20).min()) / \
                                       (data['high'].rolling(20).max() - data['low'].rolling(20).min())
            
            # Volume features (if available)
            if 'volume' in data.columns:
                features['volume_sma'] = data['volume'].rolling(20).mean()
                features['volume_ratio'] = data['volume'] / features['volume_sma']
                features['price_volume'] = features['returns'] * np.log(data['volume'])
            
            # Market microstructure
            if all(col in data.columns for col in ['high', 'low', 'open']):
                features['hl_ratio'] = (data['high'] - data['low']) / data['close']
                features['oc_ratio'] = (data['close'] - data['open']) / data['open']
                features['gap'] = (data['open'] - data['close'].shift(1)) / data['close'].shift(1)
            
            # Technical indicators using feature engineer
            if self.config.use_technical_features:
                tech_features = self.feature_engineer.create_technical_features(data)
                # Select key technical features
                tech_cols = ['rsi_14', 'macd_signal', 'bb_position', 'stoch_k']
                for col in tech_cols:
                    if col in tech_features.columns:
                        features[col] = tech_features[col]
            
            # Remove infinite and NaN values
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.fillna(method='ffill').fillna(0)
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting regime features: {e}")
            # Return basic features as fallback
            features['returns'] = data['close'].pct_change().fillna(0)
            features['volatility'] = features['returns'].rolling(20).std().fillna(0)
            return features
    
    def fit(self, data: pd.DataFrame) -> 'MarketRegimeDetector':
        """Fit the regime detection model"""
        try:
            # Extract features
            features = self.extract_regime_features(data)
            
            # Store features history
            self.features_history.append(features)
            
            # Prepare data for clustering
            feature_matrix = features.dropna()
            
            if len(feature_matrix) < self.config.n_clusters:
                logging.warning("Insufficient data for clustering")
                return self
            
            # Scale features
            if self.scaler is not None:
                scaled_features = self.scaler.fit_transform(feature_matrix)
            else:
                scaled_features = feature_matrix.values
            
            # Apply PCA if configured
            if self.pca is not None:
                scaled_features = self.pca.fit_transform(scaled_features)
            
            # Fit clustering model
            if self.clustering_model is not None:
                self.clustering_model.fit(scaled_features)
                
                # Evaluate clustering quality
                if len(np.unique(self.clustering_model.labels_)) > 1:
                    silhouette_avg = silhouette_score(scaled_features, self.clustering_model.labels_)
                    logging.info(f"Clustering silhouette score: {silhouette_avg:.3f}")
            
            self.last_refit = datetime.now()
            logging.info("Market regime detector fitted successfully")
            
        except Exception as e:
            logging.error(f"Error fitting regime detector: {e}")
        
        return self
    
    def predict_regime(self, data: pd.DataFrame) -> RegimeState:
        """Predict current market regime"""
        try:
            # Extract features for latest data
            features = self.extract_regime_features(data)
            latest_features = features.iloc[-1:].dropna()
            
            if len(latest_features) == 0:
                return RegimeState(
                    regime_type=RegimeType.UNKNOWN,
                    confidence=0.0,
                    duration=0,
                    stability=0.0
                )
            
            # Preprocess features
            if self.scaler is not None:
                scaled_features = self.scaler.transform(latest_features)
            else:
                scaled_features = latest_features.values
            
            if self.pca is not None:
                scaled_features = self.pca.transform(scaled_features)
            
            # Predict cluster
            if self.clustering_model is not None:
                cluster_id = self.clustering_model.predict(scaled_features)[0]
                
                # Map cluster to regime type
                regime_type = self.regime_mapping.get(cluster_id, RegimeType.UNKNOWN)
                
                # Calculate confidence
                confidence = self._calculate_confidence(scaled_features, cluster_id)
                
                # Calculate regime duration and stability
                duration = self._calculate_regime_duration(regime_type)
                stability = self._calculate_regime_stability(regime_type)
                
                regime_state = RegimeState(
                    regime_type=regime_type,
                    confidence=confidence,
                    duration=duration,
                    stability=stability,
                    features=latest_features.iloc[0].to_dict()
                )
                
                # Update regime history
                self.regime_history.append(regime_state)
                
                # Keep only recent history
                if len(self.regime_history) > 1000:
                    self.regime_history = self.regime_history[-1000:]
                
                return regime_state
            
        except Exception as e:
            logging.error(f"Error predicting regime: {e}")
        
        return RegimeState(
            regime_type=RegimeType.UNKNOWN,
            confidence=0.0,
            duration=0,
            stability=0.0
        )
    
    def _calculate_confidence(self, features: np.ndarray, cluster_id: int) -> float:
        """Calculate confidence in regime prediction"""
        try:
            if hasattr(self.clustering_model, 'cluster_centers_'):
                # For KMeans, use distance to cluster center
                center = self.clustering_model.cluster_centers_[cluster_id]
                distance = np.linalg.norm(features[0] - center)
                
                # Convert distance to confidence (closer = higher confidence)
                max_distance = np.max([np.linalg.norm(features[0] - c) 
                                     for c in self.clustering_model.cluster_centers_])
                confidence = 1.0 - (distance / max_distance) if max_distance > 0 else 0.5
                
                return max(0.0, min(1.0, confidence))
            
            elif hasattr(self.clustering_model, 'predict_proba'):
                # For Gaussian Mixture, use probability
                probabilities = self.clustering_model.predict_proba(features)
                return float(np.max(probabilities))
            
        except Exception as e:
            logging.error(f"Error calculating confidence: {e}")
        
        return 0.5  # Default confidence
    
    def _calculate_regime_duration(self, current_regime: RegimeType) -> int:
        """Calculate how long we've been in current regime"""
        if not self.regime_history:
            return 0
        
        duration = 0
        for regime_state in reversed(self.regime_history):
            if regime_state.regime_type == current_regime:
                duration += 1
            else:
                break
        
        return duration
    
    def _calculate_regime_stability(self, current_regime: RegimeType) -> float:
        """Calculate regime stability score"""
        if len(self.regime_history) < 10:
            return 0.5
        
        recent_regimes = [rs.regime_type for rs in self.regime_history[-20:]]
        regime_count = recent_regimes.count(current_regime)
        stability = regime_count / len(recent_regimes)
        
        return stability

class AnomalyDetectionStrategy:
    """
    Anomaly detection for identifying unusual market conditions
    """
    
    def __init__(self, config: ClusteringConfig):
        self.config = config
        self.anomaly_detector = None
        self.feature_engineer = FeatureEngineer(FeatureConfig())
        self.scaler = RobustScaler() if SKLEARN_AVAILABLE else None
        self.anomaly_history: List[Tuple[datetime, float, bool]] = []
        
        self._initialize_detector()
    
    def _initialize_detector(self):
        """Initialize anomaly detection model"""
        if not SKLEARN_AVAILABLE:
            logging.warning("scikit-learn not available for anomaly detection")
            return
        
        if self.config.anomaly_method == AnomalyMethod.ISOLATION_FOREST:
            self.anomaly_detector = IsolationForest(
                contamination=self.config.anomaly_threshold,
                random_state=42
            )
        elif self.config.anomaly_method == AnomalyMethod.ONE_CLASS_SVM:
            self.anomaly_detector = OneClassSVM(
                nu=self.config.anomaly_threshold
            )
        elif self.config.anomaly_method == AnomalyMethod.ELLIPTIC_ENVELOPE:
            self.anomaly_detector = EllipticEnvelope(
                contamination=self.config.anomaly_threshold
            )
    
    def fit(self, data: pd.DataFrame) -> 'AnomalyDetectionStrategy':
        """Fit anomaly detection model"""
        try:
            # Extract features
            features = self._extract_anomaly_features(data)
            
            # Scale features
            if self.scaler is not None:
                scaled_features = self.scaler.fit_transform(features.dropna())
            else:
                scaled_features = features.dropna().values
            
            # Fit anomaly detector
            if self.anomaly_detector is not None:
                self.anomaly_detector.fit(scaled_features)
                logging.info("Anomaly detector fitted successfully")
            
        except Exception as e:
            logging.error(f"Error fitting anomaly detector: {e}")
        
        return self
    
    def detect_anomalies(self, data: pd.DataFrame) -> Tuple[bool, float]:
        """Detect if current market conditions are anomalous"""
        try:
            # Extract features
            features = self._extract_anomaly_features(data)
            latest_features = features.iloc[-1:].dropna()
            
            if len(latest_features) == 0:
                return False, 0.5
            
            # Scale features
            if self.scaler is not None:
                scaled_features = self.scaler.transform(latest_features)
            else:
                scaled_features = latest_features.values
            
            # Predict anomaly
            if self.anomaly_detector is not None:
                anomaly_score = self.anomaly_detector.decision_function(scaled_features)[0]
                is_anomaly = self.anomaly_detector.predict(scaled_features)[0] == -1
                
                # Normalize anomaly score to [0, 1]
                normalized_score = (anomaly_score + 1) / 2
                
                # Record anomaly
                self.anomaly_history.append((
                    datetime.now(),
                    normalized_score,
                    is_anomaly
                ))
                
                # Keep only recent history
                if len(self.anomaly_history) > 1000:
                    self.anomaly_history = self.anomaly_history[-1000:]
                
                return is_anomaly, normalized_score
            
        except Exception as e:
            logging.error(f"Error detecting anomalies: {e}")
        
        return False, 0.5
    
    def _extract_anomaly_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Extract features for anomaly detection"""
        features = pd.DataFrame(index=data.index)
        
        try:
            # Price features
            features['returns'] = data['close'].pct_change()
            features['log_returns'] = np.log(data['close'] / data['close'].shift(1))
            features['price_change_5d'] = data['close'].pct_change(5)
            
            # Volatility features
            features['volatility'] = features['returns'].rolling(20).std()
            features['vol_spike'] = features['volatility'] / features['volatility'].rolling(60).mean()
            
            # Volume features (if available)
            if 'volume' in data.columns:
                features['volume_spike'] = data['volume'] / data['volume'].rolling(20).mean()
                features['volume_price_trend'] = features['returns'] * np.log(data['volume'])
            
            # Range features
            if all(col in data.columns for col in ['high', 'low']):
                features['true_range'] = np.maximum(
                    data['high'] - data['low'],
                    np.maximum(
                        abs(data['high'] - data['close'].shift(1)),
                        abs(data['low'] - data['close'].shift(1))
                    )
                )
                features['range_expansion'] = features['true_range'] / features['true_range'].rolling(20).mean()
            
            # Technical indicators
            tech_features = self.feature_engineer.create_technical_features(data)
            if 'rsi_14' in tech_features.columns:
                features['rsi_extreme'] = np.where(
                    (tech_features['rsi_14'] > 80) | (tech_features['rsi_14'] < 20),
                    1, 0
                )
            
            # Statistical features
            features['z_score'] = (features['returns'] - features['returns'].rolling(60).mean()) / \
                                features['returns'].rolling(60).std()
            
            # Clean data
            features = features.replace([np.inf, -np.inf], np.nan)
            features = features.fillna(method='ffill').fillna(0)
            
            return features
            
        except Exception as e:
            logging.error(f"Error extracting anomaly features: {e}")
            # Return basic features
            features['returns'] = data['close'].pct_change().fillna(0)
            return features

class ClusteringStrategy:
    """
    Main clustering strategy that combines regime detection and anomaly detection
    """
    
    def __init__(self, config: ClusteringConfig):
        self.config = config
        self.regime_detector = MarketRegimeDetector(config)
        self.anomaly_detector = AnomalyDetectionStrategy(config)
        self.current_regime: Optional[RegimeState] = None
        self.is_anomalous = False
        self.anomaly_score = 0.0
        
        # Strategy parameters by regime
        self.regime_parameters = {
            RegimeType.BULL_MARKET: {'position_size': 1.0, 'stop_loss': 0.05, 'take_profit': 0.15},
            RegimeType.BEAR_MARKET: {'position_size': 0.5, 'stop_loss': 0.03, 'take_profit': 0.08},
            RegimeType.SIDEWAYS: {'position_size': 0.7, 'stop_loss': 0.02, 'take_profit': 0.05},
            RegimeType.HIGH_VOLATILITY: {'position_size': 0.3, 'stop_loss': 0.02, 'take_profit': 0.10},
            RegimeType.LOW_VOLATILITY: {'position_size': 1.2, 'stop_loss': 0.03, 'take_profit': 0.08}
        }
    
    def fit(self, data: pd.DataFrame) -> 'ClusteringStrategy':
        """Fit both regime detector and anomaly detector"""
        logging.info("Fitting clustering strategy...")
        
        # Fit regime detector
        self.regime_detector.fit(data)
        
        # Fit anomaly detector
        self.anomaly_detector.fit(data)
        
        logging.info("Clustering strategy fitted successfully")
        return self
    
    def update(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Update regime and anomaly detection"""
        # Detect current regime
        self.current_regime = self.regime_detector.predict_regime(data)
        
        # Detect anomalies
        self.is_anomalous, self.anomaly_score = self.anomaly_detector.detect_anomalies(data)
        
        # Get regime-specific parameters
        regime_params = self.regime_parameters.get(
            self.current_regime.regime_type,
            self.regime_parameters[RegimeType.SIDEWAYS]
        )
        
        # Adjust parameters based on anomaly detection
        if self.is_anomalous:
            regime_params = regime_params.copy()
            regime_params['position_size'] *= 0.5  # Reduce position size during anomalies
            regime_params['stop_loss'] *= 0.7     # Tighter stop loss
        
        return {
            'regime': self.current_regime,
            'is_anomalous': self.is_anomalous,
            'anomaly_score': self.anomaly_score,
            'parameters': regime_params,
            'confidence': self.current_regime.confidence if self.current_regime else 0.0
        }
    
    def should_refit(self) -> bool:
        """Check if model should be refitted"""
        if self.regime_detector.last_refit is None:
            return True
        
        days_since_refit = (datetime.now() - self.regime_detector.last_refit).days
        return days_since_refit >= self.config.refit_frequency
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get summary of recent regime history"""
        if not self.regime_detector.regime_history:
            return {}
        
        recent_regimes = self.regime_detector.regime_history[-50:]
        regime_counts = {}
        
        for regime_state in recent_regimes:
            regime_type = regime_state.regime_type
            if regime_type not in regime_counts:
                regime_counts[regime_type] = 0
            regime_counts[regime_type] += 1
        
        total_count = len(recent_regimes)
        regime_distribution = {
            regime.value: count / total_count 
            for regime, count in regime_counts.items()
        }
        
        return {
            'current_regime': self.current_regime.regime_type.value if self.current_regime else 'unknown',
            'regime_distribution': regime_distribution,
            'average_confidence': np.mean([rs.confidence for rs in recent_regimes]),
            'regime_changes': len(set(rs.regime_type for rs in recent_regimes)),
            'anomaly_rate': sum(1 for _, _, is_anom in self.anomaly_detector.anomaly_history[-50:] if is_anom) / min(50, len(self.anomaly_detector.anomaly_history))
        }

# Factory function for creating clustering strategies
def create_clustering_strategy(config: Optional[ClusteringConfig] = None) -> ClusteringStrategy:
    """Factory function to create clustering strategy"""
    if config is None:
        config = ClusteringConfig()
    
    return ClusteringStrategy(config)

# Example usage and testing
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=500, freq='D')
    
    # Simulate different market regimes
    returns = np.concatenate([
        np.random.normal(0.001, 0.01, 100),  # Bull market
        np.random.normal(-0.002, 0.02, 100), # Bear market
        np.random.normal(0.0, 0.005, 100),   # Sideways
        np.random.normal(0.001, 0.03, 100),  # High volatility
        np.random.normal(0.0005, 0.008, 100) # Recovery
    ])
    
    prices = 100 * np.exp(np.cumsum(returns))
    
    sample_data = pd.DataFrame({
        'close': prices,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
        'open': prices + np.random.normal(0, 0.5, len(prices)),
        'volume': np.random.lognormal(10, 1, len(prices))
    }, index=dates)
    
    # Test clustering strategy
    config = ClusteringConfig(
        n_clusters=4,
        clustering_method=ClusteringMethod.KMEANS,
        lookback_period=200
    )
    
    strategy = create_clustering_strategy(config)
    
    # Fit strategy
    strategy.fit(sample_data[:400])
    
    # Test predictions
    for i in range(400, 500, 10):
        result = strategy.update(sample_data[:i])
        print(f"Period {i}: Regime={result['regime'].regime_type.value}, "
              f"Confidence={result['confidence']:.3f}, "
              f"Anomaly={result['is_anomalous']}")
    
    # Print summary
    summary = strategy.get_regime_summary()
    print("\nRegime Summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")