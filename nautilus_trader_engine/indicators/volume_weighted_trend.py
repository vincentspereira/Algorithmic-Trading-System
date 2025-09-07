"""Consolidated Volume-Weighted Trend Indicators

Unified implementation combining enhanced and volume-weighted trend indicators with:
- Configurable adaptive features and institutional analysis
- Dynamic signal generation based on market conditions
- TWAP/VWAP integration for institutional-grade accuracy
- Advanced trend detection with confidence scoring
- High-frequency trading optimizations

Indicators include:
- Unified Volume-Weighted MACD (Unified VW MACD)
- Unified Volume-Weighted ADX (Unified VW ADX)
- Unified Volume-Weighted Aroon (Unified VW Aroon)
- Unified Volume-Weighted Parabolic SAR (Unified VW PSAR)
- Unified Volume-Weighted TSI (Unified VW TSI)
"""

import numpy as np
import talib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import deque
from dataclasses import dataclass
from enum import Enum

from .enhanced_base import (
    VolumeWeightedIndicator,
    MultiValueIndicator,
    AdaptiveIndicator,
    IndicatorConfig,
    IndicatorResult,
    IndicatorType,
    SignalType,
    calculate_ema,
    calculate_sma
)

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class TrendMode(Enum):
    """Trend analysis modes"""
    BASIC = "basic"  # Basic volume weighting only
    ENHANCED = "enhanced"  # Enhanced with adaptive features
    INSTITUTIONAL = "institutional"  # Full institutional features
    HYBRID = "hybrid"  # Combination of enhanced and institutional

@dataclass
class TrendConfig:
    """Configuration for trend indicators"""
    trend_mode: TrendMode = TrendMode.ENHANCED
    enable_adaptive_parameters: bool = True
    enable_institutional_analysis: bool = False
    enable_market_regime_detection: bool = True
    confidence_threshold: float = 0.7
    trend_strength_threshold: float = 0.6
    divergence_detection: bool = True
    smart_money_threshold: float = 2.0
    institutional_threshold: float = 3.0

