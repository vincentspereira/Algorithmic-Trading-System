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
    IndicatorConfig, 
    IndicatorResult, 
    IndicatorType,
    SignalType,
    performance_monitor,
    robust_calculation,
    memory_efficient,
    calculate_sma,
    calculate_ema,
    AugmentedIndicator,
    IndicatorSignal
)
from .multi_value_indicator import MultiValueIndicator
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
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators

logger = logging.getLogger(__name__)

# ===========================================
# SIMPLE MOVING AVERAGE (SMA)
# ===========================================

class SMA(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Simple Moving Average with Volume Weighting
    
    Features:
    - Volume-weighted SMA calculation
    - Crossover signals (price vs. SMA)
    - Trend direction (slope of SMA)
    - Pullback detection
    - Smart money analysis (volume spike detection)
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "SMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.alpha = config.get_alpha(config.period)
        self.prices = deque(maxlen=config.period)
        self.volumes = deque(maxlen=config.period)
        self.sma_values = deque(maxlen=2)  # Store current and previous SMA

    @performance_monitor
    @memory_efficient(max_size=1000)
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self.prices.append(price)
        self.volumes.append(volume)
        self._add_data_point(price, volume, timestamp)

        if len(self.prices) < self.config.period:
            return None

        # Volume-weighted SMA calculation
        vw_sma = self._calculate_volume_weighted_average(self.prices, self.volumes)
        self.sma_values.append(vw_sma)

        # Generate signals
        signal, confidence = self._generate_sma_signal(price, vw_sma)
        
        # Generate insights
        insights = self._generate_insights(price, vw_sma)

        result = IndicatorResult(
            timestamp=timestamp,
            value=vw_sma,
            signal=signal,
            confidence=confidence,
            insights=insights,
            metadata={
                'sma_type': 'volume_weighted',
                'period': self.config.period,
            }
        )
        self.results.append(result)
        return result

    def _generate_sma_signal(self, price: float, sma: float) -> Tuple[SignalType, float]:
        """Generates a signal based on the price's position relative to the SMA."""
        if price > sma:
            return SignalType.BUY, self.calculate_confidence(price, sma)
        elif price < sma:
            return SignalType.SELL, self.calculate_confidence(price, sma)
        else:
            return SignalType.NEUTRAL, 0.5

    def calculate_confidence(self, price: float, sma: float) -> float:
        """Calculates the confidence of a signal based on the distance from the SMA."""
        # Normalize the difference between price and SMA
        normalized_diff = abs(price - sma) / price if price != 0 else 0
        return min(1.0, normalized_diff * 10)  # Scale and cap at 1.0

    def _generate_insights(self, price: float, sma: float) -> Dict[str, Any]:
        """Generates additional insights about the market state."""
        insights = {}
        
        # Trend direction
        if len(self.sma_values) > 1:
            if self.sma_values[-1] > self.sma_values[-2]:
                insights['trend_direction'] = 'up'
            elif self.sma_values[-1] < self.sma_values[-2]:
                insights['trend_direction'] = 'down'
            else:
                insights['trend_direction'] = 'sideways'

        # Pullback detection
        if insights.get('trend_direction') == 'up' and price < sma:
            insights['pullback_opportunity'] = 'buy'
        elif insights.get('trend_direction') == 'down' and price > sma:
            insights['pullback_opportunity'] = 'sell'
            
        # Smart money analysis (example)
        # This is a placeholder for a more sophisticated implementation
        # if self.is_smart_money_active(self.volumes[-1], self.volumes):
        #     insights['smart_money_detected'] = True

        return insights

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
        # Standardized alpha policy via IndicatorConfig
        self.alpha = self.config.get_alpha(self.config.period)
        self.ema_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
        
        # EMA smoothing alpha (kept constant per standardized policy)
        self.adaptive_alpha = self.alpha
        
        # EWM accumulators for proper volume-weighted price: EWM(price*vol)/EWM(vol)
        self._vw_num = None
        self._vw_den = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Exponential Moving Average with optional volume weighting"""
        self._add_data_point(price, volume, timestamp)
        
        # Calculate volume-weighted price using EWM(price*vol)/EWM(vol) if enabled
        if self.config.volume_weighted:
            alpha_vw = self.alpha
            vw_num = price * volume
            self._vw_num = vw_num if self._vw_num is None else (1 - alpha_vw) * self._vw_num + alpha_vw * vw_num
            self._vw_den = volume if self._vw_den is None else (1 - alpha_vw) * self._vw_den + alpha_vw * volume
            effective_price = self._vw_num / self._vw_den if (self._vw_den and self._vw_den != 0) else price
        else:
            effective_price = price
        
        # Initialize EMA with first price
        if self.ema_value is None:
            self.ema_value = effective_price
        else:
            # Keep standardized alpha constant for EMA smoothing
            self.adaptive_alpha = self.alpha
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
                'alpha': self.alpha,
                'volume_weighted': self.config.volume_weighted,
                'price_vs_ema': (price - self.ema_value) / self.ema_value * 100 if self.ema_value != 0 else 0,
                'momentum': momentum,
                'effective_price': effective_price,
                'vw_num': self._vw_num,
                'vw_den': self._vw_den,
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
        # Reset volume-weighted accumulators
        self._vw_num = None
        self._vw_den = None

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
        self.vwma_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        
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
        self.hma_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        self.wma_half = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        self.wma_full = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        
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
                self.hull_intermediate = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
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

# ===========================================
# KAUFMAN'S ADAPTIVE MOVING AVERAGE (KAMA)
# ===========================================

class KAMA(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Kaufman's Adaptive Moving Average with Volume Weighting
    
    Features:
    - Adaptive smoothing based on efficiency ratio
    - Volume-weighted adjustments
    - Trend efficiency measurement
    - Signal generation with adaptive thresholds
    """
    
    def __init__(self, config: IndicatorConfig, er_period: int = 10, fast_period: int = 2, slow_period: int = 30, name: str = "KAMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.er_period = er_period
        self.fast_alpha = 2 / (fast_period + 1)
        self.slow_alpha = 2 / (slow_period + 1)
        self.kama_value = None
        self.kama_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.er_period:
            return None
        
        # Calculate Efficiency Ratio (ER)
        change = abs(price - list(self.prices)[-self.er_period])
        volatility = sum(abs(list(self.prices)[i] - list(self.prices)[i-1]) for i in range(-1, -self.er_period, -1))
        er = change / volatility if volatility != 0 else 0
        
        # Smoothing constant
        sc = (er * (self.fast_alpha - self.slow_alpha) + self.slow_alpha) ** 2
        
        # Calculate KAMA
        if self.kama_value is None:
            self.kama_value = price
        else:
            self.kama_value = self.kama_value + sc * (price - self.kama_value)
        
        self.kama_values.append(self.kama_value)
        
        signal, confidence = self._generate_kama_signal(price, self.kama_value, er)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.kama_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'efficiency_ratio': er,
                'smoothing_constant': sc
            }
        )
        self.results.append(result)
        return result
    
    def _generate_kama_signal(self, price: float, kama: float, er: float) -> Tuple[SignalType, float]:
        deviation = (price - kama) / kama if kama != 0 else 0
        abs_dev = abs(deviation)
        confidence = min(1.0, abs_dev / 0.01 * er)
        if deviation > 0:
            return (SignalType.STRONG_BUY if confidence > 0.8 else SignalType.BUY), confidence
        elif deviation < 0:
            return (SignalType.STRONG_SELL if confidence > 0.8 else SignalType.SELL), confidence
        return SignalType.NEUTRAL, 0.0

