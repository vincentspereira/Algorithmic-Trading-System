"""Consolidated Trend Indicators

This module contains all trend-based technical indicators consolidated from multiple files:
- Simple Moving Average (SMA) with volume weighting
- Exponential Moving Average (EMA) with adaptive features
- Volume Weighted Moving Average (VWMA)
- Hull Moving Average (HMA) with volume integration
- Adaptive Moving Average (AMA) with Kaufman's algorithm
- Linear Regression with volume weighting
- Parabolic SAR with trend detection
- Average Directional Index (ADX) with volume confirmation

All indicators support:
- Volume weighting for institutional analysis
- Adaptive parameters based on market conditions
- Trend strength measurement
- Signal generation with confidence scoring
- Performance optimization for HFT environments

Author: Vincent S. Pereira
Version: 1.0.0 (Consolidated)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Any, Tuple, Union
from datetime import datetime
from collections import deque
from enum import Enum
import logging

from .core_indicator_base import (
    VolumeWeightedIndicator, 
    MultiValueIndicator,
    AdaptiveIndicator,
    IndicatorConfig, 
    IndicatorResult, 
    IndicatorType,
    SignalType,
    performance_monitor,
    robust_calculation,
    memory_efficient,
    calculate_sma,
    calculate_ema
)
from .volume_confirmation import (
    VolumeConfirmationEngine,
    VolumeConfirmationMixin,
    VolumeConfirmationScore,
    VolumeAnalysis,
    VolumeRegime,
    VolumeQuality,
    OrderFlowBias
)
from .smart_money_analysis import (
    SmartMoneyAnalysisEngine,
    SmartMoneyMixin,
    SmartMoneyMetrics,
    SmartMoneyBias,
    InstitutionalActivity
)

logger = logging.getLogger(__name__)

# ===========================================
# SIMPLE MOVING AVERAGE (SMA)
# ===========================================

class SMA(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Simple Moving Average with Volume Weighting
    
    Features:
    - Traditional SMA calculation
    - Volume-weighted SMA for institutional analysis
    - Trend direction detection
    - Signal generation based on price vs SMA
    - Adaptive smoothing based on volatility
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "SMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        
        # SMA calculation components
        self.sma_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
        
        # Smart money analysis integration
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
        self.institutional_bias: Optional[SmartMoneyBias] = None
        self.institutional_activity: Optional[InstitutionalActivity] = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Simple Moving Average with optional volume weighting"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get window data
        window_prices = list(self.prices)[-self.config.period:]
        window_volumes = list(self.volumes)[-self.config.period:]
        
        # Calculate SMA
        if self.config.volume_weighted and sum(window_volumes) > 0:
            # Volume-weighted SMA
            sma_value = self._calculate_volume_weighted_average(window_prices, window_volumes)
        else:
            # Traditional SMA
            sma_value = np.mean(window_prices)
        
        self.sma_values.append(sma_value)
        
        # Generate signal based on price vs SMA
        signal, confidence = self._generate_sma_signal(price, sma_value)
        
        # Calculate trend strength
        trend_strength = self._calculate_trend_strength()
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=sma_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'volume_weighted': self.config.volume_weighted,
                'price_vs_sma': (price - sma_value) / sma_value * 100 if sma_value != 0 else 0,
                'trend_strength': trend_strength,
                'current_price': price,
                'volume_ratio': volume / np.mean(window_volumes) if np.mean(window_volumes) > 0 else 1.0
            }
        )
        
        self.results.append(result)
        return result
    
    def _generate_sma_signal(self, price: float, sma: float) -> Tuple[SignalType, float]:
        """Generate signal based on price position relative to SMA"""
        if sma == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (price - sma) / sma
        abs_deviation = abs(price_deviation)
        
        # Generate signal based on deviation
        if abs_deviation < self.config.signal_threshold:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, abs_deviation / 0.02)  # 2% deviation = full confidence
        
        if price_deviation > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        else:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
    
    def _calculate_trend_strength(self) -> float:
        """Calculate trend strength based on SMA slope"""
        if len(self.sma_values) < 5:
            return 0.0
        
        recent_sma = list(self.sma_values)[-5:]
        x = np.arange(len(recent_sma))
        slope, _ = np.polyfit(x, recent_sma, 1)
        
        # Normalize slope by average SMA value
        avg_sma = np.mean(recent_sma)
        if avg_sma == 0:
            return 0.0
        
        normalized_slope = slope / avg_sma
        return min(1.0, abs(normalized_slope) * 100)  # Scale to 0-1
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update SMA with enhanced volume confirmation analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update volume confirmation analysis
        volume_data = self.update_with_volume_confirmation(price, volume, timestamp)
        self.volume_confirmation_score = volume_data.get('volume_confirmation')
        self.volume_analysis = volume_data.get('volume_analysis')
        
        # Call parent calculate method
        result = self.calculate(price, volume, timestamp)
        
        # Enhance result with volume confirmation data if available
        if result and self.volume_confirmation_score and result.signal:
            # Adjust signal strength based on volume confirmation
            adjusted_strength = self.get_volume_adjusted_signal(
                result.confidence, 
                self.volume_confirmation_score
            )
            
            # Update result with volume-adjusted confidence
            result.confidence = adjusted_strength
            result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
            result.signal.volume_strength = self.volume_confirmation_score.overall_score
            
            # Add volume analysis to metadata
            if 'volume_confirmation_details' not in result.metadata:
                result.metadata['volume_confirmation_details'] = {}
            
            result.metadata['volume_confirmation_details'].update({
                'confirmation_score': self.volume_confirmation_score.overall_score,
                'price_volume_sync': self.volume_confirmation_score.price_volume_sync,
                'volume_breakout': self.volume_confirmation_score.volume_breakout,
                'institutional_presence': self.volume_confirmation_score.institutional_presence,
                'volume_quality': self.volume_confirmation_score.volume_quality,
                'confidence': self.volume_confirmation_score.confidence
            })
            
            if self.volume_analysis:
                result.metadata['volume_confirmation_details'].update({
                    'volume_regime': self.volume_analysis.volume_regime.value,
                    'volume_quality_rating': self.volume_analysis.volume_quality.value,
                    'order_flow_bias': self.volume_analysis.order_flow_bias.value,
                    'institutional_activity': self.volume_analysis.institutional_activity,
                    'relative_volume': self.volume_analysis.relative_volume,
                    'smart_money_flow': self.volume_analysis.smart_money_flow
                })
        
        return result
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.sma_values.clear()

# ===========================================
# EXPONENTIAL MOVING AVERAGE (EMA)
# ===========================================

class EMA(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Exponential Moving Average with Volume Weighting
    
    Features:
    - Traditional EMA calculation with exponential smoothing
    - Volume-weighted EMA for institutional analysis
    - Adaptive alpha based on volatility
    - Trend direction and momentum detection
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "EMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        
        # EMA calculation components
        self.ema_value = None
        self.alpha = 2.0 / (config.period + 1)
        self.ema_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
        
        # Adaptive alpha for volume weighting
        self.adaptive_alpha = self.alpha
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Exponential Moving Average with optional volume weighting"""
        self._add_data_point(price, volume, timestamp)
        
        # Calculate volume-weighted price if enabled
        if self.config.volume_weighted:
            effective_price = self._calculate_volume_weighted_price(price, volume)
        else:
            effective_price = price
        
        # Initialize EMA with first price
        if self.ema_value is None:
            self.ema_value = effective_price
        else:
            # Update adaptive alpha if volume weighting is enabled
            if self.config.volume_weighted:
                self.adaptive_alpha = self._calculate_adaptive_alpha(volume)
            
            # Calculate EMA
            self.ema_value = self.adaptive_alpha * effective_price + (1 - self.adaptive_alpha) * self.ema_value
        
        self.ema_values.append(self.ema_value)
        
        # Generate signal
        signal, confidence = self._generate_ema_signal(price, self.ema_value)
        
        # Calculate momentum
        momentum = self._calculate_ema_momentum()
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.ema_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'alpha': self.adaptive_alpha,
                'volume_weighted': self.config.volume_weighted,
                'price_vs_ema': (price - self.ema_value) / self.ema_value * 100 if self.ema_value != 0 else 0,
                'momentum': momentum,
                'effective_price': effective_price
            }
        )
        
        self.results.append(result)
        return result
    
    def _calculate_volume_weighted_price(self, price: float, volume: float) -> float:
        """Calculate volume-weighted price for EMA calculation"""
        if len(self.volumes) < 3:
            return price
        
        # Use recent volume data to weight current price
        recent_volumes = list(self.volumes)[-3:]
        avg_volume = np.mean(recent_volumes)
        
        if avg_volume == 0:
            return price
        
        volume_weight = min(2.0, max(0.5, volume / avg_volume))
        return price * volume_weight
    
    def _calculate_adaptive_alpha(self, volume: float) -> float:
        """Calculate adaptive alpha based on volume"""
        if len(self.volumes) < 5:
            return self.alpha
        
        # Calculate volume ratio
        recent_volumes = list(self.volumes)[-5:]
        avg_volume = np.mean(recent_volumes)
        
        if avg_volume == 0:
            return self.alpha
        
        volume_ratio = volume / avg_volume
        
        # Adjust alpha based on volume (higher volume = more responsive)
        alpha_multiplier = min(2.0, max(0.5, volume_ratio))
        return min(1.0, self.alpha * alpha_multiplier)
    
    def _generate_ema_signal(self, price: float, ema: float) -> Tuple[SignalType, float]:
        """Generate signal based on price position relative to EMA"""
        if ema == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (price - ema) / ema
        abs_deviation = abs(price_deviation)
        
        if abs_deviation < self.config.signal_threshold:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, abs_deviation / 0.015)  # 1.5% deviation = full confidence
        
        # Consider EMA momentum for signal strength
        momentum = self._calculate_ema_momentum()
        confidence *= (0.7 + 0.3 * abs(momentum))
        
        if price_deviation > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        else:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
    
    def _calculate_ema_momentum(self) -> float:
        """Calculate EMA momentum (rate of change)"""
        if len(self.ema_values) < 3:
            return 0.0
        
        recent_ema = list(self.ema_values)[-3:]
        if len(recent_ema) < 2:
            return 0.0
        
        momentum = (recent_ema[-1] - recent_ema[0]) / recent_ema[0] if recent_ema[0] != 0 else 0.0
        return max(-1.0, min(1.0, momentum * 100))  # Scale and clamp to [-1, 1]
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.ema_value = None
        self.adaptive_alpha = self.alpha
        self.ema_values.clear()

