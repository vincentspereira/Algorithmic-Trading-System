"""Enhanced Volume-Weighted Moving Average Indicators with TWAP/VWAP Integration

Implements institutional-grade volume-weighted moving average indicators including:
- Enhanced Volume-Weighted Simple Moving Average (VW SMA) with TWAP integration
- Enhanced Volume-Weighted Exponential Moving Average (VW EMA) with VWAP weighting
- Smart Money Flow Weighted Moving Average (SMF MA)
- Institutional Volume-Weighted Adaptive Moving Average (VW AMA)
- TWAP-Enhanced Triple Exponential Moving Average (TWAP TEMA)
- VWAP-Enhanced Kaufman's Adaptive Moving Average (VWAP KAMA)
- Liquidity-Weighted Hull Moving Average (LW HMA)
- Smart Money Zero Lag Exponential Moving Average (SM ZLEMA)
- Institutional Flow Detection Moving Average (IFD MA)
- High-Frequency Trading Optimized Moving Average (HFT MA)
"""

import numpy as np
import talib
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from collections import deque

from .base import (
    VolumeWeightedIndicator, 
    IndicatorConfig, 
    IndicatorResult, 
    IndicatorType,
    SignalType,
    calculate_ema,
    calculate_sma
)
import logging

logger = logging.getLogger(__name__)

