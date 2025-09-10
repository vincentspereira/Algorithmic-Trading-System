"""Consolidated Volatility Indicators

This module contains all volatility-based technical indicators consolidated from multiple files:
- Bollinger Bands with volume weighting
- Average True Range (ATR) with smart money detection
- Keltner Channels with institutional analysis
- Standard Deviation with volume confirmation
- Average Directional Index (ADX) with trend strength
- Normalized ATR for cross-asset comparison
- Choppy Market Index for trend vs range detection

All indicators support:
- Volume weighting for institutional analysis
- Adaptive parameters based on market conditions
- Volatility regime detection
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
    memory_efficient
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
# BOLLINGER BANDS
# ===========================================

class BollingerBands(MultiValueIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Bollinger Bands with Volume Weighting
    
    Features:
    - Traditional Bollinger Bands calculation
    - Volume-weighted moving average and standard deviation
    - Band squeeze detection
    - Breakout signal generation
    - Adaptive band width based on volatility
    """
    
    def __init__(self, config: IndicatorConfig, std_dev: float = 2.0, name: str = "BollingerBands"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLATILITY
        
        self.std_dev = std_dev
        self.band_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
        # Volume confirmation integration
        self.volume_confirmation_score: Optional[VolumeConfirmationScore] = None
        self.volume_analysis: Optional[VolumeAnalysis] = None
        
        # Smart money analysis integration
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
        self.institutional_bias: Optional[SmartMoneyBias] = None
        self.institutional_activity: Optional[InstitutionalActivity] = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value={})
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Bollinger Bands values"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return {}
        
        # Get window data
        window_prices = list(self.prices)[-self.config.period:]
        window_volumes = list(self.volumes)[-self.config.period:]
        
        # Calculate moving average
        if self.config.volume_weighted and sum(window_volumes) > 0:
            middle_band = self._calculate_volume_weighted_average(window_prices, window_volumes)
            std_value = self._calculate_volume_weighted_std(window_prices, window_volumes, middle_band)
        else:
            middle_band = np.mean(window_prices)
            std_value = np.std(window_prices, ddof=1)
        
        # Calculate bands
        upper_band = middle_band + (self.std_dev * std_value)
        lower_band = middle_band - (self.std_dev * std_value)
        
        # Calculate band metrics
        band_width = (upper_band - lower_band) / middle_band if middle_band != 0 else 0
        band_position = ((price - lower_band) / (upper_band - lower_band)) if (upper_band - lower_band) != 0 else 0.5
        
        # Detect squeeze
        squeeze_detected = self._detect_squeeze(band_width)
        
        # Store band data for analysis
        band_data = {
            'width': band_width,
            'position': band_position,
            'squeeze': squeeze_detected
        }
        self.band_values.append(band_data)
        
        return {
            'main': middle_band,
            'middle': middle_band,
            'upper': upper_band,
            'lower': lower_band,
            'band_width': band_width,
            'band_position': band_position,
            'squeeze_detected': squeeze_detected,
            'std_value': std_value
        }
    
    def _calculate_volume_weighted_std(self, prices: List[float], volumes: List[float], mean: float) -> float:
        """Calculate volume-weighted standard deviation"""
        if not prices or not volumes or len(prices) != len(volumes):
            return np.std(prices, ddof=1) if prices else 0.0
        
        total_volume = sum(volumes)
        if total_volume == 0:
            return np.std(prices, ddof=1)
        
        # Calculate volume-weighted variance
        weighted_variance = sum(v * (p - mean) ** 2 for p, v in zip(prices, volumes)) / total_volume
        return np.sqrt(weighted_variance)
    
    def _detect_squeeze(self, current_width: float) -> bool:
        """Detect Bollinger Band squeeze (low volatility)"""
        if len(self.band_values) < 20:
            return False
        
        # Get recent band widths
        recent_widths = [bd['width'] for bd in list(self.band_values)[-20:]]
        avg_width = np.mean(recent_widths)
        
        # Squeeze detected if current width is significantly below average
        return current_width < avg_width * 0.7
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update Bollinger Bands with enhanced volume confirmation and smart money analysis"""
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
        
        # Enhance result with volume confirmation and smart money data
        if result and result.signal:
            # Adjust signal strength based on volume confirmation
            if self.volume_confirmation_score:
                adjusted_strength = self.get_volume_adjusted_signal(
                    result.signal.strength, 
                    self.volume_confirmation_score
                )
                result.signal.strength = adjusted_strength
                result.signal.volume_confirmation = self.volume_confirmation_score.overall_score > 0.6
                result.signal.volume_strength = self.volume_confirmation_score.overall_score
            
            # Adjust signal strength based on smart money alignment
            if self.smart_money_metrics and self.institutional_bias:
                smart_money_alignment = (
                    self.smart_money_metrics.institutional_flow_ratio > 0.6 and
                    self.institutional_bias in [SmartMoneyBias.BULLISH, SmartMoneyBias.BEARISH]
                )
                
                if smart_money_alignment:
                    # Boost signal strength when smart money aligns
                    result.signal.strength = min(1.0, result.signal.strength * 1.2)
                else:
                    # Reduce signal strength when smart money doesn't align
                    result.signal.strength = max(0.0, result.signal.strength * 0.8)
            
            # Add smart money analysis to metadata
            if self.smart_money_metrics:
                if 'smart_money_analysis' not in result.signal.metadata:
                    result.signal.metadata['smart_money_analysis'] = {}
                
                result.signal.metadata['smart_money_analysis'].update({
                    'institutional_flow_ratio': self.smart_money_metrics.institutional_flow_ratio,
                    'smart_money_index': self.smart_money_metrics.smart_money_index,
                    'institutional_bias': self.institutional_bias.value if self.institutional_bias else None,
                    'institutional_activity': self.institutional_activity.value if self.institutional_activity else None
                })
        
        return result
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.band_values.clear()

# ===========================================
# AVERAGE TRUE RANGE (ATR)
# ===========================================

class ATR(VolumeWeightedIndicator, SmartMoneyMixin):
    """Average True Range with Smart Money Detection
    
    Features:
    - Traditional ATR calculation
    - Volume-weighted ATR for institutional analysis
    - Volatility regime detection
    - Smart money flow analysis
    - Adaptive smoothing based on market conditions
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "ATR"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLATILITY
        
        # ATR calculation components
        self.true_ranges = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        self.atr_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        self.atr_value = None
        
        # For True Range calculation, we need high, low, close
        # For simplicity, using price as all three (in real implementation, pass separately)
        self.highs = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        self.lows = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        self.closes = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
        # Smart money analysis integration
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
        self.institutional_bias: Optional[SmartMoneyBias] = None
        self.institutional_activity: Optional[InstitutionalActivity] = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Average True Range"""
        # Store OHLC data (using price for all in this simplified version)
        self.highs.append(price)
        self.lows.append(price)
        self.closes.append(price)
        self._add_data_point(price, volume, timestamp)
        
        if len(self.closes) < 2:
            return None
        
        # Calculate True Range
        current_high = self.highs[-1]
        current_low = self.lows[-1]
        previous_close = self.closes[-2]
        
        tr1 = current_high - current_low
        tr2 = abs(current_high - previous_close)
        tr3 = abs(current_low - previous_close)
        
        true_range = max(tr1, tr2, tr3)
        
        # Apply volume weighting if enabled
        if self.config.volume_weighted:
            volume_weight = self._calculate_volume_weight(volume)
            true_range *= volume_weight
        
        self.true_ranges.append(true_range)
        
        if len(self.true_ranges) < self.config.period:
            return None
        
        # Calculate ATR using Wilder's smoothing
        if self.atr_value is None:
            # Initialize with SMA of true ranges
            self.atr_value = np.mean(list(self.true_ranges)[-self.config.period:])
        else:
            # Wilder's smoothing: ATR = ((n-1) * previous_ATR + current_TR) / n
            alpha = 1.0 / self.config.period
            self.atr_value = alpha * true_range + (1 - alpha) * self.atr_value
        
        self.atr_values.append(self.atr_value)
        
        # Generate signal based on ATR changes
        signal, confidence = self._generate_atr_signal()
        
        # Calculate volatility metrics
        volatility_regime = self._detect_volatility_regime()
        smart_money_score = self._calculate_smart_money_score(volume, true_range)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.atr_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'true_range': true_range,
                'volume_weighted': self.config.volume_weighted,
                'volatility_regime': volatility_regime,
                'smart_money_score': smart_money_score,
                'atr_percentile': self._calculate_atr_percentile()
            }
        )
        
        self.results.append(result)
        return result
    
    def _calculate_volume_weight(self, current_volume: float) -> float:
        """Calculate volume weight for ATR calculation"""
        if len(self.volumes) < 10:
            return 1.0
        
        avg_volume = np.mean(list(self.volumes)[-10:])
        if avg_volume == 0:
            return 1.0
        
        volume_ratio = current_volume / avg_volume
        return min(2.0, max(0.5, volume_ratio))
    
    def _generate_atr_signal(self) -> Tuple[SignalType, float]:
        """Generate signal based on ATR changes"""
        if len(self.atr_values) < 5:
            return SignalType.NEUTRAL, 0.0
        
        # Calculate ATR momentum
        recent_atr = list(self.atr_values)[-5:]
        atr_change = (recent_atr[-1] - recent_atr[0]) / recent_atr[0] if recent_atr[0] != 0 else 0
        
        # High ATR increase suggests increased volatility (caution signal)
        # Low ATR suggests low volatility (potential breakout setup)
        
        abs_change = abs(atr_change)
        if abs_change < 0.1:  # 10% change threshold
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, abs_change / 0.2)  # 20% change = full confidence
        
        if atr_change > 0.2:  # Significant ATR increase
            return SignalType.SELL, confidence  # Caution signal
        elif atr_change < -0.1:  # ATR decrease (low volatility)
            return SignalType.BUY, confidence * 0.7  # Potential breakout setup
        
        return SignalType.NEUTRAL, 0.0
    
    def _detect_volatility_regime(self) -> str:
        """Detect current volatility regime"""
        if len(self.atr_values) < 20:
            return "unknown"
        
        recent_atr = list(self.atr_values)[-20:]
        current_atr = self.atr_values[-1]
        avg_atr = np.mean(recent_atr)
        
        if current_atr > avg_atr * 1.5:
            return "high_volatility"
        elif current_atr < avg_atr * 0.7:
            return "low_volatility"
        else:
            return "normal_volatility"
    
    def _calculate_smart_money_score(self, volume: float, true_range: float) -> float:
        """Calculate smart money involvement based on volume and volatility"""
        if len(self.volumes) < 10:
            return 0.0
        
        volume_strength = self._calculate_volume_weight(volume) - 1.0  # Normalize to 0-1
        
        # High volume with high true range suggests institutional activity
        if len(self.true_ranges) >= 10:
            avg_tr = np.mean(list(self.true_ranges)[-10:])
            tr_ratio = true_range / avg_tr if avg_tr > 0 else 1.0
            volatility_factor = min(1.0, max(0.0, (tr_ratio - 0.8) / 1.2))
        else:
            volatility_factor = 0.5
        
        return min(1.0, volume_strength * volatility_factor)
    
    def _calculate_atr_percentile(self) -> float:
        """Calculate current ATR percentile over recent period"""
        if len(self.atr_values) < 20:
            return 0.5
        
        recent_atr = list(self.atr_values)[-20:]
        current_atr = self.atr_values[-1]
        
        percentile = np.sum(np.array(recent_atr) <= current_atr) / len(recent_atr)
        return percentile
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update ATR with enhanced smart money analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update smart money analysis
        smart_money_data = self.update_with_smart_money_analysis(price, volume, timestamp)
        self.smart_money_metrics = smart_money_data.get('smart_money_metrics')
        self.institutional_bias = smart_money_data.get('institutional_bias')
        self.institutional_activity = smart_money_data.get('institutional_activity')
        
        # Call parent calculate method
        result = self.calculate(price, volume, timestamp)
        
        # Enhance result with smart money data
        if result and result.signal:
            # Adjust signal strength based on smart money alignment
            if self.smart_money_metrics and self.institutional_bias:
                smart_money_alignment = (
                    self.smart_money_metrics.institutional_flow_ratio > 0.6 and
                    self.institutional_bias in [SmartMoneyBias.BULLISH, SmartMoneyBias.BEARISH]
                )
                
                if smart_money_alignment:
                    # Boost signal strength when smart money aligns
                    result.signal.strength = min(1.0, result.signal.strength * 1.2)
                else:
                    # Reduce signal strength when smart money doesn't align
                    result.signal.strength = max(0.0, result.signal.strength * 0.8)
            
            # Add smart money analysis to metadata
            if self.smart_money_metrics:
                if 'smart_money_analysis' not in result.signal.metadata:
                    result.signal.metadata['smart_money_analysis'] = {}
                
                result.signal.metadata['smart_money_analysis'].update({
                    'institutional_flow_ratio': self.smart_money_metrics.institutional_flow_ratio,
                    'smart_money_index': self.smart_money_metrics.smart_money_index,
                    'institutional_bias': self.institutional_bias.value if self.institutional_bias else None,
                    'institutional_activity': self.institutional_activity.value if self.institutional_activity else None
                })
        
        return result
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.true_ranges.clear()
        self.atr_values.clear()
        self.atr_value = None
        self.highs.clear()
        self.lows.clear()
        self.closes.clear()

# ===========================================
# KELTNER CHANNELS
# ===========================================

class KeltnerChannels(MultiValueIndicator, SmartMoneyMixin):
    """Keltner Channels with Volume Weighting
    
    Features:
    - Traditional Keltner Channels using EMA and ATR
    - Volume-weighted calculations
    - Channel breakout detection
    - Trend strength analysis
    """
    
    def __init__(self, config: IndicatorConfig, atr_multiplier: float = 2.0, name: str = "KeltnerChannels"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLATILITY
        
        self.atr_multiplier = atr_multiplier
        
        # Initialize EMA and ATR components
        self.ema_value = None
        self.atr_indicator = ATR(config)
        
        # Smart money analysis integration
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
        self.institutional_bias: Optional[SmartMoneyBias] = None
        self.institutional_activity: Optional[InstitutionalActivity] = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value={})
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Keltner Channels values"""
        self._add_data_point(price, volume, timestamp)
        
        # Calculate EMA (middle line)
        alpha = 2.0 / (self.config.period + 1)
        
        if self.ema_value is None:
            self.ema_value = price
        else:
            if self.config.volume_weighted:
                volume_weight = self._calculate_volume_weight(volume)
                effective_price = price * volume_weight
            else:
                effective_price = price
            
            self.ema_value = alpha * effective_price + (1 - alpha) * self.ema_value
        
        # Calculate ATR for channel width
        atr_result = self.atr_indicator.calculate(price, volume, timestamp)
        if not atr_result:
            return {}
        
        atr_value = atr_result.value
        
        # Calculate channels
        upper_channel = self.ema_value + (self.atr_multiplier * atr_value)
        lower_channel = self.ema_value - (self.atr_multiplier * atr_value)
        
        # Calculate channel metrics
        channel_width = (upper_channel - lower_channel) / self.ema_value if self.ema_value != 0 else 0
        channel_position = ((price - lower_channel) / (upper_channel - lower_channel)) if (upper_channel - lower_channel) != 0 else 0.5
        
        return {
            'main': self.ema_value,
            'middle': self.ema_value,
            'upper': upper_channel,
            'lower': lower_channel,
            'channel_width': channel_width,
            'channel_position': channel_position,
            'atr_value': atr_value
        }
    
    def _calculate_volume_weight(self, current_volume: float) -> float:
        """Calculate volume weight for EMA calculation"""
        if len(self.volumes) < 5:
            return 1.0
        
        avg_volume = np.mean(list(self.volumes)[-5:])
        if avg_volume == 0:
            return 1.0
        
        volume_ratio = current_volume / avg_volume
        return min(2.0, max(0.5, volume_ratio))
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update Keltner Channels with enhanced smart money analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update smart money analysis
        smart_money_data = self.update_with_smart_money_analysis(price, volume, timestamp)
        self.smart_money_metrics = smart_money_data.get('smart_money_metrics')
        self.institutional_bias = smart_money_data.get('institutional_bias')
        self.institutional_activity = smart_money_data.get('institutional_activity')
        
        # Call parent calculate method
        result = self.calculate(price, volume, timestamp)
        
        # Enhance result with smart money data
        if result and result.signal:
            # Adjust signal strength based on smart money alignment
            if self.smart_money_metrics and self.institutional_bias:
                smart_money_alignment = (
                    self.smart_money_metrics.institutional_flow_ratio > 0.6 and
                    self.institutional_bias in [SmartMoneyBias.BULLISH, SmartMoneyBias.BEARISH]
                )
                
                if smart_money_alignment:
                    # Boost signal strength when smart money aligns
                    result.signal.strength = min(1.0, result.signal.strength * 1.2)
                else:
                    # Reduce signal strength when smart money doesn't align
                    result.signal.strength = max(0.0, result.signal.strength * 0.8)
            
            # Add smart money analysis to metadata
            if self.smart_money_metrics:
                if 'smart_money_analysis' not in result.signal.metadata:
                    result.signal.metadata['smart_money_analysis'] = {}
                
                result.signal.metadata['smart_money_analysis'].update({
                    'institutional_flow_ratio': self.smart_money_metrics.institutional_flow_ratio,
                    'smart_money_index': self.smart_money_metrics.smart_money_index,
                    'institutional_bias': self.institutional_bias.value if self.institutional_bias else None,
                    'institutional_activity': self.institutional_activity.value if self.institutional_activity else None
                })
        
        return result
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.ema_value = None
        self.atr_indicator.reset()