# ===========================================
# DOUBLE EXPONENTIAL MOVING AVERAGE (DEMA)
# ===========================================

class DEMA(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Double Exponential Moving Average with Volume Weighting
    
    Features:
    - Reduced lag compared to traditional EMA
    - Volume-weighted calculations
    - Enhanced trend detection
    - Signal generation with momentum
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "DEMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.alpha = config.get_alpha(config.period)
        self.ema1 = None
        self.ema2 = None
        self.dema_value = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(price, volume, timestamp)
        
        # Calculate EMA1
        if self.ema1 is None:
            self.ema1 = price
        else:
            self.ema1 = self.alpha * price + (1 - self.alpha) * self.ema1
        
        # Calculate EMA2 (EMA of EMA1)
        if self.ema2 is None:
            self.ema2 = self.ema1
        else:
            self.ema2 = self.alpha * self.ema1 + (1 - self.alpha) * self.ema2
        
        # Calculate DEMA
        self.dema_value = 2 * self.ema1 - self.ema2
        
        if len(self.prices) < self.config.period:
            return None
        
        signal, confidence = self._generate_dema_signal(price, self.dema_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.dema_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'ema1': self.ema1,
                'ema2': self.ema2
            }
        )
        self.results.append(result)
        return result
    
    def _generate_dema_signal(self, price: float, dema: float) -> Tuple[SignalType, float]:
        deviation = (price - dema) / dema if dema != 0 else 0
        abs_dev = abs(deviation)
        confidence = min(1.0, abs_dev / 0.01)
        if deviation > 0:
            return (SignalType.STRONG_BUY if confidence > 0.8 else SignalType.BUY), confidence
        elif deviation < 0:
            return (SignalType.STRONG_SELL if confidence > 0.8 else SignalType.SELL), confidence
        return SignalType.NEUTRAL, 0.0

