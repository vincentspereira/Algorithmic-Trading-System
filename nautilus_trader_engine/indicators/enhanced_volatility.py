"""Enhanced Volume-Weighted Volatility Indicators

Implements sophisticated volume-weighted volatility indicators including:
- Volume-Weighted ATR with adaptive smoothing
- Volume-Weighted Bollinger Bands with dynamic bands
- Normalized ATR with price adjustment
- Choppy Market Index for trend/range detection
- Volume-Weighted Keltner Channels
- Volume-Weighted Standard Deviation
- Advanced volatility analysis and market condition detection
"""

import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import deque
from enum import Enum

from .enhanced_base import (
    EnhancedVolumeWeightedIndicator,
    IndicatorConfig,
    IndicatorResult,
    IndicatorType,
    SignalType
)
from utils.logging_config import get_logger

logger = get_logger(__name__)

class MarketCondition(Enum):
    """Market condition classification"""
    TRENDING = "trending"
    CHOPPY = "choppy"
    VOLATILE = "volatile"
    CALM = "calm"
    BREAKOUT = "breakout"

class EnhancedVolumeWeightedATR(EnhancedVolumeWeightedIndicator):
    """Enhanced Volume-Weighted Average True Range
    
    Advanced ATR implementation with volume weighting, adaptive smoothing,
    and comprehensive volatility analysis.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "Enhanced_VW_ATR")
        self.indicator_type = IndicatorType.VOLATILITY
        
        # True Range components
        self.true_ranges = deque(maxlen=config.period * 3)
        self.volume_weighted_trs = deque(maxlen=config.period * 3)
        self.previous_close = None
        
        # ATR smoothing
        self.atr_value = None
        self.adaptive_smoothing = config.adaptive_parameters
        
        # Volatility analysis
        self.volatility_percentiles = deque(maxlen=100)  # For percentile calculation
        self.volatility_spikes = deque(maxlen=20)  # Track volatility spikes
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime,
                       high: float = None, low: float = None) -> Dict[str, float]:
        """Calculate Enhanced Volume-Weighted ATR"""
        self._add_data_point(price, volume, timestamp)
        
        # Use price as high/low if not provided
        if high is None:
            high = price * 1.001
        if low is None:
            low = price * 0.999
        
        close = price
        
        # Calculate True Range
        if self.previous_close is not None:
            tr1 = high - low
            tr2 = abs(high - self.previous_close)
            tr3 = abs(low - self.previous_close)
            true_range = max(tr1, tr2, tr3)
        else:
            true_range = high - low
        
        self.previous_close = close
        self.true_ranges.append(true_range)
        
        # Apply volume weighting
        if self.config.volume_weighted and len(self.volumes) > 1:
            avg_volume = np.mean(list(self.volumes)[-min(20, len(self.volumes)):]) if self.volumes else 1
            volume_weight = min(3.0, max(0.3, volume / avg_volume)) if avg_volume > 0 else 1.0
            volume_weighted_tr = true_range * volume_weight
        else:
            volume_weight = 1.0
            volume_weighted_tr = true_range
        
        self.volume_weighted_trs.append(volume_weighted_tr)
        
        if len(self.volume_weighted_trs) < self.config.period:
            return {'atr': true_range, 'normalized_atr': 0.0, 'volatility_percentile': 50.0}
        
        # Calculate ATR with adaptive smoothing
        if self.atr_value is None:
            self.atr_value = np.mean(list(self.volume_weighted_trs)[-self.config.period:])
        else:
            # Adaptive smoothing factor based on volatility
            if self.adaptive_smoothing:
                volatility = self._calculate_volatility()
                smoothing_factor = max(0.05, min(0.3, 0.1 + volatility * 0.2))
            else:
                smoothing_factor = 2.0 / (self.config.period + 1)
            
            current_tr_avg = np.mean(list(self.volume_weighted_trs)[-self.config.period:])
            self.atr_value = self.atr_value * (1 - smoothing_factor) + current_tr_avg * smoothing_factor
        
        # Calculate normalized ATR (ATR as percentage of price)
        normalized_atr = (self.atr_value / close) * 100 if close > 0 else 0
        
        # Track volatility percentiles
        self.volatility_percentiles.append(normalized_atr)
        if len(self.volatility_percentiles) >= 20:
            volatility_percentile = (np.searchsorted(sorted(self.volatility_percentiles), normalized_atr) / 
                                   len(self.volatility_percentiles)) * 100
        else:
            volatility_percentile = 50.0
        
        # Detect volatility spikes
        volatility_spike = self._detect_volatility_spike(normalized_atr)
        
        # Market condition analysis
        market_condition = self._analyze_market_condition(normalized_atr, volatility_percentile)
        
        return {
            'atr': self.atr_value,
            'normalized_atr': normalized_atr,
            'volatility_percentile': volatility_percentile,
            'volatility_spike': volatility_spike,
            'market_condition': market_condition.value,
            'true_range': true_range,
            'volume_weight': volume_weight,
            'smoothing_factor': smoothing_factor if self.adaptive_smoothing else 2.0 / (self.config.period + 1)
        }
    
    def _generate_signal(self, current_values: Dict[str, float], 
                        previous_values: Dict[str, float] = None) -> Tuple[SignalType, float]:
        """Generate volatility-based signals"""
        normalized_atr = current_values['normalized_atr']
        volatility_percentile = current_values['volatility_percentile']
        volatility_spike = current_values['volatility_spike']
        market_condition = current_values['market_condition']
        
        # Volatility breakout signals
        if volatility_spike and volatility_percentile > 80:
            # High volatility spike suggests potential breakout
            return SignalType.NEUTRAL, min(1.0, volatility_percentile / 100)  # Neutral but high confidence
        
        # Market condition based signals
        if market_condition == MarketCondition.BREAKOUT.value:
            return SignalType.NEUTRAL, 0.8  # Breakout detected, direction unclear
        elif market_condition == MarketCondition.CALM.value and volatility_percentile < 20:
            return SignalType.NEUTRAL, 0.3  # Low volatility, potential for movement
        
        # Volatility expansion/contraction
        if previous_values:
            prev_normalized_atr = previous_values['normalized_atr']
            atr_change = (normalized_atr - prev_normalized_atr) / prev_normalized_atr if prev_normalized_atr > 0 else 0
            
            if atr_change > 0.5:  # 50% increase in volatility
                return SignalType.NEUTRAL, min(0.7, atr_change)
        
        return SignalType.NEUTRAL, 0.0
    
    def _detect_volatility_spike(self, current_natr: float) -> bool:
        """Detect volatility spikes"""
        if len(self.volatility_percentiles) < 10:
            return False
        
        recent_avg = np.mean(list(self.volatility_percentiles)[-10:])
        return current_natr > recent_avg * 2.0  # Spike if 2x recent average
    
    def _analyze_market_condition(self, normalized_atr: float, percentile: float) -> MarketCondition:
        """Analyze current market condition based on volatility"""
        if percentile > 90:
            return MarketCondition.VOLATILE
        elif percentile > 75 and len(self.results) > 0:
            # Check for breakout pattern
            prev_percentile = self.results[-1].metadata.get('all_values', {}).get('volatility_percentile', 50)
            if percentile > prev_percentile * 1.5:
                return MarketCondition.BREAKOUT
            return MarketCondition.VOLATILE
        elif percentile < 25:
            return MarketCondition.CALM
        elif self._is_choppy_market():
            return MarketCondition.CHOPPY
        else:
            return MarketCondition.TRENDING
    
    def _is_choppy_market(self) -> bool:
        """Detect choppy market conditions"""
        if len(self.results) < 10:
            return False
        
        # Check for high volatility with low directional movement
        recent_prices = [r.value for r in self.results[-10:]]
        price_range = max(recent_prices) - min(recent_prices)
        total_movement = sum(abs(recent_prices[i] - recent_prices[i-1]) for i in range(1, len(recent_prices)))
        
        # Choppy if total movement is much larger than net movement
        return total_movement > price_range * 3

class EnhancedVolumeWeightedBollingerBands(EnhancedVolumeWeightedIndicator):
    """Enhanced Volume-Weighted Bollinger Bands
    
    Advanced Bollinger Bands with volume weighting, dynamic band adjustment,
    and sophisticated squeeze/expansion detection.
    """
    
    def __init__(self, config: IndicatorConfig, std_dev_multiplier: float = 2.0):
        super().__init__(config, "Enhanced_VW_BollingerBands")
        self.indicator_type = IndicatorType.VOLATILITY
        
        self.std_dev_multiplier = std_dev_multiplier
        
        # Band calculation components
        self.sma_values = deque(maxlen=config.period * 2)
        self.band_widths = deque(maxlen=50)  # Track band width history
        
        # Squeeze detection
        self.squeeze_threshold = 0.1  # 10% of average band width
        self.expansion_threshold = 2.0  # 200% of average band width
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Enhanced Volume-Weighted Bollinger Bands"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return {
                'middle_band': price, 'upper_band': price, 'lower_band': price,
                'band_width': 0.0, 'percent_b': 0.5, 'squeeze_detected': False
            }
        
        # Calculate volume-weighted moving average (middle band)
        if self.config.volume_weighted:
            recent_prices = list(self.prices)[-self.config.period:]
            recent_volumes = list(self.volumes)[-self.config.period:]
            
            if sum(recent_volumes) > 0:
                middle_band = sum(p * v for p, v in zip(recent_prices, recent_volumes)) / sum(recent_volumes)
            else:
                middle_band = np.mean(recent_prices)
        else:
            middle_band = np.mean(list(self.prices)[-self.config.period:])
        
        self.sma_values.append(middle_band)
        
        # Calculate volume-weighted standard deviation
        recent_prices = list(self.prices)[-self.config.period:]
        if self.config.volume_weighted:
            recent_volumes = list(self.volumes)[-self.config.period:]
            
            # Volume-weighted variance calculation
            if sum(recent_volumes) > 0:
                weighted_variance = sum(v * (p - middle_band) ** 2 for p, v in zip(recent_prices, recent_volumes)) / sum(recent_volumes)
            else:
                weighted_variance = np.var(recent_prices)
        else:
            weighted_variance = np.var(recent_prices)
        
        std_dev = np.sqrt(weighted_variance)
        
        # Dynamic multiplier adjustment based on volatility
        if self.config.adaptive_parameters:
            volatility = self._calculate_volatility()
            dynamic_multiplier = self.std_dev_multiplier * (1 + volatility * 0.5)
        else:
            dynamic_multiplier = self.std_dev_multiplier
        
        # Calculate bands
        upper_band = middle_band + (dynamic_multiplier * std_dev)
        lower_band = middle_band - (dynamic_multiplier * std_dev)
        
        # Calculate band width and %B
        band_width = (upper_band - lower_band) / middle_band * 100 if middle_band > 0 else 0
        self.band_widths.append(band_width)
        
        if upper_band != lower_band:
            percent_b = (price - lower_band) / (upper_band - lower_band)
        else:
            percent_b = 0.5
        
        # Squeeze and expansion detection
        squeeze_detected, expansion_detected = self._detect_squeeze_expansion(band_width)
        
        # Band touch analysis
        band_touch = self._analyze_band_touch(price, upper_band, lower_band, percent_b)
        
        return {
            'middle_band': middle_band,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'band_width': band_width,
            'percent_b': percent_b,
            'squeeze_detected': squeeze_detected,
            'expansion_detected': expansion_detected,
            'band_touch': band_touch,
            'std_dev': std_dev,
            'dynamic_multiplier': dynamic_multiplier
        }
    
    def _generate_signal(self, current_values: Dict[str, float], 
                        previous_values: Dict[str, float] = None) -> Tuple[SignalType, float]:
        """Generate Bollinger Bands based signals"""
        percent_b = current_values['percent_b']
        squeeze_detected = current_values['squeeze_detected']
        expansion_detected = current_values['expansion_detected']
        band_touch = current_values['band_touch']
        
        # Squeeze breakout signals
        if squeeze_detected and previous_values:
            prev_squeeze = previous_values.get('squeeze_detected', False)
            if not prev_squeeze:  # Entering squeeze
                return SignalType.NEUTRAL, 0.6  # Prepare for breakout
        
        if expansion_detected:
            # Band expansion suggests strong move
            if percent_b > 0.8:
                return SignalType.BUY, min(1.0, (percent_b - 0.8) * 5)
            elif percent_b < 0.2:
                return SignalType.SELL, min(1.0, (0.2 - percent_b) * 5)
        
        # Band touch signals
        if band_touch == 'upper':
            return SignalType.SELL, min(0.8, max(0.3, (percent_b - 0.9) * 10))
        elif band_touch == 'lower':
            return SignalType.BUY, min(0.8, max(0.3, (0.1 - percent_b) * 10))
        
        # %B extreme signals
        if percent_b >= 1.0:
            return SignalType.SELL, min(1.0, (percent_b - 1.0) * 2 + 0.5)
        elif percent_b <= 0.0:
            return SignalType.BUY, min(1.0, abs(percent_b) * 2 + 0.5)
        
        # Mean reversion signals
        if percent_b > 0.8:
            return SignalType.SELL, min(0.6, (percent_b - 0.8) * 3)
        elif percent_b < 0.2:
            return SignalType.BUY, min(0.6, (0.2 - percent_b) * 3)
        
        return SignalType.NEUTRAL, 0.0
    
    def _detect_squeeze_expansion(self, current_width: float) -> Tuple[bool, bool]:
        """Detect squeeze and expansion conditions"""
        if len(self.band_widths) < 20:
            return False, False
        
        avg_width = np.mean(list(self.band_widths)[-20:])
        
        squeeze_detected = current_width < avg_width * self.squeeze_threshold
        expansion_detected = current_width > avg_width * self.expansion_threshold
        
        return squeeze_detected, expansion_detected
    
    def _analyze_band_touch(self, price: float, upper: float, lower: float, percent_b: float) -> str:
        """Analyze if price is touching bands"""
        tolerance = 0.02  # 2% tolerance
        
        if percent_b >= (1 - tolerance):
            return 'upper'
        elif percent_b <= tolerance:
            return 'lower'
        else:
            return 'middle'

class EnhancedNormalizedATR(EnhancedVolumeWeightedIndicator):
    """Enhanced Normalized ATR
    
    Advanced NATR implementation with price normalization and
    adaptive volatility analysis.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "Enhanced_NATR")
        self.indicator_type = IndicatorType.VOLATILITY
        
        # Use Enhanced ATR as base
        self.atr_indicator = EnhancedVolumeWeightedATR(config)
        
        # Normalization components
        self.price_levels = deque(maxlen=config.period * 2)
        self.natr_history = deque(maxlen=100)
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime,
                       high: float = None, low: float = None) -> Dict[str, float]:
        """Calculate Enhanced Normalized ATR"""
        self._add_data_point(price, volume, timestamp)
        
        # Calculate base ATR
        atr_values = self.atr_indicator.calculate_values(price, volume, timestamp, high, low)
        atr = atr_values['atr']
        
        # Store price levels for normalization
        self.price_levels.append(price)
        
        if len(self.price_levels) < self.config.period:
            return {'natr': 0.0, 'volatility_regime': 'normal', 'price_efficiency': 0.5}
        
        # Calculate different normalization methods
        current_price_natr = (atr / price) * 100 if price > 0 else 0
        
        # Average price normalization
        avg_price = np.mean(list(self.price_levels)[-self.config.period:])
        avg_price_natr = (atr / avg_price) * 100 if avg_price > 0 else 0
        
        # Median price normalization (more robust to outliers)
        median_price = np.median(list(self.price_levels)[-self.config.period:])
        median_price_natr = (atr / median_price) * 100 if median_price > 0 else 0
        
        # Use median-based NATR as primary
        natr = median_price_natr
        self.natr_history.append(natr)
        
        # Volatility regime classification
        volatility_regime = self._classify_volatility_regime(natr)
        
        # Price efficiency calculation
        price_efficiency = self._calculate_price_efficiency()
        
        return {
            'natr': natr,
            'current_price_natr': current_price_natr,
            'avg_price_natr': avg_price_natr,
            'median_price_natr': median_price_natr,
            'volatility_regime': volatility_regime,
            'price_efficiency': price_efficiency,
            'atr': atr,
            'normalization_price': median_price
        }
    
    def _generate_signal(self, current_values: Dict[str, float], 
                        previous_values: Dict[str, float] = None) -> Tuple[SignalType, float]:
        """Generate NATR-based signals"""
        natr = current_values['natr']
        volatility_regime = current_values['volatility_regime']
        price_efficiency = current_values['price_efficiency']
        
        # Volatility regime based signals
        if volatility_regime == 'high' and price_efficiency < 0.3:
            # High volatility with low efficiency suggests choppy market
            return SignalType.NEUTRAL, 0.4
        elif volatility_regime == 'low' and price_efficiency > 0.7:
            # Low volatility with high efficiency suggests potential breakout
            return SignalType.NEUTRAL, 0.6
        
        # NATR threshold signals
        if len(self.natr_history) >= 20:
            natr_percentile = (np.searchsorted(sorted(self.natr_history), natr) / len(self.natr_history)) * 100
            
            if natr_percentile > 90:
                return SignalType.NEUTRAL, min(1.0, natr_percentile / 100)  # Extreme volatility
            elif natr_percentile < 10:
                return SignalType.NEUTRAL, 0.3  # Very low volatility
        
        return SignalType.NEUTRAL, 0.0
    
    def _classify_volatility_regime(self, natr: float) -> str:
        """Classify current volatility regime"""
        if len(self.natr_history) < 20:
            return 'normal'
        
        natr_percentile = (np.searchsorted(sorted(self.natr_history), natr) / len(self.natr_history)) * 100
        
        if natr_percentile > 80:
            return 'high'
        elif natr_percentile < 20:
            return 'low'
        else:
            return 'normal'
    
    def _calculate_price_efficiency(self) -> float:
        """Calculate price movement efficiency"""
        if len(self.price_levels) < 10:
            return 0.5
        
        prices = list(self.price_levels)[-10:]
        
        # Net movement vs total movement
        net_movement = abs(prices[-1] - prices[0])
        total_movement = sum(abs(prices[i] - prices[i-1]) for i in range(1, len(prices)))
        
        if total_movement == 0:
            return 0.5
        
        efficiency = net_movement / total_movement
        return min(1.0, efficiency)

