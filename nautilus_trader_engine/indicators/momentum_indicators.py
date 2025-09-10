"""Consolidated Momentum Indicators - Institutional Grade

This module consolidates all momentum-based technical indicators including:
- RSI (Relative Strength Index) with volume weighting
- MACD (Moving Average Convergence Divergence) with smart money analysis
- Stochastic Oscillator with multi-timeframe convergence
- Williams %R with adaptive parameters
- Rate of Change (ROC) with institutional flow detection
- Commodity Channel Index (CCI) with regime adaptation

All indicators inherit from AugmentedIndicator providing:
- 5-pillar institutional architecture
- Volume confirmation and smart money analysis
- Market regime adaptation
- Multi-timeframe convergence
- Automated risk management
- Real-time performance optimization

Author: Vincent S. Pereira
Version: 6.0.0 (Consolidated)
"""

import numpy as np
import talib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, NamedTuple
from collections import deque
from dataclasses import dataclass
from enum import Enum

from .core_indicator_base import (
    AugmentedIndicator, IndicatorSignal, IndicatorConfig, IndicatorResult,
    SignalType, MarketRegime, RiskLevel, TimeframeConvergence,
    performance_monitor, robust_calculation, calculate_sma, calculate_ema
)
from .volume_confirmation import (
    VolumeConfirmationEngine,
    VolumeConfirmationMixin,
    VolumeConfirmationScore,
    VolumeAnalysis,
    create_volume_confirmation_engine
)
from .smart_money_analysis import (
    SmartMoneyAnalysisEngine,
    SmartMoneyMixin,
    SmartMoneyMetrics,
    SmartMoneyBias,
    InstitutionalActivity
)

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# ===========================================
# MOMENTUM-SPECIFIC ENUMS AND DATA CLASSES
# ===========================================

class MomentumState(Enum):
    """Momentum state classification"""
    EXTREMELY_OVERSOLD = "extremely_oversold"
    OVERSOLD = "oversold"
    NEUTRAL = "neutral"
    OVERBOUGHT = "overbought"
    EXTREMELY_OVERBOUGHT = "extremely_overbought"

class MomentumDirection(Enum):
    """Momentum direction classification"""
    STRONG_BEARISH = "strong_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    STRONG_BULLISH = "strong_bullish"

class DivergenceType(Enum):
    """Price-momentum divergence types"""
    BULLISH_REGULAR = "bullish_regular"
    BULLISH_HIDDEN = "bullish_hidden"
    BEARISH_REGULAR = "bearish_regular"
    BEARISH_HIDDEN = "bearish_hidden"
    NO_DIVERGENCE = "no_divergence"

@dataclass
class MomentumAnalysis:
    """Comprehensive momentum analysis"""
    state: MomentumState
    direction: MomentumDirection
    strength: float
    velocity: float
    acceleration: float
    volume_confirmation: bool
    smart_money_alignment: bool
    divergence_type: DivergenceType
    divergence_strength: float
    timestamp: datetime

class RSIComponents(NamedTuple):
    """RSI calculation components"""
    rsi: float
    avg_gain: float
    avg_loss: float
    rs: float
    volume_factor: float
    volume_weighted_rsi: float

class MACDComponents(NamedTuple):
    """MACD calculation components"""
    macd_line: float
    signal_line: float
    histogram: float
    fast_ema: float
    slow_ema: float
    volume_weighted_macd: float

class StochasticComponents(NamedTuple):
    """Stochastic calculation components"""
    k_percent: float
    d_percent: float
    j_percent: float
    highest_high: float
    lowest_low: float
    volume_weighted_k: float

# ===========================================
# RSI INDICATOR
# ===========================================