# ===========================================
# VOLUME WEIGHTED MOVING AVERAGE (VWMA)
# ===========================================

class VWMA(VolumeWeightedIndicator):
    """Volume Weighted Moving Average
    
    Features:
    - Pure volume-weighted moving average calculation
    - Institutional money flow detection
    - Smart money analysis
    - Volume-based signal generation
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "VWMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        
        # VWMA calculation components
        self.vwma_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume Weighted Moving Average"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get window data
        window_prices = list(self.prices)[-self.config.period:]
        window_volumes = list(self.volumes)[-self.config.period:]
        
        # Calculate VWMA
        total_volume = sum(window_volumes)
        if total_volume == 0:
            vwma_value = np.mean(window_prices)
        else:
            vwma_value = sum(p * v for p, v in zip(window_prices, window_volumes)) / total_volume
        
        self.vwma_values.append(vwma_value)
        
        # Generate signal
        signal, confidence = self._generate_vwma_signal(price, vwma_value, volume)
        
        # Calculate volume metrics
        volume_strength = self._calculate_volume_strength(volume)
        smart_money_score = self._calculate_smart_money_score(volume, price, vwma_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=vwma_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'total_volume': total_volume,
                'avg_volume': total_volume / self.config.period,
                'volume_strength': volume_strength,
                'smart_money_score': smart_money_score,
                'price_vs_vwma': (price - vwma_value) / vwma_value * 100 if vwma_value != 0 else 0
            }
        )
        
        self.results.append(result)
        return result
    
    def _generate_vwma_signal(self, price: float, vwma: float, volume: float) -> Tuple[SignalType, float]:
        """Generate signal based on price vs VWMA with volume confirmation"""
        if vwma == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (price - vwma) / vwma
        abs_deviation = abs(price_deviation)
        
        if abs_deviation < self.config.signal_threshold:
            return SignalType.NEUTRAL, 0.0
        
        # Base confidence from price deviation
        confidence = min(1.0, abs_deviation / 0.02)
        
        # Enhance confidence with volume strength
        volume_strength = self._calculate_volume_strength(volume)
        confidence *= (0.6 + 0.4 * volume_strength)
        
        if price_deviation > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        else:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
    
    def _calculate_volume_strength(self, current_volume: float) -> float:
        """Calculate volume strength relative to recent average"""
        if len(self.volumes) < 5:
            return 0.5
        
        recent_volumes = list(self.volumes)[-5:]
        avg_volume = np.mean(recent_volumes)
        
        if avg_volume == 0:
            return 0.5
        
        volume_ratio = current_volume / avg_volume
        return min(1.0, max(0.0, (volume_ratio - 0.5) / 2.0))  # Scale to 0-1
    
    def _calculate_smart_money_score(self, volume: float, price: float, vwma: float) -> float:
        """Calculate smart money involvement score"""
        if len(self.volumes) < 10 or vwma == 0:
            return 0.0
        
        # High volume with price moving away from VWMA suggests smart money
        volume_strength = self._calculate_volume_strength(volume)
        price_momentum = abs((price - vwma) / vwma)
        
        return min(1.0, volume_strength * price_momentum * 2.0)
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.vwma_values.clear()

# ===========================================
# HULL MOVING AVERAGE (HMA)
# ===========================================

class HMA(VolumeWeightedIndicator):
    """Hull Moving Average with Volume Integration
    
    Features:
    - Hull Moving Average calculation for reduced lag
    - Volume weighting integration
    - Trend direction detection with minimal lag
    - Adaptive smoothing based on market conditions
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "HMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        
        # HMA calculation components
        self.hma_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        self.wma_half = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        self.wma_full = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Hull Moving Average"""
        self._add_data_point(price, volume, timestamp)
        
        half_period = max(1, self.config.period // 2)
        sqrt_period = max(1, int(np.sqrt(self.config.period)))
        
        if len(self.prices) < self.config.period:
            return None
        
        # Calculate WMA for half period and full period
        window_prices = list(self.prices)[-self.config.period:]
        window_volumes = list(self.volumes)[-self.config.period:]
        
        # WMA for half period
        if len(window_prices) >= half_period:
            wma_half_value = self._calculate_wma(window_prices[-half_period:], 
                                               window_volumes[-half_period:] if self.config.volume_weighted else None)
            self.wma_half.append(wma_half_value)
        
        # WMA for full period
        wma_full_value = self._calculate_wma(window_prices, 
                                           window_volumes if self.config.volume_weighted else None)
        self.wma_full.append(wma_full_value)
        
        # Calculate Hull MA intermediate value
        if len(self.wma_half) > 0:
            hull_intermediate = 2 * self.wma_half[-1] - self.wma_full[-1]
            
            # Store intermediate values for final HMA calculation
            if not hasattr(self, 'hull_intermediate'):
                self.hull_intermediate = deque(maxlen=config.max_memory_items if config.hft_mode else None)
            self.hull_intermediate.append(hull_intermediate)
            
            # Calculate final HMA using WMA of intermediate values
            if len(self.hull_intermediate) >= sqrt_period:
                recent_intermediate = list(self.hull_intermediate)[-sqrt_period:]
                hma_value = self._calculate_wma(recent_intermediate, None)  # No volume weighting for final step
                
                self.hma_values.append(hma_value)
                
                # Generate signal
                signal, confidence = self._generate_hma_signal(price, hma_value)
                
                result = IndicatorResult(
                    timestamp=timestamp,
                    value=hma_value,
                    signal=signal,
                    confidence=confidence,
                    metadata={
                        'period': self.config.period,
                        'half_period': half_period,
                        'sqrt_period': sqrt_period,
                        'volume_weighted': self.config.volume_weighted,
                        'wma_half': self.wma_half[-1] if self.wma_half else None,
                        'wma_full': self.wma_full[-1],
                        'hull_intermediate': hull_intermediate
                    }
                )
                
                self.results.append(result)
                return result
        
        return None
    
    def _calculate_wma(self, prices: List[float], volumes: List[float] = None) -> float:
        """Calculate Weighted Moving Average"""
        if not prices:
            return 0.0
        
        n = len(prices)
        weights = np.arange(1, n + 1)
        
        if volumes and self.config.volume_weighted:
            # Combine linear weights with volume weights
            volume_weights = np.array(volumes)
            combined_weights = weights * volume_weights
            if np.sum(combined_weights) == 0:
                return np.mean(prices)
            return np.sum(np.array(prices) * combined_weights) / np.sum(combined_weights)
        else:
            # Standard WMA
            return np.sum(np.array(prices) * weights) / np.sum(weights)
    
    def _generate_hma_signal(self, price: float, hma: float) -> Tuple[SignalType, float]:
        """Generate signal based on price vs HMA and HMA slope"""
        if hma == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (price - hma) / hma
        abs_deviation = abs(price_deviation)
        
        # Calculate HMA slope for trend confirmation
        hma_slope = self._calculate_hma_slope()
        
        if abs_deviation < self.config.signal_threshold:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, abs_deviation / 0.015)
        
        # Enhance confidence with trend confirmation
        if (price_deviation > 0 and hma_slope > 0) or (price_deviation < 0 and hma_slope < 0):
            confidence *= 1.2  # Trend confirmation
        
        confidence = min(1.0, confidence)
        
        if price_deviation > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        else:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
    
    def _calculate_hma_slope(self) -> float:
        """Calculate HMA slope for trend direction"""
        if len(self.hma_values) < 3:
            return 0.0
        
        recent_hma = list(self.hma_values)[-3:]
        if len(recent_hma) < 2:
            return 0.0
        
        slope = (recent_hma[-1] - recent_hma[0]) / len(recent_hma)
        return slope / recent_hma[-1] if recent_hma[-1] != 0 else 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.hma_values.clear()
        self.wma_half.clear()
        self.wma_full.clear()
        if hasattr(self, 'hull_intermediate'):
            self.hull_intermediate.clear()

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_sma(period: int = 20, volume_weighted: bool = False, **kwargs) -> SMA:
    """Create SMA indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return SMA(config)

def create_ema(period: int = 20, volume_weighted: bool = False, **kwargs) -> EMA:
    """Create EMA indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return EMA(config)

def create_vwma(period: int = 20, **kwargs) -> VWMA:
    """Create VWMA indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=True,  # VWMA is always volume weighted
        **kwargs
    )
    return VWMA(config)

def create_hma(period: int = 20, volume_weighted: bool = False, **kwargs) -> HMA:
    """Create HMA indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return HMA(config)

# Export all indicators
__all__ = [
    'SMA',
    'EMA',
    'VWMA', 
    'HMA',
    'create_sma',
    'create_ema',
    'create_vwma',
    'create_hma'
]