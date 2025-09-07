"""Enhanced Volume-Weighted Oscillator Indicators with Institutional Features

Implements advanced volume-weighted oscillator indicators with TWAP/VWAP integration including:
- Enhanced Volume-Weighted RSI with Smart Money Flow Detection
- Institutional Volume-Weighted MACD with Order Flow Analysis
- Smart Money Stochastic with Liquidity Weighting
- Institutional Williams %R with Flow Momentum
- Advanced Money Flow Index with Smart Money Detection
- Adaptive Confidence Scoring and Risk Management
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
    calculate_rsi,
    calculate_macd
)
import logging

logger = logging.getLogger(__name__)

class VolumeWeightedRSI(VolumeWeightedIndicator):
    """Enhanced Volume-Weighted Relative Strength Index with Smart Money Flow Detection
    
    Advanced RSI implementation that incorporates:
    - Volume-weighted price changes for institutional activity detection
    - Smart money flow analysis for enhanced signal generation
    - Adaptive thresholds based on market regime
    - TWAP/VWAP integration for institutional order flow analysis
    - Risk-adjusted confidence scoring
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "Enhanced_VW_RSI")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.gains = []
        self.losses = []
        self.volume_weighted_gains = []
        self.volume_weighted_losses = []
        
        # Institutional features
        self.smart_money_flows = []
        self.institutional_factors = []
        self.market_regimes = []
        self.liquidity_scores = []
        
        # Adaptive thresholds
        self.overbought_threshold = 70.0
        self.oversold_threshold = 30.0
        self.extreme_overbought = 80.0
        self.extreme_oversold = 20.0
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Enhanced Volume-Weighted RSI with Smart Money Flow Detection"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < 2:
            return None
        
        # Calculate price change
        price_change = price - self.prices[-2]
        
        # Separate gains and losses
        gain = max(0, price_change)
        loss = max(0, -price_change)
        
        self.gains.append(gain)
        self.losses.append(loss)
        
        # Detect smart money flow
        smart_money_factor = self._detect_smart_money_flow(price, volume, price_change)
        self.smart_money_flows.append(smart_money_factor)
        
        # Detect institutional activity
        institutional_factor = self._detect_institutional_activity(price, volume)
        self.institutional_factors.append(institutional_factor)
        
        # Calculate liquidity score
        liquidity_score = self._calculate_liquidity_score(volume)
        self.liquidity_scores.append(liquidity_score)
        
        # Detect market regime
        market_regime = self._detect_market_regime()
        self.market_regimes.append(market_regime)
        
        # Enhanced volume-weighting with institutional factors
        if self.config.volume_weighted:
            # Apply smart money and institutional weighting
            enhanced_volume_weight = volume * (1 + smart_money_factor * 0.5) * (1 + institutional_factor * 0.3)
            vw_gain = gain * enhanced_volume_weight
            vw_loss = loss * enhanced_volume_weight
        else:
            vw_gain = gain
            vw_loss = loss
        
        self.volume_weighted_gains.append(vw_gain)
        self.volume_weighted_losses.append(vw_loss)
        
        # Need enough data for RSI calculation
        if len(self.gains) < self.config.period:
            return None
        
        # Calculate average gains and losses over the period
        recent_gains = self.volume_weighted_gains[-self.config.period:]
        recent_losses = self.volume_weighted_losses[-self.config.period:]
        recent_volumes = self.volumes[-self.config.period:] if self.config.volume_weighted else [1] * self.config.period
        
        # Enhanced volume-weighted averages with TWAP integration
        if self.config.volume_weighted and sum(recent_volumes) > 0:
            # Apply TWAP weighting to gains/losses calculation
            twap_weights = self._calculate_twap_weights(recent_volumes)
            avg_gain = sum(g * w for g, w in zip(recent_gains, twap_weights)) / sum(twap_weights)
            avg_loss = sum(l * w for l, w in zip(recent_losses, twap_weights)) / sum(twap_weights)
        else:
            avg_gain = np.mean(recent_gains)
            avg_loss = np.mean(recent_losses)
        
        # Calculate enhanced RSI
        if avg_loss == 0:
            enhanced_rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            enhanced_rsi = 100 - (100 / (1 + rs))
        
        # Apply adaptive thresholds based on market regime
        self._update_adaptive_thresholds(market_regime, liquidity_score)
        
        # Generate enhanced signal with institutional analysis
        signal, confidence = self._generate_enhanced_rsi_signal(
            enhanced_rsi, smart_money_factor, institutional_factor, market_regime
        )
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=enhanced_rsi,
            signal=signal,
            confidence=confidence,
            metadata={
                'avg_gain': avg_gain,
                'avg_loss': avg_loss,
                'rs': avg_gain / avg_loss if avg_loss > 0 else float('inf'),
                'volume_weighted': self.config.volume_weighted,
                'smart_money_factor': smart_money_factor,
                'institutional_factor': institutional_factor,
                'liquidity_score': liquidity_score,
                'market_regime': market_regime,
                'overbought_threshold': self.overbought_threshold,
                'oversold_threshold': self.oversold_threshold,
                'enhanced_volume_weight': enhanced_volume_weight if self.config.volume_weighted else volume,
                'price_change': price_change,
                'gain': gain,
                'loss': loss
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = self.config.period * 3
        if len(self.gains) > max_length:
            self.gains = self.gains[-max_length:]
            self.losses = self.losses[-max_length:]
            self.volume_weighted_gains = self.volume_weighted_gains[-max_length:]
            self.volume_weighted_losses = self.volume_weighted_losses[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _detect_smart_money_flow(self, price: float, volume: float, price_change: float) -> float:
        """Detect smart money flow patterns"""
        if len(self.volumes) < 5:
            return 0.5
        
        # Calculate volume percentile
        recent_volumes = self.volumes[-10:] if len(self.volumes) >= 10 else self.volumes
        volume_percentile = np.percentile(recent_volumes, 75) if recent_volumes else volume
        
        # Smart money indicators
        volume_factor = min(2.0, volume / volume_percentile) if volume_percentile > 0 else 1.0
        
        # Price momentum factor
        momentum_factor = 1.0
        if len(self.prices) >= 3:
            recent_changes = [self.prices[i] - self.prices[i-1] for i in range(-2, 0)]
            if all(change > 0 for change in recent_changes) and price_change > 0:
                momentum_factor = 1.3  # Consistent upward momentum
            elif all(change < 0 for change in recent_changes) and price_change < 0:
                momentum_factor = 1.3  # Consistent downward momentum
        
        # Combined smart money factor
        smart_factor = (volume_factor * momentum_factor - 1.0) * 0.5 + 0.5
        return max(0.1, min(0.9, smart_factor))
    
    def _detect_institutional_activity(self, price: float, volume: float) -> float:
        """Detect institutional order flow activity"""
        if len(self.volumes) < 3:
            return 0.5
        
        # Large order detection
        avg_volume = np.mean(self.volumes[-20:]) if len(self.volumes) >= 20 else np.mean(self.volumes)
        large_order_threshold = avg_volume * 2.5
        
        # Institutional flow patterns
        if volume > large_order_threshold:
            # Large volume suggests institutional activity
            institutional_strength = min(0.9, 0.5 + (volume / large_order_threshold - 1) * 0.2)
        else:
            # Check for sustained volume patterns
            recent_volumes = self.volumes[-5:]
            volume_consistency = 1.0 - (np.std(recent_volumes) / np.mean(recent_volumes)) if np.mean(recent_volumes) > 0 else 0.5
            institutional_strength = 0.3 + volume_consistency * 0.4
        
        return max(0.1, min(0.9, institutional_strength))
    
    def _calculate_liquidity_score(self, volume: float) -> float:
        """Calculate market liquidity score"""
        if len(self.volumes) < 5:
            return 0.5
        
        # Volume-based liquidity
        avg_volume = np.mean(self.volumes[-10:]) if len(self.volumes) >= 10 else np.mean(self.volumes)
        volume_liquidity = min(1.0, volume / avg_volume) if avg_volume > 0 else 0.5
        
        # Price stability factor
        if len(self.prices) >= 5:
            recent_prices = self.prices[-5:]
            price_volatility = np.std(recent_prices) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0
            stability_factor = max(0.1, 1.0 - price_volatility * 10)
        else:
            stability_factor = 0.5
        
        # Combined liquidity score
        liquidity_score = (volume_liquidity * 0.7 + stability_factor * 0.3)
        return max(0.1, min(0.9, liquidity_score))
    
    def _detect_market_regime(self) -> str:
        """Detect current market regime"""
        if len(self.prices) < 10:
            return "UNKNOWN"
        
        recent_prices = self.prices[-10:]
        recent_volumes = self.volumes[-10:]
        
        # Price trend analysis
        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        
        # Volume trend analysis
        volume_trend = (np.mean(recent_volumes[-5:]) - np.mean(recent_volumes[:5])) / np.mean(recent_volumes[:5]) if np.mean(recent_volumes[:5]) > 0 else 0
        
        # Volatility analysis
        price_changes = [recent_prices[i] - recent_prices[i-1] for i in range(1, len(recent_prices))]
        volatility = np.std(price_changes) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0
        
        # Regime classification
        if volatility > 0.02:  # High volatility
            return "HIGH_VOLATILITY"
        elif price_trend > 0.05 and volume_trend > 0.2:
            return "BULLISH_MOMENTUM"
        elif price_trend < -0.05 and volume_trend > 0.2:
            return "BEARISH_MOMENTUM"
        elif abs(price_trend) < 0.02:
            return "CONSOLIDATION"
        else:
            return "TRENDING"
    
    def _calculate_twap_weights(self, volumes: List[float]) -> List[float]:
        """Calculate TWAP weights for enhanced averaging"""
        if not volumes:
            return [1.0]
        
        # Time-weighted with volume adjustment
        weights = []
        for i, volume in enumerate(volumes):
            time_weight = (i + 1) / len(volumes)  # Linear time weighting
            volume_weight = volume / np.mean(volumes) if np.mean(volumes) > 0 else 1.0
            combined_weight = time_weight * (1 + volume_weight * 0.5)
            weights.append(combined_weight)
        
        return weights
    
    def _update_adaptive_thresholds(self, market_regime: str, liquidity_score: float) -> None:
        """Update adaptive RSI thresholds based on market conditions"""
        base_overbought = 70.0
        base_oversold = 30.0
        base_extreme_overbought = 80.0
        base_extreme_oversold = 20.0
        
        # Adjust based on market regime
        if market_regime == "HIGH_VOLATILITY":
            # Wider thresholds in volatile markets
            self.overbought_threshold = base_overbought + 5
            self.oversold_threshold = base_oversold - 5
            self.extreme_overbought = base_extreme_overbought + 5
            self.extreme_oversold = base_extreme_oversold - 5
        elif market_regime in ["BULLISH_MOMENTUM", "BEARISH_MOMENTUM"]:
            # Tighter thresholds in trending markets
            self.overbought_threshold = base_overbought - 5
            self.oversold_threshold = base_oversold + 5
            self.extreme_overbought = base_extreme_overbought - 5
            self.extreme_oversold = base_extreme_oversold + 5
        else:
            # Standard thresholds
            self.overbought_threshold = base_overbought
            self.oversold_threshold = base_oversold
            self.extreme_overbought = base_extreme_overbought
            self.extreme_oversold = base_extreme_oversold
        
        # Adjust based on liquidity
        liquidity_adjustment = (liquidity_score - 0.5) * 5  # ±2.5 point adjustment
        self.overbought_threshold += liquidity_adjustment
        self.oversold_threshold -= liquidity_adjustment
    
    def _generate_enhanced_rsi_signal(self, rsi_value: float, smart_money_factor: float, 
                                      institutional_factor: float, market_regime: str) -> Tuple[SignalType, float]:
        """Generate enhanced RSI signal with institutional analysis"""
        # Base confidence from RSI extremes
        if rsi_value >= self.extreme_overbought:
            base_confidence = min(1.0, (rsi_value - self.extreme_overbought) / 20)
            signal_type = SignalType.SELL
        elif rsi_value >= self.overbought_threshold:
            base_confidence = min(0.8, (rsi_value - self.overbought_threshold) / 10)
            signal_type = SignalType.SELL
        elif rsi_value <= self.extreme_oversold:
            base_confidence = min(1.0, (self.extreme_oversold - rsi_value) / 20)
            signal_type = SignalType.BUY
        elif rsi_value <= self.oversold_threshold:
            base_confidence = min(0.8, (self.oversold_threshold - rsi_value) / 10)
            signal_type = SignalType.BUY
        else:
            return SignalType.NEUTRAL, 0.2
        
        # Enhance confidence with institutional factors
        smart_money_boost = (smart_money_factor - 0.5) * 0.3
        institutional_boost = (institutional_factor - 0.5) * 0.2
        
        # Market regime adjustment
        regime_adjustment = 0.0
        if market_regime in ["BULLISH_MOMENTUM", "BEARISH_MOMENTUM"]:
            regime_adjustment = 0.1  # Higher confidence in trending markets
        elif market_regime == "HIGH_VOLATILITY":
            regime_adjustment = -0.1  # Lower confidence in volatile markets
        
        # Final confidence calculation
        enhanced_confidence = base_confidence + smart_money_boost + institutional_boost + regime_adjustment
        enhanced_confidence = max(0.1, min(0.95, enhanced_confidence))
        
        return signal_type, enhanced_confidence
    
    def _generate_rsi_signal(self, rsi_value: float) -> Tuple[SignalType, float]:
        """Generate trading signal based on RSI levels (legacy method)"""
        if rsi_value >= 80:
            return SignalType.SELL, min(1.0, (rsi_value - 80) / 20)
        elif rsi_value >= 70:
            return SignalType.SELL, min(1.0, (rsi_value - 70) / 10)
        elif rsi_value <= 20:
            return SignalType.BUY, min(1.0, (20 - rsi_value) / 20)
        elif rsi_value <= 30:
            return SignalType.BUY, min(1.0, (30 - rsi_value) / 10)
        else:
            return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.gains.clear()
        self.losses.clear()
        self.volume_weighted_gains.clear()
        self.volume_weighted_losses.clear()
        self.smart_money_flows.clear()
        self.institutional_factors.clear()
        self.market_regimes.clear()
        self.liquidity_scores.clear()
        logger.debug(f"{self.name} reset")

class Enhanced_VW_MACD(MultiValueIndicator):
    """Enhanced Volume-Weighted MACD with Institutional Features
    
    Advanced MACD implementation with:
    - Volume-weighted exponential moving averages
    - Smart money flow detection and weighting
    - Institutional order flow analysis
    - TWAP/VWAP integration for institutional-grade accuracy
    - Adaptive signal thresholds based on market regime
    - Risk-adjusted confidence scoring
    - High-frequency trading optimizations
    """
    
    def __init__(self, config: IndicatorConfig, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9,
                 smart_money_threshold: float = 0.7, institutional_threshold: float = 0.8):
        super().__init__(config, "Enhanced_VW_MACD")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.smart_money_threshold = smart_money_threshold
        self.institutional_threshold = institutional_threshold
        
        # EMA calculations
        self.fast_ema = None
        self.slow_ema = None
        self.signal_ema = None
        
        # Alpha values for EMA
        self.fast_alpha = 2.0 / (fast_period + 1)
        self.slow_alpha = 2.0 / (slow_period + 1)
        self.signal_alpha = 2.0 / (signal_period + 1)
        
        self.macd_values = []
        
        # Institutional features
        self.smart_money_flows = deque(maxlen=100)
        self.institutional_factors = deque(maxlen=100)
        self.market_regimes = deque(maxlen=50)
        self.liquidity_scores = deque(maxlen=100)
        self.twap_weights = deque(maxlen=50)
        
        # Adaptive thresholds
        self.bullish_threshold = 0.0
        self.bearish_threshold = 0.0
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Enhanced MACD values with institutional features"""
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.slow_period:
            return {}
        
        # Detect smart money flow and institutional activity
        smart_money_factor = self._detect_smart_money_flow(price, volume)
        institutional_factor = self._detect_institutional_activity(price, volume)
        liquidity_score = self._calculate_liquidity_score(volume)
        market_regime = self._detect_market_regime()
        
        # Store institutional data
        self.smart_money_flows.append(smart_money_factor)
        self.institutional_factors.append(institutional_factor)
        self.liquidity_scores.append(liquidity_score)
        self.market_regimes.append(market_regime)
        
        # Enhanced volume weighting with institutional factors
        if self.config.volume_weighted and len(self.volumes) > 0:
            avg_volume = np.mean(self.volumes[-min(self.slow_period, len(self.volumes)):]) if self.volumes else 1
            base_volume_weight = min(2.0, max(0.5, volume / avg_volume)) if avg_volume > 0 else 1.0
            
            # Apply institutional weighting
            institutional_weight = 1.0 + (institutional_factor * 0.3) + (smart_money_factor * 0.2)
            enhanced_volume_weight = base_volume_weight * institutional_weight
            
            # TWAP integration
            twap_weight = self._calculate_twap_weights(price, volume)
            self.twap_weights.append(twap_weight)
            
            weighted_price = price * enhanced_volume_weight * twap_weight
        else:
            weighted_price = price
        
        # Calculate Fast EMA
        if self.fast_ema is None:
            self.fast_ema = weighted_price
        else:
            self.fast_ema = self.fast_alpha * weighted_price + (1 - self.fast_alpha) * self.fast_ema
        
        # Calculate Slow EMA
        if self.slow_ema is None:
            self.slow_ema = weighted_price
        else:
            self.slow_ema = self.slow_alpha * weighted_price + (1 - self.slow_alpha) * self.slow_ema
        
        # Calculate MACD Line
        macd_line = self.fast_ema - self.slow_ema
        self.macd_values.append(macd_line)
        
        # Calculate Signal Line
        if self.signal_ema is None:
            self.signal_ema = macd_line
        else:
            self.signal_ema = self.signal_alpha * macd_line + (1 - self.signal_alpha) * self.signal_ema
        
        # Calculate Enhanced Histogram with institutional factors
        base_histogram = macd_line - self.signal_ema
        
        # Apply institutional enhancement to histogram
        institutional_enhancement = 1.0 + (institutional_factor * 0.2)
        enhanced_histogram = base_histogram * institutional_enhancement
        
        # Update adaptive thresholds
        self._update_adaptive_thresholds(market_regime, liquidity_score)
        
        # Maintain rolling window
        max_length = max(self.slow_period * 2, 100)
        if len(self.macd_values) > max_length:
            self.macd_values = self.macd_values[-max_length:]
        
        return {
            'main': macd_line,
            'macd': macd_line,
            'signal': self.signal_ema,
            'histogram': enhanced_histogram,
            'fast_ema': self.fast_ema,
            'slow_ema': self.slow_ema,
            'smart_money_factor': smart_money_factor,
            'institutional_factor': institutional_factor,
            'liquidity_score': liquidity_score,
            'market_regime': market_regime,
            'enhanced_volume_weight': enhanced_volume_weight if self.config.volume_weighted else 1.0,
            'twap_weight': twap_weight if self.config.volume_weighted else 1.0
        }
    
    def _generate_signal(self, current_value: float, previous_value: float = None) -> Tuple[SignalType, float]:
        """Generate Enhanced MACD trading signals with institutional analysis"""
        if len(self.results) < 2:
            return SignalType.NEUTRAL, 0.0
        
        return self._generate_enhanced_macd_signal()
    
    def _generate_enhanced_macd_signal(self) -> Tuple[SignalType, float]:
        """Generate enhanced MACD signals with institutional factors"""
        current_result = self.results[-1]
        previous_result = self.results[-2]
        
        current_histogram = current_result.histogram or 0
        previous_histogram = previous_result.histogram or 0
        current_macd = current_result.value
        current_signal = current_result.signal_line or 0
        
        # Get institutional factors
        smart_money_factor = self.smart_money_flows[-1] if self.smart_money_flows else 0.0
        institutional_factor = self.institutional_factors[-1] if self.institutional_factors else 0.0
        liquidity_score = self.liquidity_scores[-1] if self.liquidity_scores else 0.5
        market_regime = self.market_regimes[-1] if self.market_regimes else 'normal'
        
        # Base signal strength
        base_confidence = min(1.0, abs(current_histogram) / (abs(current_macd) + 0.001))
        
        # Institutional enhancement
        institutional_boost = 1.0 + (institutional_factor * 0.3) + (smart_money_factor * 0.2)
        liquidity_adjustment = 0.8 + (liquidity_score * 0.4)
        
        # Market regime adjustment
        regime_multiplier = {'trending': 1.2, 'ranging': 0.8, 'volatile': 0.9}.get(market_regime, 1.0)
        
        # Enhanced confidence
        enhanced_confidence = min(1.0, base_confidence * institutional_boost * liquidity_adjustment * regime_multiplier)
        
        # MACD line crosses above signal line with adaptive thresholds
        if current_macd > current_signal and current_histogram > max(previous_histogram, self.bullish_threshold):
            # Additional confirmation from institutional factors
            if smart_money_factor > self.smart_money_threshold or institutional_factor > self.institutional_threshold:
                enhanced_confidence *= 1.2
            return SignalType.BUY, min(1.0, enhanced_confidence)
        
        # MACD line crosses below signal line with adaptive thresholds
        elif current_macd < current_signal and current_histogram < min(previous_histogram, self.bearish_threshold):
            # Additional confirmation from institutional factors
            if smart_money_factor < -self.smart_money_threshold or institutional_factor < -self.institutional_threshold:
                enhanced_confidence *= 1.2
            return SignalType.SELL, min(1.0, enhanced_confidence)
        
        return SignalType.NEUTRAL, 0.0
    
    def _detect_smart_money_flow(self, price: float, volume: float) -> float:
        """Detect smart money flow patterns"""
        if len(self.prices) < 10:
            return 0.0
        
        recent_prices = self.prices[-10:]
        recent_volumes = self.volumes[-10:]
        
        # Calculate price momentum and volume surge
        price_change = (price - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        avg_volume = np.mean(recent_volumes) if recent_volumes else 1
        volume_surge = (volume - avg_volume) / avg_volume if avg_volume > 0 else 0
        
        # Smart money typically shows volume surge with price momentum
        if abs(price_change) > 0.02 and volume_surge > 1.0:
            return np.sign(price_change) * min(1.0, volume_surge / 2.0)
        
        return 0.0
    
    def _detect_institutional_activity(self, price: float, volume: float) -> float:
        """Detect institutional trading activity"""
        if len(self.volumes) < 20:
            return 0.0
        
        # Large volume relative to recent average indicates institutional activity
        recent_volumes = self.volumes[-20:]
        avg_volume = np.mean(recent_volumes)
        volume_percentile = np.percentile(recent_volumes, 90)
        
        if volume > volume_percentile and volume > avg_volume * 2:
            # Check for sustained activity
            recent_large_volumes = sum(1 for v in recent_volumes[-5:] if v > avg_volume * 1.5)
            institutional_strength = min(1.0, recent_large_volumes / 5.0)
            
            # Direction based on price movement
            if len(self.prices) >= 2:
                price_direction = np.sign(self.prices[-1] - self.prices[-2])
                return price_direction * institutional_strength
        
        return 0.0
    
    def _calculate_liquidity_score(self, volume: float) -> float:
        """Calculate market liquidity score"""
        if len(self.volumes) < 10:
            return 0.5
        
        recent_volumes = self.volumes[-10:]
        volume_std = np.std(recent_volumes) if len(recent_volumes) > 1 else 0
        avg_volume = np.mean(recent_volumes)
        
        # Higher consistency in volume indicates better liquidity
        if avg_volume > 0:
            cv = volume_std / avg_volume  # Coefficient of variation
            liquidity_score = max(0.0, min(1.0, 1.0 - cv))
        else:
            liquidity_score = 0.5
        
        return liquidity_score
    
    def _detect_market_regime(self) -> str:
        """Detect current market regime"""
        if len(self.prices) < 20:
            return 'normal'
        
        recent_prices = self.prices[-20:]
        price_changes = np.diff(recent_prices)
        volatility = np.std(price_changes) if len(price_changes) > 1 else 0
        
        # Calculate trend strength
        trend_strength = abs(np.mean(price_changes)) / (volatility + 1e-8)
        
        if trend_strength > 1.5:
            return 'trending'
        elif volatility > np.mean(np.abs(price_changes)) * 2:
            return 'volatile'
        else:
            return 'ranging'
    
    def _calculate_twap_weights(self, price: float, volume: float) -> float:
        """Calculate TWAP-based weights"""
        if len(self.prices) < 5:
            return 1.0
        
        # Simple TWAP calculation over recent periods
        recent_prices = self.prices[-5:]
        recent_volumes = self.volumes[-5:]
        
        if sum(recent_volumes) > 0:
            twap = sum(p * v for p, v in zip(recent_prices, recent_volumes)) / sum(recent_volumes)
            # Weight based on deviation from TWAP
            deviation = abs(price - twap) / twap if twap > 0 else 0
            return max(0.5, min(1.5, 1.0 - deviation))
        
        return 1.0
    
    def _update_adaptive_thresholds(self, market_regime: str, liquidity_score: float):
        """Update adaptive signal thresholds based on market conditions"""
        base_threshold = 0.001
        
        # Adjust thresholds based on market regime
        regime_multipliers = {
            'trending': 0.8,  # Lower thresholds in trending markets
            'ranging': 1.2,   # Higher thresholds in ranging markets
            'volatile': 1.5   # Much higher thresholds in volatile markets
        }
        
        regime_multiplier = regime_multipliers.get(market_regime, 1.0)
        liquidity_multiplier = 2.0 - liquidity_score  # Lower liquidity = higher thresholds
        
        threshold = base_threshold * regime_multiplier * liquidity_multiplier
        
        self.bullish_threshold = threshold
        self.bearish_threshold = -threshold
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.fast_ema = None
        self.slow_ema = None
        self.signal_ema = None
        self.macd_values.clear()
        self.smart_money_flows.clear()
        self.institutional_factors.clear()
        self.market_regimes.clear()
        self.liquidity_scores.clear()
        self.twap_weights.clear()
        logger.debug(f"{self.name} reset")

class VolumeWeightedStochastic(MultiValueIndicator):
    """Volume-Weighted Stochastic Oscillator
    
    Incorporates volume weighting into stochastic calculations
    for more accurate overbought/oversold signals.
    """
    
    def __init__(self, config: IndicatorConfig, k_period: int = 14, d_period: int = 3):
        super().__init__(config, "VW_Stoch")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.k_period = k_period
        self.d_period = d_period
        self.highs = []
        self.lows = []
        self.k_values = []
    
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate Stochastic values"""
        # For stochastic, we need high, low, close - using price as close
        # In real implementation, you'd pass Bar object with OHLC data
        high = price * 1.001  # Approximate high
        low = price * 0.999   # Approximate low
        close = price
        
        self._add_data_point(price, volume, timestamp)
        self.highs.append(high)
        self.lows.append(low)
        
        if len(self.prices) < self.k_period:
            return {}
        
        # Get the window of data
        window_highs = self.highs[-self.k_period:]
        window_lows = self.lows[-self.k_period:]
        window_volumes = self.volumes[-self.k_period:] if self.config.volume_weighted else [1] * self.k_period
        
        # Volume-weighted highest high and lowest low
        if self.config.volume_weighted and sum(window_volumes) > 0:
            # Weight the extremes by volume
            weighted_high = max(h * v for h, v in zip(window_highs, window_volumes)) / max(window_volumes)
            weighted_low = min(l * v for l, v in zip(window_lows, window_volumes)) / max(window_volumes)
        else:
            weighted_high = max(window_highs)
            weighted_low = min(window_lows)
        
        # Calculate %K
        if weighted_high == weighted_low:
            k_percent = 50.0  # Neutral when no range
        else:
            k_percent = ((close - weighted_low) / (weighted_high - weighted_low)) * 100
        
        self.k_values.append(k_percent)
        
        # Calculate %D (moving average of %K)
        if len(self.k_values) >= self.d_period:
            recent_k = self.k_values[-self.d_period:]
            d_percent = np.mean(recent_k)
        else:
            d_percent = k_percent
        
        # Maintain rolling window
        max_length = max(self.k_period * 2, 50)
        if len(self.highs) > max_length:
            self.highs = self.highs[-max_length:]
            self.lows = self.lows[-max_length:]
            self.k_values = self.k_values[-max_length:]
        
        return {
            'main': k_percent,
            'k_percent': k_percent,
            'd_percent': d_percent,
            'highest_high': weighted_high,
            'lowest_low': weighted_low
        }
    
    def _generate_signal(self, current_value: float, previous_value: float = None) -> Tuple[SignalType, float]:
        """Generate Stochastic-specific trading signals"""
        if len(self.results) < 2:
            return SignalType.NEUTRAL, 0.0
        
        current_k = current_value
        current_result = self.results[-1]
        current_d = current_result.metadata.get('all_values', {}).get('d_percent', current_k)
        
        # Overbought/Oversold signals
        if current_k >= 80 and current_d >= 80:
            return SignalType.SELL, min(1.0, (current_k - 80) / 20)
        elif current_k <= 20 and current_d <= 20:
            return SignalType.BUY, min(1.0, (20 - current_k) / 20)
        
        # %K crosses %D signals
        if len(self.results) >= 2:
            prev_result = self.results[-2]
            prev_k = prev_result.value
            prev_d = prev_result.metadata.get('all_values', {}).get('d_percent', prev_k)
            
            # Bullish crossover
            if current_k > current_d and prev_k <= prev_d:
                return SignalType.BUY, 0.7
            # Bearish crossover
            elif current_k < current_d and prev_k >= prev_d:
                return SignalType.SELL, 0.7
        
        return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.highs.clear()
        self.lows.clear()
        self.k_values.clear()
        logger.debug(f"{self.name} reset")

class VolumeWeightedWilliamsR(VolumeWeightedIndicator):
    """Volume-Weighted Williams %R
    
    Volume-weighted version of Williams %R oscillator for improved
    momentum analysis in varying volume conditions.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "VW_WilliamsR")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.highs = []
        self.lows = []
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted Williams %R"""
        start_time = datetime.now()
        
        # Approximate OHLC from price
        high = price * 1.001
        low = price * 0.999
        close = price
        
        self._add_data_point(price, volume, timestamp)
        self.highs.append(high)
        self.lows.append(low)
        
        if len(self.prices) < self.config.period:
            return None
        
        # Get the window of data
        window_highs = self.highs[-self.config.period:]
        window_lows = self.lows[-self.config.period:]
        window_volumes = self.volumes[-self.config.period:] if self.config.volume_weighted else [1] * self.config.period
        
        # Volume-weighted highest high and lowest low
        if self.config.volume_weighted and sum(window_volumes) > 0:
            # Weight extremes by volume
            volume_weighted_highs = [h * v for h, v in zip(window_highs, window_volumes)]
            volume_weighted_lows = [l * v for l, v in zip(window_lows, window_volumes)]
            
            highest_high = max(volume_weighted_highs) / max(window_volumes)
            lowest_low = min(volume_weighted_lows) / max(window_volumes)
        else:
            highest_high = max(window_highs)
            lowest_low = min(window_lows)
        
        # Calculate Williams %R
        if highest_high == lowest_low:
            williams_r = -50.0  # Neutral when no range
        else:
            williams_r = ((highest_high - close) / (highest_high - lowest_low)) * -100
        
        # Generate signal
        signal, confidence = self._generate_williams_signal(williams_r)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=williams_r,
            signal=signal,
            confidence=confidence,
            metadata={
                'highest_high': highest_high,
                'lowest_low': lowest_low,
                'range': highest_high - lowest_low,
                'volume_weighted': self.config.volume_weighted
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = self.config.period * 3
        if len(self.highs) > max_length:
            self.highs = self.highs[-max_length:]
            self.lows = self.lows[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _generate_williams_signal(self, williams_r: float) -> Tuple[SignalType, float]:
        """Generate Williams %R specific signals"""
        if williams_r <= -80:
            return SignalType.BUY, min(1.0, (-80 - williams_r) / 20)
        elif williams_r >= -20:
            return SignalType.SELL, min(1.0, (williams_r + 20) / 20)
        else:
            return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.highs.clear()
        self.lows.clear()
        logger.debug(f"{self.name} reset")

class VolumeWeightedMFI(VolumeWeightedIndicator):
    """Volume-Weighted Money Flow Index
    
    Enhanced Money Flow Index that incorporates additional volume weighting
    for more accurate money flow analysis.
    """
    
    def __init__(self, config: IndicatorConfig):
        super().__init__(config, "VW_MFI")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.typical_prices = []
        self.money_flows = []
        self.positive_flows = []
        self.negative_flows = []
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Volume-Weighted MFI"""
        start_time = datetime.now()
        
        # Use price as typical price (in real implementation, use (H+L+C)/3)
        typical_price = price
        
        self._add_data_point(price, volume, timestamp)
        self.typical_prices.append(typical_price)
        
        if len(self.typical_prices) < 2:
            return None
        
        # Calculate money flow
        money_flow = typical_price * volume
        
        # Enhanced volume weighting
        if self.config.volume_weighted and len(self.volumes) > 1:
            avg_volume = np.mean(self.volumes[-min(self.config.period, len(self.volumes)):]) if self.volumes else 1
            volume_multiplier = min(2.0, max(0.5, volume / avg_volume)) if avg_volume > 0 else 1.0
            money_flow *= volume_multiplier
        
        self.money_flows.append(money_flow)
        
        # Determine if money flow is positive or negative
        if typical_price > self.typical_prices[-2]:
            self.positive_flows.append(money_flow)
            self.negative_flows.append(0)
        elif typical_price < self.typical_prices[-2]:
            self.positive_flows.append(0)
            self.negative_flows.append(money_flow)
        else:
            self.positive_flows.append(0)
            self.negative_flows.append(0)
        
        if len(self.money_flows) < self.config.period:
            return None
        
        # Calculate MFI over the period
        recent_positive = sum(self.positive_flows[-self.config.period:])
        recent_negative = sum(self.negative_flows[-self.config.period:])
        
        if recent_negative == 0:
            mfi = 100.0
        else:
            money_ratio = recent_positive / recent_negative
            mfi = 100 - (100 / (1 + money_ratio))
        
        # Generate signal
        signal, confidence = self._generate_mfi_signal(mfi)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=mfi,
            signal=signal,
            confidence=confidence,
            metadata={
                'positive_flow': recent_positive,
                'negative_flow': recent_negative,
                'money_ratio': recent_positive / recent_negative if recent_negative > 0 else float('inf'),
                'typical_price': typical_price,
                'money_flow': money_flow
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = self.config.period * 3
        if len(self.money_flows) > max_length:
            self.typical_prices = self.typical_prices[-max_length:]
            self.money_flows = self.money_flows[-max_length:]
            self.positive_flows = self.positive_flows[-max_length:]
            self.negative_flows = self.negative_flows[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _generate_mfi_signal(self, mfi_value: float) -> Tuple[SignalType, float]:
        """Generate MFI-specific trading signals"""
        if mfi_value >= 80:
            return SignalType.SELL, min(1.0, (mfi_value - 80) / 20)
        elif mfi_value <= 20:
            return SignalType.BUY, min(1.0, (20 - mfi_value) / 20)
        else:
            return SignalType.NEUTRAL, 0.0
    
    def reset(self) -> None:
        """Reset indicator state"""
        super().reset()
        self.typical_prices.clear()
        self.money_flows.clear()
        self.positive_flows.clear()
        self.negative_flows.clear()
        logger.debug(f"{self.name} reset")

class InstitutionalVolumeWeightedMACD(VolumeWeightedIndicator):
    """
    Institutional Volume-Weighted MACD with Smart Money Flow Detection
    
    Enhanced MACD oscillator that incorporates:
    - Volume-weighted price calculations
    - Smart money flow detection
    - Institutional order flow analysis
    - Adaptive signal line smoothing
    - Market regime-aware thresholds
    """
    
    def __init__(self, config: IndicatorConfig, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9,
                 smart_money_threshold: float = 0.7, institutional_threshold: float = 0.6):
        super().__init__(config, "Institutional_VW_MACD")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.smart_money_threshold = smart_money_threshold
        self.institutional_threshold = institutional_threshold
        
        # Data storage
        self.fast_ema_values = []
        self.slow_ema_values = []
        self.macd_values = []
        self.signal_values = []
        self.histogram_values = []
        
        # Institutional analysis storage
        self.smart_money_flows = []
        self.institutional_factors = []
        self.market_regimes = []
        
        # EMA multipliers
        self.fast_multiplier = 2.0 / (fast_period + 1)
        self.slow_multiplier = 2.0 / (slow_period + 1)
        self.signal_multiplier = 2.0 / (signal_period + 1)
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Institutional Volume-Weighted MACD"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < 2:
            return None
        
        # Detect smart money flow and institutional activity
        price_change = price - self.prices[-2]
        smart_money_factor = self._detect_smart_money_flow(price, volume, price_change)
        institutional_factor = self._detect_institutional_activity(price, volume)
        market_regime = self._detect_market_regime()
        
        self.smart_money_flows.append(smart_money_factor)
        self.institutional_factors.append(institutional_factor)
        self.market_regimes.append(market_regime)
        
        # Calculate volume-weighted price with institutional factors
        vw_price = self._calculate_institutional_weighted_price(price, volume, smart_money_factor, institutional_factor)
        
        # Calculate EMAs
        fast_ema = self._calculate_institutional_ema(vw_price, self.fast_ema_values, self.fast_multiplier, smart_money_factor)
        slow_ema = self._calculate_institutional_ema(vw_price, self.slow_ema_values, self.slow_multiplier, institutional_factor)
        
        self.fast_ema_values.append(fast_ema)
        self.slow_ema_values.append(slow_ema)
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        self.macd_values.append(macd_line)
        
        # Calculate signal line
        if len(self.signal_values) == 0:
            signal_line = macd_line
        else:
            # Adaptive signal smoothing based on market regime
            adaptive_multiplier = self._get_adaptive_signal_multiplier(market_regime)
            signal_line = self.signal_values[-1] + adaptive_multiplier * (macd_line - self.signal_values[-1])
        
        self.signal_values.append(signal_line)
        
        # Calculate histogram
        histogram = macd_line - signal_line
        self.histogram_values.append(histogram)
        
        # Generate enhanced signal
        signal_type, confidence = self._generate_enhanced_macd_signal(
            macd_line, signal_line, histogram, smart_money_factor, institutional_factor, market_regime
        )
        
        # Create result with enhanced metadata
        result = IndicatorResult(
            timestamp=timestamp,
            value=macd_line,
            signal=signal_type,
            confidence=confidence,
            metadata={
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram,
                'fast_ema': fast_ema,
                'slow_ema': slow_ema,
                'smart_money_factor': smart_money_factor,
                'institutional_factor': institutional_factor,
                'market_regime': market_regime,
                'vw_price': vw_price,
                'adaptive_signal_multiplier': self._get_adaptive_signal_multiplier(market_regime)
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = max(self.slow_period * 3, 100)
        if len(self.fast_ema_values) > max_length:
            self.fast_ema_values = self.fast_ema_values[-max_length:]
            self.slow_ema_values = self.slow_ema_values[-max_length:]
            self.macd_values = self.macd_values[-max_length:]
            self.signal_values = self.signal_values[-max_length:]
            self.histogram_values = self.histogram_values[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _calculate_institutional_weighted_price(self, price: float, volume: float, 
                                                smart_money_factor: float, institutional_factor: float) -> float:
        """Calculate price weighted by institutional factors"""
        # Base volume weight
        if len(self.volumes) < 2:
            return price
        
        avg_volume = np.mean(self.volumes[-10:]) if len(self.volumes) >= 10 else np.mean(self.volumes)
        volume_weight = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Institutional enhancement
        institutional_weight = 1.0 + (smart_money_factor - 0.5) * 0.3 + (institutional_factor - 0.5) * 0.2
        
        # Combined weighting
        total_weight = volume_weight * institutional_weight
        return price * total_weight
    
    def _calculate_institutional_ema(self, price: float, ema_values: List[float], multiplier: float, 
                                     institutional_factor: float) -> float:
        """Calculate EMA with institutional factor adjustment"""
        if not ema_values:
            return price
        
        # Adaptive multiplier based on institutional activity
        adaptive_multiplier = multiplier * (1.0 + (institutional_factor - 0.5) * 0.2)
        adaptive_multiplier = max(0.01, min(0.5, adaptive_multiplier))
        
        return ema_values[-1] + adaptive_multiplier * (price - ema_values[-1])
    
    def _get_adaptive_signal_multiplier(self, market_regime: str) -> float:
        """Get adaptive signal line multiplier based on market regime"""
        base_multiplier = self.signal_multiplier
        
        if market_regime == "HIGH_VOLATILITY":
            return base_multiplier * 0.7  # Slower signal in volatile markets
        elif market_regime in ["BULLISH_MOMENTUM", "BEARISH_MOMENTUM"]:
            return base_multiplier * 1.3  # Faster signal in trending markets
        else:
            return base_multiplier
    
    def _generate_enhanced_macd_signal(self, macd_line: float, signal_line: float, histogram: float,
                                       smart_money_factor: float, institutional_factor: float, 
                                       market_regime: str) -> Tuple[SignalType, float]:
        """Generate enhanced MACD signal with institutional analysis"""
        # Base signal from MACD crossover
        if macd_line > signal_line and len(self.macd_values) >= 2:
            if self.macd_values[-2] <= (self.signal_values[-2] if len(self.signal_values) >= 2 else signal_line):
                # Bullish crossover
                base_confidence = min(0.8, abs(histogram) * 10)
                signal_type = SignalType.BUY
            else:
                # Continued bullish
                base_confidence = min(0.6, abs(histogram) * 5)
                signal_type = SignalType.BUY
        elif macd_line < signal_line and len(self.macd_values) >= 2:
            if self.macd_values[-2] >= (self.signal_values[-2] if len(self.signal_values) >= 2 else signal_line):
                # Bearish crossover
                base_confidence = min(0.8, abs(histogram) * 10)
                signal_type = SignalType.SELL
            else:
                # Continued bearish
                base_confidence = min(0.6, abs(histogram) * 5)
                signal_type = SignalType.SELL
        else:
            return SignalType.NEUTRAL, 0.2
        
        # Enhance with institutional factors
        smart_money_boost = (smart_money_factor - 0.5) * 0.25
        institutional_boost = (institutional_factor - 0.5) * 0.2
        
        # Market regime adjustment
        regime_adjustment = 0.0
        if market_regime in ["BULLISH_MOMENTUM", "BEARISH_MOMENTUM"]:
            regime_adjustment = 0.15  # Higher confidence in trending markets
        elif market_regime == "HIGH_VOLATILITY":
            regime_adjustment = -0.1  # Lower confidence in volatile markets
        
        # Final confidence
        enhanced_confidence = base_confidence + smart_money_boost + institutional_boost + regime_adjustment
        enhanced_confidence = max(0.1, min(0.95, enhanced_confidence))
        
        return signal_type, enhanced_confidence
    
    def _detect_smart_money_flow(self, price: float, volume: float, price_change: float) -> float:
        """Detect smart money flow patterns"""
        if len(self.volumes) < 5:
            return 0.5
        
        # Calculate volume percentile
        recent_volumes = self.volumes[-10:] if len(self.volumes) >= 10 else self.volumes
        volume_percentile = np.percentile(recent_volumes, 75) if recent_volumes else volume
        
        # Smart money indicators
        volume_factor = min(2.0, volume / volume_percentile) if volume_percentile > 0 else 1.0
        
        # Price momentum factor
        momentum_factor = 1.0
        if len(self.prices) >= 3:
            recent_changes = [self.prices[i] - self.prices[i-1] for i in range(-2, 0)]
            if all(change > 0 for change in recent_changes) and price_change > 0:
                momentum_factor = 1.3  # Consistent upward momentum
            elif all(change < 0 for change in recent_changes) and price_change < 0:
                momentum_factor = 1.3  # Consistent downward momentum
        
        # Combined smart money factor
        smart_factor = (volume_factor * momentum_factor - 1.0) * 0.5 + 0.5
        return max(0.1, min(0.9, smart_factor))
    
    def _detect_institutional_activity(self, price: float, volume: float) -> float:
        """Detect institutional order flow activity"""
        if len(self.volumes) < 3:
            return 0.5
        
        # Large order detection
        avg_volume = np.mean(self.volumes[-20:]) if len(self.volumes) >= 20 else np.mean(self.volumes)
        large_order_threshold = avg_volume * 2.5
        
        # Institutional flow patterns
        if volume > large_order_threshold:
            # Large volume suggests institutional activity
            institutional_strength = min(0.9, 0.5 + (volume / large_order_threshold - 1) * 0.2)
        else:
            # Check for sustained volume patterns
            recent_volumes = self.volumes[-5:]
            volume_consistency = 1.0 - (np.std(recent_volumes) / np.mean(recent_volumes)) if np.mean(recent_volumes) > 0 else 0.5
            institutional_strength = 0.3 + volume_consistency * 0.4
        
        return max(0.1, min(0.9, institutional_strength))
    
    def _detect_market_regime(self) -> str:
        """Detect current market regime"""
        if len(self.prices) < 10:
            return "UNKNOWN"
        
        recent_prices = self.prices[-10:]
        recent_volumes = self.volumes[-10:]
        
        # Price trend analysis
        price_trend = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] if recent_prices[0] != 0 else 0
        
        # Volume trend analysis
        volume_trend = (np.mean(recent_volumes[-5:]) - np.mean(recent_volumes[:5])) / np.mean(recent_volumes[:5]) if np.mean(recent_volumes[:5]) > 0 else 0
        
        # Volatility analysis
        price_changes = [recent_prices[i] - recent_prices[i-1] for i in range(1, len(recent_prices))]
        volatility = np.std(price_changes) / np.mean(recent_prices) if np.mean(recent_prices) > 0 else 0
        
        # Regime classification
        if volatility > 0.02:  # High volatility
            return "HIGH_VOLATILITY"
        elif price_trend > 0.05 and volume_trend > 0.2:
            return "BULLISH_MOMENTUM"
        elif price_trend < -0.05 and volume_trend > 0.2:
            return "BEARISH_MOMENTUM"
        elif abs(price_trend) < 0.02:
            return "CONSOLIDATION"
        else:
            return "TRENDING"
    
    def reset(self) -> None:
        """Reset the indicator state"""
        super().reset()
        self.fast_ema_values.clear()
        self.slow_ema_values.clear()
        self.macd_values.clear()
        self.signal_values.clear()
        self.histogram_values.clear()
        self.smart_money_flows.clear()
        self.institutional_factors.clear()
        self.market_regimes.clear()
        logger.debug(f"{self.name} reset")

class SmartMoneyFlowOscillator(VolumeWeightedIndicator):
    """
    Smart Money Flow Oscillator - Proprietary oscillator for detecting institutional activity
    
    This oscillator combines:
    - Volume flow analysis
    - Price momentum detection
    - Order flow imbalance detection
    - Liquidity analysis
    - Market microstructure signals
    """
    
    def __init__(self, config: IndicatorConfig, sensitivity: float = 1.0):
        super().__init__(config, "Smart_Money_Flow_Oscillator")
        self.indicator_type = IndicatorType.OSCILLATOR
        self.sensitivity = sensitivity
        
        # Data storage
        self.money_flows = []
        self.flow_ratios = []
        self.order_imbalances = []
        self.liquidity_flows = []
        
        # Analysis storage
        self.smart_money_scores = []
        self.flow_momentum = []
        self.market_pressure = []
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Smart Money Flow Oscillator"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < 2:
            return None
        
        # Calculate money flow components
        price_change = price - self.prices[-2]
        typical_price = price  # Simplified for single price input
        money_flow = typical_price * volume
        
        # Classify money flow
        if price_change > 0:
            positive_flow = money_flow
            negative_flow = 0
        elif price_change < 0:
            positive_flow = 0
            negative_flow = money_flow
        else:
            positive_flow = money_flow * 0.5
            negative_flow = money_flow * 0.5
        
        self.money_flows.append((positive_flow, negative_flow))
        
        # Calculate flow ratio
        if len(self.money_flows) >= self.config.period:
            total_positive = sum(flow[0] for flow in self.money_flows[-self.config.period:])
            total_negative = sum(flow[1] for flow in self.money_flows[-self.config.period:])
            
            if total_positive + total_negative > 0:
                flow_ratio = (total_positive - total_negative) / (total_positive + total_negative)
            else:
                flow_ratio = 0.0
        else:
            flow_ratio = 0.0
        
        self.flow_ratios.append(flow_ratio)
        
        # Calculate order imbalance
        order_imbalance = self._calculate_order_imbalance(price, volume)
        self.order_imbalances.append(order_imbalance)
        
        # Calculate liquidity flow
        liquidity_flow = self._calculate_liquidity_flow(price, volume)
        self.liquidity_flows.append(liquidity_flow)
        
        # Calculate smart money score
        smart_money_score = self._calculate_smart_money_score(flow_ratio, order_imbalance, liquidity_flow)
        self.smart_money_scores.append(smart_money_score)
        
        # Calculate flow momentum
        flow_momentum = self._calculate_flow_momentum()
        self.flow_momentum.append(flow_momentum)
        
        # Calculate market pressure
        market_pressure = self._calculate_market_pressure()
        self.market_pressure.append(market_pressure)
        
        # Generate signal
        signal_type, confidence = self._generate_smart_money_signal(
            smart_money_score, flow_momentum, market_pressure
        )
        
        # Create result
        result = IndicatorResult(
            timestamp=timestamp,
            value=smart_money_score,
            signal=signal_type,
            confidence=confidence,
            metadata={
                'smart_money_score': smart_money_score,
                'flow_ratio': flow_ratio,
                'order_imbalance': order_imbalance,
                'liquidity_flow': liquidity_flow,
                'flow_momentum': flow_momentum,
                'market_pressure': market_pressure,
                'positive_flow': positive_flow,
                'negative_flow': negative_flow
            }
        )
        
        self.results.append(result)
        
        # Maintain rolling window
        max_length = self.config.period * 3
        if len(self.money_flows) > max_length:
            self.money_flows = self.money_flows[-max_length:]
            self.flow_ratios = self.flow_ratios[-max_length:]
            self.order_imbalances = self.order_imbalances[-max_length:]
            self.liquidity_flows = self.liquidity_flows[-max_length:]
            self.smart_money_scores = self.smart_money_scores[-max_length:]
            self.flow_momentum = self.flow_momentum[-max_length:]
            self.market_pressure = self.market_pressure[-max_length:]
        
        # Track performance
        calc_time = (datetime.now() - start_time).total_seconds()
        self.calculation_times.append(calc_time)
        
        if not self.initialized and len(self.results) >= self.config.min_periods:
            self.initialized = True
            logger.info(f"{self.name} initialized with {len(self.results)} periods")
        
        return result
    
    def _calculate_order_imbalance(self, price: float, volume: float) -> float:
        """Calculate order flow imbalance"""
        if len(self.volumes) < 5:
            return 0.0
        
        # Volume surge detection
        avg_volume = np.mean(self.volumes[-5:])
        volume_surge = (volume - avg_volume) / avg_volume if avg_volume > 0 else 0.0
        
        # Price impact analysis
        if len(self.prices) >= 3:
            price_impact = abs(price - self.prices[-2]) / self.prices[-2] if self.prices[-2] != 0 else 0.0
        else:
            price_impact = 0.0
        
        # Combined imbalance score
        imbalance = (volume_surge * 0.6 + price_impact * 100 * 0.4) * self.sensitivity
        return max(-1.0, min(1.0, imbalance))
    
    def _calculate_liquidity_flow(self, price: float, volume: float) -> float:
        """Calculate liquidity flow patterns"""
        if len(self.volumes) < 3:
            return 0.0
        
        # Volume consistency
        recent_volumes = self.volumes[-3:]
        volume_std = np.std(recent_volumes)
        volume_mean = np.mean(recent_volumes)
        consistency = 1.0 - (volume_std / volume_mean) if volume_mean > 0 else 0.0
        
        # Price stability
        if len(self.prices) >= 3:
            recent_prices = self.prices[-3:]
            price_std = np.std(recent_prices)
            price_mean = np.mean(recent_prices)
            stability = 1.0 - (price_std / price_mean) if price_mean > 0 else 0.0
        else:
            stability = 0.0
        
        # Combined liquidity flow
        liquidity_flow = (consistency * 0.6 + stability * 0.4) * 2.0 - 1.0  # Scale to [-1, 1]
        return max(-1.0, min(1.0, liquidity_flow))
    
    def _calculate_smart_money_score(self, flow_ratio: float, order_imbalance: float, liquidity_flow: float) -> float:
        """Calculate overall smart money score"""
        # Weighted combination of factors
        score = (flow_ratio * 0.4 + order_imbalance * 0.35 + liquidity_flow * 0.25) * 100
        return max(-100.0, min(100.0, score))
    
    def _calculate_flow_momentum(self) -> float:
        """Calculate momentum of money flows"""
        if len(self.smart_money_scores) < 3:
            return 0.0
        
        recent_scores = self.smart_money_scores[-3:]
        momentum = (recent_scores[-1] - recent_scores[0]) / 2.0  # Momentum over 3 periods
        return max(-50.0, min(50.0, momentum))
    
    def _calculate_market_pressure(self) -> float:
        """Calculate overall market pressure"""
        if len(self.flow_ratios) < 5:
            return 0.0
        
        recent_ratios = self.flow_ratios[-5:]
        pressure = np.mean(recent_ratios) * 100
        return max(-100.0, min(100.0, pressure))
    
    def _generate_smart_money_signal(self, smart_money_score: float, flow_momentum: float, 
                                     market_pressure: float) -> Tuple[SignalType, float]:
        """Generate trading signal based on smart money analysis"""
        # Strong smart money signals
        if smart_money_score > 60 and flow_momentum > 20:
            return SignalType.BUY, min(0.9, (smart_money_score + flow_momentum) / 100)
        elif smart_money_score < -60 and flow_momentum < -20:
            return SignalType.SELL, min(0.9, abs(smart_money_score + flow_momentum) / 100)
        
        # Moderate signals
        elif smart_money_score > 30 and market_pressure > 20:
            return SignalType.BUY, min(0.7, (smart_money_score + market_pressure) / 120)
        elif smart_money_score < -30 and market_pressure < -20:
            return SignalType.SELL, min(0.7, abs(smart_money_score + market_pressure) / 120)
        
        # Weak signals
        elif smart_money_score > 15:
            return SignalType.BUY, min(0.4, smart_money_score / 50)
        elif smart_money_score < -15:
            return SignalType.SELL, min(0.4, abs(smart_money_score) / 50)
        
        return SignalType.NEUTRAL, 0.1
    
    def reset(self) -> None:
        """Reset the indicator state"""
        super().reset()
        self.money_flows.clear()
        self.flow_ratios.clear()
        self.order_imbalances.clear()
        self.liquidity_flows.clear()
        self.smart_money_scores.clear()
        self.flow_momentum.clear()
        self.market_pressure.clear()
        logger.debug(f"{self.name} reset")

# Factory function for creating oscillator indicators
def create_oscillator_indicator(indicator_type: str, config: IndicatorConfig, **kwargs) -> VolumeWeightedIndicator:
    """Factory function to create oscillator indicators"""
    indicators = {
        'enhanced_vw_rsi': Enhanced_VW_RSI,
        'enhanced_vw_macd': lambda cfg: Enhanced_VW_MACD(cfg, **kwargs),
        'institutional_vw_macd': InstitutionalVolumeWeightedMACD,
        'smart_money_flow': SmartMoneyFlowOscillator,
        'vw_rsi': Enhanced_VW_RSI,  # Default to enhanced version
        'vw_macd': lambda cfg: Enhanced_VW_MACD(cfg, **kwargs),  # Default to enhanced version
        'vw_stoch': lambda cfg: VolumeWeightedStochastic(cfg, **kwargs),
        'vw_williams_r': VolumeWeightedWilliamsR,
        'vw_mfi': VolumeWeightedMFI
    }
    
    indicator_factory = indicators.get(indicator_type.lower())
    if not indicator_factory:
        raise ValueError(f"Unknown oscillator indicator type: {indicator_type}")
    
    if callable(indicator_factory) and indicator_type.lower() in ['vw_macd', 'enhanced_vw_macd', 'vw_stoch']:
        return indicator_factory(config)
    else:
        return indicator_factory(config)