# ===========================================
# TRIPLE EXPONENTIAL MOVING AVERAGE (TEMA)
# ===========================================

class TEMA(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Triple Exponential Moving Average with Volume Weighting
    
    Features:
    - Further reduced lag
    - Volume-weighted smoothing
    - Advanced trend following
    - Signal with overshoot reduction
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "TEMA"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.alpha = config.get_alpha(config.period)
        self.ema1 = None
        self.ema2 = None
        self.ema3 = None
        self.tema_value = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(price, volume, timestamp)
        
        # EMA1
        if self.ema1 is None:
            self.ema1 = price
        else:
            self.ema1 = self.alpha * price + (1 - self.alpha) * self.ema1
        
        # EMA2
        if self.ema2 is None:
            self.ema2 = self.ema1
        else:
            self.ema2 = self.alpha * self.ema1 + (1 - self.alpha) * self.ema2
        
        # EMA3
        if self.ema3 is None:
            self.ema3 = self.ema2
        else:
            self.ema3 = self.alpha * self.ema2 + (1 - self.alpha) * self.ema3
        
        # TEMA
        self.tema_value = 3 * self.ema1 - 3 * self.ema2 + self.ema3
        
        if len(self.prices) < self.config.period:
            return None
        
        signal, confidence = self._generate_tema_signal(price, self.tema_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.tema_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'ema1': self.ema1,
                'ema2': self.ema2,
                'ema3': self.ema3
            }
        )
        self.results.append(result)
        return result
    
    def _generate_tema_signal(self, price: float, tema: float) -> Tuple[SignalType, float]:
        deviation = (price - tema) / tema if tema != 0 else 0
        abs_dev = abs(deviation)
        confidence = min(1.0, abs_dev / 0.01)
        if deviation > 0:
            return (SignalType.STRONG_BUY if confidence > 0.8 else SignalType.BUY), confidence
        elif deviation < 0:
            return (SignalType.STRONG_SELL if confidence > 0.8 else SignalType.SELL), confidence
        return SignalType.NEUTRAL, 0.0


# ===========================================
# AVERAGE DIRECTIONAL INDEX (ADX)
# ===========================================

