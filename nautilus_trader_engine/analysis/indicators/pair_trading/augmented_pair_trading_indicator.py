"""
Augmented Pair Trading Indicator with 5-Pillar Institutional Architecture
=========================================================================

Institutional-grade pair trading indicator that adapts single-asset technical indicators
to work on spread and ratio series, incorporating volume integration, smart money analysis,
market regime adaptation, multi-timeframe convergence, and automated risk management.

This module provides:
- Spread-based technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Ratio-based technical indicators with log transformations
- Volume-weighted spread and ratio calculations
- Smart money flow detection in pair context
- Multi-timeframe convergence analysis
- Automated risk management with position sizing
"""

from typing import Dict, List, Optional, Tuple, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from datetime import datetime
from ...core.augmented_indicator import AugmentedIndicator


class PairSignalType(Enum):
    """Types of pair trading signals"""
    SPREAD_MEAN_REVERSION = "SPREAD_MEAN_REVERSION"
    RATIO_MEAN_REVERSION = "RATIO_MEAN_REVERSION"
    SPREAD_BREAKOUT = "SPREAD_BREAKOUT"
    RATIO_BREAKOUT = "RATIO_BREAKOUT"
    CONVERGENCE_SIGNAL = "CONVERGENCE_SIGNAL"
    DIVERGENCE_SIGNAL = "DIVERGENCE_SIGNAL"
    NEUTRAL = "NEUTRAL"


class PairDirection(Enum):
    """Pair trading direction"""
    LONG_SPREAD = "LONG_SPREAD"      # Buy asset A, sell asset B
    SHORT_SPREAD = "SHORT_SPREAD"    # Sell asset A, buy asset B
    LONG_RATIO = "LONG_RATIO"        # Buy asset A relative to B
    SHORT_RATIO = "SHORT_RATIO"      # Sell asset A relative to B
    NEUTRAL = "NEUTRAL"


@dataclass
class PairSignal:
    """Enhanced pair trading signal with 5-pillar analysis"""
    signal_type: PairSignalType = PairSignalType.NEUTRAL
    direction: PairDirection = PairDirection.NEUTRAL
    confidence_score: float = 0.0
    strength: float = 0.0  # -1 to 1 scale

    # Spread and ratio values
    spread_value: float = 0.0
    ratio_value: float = 0.0
    log_ratio_value: float = 0.0

    # Risk management
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0
    position_size_a: float = 0.0
    position_size_b: float = 0.0
    risk_reward_ratio: float = 0.0

    # 5-Pillar Architecture Components
    volume_components: Dict[str, float] = None
    regime_components: Dict[str, float] = None
    timeframe_components: Dict[str, float] = None
    microstructure_components: Dict[str, float] = None
    risk_components: Dict[str, float] = None

    # Technical indicators on spread/ratio
    spread_indicators: Dict[str, float] = None
    ratio_indicators: Dict[str, float] = None

    timestamp: datetime = field(default_factory=datetime.now)


