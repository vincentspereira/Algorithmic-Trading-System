"""
Augmented Weighted Moving Average (WMA) Indicator

An institutional-grade implementation of the Weighted Moving Average (WMA) that
integrates the 5-pillar augmentation architecture.

Pillars Integrated:
1.  **Volume Integration**: WMA calculation can be volume-weighted.
2.  **Market Regime Adaptation**: Signal generation is sensitive to the current market regime.
3.  **Multi-Timeframe Convergence**: Confidence is boosted when WMAs across different timeframes align.
4.  **Smart Money Proxies**: Confidence is adjusted based on approximations of smart money activity.
5.  **Risk Management Factory**: The indicator output includes suggested stop-loss and take-profit levels.
"""

import numpy as np
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.instruments import Instrument

from nautilus_trader_engine.indicators.core.augmented_indicator import AugmentedIndicator, SignalType, MarketRegime, IndicatorOutput


class AugmentedWMA(AugmentedIndicator):
    """
    An augmented Weighted Moving Average (WMA) indicator.
    """

    def __init__(
        self,
        period: int = 20,
        price_type: PriceType = PriceType.CLOSE,
        instrument: Instrument = None,
        volume_weight: float = 0.5,
        regime_sensitivity: float = 0.5,
        timeframes: list[str] = None,
        risk_multiplier: float = 1.5,
    ):
        """
        Initializes the AugmentedWMA indicator.

        Args:
            period (int): The period for the WMA calculation.
            price_type (PriceType): The price type to use for the calculation.
            instrument (Instrument): The instrument being traded.
            volume_weight (float): The weight to give to volume in the calculation.
            regime_sensitivity (float): The sensitivity to market regime changes.
            timeframes (list[str]): The timeframes to use for convergence analysis.
            risk_multiplier (float): The multiplier for risk management calculations.
        """
        super().__init__(
            period=period,
            volume_weight=volume_weight,
            regime_sensitivity=regime_sensitivity,
            timeframes=timeframes,
            risk_multiplier=risk_multiplier,
        )
        self.price_type = price_type
        self.instrument = instrument

    def calculate_raw_value(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """
        Calculates the raw WMA value.

        Args:
            prices (np.ndarray): An array of prices.
            volumes (np.ndarray): An array of volumes.

        Returns:
            float: The raw WMA value.
        """
        weights = np.arange(1, self.period + 1)
        
        if self.volume_weight > 0:
            # Volume-weighted WMA calculation
            vw_prices = prices * volumes
            return np.sum(vw_prices * weights) / np.sum(volumes * weights)
        else:
            # Standard WMA calculation
            return np.sum(prices * weights) / np.sum(weights)

    def _generate_signal(self, raw_value: float, confidence: "ConfidenceComponents", regime: MarketRegime) -> SignalType:
        """
        Generates a trading signal based on the augmented analysis.

        Args:
            raw_value (float): The raw indicator value.
            confidence (ConfidenceComponents): The confidence components.
            regime (MarketRegime): The current market regime.

        Returns:
            SignalType: The generated trading signal.
        """
        composite_confidence = confidence.composite_score()
        price = self._price_history[-1]

        is_bullish = price > raw_value
        is_bearish = price < raw_value

        if regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
            if is_bullish and regime == MarketRegime.TRENDING_UP:
                if composite_confidence > 0.7:
                    return SignalType.STRONG_BUY
                elif composite_confidence > 0.5:
                    return SignalType.BUY
            elif is_bearish and regime == MarketRegime.TRENDING_DOWN:
                if composite_confidence > 0.7:
                    return SignalType.STRONG_SELL
                elif composite_confidence > 0.5:
                    return SignalType.SELL

        elif regime == MarketRegime.SIDEWAYS:
            # Look for mean reversion signals
            if is_bullish and composite_confidence > 0.6:
                return SignalType.BUY
            elif is_bearish and composite_confidence > 0.6:
                return SignalType.SELL

        return SignalType.HOLD