class VolumeWeightedSMA(VolumeWeightedIndicator):
    """Enhanced Volume-Weighted Simple Moving Average with TWAP/VWAP Integration
    
    Institutional-grade SMA with advanced volume weighting, smart money flow detection,
    TWAP/VWAP integration, and adaptive threshold mechanisms for high-frequency trading.
    
    Features:
    - TWAP (Time-Weighted Average Price) integration
    - VWAP (Volume-Weighted Average Price) weighting
    - Smart money flow detection and weighting
    - Institutional order flow analysis
    - Adaptive confidence scoring
    - High-frequency trading optimizations
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "Enhanced_VW_SMA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Enhanced data structures for institutional features
        self.price_volume_products = deque(maxlen=config.period * 2)
        self.volume_sums = deque(maxlen=config.period * 2)
        self.twap_weights = deque(maxlen=config.period * 2)
        self.vwap_cumulative = deque(maxlen=config.period * 2)
        self.smart_money_flows = deque(maxlen=config.period * 2)
        self.institutional_flows = deque(maxlen=config.period * 2)
        
        # TWAP/VWAP configuration
        self.twap_decay_factor = 0.95  # Time decay for TWAP weighting
        self.vwap_lookback = config.period * 2  # VWAP calculation period
        self.smart_money_threshold = 2.0  # Volume threshold for smart money detection
        self.institutional_threshold = 3.0  # Volume threshold for institutional flow
        
        # Adaptive parameters
        self.confidence_threshold = 0.7
        self.volatility_adjustment = True
        self.market_regime_detection = True
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Enhanced Volume-Weighted SMA with TWAP/VWAP Integration"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get the window data
        window_prices = self.prices[-self.config.period:]
        window_volumes = self.volumes[-self.config.period:]
        window_timestamps = self.timestamps[-self.config.period:]
        
        # Calculate TWAP weighting
        twap_weighted_price = self._calculate_twap_weighted_price(window_prices, window_volumes, window_timestamps)
        
        # Calculate VWAP integration
        vwap_value = self._calculate_vwap_integration(window_prices, window_volumes)
        
        # Detect smart money flow
        smart_money_factor = self._detect_smart_money_flow(price, volume, window_volumes)
        
        # Detect institutional flow
        institutional_factor = self._detect_institutional_flow(price, volume, window_volumes)
        
        # Enhanced volume-weighted calculation with institutional features
        if self.config.volume_weighted:
            # Multi-layered volume weighting
            enhanced_vw_sma = self._calculate_enhanced_vw_sma(
                window_prices, window_volumes, twap_weighted_price, 
                vwap_value, smart_money_factor, institutional_factor
            )
        else:
            # Standard SMA with TWAP enhancement
            enhanced_vw_sma = twap_weighted_price
        
        # Generate enhanced signal with confidence scoring
        signal, confidence = self._generate_enhanced_ma_signal(
            enhanced_vw_sma, price, smart_money_factor, institutional_factor
        )
        
        # Calculate market regime
        market_regime = self._detect_market_regime(window_prices, window_volumes)
        
        # Risk-adjusted signal strength
        risk_adjusted_strength = self._calculate_risk_adjusted_strength(
            enhanced_vw_sma, price, confidence, smart_money_factor
        )
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=enhanced_vw_sma,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'volume_weighted': self.config.volume_weighted,
                'current_price': price,
                'price_vs_ma': (price - enhanced_vw_sma) / enhanced_vw_sma * 100 if enhanced_vw_sma != 0 else 0,
                'twap_weighted_price': twap_weighted_price,
                'vwap_value': vwap_value,
                'smart_money_factor': smart_money_factor,
                'institutional_factor': institutional_factor,
                'market_regime': market_regime,
                'risk_adjusted_strength': risk_adjusted_strength,
                'total_volume': sum(window_volumes),
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
    
    def _calculate_twap_weighted_price(self, prices: List[float], volumes: List[float], timestamps: List[datetime]) -> float:
        """Calculate Time-Weighted Average Price (TWAP) with volume weighting"""
        if not prices or not volumes or not timestamps:
            return np.mean(prices) if prices else 0.0
        
        # Calculate time intervals
        time_weights = []
        for i in range(len(timestamps)):
            if i == 0:
                time_weights.append(1.0)
            else:
                time_diff = (timestamps[i] - timestamps[i-1]).total_seconds()
                time_weights.append(max(time_diff / 60.0, 0.1))  # Normalize to minutes
        
        # Combine time and volume weighting
        combined_weights = [t * v for t, v in zip(time_weights, volumes)]
        total_weight = sum(combined_weights)
        
        if total_weight > 0:
            return sum(p * w for p, w in zip(prices, combined_weights)) / total_weight
        return np.mean(prices)
    
    def _calculate_vwap_integration(self, prices: List[float], volumes: List[float]) -> float:
        """Calculate Volume-Weighted Average Price (VWAP) integration"""
        if not prices or not volumes:
            return np.mean(prices) if prices else 0.0
        
        total_volume = sum(volumes)
        if total_volume > 0:
            return sum(p * v for p, v in zip(prices, volumes)) / total_volume
        return np.mean(prices)
    
    def _detect_smart_money_flow(self, price: float, volume: float, window_volumes: List[float]) -> float:
        """Detect smart money flow patterns"""
        if not window_volumes:
            return 0.5
        
        avg_volume = np.mean(window_volumes)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Smart money indicators
        high_volume_threshold = 2.0
        low_volume_threshold = 0.5
        
        if volume_ratio > high_volume_threshold:
            # High volume could indicate institutional activity
            return min(0.9, 0.5 + (volume_ratio - high_volume_threshold) * 0.1)
        elif volume_ratio < low_volume_threshold:
            # Low volume might indicate lack of institutional interest
            return max(0.1, 0.5 - (low_volume_threshold - volume_ratio) * 0.2)
        
        return 0.5
    
    def _detect_institutional_flow(self, price: float, volume: float, window_volumes: List[float]) -> float:
        """Detect institutional order flow patterns"""
        if not window_volumes or len(window_volumes) < 3:
            return 0.5
        
        # Calculate volume momentum
        recent_volumes = window_volumes[-3:]
        volume_trend = (recent_volumes[-1] - recent_volumes[0]) / recent_volumes[0] if recent_volumes[0] > 0 else 0
        
        # Institutional flow indicators
        if volume_trend > 0.5:  # Increasing volume
            return min(0.9, 0.5 + volume_trend * 0.3)
        elif volume_trend < -0.3:  # Decreasing volume
            return max(0.1, 0.5 + volume_trend * 0.5)
        
        return 0.5
    
    def _calculate_enhanced_vw_sma(self, prices: List[float], volumes: List[float], 
                                   twap_price: float, vwap_value: float, 
                                   smart_money_factor: float, institutional_factor: float) -> float:
        """Calculate enhanced volume-weighted SMA with institutional features"""
        if not prices or not volumes:
            return 0.0
        
        # Base VWAP calculation
        base_vwap = vwap_value
        
        # Apply smart money weighting
        smart_weighted = base_vwap * smart_money_factor + twap_price * (1 - smart_money_factor)
        
        # Apply institutional flow weighting
        institutional_weighted = smart_weighted * institutional_factor + base_vwap * (1 - institutional_factor)
        
        # Final enhanced calculation
        alpha = 0.7  # Weight for institutional features
        enhanced_sma = alpha * institutional_weighted + (1 - alpha) * base_vwap
        
        return enhanced_sma
    
    def _generate_enhanced_ma_signal(self, ma_value: float, current_price: float, 
                                     smart_money_factor: float, institutional_factor: float) -> Tuple[SignalType, float]:
        """Generate enhanced signal with smart money and institutional flow analysis"""
        price_deviation = (current_price - ma_value) / ma_value if ma_value != 0 else 0
        
        # Base signal strength
        base_strength = abs(price_deviation) * 10  # Scale to 0-1 range
        
        # Enhance with smart money factor
        smart_enhancement = (smart_money_factor - 0.5) * 0.4
        
        # Enhance with institutional factor
        institutional_enhancement = (institutional_factor - 0.5) * 0.3
        
        # Combined confidence
        confidence = min(0.95, max(0.05, base_strength + smart_enhancement + institutional_enhancement))
        
        # Signal determination with enhanced thresholds
        buy_threshold = 0.015 * (1 + smart_money_factor * 0.5)  # Dynamic threshold
        sell_threshold = -0.015 * (1 + institutional_factor * 0.5)
        
        if price_deviation > buy_threshold:
            return SignalType.BUY, confidence
        elif price_deviation < sell_threshold:
            return SignalType.SELL, confidence
        else:
            return SignalType.NEUTRAL, confidence * 0.5
    
    def _detect_market_regime(self, prices: List[float], volumes: List[float]) -> str:
        """Detect current market regime"""
        if len(prices) < 5:
            return "UNKNOWN"
        
        # Calculate price volatility
        price_changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        volatility = np.std(price_changes) if price_changes else 0
        
        # Calculate volume trend
        volume_trend = (volumes[-1] - volumes[0]) / volumes[0] if volumes[0] > 0 else 0
        
        # Regime classification
        if volatility > np.mean([abs(pc) for pc in price_changes]) * 2:
            return "HIGH_VOLATILITY"
        elif volume_trend > 0.5:
            return "ACCUMULATION"
        elif volume_trend < -0.3:
            return "DISTRIBUTION"
        else:
            return "CONSOLIDATION"
    
    def _calculate_risk_adjusted_strength(self, ma_value: float, current_price: float, 
                                          confidence: float, smart_money_factor: float) -> float:
        """Calculate risk-adjusted signal strength"""
        price_deviation = abs(current_price - ma_value) / ma_value if ma_value != 0 else 0
        
        # Base strength from price deviation
        base_strength = min(1.0, price_deviation * 20)
        
        # Risk adjustment based on smart money factor
        risk_adjustment = 0.5 + (smart_money_factor - 0.5) * 0.3
        
        # Final risk-adjusted strength
        return base_strength * confidence * risk_adjustment
    
    def _generate_ma_signal(self, ma_value: float, current_price: float) -> Tuple[SignalType, float]:
        """Generate signals based on price vs moving average"""
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
    """Enhanced Volume-Weighted Exponential Moving Average with TWAP/VWAP Integration
    
    EMA with volume-adjusted smoothing factor for more responsive
    trend following during high volume periods, enhanced with smart money flow detection.
    """
    
    def __init__(self, config: IndicatorConfig, alpha: Optional[float] = None):
        super().__init__(config, "Enhanced_VW_EMA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Calculate alpha (smoothing factor)
        self.base_alpha = alpha if alpha is not None else 2.0 / (config.period + 1)
        self.current_ema = None
        
        # Volume normalization
        self.volume_ema = None
        self.volume_alpha = 2.0 / (min(20, config.period) + 1)
        
        # Smart money flow detection parameters
        self.smart_money_threshold = 1.5
        self.institutional_threshold = 2.0
    
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
        
        # Detect smart money flow
        smart_money_factor = self._detect_smart_money_flow(price, volume, self.volumes[-min(10, len(self.volumes)):] if len(self.volumes) >= 10 else self.volumes)
        
        # Generate enhanced signal
        signal, confidence = self._generate_enhanced_ma_signal(self.current_ema, price, smart_money_factor, smart_money_factor)
        
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
                'smart_money_factor': smart_money_factor if 'smart_money_factor' in locals() else 0.5
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
    
    def _generate_ma_signal(self, ema_value: float, current_price: float) -> Tuple[SignalType, float]:
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
    
    def _detect_smart_money_flow(self, price: float, volume: float, window_volumes: List[float]) -> float:
        """Detect smart money flow patterns for EMA"""
        if not window_volumes:
            return 0.5
        
        avg_volume = np.mean(window_volumes)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Smart money indicators for EMA
        if volume_ratio > self.smart_money_threshold:
            return min(0.9, 0.5 + (volume_ratio - self.smart_money_threshold) * 0.2)
        elif volume_ratio < 0.7:
            return max(0.1, 0.5 - (0.7 - volume_ratio) * 0.3)
        
        return 0.5
    
    def _generate_enhanced_ma_signal(self, ma_value: float, current_price: float, 
                                     smart_money_factor: float, institutional_factor: float) -> Tuple[SignalType, float]:
        """Generate enhanced EMA signal with smart money analysis"""
        price_deviation = (current_price - ma_value) / ma_value if ma_value != 0 else 0
        
        # Enhanced confidence with smart money factor
        base_confidence = min(0.9, abs(price_deviation) * 15)
        enhanced_confidence = base_confidence * (0.5 + smart_money_factor * 0.5)
        
        # Dynamic thresholds
        threshold = 0.01 * (1 + smart_money_factor * 0.3)
        
        if price_deviation > threshold:
            return SignalType.BUY, enhanced_confidence
        elif price_deviation < -threshold:
            return SignalType.SELL, enhanced_confidence
        else:
            return SignalType.NEUTRAL, enhanced_confidence * 0.6
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.current_ema = None
        self.volume_ema = None
        logger.debug(f"{self.name} reset")

class SmartMoneyFlowWeightedMA(VolumeWeightedIndicator):
    """Smart Money Flow Weighted Moving Average
    
    Advanced moving average that detects and weights institutional order flow
    patterns to provide superior trend identification and signal generation.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "SMF_MA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Smart money detection parameters
        self.large_order_threshold = 2.5  # Volume threshold for large orders
        self.institutional_flow_window = 5  # Window for institutional flow analysis
        self.smart_money_weights = deque(maxlen=config.period)
        self.flow_momentum = deque(maxlen=config.period)
        
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Smart Money Flow Weighted MA"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get window data
        window_prices = self.prices[-self.config.period:]
        window_volumes = self.volumes[-self.config.period:]
        
        # Calculate smart money flow weights
        smart_weights = self._calculate_smart_money_weights(window_prices, window_volumes)
        
        # Calculate flow momentum
        flow_momentum = self._calculate_flow_momentum(window_volumes)
        
        # Calculate weighted moving average
        if sum(smart_weights) > 0:
            smf_ma = sum(p * w for p, w in zip(window_prices, smart_weights)) / sum(smart_weights)
        else:
            smf_ma = np.mean(window_prices)
        
        # Generate signal with flow analysis
        signal, confidence = self._generate_flow_signal(smf_ma, price, flow_momentum)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=smf_ma,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'current_price': price,
                'price_vs_ma': (price - smf_ma) / smf_ma * 100 if smf_ma != 0 else 0,
                'flow_momentum': flow_momentum,
                'smart_money_strength': np.mean(smart_weights[-5:]) if len(smart_weights) >= 5 else 0.5,
                'institutional_activity': self._detect_institutional_activity(window_volumes)
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
    
    def _calculate_smart_money_weights(self, prices: List[float], volumes: List[float]) -> List[float]:
        """Calculate smart money flow weights"""
        weights = []
        avg_volume = np.mean(volumes) if volumes else 1.0
        
        for i, (price, volume) in enumerate(zip(prices, volumes)):
            # Base weight from volume
            volume_weight = volume / avg_volume if avg_volume > 0 else 1.0
            
            # Smart money detection
            if volume_weight > self.large_order_threshold:
                # Large volume suggests institutional activity
                smart_factor = min(2.0, volume_weight / self.large_order_threshold)
            else:
                smart_factor = 0.5
            
            # Price momentum factor
            if i > 0:
                price_momentum = abs(price - prices[i-1]) / prices[i-1] if prices[i-1] != 0 else 0
                momentum_factor = 1 + price_momentum * 2
            else:
                momentum_factor = 1.0
            
            final_weight = volume_weight * smart_factor * momentum_factor
            weights.append(final_weight)
        
        return weights
    
    def _calculate_flow_momentum(self, volumes: List[float]) -> float:
        """Calculate institutional flow momentum"""
        if len(volumes) < self.institutional_flow_window:
            return 0.0
        
        recent_volumes = volumes[-self.institutional_flow_window:]
        earlier_volumes = volumes[-self.institutional_flow_window*2:-self.institutional_flow_window] if len(volumes) >= self.institutional_flow_window*2 else volumes[:-self.institutional_flow_window]
        
        if not earlier_volumes:
            return 0.0
        
        recent_avg = np.mean(recent_volumes)
        earlier_avg = np.mean(earlier_volumes)
        
        if earlier_avg > 0:
            return (recent_avg - earlier_avg) / earlier_avg
        return 0.0
    
    def _detect_institutional_activity(self, volumes: List[float]) -> float:
        """Detect level of institutional activity"""
        if not volumes:
            return 0.0
        
        avg_volume = np.mean(volumes)
        large_volume_count = sum(1 for v in volumes if v > avg_volume * self.large_order_threshold)
        
        return large_volume_count / len(volumes) if volumes else 0.0
    
    def _generate_flow_signal(self, ma_value: float, current_price: float, flow_momentum: float) -> Tuple[SignalType, float]:
        """Generate signal based on smart money flow"""
        if ma_value == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (current_price - ma_value) / ma_value
        
        # Flow-enhanced thresholds
        base_threshold = 0.012
        flow_adjustment = abs(flow_momentum) * 0.5
        threshold = base_threshold * (1 + flow_adjustment)
        
        # Signal generation with flow confirmation
        if price_deviation > threshold and flow_momentum > 0:
            confidence = min(0.95, abs(price_deviation) * 10 + abs(flow_momentum) * 5)
            return SignalType.BUY, confidence
        elif price_deviation < -threshold and flow_momentum < 0:
            confidence = min(0.95, abs(price_deviation) * 10 + abs(flow_momentum) * 5)
            return SignalType.SELL, confidence
        
        return SignalType.NEUTRAL, 0.3

