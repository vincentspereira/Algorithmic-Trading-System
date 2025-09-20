"""
Augmented Exponential Moving Average (EMA) Indicator

An institutional-grade implementation of the Exponential Moving Average (EMA) that
integrates the 5-pillar augmentation architecture.

Pillars Integrated:
1.  **Volume Integration**: EMA calculation can be volume-weighted.
2.  **Market Regime Adaptation**: Signal generation is sensitive to the current market regime.
3.  **Multi-Timeframe Convergence**: Confidence is boosted when EMAs across different timeframes align.
4.  **Smart Money Proxies**: Confidence is adjusted based on approximations of smart money activity.
5.  **Risk Management Factory**: The indicator output includes suggested stop-loss and take-profit levels.
"""

import numpy as np
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.instruments import Instrument

from nautilus_trader_engine.indicators.core.augmented_indicator import AugmentedIndicator, SignalType, MarketRegime, IndicatorOutput


class AugmentedEMA(AugmentedIndicator):
    """
    An augmented Exponential Moving Average (EMA) indicator.
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
        Initializes the AugmentedEMA indicator.

        Args:
            period (int): The period for the EMA calculation.
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
        self.alpha = 2.0 / (self.period + 1)
        self.ema = None

    def calculate_raw_value(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """
        Calculates the raw EMA value.

        Args:
            prices (np.ndarray): An array of prices.
            volumes (np.ndarray): An array of volumes.

        Returns:
            float: The raw EMA value.
        """
        if self.volume_weight > 0:
            # Volume-weighted EMA calculation
            vw_prices = prices * volumes
            if self.ema is None:
                self.ema = np.sum(vw_prices) / np.sum(volumes)
            else:
                self.ema = self.alpha * (np.sum(vw_prices) / np.sum(volumes)) + (1 - self.alpha) * self.ema
        else:
            # Standard EMA calculation
            if self.ema is None:
                self.ema = np.mean(prices)
            else:
                self.ema = self.alpha * prices[-1] + (1 - self.alpha) * self.ema
        
        return self.ema

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