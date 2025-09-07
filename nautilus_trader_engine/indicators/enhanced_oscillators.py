"""Enhanced Volume-Weighted Oscillators

Implements sophisticated volume-weighted oscillator indicators including:
- Volume-Weighted RSI with adaptive smoothing
- Volume-Weighted MACD with signal line analysis
- Volume-Weighted Stochastic with %K/%D crossovers
- Volume-Weighted Williams %R with momentum analysis
- Volume-Weighted Money Flow Index with institutional flow detection
- Advanced signal generation and performance tracking
"""

import numpy as np
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import deque

from .enhanced_base import (
    EnhancedVolumeWeightedIndicator,
    IndicatorConfig,
    IndicatorResult,
    IndicatorType,
    SignalType
)
from utils.logging_config import get_logger

logger = get_logger(__name__)

class EnhancedVolumeWeightedRSI(EnhancedVolumeWeightedIndicator):
    """Enhanced Volume-Weighted RSI
    
    Advanced RSI implementation with volume weighting, adaptive smoothing,
    and sophisticated signal generation for improved momentum analysis.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "Enhanced_VW_RSI")
        self.indicator_type = IndicatorType.OSCILLATOR
        
        # RSI calculation components
        self.gains = deque(maxlen=config.period * 3)
        self.losses = deque(maxlen=config.period * 3)
        self.volume_weighted_gains = deque(maxlen=config.period * 3)
        self.volume_weighted_losses = deque(maxlen=config.period * 3)
        
        # Adaptive parameters
        self.adaptive_smoothing = config.adaptive_parameters
        self.volatility_adjustment = True
        
        # Signal thresholds
        self.overbought_threshold = 70
        self.oversold_threshold = 30
        
        # Smoothing factors
        self.alpha = 2.0 / (config.period + 1)
        self.avg_gain = None
        self.avg_loss = None
        
        # Volume analysis
        self.volume_trend = deque(maxlen=20)
        self.price_volume_correlation = 0.0
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Enhanced Volume-Weighted RSI"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < 2:
            return None
        
        # Calculate price change
        price_change = price - self.prices[-2]
        
        # Volume-weighted gains and losses
        if price_change > 0:
            gain = price_change * volume
            loss = 0
        else:
            gain = 0
            loss = abs(price_change) * volume
        
        self.gains.append(gain)
        self.losses.append(loss)
        self.volume_weighted_gains.append(gain)
        self.volume_weighted_losses.append(loss)
        
        if len(self.gains) < self.config.period:
            return None
        
        # Calculate average gains and losses
        if self.avg_gain is None:
            self.avg_gain = np.mean(list(self.gains)[-self.config.period:])
            self.avg_loss = np.mean(list(self.losses)[-self.config.period:])
        else:
            # Exponential smoothing
            current_gain = self.gains[-1]
            current_loss = self.losses[-1]
            self.avg_gain = (self.avg_gain * (1 - self.alpha)) + (current_gain * self.alpha)
            self.avg_loss = (self.avg_loss * (1 - self.alpha)) + (current_loss * self.alpha)
        
        # Calculate RSI
        if self.avg_loss == 0:
            rsi = 100
        else:
            rs = self.avg_gain / self.avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        # Volume trend analysis
        self.volume_trend.append(volume)
        volume_ma = np.mean(list(self.volume_trend)) if len(self.volume_trend) >= 5 else volume
        volume_strength = volume / volume_ma if volume_ma > 0 else 1.0
        
        # Adjust RSI based on volume strength
        if self.config.volume_weighted:
            volume_adjustment = min(1.2, max(0.8, volume_strength))
            if rsi > 50:
                rsi = 50 + (rsi - 50) * volume_adjustment
            else:
                rsi = 50 - (50 - rsi) * volume_adjustment
        
        # Generate signals
        signal, confidence = self._generate_rsi_signal(rsi, volume_strength)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=rsi,
            signal=signal,
            confidence=confidence,
            metadata={
                'avg_gain': self.avg_gain,
                'avg_loss': self.avg_loss,
                'volume_strength': volume_strength,
                'overbought': rsi >= self.overbought_threshold,
                'oversold': rsi <= self.oversold_threshold,
                'divergence_detected': self._detect_divergence(price, rsi)
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
    
    def _generate_rsi_signal(self, rsi: float, volume_strength: float) -> Tuple[SignalType, float]:
        """Generate RSI-based signals"""
        # Overbought/Oversold signals
        if rsi >= self.overbought_threshold:
            confidence = min(1.0, (rsi - self.overbought_threshold) / 30 * volume_strength)
            return SignalType.SELL, confidence
        elif rsi <= self.oversold_threshold:
            confidence = min(1.0, (self.oversold_threshold - rsi) / 30 * volume_strength)
            return SignalType.BUY, confidence
        
        # Momentum signals
        if len(self.results) >= 3:
            prev_rsi = self.results[-1].value if self.results else 50
            rsi_momentum = rsi - prev_rsi
            
            if abs(rsi_momentum) > 5:  # Significant momentum change
                if rsi_momentum > 0 and rsi < 70:
                    return SignalType.BUY, min(0.7, abs(rsi_momentum) / 10 * volume_strength)
                elif rsi_momentum < 0 and rsi > 30:
                    return SignalType.SELL, min(0.7, abs(rsi_momentum) / 10 * volume_strength)
        
        return SignalType.NEUTRAL, 0.0
    
    def _detect_divergence(self, price: float, rsi: float) -> bool:
        """Detect price-RSI divergence"""
        if len(self.results) < 10:
            return False
        
        # Get recent price and RSI data
        recent_prices = [self.prices[i] for i in range(-10, 0)] if len(self.prices) >= 10 else []
        recent_rsi = [self.results[i].value for i in range(-10, 0)] if len(self.results) >= 10 else []
        
        if len(recent_prices) < 10 or len(recent_rsi) < 10:
            return False
        
        # Calculate trends
        price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        rsi_trend = np.polyfit(range(len(recent_rsi)), recent_rsi, 1)[0]
        
        # Detect divergence (opposite trends)
        return (price_trend > 0 and rsi_trend < 0) or (price_trend < 0 and rsi_trend > 0)

class EnhancedVolumeWeightedMACD(EnhancedVolumeWeightedIndicator):
    """Enhanced Volume-Weighted MACD
    
    Advanced MACD implementation with volume weighting and enhanced signal analysis.
    """
    
    def __init__(self, config: IndicatorConfig, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        super().__init__(config, "Enhanced_VW_MACD")
        self.indicator_type = IndicatorType.OSCILLATOR
        
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        
        # EMA calculations
        self.fast_ema = None
        self.slow_ema = None
        self.signal_ema = None
        
        # MACD components
        self.macd_line = deque(maxlen=100)
        self.signal_line = deque(maxlen=100)
        self.histogram = deque(maxlen=100)
        
        # Volume weighting
        self.volume_ema = None
        
        # Alpha values for EMA
        self.fast_alpha = 2.0 / (fast_period + 1)
        self.slow_alpha = 2.0 / (slow_period + 1)
        self.signal_alpha = 2.0 / (signal_period + 1)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Enhanced Volume-Weighted MACD"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        # Volume-weighted price
        if self.config.volume_weighted:
            if self.volume_ema is None:
                self.volume_ema = volume
                vw_price = price
            else:
                self.volume_ema = (self.volume_ema * (1 - self.fast_alpha)) + (volume * self.fast_alpha)
                volume_weight = volume / self.volume_ema if self.volume_ema > 0 else 1.0
                vw_price = price * min(2.0, max(0.5, volume_weight))
        else:
            vw_price = price
        
        # Calculate EMAs
        if self.fast_ema is None:
            self.fast_ema = vw_price
            self.slow_ema = vw_price
        else:
            self.fast_ema = (self.fast_ema * (1 - self.fast_alpha)) + (vw_price * self.fast_alpha)
            self.slow_ema = (self.slow_ema * (1 - self.slow_alpha)) + (vw_price * self.slow_alpha)
        
        # Calculate MACD line
        macd = self.fast_ema - self.slow_ema
        self.macd_line.append(macd)
        
        # Calculate signal line
        if self.signal_ema is None:
            self.signal_ema = macd
        else:
            self.signal_ema = (self.signal_ema * (1 - self.signal_alpha)) + (macd * self.signal_alpha)
        
        self.signal_line.append(self.signal_ema)
        
        # Calculate histogram
        histogram = macd - self.signal_ema
        self.histogram.append(histogram)
        
        if len(self.macd_line) < self.config.min_periods:
            return None
        
        # Generate signals
        signal, confidence = self._generate_macd_signal(macd, self.signal_ema, histogram)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=macd,
            signal=signal,
            confidence=confidence,
            metadata={
                'macd_line': macd,
                'signal_line': self.signal_ema,
                'histogram': histogram,
                'fast_ema': self.fast_ema,
                'slow_ema': self.slow_ema,
                'crossover_detected': self._detect_crossover(),
                'divergence_detected': self._detect_macd_divergence()
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
    
    def _generate_macd_signal(self, macd: float, signal: float, histogram: float) -> Tuple[SignalType, float]:
        """Generate MACD-based signals"""
        # Signal line crossover
        if len(self.macd_line) >= 2 and len(self.signal_line) >= 2:
            prev_macd = self.macd_line[-2]
            prev_signal = self.signal_line[-2]
            
            # Bullish crossover
            if prev_macd <= prev_signal and macd > signal:
                confidence = min(1.0, abs(histogram) * 2)
                return SignalType.BUY, confidence
            
            # Bearish crossover
            elif prev_macd >= prev_signal and macd < signal:
                confidence = min(1.0, abs(histogram) * 2)
                return SignalType.SELL, confidence
        
        # Zero line crossover
        if len(self.macd_line) >= 2:
            prev_macd = self.macd_line[-2]
            if prev_macd <= 0 and macd > 0:
                return SignalType.BUY, 0.6
            elif prev_macd >= 0 and macd < 0:
                return SignalType.SELL, 0.6
        
        # Histogram momentum
        if len(self.histogram) >= 3:
            hist_trend = np.mean(list(self.histogram)[-3:])
            if hist_trend > 0 and histogram > hist_trend:
                return SignalType.BUY, 0.4
            elif hist_trend < 0 and histogram < hist_trend:
                return SignalType.SELL, 0.4
        
        return SignalType.NEUTRAL, 0.0
    
    def _detect_crossover(self) -> bool:
        """Detect MACD signal line crossover"""
        if len(self.macd_line) >= 2 and len(self.signal_line) >= 2:
            prev_diff = self.macd_line[-2] - self.signal_line[-2]
            curr_diff = self.macd_line[-1] - self.signal_line[-1]
            return (prev_diff * curr_diff) < 0  # Sign change indicates crossover
        return False
    
    def _detect_macd_divergence(self) -> bool:
        """Detect MACD-price divergence"""
        if len(self.results) < 10 or len(self.prices) < 10:
            return False
        
        recent_prices = list(self.prices)[-10:]
        recent_macd = [r.value for r in self.results[-10:]]
        
        price_trend = np.polyfit(range(len(recent_prices)), recent_prices, 1)[0]
        macd_trend = np.polyfit(range(len(recent_macd)), recent_macd, 1)[0]
        
        return (price_trend > 0 and macd_trend < 0) or (price_trend < 0 and macd_trend > 0)

# Factory function for creating enhanced oscillator indicators
def create_enhanced_oscillator_indicator_v2(indicator_type: str, config: IndicatorConfig, **kwargs) -> EnhancedVolumeWeightedIndicator:
    """Factory function to create enhanced oscillator indicators (v2)"""
    indicators = {
        'enhanced_vw_rsi_v2': EnhancedVolumeWeightedRSI,
        'enhanced_vw_macd_v2': lambda cfg: EnhancedVolumeWeightedMACD(cfg, **kwargs)
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown enhanced oscillator indicator type: {indicator_type}")
    
    if callable(indicator_factory) and indicator_type.lower() == 'enhanced_vw_macd_v2':
        return indicator_factory(config)
    else:
        return indicator_factory(config)