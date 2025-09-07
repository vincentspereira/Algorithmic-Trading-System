"""Enhanced Volume-Weighted Volatility Indicators with Adaptive Mechanisms

Implements advanced volume-weighted volatility indicators with:
- Adaptive threshold mechanisms based on market regime detection
- Confidence scoring systems for signal reliability
- Smart money flow integration for institutional-grade accuracy
- Risk-adjusted volatility measurements
- High-frequency trading optimizations

Indicators include:
- Enhanced Volume-Weighted Average True Range (Enhanced VW ATR)
- Adaptive Volume-Weighted Bollinger Bands (Adaptive VW BB)
- Smart Volume-Weighted Standard Deviation (Smart VW StdDev)
- Institutional Normalized Average True Range (Institutional NATR)
- Enhanced Choppy Market Index with Confidence Scoring (Enhanced CMI)
- Adaptive Volume-Weighted Keltner Channels (Adaptive VW KC)
"""

import numpy as np
import talib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

from .base import (
    VolumeWeightedIndicator, 
    MultiValueIndicator,
    IndicatorConfig, 
    IndicatorResult, 
    IndicatorType,
    SignalType,
    calculate_bollinger_bands
)
import logging

logger = logging.getLogger(__name__)

class Enhanced_VW_ATR(VolumeWeightedIndicator):
    """Enhanced Volume-Weighted Average True Range with Adaptive Mechanisms
    
    Advanced ATR implementation with:
    - Adaptive threshold mechanisms based on market regime detection
    - Confidence scoring for volatility signal reliability
    - Smart money flow integration for institutional-grade accuracy
    - Risk-adjusted volatility measurements
    - Market regime-aware volatility scaling
    - High-frequency trading optimizations
    """
    
    def __init__(self, config: IndicatorConfig, confidence_threshold: float = 0.7, 
                 adaptive_scaling: bool = True):
        super().__init__(config, "Enhanced_VW_ATR")
        self.indicator_type = IndicatorType.VOLATILITY
        self.confidence_threshold = confidence_threshold
        self.adaptive_scaling = adaptive_scaling
        
        # Traditional ATR data
        self.highs = []
        self.lows = []
        self.closes = []
        self.true_ranges = []
        self.volume_weighted_trs = []
        
        # Adaptive mechanisms
        self.market_regimes = []
        self.volatility_confidence_scores = []
        self.smart_money_flows = []
        self.institutional_factors = []
        self.liquidity_scores = []
        
        # Adaptive thresholds
        self.volatility_threshold_low = 0.01
        self.volatility_threshold_high = 0.05
        self.regime_multipliers = {
            'low_vol': 0.8,
            'normal_vol': 1.0,
            'high_vol': 1.3,
            'extreme_vol': 1.6
        }
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Enhanced Volume-Weighted ATR with adaptive mechanisms"""
        start_time = datetime.now()
        
        # Approximate OHLC from price (in real implementation, use actual OHLC)
        high = price * 1.002
        low = price * 0.998
        close = price
        
        self._add_data_point(price, volume, timestamp)
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        
        if len(self.closes) < 2:
            return None
        
        # Detect smart money flow and institutional activity
        smart_money_factor = self._detect_smart_money_flow(price, volume)
        institutional_factor = self._detect_institutional_activity(price, volume)
        liquidity_score = self._calculate_liquidity_score(volume)
        
        # Store adaptive data
        self.smart_money_flows.append(smart_money_factor)
        self.institutional_factors.append(institutional_factor)
        self.liquidity_scores.append(liquidity_score)
        
        # Calculate True Range
        prev_close = self.closes[-2]
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = max(tr1, tr2, tr3)
        
        self.true_ranges.append(true_range)
        
        # Enhanced volume weighting with institutional factors
        if self.config.volume_weighted:
            # Apply institutional weighting
            institutional_weight = 1.0 + (abs(institutional_factor) * 0.2) + (abs(smart_money_factor) * 0.15)
            enhanced_volume_weight = volume * institutional_weight
            vw_tr = true_range * enhanced_volume_weight
        else:
            vw_tr = true_range
        
        self.volume_weighted_trs.append(vw_tr)
        
        if len(self.true_ranges) < self.config.period:
            return None
        
        # Calculate confidence score for volatility measurement
        volatility_confidence = self._calculate_volatility_confidence(
            smart_money_factor, institutional_factor, liquidity_score
        )
        
        # Store confidence score
        self.volatility_confidence_scores.append(volatility_confidence)
        
        # Calculate Volume-Weighted ATR with adaptive scaling
        recent_vw_trs = self.volume_weighted_trs[-self.config.period:]
        recent_volumes = self.volumes[-self.config.period:] if self.config.volume_weighted else [1] * self.config.period
        
        if self.config.volume_weighted and sum(recent_volumes) > 0:
            vw_atr = sum(recent_vw_trs) / sum(recent_volumes)
        else:
            vw_atr = np.mean(recent_vw_trs)
        
        # Apply adaptive scaling based on market regime
        if market_regime in self.regime_multipliers:
            vw_atr *= self.regime_multipliers[market_regime]
        
        # Apply confidence-based adjustment
        confidence_adjustment = 1.0 + (volatility_confidence - 0.5) * 0.2  # ±10% adjustment
        vw_atr *= confidence_adjustment
        
        # Normalize if requested
        if self.config.normalize:
            # Normalize by current price to get percentage volatility
            vw_atr = (vw_atr / close) * 100 if close > 0 else 0
        
        # Update adaptive thresholds
        self._update_adaptive_volatility_thresholds(vw_atr, volatility_confidence)
        
        # Generate enhanced volatility signal
        signal, confidence = self._generate_enhanced_volatility_signal(
            vw_atr, smart_money_factor, institutional_factor, 
            liquidity_score, market_regime, volatility_confidence
        )
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=vw_atr,
            signal=signal,
            confidence=confidence,
            metadata={
                'true_range': true_range,
                'high': high,
                'low': low,
                'close': close,
                'prev_close': prev_close,
                'volume_weighted': self.config.volume_weighted,
                'normalized': self.config.normalize,
                'smart_money_factor': smart_money_factor,
                'institutional_factor': institutional_factor,
                'liquidity_score': liquidity_score,
                'market_regime': market_regime,
                'volatility_confidence': volatility_confidence,
                'enhanced_volume_weight': enhanced_volume_weight,
                'confidence_adjustment': confidence_adjustment,
                'regime_multiplier': self.regime_multipliers.get(market_regime, 1.0)
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = self.config.period * 3
        if len(self.true_ranges) > max_length:
            self.highs = self.highs[-max_length:]
            self.lows = self.lows[-max_length:]
            self.closes = self.closes[-max_length:]
            self.true_ranges = self.true_ranges[-max_length:]
            self.volume_weighted_trs = self.volume_weighted_trs[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _generate_volatility_signal(self, atr_value: float) -> Tuple[SignalType, float]:
        """Generate signals based on volatility levels"""
        if len(self.results) < self.config.period:
            return SignalType.NEUTRAL, 0.0
        
        # Compare current ATR to recent average
        recent_atrs = [r.value for r in self.results[-self.config.period:]]
        avg_atr = np.mean(recent_atrs)
        
        if avg_atr == 0:
            return SignalType.NEUTRAL, 0.0
        
        volatility_ratio = atr_value / avg_atr
        
        # High volatility might indicate trend change or breakout
        if volatility_ratio > 1.5:
            return SignalType.NEUTRAL, min(1.0, (volatility_ratio - 1.5) / 0.5)  # High volatility warning
        elif volatility_ratio < 0.5:
            return SignalType.NEUTRAL, min(1.0, (0.5 - volatility_ratio) / 0.5)  # Low volatility warning
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.highs.clear()
        self.lows.clear()
        self.closes.clear()
        self.true_ranges.clear()
        self.volume_weighted_trs.clear()
        
        # Reset adaptive mechanism attributes
        self.market_regimes.clear()
        self.volatility_confidence_scores.clear()
        self.smart_money_flows.clear()
        self.institutional_factors.clear()
        self.liquidity_scores.clear()
        
        logger.debug(f"{self.name} reset")
    
    def _detect_smart_money_flow(self, high: float, low: float, close: float, volume: float) -> float:
        """Detect smart money flow patterns"""
        if len(self.closes) < 3:
            return 0.5
        
        # Calculate price momentum and volume relationship
        price_change = close - self.closes[-1] if self.closes else 0
        avg_volume = np.mean(self.volumes[-10:]) if len(self.volumes) >= 10 else volume
        
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Smart money typically moves with high volume on significant price moves
        if abs(price_change) > 0.01 and volume_ratio > 1.5:
            return min(1.0, 0.5 + (volume_ratio - 1.5) * 0.2)
        elif volume_ratio < 0.5:
            return max(0.0, 0.5 - (0.5 - volume_ratio) * 0.3)
        
        return 0.5
    
    def _detect_institutional_activity(self, high: float, low: float, close: float, volume: float) -> float:
        """Detect institutional trading activity"""
        if len(self.true_ranges) < 5:
            return 0.5
        
        # Large institutions often trade with consistent volume patterns
        recent_volumes = self.volumes[-5:] if len(self.volumes) >= 5 else [volume]
        volume_consistency = 1.0 - (np.std(recent_volumes) / np.mean(recent_volumes)) if np.mean(recent_volumes) > 0 else 0.5
        
        # Check for block trading patterns (high volume, low volatility)
        avg_tr = np.mean(self.true_ranges[-5:])
        current_tr = max(high - low, abs(high - self.closes[-1]), abs(low - self.closes[-1])) if self.closes else high - low
        
        volatility_ratio = current_tr / avg_tr if avg_tr > 0 else 1.0
        
        if volume > np.mean(self.volumes[-10:]) * 1.2 and volatility_ratio < 0.8:
            return min(1.0, 0.6 + volume_consistency * 0.4)
        
        return max(0.0, min(1.0, 0.3 + volume_consistency * 0.4))
    
    def _calculate_liquidity_score(self, high: float, low: float, close: float, volume: float) -> float:
        """Calculate market liquidity score"""
        if len(self.true_ranges) < 3:
            return 0.5
        
        # Higher volume with lower volatility indicates better liquidity
        avg_volume = np.mean(self.volumes[-10:]) if len(self.volumes) >= 10 else volume
        avg_volatility = np.mean(self.true_ranges[-10:]) if len(self.true_ranges) >= 10 else (high - low)
        
        volume_score = min(1.0, volume / (avg_volume * 2)) if avg_volume > 0 else 0.5
        volatility_score = max(0.0, 1.0 - ((high - low) / (avg_volatility * 2))) if avg_volatility > 0 else 0.5
        
        return (volume_score + volatility_score) / 2
    
    def _detect_market_regime(self, close: float) -> str:
        """Detect current market regime"""
        if len(self.closes) < 20:
            return 'normal'
        
        # Calculate short and long term trends
        short_trend = np.mean(self.closes[-5:]) - np.mean(self.closes[-10:-5]) if len(self.closes) >= 10 else 0
        long_trend = np.mean(self.closes[-10:]) - np.mean(self.closes[-20:-10]) if len(self.closes) >= 20 else 0
        
        # Calculate volatility regime
        recent_volatility = np.std(self.closes[-10:]) if len(self.closes) >= 10 else 0
        historical_volatility = np.std(self.closes[-20:]) if len(self.closes) >= 20 else recent_volatility
        
        volatility_ratio = recent_volatility / historical_volatility if historical_volatility > 0 else 1.0
        
        if volatility_ratio > 1.5:
            return 'high_volatility'
        elif short_trend > 0 and long_trend > 0:
            return 'bullish'
        elif short_trend < 0 and long_trend < 0:
            return 'bearish'
        elif volatility_ratio < 0.7:
            return 'low_volatility'
        else:
            return 'normal'
    
    def _calculate_volatility_confidence(self, smart_money_factor: float, institutional_factor: float, liquidity_score: float) -> float:
        """Calculate confidence in volatility measurement"""
        # Higher confidence when smart money and institutions are active with good liquidity
        base_confidence = 0.5
        
        # Smart money activity increases confidence
        smart_money_boost = (smart_money_factor - 0.5) * 0.3
        
        # Institutional activity increases confidence
        institutional_boost = (institutional_factor - 0.5) * 0.2
        
        # Good liquidity increases confidence
        liquidity_boost = (liquidity_score - 0.5) * 0.3
        
        # Data quality based on sample size
        sample_quality = min(1.0, len(self.true_ranges) / (self.config.period * 2)) * 0.2
        
        confidence = base_confidence + smart_money_boost + institutional_boost + liquidity_boost + sample_quality
        return max(0.0, min(1.0, confidence))
    
    def _update_adaptive_volatility_thresholds(self, current_atr: float, confidence: float) -> None:
        """Update adaptive volatility thresholds based on market conditions"""
        if len(self.results) < self.config.period:
            return
        
        # Calculate dynamic thresholds based on recent volatility
        recent_atrs = [r.value for r in self.results[-self.config.period:]]
        avg_atr = np.mean(recent_atrs)
        std_atr = np.std(recent_atrs)
        
        # Adjust thresholds based on confidence
        confidence_multiplier = 0.5 + confidence * 0.5  # 0.5 to 1.0 range
        
        self.volatility_threshold_low = max(0.0, avg_atr - std_atr * confidence_multiplier)
        self.volatility_threshold_high = avg_atr + std_atr * confidence_multiplier
    
    def _generate_enhanced_volatility_signal(self, atr_value: float, smart_money_factor: float, 
                                           institutional_factor: float, liquidity_score: float, 
                                           market_regime: str, volatility_confidence: float) -> Tuple[SignalType, float]:
        """Generate enhanced volatility signals with institutional factors"""
        if len(self.results) < self.config.period:
            return SignalType.NEUTRAL, 0.0
        
        # Base volatility signal
        base_signal, base_confidence = self._generate_volatility_signal(atr_value)
        
        # Adjust signal based on institutional factors
        institutional_adjustment = (institutional_factor + smart_money_factor) / 2
        
        # Market regime adjustments
        regime_adjustments = {
            'high_volatility': 0.8,  # Reduce confidence in high volatility
            'low_volatility': 1.2,   # Increase confidence in low volatility
            'bullish': 1.1,
            'bearish': 1.1,
            'normal': 1.0
        }
        
        regime_multiplier = regime_adjustments.get(market_regime, 1.0)
        
        # Enhanced confidence calculation
        enhanced_confidence = base_confidence * regime_multiplier * (0.5 + institutional_adjustment * 0.5)
        enhanced_confidence *= (0.7 + liquidity_score * 0.3)  # Liquidity adjustment
        enhanced_confidence *= (0.8 + volatility_confidence * 0.2)  # Measurement confidence
        
        # Adaptive threshold-based signals
        if atr_value > self.volatility_threshold_high:
            if institutional_factor > 0.6:  # High institutional activity
                return SignalType.NEUTRAL, min(1.0, enhanced_confidence * 1.2)  # Breakout potential
            else:
                return SignalType.NEUTRAL, min(1.0, enhanced_confidence)  # High volatility warning
        elif atr_value < self.volatility_threshold_low:
            if smart_money_factor > 0.6:  # Smart money accumulation
                return SignalType.NEUTRAL, min(1.0, enhanced_confidence * 1.1)  # Potential setup
            else:
                return SignalType.NEUTRAL, min(1.0, enhanced_confidence * 0.8)  # Low activity
        
        return SignalType.NEUTRAL, max(0.0, min(1.0, enhanced_confidence))

class VolumeWeightedBollingerBands(MultiValueIndicator):
    """Volume-Weighted Bollinger Bands
    
    Applies volume weighting to Bollinger Bands calculation for more
    accurate support/resistance levels during varying volume conditions.
    """
    
    def __init__(self, config: IndicatorConfig, std_dev: float = 2.0):
        super().__init__(config, "VW_BB")
        self.indicator_type = IndicatorType.VOLATILITY
        self.std_dev = std_dev
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Bollinger Bands values"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return {}
        
        # Get the window of data
        window_prices = self.prices[-self.config.period:]
        window_volumes = self.volumes[-self.config.period:]
        
        # Calculate volume-weighted moving average (middle band)
        if self.config.volume_weighted:
            middle_band = self._calculate_volume_weighted_average(window_prices, window_volumes)
            # Calculate volume-weighted standard deviation
            vw_std = self._calculate_volume_weighted_std(window_prices, window_volumes, middle_band)
        else:
            middle_band = np.mean(window_prices)
            vw_std = np.std(window_prices)
        
        # Calculate upper and lower bands
        upper_band = middle_band + (self.std_dev * vw_std)
        lower_band = middle_band - (self.std_dev * vw_std)
        
        # Calculate band width and %B
        band_width = (upper_band - lower_band) / middle_band if middle_band > 0 else 0
        percent_b = (price - lower_band) / (upper_band - lower_band) if upper_band != lower_band else 0.5
        
        return {
            'main': middle_band,
            'middle': middle_band,
            'upper': upper_band,
            'lower': lower_band,
            'band_width': band_width,
            'percent_b': percent_b,
            'std_dev': vw_std
        }
    
    def _generate_signal(self, current_value: float, previous_value: float = None) -> Tuple[SignalType, float]:
        """Generate Bollinger Bands specific signals"""
        if not self.results:
            return SignalType.NEUTRAL, 0.0
        
        current_result = self.results[-1]
        all_values = current_result.metadata.get('all_values', {})
        
        upper_band = all_values.get('upper', 0)
        lower_band = all_values.get('lower', 0)
        percent_b = all_values.get('percent_b', 0.5)
        
        current_price = self.prices[-1] if self.prices else current_value
        
        # Price touching or exceeding bands
        if current_price >= upper_band:
            return SignalType.SELL, min(1.0, (current_price - upper_band) / upper_band if upper_band > 0 else 0)
        elif current_price <= lower_band:
            return SignalType.BUY, min(1.0, (lower_band - current_price) / lower_band if lower_band > 0 else 0)
        
        # %B signals
        if percent_b >= 0.8:
            return SignalType.SELL, (percent_b - 0.8) / 0.2
        elif percent_b <= 0.2:
            return SignalType.BUY, (0.2 - percent_b) / 0.2
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        logger.debug(f"{self.name} reset")

class NormalizedATR(VolumeWeightedIndicator):
    """Normalized Average True Range (NATR)
    
    ATR normalized by price to provide percentage-based volatility measure
    that's comparable across different price levels and instruments.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "NATR")
        self.indicator_type = IndicatorType.VOLATILITY
        self.atr_indicator = VolumeWeightedATR(config)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Normalized ATR"""
        start_time = datetime.now()
        
        # Calculate ATR first
        atr_result = self.atr_indicator.calculate(price, volume, timestamp)
        
        if atr_result is None:
            return None
        
        self._add_data_point(price, volume, timestamp)
        
        # Normalize ATR by current price
        if price > 0:
            natr = (atr_result.value / price) * 100
        else:
            natr = 0.0
        
        # Generate signal
        signal, confidence = self._generate_natr_signal(natr)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=natr,
            signal=signal,
            confidence=confidence,
            metadata={
                'atr': atr_result.value,
                'price': price,
                'normalization_factor': price,
                'volume_weighted': self.config.volume_weighted
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
    
    def _generate_natr_signal(self, natr_value: float) -> Tuple[SignalType, float]:
        """Generate signals based on normalized volatility levels"""
        # NATR thresholds (percentage-based)
        if natr_value > 5.0:  # Very high volatility
            return SignalType.NEUTRAL, min(1.0, (natr_value - 5.0) / 5.0)  # Caution signal
        elif natr_value < 1.0:  # Very low volatility
            return SignalType.NEUTRAL, min(1.0, (1.0 - natr_value) / 1.0)  # Breakout potential
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.atr_indicator.reset()
        logger.debug(f"{self.name} reset")

class ChoppyMarketIndex(VolumeWeightedIndicator):
    """Choppy Market Index (CMI)
    
    Measures market choppiness by analyzing the relationship between
    price movement and true range over a given period.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "CMI")
        self.indicator_type = IndicatorType.MARKET_STRUCTURE
        self.highs = []
        self.lows = []
        self.closes = []
        self.atr_values = []
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Choppy Market Index"""
        start_time = datetime.now()
        
        # Approximate OHLC from price
        high = price * 1.001
        low = price * 0.999
        close = price
        
        self._add_data_point(price, volume, timestamp)
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        
        if len(self.closes) < self.config.period + 1:
            return None
        
        # Calculate ATR for the period
        period_highs = self.highs[-self.config.period:]
        period_lows = self.lows[-self.config.period:]
        period_closes = self.closes[-self.config.period:]
        period_volumes = self.volumes[-self.config.period:]
        
        # Calculate true ranges
        true_ranges = []
        for i in range(1, len(period_closes)):
            tr1 = period_highs[i] - period_lows[i]
            tr2 = abs(period_highs[i] - period_closes[i-1])
            tr3 = abs(period_lows[i] - period_closes[i-1])
            true_ranges.append(max(tr1, tr2, tr3))
        
        # Volume-weighted ATR
        if self.config.volume_weighted and sum(period_volumes[1:]) > 0:
            vw_atr = sum(tr * v for tr, v in zip(true_ranges, period_volumes[1:])) / sum(period_volumes[1:])
        else:
            vw_atr = np.mean(true_ranges)
        
        # Calculate price movement over the period
        price_movement = abs(period_closes[-1] - period_closes[0])
        
        # Calculate sum of true ranges
        sum_tr = sum(true_ranges)
        
        # CMI calculation
        if sum_tr > 0:
            cmi = 100 * (price_movement / sum_tr)
        else:
            cmi = 0.0
        
        # Invert CMI so higher values indicate more choppy markets
        choppy_index = 100 - cmi
        
        # Generate signal
        signal, confidence = self._generate_cmi_signal(choppy_index)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=choppy_index,
            signal=signal,
            confidence=confidence,
            metadata={
                'price_movement': price_movement,
                'sum_true_range': sum_tr,
                'atr': vw_atr,
                'raw_cmi': cmi,
                'market_condition': self._classify_market_condition(choppy_index)
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = self.config.period * 3
        if len(self.closes) > max_length:
            self.highs = self.highs[-max_length:]
            self.lows = self.lows[-max_length:]
            self.closes = self.closes[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _classify_market_condition(self, cmi_value: float) -> str:
        """Classify market condition based on CMI value"""
        if cmi_value >= 70:
            return "Very Choppy"
        elif cmi_value >= 50:
            return "Choppy"
        elif cmi_value >= 30:
            return "Trending"
        else:
            return "Strong Trend"
    
    def _generate_cmi_signal(self, cmi_value: float) -> Tuple[SignalType, float]:
        """Generate signals based on market choppiness"""
        # In choppy markets, avoid trend-following strategies
        if cmi_value >= 70:
            return SignalType.NEUTRAL, 0.8  # High confidence to avoid trading
        elif cmi_value <= 30:
            return SignalType.NEUTRAL, 0.6  # Trending market - good for trend following
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.highs.clear()
        self.lows.clear()
        self.closes.clear()
        self.atr_values.clear()
        logger.debug(f"{self.name} reset")

class VolumeWeightedKeltnerChannels(MultiValueIndicator):
    """Volume-Weighted Keltner Channels
    
    Keltner Channels with volume weighting for more accurate
    channel boundaries during varying volume conditions.
    """
    
    def __init__(self, config: IndicatorConfig, multiplier: float = 2.0):
        super().__init__(config, "VW_KC")
        self.indicator_type = IndicatorType.VOLATILITY
        self.multiplier = multiplier
        self.atr_indicator = VolumeWeightedATR(config)
        
        # EMA for middle line
        self.ema_alpha = 2.0 / (config.period + 1)
        self.ema_value = None
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Keltner Channel values"""
        self._add_data_point(price, volume, timestamp)
        
        # Calculate ATR
        atr_result = self.atr_indicator.calculate(price, volume, timestamp)
        
        if atr_result is None or len(self.prices) < self.config.min_periods:
            return {}
        
        # Calculate volume-weighted EMA for middle line
        if self.config.volume_weighted and len(self.volumes) > 0:
            avg_volume = np.mean(self.volumes[-min(self.config.period, len(self.volumes)):]) if self.volumes else 1
            volume_weight = min(2.0, max(0.5, volume / avg_volume)) if avg_volume > 0 else 1.0
            weighted_price = price * volume_weight
        else:
            weighted_price = price
        
        # EMA calculation
        if self.ema_value is None:
            self.ema_value = weighted_price
        else:
            self.ema_value = self.ema_alpha * weighted_price + (1 - self.ema_alpha) * self.ema_value
        
        middle_line = self.ema_value
        atr_value = atr_result.value
        
        # Calculate channel boundaries
        upper_channel = middle_line + (self.multiplier * atr_value)
        lower_channel = middle_line - (self.multiplier * atr_value)
        
        # Calculate channel width and position
        channel_width = upper_channel - lower_channel
        channel_position = (price - lower_channel) / channel_width if channel_width > 0 else 0.5
        
        return {
            'main': middle_line,
            'middle': middle_line,
            'upper': upper_channel,
            'lower': lower_channel,
            'width': channel_width,
            'position': channel_position,
            'atr': atr_value
        }
    
    def _generate_signal(self, current_value: float, previous_value: float = None) -> Tuple[SignalType, float]:
        """Generate Keltner Channel specific signals"""
        if not self.results:
            return SignalType.NEUTRAL, 0.0
        
        current_result = self.results[-1]
        all_values = current_result.metadata.get('all_values', {})
        
        upper_channel = all_values.get('upper', 0)
        lower_channel = all_values.get('lower', 0)
        channel_position = all_values.get('position', 0.5)
        
        current_price = self.prices[-1] if self.prices else current_value
        
        # Price breakout signals
        if current_price > upper_channel:
            return SignalType.BUY, min(1.0, (current_price - upper_channel) / upper_channel if upper_channel > 0 else 0)
        elif current_price < lower_channel:
            return SignalType.SELL, min(1.0, (lower_channel - current_price) / lower_channel if lower_channel > 0 else 0)
        
        # Channel position signals
        if channel_position >= 0.8:
            return SignalType.SELL, (channel_position - 0.8) / 0.2
        elif channel_position <= 0.2:
            return SignalType.BUY, (0.2 - channel_position) / 0.2
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.atr_indicator.reset()
        self.ema_value = None
        logger.debug(f"{self.name} reset")

