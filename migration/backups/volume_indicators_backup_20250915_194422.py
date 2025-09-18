"""Consolidated Volume Indicators

This module contains all volume-based technical indicators consolidated from multiple files:
- Volume Weighted Average Price (VWAP) with institutional analysis
- On Balance Volume (OBV) with smart money detection
- Money Flow Index (MFI) with volume confirmation
- Accumulation/Distribution Line with trend analysis
- Chaikin Money Flow (CMF) with institutional bias
- Volume Rate of Change (VROC) with momentum analysis
- Ease of Movement (EOM) with volume-price relationship
- Volume Profile with institutional flow detection

All indicators support:
- Smart money flow detection
- Institutional volume analysis
- Volume-price relationship analysis
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
    memory_efficient
)
from .multi_value_indicator import MultiValueIndicator

logger = logging.getLogger(__name__)

# ===========================================
# VOLUME WEIGHTED AVERAGE PRICE (VWAP)
# ===========================================

class VWAP(VolumeWeightedIndicator):
    """Volume Weighted Average Price with Institutional Analysis
    
    Features:
    - Traditional VWAP calculation
    - Intraday and multi-day VWAP
    - VWAP bands for support/resistance
    - Institutional flow detection
    - Smart money analysis
    """
    
    def __init__(self, config: IndicatorConfig, reset_period: str = "daily", name: str = "VWAP"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLUME
        
        self.reset_period = reset_period
        
        # VWAP calculation components
        self.cumulative_pv = 0.0  # Price * Volume
        self.cumulative_volume = 0.0
        self.vwap_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        
        # For VWAP bands
        self.pv_squared_sum = 0.0  # For standard deviation calculation
        
        # Reset tracking
        self.last_reset_time = None
        self.session_start = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate VWAP with institutional analysis"""
        self._add_data_point(price, volume, timestamp)
        
        # Check if we need to reset VWAP (for intraday calculations)
        if self._should_reset_vwap(timestamp):
            self._reset_vwap_calculation()
            self.session_start = timestamp
        
        # Update cumulative values
        pv = price * volume
        self.cumulative_pv += pv
        self.cumulative_volume += volume
        self.pv_squared_sum += price * price * volume
        
        if self.cumulative_volume == 0:
            return None
        
        # Calculate VWAP
        vwap_value = self.cumulative_pv / self.cumulative_volume
        self.vwap_values.append(vwap_value)
        
        # Calculate VWAP bands (standard deviation bands)
        vwap_std = self._calculate_vwap_std(vwap_value)
        upper_band = vwap_value + vwap_std
        lower_band = vwap_value - vwap_std
        
        # Generate signal based on price vs VWAP
        signal, confidence = self._generate_vwap_signal(price, vwap_value, volume)
        
        # Calculate institutional metrics
        institutional_flow = self._calculate_institutional_flow(price, volume, vwap_value)
        smart_money_score = self._calculate_smart_money_score(price, volume, vwap_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=vwap_value,
            signal=signal,
            confidence=confidence,
            upper_band=upper_band,
            lower_band=lower_band,
            metadata={
                'cumulative_volume': self.cumulative_volume,
                'cumulative_pv': self.cumulative_pv,
                'vwap_std': vwap_std,
                'price_vs_vwap': (price - vwap_value) / vwap_value * 100 if vwap_value != 0 else 0,
                'institutional_flow': institutional_flow,
                'smart_money_score': smart_money_score,
                'session_start': self.session_start,
                'volume_ratio': volume / (self.cumulative_volume / len(self.prices)) if len(self.prices) > 0 else 1.0
            }
        )
        
        self.results.append(result)
        return result
    
    def _should_reset_vwap(self, timestamp: datetime) -> bool:
        """Determine if VWAP should be reset based on reset period"""
        if self.reset_period == "never":
            return False
        
        if self.last_reset_time is None:
            self.last_reset_time = timestamp
            return True
        
        if self.reset_period == "daily":
            return timestamp.date() != self.last_reset_time.date()
        elif self.reset_period == "weekly":
            return timestamp.isocalendar()[1] != self.last_reset_time.isocalendar()[1]
        elif self.reset_period == "monthly":
            return timestamp.month != self.last_reset_time.month
        
        return False
    
    def _reset_vwap_calculation(self) -> None:
        """Reset VWAP calculation for new period"""
        self.cumulative_pv = 0.0
        self.cumulative_volume = 0.0
        self.pv_squared_sum = 0.0
    
    def _calculate_vwap_std(self, vwap: float) -> float:
        """Calculate VWAP standard deviation for bands"""
        if self.cumulative_volume == 0:
            return 0.0
        
        # Calculate volume-weighted variance
        variance = (self.pv_squared_sum / self.cumulative_volume) - (vwap * vwap)
        return np.sqrt(max(0, variance))
    
    def _generate_vwap_signal(self, price: float, vwap: float, volume: float) -> Tuple[SignalType, float]:
        """Generate signal based on price vs VWAP with volume confirmation"""
        if vwap == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (price - vwap) / vwap
        abs_deviation = abs(price_deviation)
        
        if abs_deviation < self.config.signal_threshold:
            return SignalType.NEUTRAL, 0.0
        
        # Base confidence from price deviation
        confidence = min(1.0, abs_deviation / 0.01)  # 1% deviation = full confidence
        
        # Enhance confidence with volume analysis
        volume_strength = self._calculate_volume_strength(volume)
        confidence *= (0.7 + 0.3 * volume_strength)
        
        # Institutional flow confirmation
        institutional_flow = self._calculate_institutional_flow(price, volume, vwap)
        if abs(institutional_flow) > 0.5:
            confidence *= 1.1
        
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
    
    def _calculate_volume_strength(self, current_volume: float) -> float:
        """Calculate volume strength relative to session average"""
        if len(self.volumes) < 5:
            return 0.5
        
        session_avg_volume = self.cumulative_volume / len(self.volumes)
        if session_avg_volume == 0:
            return 0.5
        
        volume_ratio = current_volume / session_avg_volume
        return min(1.0, max(0.0, (volume_ratio - 0.5) / 2.0))
    
    def _calculate_institutional_flow(self, price: float, volume: float, vwap: float) -> float:
        """Calculate institutional flow direction and strength"""
        if vwap == 0:
            return 0.0
        
        # Institutional flow: high volume trades away from VWAP
        price_distance = abs(price - vwap) / vwap
        volume_strength = self._calculate_volume_strength(volume)
        
        # Direction: positive if buying above VWAP or selling below VWAP
        direction = 1.0 if price > vwap else -1.0
        
        flow_strength = price_distance * volume_strength
        return direction * min(1.0, flow_strength * 5.0)
    
    def _calculate_smart_money_score(self, price: float, volume: float, vwap: float) -> float:
        """Calculate smart money involvement score"""
        # Smart money typically trades large volumes near VWAP
        if vwap == 0:
            return 0.0
        
        price_proximity = 1.0 - min(1.0, abs(price - vwap) / vwap / 0.005)  # Within 0.5% of VWAP
        volume_strength = self._calculate_volume_strength(volume)
        
        return price_proximity * volume_strength
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self._reset_vwap_calculation()
        self.vwap_values.clear()
        self.last_reset_time = None
        self.session_start = None