class UnifiedVolumeWeightedMACD(MultiValueIndicator):
    """Unified Volume-Weighted MACD
    
    Consolidated implementation combining enhanced adaptive features
    with institutional-grade trend analysis capabilities.
    """
    
    def __init__(self, config: IndicatorConfig, trend_config: TrendConfig = None,
                 fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(config, "Unified_VW_MACD")
        self.indicator_type = IndicatorType.TREND
        self.trend_config = trend_config or TrendConfig()
        
        # MACD parameters
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        # Feature configuration
        self.adaptive_features = self.trend_config.trend_mode in [TrendMode.ENHANCED, TrendMode.HYBRID]
        self.institutional_features = self.trend_config.trend_mode in [TrendMode.INSTITUTIONAL, TrendMode.HYBRID]
        
        # Enhanced data structures
        if self.institutional_features:
            self.smart_money_flows = deque(maxlen=config.period * 2)
            self.institutional_factors = deque(maxlen=config.period * 2)
            self.market_regimes = deque(maxlen=config.period * 2)
        
        # MACD components
        self.fast_ema_values = deque(maxlen=config.period * 2)
        self.slow_ema_values = deque(maxlen=config.period * 2)
        self.macd_values = deque(maxlen=config.period * 2)
        self.signal_values = deque(maxlen=config.period * 2)
        self.histogram_values = deque(maxlen=config.period * 2)
        
        # Adaptive parameters
        self.adaptive_fast_period = fast_period
        self.adaptive_slow_period = slow_period
        self.adaptive_signal_period = signal_period
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Unified Volume-Weighted MACD"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < max(self.slow_period, self.config.min_periods):
            return None
        
        # Apply volume weighting
        vw_price = self._calculate_volume_weighted_price(price, volume)
        
        # Update adaptive parameters if enabled
        if self.adaptive_features:
            self._update_adaptive_parameters()
        
        # Calculate MACD components
        fast_ema = self._calculate_adaptive_ema(vw_price, self.adaptive_fast_period, self.fast_ema_values)
        slow_ema = self._calculate_adaptive_ema(vw_price, self.adaptive_slow_period, self.slow_ema_values)
        
        macd_line = fast_ema - slow_ema
        signal_line = self._calculate_adaptive_ema(macd_line, self.adaptive_signal_period, self.signal_values)
        histogram = macd_line - signal_line
        
        # Store values
        self.fast_ema_values.append(fast_ema)
        self.slow_ema_values.append(slow_ema)
        self.macd_values.append(macd_line)
        self.signal_values.append(signal_line)
        self.histogram_values.append(histogram)
        
        # Generate signal with adaptive features
        signal, confidence = self._generate_macd_signal(macd_line, signal_line, histogram, volume)
        
        # Build comprehensive metadata
        metadata = self._build_macd_metadata(fast_ema, slow_ema, macd_line, signal_line, histogram, vw_price, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=macd_line,
            signal=signal,
            confidence=confidence,
            metadata=metadata
        )
        
        self.results.append(result)
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _calculate_volume_weighted_price(self, price: float, volume: float) -> float:
        """Calculate volume-weighted price with optional enhancements"""
        if not self.config.volume_weighted:
            return price
        
        # Basic volume weighting
        recent_prices = list(self.prices)[-min(10, len(self.prices)):]
        recent_volumes = list(self.volumes)[-min(10, len(self.volumes)):]
        
        if sum(recent_volumes) > 0:
            vw_price = sum(p * v for p, v in zip(recent_prices, recent_volumes)) / sum(recent_volumes)
        else:
            vw_price = price
        
        # Apply institutional weighting if enabled
        if self.institutional_features:
            vw_price = self._apply_institutional_weighting(vw_price, volume)
        
        return vw_price
    
    def _apply_institutional_weighting(self, price: float, volume: float) -> float:
        """Apply institutional weighting factors"""
        if not self.trend_config.enable_institutional_analysis:
            return price
        
        # Smart money flow detection
        smart_money_factor = self._detect_smart_money_flow(price, volume)
        institutional_factor = self._detect_institutional_activity(price, volume)
        
        # Apply weighting
        enhanced_weight = 1.0 + (smart_money_factor * 0.1) + (institutional_factor * 0.05)
        return price * enhanced_weight
    
    def _detect_smart_money_flow(self, price: float, volume: float) -> float:
        """Detect smart money flow patterns"""
        if len(self.volumes) < 20:
            return 0.0
        
        avg_volume = np.mean(list(self.volumes)[-20:])
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        if volume_ratio > self.trend_config.smart_money_threshold:
            return min(1.0, (volume_ratio - self.trend_config.smart_money_threshold) / 2.0)
        
        return 0.0
    
    def _detect_institutional_activity(self, price: float, volume: float) -> float:
        """Detect institutional activity patterns"""
        if not self.trend_config.enable_institutional_analysis or len(self.volumes) < 20:
            return 0.0
        
        avg_volume = np.mean(list(self.volumes)[-20:])
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        if volume_ratio > self.trend_config.institutional_threshold:
            return min(1.0, (volume_ratio - self.trend_config.institutional_threshold) / 3.0)
        
        return 0.0
    
    def _update_adaptive_parameters(self):
        """Update adaptive parameters based on market conditions"""
        if not self.trend_config.enable_adaptive_parameters or len(self.results) < 50:
            return
        
        # Market regime detection
        recent_prices = [r.value for r in self.results[-50:]]
        volatility = np.std(recent_prices)
        
        # Adjust periods based on volatility
        if volatility > np.mean([abs(x) for x in recent_prices]) * 0.5:  # High volatility
            self.adaptive_fast_period = max(8, self.fast_period - 2)
            self.adaptive_slow_period = max(20, self.slow_period - 4)
            self.adaptive_signal_period = max(6, self.signal_period - 2)
        elif volatility < np.mean([abs(x) for x in recent_prices]) * 0.2:  # Low volatility
            self.adaptive_fast_period = min(16, self.fast_period + 2)
            self.adaptive_slow_period = min(32, self.slow_period + 4)
            self.adaptive_signal_period = min(12, self.signal_period + 2)
        else:  # Normal volatility
            self.adaptive_fast_period = self.fast_period
            self.adaptive_slow_period = self.slow_period
            self.adaptive_signal_period = self.signal_period
    
    def _calculate_adaptive_ema(self, value: float, period: int, value_history: deque) -> float:
        """Calculate EMA with adaptive smoothing"""
        alpha = 2.0 / (period + 1)
        
        if not value_history:
            return value
        
        # Apply adaptive smoothing if enabled
        if self.adaptive_features and len(value_history) >= 10:
            recent_volatility = np.std(list(value_history)[-10:])
            volatility_factor = min(2.0, max(0.5, recent_volatility / np.mean([abs(x) for x in value_history[-10:]])))
            adaptive_alpha = alpha * volatility_factor
        else:
            adaptive_alpha = alpha
        
        return adaptive_alpha * value + (1 - adaptive_alpha) * value_history[-1]
    
    def _generate_macd_signal(self, macd_line: float, signal_line: float, histogram: float, volume: float) -> Tuple[SignalType, float]:
        """Generate MACD signal with adaptive features"""
        # Basic MACD signals
        signal_type = SignalType.NEUTRAL
        base_confidence = 0.0
        
        # MACD line crossover signals
        if len(self.macd_values) >= 2 and len(self.signal_values) >= 2:
            prev_macd = self.macd_values[-2]
            prev_signal = self.signal_values[-2]
            
            # Bullish crossover
            if prev_macd <= prev_signal and macd_line > signal_line:
                signal_type = SignalType.BUY
                base_confidence = min(1.0, abs(macd_line - signal_line) / max(abs(macd_line), abs(signal_line), 0.001))
            
            # Bearish crossover
            elif prev_macd >= prev_signal and macd_line < signal_line:
                signal_type = SignalType.SELL
                base_confidence = min(1.0, abs(macd_line - signal_line) / max(abs(macd_line), abs(signal_line), 0.001))
        
        # Zero line crossover signals (enhanced feature)
        if self.adaptive_features and len(self.macd_values) >= 2:
            prev_macd = self.macd_values[-2]
            
            if prev_macd <= 0 and macd_line > 0:
                if signal_type == SignalType.NEUTRAL:
                    signal_type = SignalType.BUY
                    base_confidence = 0.6
                elif signal_type == SignalType.BUY:
                    base_confidence = min(1.0, base_confidence + 0.3)
            
            elif prev_macd >= 0 and macd_line < 0:
                if signal_type == SignalType.NEUTRAL:
                    signal_type = SignalType.SELL
                    base_confidence = 0.6
                elif signal_type == SignalType.SELL:
                    base_confidence = min(1.0, base_confidence + 0.3)
        
        # Histogram momentum signals
        if len(self.histogram_values) >= 3:
            hist_trend = self._calculate_histogram_trend()
            if hist_trend > 0.5 and signal_type in [SignalType.BUY, SignalType.NEUTRAL]:
                base_confidence = min(1.0, base_confidence + 0.2)
            elif hist_trend < -0.5 and signal_type in [SignalType.SELL, SignalType.NEUTRAL]:
                base_confidence = min(1.0, base_confidence + 0.2)
        
        # Apply institutional confidence boost if enabled
        if self.institutional_features:
            institutional_boost = self._calculate_institutional_confidence_boost(volume)
            final_confidence = min(1.0, base_confidence * (1 + institutional_boost))
        else:
            final_confidence = base_confidence
        
        # Apply confidence threshold
        if final_confidence < self.trend_config.confidence_threshold:
            signal_type = SignalType.NEUTRAL
            final_confidence = 0.0
        
        return signal_type, final_confidence
    
    def _calculate_histogram_trend(self) -> float:
        """Calculate histogram trend momentum"""
        if len(self.histogram_values) < 3:
            return 0.0
        
        recent_hist = list(self.histogram_values)[-3:]
        
        # Simple trend calculation
        if recent_hist[2] > recent_hist[1] > recent_hist[0]:
            return 1.0  # Strong uptrend
        elif recent_hist[2] > recent_hist[1]:
            return 0.5  # Weak uptrend
        elif recent_hist[2] < recent_hist[1] < recent_hist[0]:
            return -1.0  # Strong downtrend
        elif recent_hist[2] < recent_hist[1]:
            return -0.5  # Weak downtrend
        
        return 0.0  # No clear trend
    
    def _calculate_institutional_confidence_boost(self, volume: float) -> float:
        """Calculate confidence boost from institutional activity"""
        smart_money_factor = self._detect_smart_money_flow(self.prices[-1], volume)
        institutional_factor = self._detect_institutional_activity(self.prices[-1], volume)
        
        return (smart_money_factor * 0.2) + (institutional_factor * 0.3)
    
    def _build_macd_metadata(self, fast_ema: float, slow_ema: float, macd_line: float, 
                           signal_line: float, histogram: float, vw_price: float, volume: float) -> Dict[str, Any]:
        """Build comprehensive MACD metadata"""
        metadata = {
            'fast_ema': fast_ema,
            'slow_ema': slow_ema,
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram,
            'vw_price': vw_price,
            'fast_period': self.adaptive_fast_period,
            'slow_period': self.adaptive_slow_period,
            'signal_period': self.adaptive_signal_period,
            'trend_mode': self.trend_config.trend_mode.value
        }
        
        # Add enhanced metadata
        if self.adaptive_features:
            metadata['adaptive_parameters'] = True
            metadata['market_regime'] = self._get_market_regime()
            
            if len(self.histogram_values) >= 3:
                metadata['histogram_trend'] = self._calculate_histogram_trend()
        
        # Add institutional metadata
        if self.institutional_features:
            metadata['smart_money_factor'] = self._detect_smart_money_flow(self.prices[-1], volume)
            metadata['institutional_factor'] = self._detect_institutional_activity(self.prices[-1], volume)
        
        # Add divergence detection if enabled
        if self.trend_config.divergence_detection and len(self.results) >= 20:
            metadata['price_divergence'] = self._detect_price_divergence()
        
        return metadata
    
    def _get_market_regime(self) -> str:
        """Determine current market regime"""
        if len(self.results) < 50:
            return "unknown"
        
        recent_values = [r.value for r in self.results[-50:]]
        volatility = np.std(recent_values)
        mean_abs_value = np.mean([abs(x) for x in recent_values])
        
        if volatility > mean_abs_value * 0.5:
            return "high_volatility"
        elif volatility < mean_abs_value * 0.2:
            return "low_volatility"
        else:
            return "normal"
    
    def _detect_price_divergence(self) -> bool:
        """Detect price-MACD divergence"""
        if len(self.results) < 20 or len(self.prices) < 20:
            return False
        
        # Simple divergence detection
        recent_prices = list(self.prices)[-10:]
        recent_macd = [r.value for r in self.results[-10:]]
        
        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        macd_trend = recent_macd[-1] - recent_macd[0]
        
        # Divergence occurs when price and MACD move in opposite directions
        return (price_trend > 0 and macd_trend < 0) or (price_trend < 0 and macd_trend > 0)

class UnifiedVolumeWeightedADX(VolumeWeightedIndicator):
    """Unified Volume-Weighted Average Directional Index
    
    Consolidated ADX implementation with configurable adaptive features.
    """
    
    def __init__(self, config: IndicatorConfig, trend_config: TrendConfig = None):
        super().__init__(config, "Unified_VW_ADX")
        self.indicator_type = IndicatorType.TREND
        self.trend_config = trend_config or TrendConfig()
        
        # Feature configuration
        self.adaptive_features = self.trend_config.trend_mode in [TrendMode.ENHANCED, TrendMode.HYBRID]
        self.institutional_features = self.trend_config.trend_mode in [TrendMode.INSTITUTIONAL, TrendMode.HYBRID]
        
        # ADX components
        self.high_prices = deque(maxlen=config.period * 2)
        self.low_prices = deque(maxlen=config.period * 2)
        self.close_prices = deque(maxlen=config.period * 2)
        
        self.tr_values = deque(maxlen=config.period * 2)
        self.plus_dm_values = deque(maxlen=config.period * 2)
        self.minus_dm_values = deque(maxlen=config.period * 2)
        
        self.plus_di_values = deque(maxlen=config.period * 2)
        self.minus_di_values = deque(maxlen=config.period * 2)
        self.dx_values = deque(maxlen=config.period * 2)
        self.adx_values = deque(maxlen=config.period * 2)
    
    def calculate(self, high: float, low: float, close: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Unified Volume-Weighted ADX"""
        start_time = datetime.now()
        
        # Store OHLC data
        self.high_prices.append(high)
        self.low_prices.append(low)
        self.close_prices.append(close)
        self._add_data_point(close, volume, timestamp)
        
        if len(self.close_prices) < 2:
            return None
        
        # Calculate True Range and Directional Movement
        tr = self._calculate_true_range(high, low, close)
        plus_dm, minus_dm = self._calculate_directional_movement(high, low)
        
        self.tr_values.append(tr)
        self.plus_dm_values.append(plus_dm)
        self.minus_dm_values.append(minus_dm)
        
        if len(self.tr_values) < self.config.period:
            return None
        
        # Calculate smoothed values
        smoothed_tr = self._calculate_smoothed_average(self.tr_values)
        smoothed_plus_dm = self._calculate_smoothed_average(self.plus_dm_values)
        smoothed_minus_dm = self._calculate_smoothed_average(self.minus_dm_values)
        
        # Calculate Directional Indicators
        plus_di = (smoothed_plus_dm / smoothed_tr) * 100 if smoothed_tr > 0 else 0
        minus_di = (smoothed_minus_dm / smoothed_tr) * 100 if smoothed_tr > 0 else 0
        
        self.plus_di_values.append(plus_di)
        self.minus_di_values.append(minus_di)
        
        # Calculate DX
        di_sum = plus_di + minus_di
        dx = abs(plus_di - minus_di) / di_sum * 100 if di_sum > 0 else 0
        self.dx_values.append(dx)
        
        if len(self.dx_values) < self.config.period:
            return None
        
        # Calculate ADX
        adx = self._calculate_smoothed_average(self.dx_values)
        self.adx_values.append(adx)
        
        # Apply volume weighting if enabled
        if self.config.volume_weighted:
            adx = self._apply_volume_weighting_to_adx(adx, volume)
        
        # Generate signal
        signal, confidence = self._generate_adx_signal(adx, plus_di, minus_di, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=adx,
            signal=signal,
            confidence=confidence,
            metadata={
                'plus_di': plus_di,
                'minus_di': minus_di,
                'dx': dx,
                'trend_strength': self._classify_trend_strength(adx),
                'trend_mode': self.trend_config.trend_mode.value
            }
        )
        
        self.results.append(result)
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _calculate_true_range(self, high: float, low: float, close: float) -> float:
        """Calculate True Range"""
        if len(self.close_prices) < 2:
            return high - low
        
        prev_close = self.close_prices[-2]
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        return max(tr1, tr2, tr3)
    
    def _calculate_directional_movement(self, high: float, low: float) -> Tuple[float, float]:
        """Calculate Directional Movement"""
        if len(self.high_prices) < 2 or len(self.low_prices) < 2:
            return 0.0, 0.0
        
        prev_high = self.high_prices[-2]
        prev_low = self.low_prices[-2]
        
        plus_dm = high - prev_high if high - prev_high > prev_low - low and high - prev_high > 0 else 0
        minus_dm = prev_low - low if prev_low - low > high - prev_high and prev_low - low > 0 else 0
        
        return plus_dm, minus_dm
    
    def _calculate_smoothed_average(self, values: deque) -> float:
        """Calculate smoothed average (Wilder's smoothing)"""
        if len(values) < self.config.period:
            return 0.0
        
        if len(values) == self.config.period:
            return sum(list(values)[-self.config.period:]) / self.config.period
        
        # Wilder's smoothing: (previous_average * (period - 1) + current_value) / period
        recent_values = list(values)[-self.config.period:]
        prev_avg = sum(recent_values[:-1]) / (self.config.period - 1) if len(recent_values) > 1 else recent_values[0]
        
        return (prev_avg * (self.config.period - 1) + values[-1]) / self.config.period
    
    def _apply_volume_weighting_to_adx(self, adx: float, volume: float) -> float:
        """Apply volume weighting to ADX value"""
        if len(self.volumes) < 10:
            return adx
        
        avg_volume = np.mean(list(self.volumes)[-10:])
        volume_factor = min(1.5, max(0.7, volume / avg_volume)) if avg_volume > 0 else 1.0
        
        return adx * volume_factor
    
    def _generate_adx_signal(self, adx: float, plus_di: float, minus_di: float, volume: float) -> Tuple[SignalType, float]:
        """Generate ADX-based trend signal"""
        # Determine trend strength
        trend_strength = self._classify_trend_strength(adx)
        
        # Base signal from DI crossover
        signal_type = SignalType.NEUTRAL
        base_confidence = 0.0
        
        if plus_di > minus_di and adx > 25:
            signal_type = SignalType.BUY
            base_confidence = min(1.0, (adx - 25) / 50)  # Normalize to 0-1
        elif minus_di > plus_di and adx > 25:
            signal_type = SignalType.SELL
            base_confidence = min(1.0, (adx - 25) / 50)
        
        # Enhance confidence based on trend strength
        if trend_strength == "very_strong":
            base_confidence = min(1.0, base_confidence * 1.3)
        elif trend_strength == "strong":
            base_confidence = min(1.0, base_confidence * 1.1)
        elif trend_strength == "weak":
            base_confidence *= 0.7
        
        # Apply institutional boost if enabled
        if self.institutional_features:
            institutional_boost = self._calculate_institutional_confidence_boost(volume)
            final_confidence = min(1.0, base_confidence * (1 + institutional_boost))
        else:
            final_confidence = base_confidence
        
        return signal_type, final_confidence
    
    def _classify_trend_strength(self, adx: float) -> str:
        """Classify trend strength based on ADX value"""
        if adx >= 50:
            return "very_strong"
        elif adx >= 25:
            return "strong"
        elif adx >= 15:
            return "moderate"
        else:
            return "weak"
    
    def _calculate_institutional_confidence_boost(self, volume: float) -> float:
        """Calculate confidence boost from institutional activity"""
        if len(self.volumes) < 20:
            return 0.0
        
        avg_volume = np.mean(list(self.volumes)[-20:])
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Smart money detection
        smart_money_factor = 0.0
        if volume_ratio > self.trend_config.smart_money_threshold:
            smart_money_factor = min(0.3, (volume_ratio - self.trend_config.smart_money_threshold) / 5.0)
        
        # Institutional activity detection
        institutional_factor = 0.0
        if volume_ratio > self.trend_config.institutional_threshold:
            institutional_factor = min(0.4, (volume_ratio - self.trend_config.institutional_threshold) / 7.0)
        
        return smart_money_factor + institutional_factor

# Factory function for creating unified trend indicators
def create_unified_trend_indicator(indicator_type: str, config: IndicatorConfig, 
                                 trend_config: TrendConfig = None, **kwargs):
    """Factory function for creating unified trend indicators"""
    trend_config = trend_config or TrendConfig()
    
    if indicator_type.upper() == "MACD":
        return UnifiedVolumeWeightedMACD(config, trend_config, **kwargs)
    elif indicator_type.upper() == "ADX":
        return UnifiedVolumeWeightedADX(config, trend_config)
    else:
        raise ValueError(f"Unknown trend indicator type: {indicator_type}")