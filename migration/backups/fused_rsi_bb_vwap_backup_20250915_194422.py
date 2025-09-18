"""Fused RSI, Bollinger Bands, and VWAP Indicator

This module implements an ensemble indicator that fuses signals from RSI, Bollinger Bands, and VWAP for consensus-based trading signals.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
from typing import Optional, Dict
from datetime import datetime

from .core_indicator_base import AugmentedIndicator, IndicatorConfig, IndicatorResult, SignalType
from .momentum_indicators import RSI
from .volatility_indicators import BollingerBands
from .volume_indicators import VWAP
import shap\nfrom sklearn.linear_model import LinearRegression

class FusedRSIBBVWAP(AugmentedIndicator):
    """Fused Indicator combining RSI, Bollinger Bands, and VWAP
    
    This indicator creates a consensus signal by fusing:
    - RSI for momentum
    - Bollinger Bands for volatility
    - VWAP for volume-weighted price levels
    
    The fused signal is a weighted average of normalized components.
    """
    
    def __init__(self, config: IndicatorConfig = None):
        config = config or IndicatorConfig(period=14)
        super().__init__(config)
        
        # Initialize component indicators with shared config
        self.rsi = RSI(period=config.period)
        self.bb = BollingerBands(config=config)
        self.vwap = VWAP(config=config)
        
        # Weights for fusion (can be adjusted)
        self.weights = {
            'rsi': 0.4,
            'bb': 0.3,
            'vwap': 0.3
        }
        
        # Normalization ranges
        self.normalized_signals: Dict[str, float] = {}
    
    def explain(self, normalized_signals: Dict[str, float]) -> Dict[str, float]:\n        \"\"\"Generate SHAP explanations for the fused signal\"\"\"\n        feature_names = list(self.weights.keys())\n        coefs = np.array([self.weights[name] for name in feature_names])\n\n        # Create dummy linear model\n        model = LinearRegression()\n        model.coef_ = coefs\n        model.intercept_ = 0.0\n\n        # Background data (zeros for simplicity)\n        background = np.zeros((1, len(feature_names)))\n\n        # Create explainer\n        explainer = shap.LinearExplainer(model, background)\n\n        # Input data\n        X = np.array([[normalized_signals[name] for name in feature_names]])\n\n        # Compute SHAP values\n        shap_values = explainer(X)\n\n        # Return as dict\n        return {name: float(shap_values.values[0, i]) for i, name in enumerate(feature_names)}\n
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> Optional[IndicatorResult]:\n        """Update the fused indicator and compute consensus signal"""
        timestamp = timestamp or datetime.now()
        
        # Update component indicators
        rsi_result = self.rsi.update(price, volume, timestamp)
        bb_result = self.bb.update(price, volume, timestamp)
        vwap_result = self.vwap.update(price, volume, timestamp)
        
        if not all([rsi_result, bb_result, vwap_result]):
            return None
        
        # Normalize signals to [-1, 1]
        self._normalize_signals(rsi_result, bb_result, vwap_result)
        
        # Compute fused signal
        fused_value = self._compute_fused_value()
        
        # Generate consensus signal
        signal = self._generate_consensus_signal(fused_value)
        
        # Generate SHAP explanations
        shap_explanations = self.explain(self.normalized_signals)\n
        # Create result with metadata from components
        metadata = {\n            'rsi_value': rsi_result.value,\n            'bb_position': bb_result.metadata.get('band_position', 0.5),\n            'vwap_value': vwap_result.value,\n            'normalized': self.normalized_signals,\n            'fused_value': fused_value,\n            'shap_explanations': shap_explanations\n        }\n        
        return IndicatorResult(
            timestamp=timestamp,
            value=fused_value,
            signal=signal,
            metadata=metadata
        )
    
    def _normalize_signals(self, rsi_result, bb_result, vwap_result):
        """Normalize component signals to [-1, 1] range"""
        # RSI: (rsi - 50) / 50
        rsi_norm = (rsi_result.value - 50) / 50
        
        # BB: band position - 0.5 * 2 (from 0-1 to -1 to 1)
        bb_position = bb_result.metadata.get('band_position', 0.5)
        bb_norm = (bb_position - 0.5) * 2
        
        # VWAP: normalized deviation from VWAP
        price = rsi_result.metadata.get('last_price', 0)  # Assuming price is stored
        vwap_dev = (price - vwap_result.value) / vwap_result.value if vwap_result.value != 0 else 0
        vwap_norm = np.clip(vwap_dev / 0.01, -1, 1)  # Assume 1% deviation as max
        
        self.normalized_signals = {
            'rsi': rsi_norm,
            'bb': bb_norm,
            'vwap': vwap_norm
        }
    
    def _compute_fused_value(self) -> float:
        """Compute weighted average of normalized signals"""
        return sum(self.normalized_signals[k] * w for k, w in self.weights.items())
    
    def _generate_consensus_signal(self, fused_value: float) -> SignalType:
        """Generate signal based on fused value"""
        if fused_value > 0.7:
            return SignalType.STRONG_BUY
        elif fused_value > 0.3:
            return SignalType.BUY
        elif fused_value < -0.7:
            return SignalType.STRONG_SELL
        elif fused_value < -0.3:
            return SignalType.SELL
        else:
            return SignalType.NEUTRAL
    
    def reset(self) -> None:
        """Reset all component indicators"""
        super().reset()
        self.rsi.reset()
        self.bb.reset()
        self.vwap.reset()
        self.normalized_signals = {}