"""Behavioral Overlays for Sentiment and Psychological Factors

This module implements behavioral overlays that incorporate sentiment analysis and psychological factors
into trading indicators, enhancing decision-making with behavioral finance insights.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
from collections import deque
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from .core_indicator_base import AugmentedIndicator, IndicatorSignal, SignalType, MarketRegime


class BehavioralOverlay(AugmentedIndicator):
    """Behavioral Overlay Indicator
    
    Incorporates sentiment analysis and psychological factors as an overlay to existing indicators.
    Uses sentiment scores, fear/greed metrics, and behavioral bias detection to adjust trading signals.
    """
    
    def __init__(
        self,
        sentiment_period: int = 14,
        fear_greed_threshold: float = 0.5,
        behavioral_weight: float = 0.3,
        enable_sentiment_adjustment: bool = True,
        enable_psychological_bias: bool = True,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        # Parameters
        self.sentiment_period = sentiment_period
        self.fear_greed_threshold = fear_greed_threshold
        self.behavioral_weight = behavioral_weight
        self.enable_sentiment_adjustment = enable_sentiment_adjustment
        self.enable_psychological_bias = enable_psychological_bias
        
        # Data storage
        self.sentiment_history = deque(maxlen=sentiment_period)
        self.psychological_scores = deque(maxlen=sentiment_period)
        
        # Metrics
        self.fear_greed_index = 0.0
        self.sentiment_score = 0.0
        self.psychological_bias = 0.0
        self.adjusted_signal = 0.0
        
        # Metadata
        self.metadata: Dict[str, Any] = {}
    
    def update(self, price: float, volume: float = 0.0, timestamp: Optional[datetime] = None, sentiment_input: float = 0.0):
        """Update the behavioral overlay with new data"""
        
        super().update(price, volume, timestamp)
        
        # Update sentiment history
        self.sentiment_history.append(sentiment_input)
        
        # Calculate sentiment score
        if len(self.sentiment_history) > 0:
            self.sentiment_score = np.mean(self.sentiment_history)
        
        # Calculate fear/greed index
        self.fear_greed_index = self._calculate_fear_greed()
        
        # Calculate psychological bias
        self.psychological_bias = self._calculate_psychological_bias()
        
        # Adjust base signal
        self.adjusted_signal = self._adjust_signal()
        
        # Update metadata
        self._update_metadata()
    
    def _calculate_fear_greed(self) -> float:
        """Calculate fear/greed index based on sentiment"""
        
        if abs(self.sentiment_score) < 0.1:
            return 0.0
        
        # Normalize to -1 (extreme fear) to +1 (extreme greed)
        fg_index = np.tanh(self.sentiment_score * 2)  # Tanh for smooth bounding
        
        return fg_index
    
    def _calculate_psychological_bias(self) -> float:
        """Calculate psychological bias score"""
        
        # Simple momentum-based bias (herding behavior)
        if len(self.prices) < 5:
            return 0.0
        
        recent_returns = np.diff(list(self.prices)[-5:]) / np.array(list(self.prices)[-5:-1])
        bias_score = np.mean(np.sign(recent_returns))  # -1 to 1
        
        # Adjust with volume for conviction
        if self.volume:
            volume_factor = np.mean(list(self.volumes)[-5:]) / (np.mean(list(self.volumes)) + 1e-6)
            bias_score *= min(1.5, volume_factor)
        
        return np.clip(bias_score, -1.0, 1.0)
    
    def _adjust_signal(self) -> float:
        """Adjust base indicator signal with behavioral factors"""
        
        base_signal = self.value  # Assuming value is the base indicator signal
        
        if not self.enable_sentiment_adjustment and not self.enable_psychological_bias:
            return base_signal
        
        adjustment = 0.0
        
        # Sentiment adjustment
        if self.enable_sentiment_adjustment:
            sentiment_adj = self.sentiment_score * self.behavioral_weight
            if abs(self.fear_greed_index) > self.fear_greed_threshold:
                sentiment_adj *= 1.5  # Amplify in extreme conditions
            adjustment += sentiment_adj
        
        # Psychological bias adjustment
        if self.enable_psychological_bias:
            bias_adj = self.psychological_bias * self.behavioral_weight
            # Contrarian adjustment: reduce signal strength in strong bias
            if abs(self.psychological_bias) > 0.7:
                bias_adj *= -0.5  # Partial reversal
            adjustment += bias_adj
        
        # Apply adjustment
        adjusted = base_signal + adjustment
        adjusted = np.clip(adjusted, -1.0, 1.0)  # Bound signal
        
        return adjusted
    
    def _update_metadata(self):
        """Update behavioral metadata"""
        
        self.metadata.update({
            'sentiment_score': self.sentiment_score,
            'fear_greed_index': self.fear_greed_index,
            'psychological_bias': self.psychological_bias,
            'behavioral_adjustment': self.adjusted_signal - self.value,
            'extreme_condition': abs(self.fear_greed_index) > self.fear_greed_threshold
        })
    
    def get_signal(self) -> IndicatorSignal:
        """Get behavioral-adjusted signal"""
        
        # Determine signal type based on adjusted signal value
        magnitude = abs(self.adjusted_signal)
        if self.adjusted_signal > 0:
            signal_type = SignalType.STRONG_BUY if magnitude > 0.7 else SignalType.BUY
        elif self.adjusted_signal < 0:
            signal_type = SignalType.STRONG_SELL if magnitude > 0.7 else SignalType.SELL
        else:
            signal_type = SignalType.NEUTRAL
        
        # Strength is normalized magnitude in [0, 1]
        strength = float(np.clip(magnitude, 0.0, 1.0))
        
        return IndicatorSignal(
            signal_type=signal_type,
            strength=strength,
            confidence=strength,
            timestamp=datetime.now(timezone.utc),
            value=self.adjusted_signal,
            normalized_value=self.adjusted_signal,
            metadata=self.metadata.copy()
        )
    
    def reset(self):
        """Reset the indicator state"""
        
        super().reset()
        self.sentiment_history.clear()
        self.psychological_scores.clear()
        self.fear_greed_index = 0.0
        self.sentiment_score = 0.0
        self.psychological_bias = 0.0
        self.adjusted_signal = 0.0
        self.metadata = {}