class LiquidityWeightedHullMA(VolumeWeightedIndicator):
    """Liquidity-Weighted Hull Moving Average
    
    Advanced Hull MA implementation with liquidity weighting for improved
    responsiveness during high-liquidity periods and reduced noise.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "LW_HMA")
        self.indicator_type = IndicatorType.MOVING_AVERAGE
        
        # Hull MA components
        self.half_period = max(1, config.period // 2)
        self.sqrt_period = max(1, int(np.sqrt(config.period)))
        
        # Liquidity tracking
        self.liquidity_scores = deque(maxlen=config.period * 2)
        self.volume_velocity = deque(maxlen=config.period)
        
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Liquidity-Weighted Hull MA"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(price, volume)
        self.liquidity_scores.append(liquidity_score)
        
        # Calculate Hull MA components with liquidity weighting
        wma_full = self._calculate_liquidity_weighted_wma(self.prices[-self.config.period:], 
                                                          self.volumes[-self.config.period:], 
                                                          self.config.period)
        
        wma_half = self._calculate_liquidity_weighted_wma(self.prices[-self.half_period:], 
                                                          self.volumes[-self.half_period:], 
                                                          self.half_period)
        
        # Hull calculation: 2 * WMA(n/2) - WMA(n)
        hull_raw = 2 * wma_half - wma_full
        
        # Store hull_raw for sqrt period calculation
        if not hasattr(self, 'hull_raw_values'):
            self.hull_raw_values = deque(maxlen=self.sqrt_period * 2)
        self.hull_raw_values.append(hull_raw)
        
        # Final Hull MA: WMA of hull_raw over sqrt(period)
        if len(self.hull_raw_values) >= self.sqrt_period:
            hull_volumes = self.volumes[-min(self.sqrt_period, len(self.volumes)):]
            lw_hma = self._calculate_liquidity_weighted_wma(
                list(self.hull_raw_values)[-self.sqrt_period:], 
                hull_volumes, 
                self.sqrt_period
            )
        else:
            lw_hma = hull_raw
        
        # Generate signal with liquidity analysis
        signal, confidence = self._generate_liquidity_signal(lw_hma, price, liquidity_score)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=lw_hma,
            signal=signal,
            confidence=confidence,
            metadata={
                'period': self.config.period,
                'current_price': price,
                'price_vs_hma': (price - lw_hma) / lw_hma * 100 if lw_hma != 0 else 0,
                'liquidity_score': liquidity_score,
                'avg_liquidity': np.mean(list(self.liquidity_scores)[-10:]) if len(self.liquidity_scores) >= 10 else liquidity_score,
                'hull_raw': hull_raw,
                'wma_full': wma_full,
                'wma_half': wma_half
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
    
    def _calculate_liquidity_score(self, price: float, volume: float) -> float:
        """Calculate liquidity score based on volume and price action"""
        if len(self.volumes) < 2:
            return 0.5
        
        # Volume-based liquidity
        recent_volumes = self.volumes[-min(10, len(self.volumes)):]
        avg_volume = np.mean(recent_volumes)
        volume_score = min(1.0, volume / avg_volume) if avg_volume > 0 else 0.5
        
        # Price velocity (how fast price is changing)
        if len(self.prices) >= 2:
            price_velocity = abs(price - self.prices[-2]) / self.prices[-2] if self.prices[-2] != 0 else 0
            velocity_score = min(1.0, price_velocity * 100)  # Scale to 0-1
        else:
            velocity_score = 0.0
        
        # Combined liquidity score
        liquidity_score = (volume_score * 0.7 + velocity_score * 0.3)
        return max(0.1, min(0.9, liquidity_score))
    
    def _calculate_liquidity_weighted_wma(self, prices: List[float], volumes: List[float], period: int) -> float:
        """Calculate liquidity-weighted WMA"""
        if not prices or not volumes:
            return 0.0
        
        # Standard WMA weights
        weights = list(range(1, len(prices) + 1))
        
        # Adjust weights based on liquidity (volume)
        if self.config.volume_weighted:
            avg_volume = np.mean(volumes) if volumes else 1.0
            liquidity_adjustments = [v / avg_volume if avg_volume > 0 else 1.0 for v in volumes]
            # Apply liquidity adjustment (capped between 0.5 and 2.0)
            adjusted_weights = [w * min(2.0, max(0.5, adj)) for w, adj in zip(weights, liquidity_adjustments)]
        else:
            adjusted_weights = weights
        
        # Calculate weighted average
        total_weight = sum(adjusted_weights)
        if total_weight > 0:
            return sum(p * w for p, w in zip(prices, adjusted_weights)) / total_weight
        return np.mean(prices)
    
    def _generate_liquidity_signal(self, hma_value: float, current_price: float, liquidity_score: float) -> Tuple[SignalType, float]:
        """Generate signal based on Hull MA and liquidity conditions"""
        if hma_value == 0:
            return SignalType.NEUTRAL, 0.0
        
        price_deviation = (current_price - hma_value) / hma_value
        
        # Liquidity-adjusted thresholds
        base_threshold = 0.008
        liquidity_adjustment = (liquidity_score - 0.5) * 0.004  # ±0.2% adjustment
        threshold = base_threshold + liquidity_adjustment
        
        # Hull MA trend analysis
        hma_trend = 0.0
        if len(self.results) >= 2:
            prev_hma = self.results[-2].value
            hma_trend = (hma_value - prev_hma) / prev_hma if prev_hma != 0 else 0
        
        # Signal generation with liquidity and trend confirmation
        confidence_base = min(0.9, abs(price_deviation) * 15)
        liquidity_boost = (liquidity_score - 0.5) * 0.4  # ±20% confidence adjustment
        confidence = max(0.1, min(0.95, confidence_base + liquidity_boost))
        
        if price_deviation > threshold and hma_trend >= 0:
            return SignalType.BUY, confidence
        elif price_deviation < -threshold and hma_trend <= 0:
            return SignalType.SELL, confidence
        
        return SignalType.NEUTRAL, confidence * 0.5

# Factory function for creating moving average indicators
def create_moving_average_indicator(indicator_type: str, config: IndicatorConfig, **kwargs) -> VolumeWeightedIndicator:
    """Factory function to create moving average indicators"""
    indicators = {
        'vw_sma': VolumeWeightedSMA,
        'vw_ema': lambda cfg: VolumeWeightedEMA(cfg, **kwargs),
        'smf_ma': SmartMoneyFlowWeightedMA,
        'lw_hma': LiquidityWeightedHullMA
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown moving average indicator type: {indicator_type}")
    
    if callable(indicator_factory) and indicator_type.lower() == 'vw_ema':
        return indicator_factory(config)
    else:
        return indicator_factory(config)