# ===========================================
# ON BALANCE VOLUME (OBV)
# ===========================================

class OBV(VolumeWeightedIndicator):
    """On Balance Volume with Smart Money Detection
    
    Features:
    - Traditional OBV calculation
    - Smart money flow detection
    - Volume momentum analysis
    - Divergence detection with price
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "OBV"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLUME
        
        # OBV calculation components
        self.obv_value = 0.0
        self.obv_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        self.previous_price = None
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate On Balance Volume"""
        self._add_data_point(price, volume, timestamp)
        
        if self.previous_price is None:
            self.previous_price = price
            self.obv_values.append(self.obv_value)
            return None
        
        # Update OBV based on price direction
        if price > self.previous_price:
            self.obv_value += volume
        elif price < self.previous_price:
            self.obv_value -= volume
        # If price unchanged, OBV remains the same
        
        self.obv_values.append(self.obv_value)
        self.previous_price = price
        
        # Generate signal based on OBV trend
        signal, confidence = self._generate_obv_signal()
        
        # Calculate additional metrics
        obv_momentum = self._calculate_obv_momentum()
        divergence_detected = self._detect_price_obv_divergence(price)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.obv_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'obv_momentum': obv_momentum,
                'divergence_detected': divergence_detected,
                'volume_direction': 1 if price > self.previous_price else (-1 if price < self.previous_price else 0),
                'cumulative_volume_flow': self.obv_value,
                'obv_trend': self._calculate_obv_trend()
            }
        )
        
        self.results.append(result)
        return result
    
    def _generate_obv_signal(self) -> Tuple[SignalType, float]:
        """Generate signal based on OBV momentum and trend"""
        if len(self.obv_values) < 5:
            return SignalType.NEUTRAL, 0.0
        
        obv_momentum = self._calculate_obv_momentum()
        obv_trend = self._calculate_obv_trend()
        
        # Combine momentum and trend for signal
        signal_strength = abs(obv_momentum) * abs(obv_trend)
        
        if signal_strength < 0.3:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, signal_strength)
        
        # Determine signal direction
        if obv_momentum > 0 and obv_trend > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        elif obv_momentum < 0 and obv_trend < 0:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
        
        return SignalType.NEUTRAL, confidence * 0.5
    
    def _calculate_obv_momentum(self) -> float:
        """Calculate OBV momentum (rate of change)"""
        if len(self.obv_values) < 5:
            return 0.0
        
        recent_obv = list(self.obv_values)[-5:]
        if len(recent_obv) < 2:
            return 0.0
        
        momentum = (recent_obv[-1] - recent_obv[0]) / max(abs(recent_obv[0]), 1)
        return max(-1.0, min(1.0, momentum))
    
    def _calculate_obv_trend(self) -> float:
        """Calculate OBV trend direction using linear regression"""
        if len(self.obv_values) < 10:
            return 0.0
        
        recent_obv = list(self.obv_values)[-10:]
        x = np.arange(len(recent_obv))
        
        try:
            slope, _ = np.polyfit(x, recent_obv, 1)
            # Normalize slope
            avg_obv = np.mean(recent_obv)
            normalized_slope = slope / max(abs(avg_obv), 1)
            return max(-1.0, min(1.0, normalized_slope))
        except:
            return 0.0
    
    def _detect_price_obv_divergence(self, current_price: float) -> bool:
        """Detect divergence between price and OBV trends"""
        if len(self.prices) < 10 or len(self.obv_values) < 10:
            return False
        
        # Calculate price trend
        recent_prices = list(self.prices)[-10:]
        price_x = np.arange(len(recent_prices))
        
        try:
            price_slope, _ = np.polyfit(price_x, recent_prices, 1)
            price_trend = 1 if price_slope > 0 else -1
        except:
            return False
        
        # Calculate OBV trend
        obv_trend_value = self._calculate_obv_trend()
        obv_trend = 1 if obv_trend_value > 0 else -1
        
        # Divergence occurs when trends are opposite
        return price_trend != obv_trend
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.obv_value = 0.0
        self.obv_values.clear()
        self.previous_price = None

