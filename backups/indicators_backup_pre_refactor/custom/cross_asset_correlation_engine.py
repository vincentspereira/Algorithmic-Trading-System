"""Cross-Asset Correlation Analysis and Sector Momentum Tracking Engine

Institutional-grade cross-asset correlation analysis system that:
- Tracks correlations across multiple asset classes
- Implements dynamic correlation matrices with regime awareness
- Provides sector momentum analysis and rotation signals
- Includes correlation-based risk management
- Supports multi-timeframe correlation analysis
- Implements correlation clustering and factor analysis
- Provides real-time correlation monitoring and alerts

Author: Vincent S. Pereira
Version: 2.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import deque, defaultdict
import json
from pathlib import Path
import threading
from concurrent.futures import ThreadPoolExecutor
import math
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram, fcluster
from scipy.spatial.distance import squareform
from sklearn.decomposition import PCA, FactorAnalysis
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("NetworkX not available. Network analysis features disabled.")

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    """Asset class categories"""
    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    CRYPTO = "crypto"
    REAL_ESTATE = "real_estate"
    ALTERNATIVE = "alternative"


class CorrelationType(Enum):
    """Types of correlation analysis"""
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"
    ROLLING = "rolling"
    EXPONENTIAL = "exponential"
    DYNAMIC = "dynamic"


class SectorCategory(Enum):
    """Sector categories for analysis"""
    TECHNOLOGY = "technology"
    HEALTHCARE = "healthcare"
    FINANCIALS = "financials"
    ENERGY = "energy"
    MATERIALS = "materials"
    INDUSTRIALS = "industrials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    UTILITIES = "utilities"
    REAL_ESTATE = "real_estate"
    COMMUNICATION = "communication"


class CorrelationRegime(Enum):
    """Correlation regime types"""
    LOW_CORRELATION = "low_correlation"
    MODERATE_CORRELATION = "moderate_correlation"
    HIGH_CORRELATION = "high_correlation"
    CRISIS_CORRELATION = "crisis_correlation"
    DECOUPLING = "decoupling"


@dataclass
class AssetInfo:
    """Asset information"""
    symbol: str
    name: str
    asset_class: AssetClass
    sector: Optional[SectorCategory] = None
    country: Optional[str] = None
    market_cap: Optional[float] = None
    beta: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'asset_class': self.asset_class.value,
            'sector': self.sector.value if self.sector else None,
            'country': self.country,
            'market_cap': self.market_cap,
            'beta': self.beta
        }


@dataclass
class CorrelationMetrics:
    """Correlation analysis metrics"""
    correlation_matrix: np.ndarray
    correlation_type: CorrelationType
    timestamp: datetime
    lookback_period: int
    
    # Statistical metrics
    avg_correlation: float
    max_correlation: float
    min_correlation: float
    correlation_std: float
    
    # Regime information
    regime: CorrelationRegime
    regime_confidence: float
    
    # Factor analysis
    explained_variance_ratio: Optional[List[float]] = None
    factor_loadings: Optional[np.ndarray] = None
    
    def to_dict(self) -> Dict:
        return {
            'correlation_matrix': self.correlation_matrix.tolist(),
            'correlation_type': self.correlation_type.value,
            'timestamp': self.timestamp.isoformat(),
            'lookback_period': self.lookback_period,
            'avg_correlation': self.avg_correlation,
            'max_correlation': self.max_correlation,
            'min_correlation': self.min_correlation,
            'correlation_std': self.correlation_std,
            'regime': self.regime.value,
            'regime_confidence': self.regime_confidence,
            'explained_variance_ratio': self.explained_variance_ratio,
            'factor_loadings': self.factor_loadings.tolist() if self.factor_loadings is not None else None
        }


@dataclass
class SectorMomentum:
    """Sector momentum analysis"""
    sector: SectorCategory
    momentum_score: float
    relative_strength: float
    trend_direction: str  # 'bullish', 'bearish', 'neutral'
    volatility: float
    
    # Performance metrics
    returns_1d: float
    returns_1w: float
    returns_1m: float
    returns_3m: float
    
    # Technical indicators
    rsi: Optional[float] = None
    macd_signal: Optional[str] = None
    
    # Relative metrics
    vs_market_1m: float = 0.0
    vs_market_3m: float = 0.0
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            'sector': self.sector.value,
            'momentum_score': self.momentum_score,
            'relative_strength': self.relative_strength,
            'trend_direction': self.trend_direction,
            'volatility': self.volatility,
            'returns_1d': self.returns_1d,
            'returns_1w': self.returns_1w,
            'returns_1m': self.returns_1m,
            'returns_3m': self.returns_3m,
            'rsi': self.rsi,
            'macd_signal': self.macd_signal,
            'vs_market_1m': self.vs_market_1m,
            'vs_market_3m': self.vs_market_3m,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class CorrelationAlert:
    """Correlation-based alert"""
    alert_type: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    message: str
    assets_involved: List[str]
    correlation_value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'assets_involved': self.assets_involved,
            'correlation_value': self.correlation_value,
            'threshold': self.threshold,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class CrossAssetConfig:
    """Configuration for cross-asset analysis"""
    # Correlation parameters
    correlation_lookback: int = 252  # 1 year
    correlation_types: List[CorrelationType] = field(default_factory=lambda: [CorrelationType.PEARSON, CorrelationType.SPEARMAN])
    min_correlation_threshold: float = 0.3
    max_correlation_threshold: float = 0.8
    
    # Sector analysis
    sector_momentum_lookback: int = 63  # 3 months
    sector_rebalance_frequency: int = 21  # Monthly
    
    # Factor analysis
    n_factors: int = 5
    factor_analysis_enabled: bool = True
    
    # Clustering
    clustering_enabled: bool = True
    n_clusters: int = 4
    
    # Alert thresholds
    correlation_spike_threshold: float = 0.2  # 20% increase
    correlation_breakdown_threshold: float = -0.3  # 30% decrease
    
    # Risk management
    max_sector_concentration: float = 0.3  # 30%
    correlation_risk_limit: float = 0.9
    

class CrossAssetCorrelationEngine:
    """Institutional-Grade Cross-Asset Correlation Analysis Engine
    
    Features:
    - Multi-asset class correlation tracking
    - Dynamic correlation regime detection
    - Sector momentum and rotation analysis
    - Factor analysis and PCA decomposition
    - Correlation clustering and network analysis
    - Real-time correlation monitoring
    - Risk-based correlation alerts
    """
    
    def __init__(
        self,
        config: CrossAssetConfig = None,
        data_save_path: str = "./data/cross_asset"
    ):
        self.config = config or CrossAssetConfig()
        self.data_save_path = Path(data_save_path)
        self.data_save_path.mkdir(parents=True, exist_ok=True)
        
        # Asset tracking
        self.assets: Dict[str, AssetInfo] = {}
        self.price_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.correlation_lookback * 2))
        self.returns_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.config.correlation_lookback * 2))
        
        # Correlation tracking
        self.correlation_history: deque = deque(maxlen=100)
        self.current_correlations: Dict[CorrelationType, CorrelationMetrics] = {}
        
        # Sector tracking
        self.sector_data: Dict[SectorCategory, List[str]] = defaultdict(list)
        self.sector_momentum: Dict[SectorCategory, SectorMomentum] = {}
        self.sector_history: deque = deque(maxlen=100)
        
        # Factor analysis
        self.pca_model: Optional[PCA] = None
        self.factor_model: Optional[FactorAnalysis] = None
        self.scaler = StandardScaler()
        
        # Clustering
        self.kmeans_model: Optional[KMeans] = None
        self.correlation_clusters: Dict[str, int] = {}
        
        # Network analysis (if available)
        self.correlation_network: Optional[Any] = None
        
        # Alert system
        self.alerts: deque = deque(maxlen=1000)
        self.alert_thresholds: Dict[str, float] = {
            'correlation_spike': self.config.correlation_spike_threshold,
            'correlation_breakdown': self.config.correlation_breakdown_threshold,
            'high_correlation': self.config.max_correlation_threshold,
            'low_correlation': self.config.min_correlation_threshold
        }
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.lock = threading.Lock()
        
        # Analysis state
        self.last_analysis: Optional[datetime] = None
        self.analysis_count = 0
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self) -> None:
        """Initialize analysis models"""
        if self.config.factor_analysis_enabled:
            self.pca_model = PCA(n_components=self.config.n_factors)
            self.factor_model = FactorAnalysis(n_components=self.config.n_factors)
        
        if self.config.clustering_enabled:
            self.kmeans_model = KMeans(n_clusters=self.config.n_clusters, random_state=42)
        
        if NETWORKX_AVAILABLE:
            self.correlation_network = nx.Graph()
    
    def add_asset(
        self,
        symbol: str,
        name: str,
        asset_class: AssetClass,
        sector: Optional[SectorCategory] = None,
        **kwargs
    ) -> None:
        """Add asset for correlation tracking"""
        
        asset_info = AssetInfo(
            symbol=symbol,
            name=name,
            asset_class=asset_class,
            sector=sector,
            **kwargs
        )
        
        with self.lock:
            self.assets[symbol] = asset_info
            
            # Add to sector tracking
            if sector:
                self.sector_data[sector].append(symbol)
        
        self.logger.info(f"Added asset: {symbol} ({asset_class.value})")
    
    def update_price_data(self, symbol: str, price: float, timestamp: datetime = None) -> None:
        """Update price data for an asset"""
        if symbol not in self.assets:
            self.logger.warning(f"Asset {symbol} not registered. Skipping price update.")
            return
        
        timestamp = timestamp or datetime.now(timezone.utc)
        
        with self.lock:
            # Store price
            self.price_data[symbol].append((timestamp, price))
            
            # Calculate return if we have previous price
            if len(self.price_data[symbol]) >= 2:
                prev_price = self.price_data[symbol][-2][1]
                if prev_price > 0:
                    return_value = (price - prev_price) / prev_price
                    self.returns_data[symbol].append((timestamp, return_value))
        
        # Trigger analysis if enough data
        if self._should_analyze():
            self.executor.submit(self._run_correlation_analysis)
    
    def _should_analyze(self) -> bool:
        """Determine if correlation analysis should be run"""
        # Check if we have enough assets
        if len(self.assets) < 2:
            return False
        
        # Check if we have enough data
        min_data_points = min(50, self.config.correlation_lookback // 5)
        
        for symbol in self.assets.keys():
            if len(self.returns_data[symbol]) < min_data_points:
                return False
        
        # Check timing
        if self.last_analysis:
            time_since_analysis = datetime.now(timezone.utc) - self.last_analysis
            if time_since_analysis.total_seconds() < 300:  # 5 minutes
                return False
        
        return True
    
    def _run_correlation_analysis(self) -> None:
        """Run comprehensive correlation analysis"""
        try:
            self.logger.info("Starting correlation analysis...")
            
            # Prepare data
            returns_matrix = self._prepare_returns_matrix()
            
            if returns_matrix is None or returns_matrix.shape[1] < 2:
                self.logger.warning("Insufficient data for correlation analysis")
                return
            
            # Calculate correlations for each type
            for corr_type in self.config.correlation_types:
                correlation_metrics = self._calculate_correlation_metrics(returns_matrix, corr_type)
                
                if correlation_metrics:
                    with self.lock:
                        self.current_correlations[corr_type] = correlation_metrics
                        self.correlation_history.append(correlation_metrics)
            
            # Run factor analysis
            if self.config.factor_analysis_enabled:
                self._run_factor_analysis(returns_matrix)
            
            # Run clustering analysis
            if self.config.clustering_enabled:
                self._run_clustering_analysis(returns_matrix)
            
            # Update network analysis
            if NETWORKX_AVAILABLE and self.correlation_network is not None:
                self._update_correlation_network()
            
            # Run sector momentum analysis
            self._run_sector_momentum_analysis()
            
            # Check for alerts
            self._check_correlation_alerts()
            
            # Update state
            self.analysis_count += 1
            self.last_analysis = datetime.now(timezone.utc)
            
            self.logger.info(f"Correlation analysis completed. Count: {self.analysis_count}")
            
        except Exception as e:
            self.logger.error(f"Error in correlation analysis: {e}")
    
    def _prepare_returns_matrix(self) -> Optional[np.ndarray]:
        """Prepare returns matrix for analysis"""
        symbols = list(self.assets.keys())
        
        if not symbols:
            return None
        
        # Find common time range
        min_length = min(len(self.returns_data[symbol]) for symbol in symbols)
        
        if min_length < 10:
            return None
        
        # Use the most recent data
        lookback = min(min_length, self.config.correlation_lookback)
        
        returns_matrix = []
        
        for symbol in symbols:
            recent_returns = list(self.returns_data[symbol])[-lookback:]
            returns_values = [r[1] for r in recent_returns]  # Extract return values
            returns_matrix.append(returns_values)
        
        return np.array(returns_matrix).T  # Transpose to have time as rows, assets as columns
    
    def _calculate_correlation_metrics(
        self,
        returns_matrix: np.ndarray,
        correlation_type: CorrelationType
    ) -> Optional[CorrelationMetrics]:
        """Calculate correlation metrics"""
        try:
            # Calculate correlation matrix
            if correlation_type == CorrelationType.PEARSON:
                corr_matrix = np.corrcoef(returns_matrix.T)
            elif correlation_type == CorrelationType.SPEARMAN:
                corr_matrix, _ = stats.spearmanr(returns_matrix)
            elif correlation_type == CorrelationType.KENDALL:
                # Kendall correlation for each pair
                n_assets = returns_matrix.shape[1]
                corr_matrix = np.eye(n_assets)
                for i in range(n_assets):
                    for j in range(i+1, n_assets):
                        tau, _ = stats.kendalltau(returns_matrix[:, i], returns_matrix[:, j])
                        corr_matrix[i, j] = corr_matrix[j, i] = tau
            else:
                # Default to Pearson
                corr_matrix = np.corrcoef(returns_matrix.T)
            
            # Handle NaN values
            corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
            
            # Calculate statistics (excluding diagonal)
            mask = ~np.eye(corr_matrix.shape[0], dtype=bool)
            correlations = corr_matrix[mask]
            
            avg_correlation = np.mean(correlations)
            max_correlation = np.max(correlations)
            min_correlation = np.min(correlations)
            correlation_std = np.std(correlations)
            
            # Determine correlation regime
            regime, regime_confidence = self._determine_correlation_regime(avg_correlation, correlation_std)
            
            return CorrelationMetrics(
                correlation_matrix=corr_matrix,
                correlation_type=correlation_type,
                timestamp=datetime.now(timezone.utc),
                lookback_period=returns_matrix.shape[0],
                avg_correlation=avg_correlation,
                max_correlation=max_correlation,
                min_correlation=min_correlation,
                correlation_std=correlation_std,
                regime=regime,
                regime_confidence=regime_confidence
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation metrics: {e}")
            return None
    
    def _determine_correlation_regime(
        self,
        avg_correlation: float,
        correlation_std: float
    ) -> Tuple[CorrelationRegime, float]:
        """Determine correlation regime"""
        
        # Simple regime classification
        if avg_correlation > 0.7:
            regime = CorrelationRegime.HIGH_CORRELATION
            confidence = min(avg_correlation, 1.0)
        elif avg_correlation > 0.9:
            regime = CorrelationRegime.CRISIS_CORRELATION
            confidence = min(avg_correlation, 1.0)
        elif avg_correlation > 0.3:
            regime = CorrelationRegime.MODERATE_CORRELATION
            confidence = 0.7
        elif avg_correlation < -0.2:
            regime = CorrelationRegime.DECOUPLING
            confidence = abs(avg_correlation)
        else:
            regime = CorrelationRegime.LOW_CORRELATION
            confidence = 1.0 - abs(avg_correlation)
        
        # Adjust confidence based on stability (low std = higher confidence)
        stability_factor = max(0.5, 1.0 - correlation_std)
        confidence *= stability_factor
        
        return regime, confidence
    
    def _run_factor_analysis(self, returns_matrix: np.ndarray) -> None:
        """Run factor analysis on returns"""
        try:
            if returns_matrix.shape[1] < self.config.n_factors:
                return
            
            # Standardize data
            returns_scaled = self.scaler.fit_transform(returns_matrix)
            
            # PCA analysis
            self.pca_model.fit(returns_scaled)
            
            # Factor analysis
            self.factor_model.fit(returns_scaled)
            
            # Update correlation metrics with factor information
            if CorrelationType.PEARSON in self.current_correlations:
                metrics = self.current_correlations[CorrelationType.PEARSON]
                metrics.explained_variance_ratio = self.pca_model.explained_variance_ratio_.tolist()
                metrics.factor_loadings = self.factor_model.components_
            
        except Exception as e:
            self.logger.error(f"Error in factor analysis: {e}")
    
    def _run_clustering_analysis(self, returns_matrix: np.ndarray) -> None:
        """Run clustering analysis on correlations"""
        try:
            # Get correlation matrix
            corr_matrix = np.corrcoef(returns_matrix.T)
            
            # Convert to distance matrix
            distance_matrix = 1 - np.abs(corr_matrix)
            
            # Perform clustering
            self.kmeans_model.fit(distance_matrix)
            
            # Update cluster assignments
            symbols = list(self.assets.keys())
            
            with self.lock:
                for i, symbol in enumerate(symbols):
                    if i < len(self.kmeans_model.labels_):
                        self.correlation_clusters[symbol] = int(self.kmeans_model.labels_[i])
            
        except Exception as e:
            self.logger.error(f"Error in clustering analysis: {e}")
    
    def _update_correlation_network(self) -> None:
        """Update correlation network graph"""
        try:
            if not NETWORKX_AVAILABLE or self.correlation_network is None:
                return
            
            # Clear existing network
            self.correlation_network.clear()
            
            # Get current correlation matrix
            if CorrelationType.PEARSON not in self.current_correlations:
                return
            
            corr_matrix = self.current_correlations[CorrelationType.PEARSON].correlation_matrix
            symbols = list(self.assets.keys())
            
            # Add nodes
            for symbol in symbols:
                self.correlation_network.add_node(symbol, **self.assets[symbol].to_dict())
            
            # Add edges for significant correlations
            threshold = 0.3  # Minimum correlation for edge
            
            for i, symbol1 in enumerate(symbols):
                for j, symbol2 in enumerate(symbols):
                    if i < j and i < corr_matrix.shape[0] and j < corr_matrix.shape[1]:
                        correlation = corr_matrix[i, j]
                        if abs(correlation) > threshold:
                            self.correlation_network.add_edge(
                                symbol1,
                                symbol2,
                                weight=abs(correlation),
                                correlation=correlation
                            )
            
        except Exception as e:
            self.logger.error(f"Error updating correlation network: {e}")
    
    def _run_sector_momentum_analysis(self) -> None:
        """Run sector momentum analysis"""
        try:
            for sector, symbols in self.sector_data.items():
                if not symbols:
                    continue
                
                # Calculate sector returns
                sector_returns = self._calculate_sector_returns(symbols)
                
                if not sector_returns:
                    continue
                
                # Calculate momentum metrics
                momentum = self._calculate_sector_momentum(sector_returns)
                
                if momentum:
                    with self.lock:
                        self.sector_momentum[sector] = momentum
                        self.sector_history.append(momentum)
            
        except Exception as e:
            self.logger.error(f"Error in sector momentum analysis: {e}")
    
    def _calculate_sector_returns(self, symbols: List[str]) -> Optional[List[float]]:
        """Calculate sector-level returns"""
        try:
            # Get returns for all symbols in sector
            all_returns = []
            
            for symbol in symbols:
                if symbol in self.returns_data and len(self.returns_data[symbol]) > 0:
                    recent_returns = list(self.returns_data[symbol])[-self.config.sector_momentum_lookback:]
                    returns_values = [r[1] for r in recent_returns]
                    all_returns.append(returns_values)
            
            if not all_returns:
                return None
            
            # Calculate equal-weighted sector returns
            min_length = min(len(returns) for returns in all_returns)
            
            if min_length < 10:
                return None
            
            sector_returns = []
            for i in range(min_length):
                period_returns = [returns[i] for returns in all_returns]
                sector_return = np.mean(period_returns)
                sector_returns.append(sector_return)
            
            return sector_returns
            
        except Exception as e:
            self.logger.error(f"Error calculating sector returns: {e}")
            return None
    
    def _calculate_sector_momentum(self, sector_returns: List[float]) -> Optional[SectorMomentum]:
        """Calculate sector momentum metrics"""
        try:
            if len(sector_returns) < 20:
                return None
            
            returns_array = np.array(sector_returns)
            
            # Calculate performance metrics
            returns_1d = returns_array[-1] if len(returns_array) >= 1 else 0.0
            returns_1w = np.prod(1 + returns_array[-5:]) - 1 if len(returns_array) >= 5 else 0.0
            returns_1m = np.prod(1 + returns_array[-21:]) - 1 if len(returns_array) >= 21 else 0.0
            returns_3m = np.prod(1 + returns_array[-63:]) - 1 if len(returns_array) >= 63 else 0.0
            
            # Calculate momentum score (combination of recent performance and trend)
            momentum_score = (
                returns_1w * 0.1 +
                returns_1m * 0.4 +
                returns_3m * 0.5
            )
            
            # Calculate relative strength (vs average)
            avg_return = np.mean(returns_array)
            relative_strength = returns_1m - avg_return if avg_return != 0 else 0.0
            
            # Determine trend direction
            if momentum_score > 0.02:  # 2%
                trend_direction = "bullish"
            elif momentum_score < -0.02:  # -2%
                trend_direction = "bearish"
            else:
                trend_direction = "neutral"
            
            # Calculate volatility
            volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
            
            # Simple RSI calculation
            rsi = self._calculate_simple_rsi(returns_array)
            
            return SectorMomentum(
                sector=list(self.sector_data.keys())[0],  # This needs to be passed properly
                momentum_score=momentum_score,
                relative_strength=relative_strength,
                trend_direction=trend_direction,
                volatility=volatility,
                returns_1d=returns_1d,
                returns_1w=returns_1w,
                returns_1m=returns_1m,
                returns_3m=returns_3m,
                rsi=rsi
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating sector momentum: {e}")
            return None
    
    def _calculate_simple_rsi(self, returns: np.ndarray, period: int = 14) -> Optional[float]:
        """Calculate simple RSI"""
        try:
            if len(returns) < period + 1:
                return None
            
            gains = np.where(returns > 0, returns, 0)
            losses = np.where(returns < 0, -returns, 0)
            
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return None
    
    def _check_correlation_alerts(self) -> None:
        """Check for correlation-based alerts"""
        try:
            if CorrelationType.PEARSON not in self.current_correlations:
                return
            
            current_metrics = self.current_correlations[CorrelationType.PEARSON]
            
            # Check for correlation spikes
            if len(self.correlation_history) >= 2:
                prev_metrics = self.correlation_history[-2]
                
                correlation_change = current_metrics.avg_correlation - prev_metrics.avg_correlation
                
                if correlation_change > self.alert_thresholds['correlation_spike']:
                    alert = CorrelationAlert(
                        alert_type="correlation_spike",
                        severity="high",
                        message=f"Correlation spike detected: {correlation_change:.3f} increase",
                        assets_involved=list(self.assets.keys()),
                        correlation_value=current_metrics.avg_correlation,
                        threshold=self.alert_thresholds['correlation_spike']
                    )
                    
                    with self.lock:
                        self.alerts.append(alert)
                
                elif correlation_change < -self.alert_thresholds['correlation_breakdown']:
                    alert = CorrelationAlert(
                        alert_type="correlation_breakdown",
                        severity="medium",
                        message=f"Correlation breakdown detected: {correlation_change:.3f} decrease",
                        assets_involved=list(self.assets.keys()),
                        correlation_value=current_metrics.avg_correlation,
                        threshold=self.alert_thresholds['correlation_breakdown']
                    )
                    
                    with self.lock:
                        self.alerts.append(alert)
            
            # Check for extreme correlations
            if current_metrics.max_correlation > self.alert_thresholds['high_correlation']:
                alert = CorrelationAlert(
                    alert_type="high_correlation",
                    severity="medium",
                    message=f"High correlation detected: {current_metrics.max_correlation:.3f}",
                    assets_involved=list(self.assets.keys()),
                    correlation_value=current_metrics.max_correlation,
                    threshold=self.alert_thresholds['high_correlation']
                )
                
                with self.lock:
                    self.alerts.append(alert)
            
        except Exception as e:
            self.logger.error(f"Error checking correlation alerts: {e}")
    
    def get_correlation_matrix(self, correlation_type: CorrelationType = CorrelationType.PEARSON) -> Optional[np.ndarray]:
        """Get current correlation matrix"""
        with self.lock:
            if correlation_type in self.current_correlations:
                return self.current_correlations[correlation_type].correlation_matrix.copy()
        return None
    
    def get_sector_momentum_ranking(self) -> List[Tuple[SectorCategory, float]]:
        """Get sectors ranked by momentum"""
        with self.lock:
            rankings = []
            for sector, momentum in self.sector_momentum.items():
                rankings.append((sector, momentum.momentum_score))
        
        return sorted(rankings, key=lambda x: x[1], reverse=True)
    
    def get_correlation_clusters(self) -> Dict[int, List[str]]:
        """Get correlation-based asset clusters"""
        clusters = defaultdict(list)
        
        with self.lock:
            for symbol, cluster_id in self.correlation_clusters.items():
                clusters[cluster_id].append(symbol)
        
        return dict(clusters)
    
    def get_network_centrality(self) -> Dict[str, float]:
        """Get network centrality measures"""
        if not NETWORKX_AVAILABLE or self.correlation_network is None:
            return {}
        
        try:
            centrality = nx.degree_centrality(self.correlation_network)
            return centrality
        except Exception as e:
            self.logger.error(f"Error calculating network centrality: {e}")
            return {}
    
    def get_recent_alerts(self, limit: int = 10) -> List[CorrelationAlert]:
        """Get recent correlation alerts"""
        with self.lock:
            return list(self.alerts)[-limit:]
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        summary = {
            'total_assets': len(self.assets),
            'analysis_count': self.analysis_count,
            'last_analysis': self.last_analysis.isoformat() if self.last_analysis else None,
            'correlation_regimes': {},
            'sector_count': len(self.sector_data),
            'alert_count': len(self.alerts),
            'cluster_count': len(set(self.correlation_clusters.values())) if self.correlation_clusters else 0
        }
        
        # Add correlation regime information
        with self.lock:
            for corr_type, metrics in self.current_correlations.items():
                summary['correlation_regimes'][corr_type.value] = {
                    'regime': metrics.regime.value,
                    'confidence': metrics.regime_confidence,
                    'avg_correlation': metrics.avg_correlation
                }
        
        # Add sector momentum summary
        sector_summary = {}
        for sector, momentum in self.sector_momentum.items():
            sector_summary[sector.value] = {
                'momentum_score': momentum.momentum_score,
                'trend_direction': momentum.trend_direction,
                'returns_1m': momentum.returns_1m
            }
        
        summary['sector_momentum'] = sector_summary
        
        return summary
    
    def export_correlation_data(self, filepath: str) -> bool:
        """Export correlation data to file"""
        try:
            export_data = {
                'assets': {symbol: asset.to_dict() for symbol, asset in self.assets.items()},
                'correlations': {corr_type.value: metrics.to_dict() for corr_type, metrics in self.current_correlations.items()},
                'sector_momentum': {sector.value: momentum.to_dict() for sector, momentum in self.sector_momentum.items()},
                'clusters': self.get_correlation_clusters(),
                'alerts': [alert.to_dict() for alert in list(self.alerts)[-50:]],  # Last 50 alerts
                'summary': self.get_analysis_summary()
            }
            
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting correlation data: {e}")
            return False
    
    def shutdown(self) -> None:
        """Shutdown the correlation engine"""
        self.executor.shutdown(wait=True)
        self.logger.info("Cross-asset correlation engine shutdown complete")


# Factory function
def create_cross_asset_engine(
    correlation_lookback: int = 252,
    n_factors: int = 5,
    n_clusters: int = 4,
    data_save_path: str = "./data/cross_asset"
) -> CrossAssetCorrelationEngine:
    """Create cross-asset correlation engine with specified configuration"""
    
    config = CrossAssetConfig(
        correlation_lookback=correlation_lookback,
        n_factors=n_factors,
        n_clusters=n_clusters
    )
    
    return CrossAssetCorrelationEngine(config=config, data_save_path=data_save_path)


# Example usage
if __name__ == "__main__":
    # Create correlation engine
    engine = create_cross_asset_engine()
    
    # Add sample assets
    engine.add_asset("SPY", "SPDR S&P 500 ETF", AssetClass.EQUITY, SectorCategory.TECHNOLOGY)
    engine.add_asset("QQQ", "Invesco QQQ Trust", AssetClass.EQUITY, SectorCategory.TECHNOLOGY)
    engine.add_asset("TLT", "iShares 20+ Year Treasury Bond ETF", AssetClass.FIXED_INCOME)
    engine.add_asset("GLD", "SPDR Gold Shares", AssetClass.COMMODITY)
    engine.add_asset("UUP", "Invesco DB US Dollar Index Bullish Fund", AssetClass.CURRENCY)
    
    # Simulate price updates
    import random
    base_prices = {"SPY": 400, "QQQ": 350, "TLT": 120, "GLD": 180, "UUP": 25}
    
    for i in range(100):
        timestamp = datetime.now(timezone.utc) - timedelta(days=100-i)
        
        for symbol, base_price in base_prices.items():
            # Simulate price movement
            price_change = random.gauss(0, 0.02)  # 2% daily volatility
            new_price = base_price * (1 + price_change)
            base_prices[symbol] = new_price
            
            engine.update_price_data(symbol, new_price, timestamp)
    
    # Wait for analysis to complete
    import time
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators

    time.sleep(2)
    
    # Get analysis results
    summary = engine.get_analysis_summary()
    print("Analysis Summary:")
    print(json.dumps(summary, indent=2, default=str))
    
    # Get correlation matrix
    corr_matrix = engine.get_correlation_matrix()
    if corr_matrix is not None:
        print("\nCorrelation Matrix:")
        print(corr_matrix)
    
    # Get sector rankings
    rankings = engine.get_sector_momentum_ranking()
    print("\nSector Momentum Rankings:")
    for sector, score in rankings:
        print(f"{sector.value}: {score:.4f}")
    
    # Export data
    engine.export_correlation_data("correlation_analysis.json")
    
    # Shutdown
    engine.shutdown()