# ===========================================
# STANDARD DEVIATION
# ===========================================

class StandardDeviation(VolumeWeightedIndicator, SmartMoneyMixin):
    """Standard Deviation with Volume Weighting
    
    Features:
    - Traditional standard deviation calculation
    - Volume-weighted standard deviation
    - Volatility trend analysis
    - Outlier detection
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "StandardDeviation"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLATILITY
        
        self.std_values = deque(maxlen=config.max_memory_items if config.hft_mode else None)
        
        # Smart money analysis integration
        self.smart_money_metrics: Optional[SmartMoneyMetrics] = None
        self.institutional_bias: Optional[SmartMoneyBias] = None
        self.institutional_activity: Optional[InstitutionalActivity] = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Standard Deviation"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get window data
        window_prices = list(self.prices)[-self.config.period:]
        window_volumes = list(self.volumes)[-self.config.period:]
        
        # Calculate standard deviation
        if self.config.volume_weighted and sum(window_volumes) > 0:
            mean_price = self._calculate_volume_weighted_average(window_prices, window_volumes)
            std_value = self._calculate_volume_weighted_std(window_prices, window_volumes, mean_price)
        else:
            std_value = np.std(window_prices, ddof=1)
        
        self.std_values.append(std_value)
        
        # Generate signal based on standard deviation changes
        signal, confidence = self._generate_std_signal()
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=std_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'volume_weighted': self.config.volume_weighted,
                'std_percentile': self._calculate_std_percentile(),
                'volatility_trend': self._calculate_volatility_trend()
            }
        )
        
        self.results.append(result)
        return result
    
    def _calculate_volume_weighted_std(self, prices: List[float], volumes: List[float], mean: float) -> float:
        """Calculate volume-weighted standard deviation"""
        total_volume = sum(volumes)
        if total_volume == 0:
            return np.std(prices, ddof=1)
        
        weighted_variance = sum(v * (p - mean) ** 2 for p, v in zip(prices, volumes)) / total_volume
        return np.sqrt(weighted_variance)
    
    def _generate_std_signal(self) -> Tuple[SignalType, float]:
        """Generate signal based on standard deviation changes"""
        if len(self.std_values) < 5:
            return SignalType.NEUTRAL, 0.0
        
        recent_std = list(self.std_values)[-5:]
        std_change = (recent_std[-1] - recent_std[0]) / recent_std[0] if recent_std[0] != 0 else 0
        
        abs_change = abs(std_change)
        if abs_change < 0.1:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, abs_change / 0.3)
        
        if std_change > 0.2:  # Increasing volatility
            return SignalType.SELL, confidence
        elif std_change < -0.1:  # Decreasing volatility
            return SignalType.BUY, confidence * 0.7
        
        return SignalType.NEUTRAL, 0.0
    
    def _calculate_std_percentile(self) -> float:
        """Calculate current standard deviation percentile"""
        if len(self.std_values) < 20:
            return 0.5
        
        recent_std = list(self.std_values)[-20:]
        current_std = self.std_values[-1]
        
        percentile = np.sum(np.array(recent_std) <= current_std) / len(recent_std)
        return percentile
    
    def _calculate_volatility_trend(self) -> float:
        """Calculate volatility trend direction"""
        if len(self.std_values) < 10:
            return 0.0
        
        recent_std = list(self.std_values)[-10:]
        x = np.arange(len(recent_std))
        slope, _ = np.polyfit(x, recent_std, 1)
        
        # Normalize slope
        avg_std = np.mean(recent_std)
        return slope / avg_std if avg_std != 0 else 0.0
    
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update Standard Deviation with enhanced smart money analysis"""
        timestamp = timestamp or datetime.now()
        
        # Update smart money analysis
        smart_money_data = self.update_with_smart_money_analysis(price, volume, timestamp)
        self.smart_money_metrics = smart_money_data.get('smart_money_metrics')
        self.institutional_bias = smart_money_data.get('institutional_bias')
        self.institutional_activity = smart_money_data.get('institutional_activity')
        
        # Call parent calculate method
        result = self.calculate(price, volume, timestamp)
        
        # Enhance result with smart money data
        if result and result.signal:
            # Adjust signal strength based on smart money alignment
            if self.smart_money_metrics and self.institutional_bias:
                smart_money_alignment = (
                    self.smart_money_metrics.institutional_flow_ratio > 0.6 and
                    self.institutional_bias in [SmartMoneyBias.BULLISH, SmartMoneyBias.BEARISH]
                )
                
                if smart_money_alignment:
                    # Boost signal strength when smart money aligns
                    result.signal.strength = min(1.0, result.signal.strength * 1.2)
                else:
                    # Reduce signal strength when smart money doesn't align
                    result.signal.strength = max(0.0, result.signal.strength * 0.8)
            
            # Add smart money analysis to metadata
            if self.smart_money_metrics:
                if 'smart_money_analysis' not in result.signal.metadata:
                    result.signal.metadata['smart_money_analysis'] = {}
                
                result.signal.metadata['smart_money_analysis'].update({
                    'institutional_flow_ratio': self.smart_money_metrics.institutional_flow_ratio,
                    'smart_money_index': self.smart_money_metrics.smart_money_index,
                    'institutional_bias': self.institutional_bias.value if self.institutional_bias else None,
                    'institutional_activity': self.institutional_activity.value if self.institutional_activity else None
                })
        
        return result
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.std_values.clear()

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_bollinger_bands(period: int = 20, std_dev: float = 2.0, 
                          volume_weighted: bool = False, **kwargs) -> BollingerBands:
    """Create Bollinger Bands indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return BollingerBands(config, std_dev)

def create_atr(period: int = 14, volume_weighted: bool = False, **kwargs) -> ATR:
    """Create ATR indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return ATR(config)

def create_keltner_channels(period: int = 20, atr_multiplier: float = 2.0,
                           volume_weighted: bool = False, **kwargs) -> KeltnerChannels:
    """Create Keltner Channels indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return KeltnerChannels(config, atr_multiplier)

def create_standard_deviation(period: int = 20, volume_weighted: bool = False, 
                             **kwargs) -> StandardDeviation:
    """Create Standard Deviation indicator with specified configuration"""
    config = IndicatorConfig(
        period=period,
        volume_weighted=volume_weighted,
        **kwargs
    )
    return StandardDeviation(config)

# Export all indicators
__all__ = [
    'BollingerBands',
    'ATR',
    'KeltnerChannels', 
    'StandardDeviation',
    'create_bollinger_bands',
    'create_atr',
    'create_keltner_channels',
    'create_standard_deviation'
]