# ===========================================
# MONEY FLOW INDEX (MFI)
# ===========================================

class MFI(VolumeWeightedIndicator):
    """Money Flow Index with Volume Confirmation
    
    Features:
    - Traditional MFI calculation (Volume-weighted RSI)
    - Overbought/oversold signal generation
    - Money flow analysis
    - Divergence detection
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "MFI"):
        super().__init__(config)
        self.name = name
        self.indicator_type = IndicatorType.VOLUME
        
        # MFI calculation components
        self.typical_prices = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        self.money_flows = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        self.positive_flows = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        self.negative_flows = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        
        # For typical price calculation (using price as high, low, close)
        self.previous_typical_price = None
        
        # Thresholds
        self.overbought_threshold = 80.0
        self.oversold_threshold = 20.0
        
        # EWM accumulators for volume-weighted money flows
        self._ewm_pos_flow: Optional[float] = None
        self._ewm_neg_flow: Optional[float] = None
        # Track last computed value for compatibility with base update() path
        self._last_value: float = 0.0
    
    def _extract_ohlc(self, price_input: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Duck-typed extraction of (high, low, close) from price_input.
        Accepts dict-like or object with attributes; falls back to None values if unavailable.
        """
        high = low = close = None
        try:
            if isinstance(price_input, dict):
                # Common key variants
                high = price_input.get('high') or price_input.get('High') or price_input.get('h')
                low = price_input.get('low') or price_input.get('Low') or price_input.get('l')
                close = price_input.get('close') or price_input.get('Close') or price_input.get('c') or price_input.get('price')
            else:
                # Attribute access (e.g., bar objects)
                high = getattr(price_input, 'high', None)
                low = getattr(price_input, 'low', None)
                close = getattr(price_input, 'close', getattr(price_input, 'price', None))
        except Exception:
            high = low = close = None
        
        # Ensure they are floats if present
        def _to_float(x):
            try:
                return float(x) if x is not None else None
            except Exception:
                return None
        return _to_float(high), _to_float(low), _to_float(close)
    
    def _typical_price_from_input(self, price_input: Any) -> float:
        """Compute typical price using OHLC if provided, else fallback to raw price.
        Typical Price = (High + Low + Close) / 3
        """
        h, l, c = self._extract_ohlc(price_input)
        if h is not None and l is not None and c is not None:
            return (h + l + c) / 3.0
        # Fallback: treat input as scalar price
        try:
            return float(price_input)
        except Exception:
            return 0.0
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Money Flow Index"""
        self._add_data_point(price, volume, timestamp)
        
        # Calculate typical price using OHLC if available
        typical_price = self._typical_price_from_input(price)
        self.typical_prices.append(typical_price)
        
        if self.previous_typical_price is None:
            self.previous_typical_price = typical_price
            return None
        
        # Calculate money flow
        money_flow = typical_price * volume
        self.money_flows.append(money_flow)
        
        # Determine if money flow is positive or negative
        if typical_price > self.previous_typical_price:
            self.positive_flows.append(money_flow)
            self.negative_flows.append(0.0)
        elif typical_price < self.previous_typical_price:
            self.positive_flows.append(0.0)
            self.negative_flows.append(money_flow)
        else:
            self.positive_flows.append(0.0)
            self.negative_flows.append(0.0)
        
        # Update EWM accumulators for positive/negative money flows
        alpha = self.config.get_alpha(self.config.period)
        pos_flow = money_flow if typical_price > self.previous_typical_price else 0.0
        neg_flow = money_flow if typical_price < self.previous_typical_price else 0.0
        self._ewm_pos_flow = pos_flow if self._ewm_pos_flow is None else (1.0 - alpha) * self._ewm_pos_flow + alpha * pos_flow
        self._ewm_neg_flow = neg_flow if self._ewm_neg_flow is None else (1.0 - alpha) * self._ewm_neg_flow + alpha * neg_flow
        
        self.previous_typical_price = typical_price
        
        if len(self.positive_flows) < self.config.period:
            return None
        
        # Calculate MFI using rolling sums over the configured period (classic definition)
        period_positive_flow = sum(list(self.positive_flows)[-self.config.period:])
        period_negative_flow = sum(list(self.negative_flows)[-self.config.period:])
        
        if period_negative_flow == 0:
            classic_mfi_value = 100.0
        else:
            money_ratio = period_positive_flow / period_negative_flow
            classic_mfi_value = 100.0 - (100.0 / (1.0 + money_ratio))
        
        # Calculate EWM-based MFI using standardized alpha policy
        if not self._ewm_neg_flow or self._ewm_neg_flow == 0.0:
            ewm_mfi_value = 100.0
        else:
            ewm_ratio = self._ewm_pos_flow / max(self._ewm_neg_flow, 1e-12)
            ewm_mfi_value = 100.0 - (100.0 / (1.0 + ewm_ratio))
        
        # Generate signal based on EWM-smoothed MFI (more stable)
        signal, confidence = self._generate_mfi_signal(ewm_mfi_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=ewm_mfi_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'positive_flow': period_positive_flow,
                'negative_flow': period_negative_flow,
                'money_ratio': period_positive_flow / max(period_negative_flow, 1),
                'typical_price': typical_price,
                'money_flow': money_flow,
                'classic_mfi': classic_mfi_value,
                'ewm_pos_flow': self._ewm_pos_flow,
                'ewm_neg_flow': self._ewm_neg_flow,
                'alpha': alpha,
                'overbought_threshold': self.overbought_threshold,
                'oversold_threshold': self.oversold_threshold
            }
        )
        
        self.results.append(result)
        # Track last computed value for base compatibility
        self._last_value = float(ewm_mfi_value)
        return result
    
    def _generate_mfi_signal(self, mfi: float) -> Tuple[SignalType, float]:
        """Generate signal based on MFI overbought/oversold levels"""
        confidence = 0.0
        signal = SignalType.NEUTRAL
        
        if mfi >= self.overbought_threshold:
            signal = SignalType.SELL
            confidence = min(1.0, (mfi - self.overbought_threshold) / 20.0 + 0.5)
        elif mfi <= self.oversold_threshold:
            signal = SignalType.BUY
            confidence = min(1.0, (self.oversold_threshold - mfi) / 20.0 + 0.5)
        
        # Enhance confidence for extreme levels
        if mfi >= 90:
            signal = SignalType.STRONG_SELL
            confidence = min(1.0, confidence * 1.2)
        elif mfi <= 10:
            signal = SignalType.STRONG_BUY
            confidence = min(1.0, confidence * 1.2)
        
        return signal, confidence
    
    def _calculate_volume_weighted_value(self) -> float:
        """Satisfy abstract method: return last computed MFI value for base update() compatibility."""
        try:
            return float(getattr(self, "_last_value", 0.0))
        except Exception:
            return 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.typical_prices.clear()
        self.money_flows.clear()
        self.positive_flows.clear()
        self.negative_flows.clear()
        self.previous_typical_price = None
        # Reset EWM accumulators
        self._ewm_pos_flow = None
        self._ewm_neg_flow = None
        self._last_value = 0.0

# ===========================================
# ACCUMULATION/DISTRIBUTION LINE
# ===========================================

class AccumulationDistribution(VolumeWeightedIndicator):
    """Accumulation/Distribution Line with Trend Analysis
    
    Features:
    - Traditional A/D Line calculation
    - Volume-price relationship analysis
    - Accumulation vs distribution detection
    - Trend confirmation signals
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "AccumulationDistribution"):
        super().__init__(config)
        self.name = name
        self.indicator_type = IndicatorType.VOLUME
        
        # A/D Line calculation components
        self.ad_value = 0.0
        self.ad_values = deque(maxlen=config.memory_limit if config.enable_hft_optimizations else None)
        # Initialize EWM accumulator to avoid AttributeError before first reset/calculate
        self._ewm_ad: Optional[float] = None
        # Track last computed value for base update() compatibility
        self._last_value: float = 0.0
    
    def _extract_ohlc(self, price_input: Any) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Duck-typed extraction of (high, low, close) from price_input for A/D calculation."""
        high = low = close = None
        try:
            if isinstance(price_input, dict):
                high = price_input.get('high') or price_input.get('High') or price_input.get('h')
                low = price_input.get('low') or price_input.get('Low') or price_input.get('l')
                close = price_input.get('close') or price_input.get('Close') or price_input.get('c') or price_input.get('price')
            else:
                high = getattr(price_input, 'high', None)
                low = getattr(price_input, 'low', None)
                close = getattr(price_input, 'close', getattr(price_input, 'price', None))
        except Exception:
            high = low = close = None
        
        def _to_float(x):
            try:
                return float(x) if x is not None else None
            except Exception:
                return None
        return _to_float(high), _to_float(low), _to_float(close)
        
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Accumulation/Distribution Line"""
        self._add_data_point(price, volume, timestamp)
        
        # Extract OHLC if available; fallback to scalar price for all three
        h, l, c = self._extract_ohlc(price)
        if h is None or l is None or c is None:
            try:
                scalar = float(price)
            except Exception:
                scalar = 0.0
            h = l = c = scalar
        
        # Calculate Money Flow Multiplier
        if h == l:
            mf_multiplier = 0.0
        else:
            mf_multiplier = ((c - l) - (h - c)) / (h - l)
        
        # Calculate Money Flow Volume
        mf_volume = mf_multiplier * volume
        
        # Update A/D Line
        self.ad_value += mf_volume
        self.ad_values.append(self.ad_value)
        
        # EWM-smoothed AD value for stability in signals
        alpha = self.config.get_alpha(self.config.period)
        self._ewm_ad = self.ad_value if self._ewm_ad is None else (1.0 - alpha) * self._ewm_ad + alpha * self.ad_value
        
        # Generate signal based on A/D trend
        signal, confidence = self._generate_ad_signal()
        
        # Calculate additional metrics
        ad_momentum = self._calculate_ad_momentum()
        accumulation_strength = self._calculate_accumulation_strength(mf_multiplier, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.ad_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'mf_multiplier': mf_multiplier,
                'mf_volume': mf_volume,
                'ad_momentum': ad_momentum,
                'accumulation_strength': accumulation_strength,
                'ad_trend': self._calculate_ad_trend(),
                'ewm_ad': self._ewm_ad,
                'alpha': alpha
            }
        )
        
        self.results.append(result)
        # Track last computed value for base compatibility
        self._last_value = float(self.ad_value)
        return result
    
    def _generate_ad_signal(self) -> Tuple[SignalType, float]:
        """Generate signal based on A/D Line trend and momentum"""
        if len(self.ad_values) < 5:
            return SignalType.NEUTRAL, 0.0
        
        ad_momentum = self._calculate_ad_momentum()
        ad_trend = self._calculate_ad_trend()
        
        signal_strength = abs(ad_momentum) * abs(ad_trend)
        
        if signal_strength < 0.3:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(1.0, signal_strength)
        
        if ad_momentum > 0 and ad_trend > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        elif ad_momentum < 0 and ad_trend < 0:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
        
        return SignalType.NEUTRAL, confidence * 0.5
    
    def _calculate_ad_momentum(self) -> float:
        """Calculate A/D Line momentum"""
        if len(self.ad_values) < 5:
            return 0.0
        
        recent_ad = list(self.ad_values)[-5:]
        if len(recent_ad) < 2:
            return 0.0
        
        momentum = (recent_ad[-1] - recent_ad[0]) / max(abs(recent_ad[0]), 1)
        return max(-1.0, min(1.0, momentum))
    
    def _calculate_ad_trend(self) -> float:
        """Calculate A/D Line trend using linear regression"""
        if len(self.ad_values) < 10:
            return 0.0
        
        recent_ad = list(self.ad_values)[-10:]
        x = np.arange(len(recent_ad))
        
        try:
            slope, _ = np.polyfit(x, recent_ad, 1)
            avg_ad = np.mean(recent_ad)
            normalized_slope = slope / max(abs(avg_ad), 1)
            return max(-1.0, min(1.0, normalized_slope))
        except:
            return 0.0
    
    def _calculate_accumulation_strength(self, mf_multiplier: float, volume: float) -> float:
        """Calculate current accumulation/distribution strength"""
        if len(self.volumes) < 5:
            return 0.0
        
        # Compare current volume to recent average
        recent_volumes = list(self.volumes)[-5:]
        avg_volume = np.mean(recent_volumes)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Combine with money flow multiplier
        strength = mf_multiplier * min(2.0, volume_ratio)
        return max(-1.0, min(1.0, strength))
    
    def _calculate_volume_weighted_value(self) -> float:
        """Satisfy abstract method: return last computed AD value for base update() compatibility."""
        try:
            return float(getattr(self, "_last_value", 0.0))
        except Exception:
            return 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.ad_value = 0.0
        self.ad_values.clear()
        # Reset EWM accumulator
        self._ewm_ad = None
        self._last_value = 0.0

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_vwap(reset_period: str = "daily", **kwargs) -> VWAP:
    """Create VWAP indicator with specified configuration"""
    config = IndicatorConfig(**kwargs)
    return VWAP(config, reset_period)