class EnhancedChoppyMarketIndex(EnhancedVolumeWeightedIndicator):
    """Enhanced Choppy Market Index
    
    Advanced CMI implementation with volume weighting and
    sophisticated trend/chop detection.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "Enhanced_CMI")
        self.indicator_type = IndicatorType.VOLATILITY
        
        # CMI calculation components
        self.true_ranges = deque(maxlen=config.period * 2)
        self.price_changes = deque(maxlen=config.period * 2)
        self.previous_close = None
        
        # Market condition tracking
        self.cmi_history = deque(maxlen=50)
        self.trend_strength_history = deque(maxlen=20)
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime,
                       high: float = None, low: float = None) -> Dict[str, float]:
        """Calculate Enhanced Choppy Market Index"""
        self._add_data_point(price, volume, timestamp)
        
        # Use price as high/low if not provided
        if high is None:
            high = price * 1.001
        if low is None:
            low = price * 0.999
        
        close = price
        
        # Calculate True Range and Price Change
        if self.previous_close is not None:
            tr1 = high - low
            tr2 = abs(high - self.previous_close)
            tr3 = abs(low - self.previous_close)
            true_range = max(tr1, tr2, tr3)
            price_change = abs(close - self.previous_close)
        else:
            true_range = high - low
            price_change = 0
        
        self.previous_close = close
        
        # Apply volume weighting
        if self.config.volume_weighted and len(self.volumes) > 1:
            avg_volume = np.mean(list(self.volumes)[-min(10, len(self.volumes)):]) if self.volumes else 1
            volume_weight = min(2.0, max(0.5, volume / avg_volume)) if avg_volume > 0 else 1.0
            
            weighted_tr = true_range * volume_weight
            weighted_pc = price_change * volume_weight
        else:
            volume_weight = 1.0
            weighted_tr = true_range
            weighted_pc = price_change
        
        self.true_ranges.append(weighted_tr)
        self.price_changes.append(weighted_pc)
        
        if len(self.true_ranges) < self.config.period:
            return {'cmi': 50.0, 'market_condition': 'normal', 'trend_strength': 0.5}
        
        # Calculate CMI
        sum_tr = sum(list(self.true_ranges)[-self.config.period:])
        sum_pc = sum(list(self.price_changes)[-self.config.period:])
        
        if sum_tr == 0:
            cmi = 0
        else:
            cmi = (sum_pc / sum_tr) * 100
        
        self.cmi_history.append(cmi)
        
        # Market condition classification
        market_condition = self._classify_market_condition(cmi)
        
        # Trend strength calculation
        trend_strength = self._calculate_trend_strength(cmi)
        self.trend_strength_history.append(trend_strength)
        
        # Choppiness persistence
        choppiness_persistence = self._calculate_choppiness_persistence()
        
        return {
            'cmi': cmi,
            'market_condition': market_condition,
            'trend_strength': trend_strength,
            'choppiness_persistence': choppiness_persistence,
            'sum_true_range': sum_tr,
            'sum_price_change': sum_pc,
            'volume_weight': volume_weight
        }
    
    def _generate_signal(self, current_values: Dict[str, float], 
                        previous_values: Dict[str, float] = None) -> Tuple[SignalType, float]:
        """Generate CMI-based signals"""
        cmi = current_values['cmi']
        market_condition = current_values['market_condition']
        trend_strength = current_values['trend_strength']
        choppiness_persistence = current_values['choppiness_persistence']
        
        # Market condition transition signals
        if previous_values:
            prev_condition = previous_values['market_condition']
            
            # Transition from choppy to trending
            if prev_condition == 'choppy' and market_condition == 'trending':
                return SignalType.NEUTRAL, min(0.8, trend_strength)
            
            # Transition from trending to choppy
            elif prev_condition == 'trending' and market_condition == 'choppy':
                return SignalType.NEUTRAL, 0.4  # Caution signal
        
        # Strong trend signals
        if market_condition == 'strong_trend' and trend_strength > 0.8:
            return SignalType.NEUTRAL, min(1.0, trend_strength)
        
        # Persistent choppiness warning
        if choppiness_persistence > 0.8:
            return SignalType.NEUTRAL, 0.3  # Low confidence, choppy market
        
        return SignalType.NEUTRAL, 0.0
    
    def _classify_market_condition(self, cmi: float) -> str:
        """Classify market condition based on CMI"""
        if cmi > 80:
            return 'strong_trend'
        elif cmi > 60:
            return 'trending'
        elif cmi > 40:
            return 'normal'
        elif cmi > 20:
            return 'choppy'
        else:
            return 'very_choppy'
    
    def _calculate_trend_strength(self, cmi: float) -> float:
        """Calculate trend strength (0-1 scale)"""
        return min(1.0, cmi / 100)
    
    def _calculate_choppiness_persistence(self) -> float:
        """Calculate how persistent the choppiness has been"""
        if len(self.cmi_history) < 10:
            return 0.0
        
        recent_cmi = list(self.cmi_history)[-10:]
        choppy_periods = sum(1 for cmi in recent_cmi if cmi < 40)
        
        return choppy_periods / len(recent_cmi)

# Factory function for creating enhanced volatility indicators
def create_enhanced_volatility_indicator_v2(indicator_type: str, config: IndicatorConfig, **kwargs) -> EnhancedVolumeWeightedIndicator:
    """Factory function to create enhanced volatility indicators (v2)"""
    indicators = {
        'enhanced_vw_atr_v2': EnhancedVolumeWeightedATR,
        'enhanced_vw_bollinger_v2': lambda cfg: EnhancedVolumeWeightedBollingerBands(cfg, **kwargs),
        'enhanced_natr_v2': EnhancedNormalizedATR,
        'enhanced_cmi_v2': EnhancedChoppyMarketIndex
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown enhanced volatility indicator type: {indicator_type}")
    
    if callable(indicator_factory) and indicator_type.lower() == 'enhanced_vw_bollinger_v2':
        return indicator_factory(config)
    else:
        return indicator_factory(config)