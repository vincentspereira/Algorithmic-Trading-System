"""Volume Confirmation and Analysis Module

This module provides comprehensive volume confirmation scoring and analysis
for all technical indicators in the trading system. It implements institutional-grade
volume analysis techniques including:

- Multi-timeframe volume confirmation scoring
- Institutional volume pattern detection
- Volume-price relationship analysis
- Smart money flow detection
- Volume quality assessment
- Volume trend analysis
- Order flow imbalance detection

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, NamedTuple
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from enum import Enum
import logging
from scipy import stats


logger = logging.getLogger(__name__)

# ===========================================
# ENUMS AND DATA CLASSES
# ===========================================

class VolumeRegime(Enum):
    """Volume regime classification"""
    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    INSTITUTIONAL = "institutional"

class VolumeQuality(Enum):
    """Volume quality assessment"""
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"

class OrderFlowBias(Enum):
    """Order flow bias direction"""
    STRONG_BUYING = "strong_buying"
    MODERATE_BUYING = "moderate_buying"
    NEUTRAL = "neutral"
    MODERATE_SELLING = "moderate_selling"
    STRONG_SELLING = "strong_selling"

@dataclass
class VolumeConfirmationScore:
    """Comprehensive volume confirmation scoring"""
    overall_score: float  # 0-1 scale
    price_volume_sync: float
    volume_breakout: float
    volume_persistence: float
    institutional_presence: float
    volume_trend_alignment: float
    volume_quality: float
    confidence: float
    timestamp: datetime

@dataclass
class VolumeAnalysis:
    """Detailed volume analysis results"""
    volume_regime: VolumeRegime
    volume_quality: VolumeQuality
    order_flow_bias: OrderFlowBias
    institutional_activity: float  # 0-1 scale
    volume_momentum: float
    volume_acceleration: float
    relative_volume: float
    volume_z_score: float
    volume_percentile: float
    smart_money_flow: float
    retail_flow: float
    timestamp: datetime

@dataclass
class VolumeProfile:
    """Volume profile analysis"""
    poc_price: float  # Point of Control
    value_area_high: float
    value_area_low: float
    volume_weighted_price: float
    high_volume_nodes: List[float]
    low_volume_nodes: List[float]
    total_volume: float
    buying_volume: float
    selling_volume: float
    neutral_volume: float

# ===========================================
# VOLUME CONFIRMATION ENGINE
# ===========================================

class VolumeConfirmationEngine:
    """Advanced volume confirmation and analysis engine"""
    
    def __init__(self, lookback_period: int = 50, institutional_threshold: float = 2.0):
        self.lookback_period = lookback_period
        self.institutional_threshold = institutional_threshold
        
        # Data storage
        self.prices: deque = deque(maxlen=lookback_period * 2)
        self.volumes: deque = deque(maxlen=lookback_period * 2)
        self.timestamps: deque = deque(maxlen=lookback_period * 2)
        
        # Analysis results
        self.volume_history: deque = deque(maxlen=1000)
        self.confirmation_history: deque = deque(maxlen=1000)
        
        # Cached calculations
        self._volume_stats_cache = {}
        self._cache_timestamp = None
        
    def update(self, price: float, volume: float, timestamp: datetime = None) -> VolumeConfirmationScore:
        """Update volume confirmation analysis"""
        timestamp = timestamp or datetime.now()
        
        # Store data
        self.prices.append(price)
        self.volumes.append(volume)
        self.timestamps.append(timestamp)
        
        # Calculate confirmation score
        confirmation_score = self._calculate_comprehensive_confirmation(price, volume, timestamp)
        
        # Store results
        self.confirmation_history.append(confirmation_score)
        
        return confirmation_score
    
    def _calculate_comprehensive_confirmation(self, price: float, volume: float, timestamp: datetime) -> VolumeConfirmationScore:
        """Calculate comprehensive volume confirmation score"""
        if len(self.volumes) < 10:
            return VolumeConfirmationScore(
                overall_score=0.5,
                price_volume_sync=0.5,
                volume_breakout=0.5,
                volume_persistence=0.5,
                institutional_presence=0.5,
                volume_trend_alignment=0.5,
                volume_quality=0.5,
                confidence=0.3,
                timestamp=timestamp
            )
        
        # Get volume statistics
        volume_stats = self._get_volume_statistics()
        
        # Calculate individual components
        price_volume_sync = self._calculate_price_volume_sync(price, volume, volume_stats)
        volume_breakout = self._calculate_volume_breakout(volume, volume_stats)
        volume_persistence = self._calculate_volume_persistence(volume_stats)
        institutional_presence = self._detect_institutional_presence(volume, volume_stats)
        volume_trend_alignment = self._calculate_volume_trend_alignment(volume_stats)
        volume_quality = self._assess_volume_quality(volume, volume_stats)
        
        # Weighted overall score
        weights = {
            'price_volume_sync': 0.25,
            'volume_breakout': 0.20,
            'volume_persistence': 0.15,
            'institutional_presence': 0.20,
            'volume_trend_alignment': 0.10,
            'volume_quality': 0.10
        }
        
        overall_score = (
            price_volume_sync * weights['price_volume_sync'] +
            volume_breakout * weights['volume_breakout'] +
            volume_persistence * weights['volume_persistence'] +
            institutional_presence * weights['institutional_presence'] +
            volume_trend_alignment * weights['volume_trend_alignment'] +
            volume_quality * weights['volume_quality']
        )
        
        # Calculate confidence based on data quality and consistency
        confidence = self._calculate_confidence(volume_stats)
        
        return VolumeConfirmationScore(
            overall_score=overall_score,
            price_volume_sync=price_volume_sync,
            volume_breakout=volume_breakout,
            volume_persistence=volume_persistence,
            institutional_presence=institutional_presence,
            volume_trend_alignment=volume_trend_alignment,
            volume_quality=volume_quality,
            confidence=confidence,
            timestamp=timestamp
        )
    
    def _get_volume_statistics(self) -> Dict:
        """Get comprehensive volume statistics with caching"""
        current_time = datetime.now()
        
        # Use cache if recent (within 1 second)
        if (self._cache_timestamp and 
            (current_time - self._cache_timestamp).total_seconds() < 1.0):
            return self._volume_stats_cache
        
        volumes_array = np.array(list(self.volumes))
        
        stats = {
            'current_volume': volumes_array[-1] if len(volumes_array) > 0 else 0.0,
            'volume_ma_5': np.mean(volumes_array[-5:]) if len(volumes_array) >= 5 else np.mean(volumes_array),
            'volume_ma_10': np.mean(volumes_array[-10:]) if len(volumes_array) >= 10 else np.mean(volumes_array),
            'volume_ma_20': np.mean(volumes_array[-20:]) if len(volumes_array) >= 20 else np.mean(volumes_array),
            'volume_std': np.std(volumes_array),
            'volume_median': np.median(volumes_array),
            'volume_95th': np.percentile(volumes_array, 95),
            'volume_99th': np.percentile(volumes_array, 99),
            'volume_min': np.min(volumes_array),
            'volume_max': np.max(volumes_array),
            'volume_range': np.max(volumes_array) - np.min(volumes_array),
            'volume_cv': np.std(volumes_array) / np.mean(volumes_array) if np.mean(volumes_array) > 0 else 0.0
        }
        
        # Cache results
        self._volume_stats_cache = stats
        self._cache_timestamp = current_time
        
        return stats
    
    def _calculate_price_volume_sync(self, price: float, volume: float, volume_stats: Dict) -> float:
        """Calculate price-volume synchronization score"""
        if len(self.prices) < 2:
            return 0.5
        
        # Price change analysis
        price_change = (price - self.prices[-2]) / self.prices[-2] if self.prices[-2] != 0 else 0.0
        price_strength = abs(price_change) * 100  # Convert to percentage
        
        # Volume strength relative to average
        volume_strength = max(0.0, (volume / volume_stats['volume_ma_10']) - 1.0)
        
        # Synchronization scoring
        if price_strength > 0.5 and volume_strength > 0.5:
            # Strong price move with strong volume = excellent sync
            sync_score = min(1.0, (price_strength * volume_strength) / 2.0)
        elif price_strength > 1.0 and volume_strength < 0.2:
            # Strong price move with weak volume = poor sync
            sync_score = 0.2
        elif price_strength < 0.2 and volume_strength > 1.0:
            # Weak price move with strong volume = accumulation/distribution
            sync_score = 0.7
        else:
            # Moderate synchronization
            sync_score = 0.5 + (min(price_strength, volume_strength) * 0.3)
        
        return min(1.0, max(0.0, sync_score))
    
    def _calculate_volume_breakout(self, volume: float, volume_stats: Dict) -> float:
        """Calculate volume breakout score"""
        # Multiple breakout thresholds
        breakout_1_5x = volume / volume_stats['volume_ma_10'] if volume_stats['volume_ma_10'] > 0 else 1.0
        breakout_2x = volume / volume_stats['volume_ma_20'] if volume_stats['volume_ma_20'] > 0 else 1.0
        
        # Statistical breakout (z-score based)
        z_score = (volume - volume_stats['volume_ma_20']) / volume_stats['volume_std'] if volume_stats['volume_std'] > 0 else 0.0
        
        # Percentile breakout
        percentile_score = 1.0 if volume > volume_stats['volume_95th'] else 0.5 if volume > volume_stats['volume_median'] else 0.0
        
        # Combined breakout score
        breakout_components = [
            min(1.0, max(0.0, (breakout_1_5x - 1.0) / 1.5)),  # 1.5x threshold
            min(1.0, max(0.0, (breakout_2x - 1.0) / 2.0)),     # 2x threshold
            min(1.0, max(0.0, (z_score - 1.0) / 2.0)),         # Z-score threshold
            percentile_score                                     # Percentile threshold
        ]
        
        return np.mean(breakout_components)
    
    def _calculate_volume_persistence(self, volume_stats: Dict) -> float:
        """Calculate volume persistence score"""
        if len(self.volumes) < 10:
            return 0.5
        
        recent_volumes = list(self.volumes)[-10:]
        volume_mean = volume_stats['volume_ma_20']
        
        # Count periods with above-average volume
        above_average_count = sum(1 for v in recent_volumes if v > volume_mean)
        
        # Persistence score
        persistence_score = above_average_count / len(recent_volumes)
        
        # Bonus for consecutive high-volume periods
        consecutive_bonus = 0.0
        consecutive_count = 0
        for v in reversed(recent_volumes):
            if v > volume_mean * 1.2:  # 20% above average
                consecutive_count += 1
            else:
                break
        
        if consecutive_count >= 3:
            consecutive_bonus = min(0.3, consecutive_count * 0.1)
        
        return min(1.0, persistence_score + consecutive_bonus)
    
    def _detect_institutional_presence(self, volume: float, volume_stats: Dict) -> float:
        """Detect institutional presence in volume"""
        # Multiple institutional detection methods
        detection_scores = []
        
        # Method 1: Statistical threshold (2+ standard deviations)
        if volume_stats['volume_std'] > 0:
            z_score = (volume - volume_stats['volume_ma_20']) / volume_stats['volume_std']
            z_score_component = min(1.0, max(0.0, (z_score - 1.5) / 2.0))
            detection_scores.append(z_score_component)
        
        # Method 2: Percentile-based detection
        if volume > volume_stats['volume_99th']:
            percentile_component = 1.0
        elif volume > volume_stats['volume_95th']:
            percentile_component = 0.7
        elif volume > volume_stats['volume_median']:
            percentile_component = 0.3
        else:
            percentile_component = 0.0
        detection_scores.append(percentile_component)
        
        # Method 3: Volume spike detection
        if len(self.volumes) >= 5:
            recent_volumes = list(self.volumes)[-5:]
            max_recent = max(recent_volumes[:-1]) if len(recent_volumes) > 1 else volume_stats['volume_ma_10']
            spike_ratio = volume / max_recent if max_recent > 0 else 1.0
            spike_component = min(1.0, max(0.0, (spike_ratio - 1.5) / 2.0))
            detection_scores.append(spike_component)
        
        # Method 4: Volume clustering (institutional orders often come in clusters)
        if len(self.volumes) >= 10:
            recent_volumes = list(self.volumes)[-10:]
            high_volume_threshold = volume_stats['volume_ma_20'] * 1.5
            high_volume_count = sum(1 for v in recent_volumes if v > high_volume_threshold)
            cluster_component = min(1.0, high_volume_count / 5.0)
            detection_scores.append(cluster_component)
        
        return np.mean(detection_scores) if detection_scores else 0.0
    
    def _calculate_volume_trend_alignment(self, volume_stats: Dict) -> float:
        """Calculate volume trend alignment score"""
        if len(self.volumes) < 10:
            return 0.5
        
        recent_volumes = list(self.volumes)[-10:]
        
        # Calculate volume trend using linear regression
        x = np.arange(len(recent_volumes))
        slope, _ = np.polyfit(x, recent_volumes, 1)
        
        # Normalize slope
        volume_mean = np.mean(recent_volumes)
        normalized_slope = slope / volume_mean if volume_mean > 0 else 0.0
        
        # Convert to 0-1 score (positive trend = higher score)
        trend_score = 0.5 + (normalized_slope * 5.0)  # Scale factor
        return min(1.0, max(0.0, trend_score))
    
    def _assess_volume_quality(self, volume: float, volume_stats: Dict) -> float:
        """Assess volume quality"""
        # Quality factors
        quality_components = []
        
        # 1. Volume consistency (lower coefficient of variation = higher quality)
        if volume_stats['volume_cv'] > 0:
            consistency_score = 1.0 - min(1.0, volume_stats['volume_cv'])
            quality_components.append(consistency_score)
        
        # 2. Volume adequacy (current volume relative to average)
        adequacy_score = min(1.0, volume / volume_stats['volume_ma_10']) if volume_stats['volume_ma_10'] > 0 else 0.5
        quality_components.append(adequacy_score)
        
        # 3. Volume stability (not too extreme)
        if volume_stats['volume_range'] > 0:
            stability_score = 1.0 - min(1.0, abs(volume - volume_stats['volume_median']) / volume_stats['volume_range'])
            quality_components.append(stability_score)
        
        # 4. Volume distribution quality
        if len(self.volumes) >= 20:
            recent_volumes = np.array(list(self.volumes)[-20:])
            # Check for normal distribution (lower skewness = higher quality)


            try:
                skewness = abs(stats.skew(recent_volumes))
                distribution_score = max(0.0, 1.0 - (skewness / 3.0))  # Normalize skewness
                quality_components.append(distribution_score)
            except:
                pass  # Skip if scipy not available
        
        return np.mean(quality_components) if quality_components else 0.5
    
    def _calculate_confidence(self, volume_stats: Dict) -> float:
        """Calculate confidence in volume analysis"""
        confidence_factors = []
        
        # Data sufficiency
        data_sufficiency = min(1.0, len(self.volumes) / self.lookback_period)
        confidence_factors.append(data_sufficiency)
        
        # Volume consistency
        if volume_stats['volume_cv'] > 0:
            consistency_factor = max(0.3, 1.0 - volume_stats['volume_cv'])
            confidence_factors.append(consistency_factor)
        
        # Recent data quality
        if len(self.volumes) >= 5:
            recent_volumes = list(self.volumes)[-5:]
            recent_consistency = 1.0 - (np.std(recent_volumes) / np.mean(recent_volumes)) if np.mean(recent_volumes) > 0 else 0.5
            confidence_factors.append(max(0.2, recent_consistency))
        
        return np.mean(confidence_factors) if confidence_factors else 0.5
    
    def get_volume_analysis(self) -> Optional[VolumeAnalysis]:
        """Get comprehensive volume analysis"""
        if len(self.volumes) < 10:
            return None
        
        volume_stats = self._get_volume_statistics()
        current_volume = volume_stats['current_volume']
        
        # Determine volume regime
        volume_regime = self._classify_volume_regime(current_volume, volume_stats)
        
        # Assess volume quality
        volume_quality = self._classify_volume_quality(current_volume, volume_stats)
        
        # Determine order flow bias
        order_flow_bias = self._assess_order_flow_bias()
        
        # Calculate additional metrics
        institutional_activity = self._detect_institutional_presence(current_volume, volume_stats)
        volume_momentum = self._calculate_volume_momentum()
        volume_acceleration = self._calculate_volume_acceleration()
        relative_volume = current_volume / volume_stats['volume_ma_20'] if volume_stats['volume_ma_20'] > 0 else 1.0
        volume_z_score = (current_volume - volume_stats['volume_ma_20']) / volume_stats['volume_std'] if volume_stats['volume_std'] > 0 else 0.0
        
        # Calculate percentile
        volumes_array = np.array(list(self.volumes))
        volume_percentile = (np.sum(volumes_array <= current_volume) / len(volumes_array)) * 100
        
        # Smart money vs retail flow (simplified)
        smart_money_flow = institutional_activity
        retail_flow = 1.0 - institutional_activity
        
        return VolumeAnalysis(
            volume_regime=volume_regime,
            volume_quality=volume_quality,
            order_flow_bias=order_flow_bias,
            institutional_activity=institutional_activity,
            volume_momentum=volume_momentum,
            volume_acceleration=volume_acceleration,
            relative_volume=relative_volume,
            volume_z_score=volume_z_score,
            volume_percentile=volume_percentile,
            smart_money_flow=smart_money_flow,
            retail_flow=retail_flow,
            timestamp=datetime.now()
        )
    
    def _classify_volume_regime(self, volume: float, volume_stats: Dict) -> VolumeRegime:
        """Classify current volume regime"""
        relative_volume = volume / volume_stats['volume_ma_20'] if volume_stats['volume_ma_20'] > 0 else 1.0
        
        if volume > volume_stats['volume_99th']:
            return VolumeRegime.INSTITUTIONAL
        elif relative_volume > 2.0:
            return VolumeRegime.VERY_HIGH
        elif relative_volume > 1.5:
            return VolumeRegime.HIGH
        elif relative_volume > 0.8:
            return VolumeRegime.NORMAL
        elif relative_volume > 0.5:
            return VolumeRegime.LOW
        else:
            return VolumeRegime.VERY_LOW
    
    def _classify_volume_quality(self, volume: float, volume_stats: Dict) -> VolumeQuality:
        """Classify volume quality"""
        quality_score = self._assess_volume_quality(volume, volume_stats)
        
        if quality_score > 0.8:
            return VolumeQuality.EXCELLENT
        elif quality_score > 0.6:
            return VolumeQuality.GOOD
        elif quality_score > 0.4:
            return VolumeQuality.FAIR
        else:
            return VolumeQuality.POOR
    
    def _assess_order_flow_bias(self) -> OrderFlowBias:
        """Assess order flow bias based on price-volume relationship"""
        if len(self.prices) < 5 or len(self.volumes) < 5:
            return OrderFlowBias.NEUTRAL
        
        # Analyze recent price-volume relationship
        recent_prices = list(self.prices)[-5:]
        recent_volumes = list(self.volumes)[-5:]
        
        # Calculate price momentum and volume momentum
        price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0.0
        volume_momentum = (recent_volumes[-1] - recent_volumes[0]) / recent_volumes[0] if recent_volumes[0] != 0 else 0.0
        
        # Determine bias based on momentum alignment
        if price_momentum > 0.01 and volume_momentum > 0.2:
            return OrderFlowBias.STRONG_BUYING
        elif price_momentum > 0.005 and volume_momentum > 0.1:
            return OrderFlowBias.MODERATE_BUYING
        elif price_momentum < -0.01 and volume_momentum > 0.2:
            return OrderFlowBias.STRONG_SELLING
        elif price_momentum < -0.005 and volume_momentum > 0.1:
            return OrderFlowBias.MODERATE_SELLING
        else:
            return OrderFlowBias.NEUTRAL
    
    def _calculate_volume_momentum(self) -> float:
        """Calculate volume momentum"""
        if len(self.volumes) < 10:
            return 0.0
        
        recent_volumes = list(self.volumes)[-10:]
        early_avg = np.mean(recent_volumes[:5])
        late_avg = np.mean(recent_volumes[5:])
        
        momentum = (late_avg - early_avg) / early_avg if early_avg > 0 else 0.0
        return momentum
    
    def _calculate_volume_acceleration(self) -> float:
        """Calculate volume acceleration (second derivative)"""
        if len(self.volumes) < 15:
            return 0.0
        
        recent_volumes = list(self.volumes)[-15:]
        
        # Calculate momentum for two periods
        period1_volumes = recent_volumes[:5]
        period2_volumes = recent_volumes[5:10]
        period3_volumes = recent_volumes[10:]
        
        momentum1 = (np.mean(period2_volumes) - np.mean(period1_volumes)) / np.mean(period1_volumes) if np.mean(period1_volumes) > 0 else 0.0
        momentum2 = (np.mean(period3_volumes) - np.mean(period2_volumes)) / np.mean(period2_volumes) if np.mean(period2_volumes) > 0 else 0.0
        
        acceleration = momentum2 - momentum1
        return acceleration

# ===========================================
# VOLUME-WEIGHTED INDICATOR MIXINS
# ===========================================

class VolumeConfirmationMixin:
    """Mixin to add volume confirmation to any indicator"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.volume_engine = VolumeConfirmationEngine()
        self.volume_confirmation_enabled = True
    
    def update_with_volume_confirmation(self, price: float, volume: float, timestamp: datetime = None) -> Dict:
        """Update indicator with volume confirmation analysis"""
        if not self.volume_confirmation_enabled:
            return {}
        
        # Get volume confirmation score
        confirmation_score = self.volume_engine.update(price, volume, timestamp)
        
        # Get detailed volume analysis
        volume_analysis = self.volume_engine.get_volume_analysis()
        
        return {
            'volume_confirmation': confirmation_score,
            'volume_analysis': volume_analysis
        }
    
    def get_volume_adjusted_signal(self, base_signal: float, volume_confirmation: VolumeConfirmationScore) -> float:
        """Adjust signal strength based on volume confirmation"""
        if not self.volume_confirmation_enabled:
            return base_signal
        
        # Volume confirmation multiplier (0.5 to 1.5 range)
        volume_multiplier = 0.5 + (volume_confirmation.overall_score * 1.0)
        
        # Apply confidence weighting
        confidence_weight = volume_confirmation.confidence
        
        # Calculate adjusted signal
        adjusted_signal = base_signal * (volume_multiplier * confidence_weight + (1 - confidence_weight))
        
        return adjusted_signal

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def create_volume_confirmation_engine(lookback_period: int = 50, institutional_threshold: float = 2.0) -> VolumeConfirmationEngine:
    """Factory function to create volume confirmation engine"""
    return VolumeConfirmationEngine(lookback_period, institutional_threshold)

