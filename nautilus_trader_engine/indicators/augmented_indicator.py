#!/usr/bin/env python3
"""
AugmentedIndicator Base Class

Institutional-grade base class for all technical indicators following the 5-pillar
augmentation architecture as specified in the institutional standards:

1. Volume Integration
2. Market Regime Adaptation
3. Multi-Timeframe Convergence
4. Smart Money Proxies
5. Risk Management Factory

Author: AI Assistant
Date: 2024-12-15
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
from datetime import datetime

class SignalType(Enum):
    """Signal types for indicator outputs"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    NEUTRAL = "NEUTRAL"

class MarketRegime(Enum):
    """Market regime classifications"""
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    BREAKOUT = "BREAKOUT"
    REVERSAL = "REVERSAL"

@dataclass
class ConfidenceComponents:
    """Breakdown of confidence scoring components"""
    volume_confirmation: float
    regime_alignment: float
    timeframe_convergence: float
    smart_money_flow: float
    risk_reward_ratio: float
    
    def composite_score(self) -> float:
        """Calculate composite confidence score"""
        weights = [0.25, 0.20, 0.20, 0.20, 0.15]
        components = [self.volume_confirmation, self.regime_alignment, 
                     self.timeframe_convergence, self.smart_money_flow, 
                     self.risk_reward_ratio]
        return sum(w * c for w, c in zip(weights, components))

@dataclass
class IndicatorOutput:
    """Standardized output structure for all augmented indicators"""
    value_raw: float
    signal_type: SignalType
    composite_confidence: float
    confidence_components: ConfidenceComponents
    suggested_sl: Optional[float]
    suggested_tp: Optional[float]
    market_regime: MarketRegime
    timestamp: datetime
    metadata: Dict[str, Any]