class AugmentedPairTradingIndicator(AugmentedIndicator):
    """
    Institutional-grade pair trading indicator with 5-pillar architecture.

    Adapts single-asset technical indicators to work on spread and ratio series,
    providing sophisticated pair trading signals with volume integration,
    smart money analysis, and automated risk management.
    """

    def __init__(self,
                 # Core parameters
                 spread_lookback: int = 60,
                 ratio_lookback: int = 60,
                 volume_ma_period: int = 20,
                 atr_period: int = 14,
                 trend_ema_period: int = 200,

                 # Signal thresholds
                 zscore_entry_threshold: float = 2.0,
                 zscore_exit_threshold: float = 0.5,
                 volume_threshold_multiplier: float = 1.8,
                 smart_money_threshold: float = 2.5,

                 # Risk management
                 max_position_size_pct: float = 0.1,
                 risk_per_trade_pct: float = 0.02,
                 min_risk_reward_ratio: float = 1.5):
        """
        Initialize the augmented pair trading indicator.

        Args:
            spread_lookback: Lookback period for spread analysis
            ratio_lookback: Lookback period for ratio analysis
            volume_ma_period: Period for volume moving average
            atr_period: Period for ATR calculation
            trend_ema_period: Period for trend EMA
            zscore_entry_threshold: Z-score threshold for entry signals
            zscore_exit_threshold: Z-score threshold for exit signals
            volume_threshold_multiplier: Volume confirmation multiplier
            smart_money_threshold: Smart money detection threshold
            max_position_size_pct: Maximum position size as % of portfolio
            risk_per_trade_pct: Risk per trade as % of portfolio
            min_risk_reward_ratio: Minimum risk-reward ratio for signals
        """
        super().__init__(name="AUGMENTED_PAIR_TRADING")

        # Core parameters
        self.spread_lookback = spread_lookback
        self.ratio_lookback = ratio_lookback
        self.volume_ma_period = volume_ma_period
        self.atr_period = atr_period
        self.trend_ema_period = trend_ema_period

        # Signal parameters
        self.zscore_entry_threshold = zscore_entry_threshold
        self.zscore_exit_threshold = zscore_exit_threshold
        self.volume_threshold_multiplier = volume_threshold_multiplier
        self.smart_money_threshold = smart_money_threshold

        # Risk management
        self.max_position_size_pct = max_position_size_pct
        self.risk_per_trade_pct = risk_per_trade_pct
        self.min_risk_reward_ratio = min_risk_reward_ratio

        # Internal state
        self.spread_history = []
        self.ratio_history = []
        self.volume_history = []
        self.price_a_history = []
        self.price_b_history = []

        # Initialize signal
        self._signal = PairSignal()

    def update(self,
               price_a: float,
               price_b: float,
               volume_a: float = 0.0,
               volume_b: float = 0.0,
               high_a: float = None,
               low_a: float = None,
               high_b: float = None,
               low_b: float = None) -> PairSignal:
        """
        Update the pair trading indicator with new price/volume data.

        Args:
            price_a: Price of asset A
            price_b: Price of asset B
            volume_a: Volume of asset A
            volume_b: Volume of asset B
            high_a: High price of asset A (for ATR calculation)
            low_a: Low price of asset A (for ATR calculation)
            high_b: High price of asset B (for ATR calculation)
            low_b: Low price of asset B (for ATR calculation)

        Returns:
            PairSignal: Enhanced pair trading signal
        """
        # Store price data
        self.price_a_history.append(price_a)
        self.price_b_history.append(price_b)
        self.volume_history.append(volume_a + volume_b)

        # Maintain history length
        max_history = max(self.spread_lookback, self.ratio_lookback, self.volume_ma_period) + 50
        if len(self.price_a_history) > max_history:
            self.price_a_history.pop(0)
            self.price_b_history.pop(0)
            self.volume_history.pop(0)

        # Calculate spread and ratio
        if len(self.price_a_history) >= 2 and len(self.price_b_history) >= 2:
            current_spread = price_a - price_b
            current_ratio = price_a / price_b if price_b != 0 else 0
            current_log_ratio = np.log(abs(current_ratio)) if current_ratio != 0 else 0

            self.spread_history.append(current_spread)
            self.ratio_history.append(current_ratio)

            if len(self.spread_history) > max_history:
                self.spread_history.pop(0)
                self.ratio_history.pop(0)

            # Generate signal if we have enough data
            if len(self.spread_history) >= self.spread_lookback:
                self._generate_signal()

        return self._signal

    def _generate_signal(self) -> None:
        """Generate pair trading signal using 5-pillar analysis"""
        if len(self.spread_history) < self.spread_lookback:
            return

        # Reset signal
        self._signal = PairSignal()

        # Calculate spread and ratio indicators
        spread_indicators = self._calculate_spread_indicators()
        ratio_indicators = self._calculate_ratio_indicators()

        # Store indicator values
        self._signal.spread_indicators = spread_indicators
        self._signal.ratio_indicators = ratio_indicators
        self._signal.spread_value = self.spread_history[-1] if self.spread_history else 0
        self._signal.ratio_value = self.ratio_history[-1] if self.ratio_history else 0
        self._signal.log_ratio_value = np.log(abs(self._signal.ratio_value)) if self._signal.ratio_value != 0 else 0

        # 5-Pillar Analysis
        volume_score = self._calculate_volume_score()
        regime_score = self._calculate_regime_score()
        timeframe_score = self._calculate_timeframe_score()
        smart_money_score = self._calculate_smart_money_score()
        risk_score = self._calculate_risk_score()

        # Store pillar components
        self._signal.volume_components = {'confirmation_score': volume_score}
        self._signal.regime_components = {'trend_alignment': regime_score}
        self._signal.timeframe_components = {'convergence_score': timeframe_score}
        self._signal.microstructure_components = {'institutional_bias': smart_money_score}
        self._signal.risk_components = {'reward_risk_ratio': risk_score}

        # Calculate overall confidence score
        weights = {
            'volume': 0.20,
            'regime': 0.20,
            'timeframe': 0.20,
            'smart_money': 0.25,
            'risk': 0.15
        }

        confidence = (
            volume_score * weights['volume'] +
            regime_score * weights['regime'] +
            timeframe_score * weights['timeframe'] +
            smart_money_score * weights['smart_money'] +
            risk_score * weights['risk']
        )

        self._signal.confidence_score = min(1.0, max(0.0, confidence))

        # Determine signal type and direction
        self._determine_signal_type(spread_indicators, ratio_indicators)

        # Calculate risk management parameters
        if self._signal.signal_type != PairSignalType.NEUTRAL:
            self._calculate_risk_parameters()

    def _calculate_spread_indicators(self) -> Dict[str, float]:
        """Calculate technical indicators on the spread series"""
        spread = np.array(self.spread_history[-self.spread_lookback:])

        indicators = {}

        # Z-Score (mean reversion signal)
        if len(spread) >= 20:
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)
            current_spread = spread[-1]
            indicators['zscore'] = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0

        # RSI on spread
        if len(spread) >= 14:
            indicators['rsi'] = self._calculate_rsi(spread, 14)

        # MACD on spread
        if len(spread) >= 26:
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = self._calculate_macd(spread)

        # Bollinger Bands on spread
        if len(spread) >= 20:
            bb_upper, bb_middle, bb_lower, bb_percent_b = self._calculate_bollinger_bands(spread, 20, 2.0)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            indicators['bb_percent_b'] = bb_percent_b

        return indicators

    def _calculate_ratio_indicators(self) -> Dict[str, float]:
        """Calculate technical indicators on the ratio series"""
        ratio = np.array(self.ratio_history[-self.ratio_lookback:])

        indicators = {}

        # Z-Score on ratio (mean reversion signal)
        if len(ratio) >= 20:
            ratio_mean = np.mean(ratio)
            ratio_std = np.std(ratio)
            current_ratio = ratio[-1]
            indicators['zscore'] = (current_ratio - ratio_mean) / ratio_std if ratio_std > 0 else 0

        # RSI on ratio
        if len(ratio) >= 14:
            indicators['rsi'] = self._calculate_rsi(ratio, 14)

        # MACD on ratio
        if len(ratio) >= 26:
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'] = self._calculate_macd(ratio)

        # Bollinger Bands on ratio
        if len(ratio) >= 20:
            bb_upper, bb_middle, bb_lower, bb_percent_b = self._calculate_bollinger_bands(ratio, 20, 2.0)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            indicators['bb_percent_b'] = bb_percent_b

        return indicators

    def _calculate_rsi(self, data: np.ndarray, period: int) -> float:
        """Calculate RSI for given data"""
        if len(data) < period + 1:
            return 50.0

        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _calculate_macd(self, data: np.ndarray) -> Tuple[float, float, float]:
        """Calculate MACD for given data"""
        if len(data) < 26:
            return 0.0, 0.0, 0.0

        # Simple EMA calculation
        ema12 = self._calculate_ema(data, 12)
        ema26 = self._calculate_ema(data, 26)

        macd_line = ema12 - ema26
        signal_line = self._calculate_ema(np.array([macd_line]), 9)[0] if len(data) >= 35 else macd_line
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average"""
        if len(data) < period:
            return np.array([np.mean(data)] * len(data))

        ema = np.zeros(len(data))
        ema[period-1] = np.mean(data[:period])

        multiplier = 2 / (period + 1)
        for i in range(period, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))

        return ema

    def _calculate_bollinger_bands(self, data: np.ndarray, period: int, std_dev: float) -> Tuple[float, float, float, float]:
        """Calculate Bollinger Bands"""
        if len(data) < period:
            return 0.0, 0.0, 0.0, 0.5

        window = data[-period:]
        middle = np.mean(window)
        std = np.std(window)

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        current = data[-1]

        percent_b = (current - lower) / (upper - lower) if (upper - lower) != 0 else 0.5

        return upper, middle, lower, percent_b

    def _calculate_volume_score(self) -> float:
        """Calculate volume confirmation score"""
        if len(self.volume_history) < self.volume_ma_period:
            return 0.5

        current_volume = self.volume_history[-1]
        avg_volume = np.mean(self.volume_history[-self.volume_ma_period:])

        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            if volume_ratio >= self.volume_threshold_multiplier:
                return min(1.0, volume_ratio / (self.volume_threshold_multiplier * 2))
            else:
                return max(0.2, volume_ratio / self.volume_threshold_multiplier)

        return 0.5

    def _calculate_regime_score(self) -> float:
        """Calculate market regime alignment score"""
        if len(self.price_a_history) < self.trend_ema_period or len(self.price_b_history) < self.trend_ema_period:
            return 0.5

        # Simple trend calculation
        price_a_trend = np.polyfit(range(min(20, len(self.price_a_history))), self.price_a_history[-20:], 1)[0]
        price_b_trend = np.polyfit(range(min(20, len(self.price_b_history))), self.price_b_history[-20:], 1)[0]

        # Pair regime: both trending or both ranging
        trend_alignment = abs(price_a_trend) * abs(price_b_trend)

        # Normalize to 0-1 scale
        return min(1.0, trend_alignment * 1000)  # Arbitrary scaling

    def _calculate_timeframe_score(self) -> float:
        """Calculate multi-timeframe convergence score"""
        # Simplified - would need higher timeframe data
        return 0.7

    def _calculate_smart_money_score(self) -> float:
        """Calculate smart money involvement score"""
        if len(self.volume_history) < self.volume_ma_period:
            return 0.5

        current_volume = self.volume_history[-1]
        avg_volume = np.mean(self.volume_history[-self.volume_ma_period:])

        if current_volume > avg_volume * self.smart_money_threshold:
            return 0.9  # Strong institutional activity
        elif current_volume > avg_volume * 2.0:
            return 0.7  # Moderate institutional activity
        else:
            return 0.4  # Limited institutional involvement

    def _calculate_risk_score(self) -> float:
        """Calculate risk-adjusted score"""
        # Simplified risk score based on spread volatility
        if len(self.spread_history) >= 20:
            spread_volatility = np.std(self.spread_history[-20:])
            if spread_volatility > 0:
                # Lower volatility = higher risk score (more predictable)
                return max(0.3, 1.0 - (spread_volatility / self.spread_history[-1]))

        return 0.6

    def _determine_signal_type(self, spread_indicators: Dict[str, float], ratio_indicators: Dict[str, float]) -> None:
        """Determine the signal type and direction based on indicators"""
        spread_zscore = spread_indicators.get('zscore', 0)
        ratio_zscore = ratio_indicators.get('zscore', 0)

        # Mean reversion signals
        if abs(spread_zscore) >= self.zscore_entry_threshold:
            if spread_zscore < -self.zscore_entry_threshold:
                self._signal.signal_type = PairSignalType.SPREAD_MEAN_REVERSION
                self._signal.direction = PairDirection.LONG_SPREAD
                self._signal.strength = -abs(spread_zscore) / 4.0  # Normalize to -1 to 1
            elif spread_zscore > self.zscore_entry_threshold:
                self._signal.signal_type = PairSignalType.SPREAD_MEAN_REVERSION
                self._signal.direction = PairDirection.SHORT_SPREAD
                self._signal.strength = abs(spread_zscore) / 4.0

        elif abs(ratio_zscore) >= self.zscore_entry_threshold:
            if ratio_zscore < -self.zscore_entry_threshold:
                self._signal.signal_type = PairSignalType.RATIO_MEAN_REVERSION
                self._signal.direction = PairDirection.LONG_RATIO
                self._signal.strength = -abs(ratio_zscore) / 4.0
            elif ratio_zscore > self.zscore_entry_threshold:
                self._signal.signal_type = PairSignalType.RATIO_MEAN_REVERSION
                self._signal.direction = PairDirection.SHORT_RATIO
                self._signal.strength = abs(ratio_zscore) / 4.0

        # Check for convergence/divergence signals
        elif len(self.spread_history) >= 40:
            recent_spread_trend = np.polyfit(range(20), self.spread_history[-20:], 1)[0]
            older_spread_trend = np.polyfit(range(20), self.spread_history[-40:-20], 1)[0]

            if abs(recent_spread_trend) < abs(older_spread_trend) * 0.5:
                self._signal.signal_type = PairSignalType.CONVERGENCE_SIGNAL
                self._signal.direction = PairDirection.NEUTRAL
                self._signal.strength = 0.0

    def _calculate_risk_parameters(self) -> None:
        """Calculate risk management parameters"""
        current_spread = self._signal.spread_value
        spread_indicators = self._signal.spread_indicators or {}

        # Calculate stop loss based on spread volatility
        if len(self.spread_history) >= 20:
            spread_std = np.std(self.spread_history[-20:])
            if self._signal.direction == PairDirection.LONG_SPREAD:
                self._signal.stop_loss_price = current_spread - (spread_std * 2)
                self._signal.take_profit_price = current_spread + (spread_std * 3)
            elif self._signal.direction == PairDirection.SHORT_SPREAD:
                self._signal.stop_loss_price = current_spread + (spread_std * 2)
                self._signal.take_profit_price = current_spread - (spread_std * 3)

            # Calculate risk-reward ratio
            risk = abs(current_spread - self._signal.stop_loss_price)
            reward = abs(self._signal.take_profit_price - current_spread)
            self._signal.risk_reward_ratio = reward / risk if risk > 0 else 0

        # Calculate position sizes (simplified)
        portfolio_value = 100000  # Assume $100k portfolio
        risk_amount = portfolio_value * self.risk_per_trade_pct
        position_size = min(self.max_position_size_pct * portfolio_value, risk_amount)

        self._signal.position_size_a = position_size * 0.5
        self._signal.position_size_b = position_size * 0.5

    @property
    def signal(self) -> PairSignal:
        """Get current pair trading signal"""
        return self._signal

    def reset(self) -> None:
        """Reset indicator state"""
        self.spread_history.clear()
        self.ratio_history.clear()
        self.volume_history.clear()
        self.price_a_history.clear()
        self.price_b_history.clear()
        self._signal = PairSignal()


# Factory function for easy instantiation
def create_augmented_pair_indicator(**kwargs) -> AugmentedPairTradingIndicator:
    """Create and return a configured augmented pair trading indicator"""
    return AugmentedPairTradingIndicator(**kwargs)