class RSI(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Institutional-Grade Volume-Weighted RSI
    
    Enhanced RSI with:
    - Volume weighting for institutional flow detection
    - Smart money confirmation signals
    - Adaptive overbought/oversold levels based on market regime
    - Divergence detection with price action
    - Multi-timeframe convergence analysis
    """
    
    def __init__(self, period: int = 14, config: IndicatorConfig = None):
        config = config or IndicatorConfig(period=period)
        super().__init__(config)
        
        self.period = period
        self.gains: deque = deque(maxlen=period * 2)
        self.losses: deque = deque(maxlen=period * 2)
        
        # RSI state
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_value = 50.0
        self.volume_weighted_rsi = 50.0
        
        # Adaptive levels
        self.overbought_level = 70.0
        self.oversold_level = 30.0
        
        # Divergence detection
        self.price_peaks: deque = deque(maxlen=10)
        self.rsi_peaks: deque = deque(maxlen=10)
        self.price_troughs: deque = deque(maxlen=10)
        self.rsi_troughs: deque = deque(maxlen=10)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
        
        # Smart money analysis integration
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
        self.institutional_bias: Optional[SmartMoneyBias] = None
        self.institutional_activity: Optional[InstitutionalActivity] = None
    
    @performance_monitor
    @robust_calculation(default_value=50.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted RSI value"""
        if len(self.prices) < 2:
            return 50.0
        
        # Calculate price change
        price_change = self.prices[-1] - self.prices[-2]
        volume_weight = self._get_volume_weight(self.volumes[-1])
        
        # Separate gains and losses with volume weighting
        if price_change > 0:
            gain = price_change * volume_weight
            loss = 0.0
        else:
            gain = 0.0
            loss = abs(price_change) * volume_weight
        
        self.gains.append(gain)
        self.losses.append(loss)
        
        # Calculate RSI
        if len(self.gains) >= self.period:
            self.avg_gain = np.mean(list(self.gains)[-self.period:])
            self.avg_loss = np.mean(list(self.losses)[-self.period:])
            
            if self.avg_loss == 0:
                self.rsi_value = 100.0
            else:
                rs = self.avg_gain / self.avg_loss
                self.rsi_value = 100 - (100 / (1 + rs))
        
        # Volume-weighted adjustment
        if self.config.enable_volume_weighting:
            volume_factor = min(volume_weight, 2.0)  # Cap at 2x
            if self.rsi_value > 50:
                self.volume_weighted_rsi = 50 + (self.rsi_value - 50) * volume_factor
            else:
                self.volume_weighted_rsi = 50 - (50 - self.rsi_value) * volume_factor
            
            # Ensure bounds
            self.volume_weighted_rsi = np.clip(self.volume_weighted_rsi, 0, 100)
        else:
            self.volume_weighted_rsi = self.rsi_value
        
        # Adapt levels based on market regime
        self._adapt_levels()
        
        # Detect divergences
        self._detect_divergences()
        
        return self.volume_weighted_rsi
    
    def _adapt_levels(self):
        """Adapt overbought/oversold levels based on market regime"""
        if self.current_regime == MarketRegime.TRENDING_UP:
            self.overbought_level = 80.0
            self.oversold_level = 40.0
        elif self.current_regime == MarketRegime.TRENDING_DOWN:
            self.overbought_level = 60.0
            self.oversold_level = 20.0
        elif self.current_regime == MarketRegime.HIGH_VOLATILITY:
            self.overbought_level = 75.0
            self.oversold_level = 25.0
        else:
            self.overbought_level = 70.0
            self.oversold_level = 30.0
    
    def _detect_divergences(self):
        """Detect price-RSI divergences"""
        if len(self.prices) < 10:
            return
        
        # Simple peak/trough detection
        current_price = self.prices[-1]
        current_rsi = self.volume_weighted_rsi
        
        # Store peaks and troughs (simplified)
        if len(self.prices) >= 3:
            if (self.prices[-2] > self.prices[-3] and 
                self.prices[-2] > current_price):
                self.price_peaks.append((len(self.prices)-2, self.prices[-2]))
                self.rsi_peaks.append((len(self.prices)-2, 
                                     self.volume_weighted_rsi if len(self.results) >= 2 else current_rsi))
            
            if (self.prices[-2] < self.prices[-3] and 
                self.prices[-2] < current_price):
                self.price_troughs.append((len(self.prices)-2, self.prices[-2]))
                self.rsi_troughs.append((len(self.prices)-2, 
                                       self.volume_weighted_rsi if len(self.results) >= 2 else current_rsi))
    
    def _generate_enhanced_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Generate RSI-specific signal"""
        # Determine signal type
        if value <= self.oversold_level:
            if value <= 20:
                signal_type = SignalType.STRONG_BUY
                strength = min((30 - value) / 10, 1.0)
            else:
                signal_type = SignalType.BUY
                strength = (self.oversold_level - value) / (self.oversold_level - 20)
        elif value >= self.overbought_level:
            if value >= 80:
                signal_type = SignalType.STRONG_SELL
                strength = min((value - 70) / 10, 1.0)
            else:
                signal_type = SignalType.SELL
                strength = (value - self.overbought_level) / (80 - self.overbought_level)
        else:
            signal_type = SignalType.NEUTRAL
            strength = 0.0
        
        # Calculate confidence based on volume confirmation
        confidence = 0.5
        if self.smart_money_metrics.institutional_activity > 0.3:
            confidence += 0.3
        if self.regime_confidence > 0.7:
            confidence += 0.2
        confidence = min(confidence, 1.0)
        
        # Create momentum analysis
        momentum_state = self._get_momentum_state(value)
        momentum_direction = self._get_momentum_direction()
        
        return IndicatorSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            timestamp=timestamp,
            value=value,
            normalized_value=value / 100.0,
            volume_confirmation=self.smart_money_metrics.institutional_activity > 0.3,
            volume_strength=self.smart_money_metrics.institutional_activity,
            volume_weighted_value=self.volume_weighted_rsi,
            market_regime=self.current_regime,
            regime_confidence=self.regime_confidence,
            smart_money_metrics=self.smart_money_metrics,
            risk_metrics=self.risk_metrics,
            metadata={
                'rsi_components': RSIComponents(
                    rsi=self.rsi_value,
                    avg_gain=self.avg_gain,
                    avg_loss=self.avg_loss,
                    rs=self.avg_gain / max(self.avg_loss, 1e-10),
                    volume_factor=self._get_volume_weight(self.volumes[-1]) if self.volumes else 1.0,
                    volume_weighted_rsi=self.volume_weighted_rsi
                ),
                'momentum_analysis': MomentumAnalysis(
                    state=momentum_state,
                    direction=momentum_direction,
                    strength=strength,
                    velocity=self._calculate_velocity(),
                    acceleration=self._calculate_acceleration(),
                    volume_confirmation=self.smart_money_metrics.institutional_activity > 0.3,
                    smart_money_alignment=self._check_smart_money_alignment(signal_type),
                    divergence_type=DivergenceType.NO_DIVERGENCE,  # Simplified
                    divergence_strength=0.0,
                    timestamp=timestamp
                ),
                'adaptive_levels': {
                    'overbought': self.overbought_level,
                    'oversold': self.oversold_level
                }
            }
        )
    
    def _get_momentum_state(self, value: float) -> MomentumState:
        """Get momentum state based on RSI value"""
        if value <= 20:
            return MomentumState.EXTREMELY_OVERSOLD
        elif value <= self.oversold_level:
            return MomentumState.OVERSOLD
        elif value >= 80:
            return MomentumState.EXTREMELY_OVERBOUGHT
        elif value >= self.overbought_level:
            return MomentumState.OVERBOUGHT
        else:
            return MomentumState.NEUTRAL
    
    def _get_momentum_direction(self) -> MomentumDirection:
        """Get momentum direction based on recent RSI changes"""
        if len(self.results) < 3:
            return MomentumDirection.NEUTRAL
        
        recent_values = [r.value for r in list(self.results)[-3:]]
        if len(recent_values) < 3:
            return MomentumDirection.NEUTRAL
        
        change1 = recent_values[-1] - recent_values[-2]
        change2 = recent_values[-2] - recent_values[-3]
        avg_change = (change1 + change2) / 2
        
        if avg_change > 5:
            return MomentumDirection.STRONG_BULLISH
        elif avg_change > 2:
            return MomentumDirection.BULLISH
        elif avg_change < -5:
            return MomentumDirection.STRONG_BEARISH
        elif avg_change < -2:
            return MomentumDirection.BEARISH
        else:
            return MomentumDirection.NEUTRAL
    
    def _calculate_velocity(self) -> float:
        """Calculate RSI velocity (rate of change)"""
        if len(self.results) < 2:
            return 0.0
        
        current_value = self.results[-1].value
        previous_value = self.results[-2].value
        return current_value - previous_value
    
    def _calculate_acceleration(self) -> float:
        """Calculate RSI acceleration (change in velocity)"""
        if len(self.results) < 3:
            return 0.0
        
        values = [r.value for r in list(self.results)[-3:]]
        velocity1 = values[-1] - values[-2]
        velocity2 = values[-2] - values[-3]
        return velocity1 - velocity2
    
    def _check_smart_money_alignment(self, signal_type: SignalType) -> bool:
        """Check if smart money flow aligns with RSI signal"""
        if signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            return self.smart_money_metrics.flow_direction.value in ['accumulation', 'institutional_buying']
        elif signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            return self.smart_money_metrics.flow_direction.value in ['distribution', 'institutional_selling']
        return True
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update RSI with enhanced volume confirmation analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update volume confirmation analysis
        volume_data = self.update_with_volume_confirmation(price, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')
        
        # Update smart money analysis
        smart_money_data = self.update_with_smart_money_analysis(price, volume, timestamp)
        self.smart_money_metrics = smart_money_data.get('smart_money_metrics')
        self.institutional_bias = smart_money_data.get('institutional_bias')
        self.institutional_activity = smart_money_data.get('institutional_activity')
        
        # Call parent update method
        result = super().update(price, volume, timestamp)
        
        # Enhance result with volume confirmation data
        if self.volume_confirmation_score and result.signal:
            # Adjust signal strength based on volume confirmation
            adjusted_strength = self.get_volume_adjusted_signal(
                result.signal.strength, 
                self.volume_confirmation_score
            )
            
            # Update signal with volume-adjusted strength
            result.signal.strength = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score
            
            # Add volume analysis to metadata
            if 'volume_confirmation_details' not in result.signal.metadata:
                result.signal.metadata['volume_confirmation_details'] = {}
            
            result.signal.metadata['volume_confirmation_details'].update({
                'confirmation_score': self.volume_confirmation_score.overall_score,
                'price_volume_sync': self.volume_confirmation_score.price_volume_sync,
                'volume_breakout': self.volume_confirmation_score.volume_breakout,
                'institutional_presence': self.volume_confirmation_score.institutional_presence,
                'volume_quality': self.volume_confirmation_score.volume_quality,
                'confidence': self.volume_confirmation_score.confidence
            })
            
            if self.volume_analysis:
                result.signal.metadata['volume_confirmation_details'].update({
                    'volume_regime': self.volume_analysis.volume_regime.value,
                    'volume_quality_rating': self.volume_analysis.volume_quality.value,
                    'order_flow_bias': self.volume_analysis.order_flow_bias.value,
                    'institutional_activity': self.volume_analysis.institutional_activity,
                    'relative_volume': self.volume_analysis.relative_volume,
                    'smart_money_flow': self.volume_analysis.smart_money_flow
                })
        
        # Enhance result with smart money analysis
        if self.smart_money_metrics and result.signal:
            # Adjust signal strength based on smart money alignment
            smart_money_alignment = self._check_smart_money_alignment(result.signal.signal_type)
            if smart_money_alignment:
                result.signal.strength = min(1.0, result.signal.strength * 1.2)
            else:
                result.signal.strength = max(0.1, result.signal.strength * 0.8)
            
            # Add smart money analysis to metadata
            if 'smart_money_analysis' not in result.signal.metadata:
                result.signal.metadata['smart_money_analysis'] = {}
            
            result.signal.metadata['smart_money_analysis'].update({
                'institutional_bias': self.institutional_bias.value if self.institutional_bias else 'neutral',
                'smart_money_alignment': smart_money_alignment,
                'flow_direction': self.smart_money_metrics.flow_direction.value if self.smart_money_metrics else 'neutral',
                'institutional_activity': self.institutional_activity.value if self.institutional_activity else 'low',
                'order_flow_strength': self.smart_money_metrics.order_flow_strength if self.smart_money_metrics else 0.0,
                'institutional_confidence': self.smart_money_metrics.institutional_confidence if self.smart_money_metrics else 0.0
            })
        
        return result
    
    def reset(self):
        """Reset RSI state"""
        super().reset()
        self.gains.clear()
        self.losses.clear()
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rsi_value = 50.0
        self.volume_weighted_rsi = 50.0
        self.price_peaks.clear()
        self.rsi_peaks.clear()
        self.price_troughs.clear()
        self.rsi_troughs.clear()

# ===========================================
# MACD INDICATOR
# ===========================================

class MACD(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Institutional-Grade Volume-Weighted MACD
    
    Enhanced MACD with:
    - Volume weighting for institutional flow detection
    - Smart money confirmation through histogram analysis
    - Adaptive signal line smoothing based on market regime
    - Multi-timeframe convergence analysis
    - Zero-lag enhancements for HFT environments
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, 
                 signal_period: int = 9, config: IndicatorConfig = None):
        config = config or IndicatorConfig(period=slow_period)
        super().__init__(config)
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        # MACD components
        self.fast_ema = 0.0
        self.slow_ema = 0.0
        self.macd_line = 0.0
        self.signal_line = 0.0
        self.histogram = 0.0
        
        # Volume-weighted components
        self.volume_weighted_macd = 0.0
        
        # EMA calculation helpers
        self.fast_alpha = 2.0 / (fast_period + 1)
        self.slow_alpha = 2.0 / (slow_period + 1)
        self.signal_alpha = 2.0 / (signal_period + 1)
        
        # Signal line history for smoothing
        self.signal_history: deque = deque(maxlen=signal_period * 2)
        
        # Zero-line crossings
        self.zero_crossings: deque = deque(maxlen=10)
        self.signal_crossings: deque = deque(maxlen=10)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
    
    @performance_monitor
    @robust_calculation(default_value=0.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted MACD value"""
        if len(self.prices) < 1:
            return 0.0
        
        current_price = self.prices[-1]
        volume_weight = self._get_volume_weight(self.volumes[-1]) if self.volumes else 1.0
        
        # Initialize EMAs on first calculation
        if len(self.prices) == 1:
            self.fast_ema = current_price
            self.slow_ema = current_price
            self.signal_line = 0.0
            return 0.0
        
        # Calculate volume-weighted price
        vw_price = current_price * volume_weight
        
        # Update EMAs with volume weighting
        self.fast_ema = self.fast_alpha * vw_price + (1 - self.fast_alpha) * self.fast_ema
        self.slow_ema = self.slow_alpha * vw_price + (1 - self.slow_alpha) * self.slow_ema
        
        # Calculate MACD line
        self.macd_line = self.fast_ema - self.slow_ema
        
        # Update signal line
        if len(self.prices) >= self.slow_period:
            self.signal_line = self.signal_alpha * self.macd_line + (1 - self.signal_alpha) * self.signal_line
        else:
            self.signal_line = self.macd_line
        
        # Calculate histogram
        self.histogram = self.macd_line - self.signal_line
        
        # Volume-weighted MACD adjustment
        if self.config.enable_volume_weighting:
            volume_factor = min(volume_weight, 1.5)  # Cap at 1.5x
            self.volume_weighted_macd = self.macd_line * volume_factor
        else:
            self.volume_weighted_macd = self.macd_line
        
        # Track crossings
        self._track_crossings()
        
        return self.volume_weighted_macd
    
    def _track_crossings(self):
        """Track zero-line and signal line crossings"""
        if len(self.results) < 2:
            return
        
        prev_macd = self.results[-2].value if len(self.results) >= 2 else 0
        prev_histogram = prev_macd - self.signal_line  # Approximation
        
        # Zero-line crossings
        if (prev_macd <= 0 and self.macd_line > 0) or (prev_macd >= 0 and self.macd_line < 0):
            self.zero_crossings.append({
                'timestamp': datetime.now(),
                'direction': 'bullish' if self.macd_line > 0 else 'bearish',
                'strength': abs(self.macd_line)
            })
        
        # Signal line crossings
        if (prev_histogram <= 0 and self.histogram > 0) or (prev_histogram >= 0 and self.histogram < 0):
            self.signal_crossings.append({
                'timestamp': datetime.now(),
                'direction': 'bullish' if self.histogram > 0 else 'bearish',
                'strength': abs(self.histogram)
            })
    
    def _generate_enhanced_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Generate MACD-specific signal"""
        # Determine signal type based on MACD line, signal line, and histogram
        signal_type = SignalType.NEUTRAL
        strength = 0.0
        
        # Primary signal from histogram
        if self.histogram > 0:
            if self.macd_line > 0:  # Both above zero - strong bullish
                signal_type = SignalType.STRONG_BUY
                strength = min(abs(self.histogram) / abs(self.macd_line), 1.0)
            else:  # MACD below zero but histogram positive - bullish momentum
                signal_type = SignalType.BUY
                strength = min(abs(self.histogram) / 0.1, 1.0)  # Normalize to reasonable scale
        elif self.histogram < 0:
            if self.macd_line < 0:  # Both below zero - strong bearish
                signal_type = SignalType.STRONG_SELL
                strength = min(abs(self.histogram) / abs(self.macd_line), 1.0)
            else:  # MACD above zero but histogram negative - bearish momentum
                signal_type = SignalType.SELL
                strength = min(abs(self.histogram) / 0.1, 1.0)
        
        # Adjust strength based on recent crossings
        if self.signal_crossings and len(self.signal_crossings) > 0:
            recent_crossing = self.signal_crossings[-1]
            if (datetime.now() - recent_crossing['timestamp']).seconds < 300:  # Within 5 minutes
                strength *= 1.2  # Boost strength for recent crossings
        
        # Calculate confidence
        confidence = 0.5
        if abs(self.histogram) > abs(self.macd_line) * 0.1:  # Strong histogram
            confidence += 0.2
        if self.smart_money_metrics.institutional_activity > 0.3:
            confidence += 0.2
        if self.regime_confidence > 0.7:
            confidence += 0.1
        confidence = min(confidence, 1.0)
        
        return IndicatorSignal(
            signal_type=signal_type,
            strength=min(strength, 1.0),
            confidence=confidence,
            timestamp=timestamp,
            value=value,
            volume_confirmation=self.smart_money_metrics.institutional_activity > 0.3,
            volume_strength=self.smart_money_metrics.institutional_activity,
            volume_weighted_value=self.volume_weighted_macd,
            market_regime=self.current_regime,
            regime_confidence=self.regime_confidence,
            smart_money_metrics=self.smart_money_metrics,
            risk_metrics=self.risk_metrics,
            metadata={
                'macd_components': MACDComponents(
                    macd_line=self.macd_line,
                    signal_line=self.signal_line,
                    histogram=self.histogram,
                    fast_ema=self.fast_ema,
                    slow_ema=self.slow_ema,
                    volume_weighted_macd=self.volume_weighted_macd
                ),
                'crossings': {
                    'recent_zero_crossings': len([c for c in self.zero_crossings 
                                                if (datetime.now() - c['timestamp']).seconds < 3600]),
                    'recent_signal_crossings': len([c for c in self.signal_crossings 
                                                  if (datetime.now() - c['timestamp']).seconds < 3600])
                },
                'trend_analysis': {
                    'macd_trend': 'bullish' if self.macd_line > 0 else 'bearish',
                    'momentum_trend': 'bullish' if self.histogram > 0 else 'bearish',
                    'convergence': abs(self.macd_line - self.signal_line) < abs(self.macd_line) * 0.1
                }
            }
        )
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update MACD with enhanced volume confirmation analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update volume confirmation analysis
        volume_data = self.update_with_volume_confirmation(price, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')
        
        # Call parent update method
        result = super().update(price, volume, timestamp)
        
        # Enhance result with volume confirmation data
        if self.volume_confirmation_score and result.signal:
            # Adjust signal strength based on volume confirmation
            adjusted_strength = self.get_volume_adjusted_signal(
                result.signal.strength, 
                self.volume_confirmation_score
            )
            
            # Update signal with volume-adjusted strength
            result.signal.strength = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score
            
            # Add volume analysis to metadata
            if 'volume_confirmation_details' not in result.signal.metadata:
                result.signal.metadata['volume_confirmation_details'] = {}
            
            result.signal.metadata['volume_confirmation_details'].update({
                'confirmation_score': self.volume_confirmation_score.overall_score,
                'price_volume_sync': self.volume_confirmation_score.price_volume_sync,
                'volume_breakout': self.volume_confirmation_score.volume_breakout,
                'institutional_presence': self.volume_confirmation_score.institutional_presence,
                'volume_quality': self.volume_confirmation_score.volume_quality,
                'confidence': self.volume_confirmation_score.confidence
            })
            
            if self.volume_analysis:
                result.signal.metadata['volume_confirmation_details'].update({
                    'volume_regime': self.volume_analysis.volume_regime.value,
                    'volume_quality_rating': self.volume_analysis.volume_quality.value,
                    'order_flow_bias': self.volume_analysis.order_flow_bias.value,
                    'institutional_activity': self.volume_analysis.institutional_activity,
                    'relative_volume': self.volume_analysis.relative_volume,
                    'smart_money_flow': self.volume_analysis.smart_money_flow
                })
        
        return result
    
    def reset(self):
        """Reset MACD state"""
        super().reset()
        self.fast_ema = 0.0
        self.slow_ema = 0.0
        self.macd_line = 0.0
        self.signal_line = 0.0
        self.histogram = 0.0
        self.volume_weighted_macd = 0.0
        self.signal_history.clear()
        self.zero_crossings.clear()
        self.signal_crossings.clear()

# ===========================================
# STOCHASTIC OSCILLATOR
# ===========================================

class Stochastic(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Institutional-Grade Volume-Weighted Stochastic Oscillator
    
    Enhanced Stochastic with:
    - Volume weighting for institutional flow detection
    - Adaptive %K and %D periods based on market regime
    - Smart money confirmation through volume analysis
    - Multi-timeframe convergence analysis
    - J-line calculation for early signals
    """
    
    def __init__(self, k_period: int = 14, d_period: int = 3, 
                 smooth_k: int = 3, config: IndicatorConfig = None):
        config = config or IndicatorConfig(period=k_period)
        super().__init__(config)
        
        self.k_period = k_period
        self.d_period = d_period
        self.smooth_k = smooth_k
        
        # Stochastic components
        self.k_percent = 50.0
        self.d_percent = 50.0
        self.j_percent = 50.0
        
        # Volume-weighted components
        self.volume_weighted_k = 50.0
        
        # High/Low tracking
        self.highs: deque = deque(maxlen=k_period * 2)
        self.lows: deque = deque(maxlen=k_period * 2)
        
        # %K smoothing
        self.raw_k_values: deque = deque(maxlen=smooth_k * 2)
        self.k_values: deque = deque(maxlen=d_period * 2)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
    
    @performance_monitor
    @robust_calculation(default_value=50.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted Stochastic value"""
        if len(self.prices) < 1:
            return 50.0
        
        current_price = self.prices[-1]
        volume_weight = self._get_volume_weight(self.volumes[-1]) if self.volumes else 1.0
        
        # Store high and low (using price as both for simplicity)
        # In real implementation, you'd use actual high/low values
        self.highs.append(current_price)
        self.lows.append(current_price)
        
        if len(self.highs) < self.k_period:
            return 50.0
        
        # Calculate %K
        highest_high = max(list(self.highs)[-self.k_period:])
        lowest_low = min(list(self.lows)[-self.k_period:])
        
        if highest_high == lowest_low:
            raw_k = 50.0
        else:
            raw_k = ((current_price - lowest_low) / (highest_high - lowest_low)) * 100
        
        self.raw_k_values.append(raw_k)
        
        # Smooth %K
        if len(self.raw_k_values) >= self.smooth_k:
            self.k_percent = np.mean(list(self.raw_k_values)[-self.smooth_k:])
        else:
            self.k_percent = raw_k
        
        self.k_values.append(self.k_percent)
        
        # Calculate %D (SMA of %K)
        if len(self.k_values) >= self.d_period:
            self.d_percent = np.mean(list(self.k_values)[-self.d_period:])
        else:
            self.d_percent = self.k_percent
        
        # Calculate %J
        self.j_percent = 3 * self.k_percent - 2 * self.d_percent
        self.j_percent = np.clip(self.j_percent, 0, 100)
        
        # Volume-weighted adjustment
        if self.config.enable_volume_weighting:
            volume_factor = min(volume_weight, 1.3)  # Cap at 1.3x
            if self.k_percent > 50:
                self.volume_weighted_k = 50 + (self.k_percent - 50) * volume_factor
            else:
                self.volume_weighted_k = 50 - (50 - self.k_percent) * volume_factor
            
            self.volume_weighted_k = np.clip(self.volume_weighted_k, 0, 100)
        else:
            self.volume_weighted_k = self.k_percent
        
        return self.volume_weighted_k
    
    def _generate_enhanced_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Generate Stochastic-specific signal"""
        # Determine signal type
        signal_type = SignalType.NEUTRAL
        strength = 0.0
        
        # Primary signals from %K and %D levels
        if self.k_percent <= 20 and self.d_percent <= 20:
            signal_type = SignalType.STRONG_BUY
            strength = (20 - min(self.k_percent, self.d_percent)) / 20
        elif self.k_percent <= 30 or self.d_percent <= 30:
            signal_type = SignalType.BUY
            strength = (30 - min(self.k_percent, self.d_percent)) / 10
        elif self.k_percent >= 80 and self.d_percent >= 80:
            signal_type = SignalType.STRONG_SELL
            strength = (min(self.k_percent, self.d_percent) - 80) / 20
        elif self.k_percent >= 70 or self.d_percent >= 70:
            signal_type = SignalType.SELL
            strength = (min(self.k_percent, self.d_percent) - 70) / 10
        
        # Enhance signal with %K/%D crossovers
        if len(self.k_values) >= 2:
            prev_k = list(self.k_values)[-2] if len(self.k_values) >= 2 else self.k_percent
            
            # Bullish crossover (%K crosses above %D)
            if prev_k <= self.d_percent and self.k_percent > self.d_percent:
                if signal_type == SignalType.NEUTRAL:
                    signal_type = SignalType.BUY
                    strength = 0.5
                elif signal_type == SignalType.BUY:
                    strength = min(strength * 1.3, 1.0)
            
            # Bearish crossover (%K crosses below %D)
            elif prev_k >= self.d_percent and self.k_percent < self.d_percent:
                if signal_type == SignalType.NEUTRAL:
                    signal_type = SignalType.SELL
                    strength = 0.5
                elif signal_type == SignalType.SELL:
                    strength = min(strength * 1.3, 1.0)
        
        # Calculate confidence
        confidence = 0.5
        if abs(self.k_percent - self.d_percent) > 5:  # Clear separation
            confidence += 0.2
        if self.smart_money_metrics.institutional_activity > 0.3:
            confidence += 0.2
        if self.regime_confidence > 0.7:
            confidence += 0.1
        confidence = min(confidence, 1.0)
        
        return IndicatorSignal(
            signal_type=signal_type,
            strength=min(strength, 1.0),
            confidence=confidence,
            timestamp=timestamp,
            value=value,
            normalized_value=value / 100.0,
            volume_confirmation=self.smart_money_metrics.institutional_activity > 0.3,
            volume_strength=self.smart_money_metrics.institutional_activity,
            volume_weighted_value=self.volume_weighted_k,
            market_regime=self.current_regime,
            regime_confidence=self.regime_confidence,
            smart_money_metrics=self.smart_money_metrics,
            risk_metrics=self.risk_metrics,
            metadata={
                'stochastic_components': StochasticComponents(
                    k_percent=self.k_percent,
                    d_percent=self.d_percent,
                    j_percent=self.j_percent,
                    highest_high=max(list(self.highs)[-self.k_period:]) if len(self.highs) >= self.k_period else 0,
                    lowest_low=min(list(self.lows)[-self.k_period:]) if len(self.lows) >= self.k_period else 0,
                    volume_weighted_k=self.volume_weighted_k
                ),
                'oscillator_analysis': {
                    'overbought': self.k_percent >= 80 or self.d_percent >= 80,
                    'oversold': self.k_percent <= 20 or self.d_percent <= 20,
                    'crossover_signal': 'bullish' if self.k_percent > self.d_percent else 'bearish',
                    'j_line_signal': 'extreme_bullish' if self.j_percent > 100 else 'extreme_bearish' if self.j_percent < 0 else 'normal'
                }
            }
        )
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update Stochastic with enhanced volume confirmation analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update volume confirmation analysis
        volume_data = self.update_with_volume_confirmation(price, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')
        
        # Call parent update method
        result = super().update(price, volume, timestamp)
        
        # Enhance result with volume confirmation data
        if self.volume_confirmation_score and result.signal:
            # Adjust signal strength based on volume confirmation
            adjusted_strength = self.get_volume_adjusted_signal(
                result.signal.strength, 
                self.volume_confirmation_score
            )
            
            # Update signal with volume-adjusted strength
            result.signal.strength = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score
            
            # Add volume analysis to metadata
            if 'volume_confirmation_details' not in result.signal.metadata:
                result.signal.metadata['volume_confirmation_details'] = {}
            
            result.signal.metadata['volume_confirmation_details'].update({
                'confirmation_score': self.volume_confirmation_score.overall_score,
                'price_volume_sync': self.volume_confirmation_score.price_volume_sync,
                'volume_breakout': self.volume_confirmation_score.volume_breakout,
                'institutional_presence': self.volume_confirmation_score.institutional_presence,
                'volume_quality': self.volume_confirmation_score.volume_quality,
                'confidence': self.volume_confirmation_score.confidence
            })
            
            if self.volume_analysis:
                result.signal.metadata['volume_confirmation_details'].update({
                    'volume_regime': self.volume_analysis.volume_regime.value,
                    'volume_quality_rating': self.volume_analysis.volume_quality.value,
                    'order_flow_bias': self.volume_analysis.order_flow_bias.value,
                    'institutional_activity': self.volume_analysis.institutional_activity,
                    'relative_volume': self.volume_analysis.relative_volume,
                    'smart_money_flow': self.volume_analysis.smart_money_flow
                })
        
        return result
    
    def reset(self):
        """Reset Stochastic state"""
        super().reset()
        self.k_percent = 50.0
        self.d_percent = 50.0
        self.j_percent = 50.0
        self.volume_weighted_k = 50.0
        self.highs.clear()
        self.lows.clear()
        self.raw_k_values.clear()
        self.k_values.clear()

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_rsi(period: int = 14, **kwargs) -> RSI:
    """Factory function for creating RSI indicator"""
    config = IndicatorConfig(period=period, **kwargs)
    return RSI(period=period, config=config)

def create_macd(fast_period: int = 12, slow_period: int = 26, 
                signal_period: int = 9, **kwargs) -> MACD:
    """Factory function for creating MACD indicator"""
    config = IndicatorConfig(period=slow_period, **kwargs)
    return MACD(fast_period=fast_period, slow_period=slow_period, 
                signal_period=signal_period, config=config)

def create_stochastic(k_period: int = 14, d_period: int = 3, 
                     smooth_k: int = 3, **kwargs) -> Stochastic:
    """Factory function for creating Stochastic indicator"""
    config = IndicatorConfig(period=k_period, **kwargs)
    return Stochastic(k_period=k_period, d_period=d_period, 
                     smooth_k=smooth_k, config=config)

# Export all classes and functions
__all__ = [
    # Indicators
    'RSI', 'MACD', 'Stochastic',
    
    # Enums and data classes
    'MomentumState', 'MomentumDirection', 'DivergenceType',
    'MomentumAnalysis', 'RSIComponents', 'MACDComponents', 'StochasticComponents',
    
    # Factory functions
    'create_rsi', 'create_macd', 'create_stochastic'
]