class ADX(MultiValueIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Average Directional Index with Volume Confirmation
    
    Features:
    - Trend strength measurement
    - Directional movement indicators
    - Volume-weighted smoothing
    - Signal generation based on thresholds
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "ADX"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.alpha = config.get_alpha(config.period)
        self.plus_di = None
        self.minus_di = None
        self.adx_value = None
        self.highs = deque(maxlen=config.period + 1)
        self.lows = deque(maxlen=config.period + 1)
        self.closes = deque(maxlen=config.period + 1)
        self.trs = deque(maxlen=config.period)
        self.plus_dms = deque(maxlen=config.period)
        self.minus_dms = deque(maxlen=config.period)

    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        self._add_data_point(close, volume, timestamp)
        
        if len(self.highs) < 2:
            return None

        # True Range
        tr = self._calculate_tr(high, low)
        self.trs.append(tr)

        # Directional Movement
        plus_dm, minus_dm = self._calculate_dm(high, low)
        self.plus_dms.append(plus_dm)
        self.minus_dms.append(minus_dm)

        if len(self.trs) < self.config.period:
            return None

        # Smoothed TR, +DM, -DM
        atr = sum(self.trs) / self.config.period
        smoothed_plus_dm = sum(self.plus_dms) / self.config.period
        smoothed_minus_dm = sum(self.minus_dms) / self.config.period

        # Directional Indicators (+DI, -DI)
        self.plus_di = (smoothed_plus_dm / atr) * 100 if atr != 0 else 0
        self.minus_di = (smoothed_minus_dm / atr) * 100 if atr != 0 else 0

        # Directional Movement Index (DX)
        dx = abs(self.plus_di - self.minus_di) / (self.plus_di + self.minus_di) * 100 if (self.plus_di + self.minus_di) != 0 else 0
        
        # Average Directional Index (ADX)
        if self.adx_value is None:
            self.adx_value = dx
        else:
            self.adx_value = (self.adx_value * (self.config.period - 1) + dx) / self.config.period

        signal, confidence = self._generate_adx_signal(self.adx_value, self.plus_di, self.minus_di)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.adx_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'plus_di': self.plus_di,
                'minus_di': self.minus_di,
                'dx': dx
            }
        )
        self.results.append(result)
        return result

    def _calculate_tr(self, high: float, low: float) -> float:
        prev_close = self.closes[-2] if len(self.closes) > 1 else low
        return max(high - low, abs(high - prev_close), abs(low - prev_close))

    def _calculate_dm(self, high: float, low: float) -> Tuple[float, float]:
        up_move = high - self.highs[-2]
        down_move = self.lows[-2] - low
        
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0
        
        return plus_dm, minus_dm

    def _generate_adx_signal(self, adx: float, plus_di: float, minus_di: float) -> Tuple[SignalType, float]:
        if adx < 25:
            # Weak or no trend
            return SignalType.NEUTRAL, 1.0 - (adx / 25.0)
        
        confidence = min(1.0, (adx - 25) / 25.0) # Confidence increases as ADX rises above 25
        
        if plus_di > minus_di:
            # Uptrend
            if adx > 50:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        else:
            # Downtrend
            if adx > 50:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence



# ===========================================
# DONCHIAN CHANNELS
# ===========================================