class AugmentedIndicator(ABC):
    """Base class for all institutional-grade technical indicators"""
    
    def __init__(self, 
                 period: int = 14,
                 volume_weight: float = 0.3,
                 regime_sensitivity: float = 0.5,
                 timeframes: List[str] = None,
                 risk_multiplier: float = 2.0):
        """
        Initialize augmented indicator
        
        Args:
            period: Base calculation period
            volume_weight: Weight for volume integration (0.0 to 1.0)
            regime_sensitivity: Sensitivity to market regime changes
            timeframes: List of timeframes for convergence analysis
            risk_multiplier: Risk-reward ratio multiplier
        """
        self.period = period
        self.volume_weight = volume_weight
        self.regime_sensitivity = regime_sensitivity
        self.timeframes = timeframes or ['1m', '5m', '15m', '1h']
        self.risk_multiplier = risk_multiplier
        
        # Internal state
        self._price_history: List[float] = []
        self._volume_history: List[float] = []
        self._timestamp_history: List[datetime] = []
        self._regime_history: List[MarketRegime] = []
        
        # Caching for performance
        self._cache: Dict[str, Any] = {}
        self._last_calculation_time: Optional[datetime] = None
    
    @abstractmethod
    def calculate_raw_value(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate the raw indicator value without augmentation"""
        pass
    
    def update(self, price: float, volume: float, timestamp: datetime) -> IndicatorOutput:
        """Update indicator with new data point and return augmented output"""
        # Update history
        self._price_history.append(price)
        self._volume_history.append(volume)
        self._timestamp_history.append(timestamp)
        
        # Maintain rolling window
        if len(self._price_history) > self.period * 3:  # Keep extra for calculations
            self._price_history = self._price_history[-self.period * 3:]
            self._volume_history = self._volume_history[-self.period * 3:]
            self._timestamp_history = self._timestamp_history[-self.period * 3:]
        
        # Calculate if we have enough data
        if len(self._price_history) < self.period:
            return self._create_insufficient_data_output(price, timestamp)
        
        # Apply 5-pillar augmentation
        return self._calculate_augmented_output(timestamp)
    
    def _calculate_augmented_output(self, timestamp: datetime) -> IndicatorOutput:
        """Calculate augmented indicator output using 5-pillar architecture"""
        prices = np.array(self._price_history)
        volumes = np.array(self._volume_history)
        
        # 1. Calculate raw value
        raw_value = self.calculate_raw_value(prices, volumes)
        
        # 2. Volume Integration
        volume_confirmation = self._calculate_volume_confirmation(prices, volumes)
        
        # 3. Market Regime Adaptation
        current_regime = self._detect_market_regime(prices, volumes)
        regime_alignment = self._calculate_regime_alignment(raw_value, current_regime)
        
        # 4. Multi-Timeframe Convergence
        timeframe_convergence = self._calculate_timeframe_convergence(prices)
        
        # 5. Smart Money Proxies
        smart_money_flow = self._calculate_smart_money_flow(prices, volumes)
        
        # Risk Management Factory
        risk_reward = self._calculate_risk_reward_ratio(prices[-1], raw_value)
        suggested_sl, suggested_tp = self._calculate_risk_levels(prices[-1], raw_value)
        
        # Create confidence components
        confidence_components = ConfidenceComponents(
            volume_confirmation=volume_confirmation,
            regime_alignment=regime_alignment,
            timeframe_convergence=timeframe_convergence,
            smart_money_flow=smart_money_flow,
            risk_reward_ratio=risk_reward
        )
        
        # Generate signal
        signal_type = self._generate_signal(raw_value, confidence_components, current_regime)
        
        return IndicatorOutput(
            value_raw=raw_value,
            signal_type=signal_type,
            composite_confidence=confidence_components.composite_score(),
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            market_regime=current_regime,
            timestamp=timestamp,
            metadata=self._generate_metadata()
        )
    
    def _calculate_volume_confirmation(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate volume confirmation score (Pillar 1)"""
        if len(volumes) < 2:
            return 0.5
        
        # Volume-weighted price momentum
        vwap = np.sum(prices * volumes) / np.sum(volumes)
        current_price = prices[-1]
        
        # Volume trend analysis
        recent_volume = np.mean(volumes[-5:])
        avg_volume = np.mean(volumes)
        volume_ratio = min(recent_volume / avg_volume, 2.0) if avg_volume > 0 else 1.0
        
        # Price-volume divergence
        price_change = (current_price - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        volume_change = (recent_volume - np.mean(volumes[-10:-5])) / np.mean(volumes[-10:-5]) if len(volumes) >= 10 else 0
        
        # Combine factors
        vwap_alignment = 1.0 if (current_price > vwap and price_change > 0) or (current_price < vwap and price_change < 0) else 0.3
        volume_support = min(volume_ratio / 2.0, 1.0)
        divergence_penalty = max(0.0, 1.0 - abs(price_change - volume_change))
        
        return np.clip((vwap_alignment * 0.4 + volume_support * 0.4 + divergence_penalty * 0.2), 0.0, 1.0)
    
    def _detect_market_regime(self, prices: np.ndarray, volumes: np.ndarray) -> MarketRegime:
        """Detect current market regime (Pillar 2)"""
        if len(prices) < 20:
            return MarketRegime.SIDEWAYS
        
        # Trend analysis
        short_ma = np.mean(prices[-5:])
        long_ma = np.mean(prices[-20:])
        
        # Volatility analysis
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else 0
        avg_volatility = np.std(returns) if len(returns) > 0 else 0
        
        # Volume analysis
        avg_volume = np.mean(volumes)
        recent_volume = np.mean(volumes[-5:])
        
        # Regime classification
        trend_strength = abs(short_ma - long_ma) / long_ma if long_ma > 0 else 0
        vol_ratio = volatility / avg_volatility if avg_volatility > 0 else 1
        
        if vol_ratio > 1.5:
            return MarketRegime.HIGH_VOLATILITY
        elif vol_ratio < 0.5:
            return MarketRegime.LOW_VOLATILITY
        elif trend_strength > 0.02:
            if short_ma > long_ma:
                return MarketRegime.TRENDING_UP
            else:
                return MarketRegime.TRENDING_DOWN
        else:
            return MarketRegime.SIDEWAYS
    
    def _calculate_regime_alignment(self, raw_value: float, regime: MarketRegime) -> float:
        """Calculate regime alignment score (Pillar 2)"""
        # This is a simplified implementation - should be customized per indicator
        if regime in [MarketRegime.HIGH_VOLATILITY, MarketRegime.LOW_VOLATILITY]:
            return 0.5  # Neutral in volatile conditions
        elif regime == MarketRegime.SIDEWAYS:
            return 0.7  # Most indicators work well in sideways markets
        else:
            return 0.9  # Strong alignment in trending markets
    
    def _calculate_timeframe_convergence(self, prices: np.ndarray) -> float:
        """Calculate multi-timeframe convergence (Pillar 3)"""
        # Simplified implementation - in practice, would analyze multiple timeframes
        if len(prices) < 50:
            return 0.5
        
        # Analyze different period lengths as proxy for timeframes
        short_trend = np.mean(prices[-5:]) - np.mean(prices[-10:-5])
        medium_trend = np.mean(prices[-15:]) - np.mean(prices[-30:-15])
        long_trend = np.mean(prices[-25:]) - np.mean(prices[-50:-25])
        
        # Check alignment
        trends = [short_trend, medium_trend, long_trend]
        positive_trends = sum(1 for t in trends if t > 0)
        negative_trends = sum(1 for t in trends if t < 0)
        
        if positive_trends == 3 or negative_trends == 3:
            return 1.0  # Perfect alignment
        elif positive_trends == 2 or negative_trends == 2:
            return 0.7  # Good alignment
        else:
            return 0.3  # Poor alignment
    
    def _calculate_smart_money_flow(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """Calculate smart money flow indicators (Pillar 4)"""
        if len(prices) < 10:
            return 0.5
        
        # Money Flow Index approximation
        typical_prices = prices  # Simplified - would use (H+L+C)/3
        money_flow = typical_prices * volumes
        
        positive_flow = 0
        negative_flow = 0
        
        for i in range(1, len(money_flow)):
            if typical_prices[i] > typical_prices[i-1]:
                positive_flow += money_flow[i]
            else:
                negative_flow += money_flow[i]
        
        if positive_flow + negative_flow == 0:
            return 0.5
        
        money_ratio = positive_flow / (positive_flow + negative_flow)
        
        # Large block analysis (simplified)
        large_volume_threshold = np.percentile(volumes, 80)
        large_volume_indices = volumes > large_volume_threshold
        
        if np.any(large_volume_indices):
            large_volume_price_change = np.mean(np.diff(prices[large_volume_indices]))
            if abs(large_volume_price_change) > np.std(np.diff(prices)):
                smart_money_factor = 1.2
            else:
                smart_money_factor = 0.8
        else:
            smart_money_factor = 1.0
        
        return np.clip(money_ratio * smart_money_factor, 0.0, 1.0)
    
    def _calculate_risk_reward_ratio(self, current_price: float, signal_value: float) -> float:
        """Calculate risk-reward ratio (Pillar 5)"""
        if len(self._price_history) < 20:
            return 0.5
        
        # Calculate ATR for risk assessment
        prices = np.array(self._price_history[-20:])
        atr = np.mean(np.abs(np.diff(prices))) * 14  # Simplified ATR
        
        # Estimate potential reward vs risk
        potential_reward = abs(signal_value - current_price)
        potential_risk = atr
        
        if potential_risk == 0:
            return 0.5
        
        risk_reward = potential_reward / potential_risk
        return np.clip(risk_reward / 3.0, 0.0, 1.0)  # Normalize to 0-1
    
    def _calculate_risk_levels(self, current_price: float, signal_value: float) -> Tuple[Optional[float], Optional[float]]:
        """Calculate suggested stop-loss and take-profit levels"""
        if len(self._price_history) < 20:
            return None, None
        
        # Calculate ATR for risk sizing
        prices = np.array(self._price_history[-20:])
        atr = np.mean(np.abs(np.diff(prices))) * 14
        
        # Determine direction
        is_bullish = signal_value > current_price
        
        if is_bullish:
            suggested_sl = current_price - (atr * self.risk_multiplier)
            suggested_tp = current_price + (atr * self.risk_multiplier * 2)
        else:
            suggested_sl = current_price + (atr * self.risk_multiplier)
            suggested_tp = current_price - (atr * self.risk_multiplier * 2)
        
        return suggested_sl, suggested_tp
    
    def _generate_signal(self, raw_value: float, confidence: ConfidenceComponents, regime: MarketRegime) -> SignalType:
        """Generate trading signal based on augmented analysis"""
        composite_confidence = confidence.composite_score()
        
        # This is a base implementation - should be overridden by specific indicators
        if composite_confidence > 0.8:
            if raw_value > 0:  # Assuming positive raw_value indicates bullish
                return SignalType.STRONG_BUY
            else:
                return SignalType.STRONG_SELL
        elif composite_confidence > 0.6:
            if raw_value > 0:
                return SignalType.BUY
            else:
                return SignalType.SELL
        else:
            return SignalType.HOLD
    
    def _generate_metadata(self) -> Dict[str, Any]:
        """Generate metadata for the indicator output"""
        return {
            'indicator_name': self.__class__.__name__,
            'period': self.period,
            'volume_weight': self.volume_weight,
            'regime_sensitivity': self.regime_sensitivity,
            'data_points': len(self._price_history),
            'calculation_time': datetime.now().isoformat()
        }
    
    def _create_insufficient_data_output(self, price: float, timestamp: datetime) -> IndicatorOutput:
        """Create output when insufficient data is available"""
        return IndicatorOutput(
            value_raw=price,
            signal_type=SignalType.NEUTRAL,
            composite_confidence=0.0,
            confidence_components=ConfidenceComponents(0.0, 0.0, 0.0, 0.0, 0.0),
            suggested_sl=None,
            suggested_tp=None,
            market_regime=MarketRegime.SIDEWAYS,
            timestamp=timestamp,
            metadata={'status': 'insufficient_data', 'required_points': self.period}
        )
    
    def reset(self):
        """Reset indicator state"""
        self._price_history.clear()
        self._volume_history.clear()
        self._timestamp_history.clear()
        self._regime_history.clear()
        self._cache.clear()
        self._last_calculation_time = None
    
    def get_state(self) -> Dict[str, Any]:
        """Get current indicator state for serialization"""
        return {
            'price_history': self._price_history,
            'volume_history': self._volume_history,
            'timestamp_history': [t.isoformat() for t in self._timestamp_history],
            'parameters': {
                'period': self.period,
                'volume_weight': self.volume_weight,
                'regime_sensitivity': self.regime_sensitivity,
                'timeframes': self.timeframes,
                'risk_multiplier': self.risk_multiplier
            }
        }
    
    def load_state(self, state: Dict[str, Any]):
        """Load indicator state from serialized data"""
        self._price_history = state.get('price_history', [])
        self._volume_history = state.get('volume_history', [])
        self._timestamp_history = [datetime.fromisoformat(t) for t in state.get('timestamp_history', [])]
        
        params = state.get('parameters', {})
        self.period = params.get('period', self.period)
        self.volume_weight = params.get('volume_weight', self.volume_weight)
        self.regime_sensitivity = params.get('regime_sensitivity', self.regime_sensitivity)
        self.timeframes = params.get('timeframes', self.timeframes)
        self.risk_multiplier = params.get('risk_multiplier', self.risk_multiplier)