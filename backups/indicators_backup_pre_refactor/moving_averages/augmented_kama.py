"""
Augmented Kaufman's Adaptive Moving Average (KAMA) Indicator

An institutional-grade implementation of Kaufman's Adaptive Moving Average (KAMA)
that integrates the 5-pillar augmentation architecture.

Pillars Integrated:
1.  **Volume Integration**: KAMA calculation can be volume-weighted.
2.  **Market Regime Adaptation**: Signal generation is sensitive to the current market regime.
3.  **Multi-Timeframe Convergence**: Confidence is boosted when KAMAs across different timeframes align.
4.  **Smart Money Proxies**: Confidence is adjusted based on approximations of smart money activity.
5.  **Risk Management Factory**: The indicator output includes suggested stop-loss and take-profit levels.
"""

import numpy as np
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.instruments import Instrument

from nautilus_trader_engine.indicators.core.augmented_indicator import AugmentedIndicator, SignalType, MarketRegime, IndicatorOutput


class AugmentedKAMA(AugmentedIndicator):
    """
    An augmented Kaufman's Adaptive Moving Average (KAMA) indicator.
    """

    def __init__(
        self,
        period: int = 10,
        fast_ema: int = 2,
        slow_ema: int = 30,
        price_type: PriceType = PriceType.CLOSE,
        instrument: Instrument = None,
        volume_weight: float = 0.5,
        regime_sensitivity: float = 0.5,
        timeframes: list[str] = None,
        risk_multiplier: float = 1.5,
    ):
        """
        Initializes the AugmentedKAMA indicator.

        Args:
            period (int): The period for the KAMA calculation.
            fast_ema (int): The fast EMA period.
            slow_ema (int): The slow EMA period.
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
        self.fast_ema = fast_ema
        self.slow_ema = slow_ema
        self.price_type = price_type
        self.instrument = instrument
        self.kama = None

        self.fast_alpha = 2.0 / (self.fast_ema + 1)
        self.slow_alpha = 2.0 / (self.slow_ema + 1)

    def update(self, price: float, volume: float, timestamp: "datetime") -> "IndicatorOutput":
        """Update indicator with new data point and return augmented output"""
        # Update history
        self._price_history.append(price)
        self._volume_history.append(volume)
        self._timestamp_history.append(timestamp)
        
        # Maintain rolling window
        if len(self._price_history) > self.period + 1:
            self._price_history.pop(0)
            self._volume_history.pop(0)
            self._timestamp_history.pop(0)
        
        # Calculate if we have enough data
        if len(self._price_history) < self.period + 1:
            return self._create_insufficient_data_output(price, timestamp)
        
        # Apply 5-pillar augmentation
        return self._calculate_augmented_output(timestamp)

    def calculate_raw_value(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """
        Calculates the raw KAMA value.

        Args:
            prices (np.ndarray): An array of prices.
            volumes (np.ndarray): An array of volumes.

        Returns:
            float: The raw KAMA value.
        """
        change = abs(prices[-1] - prices[0])
        volatility = np.sum(np.abs(np.diff(prices)))

        if volatility == 0:
            er = 1.0
        else:
            er = change / volatility

        sc = (er * (self.fast_alpha - self.slow_alpha) + self.slow_alpha) ** 2

        if self.kama is None:
            self.kama = prices[-1]
        else:
            self.kama = self.kama + sc * (prices[-1] - self.kama)
        
        return self.kama

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