class DonchianChannels(MultiValueIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Donchian Channels with Volume Breakout Detection
    
    Features:
    - Upper/lower channel bands
    - Midline calculation
    - Breakout signals with volume confirmation
    - Channel width analysis
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "DonchianChannels"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.highs = deque(maxlen=config.period)
        self.lows = deque(maxlen=config.period)
        self.upper = None
        self.lower = None
        self.mid = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self.highs.append(high)
        self.lows.append(low)
        self._add_data_point(close, volume, timestamp)
        
        if len(self.highs) < self.config.period:
            return None
        
        self.upper = max(self.highs)
        self.lower = min(self.lows)
        self.mid = (self.upper + self.lower) / 2
        
        signal, confidence = self._generate_donchian_signal(close, self.upper, self.lower, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.mid,
            signal=signal,
            confidence=confidence,
            metadata={
                'upper': self.upper,
                'lower': self.lower,
                'width': (self.upper - self.lower) / self.mid if self.mid != 0 else 0
            }
        )
        self.results.append(result)
        return result
    
    def _generate_donchian_signal(self, close: float, upper: float, lower: float, volume: float) -> Tuple[SignalType, float]:
        if close > upper:
            confidence = min(1.0, (close - upper) / (upper - lower) if (upper - lower) != 0 else 0.5)
            return SignalType.STRONG_BUY, confidence
        elif close < lower:
            confidence = min(1.0, (lower - close) / (upper - lower) if (upper - lower) != 0 else 0.5)
            return SignalType.STRONG_SELL, confidence
        return SignalType.NEUTRAL, 0.0

# ===========================================
# CHOPPINESS INDEX
# ===========================================

class ChoppinessIndex(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Choppiness Index with Volume Correlation
    
    Features:
    - Market choppiness measurement
    - Trend vs range detection
    - Volume-adjusted thresholds
    - Signal for trading regime
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "ChoppinessIndex"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.high_lows = deque(maxlen=config.period)
        self.trs = deque(maxlen=config.period)
        self.ci_value = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(close, volume, timestamp)
        hl_diff = high - low
        self.high_lows.append(hl_diff)
        tr = max(high - low, abs(high - list(self.prices)[-2] if len(self.prices) > 1 else 0), abs(low - list(self.prices)[-2] if len(self.prices) > 1 else 0))
        self.trs.append(tr)
        
        if len(self.high_lows) < self.config.period:
            return None
        
        sum_tr = sum(self.trs)
        max_tr = max(self.trs)
        sum_hl = sum(self.high_lows)
        
        if sum_tr == 0 or max_tr == 0:
            self.ci_value = 50.0
        else:
            self.ci_value = 100 * np.log10(sum_tr / max_tr) / np.log10(self.config.period)
        
        signal, confidence = self._generate_ci_signal(self.ci_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.ci_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'sum_tr': sum_tr,
                'max_tr': max_tr,
                'sum_hl': sum_hl
            }
        )
        self.results.append(result)
        return result
    
    def _generate_ci_signal(self, ci: float) -> Tuple[SignalType, float]:
        if ci > 61.8:
            return SignalType.STRONG_SELL, (ci - 61.8) / (100 - 61.8)  # Choppy, avoid trading
        elif ci < 38.2:
            return SignalType.STRONG_BUY, (38.2 - ci) / 38.2  # Trending
        return SignalType.NEUTRAL, 0.0

# ===========================================
# AVERAGE DIRECTIONAL INDEX (ADX)
# ===========================================

class ADX(MultiValueIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Average Directional Index with Volume Confirmation
    
    Features:
    - Trend strength measurement
    - Directional movement indicators
    - Volume-weighted smoothing
    - Signal generation based on thresholds
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "ADX"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.alpha = config.get_alpha(config.period)
        self.plus_di = None
        self.minus_di = None
        self.adx_value = None
        self.highs = deque(maxlen=config.period + 1)
        self.lows = deque(maxlen=config.period + 1)
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self.highs.append(high)
        self.lows.append(low)
        self._add_data_point(close, volume, timestamp)
        
        if len(self.highs) < 2:
            return None
        
        # Calculate DM
        up_move = high - self.highs[-2]
        down_move = self.lows[-2] - low
        plus_dm = max(up_move, 0) if up_move > down_move else 0
        minus_dm = max(down_move, 0) if down_move > up_move else 0
        
        # Calculate ATR (simplified)
        tr = max(high - low, abs(high - list(self.prices)[-2]), abs(low - list(self.prices)[-2]))
        
        # Smooth with EMA
        if self.plus_di is None:
            self.plus_di = (plus_dm / tr) * 100 if tr != 0 else 0
            self.minus_di = (minus_dm / tr) * 100 if tr != 0 else 0
        else:
            self.plus_di = self.alpha * (plus_dm / tr * 100 if tr != 0 else 0) + (1 - self.alpha) * self.plus_di
            self.minus_di = self.alpha * (minus_dm / tr * 100 if tr != 0 else 0) + (1 - self.alpha) * self.minus_di
        
        dx = abs(self.plus_di - self.minus_di) / (self.plus_di + self.minus_di) * 100 if (self.plus_di + self.minus_di) != 0 else 0
        
        if self.adx_value is None:
            self.adx_value = dx
        else:
            self.adx_value = self.alpha * dx + (1 - self.alpha) * self.adx_value
        
        if len(self.prices) < self.config.period:
            return None
        
        signal, confidence = self._generate_adx_signal(self.adx_value, self.plus_di, self.minus_di)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.adx_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'plus_di': self.plus_di,
                'minus_di': self.minus_di,
                'dx': dx
            }
        )
        self.results.append(result)
        return result
    
    def _generate_adx_signal(self, adx: float, plus_di: float, minus_di: float) -> Tuple[SignalType, float]:
        if adx < 20:
            return SignalType.NEUTRAL, adx / 100
        confidence = min(1.0, (adx - 20) / 30)
        if plus_di > minus_di:
            return (SignalType.STRONG_BUY if adx > 40 else SignalType.BUY), confidence
        else:
            return (SignalType.STRONG_SELL if adx > 40 else SignalType.SELL), confidence