def create_obv(**kwargs) -> OBV:
    """Create OBV indicator with specified configuration"""
    config = IndicatorConfig(**kwargs)
    return OBV(config)

def create_mfi(period: int = 14, **kwargs) -> MFI:
    """Create MFI indicator with specified configuration"""
    config = IndicatorConfig(period=period, **kwargs)
    return MFI(config)

def create_accumulation_distribution(**kwargs) -> AccumulationDistribution:
    """Create A/D Line indicator with specified configuration"""
    config = IndicatorConfig(**kwargs)
    return AccumulationDistribution(config)

# Export all indicators
__all__ = [
    'VWAP',
    'OBV',
    'MFI',
    'AccumulationDistribution',
    'create_vwap',
    'create_obv',
    'create_mfi',
    'create_accumulation_distribution'
]


# ===========================================
# CHAIKIN MONEY FLOW (CMF)
# ===========================================

class CMF(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    \"\"\"Chaikin Money Flow with Institutional Bias
    
    Features:
    - Measures buying/selling pressure
    - Institutional accumulation detection
    - Signal generation based on zero line
    \"\"\"
    
    def __init__(self, config: IndicatorConfig, name: str = \"CMF\"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLUME
        self.mf_volumes = deque(maxlen=config.period)
        self.volumes_window = deque(maxlen=config.period)
        self.cmf_value = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        if high == low:
            mf_multiplier = 0
        else:
            mf_multiplier = ((close - low) - (high - close)) / (high - low)
        mf_volume = mf_multiplier * volume
        self.mf_volumes.append(mf_volume)
        self.volumes_window.append(volume)
        
        if len(self.mf_volumes) < self.config.period:
            return None
        
        sum_mf = sum(self.mf_volumes)
        sum_vol = sum(self.volumes_window)
        self.cmf_value = sum_mf / sum_vol if sum_vol != 0 else 0
        
        signal, confidence = self._generate_cmf_signal(self.cmf_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.cmf_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'sum_mf': sum_mf,
                'sum_vol': sum_vol
            }
        )
        self.results.append(result)
        return result
    
    def _generate_cmf_signal(self, cmf: float) -> Tuple[SignalType, float]:
        strength = abs(cmf)
        confidence = min(1.0, strength * 5)
        if cmf > 0.05:
            return SignalType.STRONG_BUY, confidence
        elif cmf > 0:
            return SignalType.BUY, confidence
        elif cmf < -0.05:
            return SignalType.STRONG_SELL, confidence
        elif cmf < 0:
            return SignalType.SELL, confidence
        return SignalType.NEUTRAL, 0.0

# ===========================================
# EASE OF MOVEMENT (EOM)
# ===========================================

class EOM(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Ease of Movement with Institutional Flow Detection
    
    Features:
    - Price-volume relationship analysis
    - Movement efficiency measurement
    - Smart money flow detection
    - Signal generation with thresholds
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "EOM"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLUME
        self.alpha = config.get_alpha(config.period)
        self.eom_value = None
        self.highs = deque(maxlen=2)
        self.lows = deque(maxlen=2)
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(close, volume, timestamp)
        self.highs.append(high)
        self.lows.append(low)
        
        if len(self.highs) < 2 or volume == 0:
            return None
        
        distance_moved = ((high + low) / 2) - ((self.highs[0] + self.lows[0]) / 2)
        box_ratio = (volume / 1000000) / (high - low) if (high - low) != 0 else 0
        eom_raw = distance_moved / box_ratio if box_ratio != 0 else 0
        
        if self.eom_value is None:
            self.eom_value = eom_raw
        else:
            self.eom_value = self.alpha * eom_raw + (1 - self.alpha) * self.eom_value
        
        signal, confidence = self._generate_eom_signal(self.eom_value)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.eom_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'distance_moved': distance_moved,
                'box_ratio': box_ratio
            }
        )
        self.results.append(result)
        return result
    
    def _generate_eom_signal(self, eom: float) -> Tuple[SignalType, float]:
        abs_eom = abs(eom)
        confidence = min(1.0, abs_eom / 100)
        if eom > 0:
            return (SignalType.STRONG_BUY if abs_eom > 50 else SignalType.BUY), confidence
        elif eom < 0:
            return (SignalType.STRONG_SELL if abs_eom > 50 else SignalType.SELL), confidence
        return SignalType.NEUTRAL, 0.0

