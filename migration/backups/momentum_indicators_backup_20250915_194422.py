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
# Optional TA-Lib import with graceful fallback
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    talib = None
    TALIB_AVAILABLE = False
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

# New Williams %R components
class WilliamsRComponents(NamedTuple):
    """Williams %R calculation components"""
    williams_r_raw: float  # -100 to 0
    williams_r_normalized: float  # 0 to 100 (100 + raw)
    highest_high: float
    lowest_low: float
    volume_weighted_wr: float

# ===========================================
# RSI (Relative Strength Index)
# ===========================================

class RSI(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Institutional-Grade Volume-Weighted RSI
    
    Enhanced RSI with:
    - Proper EMA-style smoothing of gains/losses
    - Alpha = 1.0 / period for smoothing consistency across the suite
    - Volume weighting to amplify conviction away from the 50 midline
    - Smart money and regime-aware confidence scoring
    - MTF convergence and volume confirmation integration
    """

    def __init__(self, period: int = 14, config: IndicatorConfig = None):
        config = config or IndicatorConfig(period=period)
        super().__init__(config)

        self.period = period
        # Smoothing alpha per config policy
        self.alpha = self.config.get_alpha(self.period)

        # Core RSI state
        self.prev_price: Optional[float] = None
        self.avg_gain: float = 0.0
        self.avg_loss: float = 0.0
        self.rs: float = 0.0
        self.rsi: float = 50.0
        self.volume_factor: float = 1.0
        self.volume_weighted_rsi: float = 50.0

        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None

        # EWM ratio accumulators for volume-weighted RSI (avg gain/loss)
        self._gain_num = None
        self._gain_den = None
        self._loss_num = None
        self._loss_den = None

    @performance_monitor
    @robust_calculation(default_value=50.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted RSI (0-100)."""
        if len(self.prices) < 1:
            return 50.0

        price = self.prices[-1]
        volume_weight = self._get_volume_weight(self.volumes[-1]) if self.volumes else 1.0

        if self.prev_price is None:
            # Initialize on first tick
            self.prev_price = price
            return 50.0

        change = price - self.prev_price
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        # EMA-style smoothing with alpha = 1.0/period
        self.avg_gain = (1 - self.alpha) * self.avg_gain + self.alpha * gain
        self.avg_loss = (1 - self.alpha) * self.avg_loss + self.alpha * loss

        if self.avg_loss == 0:
            self.rs = float('inf') if self.avg_gain > 0 else 0.0
            self.rsi = 100.0 if self.avg_gain > 0 else 50.0
        else:
            self.rs = self.avg_gain / self.avg_loss
            self.rsi = 100.0 - (100.0 / (1.0 + self.rs))

        # Volume-weighted RSI via EWM(gain*vol)/EWM(vol) and EWM(loss*vol)/EWM(vol)
        vol = float(self.volumes[-1]) if self.volumes else 1.0
        if self._gain_num is None:
            self._gain_num = gain * vol
            self._gain_den = vol
            self._loss_num = loss * vol
            self._loss_den = vol
        else:
            one_minus = (1.0 - self.alpha)
            a = self.alpha
            self._gain_num = one_minus * self._gain_num + a * (gain * vol)
            self._gain_den = one_minus * self._gain_den + a * vol
            self._loss_num = one_minus * self._loss_num + a * (loss * vol)
            self._loss_den = one_minus * self._loss_den + a * vol
        vw_avg_gain = (self._gain_num / self._gain_den) if (self._gain_den and self._gain_den > 1e-12) else 0.0
        vw_avg_loss = (self._loss_num / self._loss_den) if (self._loss_den and self._loss_den > 1e-12) else 0.0
        if vw_avg_loss <= 1e-12:
            vw_rsi = 100.0 if vw_avg_gain > 0 else 50.0
        else:
            vw_rs = vw_avg_gain / vw_avg_loss
            vw_rsi = 100.0 - (100.0 / (1.0 + vw_rs))
        # Preserve volume_factor metadata; set to 1.0 since amplification is not used in ratio method
        self.volume_factor = 1.0
        self.volume_weighted_rsi = float(np.clip(vw_rsi, 0.0, 100.0)) if self.config.enable_volume_weighting else self.rsi

        self.prev_price = price
        return self.volume_weighted_rsi

    def _generate_enhanced_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Generate RSI-specific signal with regime/context enhancements."""
        signal_type = SignalType.NEUTRAL
        strength = 0.0

        # Classic RSI thresholds with strong zones
        if self.rsi <= 20:
            signal_type = SignalType.STRONG_BUY
            strength = (20 - self.rsi) / 20
        elif self.rsi <= 30:
            signal_type = SignalType.BUY
            strength = (30 - self.rsi) / 10
        elif self.rsi >= 80:
            signal_type = SignalType.STRONG_SELL
            strength = (self.rsi - 80) / 20
        elif self.rsi >= 70:
            signal_type = SignalType.SELL
            strength = (self.rsi - 70) / 10

        # Midline crossover filter for momentum shift reinforcement
        if len(self.results) >= 1:
            prev = getattr(self, 'prev_rsi', 50.0)
            if prev <= 50.0 and self.rsi > 50.0 and signal_type == SignalType.NEUTRAL:
                signal_type = SignalType.BUY
                strength = max(strength, 0.4)
            elif prev >= 50.0 and self.rsi < 50.0 and signal_type == SignalType.NEUTRAL:
                signal_type = SignalType.SELL
                strength = max(strength, 0.4)
        self.prev_rsi = self.rsi

        # Confidence composition
        confidence = 0.5
        if abs(self.rsi - 50.0) > 15.0:
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
            volume_weighted_value=self.volume_weighted_rsi,
            market_regime=self.current_regime,
            regime_confidence=self.regime_confidence,
            smart_money_metrics=self.smart_money_metrics,
            risk_metrics=self.risk_metrics,
            metadata={
                'rsi_components': RSIComponents(
                    rsi=self.rsi,
                    avg_gain=self.avg_gain,
                    avg_loss=self.avg_loss,
                    rs=self.rs if np.isfinite(self.rs) else 0.0,
                    volume_factor=self.volume_factor,
                    volume_weighted_rsi=self.volume_weighted_rsi
                ),
                'oscillator_analysis': {
                    'overbought': self.rsi >= 70,
                    'oversold': self.rsi <= 30,
                    'midline_cross': 'bullish' if self.rsi > 50 else 'bearish'
                }
            }
        )

    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update RSI with enhanced volume confirmation analysis."""
        timestamp = timestamp or datetime.now()

        # Update volume confirmation analysis
        volume_data = self.update_with_volume_confirmation(price, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')

        # Call parent update method
        result = super().update(price, volume, timestamp)

        # Enhance result with volume confirmation data
        if self.volume_confirmation_score and result.signal:
            adjusted_strength = self.get_volume_adjusted_signal(
                result.signal.strength,
                self.volume_confirmation_score
            )
            result.signal.strength = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score

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
        """Reset RSI state"""
        super().reset()
        self.prev_price = None
        self.avg_gain = 0.0
        self.avg_loss = 0.0
        self.rs = 0.0
        self.rsi = 50.0
        self.volume_factor = 1.0
        self.volume_weighted_rsi = 50.0
        # Clear EWM ratio accumulators for VW RSI
        self._gain_num = None
        self._gain_den = None
        self._loss_num = None
        self._loss_den = None

class MACD(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Institutional-Grade Volume-Weighted MACD
    
    Enhanced MACD with:
    - Volume weighting for institutional flow detection
    - Smart money confirmation through histogram analysis
    - Adaptive signal line smoothing based on market regime
    - Zero-lag enhancements and crossing tracking
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
        # Maintain numerator/denominator EWMs for proper volume-weighted EMA
        self._fast_num_ema = 0.0
        self._fast_den_ema = 0.0
        self._slow_num_ema = 0.0
        self._slow_den_ema = 0.0

        # EMA calculation helpers using configurable alpha policy
        self.fast_alpha = self.config.get_alpha(self.fast_period)
        self.slow_alpha = self.config.get_alpha(self.slow_period)
        self.signal_alpha = self.config.get_alpha(self.signal_period)

        # Signal line history for smoothing
        self.signal_history: deque = deque(maxlen=signal_period * 2)

        # Crossings
        self.zero_crossings: deque = deque(maxlen=10)
        self.signal_crossings: deque = deque(maxlen=10)

        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None

    @performance_monitor
    @robust_calculation(default_value=0.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted MACD value using EWM fraction methodology."""
        if len(self.prices) < 1:
            return 0.0

        current_price = float(self.prices[-1])
        current_volume = float(self.volumes[-1]) if self.volumes else 1.0
        if current_volume < 0:
            current_volume = 0.0

        # Initialize on first calculation
        if len(self.prices) == 1:
            # Initialize numerator/denominator EWMs
            pv = current_price * current_volume
            self._fast_num_ema = pv
            self._fast_den_ema = max(1e-12, current_volume)
            self._slow_num_ema = pv
            self._slow_den_ema = max(1e-12, current_volume)
            self.fast_ema = self._fast_num_ema / self._fast_den_ema
            self.slow_ema = self._slow_num_ema / self._slow_den_ema
            self.macd_line = self.fast_ema - self.slow_ema
            self.signal_line = 0.0
            self.histogram = self.macd_line - self.signal_line
            self.volume_weighted_macd = self.macd_line
            return self.volume_weighted_macd

        # Update numerator/denominator EWMs for fast and slow using alpha policy
        a_fast = self.fast_alpha
        a_slow = self.slow_alpha
        pv = current_price * current_volume
        sv = current_volume

        self._fast_num_ema = a_fast * pv + (1.0 - a_fast) * self._fast_num_ema
        self._fast_den_ema = a_fast * sv + (1.0 - a_fast) * self._fast_den_ema
        self._slow_num_ema = a_slow * pv + (1.0 - a_slow) * self._slow_num_ema
        self._slow_den_ema = a_slow * sv + (1.0 - a_slow) * self._slow_den_ema

        # Compute volume-weighted EMAs as ratios
        fast_den = max(1e-12, self._fast_den_ema)
        slow_den = max(1e-12, self._slow_den_ema)
        self.fast_ema = self._fast_num_ema / fast_den
        self.slow_ema = self._slow_num_ema / slow_den

        # MACD line and signal/histogram
        self.macd_line = self.fast_ema - self.slow_ema
        self.signal_line = self.signal_alpha * self.macd_line + (1.0 - self.signal_alpha) * self.signal_line
        self.histogram = self.macd_line - self.signal_line

        # In unified methodology, the computed MACD line is already volume-weighted
        self.volume_weighted_macd = self.macd_line

        # Track crossings
        self._track_crossings()

        return self.volume_weighted_macd

    def _track_crossings(self):
        """Track zero-line and signal line crossings."""
        if len(self.results) < 2:
            return

        prev_macd = self.results[-2].value if len(self.results) >= 2 else 0.0
        prev_histogram = prev_macd - self.signal_line  # Approximation using prior value

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
        """Generate MACD-specific signal."""
        signal_type = SignalType.NEUTRAL
        strength = 0.0

        # Primary signal from histogram and MACD sign
        if self.histogram > 0:
            if self.macd_line > 0:  # Both above zero - strong bullish
                signal_type = SignalType.STRONG_BUY
                strength = min(abs(self.histogram) / (abs(self.macd_line) + 1e-9), 1.0)
            else:  # MACD below zero but histogram positive - bullish momentum
                signal_type = SignalType.BUY
                strength = min(abs(self.histogram) / 0.1, 1.0)  # Normalize to reasonable scale
        elif self.histogram < 0:
            if self.macd_line < 0:  # Both below zero - strong bearish
                signal_type = SignalType.STRONG_SELL
                strength = min(abs(self.histogram) / (abs(self.macd_line) + 1e-9), 1.0)
            else:  # MACD above zero but histogram negative - bearish momentum
                signal_type = SignalType.SELL
                strength = min(abs(self.histogram) / 0.1, 1.0)

        # Adjust strength based on recent crossings
        if self.signal_crossings:
            recent_crossing = self.signal_crossings[-1]
            if (datetime.now() - recent_crossing['timestamp']).seconds < 300:
                strength = min(strength * 1.2, 1.0)

        # Calculate confidence
        confidence = 0.5
        if abs(self.histogram) > abs(self.macd_line) * 0.1:
            confidence += 0.2
        if self.smart_money_metrics.institutional_activity > 0.3:
            confidence += 0.2
        if self.regime_confidence > 0.7:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        return IndicatorSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            timestamp=timestamp,
            value=value,
            normalized_value=value,  # MACD is not bounded; keep as-is
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
                    'recent_zero_crossings': len([c for c in self.zero_crossings if (datetime.now() - c['timestamp']).seconds < 3600]),
                    'recent_signal_crossings': len([c for c in self.signal_crossings if (datetime.now() - c['timestamp']).seconds < 3600])
                },
                'trend_analysis': {
                    'macd_trend': 'bullish' if self.macd_line > 0 else 'bearish',
                    'momentum_trend': 'bullish' if self.histogram > 0 else 'bearish',
                    'convergence': abs(self.macd_line - self.signal_line) < (abs(self.macd_line) + 1e-9) * 0.1
                }
            }
        )

    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update MACD with enhanced volume confirmation analysis."""
        timestamp = timestamp or datetime.now()

        # Update volume confirmation analysis
        volume_data = self.update_with_volume_confirmation(price, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')

        # Call parent update method
        result = super().update(price, volume, timestamp)

        # Enhance result with volume confirmation data
        if self.volume_confirmation_score and result.signal:
            adjusted_strength = self.get_volume_adjusted_signal(
                result.signal.strength,
                self.volume_confirmation_score
            )
            result.signal.strength = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score

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
        # Clear EWM fraction accumulators
        self._fast_num_ema = 0.0
        self._fast_den_ema = 0.0
        self._slow_num_ema = 0.0
        self._slow_den_ema = 0.0
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
    def _extract_ohlc(self, price_input) -> tuple:
        """Duck-type extraction of (open, high, low, close) from various inputs.
        Returns (o, h, l, c) where any missing values are None.
        Supported inputs:
        - dict-like with keys: 'open'/'o', 'high'/'h', 'low'/'l', 'close'/'c'
        - object with attributes: open/high/low/close or o/h/l/c
        - tuple/list in order (open, high, low, close)
        - fallback: treat input as close only
        """
        o = h = l = c = None
        try:
            # Mapping-like
            if isinstance(price_input, dict):
                o = price_input.get('open') if 'open' in price_input else price_input.get('o')
                h = price_input.get('high') if 'high' in price_input else price_input.get('h')
                l = price_input.get('low') if 'low' in price_input else price_input.get('l')
                c = price_input.get('close') if 'close' in price_input else price_input.get('c')
            else:
                # Attribute-like
                for attr_pair in [('open','o'), ('high','h'), ('low','l'), ('close','c')]:
                    primary, alt = attr_pair
                    if c is None and hasattr(price_input, primary):
                        # We will set in per-field below
                        pass
                # Open
                if hasattr(price_input, 'open'):
                    o = getattr(price_input, 'open')
                elif hasattr(price_input, 'o'):
                    o = getattr(price_input, 'o')
                # High
                if hasattr(price_input, 'high'):
                    h = getattr(price_input, 'high')
                elif hasattr(price_input, 'h'):
                    h = getattr(price_input, 'h')
                # Low
                if hasattr(price_input, 'low'):
                    l = getattr(price_input, 'low')
                elif hasattr(price_input, 'l'):
                    l = getattr(price_input, 'l')
                # Close
                if hasattr(price_input, 'close'):
                    c = getattr(price_input, 'close')
                elif hasattr(price_input, 'c'):
                    c = getattr(price_input, 'c')
                # Sequence-like (open, high, low, close)
                if c is None and isinstance(price_input, (list, tuple)):
                    if len(price_input) >= 4:
                        o, h, l, c = price_input[0], price_input[1], price_input[2], price_input[3]
                    elif len(price_input) == 3:
                        # Could be (high, low, close)
                        h, l, c = price_input[0], price_input[1], price_input[2]
        except Exception:
            pass
        return o, h, l, c

    @performance_monitor
    @robust_calculation(default_value=50.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted Stochastic value using EWM(price*vol)/EWM(vol)."""
        if len(self.prices) < 1:
            return 50.0
        
        # Lazy-init alphas and accumulators to avoid __init__ edits
        if not hasattr(self, 'alpha_k'):
            self.alpha_k = self.config.get_alpha(self.k_period)
        if not hasattr(self, 'alpha_d'):
            self.alpha_d = self.config.get_alpha(self.d_period)
        if not hasattr(self, 'alpha_smooth_k'):
            self.alpha_smooth_k = self.config.get_alpha(self.smooth_k)
        if not hasattr(self, '_vwk_num'):
            self._vwk_num = None
            self._vwk_den = None
            self._ewm_k = None
            self._ewm_d = None
        
        current_close = float(self.prices[-1])
        
        # Track highs/lows using last provided OHLC when available
        if getattr(self, '_last_high', None) is not None and getattr(self, '_last_low', None) is not None:
            self.highs.append(float(self._last_high))
            self.lows.append(float(self._last_low))
        else:
            self.highs.append(current_close)
            self.lows.append(current_close)
        
        if len(self.highs) < self.k_period:
            return 50.0
        
        highest_high = max(list(self.highs)[-self.k_period:])
        lowest_low = min(list(self.lows)[-self.k_period:])
        
        # Raw %K (0..100)
        if highest_high == lowest_low:
            raw_k = 50.0
        else:
            raw_k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100.0
        self.raw_k_values.append(raw_k)
        
        # Volume-weighted %K via EWM ratio
        vol = float(self.volumes[-1]) if self.volumes else 1.0
        if self._vwk_num is None:
            self._vwk_num = raw_k * vol
            self._vwk_den = vol
        else:
            self._vwk_num = (1.0 - self.alpha_k) * self._vwk_num + self.alpha_k * (raw_k * vol)
            self._vwk_den = (1.0 - self.alpha_k) * self._vwk_den + self.alpha_k * vol
        vw_k = (self._vwk_num / self._vwk_den) if (self._vwk_den or 0.0) > 1e-12 else raw_k
        
        # Smooth %K with EWM
        if self._ewm_k is None:
            self._ewm_k = vw_k
        else:
            self._ewm_k = (1.0 - self.alpha_smooth_k) * self._ewm_k + self.alpha_smooth_k * vw_k
        self.k_percent = float(np.clip(self._ewm_k, 0.0, 100.0))
        
        # %D as EWM of %K
        if self._ewm_d is None:
            self._ewm_d = self.k_percent
        else:
            self._ewm_d = (1.0 - self.alpha_d) * self._ewm_d + self.alpha_d * self.k_percent
        self.d_percent = float(np.clip(self._ewm_d, 0.0, 100.0))
        
        # %J line
        self.j_percent = float(np.clip(3.0 * self.k_percent - 2.0 * self.d_percent, 0.0, 100.0))
        
        # Maintain history for crossover logic
        self.k_values.append(self.k_percent)
        
        # Report volume-weighted K
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
        
        # Duck-type OHLC extraction; pass close to base update
        o, h, l, c = self._extract_ohlc(price)
        close_val = float(c if c is not None else price)
        self._last_high = float(h) if h is not None else None
        self._last_low = float(l) if l is not None else None
        self._last_close = close_val
        
        # Update volume confirmation analysis using close
        volume_data = self.update_with_volume_confirmation(close_val, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')
        
        # Call parent update method with close price
        result = super().update(close_val, volume, timestamp)
        
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
        
        # Clear EWM and VW accumulators
        self._ewm_k = None
        self._ewm_d = None
        self._vwk_num = None
        self._vwk_den = None
        
        # Clear last OHLC cache
        self._last_high = None
        self._last_low = None
        self._last_close = None

# ===========================================
# WILLIAMS %R
# ===========================================

class WilliamsR(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Institutional-Grade Volume-Weighted Williams %R
    
    Enhanced Williams %R with:
    - Volume weighting for institutional flow detection
    - Adaptive thresholds based on market regime
    - Smart money confirmation through volume analysis
    - Multi-timeframe convergence analysis
    
    Note: Internally computes raw %R in [-100, 0] and normalized value in [0, 100]
    to align thresholds with other oscillators (<=20 oversold, >=80 overbought).
    """

    def __init__(self, period: int = 14, config: IndicatorConfig = None):
        config = config or IndicatorConfig(period=period)
        super().__init__(config)

        self.period = period
        # State
        self.williams_r_raw = -50.0
        self.williams_r_normalized = 50.0
        self.volume_weighted_wr = 50.0
        
        # High/Low tracking (using last price for both in this implementation)
        self.highs: deque = deque(maxlen=period * 2)
        self.lows: deque = deque(maxlen=period * 2)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None

    def _extract_ohlc(self, price_input) -> tuple:
        """Duck-type extraction of (open, high, low, close) from various inputs.
        See Stochastic._extract_ohlc for supported formats.
        """
        o = h = l = c = None
        try:
            if isinstance(price_input, dict):
                o = price_input.get('open') if 'open' in price_input else price_input.get('o')
                h = price_input.get('high') if 'high' in price_input else price_input.get('h')
                l = price_input.get('low') if 'low' in price_input else price_input.get('l')
                c = price_input.get('close') if 'close' in price_input else price_input.get('c')
            else:
                if hasattr(price_input, 'open'):
                    o = getattr(price_input, 'open')
                elif hasattr(price_input, 'o'):
                    o = getattr(price_input, 'o')
                if hasattr(price_input, 'high'):
                    h = getattr(price_input, 'high')
                elif hasattr(price_input, 'h'):
                    h = getattr(price_input, 'h')
                if hasattr(price_input, 'low'):
                    l = getattr(price_input, 'low')
                elif hasattr(price_input, 'l'):
                    l = getattr(price_input, 'l')
                if hasattr(price_input, 'close'):
                    c = getattr(price_input, 'close')
                elif hasattr(price_input, 'c'):
                    c = getattr(price_input, 'c')
                if c is None and isinstance(price_input, (list, tuple)):
                    if len(price_input) >= 4:
                        o, h, l, c = price_input[0], price_input[1], price_input[2], price_input[3]
                    elif len(price_input) == 3:
                        h, l, c = price_input[0], price_input[1], price_input[2]
        except Exception:
            pass
        return o, h, l, c

    @performance_monitor
    @robust_calculation(default_value=50.0)
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate volume-weighted Williams %R normalized value (0-100) via EWM(norm*vol)/EWM(vol)."""
        if len(self.prices) < 1:
            return 50.0
        
        # Lazy-init alpha and accumulators
        if not hasattr(self, 'alpha'):
            self.alpha = self.config.get_alpha(self.period)
        if not hasattr(self, '_vw_norm_num'):
            self._vw_norm_num = None
            self._vw_norm_den = None
        
        current_close = float(self.prices[-1])
        
        # Track highs and lows using last provided OHLC when available
        if getattr(self, '_last_high', None) is not None and getattr(self, '_last_low', None) is not None:
            self.highs.append(float(self._last_high))
            self.lows.append(float(self._last_low))
        else:
            self.highs.append(current_close)
            self.lows.append(current_close)
        
        if len(self.highs) < self.period:
            return 50.0
        
        highest_high = max(list(self.highs)[-self.period:])
        lowest_low = min(list(self.lows)[-self.period:])
        
        if highest_high == lowest_low:
            self.williams_r_raw = 0.0
        else:
            self.williams_r_raw = ((highest_high - current_close) / (highest_high - lowest_low)) * -100.0
        
        # Normalize to 0..100 for unified handling
        self.williams_r_normalized = float(np.clip(100.0 + self.williams_r_raw, 0.0, 100.0))
        
        # Volume-weighted normalized value via EWM(norm*vol)/EWM(vol)
        vol = float(self.volumes[-1]) if self.volumes else 1.0
        if self._vw_norm_num is None:
            self._vw_norm_num = self.williams_r_normalized * vol
            self._vw_norm_den = vol
        else:
            self._vw_norm_num = (1.0 - self.alpha) * self._vw_norm_num + self.alpha * (self.williams_r_normalized * vol)
            self._vw_norm_den = (1.0 - self.alpha) * self._vw_norm_den + self.alpha * vol
        denom = self._vw_norm_den if self._vw_norm_den is not None else 0.0
        vw_norm = (self._vw_norm_num / denom) if denom > 1e-12 else self.williams_r_normalized
        self.volume_weighted_wr = float(np.clip(vw_norm, 0.0, 100.0))
        
        return self.volume_weighted_wr

    def _generate_enhanced_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Generate Williams %R-specific signal using normalized values."""
        signal_type = SignalType.NEUTRAL
        strength = 0.0
        
        # Primary thresholds (aligned with Stochastic)
        if self.williams_r_normalized <= 20:
            signal_type = SignalType.BUY
            strength = (20 - self.williams_r_normalized) / 20
            if self.williams_r_normalized <= 10:
                signal_type = SignalType.STRONG_BUY
                strength = min(1.0, (20 - self.williams_r_normalized) / 10)
        elif self.williams_r_normalized >= 80:
            signal_type = SignalType.SELL
            strength = (self.williams_r_normalized - 80) / 20
            if self.williams_r_normalized >= 90:
                signal_type = SignalType.STRONG_SELL
                strength = min(1.0, (self.williams_r_normalized - 80) / 10)
        
        # Add 50-cross filter for momentum shift
        if len(self.results) >= 2:
            prev_norm = getattr(self, 'prev_wr_norm', 50.0)
            if prev_norm <= 50 and self.williams_r_normalized > 50 and signal_type == SignalType.NEUTRAL:
                signal_type = SignalType.BUY
                strength = max(strength, 0.4)
            elif prev_norm >= 50 and self.williams_r_normalized < 50 and signal_type == SignalType.NEUTRAL:
                signal_type = SignalType.SELL
                strength = max(strength, 0.4)
        self.prev_wr_norm = self.williams_r_normalized
        
        # Confidence composition
        confidence = 0.5
        if abs(self.williams_r_normalized - 50) > 20:
            confidence += 0.2
        if self.smart_money_metrics.institutional_activity > 0.3:
            confidence += 0.2
        if self.regime_confidence > 0.7:
            confidence += 0.1
        confidence = min(confidence, 1.0)
        
        return IndicatorSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            timestamp=timestamp,
            value=value,
            normalized_value=value / 100.0,
            volume_confirmation=self.smart_money_metrics.institutional_activity > 0.3,
            volume_strength=self.smart_money_metrics.institutional_activity,
            volume_weighted_value=self.volume_weighted_wr,
            market_regime=self.current_regime,
            regime_confidence=self.regime_confidence,
            smart_money_metrics=self.smart_money_metrics,
            risk_metrics=self.risk_metrics,
            metadata={
                'williams_r_components': WilliamsRComponents(
                    williams_r_raw=self.williams_r_raw,
                    williams_r_normalized=self.williams_r_normalized,
                    highest_high=max(list(self.highs)[-self.period:]) if len(self.highs) >= self.period else 0,
                    lowest_low=min(list(self.lows)[-self.period:]) if len(self.lows) >= self.period else 0,
                    volume_weighted_wr=self.volume_weighted_wr
                ),
                'oscillator_analysis': {
                    'overbought': self.williams_r_normalized >= 80,
                    'oversold': self.williams_r_normalized <= 20,
                    'midline_cross': 'bullish' if self.williams_r_normalized > 50 else 'bearish'
                }
            }
        )

    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update Williams %R with enhanced volume confirmation analysis using OHLC-aware close price."""
        timestamp = timestamp or datetime.now()
        
        # Duck-type OHLC extraction; pass close to base update
        o, h, l, c = self._extract_ohlc(price)
        close_val = float(c if c is not None else price)
        self._last_high = float(h) if h is not None else None
        self._last_low = float(l) if l is not None else None
        self._last_close = close_val
        
        # Update volume confirmation analysis using close
        volume_data = self.update_with_volume_confirmation(close_val, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')
        
        # Call parent update method with close price
        result = super().update(close_val, volume, timestamp)
        
        # Enhance result with volume confirmation data
        if self.volume_confirmation_score and result.signal:
            adjusted_strength = self.get_volume_adjusted_signal(
                result.signal.strength,
                self.volume_confirmation_score
            )
            result.signal.strength = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score
            
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
        """Reset Williams %R state"""
        super().reset()
        self.williams_r_raw = -50.0
        self.williams_r_normalized = 50.0
        self.volume_weighted_wr = 50.0
        self.highs.clear()
        self.lows.clear()
        
        # Clear EWM ratio accumulators
        self._vw_norm_num = None
        self._vw_norm_den = None
        
        # Clear last OHLC cache
        self._last_high = None
        self._last_low = None
        self._last_close = None

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

# New factory function for Williams %R

def create_williams_r(period: int = 14, **kwargs) -> WilliamsR:
    """Factory function for creating Williams %R indicator"""
    config = IndicatorConfig(period=period, **kwargs)
    return WilliamsR(period=period, config=config)

# Export all classes and functions
__all__ = [
    # Indicators
    'RSI', 'MACD', 'Stochastic', 'WilliamsR',
    
    # Enums and data classes
    'MomentumState', 'MomentumDirection', 'DivergenceType',
    'MomentumAnalysis', 'RSIComponents', 'MACDComponents', 'StochasticComponents', 'WilliamsRComponents',
    
    # Factory functions
    'create_rsi', 'create_macd', 'create_stochastic', 'create_williams_r'
]

# Add missing momentum indicators: CCI, ROC, PPO, TRIX with similar structure as RSI and MACD

class CCI(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    \"\"\"Commodity Channel Index with Volume Weighting
    
    Features:
    - Measures deviation from average price
    - Volume weighting for institutional analysis
    - Overbought/oversold detection
    \"\"\"
    
    def __init__(self, config: IndicatorConfig, name: str = \"CCI\"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.MOMENTUM
        self.typical_prices = deque(maxlen=config.period)
        self.sma_tp = None
        self.mad = None
        self.cci_value = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        tp = (high + low + close) / 3
        self.typical_prices.append(tp)
        
        if len(self.typical_prices) < self.config.period:
            return None
        
        self.sma_tp = np.mean(self.typical_prices)
        self.mad = np.mean([abs(x - self.sma_tp) for x in self.typical_prices])
        self.cci_value = (tp - self.sma_tp) / (0.015 * self.mad) if self.mad != 0 else 0
        
        signal, confidence = self._generate_cci_signal(self.cci_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.cci_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'sma_tp': self.sma_tp,
                'mad': self.mad
            }
        )
        
        self.results.append(result)
        return result
    
    def _generate_cci_signal(self, cci: float) -> Tuple[SignalType, float]:
        if cci > 100:
            return SignalType.SELL, min(1.0, (cci - 100) / 100)
        elif cci < -100:
            return SignalType.BUY, min(1.0, (-cci - 100) / 100)
        return SignalType.NEUTRAL, 0.0
    
    # Update method similar to others

# Similarly for ROC, PPO, TRIX

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
                    lowest_low=min(list(self.low