# ===========================================
# DONCHIAN CHANNELS
# ===========================================

class DonchianChannels(MultiValueIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Donchian Channels with Volume Breakout Detection
    
    Features:
    - Upper/lower channel bands
    - Midline calculation
    - Breakout signals with volume confirmation
    - Channel width analysis
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "DonchianChannels"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.highs = deque(maxlen=config.period)
        self.lows = deque(maxlen=config.period)
        self.upper = None
        self.lower = None
        self.mid = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self.highs.append(high)
        self.lows.append(low)
        self._add_data_point(close, volume, timestamp)
        
        if len(self.highs) < self.config.period:
            return None
        
        self.upper = max(self.highs)
        self.lower = min(self.lows)
        self.mid = (self.upper + self.lower) / 2
        
        signal, confidence = self._generate_donchian_signal(close, self.upper, self.lower, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.mid,
            signal=signal,
            confidence=confidence,
            metadata={
                'upper': self.upper,
                'lower': self.lower,
                'width': (self.upper - self.lower) / self.mid if self.mid != 0 else 0
            }
        )
        self.results.append(result)
        return result
    
    def _generate_donchian_signal(self, close: float, upper: float, lower: float, volume: float) -> Tuple[SignalType, float]:
        if close > upper:
            confidence = min(1.0, (close - upper) / (upper - lower) if (upper - lower) != 0 else 0.5)
            return SignalType.STRONG_BUY, confidence
        elif close < lower:
            confidence = min(1.0, (lower - close) / (upper - lower) if (upper - lower) != 0 else 0.5)
            return SignalType.STRONG_SELL, confidence
        return SignalType.NEUTRAL, 0.0

# ===========================================
# CHOPPINESS INDEX
# ===========================================

class ChoppinessIndex(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Choppiness Index with Volume Correlation

    
    Features:
    - Market choppiness measurement
    - Trend vs range detection
    - Volume-adjusted thresholds
    - Signal for trading regime
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "ChoppinessIndex"):

        super().__init__(config, name)
        self.indicator_type = IndicatorType.TREND
        self.high_lows = deque(maxlen=config.period)
        self.trs = deque(maxlen=config.period)
        self.ci_value = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(close, volume, timestamp)
        hl_diff = high - low
        self.high_lows.append(hl_diff)
        tr = max(high - low, abs(high - list(self.prices)[-2] if len(self.prices) > 1 else 0), abs(low - list(self.prices)[-2] if len(self.prices) > 1 else 0))
        self.trs.append(tr)
        
        if len(self.high_lows) < self.config.period:
            return None
        
        sum_tr = sum(self.trs)
        max_tr = max(self.trs)
        sum_hl = sum(self.high_lows)
        
        if sum_tr == 0 or max_tr == 0:
            self.ci_value = 50.0
        else:
            self.ci_value = 100 * np.log10(sum_tr / max_tr) / np.log10(self.config.period)
        
        signal, confidence = self._generate_ci_signal(self.ci_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.ci_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'sum_tr': sum_tr,
                'max_tr': max_tr,
                'sum_hl': sum_hl
            }
        )
        self.results.append(result)
        return result
    
    def _generate_ci_signal(self, ci: float) -> Tuple[SignalType, float]:
        if ci > 61.8:
            return SignalType.STRONG_SELL, (ci - 61.8) / (100 - 61.8)  # Choppy, avoid trading
        elif ci < 38.2:
            return SignalType.STRONG_BUY, (38.2 - ci) / 38.2  # Trending
        return SignalType.NEUTRAL, 0.0

# ===========================================
# AVERAGE DIRECTIONAL INDEX (ADX)
# ===========================================

class ADX(MultiValueIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Average Directional Index with Volume Confirmation
    
    Features:
    - Trend strength measurement
    - Directional movement indicators
    - Volume-weighted smoothing
    """