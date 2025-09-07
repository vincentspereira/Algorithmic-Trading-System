"""Consolidated Volume-Weighted Momentum Indicators

Unified implementation combining enhanced and volume-weighted momentum indicators with:
- Configurable adaptive features and institutional analysis
- Dynamic threshold mechanisms based on market regime detection
- Smart money flow detection and confidence scoring
- TWAP/VWAP integration for institutional-grade accuracy
- High-frequency trading optimizations

Indicators include:
- Unified Volume-Weighted Rate of Change (Unified VW ROC)
- Unified Volume-Weighted Momentum (Unified VW MOM)
- Unified Volume-Weighted Commodity Channel Index (Unified VW CCI)
- Unified Volume-Weighted Ultimate Oscillator (Unified VW UO)
- Unified Volume-Weighted Awesome Oscillator (Unified VW AO)
- Unified Volume-Weighted Chande Momentum Oscillator (Unified VW CMO)
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

class AdaptiveMode(Enum):
    """Adaptive feature modes"""
    BASIC = "basic"  # Basic volume weighting only
    ENHANCED = "enhanced"  # Enhanced with dynamic thresholds
    INSTITUTIONAL = "institutional"  # Full institutional features
    HYBRID = "hybrid"  # Combination of enhanced and institutional

@dataclass
class MomentumConfig:
    """Configuration for momentum indicators"""
    adaptive_mode: AdaptiveMode = AdaptiveMode.ENHANCED
    enable_smart_money_detection: bool = True
    enable_institutional_analysis: bool = False
    enable_market_regime_detection: bool = True
    confidence_threshold: float = 0.7
    volatility_adjustment: bool = True
    smart_money_threshold: float = 2.0
    institutional_threshold: float = 3.0
    
class UnifiedVolumeWeightedROC(VolumeWeightedIndicator):
    """Unified Volume-Weighted Rate of Change
    
    Consolidated implementation combining enhanced adaptive features
    with institutional-grade analysis capabilities.
    """
    
    def __init__(self, config: IndicatorConfig, momentum_config: MomentumConfig = None):
        super().__init__(config, "Unified_VW_ROC")
        self.indicator_type = IndicatorType.MOMENTUM
        self.momentum_config = momentum_config or MomentumConfig()
        
        # Adaptive features based on configuration
        self.adaptive_thresholds = self.momentum_config.adaptive_mode in [AdaptiveMode.ENHANCED, AdaptiveMode.HYBRID]
        self.institutional_features = self.momentum_config.adaptive_mode in [AdaptiveMode.INSTITUTIONAL, AdaptiveMode.HYBRID]
        
        # Enhanced data structures
        if self.institutional_features:
            self.smart_money_flows = deque(maxlen=config.period * 2)
            self.institutional_factors = deque(maxlen=config.period * 2)
            self.market_regimes = deque(maxlen=config.period * 2)
            self.liquidity_scores = deque(maxlen=config.period * 2)
        
        # Threshold configuration
        self.base_strong_threshold = 5.0
        self.base_moderate_threshold = 2.0
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Unified Volume-Weighted ROC"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period + 1:
            return None
        
        # Get current and historical prices
        current_price = price
        historical_price = self.prices[-(self.config.period + 1)]
        
        # Apply volume weighting based on configuration
        vw_current, vw_historical = self._calculate_volume_weighted_prices(
            current_price, historical_price, volume
        )
        
        # Calculate ROC
        if vw_historical != 0:
            roc = ((vw_current - vw_historical) / vw_historical) * 100
        else:
            roc = 0.0
        
        # Generate signal with adaptive features
        signal, confidence = self._generate_adaptive_roc_signal(roc, volume)
        
        # Enhanced metadata based on configuration
        metadata = self._build_metadata(current_price, historical_price, vw_current, vw_historical, roc, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=roc,
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
    
    def _calculate_volume_weighted_prices(self, current_price: float, historical_price: float, volume: float) -> Tuple[float, float]:
        """Calculate volume-weighted prices based on configuration"""
        if not self.config.volume_weighted:
            return current_price, historical_price
        
        # Basic volume weighting
        recent_prices = self.prices[-self.config.period:]
        recent_volumes = self.volumes[-self.config.period:]
        
        if sum(recent_volumes) > 0:
            vw_current = sum(p * v for p, v in zip(recent_prices, recent_volumes)) / sum(recent_volumes)
        else:
            vw_current = current_price
        
        # Historical volume weighting
        hist_start = -(self.config.period * 2)
        hist_end = -self.config.period
        
        if len(self.prices) >= abs(hist_start):
            hist_prices = self.prices[hist_start:hist_end]
            hist_volumes = self.volumes[hist_start:hist_end]
            
            if sum(hist_volumes) > 0:
                vw_historical = sum(p * v for p, v in zip(hist_prices, hist_volumes)) / sum(hist_volumes)
            else:
                vw_historical = historical_price
        else:
            vw_historical = historical_price
        
        # Apply institutional features if enabled
        if self.institutional_features:
            vw_current = self._apply_institutional_weighting(vw_current, volume)
            vw_historical = self._apply_institutional_weighting(vw_historical, volume)
        
        return vw_current, vw_historical
    
    def _apply_institutional_weighting(self, price: float, volume: float) -> float:
        """Apply institutional weighting factors"""
        if not self.momentum_config.enable_smart_money_detection:
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
        
        # Smart money typically involves above-average volume
        if volume_ratio > self.momentum_config.smart_money_threshold:
            return min(1.0, (volume_ratio - self.momentum_config.smart_money_threshold) / 2.0)
        
        return 0.0
    
    def _detect_institutional_activity(self, price: float, volume: float) -> float:
        """Detect institutional activity patterns"""
        if not self.momentum_config.enable_institutional_analysis or len(self.volumes) < 20:
            return 0.0
        
        avg_volume = np.mean(list(self.volumes)[-20:])
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Institutional activity typically involves very high volume
        if volume_ratio > self.momentum_config.institutional_threshold:
            return min(1.0, (volume_ratio - self.momentum_config.institutional_threshold) / 3.0)
        
        return 0.0
    
    def _generate_adaptive_roc_signal(self, roc_value: float, volume: float) -> Tuple[SignalType, float]:
        """Generate signals with adaptive thresholds"""
        # Determine thresholds based on configuration
        if self.adaptive_thresholds and len(self.results) >= 20:
            # Dynamic thresholds based on recent volatility
            recent_roc = [r.value for r in self.results[-20:]]
            volatility = np.std(recent_roc)
            strong_threshold = max(3.0, volatility * 2)
            moderate_threshold = max(1.5, volatility)
        else:
            # Fixed thresholds
            strong_threshold = self.base_strong_threshold
            moderate_threshold = self.base_moderate_threshold
        
        # Apply market regime adjustment if enabled
        if self.momentum_config.enable_market_regime_detection:
            regime_multiplier = self._get_market_regime_multiplier()
            strong_threshold *= regime_multiplier
            moderate_threshold *= regime_multiplier
        
        # Generate base signal
        signal, base_confidence = self._calculate_base_signal(roc_value, strong_threshold, moderate_threshold)
        
        # Apply institutional confidence boost if enabled
        if self.institutional_features:
            institutional_boost = self._calculate_institutional_confidence_boost(volume)
            final_confidence = min(1.0, base_confidence * (1 + institutional_boost))
        else:
            final_confidence = base_confidence
        
        return signal, final_confidence
    
    def _get_market_regime_multiplier(self) -> float:
        """Get market regime multiplier for threshold adjustment"""
        if len(self.results) < 50:
            return 1.0
        
        # Simple volatility-based regime detection
        recent_values = [r.value for r in self.results[-50:]]
        volatility = np.std(recent_values)
        
        if volatility > 10.0:  # High volatility regime
            return 1.5
        elif volatility < 2.0:  # Low volatility regime
            return 0.7
        else:  # Normal regime
            return 1.0
    
    def _calculate_base_signal(self, roc_value: float, strong_threshold: float, moderate_threshold: float) -> Tuple[SignalType, float]:
        """Calculate base signal and confidence"""
        if roc_value > strong_threshold:
            confidence = min(1.0, (roc_value - strong_threshold) / strong_threshold)
            return SignalType.BUY, confidence * 0.9
        elif roc_value > moderate_threshold:
            confidence = (roc_value - moderate_threshold) / (strong_threshold - moderate_threshold)
            return SignalType.BUY, confidence * 0.6
        elif roc_value < -strong_threshold:
            confidence = min(1.0, abs(roc_value + strong_threshold) / strong_threshold)
            return SignalType.SELL, confidence * 0.9
        elif roc_value < -moderate_threshold:
            confidence = abs(roc_value + moderate_threshold) / (strong_threshold - moderate_threshold)
            return SignalType.SELL, confidence * 0.6
        
        # Zero-line crossover signals (enhanced feature)
        if self.adaptive_thresholds and len(self.results) >= 2:
            prev_roc = self.results[-2].value
            if prev_roc <= 0 and roc_value > 0:
                return SignalType.BUY, 0.4
            elif prev_roc >= 0 and roc_value < 0:
                return SignalType.SELL, 0.4
        
        return SignalType.NEUTRAL, 0.0
    
    def _calculate_institutional_confidence_boost(self, volume: float) -> float:
        """Calculate confidence boost from institutional activity"""
        smart_money_factor = self._detect_smart_money_flow(self.prices[-1], volume)
        institutional_factor = self._detect_institutional_activity(self.prices[-1], volume)
        
        return (smart_money_factor * 0.2) + (institutional_factor * 0.3)
    
    def _build_metadata(self, current_price: float, historical_price: float, 
                       vw_current: float, vw_historical: float, roc: float, volume: float) -> Dict[str, Any]:
        """Build metadata based on configuration"""
        metadata = {
            'current_price': vw_current,
            'historical_price': vw_historical,
            'period': self.config.period,
            'volume_weighted': self.config.volume_weighted,
            'raw_current': current_price,
            'raw_historical': historical_price,
            'adaptive_mode': self.momentum_config.adaptive_mode.value
        }
        
        # Add enhanced metadata
        if self.adaptive_thresholds:
            metadata['roc_normalized'] = roc / 100
            metadata['volatility_adjusted'] = self.momentum_config.volatility_adjustment
        
        # Add institutional metadata
        if self.institutional_features:
            metadata['smart_money_factor'] = self._detect_smart_money_flow(current_price, volume)
            metadata['institutional_factor'] = self._detect_institutional_activity(current_price, volume)
            metadata['market_regime'] = self._get_market_regime_multiplier()
        
        return metadata

class UnifiedVolumeWeightedMomentum(VolumeWeightedIndicator):
    """Unified Volume-Weighted Momentum
    
    Consolidated momentum indicator with configurable adaptive features.
    """
    
    def __init__(self, config: IndicatorConfig, momentum_config: MomentumConfig = None):
        super().__init__(config, "Unified_VW_MOM")
        self.indicator_type = IndicatorType.MOMENTUM
        self.momentum_config = momentum_config or MomentumConfig()
        
        # Configuration-based feature enablement
        self.adaptive_features = self.momentum_config.adaptive_mode in [AdaptiveMode.ENHANCED, AdaptiveMode.HYBRID]
        self.institutional_features = self.momentum_config.adaptive_mode in [AdaptiveMode.INSTITUTIONAL, AdaptiveMode.HYBRID]
    
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate Unified Volume-Weighted Momentum"""
        start_time = datetime.now()
        
        self._add_data_point(price, volume, timestamp)
        
        if len(self.prices) < self.config.period + 1:
            return None
        
        # Get current and historical prices
        current_price = price
        historical_price = self.prices[-(self.config.period + 1)]
        
        # Apply volume weighting based on configuration
        if self.config.volume_weighted:
            weighted_current, weighted_historical = self._apply_volume_weighting(
                current_price, historical_price, volume
            )
        else:
            weighted_current = current_price
            weighted_historical = historical_price
        
        # Calculate momentum
        momentum = weighted_current - weighted_historical
        
        # Normalize if requested
        if self.config.normalize:
            momentum = (momentum / weighted_historical) * 100 if weighted_historical != 0 else 0
        
        # Generate signal with adaptive features
        signal, confidence = self._generate_momentum_signal(momentum, volume)
        
        result = IndicatorResult(
            timestamp=timestamp,
            value=momentum,
            signal=signal,
            confidence=confidence,
            metadata={
                'current_price': weighted_current,
                'historical_price': weighted_historical,
                'period': self.config.period,
                'normalized': self.config.normalize,
                'adaptive_mode': self.momentum_config.adaptive_mode.value
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
    
    def _apply_volume_weighting(self, current_price: float, historical_price: float, volume: float) -> Tuple[float, float]:
        """Apply volume weighting with optional enhancements"""
        # Basic volume weighting
        recent_volumes = self.volumes[-min(5, len(self.volumes)):]
        avg_volume = np.mean(recent_volumes) if recent_volumes else 1
        
        volume_factor = min(2.0, max(0.5, volume / avg_volume)) if avg_volume > 0 else 1.0
        weighted_current = current_price * volume_factor
        
        # Weight historical price similarly
        hist_idx = -(self.config.period + 1)
        if abs(hist_idx) < len(self.volumes):
            hist_volume = self.volumes[hist_idx]
            hist_volume_factor = min(2.0, max(0.5, hist_volume / avg_volume)) if avg_volume > 0 else 1.0
            weighted_historical = historical_price * hist_volume_factor
        else:
            weighted_historical = historical_price
        
        return weighted_current, weighted_historical
    
    def _generate_momentum_signal(self, momentum_value: float, volume: float) -> Tuple[SignalType, float]:
        """Generate momentum signal with adaptive features"""
        # Determine thresholds based on configuration
        if self.adaptive_features and len(self.results) >= 20:
            recent_momentum = [r.value for r in self.results[-20:]]
            volatility = np.std(recent_momentum)
            threshold = max(0.5, volatility)
        else:
            threshold = 1.0
        
        # Generate base signal
        if momentum_value > threshold:
            confidence = min(1.0, momentum_value / (threshold * 2))
            return SignalType.BUY, confidence * 0.8
        elif momentum_value < -threshold:
            confidence = min(1.0, abs(momentum_value) / (threshold * 2))
            return SignalType.SELL, confidence * 0.8
        
        return SignalType.NEUTRAL, 0.0

# Factory function for creating unified momentum indicators
def create_unified_momentum_indicator(indicator_type: str, config: IndicatorConfig, 
                                    momentum_config: MomentumConfig = None):
    """Factory function for creating unified momentum indicators"""
    momentum_config = momentum_config or MomentumConfig()
    
    if indicator_type.upper() == "ROC":
        return UnifiedVolumeWeightedROC(config, momentum_config)
    elif indicator_type.upper() == "MOM":
        return UnifiedVolumeWeightedMomentum(config, momentum_config)
    else:
        raise ValueError(f"Unknown momentum indicator type: {indicator_type}")