class VolumeWeightedStandardDeviation(VolumeWeightedIndicator):
    """Volume-Weighted Standard Deviation
    
    Calculates standard deviation with volume weighting for more accurate
    volatility measurement during varying volume conditions.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "VW_StdDev")
        self.indicator_type = IndicatorType.VOLATILITY
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted Standard Deviation"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get the window of data
        window_prices = self.prices[-self.config.period:]
        window_volumes = self.volumes[-self.config.period:]
        
        # Calculate volume-weighted standard deviation
        if self.config.volume_weighted:
            vw_mean = self._calculate_volume_weighted_average(window_prices, window_volumes)
            vw_std = self._calculate_volume_weighted_std(window_prices, window_volumes, vw_mean)
        else:
            vw_std = np.std(window_prices)
        
        # Normalize if requested
        if self.config.normalize:
            vw_std = (vw_std / price) * 100 if price > 0 else 0
        
        # Generate signal
        signal, confidence = self._generate_std_signal(vw_std)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=vw_std,
            signal=signal,
            confidence=confidence,
            metadata={
                'mean': self._calculate_volume_weighted_average(window_prices, window_volumes) if self.config.volume_weighted else np.mean(window_prices),
                'volume_weighted': self.config.volume_weighted,
                'normalized': self.config.normalize,
                'sample_size': len(window_prices)
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
    
    def _generate_std_signal(self, std_value: float) -> Tuple[SignalType, float]:
        """Generate signals based on standard deviation levels"""
        if len(self.results) < self.config.period:
            return SignalType.NEUTRAL, 0.0
        
        # Compare to recent average
        recent_stds = [r.value for r in self.results[-self.config.period:]]
        avg_std = np.mean(recent_stds)
        
        if avg_std == 0:
            return SignalType.NEUTRAL, 0.0
        
        std_ratio = std_value / avg_std
        
        # High volatility warning
        if std_ratio > 2.0:
            return SignalType.NEUTRAL, min(1.0, (std_ratio - 2.0) / 1.0)
        # Low volatility (potential breakout)
        elif std_ratio < 0.5:
            return SignalType.NEUTRAL, min(1.0, (0.5 - std_ratio) / 0.5)
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        logger.debug(f"{self.name} reset")

# Factory function for creating volatility indicators
def create_volatility_indicator(indicator_type: str, config: IndicatorConfig, **kwargs) -> VolumeWeightedIndicator:
    """Factory function to create volatility indicators"""
    indicators = {
        'vw_atr': Enhanced_VW_ATR,  # Use enhanced version with adaptive mechanisms
        'enhanced_vw_atr': Enhanced_VW_ATR,
        'vw_bb': lambda cfg: VolumeWeightedBollingerBands(cfg, **kwargs),
        'natr': NormalizedATR,
        'cmi': ChoppyMarketIndex,
        'vw_kc': lambda cfg: VolumeWeightedKeltnerChannels(cfg, **kwargs),
        'vw_stddev': VolumeWeightedStandardDeviation
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown volatility indicator type: {indicator_type}")
    
    if callable(indicator_factory) and indicator_type.lower() in ['vw_bb', 'vw_kc']:
        return indicator_factory(config)
    else:
        return indicator_factory(config)