def calculate_volume_weighted_price(prices: List[float], volumes: List[float]) -> float:
    """Calculate volume-weighted average price"""
    if len(prices) != len(volumes) or len(prices) == 0:
        return 0.0
    
    total_volume = sum(volumes)
    if total_volume == 0:
        return np.mean(prices)
    
    weighted_sum = sum(p * v for p, v in zip(prices, volumes))
    return weighted_sum / total_volume

def calculate_relative_volume(current_volume: float, historical_volumes: List[float]) -> float:
    """Calculate relative volume ratio"""
    if not historical_volumes:
        return 1.0
    
    avg_volume = np.mean(historical_volumes)
    return current_volume / avg_volume if avg_volume > 0 else 1.0

def detect_volume_anomalies(volumes: List[float], threshold: float = 3.0) -> List[int]:
    """Detect volume anomalies using z-score"""
    if len(volumes) < 10:
        return []
    
    volumes_array = np.array(volumes)
    mean_volume = np.mean(volumes_array)
    std_volume = np.std(volumes_array)
    
    if std_volume == 0:
        return []
    
    z_scores = np.abs((volumes_array - mean_volume) / std_volume)
    anomaly_indices = np.where(z_scores > threshold)[0].tolist()
    
    return anomaly_indices

# Export all classes and functions
__all__ = [
    # Enums
    'VolumeRegime', 'VolumeQuality', 'OrderFlowBias',
    
    # Data classes
    'VolumeConfirmationScore', 'VolumeAnalysis', 'VolumeProfile',
    
    # Main classes
    'VolumeConfirmationEngine', 'VolumeConfirmationMixin',
    
    # Utility functions
    'create_volume_confirmation_engine', 'calculate_volume_weighted_price',
    'calculate_relative_volume', 'detect_volume_anomalies'
]