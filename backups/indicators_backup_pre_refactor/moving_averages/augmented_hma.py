"""
Augmented Hull Moving Average (HMA) Indicator

An institutional-grade implementation of the Hull Moving Average (HMA) that
integrates the 5-pillar augmentation architecture.

Pillars Integrated:
1.  **Volume Integration**: HMA calculation can be volume-weighted.
2.  **Market Regime Adaptation**: Signal generation is sensitive to the current market regime.
3.  **Multi-Timeframe Convergence**: Confidence is boosted when HMAs across different timeframes align.
4.  **Smart Money Proxies**: Confidence is adjusted based on approximations of smart money activity.
5.  **Risk Management Factory**: The indicator output includes suggested stop-loss and take-profit levels.
"""

import math
import numpy as np
from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import PriceType
from nautilus_trader.model.events import OrderSide
from nautilus_trader.model.instruments import Instrument

from nautilus_trader_engine.indicators.core.augmented_indicator import AugmentedIndicator, SignalType, MarketRegime, IndicatorOutput
from nautilus_trader_engine.indicators.moving_averages.augmented_wma import AugmentedWMA


class AugmentedHMA(AugmentedIndicator):
    """
    An augmented Hull Moving Average (HMA) indicator.
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
        Initializes the AugmentedHMA indicator.

        Args:
            period (int): The period for the HMA calculation.
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
        
        self.wma_half = AugmentedWMA(period // 2, price_type, instrument, volume_weight, regime_sensitivity, timeframes, risk_multiplier)
        self.wma_full = AugmentedWMA(period, price_type, instrument, volume_weight, regime_sensitivity, timeframes, risk_multiplier)
        self.wma_sqrt = AugmentedWMA(int(math.sqrt(period)), price_type, instrument, volume_weight, regime_sensitivity, timeframes, risk_multiplier)

    def update(self, price: float, volume: float, timestamp: "datetime") -> "IndicatorOutput":
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
        
        # Update WMAs
        self.wma_half.update(price, volume, timestamp)
        self.wma_full.update(price, volume, timestamp)

        if self.wma_half.is_ready and self.wma_full.is_ready:
            wma_diff = 2 * self.wma_half.value - self.wma_full.value
            self.wma_sqrt.update(wma_diff, volume, timestamp)

        # Apply 5-pillar augmentation
        return self._calculate_augmented_output(timestamp)

    def calculate_raw_value(self, prices: np.ndarray, volumes: np.ndarray) -> float:
        """
        Calculates the raw HMA value.

        Args:
            prices (np.ndarray): An array of prices.
            volumes (np.ndarray): An array of volumes.

        Returns:
            float: The raw HMA value.
        """
        if not self.wma_sqrt.is_ready:
            return prices[-1] # Not enough data

        return self.wma_sqrt.value

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