# ===========================================
# NEGATIVE VOLUME INDEX (NVI)
# ===========================================

class NVI(AugmentedIndicator, VolumeConfirmationMixin, SmartMoneyMixin):
    """Negative Volume Index with Smart Money Enhancements
    
    Features:
    - Focus on price changes on down-volume days
    - Smart money accumulation detection
    - Trend persistence analysis
    - Signal generation with volume confirmation
    """
    
    def __init__(self, config: IndicatorConfig, name: str = "NVI"):
        super().__init__(config, name)
        self.indicator_type = IndicatorType.VOLUME
        self.alpha = config.get_alpha(config.period)
        self.nvi_value = 1000  # Standard starting point
        self.prev_volume = None
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        self._add_data_point(price, volume, timestamp)
        
        if self.prev_volume is None:
            self.prev_volume = volume
            return None
        
        if volume < self.prev_volume:
            price_change = (price - list(self.prices)[-2]) / list(self.prices)[-2] if list(self.prices)[-2] != 0 else 0
            self.nvi_value += price_change * self.nvi_value
        
        # Apply EMA smoothing
        self.nvi_value = self.alpha * self.nvi_value + (1 - self.alpha) * self.nvi_value
        
        self.prev_volume = volume
        
        if len(self.prices) < self.config.period:
            return None
        
        signal, confidence = self._generate_nvi_signal(self.nvi_value, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.nvi_value,
            signal=signal,
            confidence=confidence,
            metadata={
                'volume_change': (volume - self.prev_volume) / self.prev_volume if self.prev_volume != 0 else 0
            }
        )
        self.results.append(result)
        return result
    
    def _generate_nvi_signal(self, nvi: float, volume: float) -> Tuple[SignalType, float]:
        # Assuming higher NVI indicates smart money accumulation
        deviation = (nvi - 1000) / 1000
        confidence = min(1.0, abs(deviation))
        if deviation > 0:
            return SignalType.BUY, confidence
        elif deviation < 0:
            return SignalType.SELL, confidence
        return SignalType.NEUTRAL, 0.0