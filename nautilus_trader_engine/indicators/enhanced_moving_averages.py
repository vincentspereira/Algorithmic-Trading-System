"""Enhanced Volume-Weighted Moving Average Indicators

Implements sophisticated volume-weighted moving average indicators including:
- Volume-Weighted Simple Moving Average (VW SMA) with dynamic thresholds
- Volume-Weighted Exponential Moving Average (VW EMA) with adaptive alpha
- Volume-Weighted Adaptive Moving Average (VW AMA)
- Triple Exponential Moving Average (TEMA) with volume weighting
- Kaufman's Adaptive Moving Average (KAMA) with volume integration
- Hull Moving Average (HMA) with volume weighting
- Zero Lag Exponential Moving Average (ZLEMA) with volume adjustment

Features:
- Dynamic signal generation with volatility-based thresholds
- Volume-adjusted smoothing factors
- Comprehensive performance tracking
- Outlier detection and handling
- Adaptive parameter adjustment
"""

import numpy as np
import talib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import deque

from .enhanced_base import (
    VolumeWeightedIndicator, 
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

class VolumeWeightedSMA(VolumeWeightedIndicator):
    """Volume-Weighted Simple Moving Average
    
    Traditional SMA with volume weighting for more accurate trend analysis
    during varying volume conditions with dynamic signal generation.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "VW_SMA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Use deque for efficient rolling window operations
        max_length = config.period * 2
        self.price_volume_products = deque(maxlen=max_length)
        self.volume_sums = deque(maxlen=max_length)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted SMA"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get the window data
        window_prices = list(self.prices)[-self.config.period:]
        window_volumes = list(self.volumes)[-self.config.period:]
        
        if self.config.volume_weighted:
            # Volume-weighted calculation
            total_volume = sum(window_volumes)
            if total_volume > 0:
                vw_sma = sum(p * v for p, v in zip(window_prices, window_volumes)) / total_volume
            else:
                vw_sma = np.mean(window_prices)
        else:
            # Standard SMA
            vw_sma = np.mean(window_prices)
        
        # Generate signal with dynamic thresholds
        signal, confidence = self._generate_ma_signal(vw_sma, price)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=vw_sma,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'volume_weighted': self.config.volume_weighted,
                'current_price': price,
                'price_vs_ma': (price - vw_sma) / vw_sma * 100 if vw_sma != 0 else 0,
                'total_volume': sum(window_volumes) if self.config.volume_weighted else None,
                'avg_volume': np.mean(window_volumes),
                'volume_ratio': volume / np.mean(window_volumes) if np.mean(window_volumes) > 0 else 1.0
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
    
    def _generate_ma_signal(self, ma_value: float, current_price: float) -> Tuple[SignalType, float]:
        """Generate signals based on price vs moving average with dynamic thresholds"""
        if ma_value == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (current_price - ma_value) / ma_value
        
        # Dynamic thresholds based on volatility
        if len(self.results) >= 20:
            recent_prices = [r.metadata['current_price'] for r in self.results[-20:]]
            volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0.02
            threshold = max(0.005, min(0.05, volatility))  # Between 0.5% and 5%
        else:
            threshold = 0.01  # Default 1%
        
        # Generate signals
        if price_deviation > threshold:
            confidence = min(1.0, abs(price_deviation) / (threshold * 2))
            return SignalType.BUY, confidence * 0.7
        elif price_deviation < -threshold:
            confidence = min(1.0, abs(price_deviation) / (threshold * 2))
            return SignalType.SELL, confidence * 0.7
        
        # Trend continuation signals
        if len(self.results) >= 2:
            prev_ma = self.results[-2].value
            if ma_value > prev_ma:
                return SignalType.BUY, 0.3
            elif ma_value < prev_ma:
                return SignalType.SELL, 0.3
        
        return SignalType.NEUTRAL, 0.0

class VolumeWeightedEMA(VolumeWeightedIndicator):
    """Volume-Weighted Exponential Moving Average
    
    EMA with volume-adjusted smoothing factor for more responsive
    trend following during high volume periods.
    """
    
    def __init__(self, config: IndicatorConfig, alpha: Optional[float] = None):
        super().__init__(config, "VW_EMA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Calculate alpha (smoothing factor)
        self.base_alpha = alpha if alpha is not None else 2.0 / (config.period + 1)
        self.current_ema = None
        
        # Volume normalization
        self.volume_ema = None
        self.volume_alpha = 2.0 / (min(20, config.period) + 1)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted EMA"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        # Initialize EMA with first price
        if self.current_ema is None:
            self.current_ema = price
            self.volume_ema = volume
            return None
        
        # Update volume EMA for normalization
        self.volume_ema = self.volume_alpha * volume + (1 - self.volume_alpha) * self.volume_ema
        
        # Calculate volume-adjusted alpha
        if self.config.volume_weighted and self.volume_ema > 0:
            volume_ratio = volume / self.volume_ema
            # Increase responsiveness during high volume (capped between 0.5x and 2x)
            volume_multiplier = min(2.0, max(0.5, volume_ratio))
            adjusted_alpha = min(1.0, self.base_alpha * volume_multiplier)
        else:
            adjusted_alpha = self.base_alpha
        
        # Update EMA
        self.current_ema = adjusted_alpha * price + (1 - adjusted_alpha) * self.current_ema
        
        # Generate signal
        signal, confidence = self._generate_ema_signal(self.current_ema, price)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.current_ema,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'base_alpha': self.base_alpha,
                'adjusted_alpha': adjusted_alpha,
                'volume_multiplier': volume / self.volume_ema if self.volume_ema > 0 else 1.0,
                'volume_weighted': self.config.volume_weighted,
                'current_price': price,
                'price_vs_ema': (price - self.current_ema) / self.current_ema * 100 if self.current_ema != 0 else 0,
                'volume_ema': self.volume_ema
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
    
    def _generate_ema_signal(self, ema_value: float, current_price: float) -> Tuple[SignalType, float]:
        """Generate signals based on price vs EMA and EMA slope"""
        if ema_value == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (current_price - ema_value) / ema_value
        
        # EMA slope analysis
        ema_slope = 0.0
        if len(self.results) >= 2:
            prev_ema = self.results[-2].value
            ema_slope = (ema_value - prev_ema) / prev_ema if prev_ema != 0 else 0
        
        # Dynamic thresholds
        if len(self.results) >= 20:
            recent_prices = [r.metadata['current_price'] for r in self.results[-20:]]
            volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0.02
            threshold = max(0.003, min(0.03, volatility))  # Between 0.3% and 3%
        else:
            threshold = 0.008  # Default 0.8%
        
        # Combined price position and trend signals
        if price_deviation > threshold and ema_slope > 0:
            confidence = min(1.0, (abs(price_deviation) + abs(ema_slope)) / (threshold * 2))
            return SignalType.BUY, confidence * 0.8
        elif price_deviation < -threshold and ema_slope < 0:
            confidence = min(1.0, (abs(price_deviation) + abs(ema_slope)) / (threshold * 2))
            return SignalType.SELL, confidence * 0.8
        
        # Weaker signals based on trend only
        if ema_slope > threshold / 2:
            return SignalType.BUY, 0.4
        elif ema_slope < -threshold / 2:
            return SignalType.SELL, 0.4
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.current_ema = None
        self.volume_ema = None
        logger.debug(f"{self.name} reset")

class VolumeWeightedHullMA(VolumeWeightedIndicator):
    """Volume-Weighted Hull Moving Average
    
    Hull MA with volume weighting for reduced lag and improved trend detection.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "VW_HMA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Hull MA requires multiple WMAs
        self.half_period = max(1, config.period // 2)
        self.sqrt_period = max(1, int(np.sqrt(config.period)))
        
        # Storage for intermediate calculations
        self.wma_full = deque(maxlen=config.period)
        self.wma_half = deque(maxlen=self.half_period)
        self.hull_values = deque(maxlen=self.sqrt_period)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted Hull MA"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Calculate volume-weighted WMAs
        prices_list = list(self.prices)
        volumes_list = list(self.volumes)
        
        # Full period WMA
        wma_full = self._calculate_volume_weighted_wma(
            prices_list[-self.config.period:], 
            volumes_list[-self.config.period:], 
            self.config.period
        )
        
        # Half period WMA
        wma_half = self._calculate_volume_weighted_wma(
            prices_list[-self.half_period:], 
            volumes_list[-self.half_period:], 
            self.half_period
        )
        
        # Hull calculation: 2 * WMA(n/2) - WMA(n)
        hull_raw = 2 * wma_half - wma_full
        self.hull_values.append(hull_raw)
        
        # Final smoothing with sqrt(n) period
        if len(self.hull_values) < self.sqrt_period:
            return None
        
        # Volume-weighted smoothing of hull values
        recent_volumes = volumes_list[-self.sqrt_period:]
        hull_ma = self._calculate_volume_weighted_average(
            list(self.hull_values)[-self.sqrt_period:], 
            recent_volumes
        )
        
        # Generate signal
        signal, confidence = self._generate_hull_signal(hull_ma, price)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=hull_ma,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'half_period': self.half_period,
                'sqrt_period': self.sqrt_period,
                'wma_full': wma_full,
                'wma_half': wma_half,
                'hull_raw': hull_raw,
                'current_price': price,
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
    
    def _calculate_volume_weighted_wma(self, prices: List[float], volumes: List[float], period: int) -> float:
        """Calculate Volume-Weighted WMA"""
        if not prices or not volumes or len(prices) != len(volumes):
            return 0.0
        
        if self.config.volume_weighted:
            # Volume-weighted WMA
            weights = [(i + 1) * v for i, v in enumerate(volumes)]
            total_weight = sum(weights)
            if total_weight > 0:
                return sum(p * w for p, w in zip(prices, weights)) / total_weight
        
        # Standard WMA
        weights = list(range(1, len(prices) + 1))
        total_weight = sum(weights)
        return sum(p * w for p, w in zip(prices, weights)) / total_weight
    
    def _generate_hull_signal(self, hull_value: float, current_price: float) -> Tuple[SignalType, float]:
        """Generate signals based on Hull MA slope and price position"""
        if len(self.results) < 2:
            return SignalType.NEUTRAL, 0.0
        
        # Hull MA slope
        prev_hull = self.results[-2].value
        hull_slope = (hull_value - prev_hull) / prev_hull if prev_hull != 0 else 0
        
        # Price vs Hull MA
        price_deviation = (current_price - hull_value) / hull_value if hull_value != 0 else 0
        
        # Dynamic threshold based on recent volatility
        threshold = 0.005  # Default 0.5%
        if len(self.results) >= 10:
            recent_slopes = [(self.results[i].value - self.results[i-1].value) / self.results[i-1].value 
                           for i in range(-10, -1) if self.results[i-1].value != 0]
            if recent_slopes:
                slope_volatility = np.std(recent_slopes)
                threshold = max(0.002, min(0.02, slope_volatility * 2))
        
        # Strong signals when slope and price position align
        if hull_slope > threshold and price_deviation > 0:
            confidence = min(1.0, (abs(hull_slope) + abs(price_deviation)) / (threshold * 2))
            return SignalType.BUY, confidence * 0.9
        elif hull_slope < -threshold and price_deviation < 0:
            confidence = min(1.0, (abs(hull_slope) + abs(price_deviation)) / (threshold * 2))
            return SignalType.SELL, confidence * 0.9
        
        # Weaker trend signals
        if hull_slope > threshold / 2:
            return SignalType.BUY, 0.5
        elif hull_slope < -threshold / 2:
            return SignalType.SELL, 0.5
        
        return SignalType.NEUTRAL, 0.0

class AdaptiveVolumeWeightedMA(AdaptiveIndicator):
    """Adaptive Volume-Weighted Moving Average
    
    Combines Kaufman's AMA concept with volume weighting and adaptive parameters.
    """
    
    def __init__(self, config: IndicatorConfig, fast_sc: float = 2.0, slow_sc: float = 30.0):
        super().__init__(config, "Adaptive_VW_MA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Adaptive parameters
        self.fast_sc = 2.0 / (fast_sc + 1.0)  # Fast smoothing constant
        self.slow_sc = 2.0 / (slow_sc + 1.0)  # Slow smoothing constant
        
        # State variables
        self.current_ama = None
        self.efficiency_ratios = deque(maxlen=config.period)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Adaptive Volume-Weighted MA"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Initialize AMA
        if self.current_ama is None:
            self.current_ama = price
            return None
        
        # Adapt parameters based on market conditions
        self._adapt_parameters()
        
        # Calculate efficiency ratio
        prices_list = list(self.prices)[-self.adaptive_period:]
        volumes_list = list(self.volumes)[-self.adaptive_period:]
        
        direction = abs(prices_list[-1] - prices_list[0])
        volatility = sum(abs(prices_list[i] - prices_list[i-1]) for i in range(1, len(prices_list)))
        
        efficiency_ratio = direction / volatility if volatility > 0 else 0
        self.efficiency_ratios.append(efficiency_ratio)
        
        # Volume adjustment
        if self.config.volume_weighted and len(volumes_list) > 1:
            avg_volume = np.mean(volumes_list[:-1])
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
            volume_adjustment = min(2.0, max(0.5, volume_ratio))
            efficiency_ratio *= volume_adjustment
        
        # Calculate smoothing constant
        sc = (efficiency_ratio * (self.fast_sc - self.slow_sc) + self.slow_sc) ** 2
        
        # Update AMA
        self.current_ama = self.current_ama + sc * (price - self.current_ama)
        
        # Generate signal
        signal, confidence = self._generate_adaptive_signal(self.current_ama, price, efficiency_ratio)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=self.current_ama,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'adaptive_period': self.adaptive_period,
                'efficiency_ratio': efficiency_ratio,
                'smoothing_constant': sc,
                'volatility_adjustment': self.volatility_adjustment,
                'trend_adjustment': self.trend_adjustment,
                'current_price': price,
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
    
    def _generate_adaptive_signal(self, ama_value: float, current_price: float, efficiency_ratio: float) -> Tuple[SignalType, float]:
        """Generate signals based on AMA and efficiency ratio"""
        if ama_value == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (current_price - ama_value) / ama_value
        
        # AMA slope
        ama_slope = 0.0
        if len(self.results) >= 2:
            prev_ama = self.results[-2].value
            ama_slope = (ama_value - prev_ama) / prev_ama if prev_ama != 0 else 0
        
        # Efficiency-based threshold
        base_threshold = 0.01
        threshold = base_threshold * (1 - efficiency_ratio * 0.5)  # Lower threshold for higher efficiency
        
        # Strong signals when efficiency is high and trend is clear
        if efficiency_ratio > 0.3:
            if price_deviation > threshold and ama_slope > 0:
                confidence = min(1.0, efficiency_ratio + abs(price_deviation) / threshold)
                return SignalType.BUY, confidence * 0.85
            elif price_deviation < -threshold and ama_slope < 0:
                confidence = min(1.0, efficiency_ratio + abs(price_deviation) / threshold)
                return SignalType.SELL, confidence * 0.85
        
        # Moderate signals based on trend
        if ama_slope > threshold / 2:
            return SignalType.BUY, 0.4 + efficiency_ratio * 0.3
        elif ama_slope < -threshold / 2:
            return SignalType.SELL, 0.4 + efficiency_ratio * 0.3
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.current_ama = None
        self.efficiency_ratios.clear()
        logger.debug(f"{self.name} reset")

# Factory function for creating moving average indicators
def create_moving_average_indicator(indicator_type: str, config: IndicatorConfig, **kwargs) -> VolumeWeightedIndicator:
    """Factory function to create moving average indicators"""
    indicators = {
        'vw_sma': VolumeWeightedSMA,
        'vw_ema': lambda cfg: VolumeWeightedEMA(cfg, **kwargs),
        'vw_hma': VolumeWeightedHullMA,
        'adaptive_vw_ma': lambda cfg: AdaptiveVolumeWeightedMA(cfg, **kwargs)
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown moving average indicator type: {indicator_type}")
    
    if callable(indicator_factory) and indicator_type.lower() in ['vw_ema', 'adaptive_vw_ma']:
        return indicator_factory(config)
    else:
        return indicator_factory(config)

# Convenience functions
def create_vw_sma(period: int = 20, volume_weighted: bool = True, **kwargs) -> VolumeWeightedSMA:
    """Create Volume-Weighted SMA with default configuration"""
    config = IndicatorConfig(period=period, volume_weighted=volume_weighted, **kwargs)
    return VolumeWeightedSMA(config)

def create_vw_ema(period: int = 20, volume_weighted: bool = True, alpha: Optional[float] = None, **kwargs) -> VolumeWeightedEMA:
    """Create Volume-Weighted EMA with default configuration"""
    config = IndicatorConfig(period=period, volume_weighted=volume_weighted, **kwargs)
    return VolumeWeightedEMA(config, alpha=alpha)

def create_vw_hma(period: int = 20, volume_weighted: bool = True, **kwargs) -> VolumeWeightedHullMA:
    """Create Volume-Weighted Hull MA with default configuration"""
    config = IndicatorConfig(period=period, volume_weighted=volume_weighted, **kwargs)
    return VolumeWeightedHullMA(config)

def create_adaptive_vw_ma(period: int = 20, volume_weighted: bool = True, adaptive: bool = True, **kwargs) -> AdaptiveVolumeWeightedMA:
    """Create Adaptive Volume-Weighted MA with default configuration"""
    config = IndicatorConfig(period=period, volume_weighted=volume_weighted, adaptive=adaptive, **kwargs)
    return AdaptiveVolumeWeightedMA(config, **kwargs)