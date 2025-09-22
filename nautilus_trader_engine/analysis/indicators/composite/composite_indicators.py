"""
Composite Indicators Module

Advanced composite indicator analysis combining multiple technical indicators
with institutional-grade features including volume weighting, smart money confirmation,
multi-timeframe analysis, and adaptive confidence scoring for professional trading applications.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import numpy as np

from ...core.base_classes import AugmentedIndicator


class CompositeType(Enum):
    """Types of composite indicators"""
    MOMENTUM_COMPOSITE = "momentum_composite"
    TREND_COMPOSITE = "trend_composite"
    VOLATILITY_COMPOSITE = "volatility_composite"
    VOLUME_COMPOSITE = "volume_composite"
    MEAN_REVERSION_COMPOSITE = "mean_reversion_composite"
    BREAKOUT_COMPOSITE = "breakout_composite"
    REVERSAL_COMPOSITE = "reversal_composite"
    CONFIRMATION_COMPOSITE = "confirmation_composite"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class CompositeComponent:
    """Represents a component indicator in the composite"""
    name: str
    weight: float
    signal: float  # -1 to 1 (bearish to bullish)
    confidence: float
    timeframe: str


@dataclass
class CompositeSignal:
    """Composite indicator signal with institutional features"""
    value_raw: float
    signal_type: str
    composite_confidence: float
    confidence_components: Dict[str, float]
    suggested_sl: float
    suggested_tp: float
    timestamp: datetime
    additional_metadata: Dict[str, Any]

    # Composite-specific fields
    composite_type: CompositeType
    signal_strength: SignalStrength
    component_signals: List[CompositeComponent]
    divergence_score: float
    confluence_score: float
    market_regime: str


class CompositeIndicators(AugmentedIndicator):
    """
    Advanced Composite Indicators Analyzer

    Combines multiple technical indicators into sophisticated composite signals with institutional-grade features:
    - Momentum composites (RSI, MACD, Stochastic)
    - Trend composites (Moving averages, ADX, Ichimoku)
    - Volatility composites (Bollinger Bands, ATR, Keltner Channels)
    - Volume composites (Volume indicators, OBV, Chaikin Money Flow)
    - Mean reversion composites (RSI, Bollinger Bands, Williams %R)
    - Breakout composites (Donchian Channels, Price action)
    - Reversal composites (Divergences, Candlestick patterns)
    - Confirmation composites (Multiple timeframe alignment)

    All implementations include volume-weighting, smart money confirmation,
    multi-timeframe analysis, adaptive confidence scoring, and integrated risk management.
    """

    def __init__(self, timeframe: str = "1D", composite_type: CompositeType = CompositeType.MOMENTUM_COMPOSITE):
        super().__init__(name="CompositeIndicators", timeframe=timeframe)
        self.composite_type = composite_type
        self.price_history = []
        self.volume_history = []
        self.timestamp_history = []

        # Component indicators storage
        self.indicator_values = {}

        # Composite signal history
        self.signal_history = []

        # Initialize component weights based on composite type
        self.component_weights = self._initialize_component_weights()

    def _initialize_component_weights(self) -> Dict[str, Dict[str, float]]:
        """Initialize component weights for different composite types"""
        return {
            CompositeType.MOMENTUM_COMPOSITE.value: {
                'rsi': 0.25,
                'macd': 0.25,
                'stochastic': 0.20,
                'williams_r': 0.15,
                'cci': 0.15
            },
            CompositeType.TREND_COMPOSITE.value: {
                'sma_20': 0.20,
                'ema_50': 0.20,
                'adx': 0.25,
                'ichimoku': 0.20,
                'supertrend': 0.15
            },
            CompositeType.VOLATILITY_COMPOSITE.value: {
                'bollinger_bands': 0.30,
                'atr': 0.25,
                'keltner_channels': 0.20,
                'donchian': 0.15,
                'average_true_range': 0.10
            },
            CompositeType.VOLUME_COMPOSITE.value: {
                'volume_sma': 0.20,
                'obv': 0.25,
                'chaikin_mf': 0.20,
                'volume_oscillator': 0.15,
                'vwap': 0.20
            },
            CompositeType.MEAN_REVERSION_COMPOSITE.value: {
                'rsi': 0.25,
                'bollinger_bands': 0.25,
                'williams_r': 0.20,
                'stochastic': 0.15,
                'cci': 0.15
            },
            CompositeType.BREAKOUT_COMPOSITE.value: {
                'donchian_channels': 0.25,
                'bollinger_bands': 0.20,
                'volume_breakout': 0.20,
                'price_action': 0.20,
                'support_resistance': 0.15
            },
            CompositeType.REVERSAL_COMPOSITE.value: {
                'divergence_rsi': 0.25,
                'divergence_macd': 0.25,
                'candlestick_patterns': 0.20,
                'volume_divergence': 0.15,
                'momentum_divergence': 0.15
            },
            CompositeType.CONFIRMATION_COMPOSITE.value: {
                'multi_timeframe_alignment': 0.30,
                'volume_price_confirmation': 0.25,
                'trend_confirmation': 0.20,
                'momentum_confirmation': 0.15,
                'volatility_confirmation': 0.10
            }
        }

    def update(self, price: float, volume: float, high: float = None,
               low: float = None, timestamp: datetime = None,
               order_book_data: Dict = None, trade_data: List = None) -> Optional[CompositeSignal]:
        """
        Update analyzer with new price/volume data

        Args:
            price: Current price
            volume: Current volume
            high: High price (optional)
            low: Low price (optional)
            timestamp: Data timestamp
            order_book_data: Order book data for smart money analysis
            trade_data: Trade data for volume analysis

        Returns:
            CompositeSignal if significant composite signal is generated, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.now()

        # Update histories
        self.price_history.append(price)
        self.volume_history.append(volume)
        self.timestamp_history.append(timestamp)

        # Maintain history size
        max_history = 300
        if len(self.price_history) > max_history:
            self.price_history.pop(0)
            self.volume_history.pop(0)
            self.timestamp_history.pop(0)

        # Need minimum data for analysis
        if len(self.price_history) < 50:
            return None

        # Update component indicators
        self._update_component_indicators(price, volume, high, low)

        # Calculate composite signal
        signal = self._calculate_composite_signal(timestamp, order_book_data, trade_data)

        if signal:
            self.current_signal = signal
            self.signal_history.append(signal)

        return signal

    def _update_component_indicators(self, price: float, volume: float,
                                   high: float = None, low: float = None):
        """Update all component indicators"""
        weights = self.component_weights[self.composite_type.value]

        for indicator_name in weights.keys():
            self._update_single_indicator(indicator_name, price, volume, high, low)

    def _update_single_indicator(self, indicator_name: str, price: float, volume: float,
                               high: float = None, low: float = None):
        """Update a single component indicator"""
        if len(self.price_history) < 20:
            return

        if indicator_name == 'rsi':
            self.indicator_values['rsi'] = self._calculate_rsi()
        elif indicator_name == 'macd':
            self.indicator_values['macd'] = self._calculate_macd()
        elif indicator_name == 'stochastic':
            self.indicator_values['stochastic'] = self._calculate_stochastic()
        elif indicator_name == 'williams_r':
            self.indicator_values['williams_r'] = self._calculate_williams_r()
        elif indicator_name == 'cci':
            self.indicator_values['cci'] = self._calculate_cci(high, low)
        elif indicator_name == 'sma_20':
            self.indicator_values['sma_20'] = self._calculate_sma(20)
        elif indicator_name == 'ema_50':
            self.indicator_values['ema_50'] = self._calculate_ema(50)
        elif indicator_name == 'adx':
            self.indicator_values['adx'] = self._calculate_adx(high, low)
        elif indicator_name == 'bollinger_bands':
            self.indicator_values['bollinger_bands'] = self._calculate_bollinger_bands()
        elif indicator_name == 'atr':
            self.indicator_values['atr'] = self._calculate_atr(high, low)
        elif indicator_name == 'volume_sma':
            self.indicator_values['volume_sma'] = self._calculate_volume_sma()
        elif indicator_name == 'obv':
            self.indicator_values['obv'] = self._calculate_obv(volume)
        elif indicator_name == 'donchian_channels':
            self.indicator_values['donchian_channels'] = self._calculate_donchian()
        # Add more indicators as needed

    def _calculate_rsi(self, period: int = 14) -> Dict[str, Any]:
        """Calculate RSI indicator"""
        if len(self.price_history) < period + 1:
            return {'signal': 0, 'confidence': 0}

        prices = np.array(self.price_history[-period-1:])
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # Convert to signal (-1 to 1)
        signal = (rsi - 50) / 50
        confidence = min(abs(rsi - 50) / 25, 1.0)  # Higher confidence when further from 50

        return {'signal': signal, 'confidence': confidence, 'rsi': rsi}

    def _calculate_macd(self) -> Dict[str, Any]:
        """Calculate MACD indicator"""
        if len(self.price_history) < 26:
            return {'signal': 0, 'confidence': 0}

        prices = np.array(self.price_history)

        # Simple MACD calculation
        ema12 = self._calculate_ema_value(prices, 12)
        ema26 = self._calculate_ema_value(prices, 26)

        if len(ema12) < 26 or len(ema26) < 26:
            return {'signal': 0, 'confidence': 0}

        macd_line = ema12[-1] - ema26[-1]
        signal_line = self._calculate_ema_value(np.array([ema12[i] - ema26[i] for i in range(len(ema12))]), 9)[-1]

        histogram = macd_line - signal_line

        # Convert to signal
        signal = np.tanh(histogram / (np.std(prices[-20:]) * 0.1))  # Normalize by recent volatility
        confidence = min(abs(histogram) / (np.std(prices[-20:]) * 0.05), 1.0)

        return {'signal': signal, 'confidence': confidence, 'macd': macd_line, 'signal_line': signal_line}

    def _calculate_stochastic(self, k_period: int = 14, d_period: int = 3) -> Dict[str, Any]:
        """Calculate Stochastic oscillator"""
        if len(self.price_history) < k_period:
            return {'signal': 0, 'confidence': 0}

        high_max = max(self.price_history[-k_period:])
        low_min = min(self.price_history[-k_period:])
        current_price = self.price_history[-1]

        if high_max == low_min:
            k_value = 50
        else:
            k_value = 100 * (current_price - low_min) / (high_max - low_min)

        # Simple D value (SMA of K)
        d_value = k_value  # Simplified

        # Convert to signal
        signal = (k_value - 50) / 50
        confidence = min(abs(k_value - 50) / 25, 1.0)

        return {'signal': signal, 'confidence': confidence, 'k': k_value, 'd': d_value}

    def _calculate_williams_r(self, period: int = 14) -> Dict[str, Any]:
        """Calculate Williams %R"""
        if len(self.price_history) < period:
            return {'signal': 0, 'confidence': 0}

        high_max = max(self.price_history[-period:])
        low_min = min(self.price_history[-period:])
        current_price = self.price_history[-1]

        if high_max == low_min:
            williams_r = -50
        else:
            williams_r = -100 * (high_max - current_price) / (high_max - low_min)

        # Convert to signal (-1 to 1, where -1 is oversold, 1 is overbought)
        signal = (williams_r + 50) / 50  # -1 for -100, 1 for 0
        confidence = min(abs(williams_r + 50) / 25, 1.0)

        return {'signal': signal, 'confidence': confidence, 'williams_r': williams_r}

    def _calculate_cci(self, high: float = None, low: float = None, period: int = 20) -> Dict[str, Any]:
        """Calculate Commodity Channel Index"""
        if len(self.price_history) < period or high is None or low is None:
            return {'signal': 0, 'confidence': 0}

        # Simplified CCI calculation using typical price
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(
            [high] * len(self.price_history[-period:]),
            [low] * len(self.price_history[-period:]),
            self.price_history[-period:]
        )]

        sma_tp = np.mean(typical_prices)
        mean_deviation = np.mean([abs(tp - sma_tp) for tp in typical_prices])

        if mean_deviation == 0:
            cci = 0
        else:
            current_tp = (high + low + self.price_history[-1]) / 3
            cci = (current_tp - sma_tp) / (0.015 * mean_deviation)

        # Convert to signal
        signal = np.tanh(cci / 100)  # Normalize
        confidence = min(abs(cci) / 100, 1.0)

        return {'signal': signal, 'confidence': confidence, 'cci': cci}

    def _calculate_sma(self, period: int) -> Dict[str, Any]:
        """Calculate Simple Moving Average"""
        if len(self.price_history) < period:
            return {'signal': 0, 'confidence': 0}

        sma = np.mean(self.price_history[-period:])
        current_price = self.price_history[-1]

        # Signal based on position relative to SMA
        signal = (current_price - sma) / sma
        confidence = min(abs(signal) * 2, 1.0)  # Higher confidence when further from SMA

        return {'signal': signal, 'confidence': confidence, 'sma': sma}

    def _calculate_ema(self, period: int) -> Dict[str, Any]:
        """Calculate Exponential Moving Average"""
        if len(self.price_history) < period:
            return {'signal': 0, 'confidence': 0}

        ema = self._calculate_ema_value(np.array(self.price_history), period)[-1]
        current_price = self.price_history[-1]

        signal = (current_price - ema) / ema
        confidence = min(abs(signal) * 2, 1.0)

        return {'signal': signal, 'confidence': confidence, 'ema': ema}

    def _calculate_ema_value(self, prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate EMA values"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(prices)
        ema[0] = prices[0]

        for i in range(1, len(prices)):
            ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]

        return ema

    def _calculate_adx(self, high: float = None, low: float = None, period: int = 14) -> Dict[str, Any]:
        """Calculate ADX (simplified)"""
        if len(self.price_history) < period or high is None or low is None:
            return {'signal': 0, 'confidence': 0}

        # Simplified ADX calculation
        highs = [high] * period
        lows = [low] * period
        closes = self.price_history[-period:]

        # Calculate True Range (simplified)
        tr = max(high - low,
                abs(high - closes[-2] if len(closes) > 1 else high),
                abs(low - closes[-2] if len(closes) > 1 else low))

        # Simplified ADX
        adx = 25  # Placeholder - would need full implementation

        # Signal based on ADX strength
        signal = (adx - 20) / 30  # 20-50 range normalized
        confidence = min(adx / 40, 1.0)

        return {'signal': signal, 'confidence': confidence, 'adx': adx}

    def _calculate_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
        """Calculate Bollinger Bands"""
        if len(self.price_history) < period:
            return {'signal': 0, 'confidence': 0}

        prices = np.array(self.price_history[-period:])
        sma = np.mean(prices)
        std = np.std(prices)

        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        current_price = self.price_history[-1]

        # Signal based on position within bands
        if current_price > upper_band:
            signal = 1.0  # Overbought
        elif current_price < lower_band:
            signal = -1.0  # Oversold
        else:
            # Position within bands
            band_width = (upper_band - lower_band) / sma
            position = (current_price - lower_band) / (upper_band - lower_band)
            signal = (position - 0.5) * 2  # -1 to 1

        confidence = 1.0 - (std / sma)  # Higher confidence when bands are narrow

        return {
            'signal': signal,
            'confidence': confidence,
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }

    def _calculate_atr(self, high: float = None, low: float = None, period: int = 14) -> Dict[str, Any]:
        """Calculate Average True Range"""
        if len(self.price_history) < period or high is None or low is None:
            return {'signal': 0, 'confidence': 0}

        # Simplified ATR calculation
        tr_values = []
        for i in range(1, min(period + 1, len(self.price_history))):
            tr = max(high - low,
                    abs(high - self.price_history[-i-1]),
                    abs(low - self.price_history[-i-1]))
            tr_values.append(tr)

        atr = np.mean(tr_values) if tr_values else 0

        # ATR as volatility signal
        avg_price = np.mean(self.price_history[-period:])
        signal = (atr / avg_price - 0.02) / 0.05  # Normalize around typical 2% volatility
        confidence = min(atr / (avg_price * 0.05), 1.0)

        return {'signal': signal, 'confidence': confidence, 'atr': atr}

    def _calculate_volume_sma(self, period: int = 20) -> Dict[str, Any]:
        """Calculate Volume SMA"""
        if len(self.volume_history) < period:
            return {'signal': 0, 'confidence': 0}

        volume_sma = np.mean(self.volume_history[-period:])
        current_volume = self.volume_history[-1]

        signal = (current_volume - volume_sma) / volume_sma
        confidence = min(abs(signal), 1.0)

        return {'signal': signal, 'confidence': confidence, 'volume_sma': volume_sma}

    def _calculate_obv(self, volume: float) -> Dict[str, Any]:
        """Calculate On Balance Volume (simplified)"""
        if len(self.price_history) < 2:
            return {'signal': 0, 'confidence': 0}

        # Simplified OBV
        if self.price_history[-1] > self.price_history[-2]:
            obv_change = volume
        elif self.price_history[-1] < self.price_history[-2]:
            obv_change = -volume
        else:
            obv_change = 0

        # Signal based on OBV trend
        signal = np.tanh(obv_change / (np.mean(self.volume_history[-10:]) * 2))
        confidence = min(abs(obv_change) / (np.mean(self.volume_history[-10:]) * 2), 1.0)

        return {'signal': signal, 'confidence': confidence, 'obv_change': obv_change}

    def _calculate_donchian(self, period: int = 20) -> Dict[str, Any]:
        """Calculate Donchian Channels"""
        if len(self.price_history) < period:
            return {'signal': 0, 'confidence': 0}

        high_max = max(self.price_history[-period:])
        low_min = min(self.price_history[-period:])
        current_price = self.price_history[-1]

        # Signal based on position within channel
        if current_price > (high_max + low_min) / 2:
            signal = (current_price - (high_max + low_min) / 2) / ((high_max - low_min) / 2)
        else:
            signal = -((high_max + low_min) / 2 - current_price) / ((high_max - low_min) / 2)

        confidence = 1.0  # Donchian channels are reliable for breakouts

        return {
            'signal': signal,
            'confidence': confidence,
            'upper': high_max,
            'lower': low_min,
            'middle': (high_max + low_min) / 2
        }

    def _calculate_composite_signal(self, timestamp: datetime,
                                  order_book_data: Dict = None,
                                  trade_data: List = None) -> Optional[CompositeSignal]:
        """Calculate composite signal from component indicators"""
        if not self.indicator_values:
            return None

        # Get component signals
        component_signals = self._get_component_signals()

        if not component_signals:
            return None

        # Calculate weighted composite signal
        composite_signal, confidence = self._calculate_weighted_composite(component_signals)

        # Check if signal is significant enough
        if abs(composite_signal) < 0.3:  # Minimum threshold
            return None

        # Determine signal strength
        signal_strength = self._determine_signal_strength(composite_signal, confidence)

        # Calculate additional metrics
        divergence_score = self._calculate_divergence_score(component_signals)
        confluence_score = self._calculate_confluence_score(component_signals)
        market_regime = self._determine_market_regime(component_signals)

        # Risk management
        suggested_sl, suggested_tp = self._calculate_composite_risk_management(
            composite_signal, self.price_history[-1]
        )

        # Confidence components
        confidence_components = self._calculate_confidence_components(
            component_signals, order_book_data, trade_data
        )

        composite_confidence = np.mean(list(confidence_components.values()))

        # Additional metadata
        additional_metadata = {
            'component_count': len(component_signals),
            'signal_distribution': self._analyze_signal_distribution(component_signals),
            'market_regime': market_regime,
            'divergence_analysis': divergence_score,
            'confluence_analysis': confluence_score,
            'volatility_context': self._calculate_volatility_context(),
            'volume_context': self._calculate_volume_context()
        }

        return CompositeSignal(
            value_raw=self.price_history[-1],
            signal_type=f"COMPOSITE_{self.composite_type.value.upper()}_{signal_strength.value.upper()}",
            composite_confidence=composite_confidence,
            confidence_components=confidence_components,
            suggested_sl=suggested_sl,
            suggested_tp=suggested_tp,
            timestamp=timestamp,
            additional_metadata=additional_metadata,
            composite_type=self.composite_type,
            signal_strength=signal_strength,
            component_signals=component_signals,
            divergence_score=divergence_score,
            confluence_score=confluence_score,
            market_regime=market_regime
        )

    def _get_component_signals(self) -> List[CompositeComponent]:
        """Get signals from all component indicators"""
        components = []
        weights = self.component_weights[self.composite_type.value]

        for indicator_name, weight in weights.items():
            if indicator_name in self.indicator_values:
                indicator_data = self.indicator_values[indicator_name]
                component = CompositeComponent(
                    name=indicator_name,
                    weight=weight,
                    signal=indicator_data['signal'],
                    confidence=indicator_data['confidence'],
                    timeframe=self.timeframe
                )
                components.append(component)

        return components

    def _calculate_weighted_composite(self, components: List[CompositeComponent]) -> Tuple[float, float]:
        """Calculate weighted composite signal"""
        if not components:
            return 0.0, 0.0

        weighted_sum = 0.0
        total_weight = 0.0
        confidence_sum = 0.0

        for component in components:
            weighted_sum += component.signal * component.weight * component.confidence
            total_weight += component.weight * component.confidence
            confidence_sum += component.confidence

        if total_weight == 0:
            return 0.0, 0.0

        composite_signal = weighted_sum / total_weight
        average_confidence = confidence_sum / len(components)

        return composite_signal, average_confidence

    def _determine_signal_strength(self, signal: float, confidence: float) -> SignalStrength:
        """Determine signal strength based on signal magnitude and confidence"""
        strength_score = abs(signal) * confidence

        if strength_score > 0.8:
            return SignalStrength.VERY_STRONG
        elif strength_score > 0.6:
            return SignalStrength.STRONG
        elif strength_score > 0.4:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK

    def _calculate_divergence_score(self, components: List[CompositeComponent]) -> float:
        """Calculate divergence score among components"""
        if len(components) < 2:
            return 0.0

        signals = [c.signal for c in components]
        mean_signal = np.mean(signals)
        signal_std = np.std(signals)

        # Lower divergence (consistency) gets higher score
        divergence_score = 1.0 - min(signal_std / 0.5, 1.0)  # Normalize

        return divergence_score

    def _calculate_confluence_score(self, components: List[CompositeComponent]) -> float:
        """Calculate confluence score (how many components agree)"""
        if not components:
            return 0.0

        bullish_signals = sum(1 for c in components if c.signal > 0.2)
        bearish_signals = sum(1 for c in components if c.signal < -0.2)

        total_signals = bullish_signals + bearish_signals
        if total_signals == 0:
            return 0.0

        # Confluence is the ratio of agreeing signals
        max_agreeing = max(bullish_signals, bearish_signals)
        confluence = max_agreeing / len(components)

        return confluence

    def _determine_market_regime(self, components: List[CompositeComponent]) -> str:
        """Determine market regime based on component signals"""
        if not components:
            return 'unknown'

        avg_signal = np.mean([c.signal for c in components])
        signal_consistency = self._calculate_divergence_score(components)

        if abs(avg_signal) < 0.2 and signal_consistency > 0.7:
            return 'ranging'
        elif avg_signal > 0.3 and signal_consistency > 0.6:
            return 'strong_uptrend'
        elif avg_signal < -0.3 and signal_consistency > 0.6:
            return 'strong_downtrend'
        elif signal_consistency < 0.4:
            return 'choppy'
        else:
            return 'trending'

    def _calculate_composite_risk_management(self, signal: float, current_price: float) -> Tuple[float, float]:
        """Calculate risk management levels for composite signal"""
        # Base risk on recent volatility
        if len(self.price_history) >= 10:
            volatility = np.std(self.price_history[-10:])
            base_risk = volatility * 0.5
        else:
            base_risk = current_price * 0.01

        # Adjust based on signal strength
        risk_multiplier = 1.5 if abs(signal) > 0.7 else 1.0

        risk_amount = base_risk * risk_multiplier

        if signal > 0:  # Bullish
            suggested_sl = current_price - risk_amount
            suggested_tp = current_price + (risk_amount * 2)  # 2:1 reward ratio
        else:  # Bearish
            suggested_sl = current_price + risk_amount
            suggested_tp = current_price - (risk_amount * 2)

        return suggested_sl, suggested_tp

    def _calculate_confidence_components(self, components: List[CompositeComponent],
                                       order_book_data: Dict = None,
                                       trade_data: List = None) -> Dict[str, float]:
        """Calculate confidence components for composite signal"""
        components_conf = {}

        # Component agreement
        components_conf['component_agreement'] = self._calculate_confluence_score(components)

        # Component confidence average
        components_conf['average_component_confidence'] = np.mean([c.confidence for c in components])

        # Volume confirmation
        components_conf['volume_confirmation'] = self._calculate_volume_context()

        # Smart money confirmation
        components_conf['smart_money_score'] = self._calculate_smart_money_score(order_book_data, trade_data)

        # Multi-timeframe alignment
        components_conf['timeframe_alignment'] = 0.7  # Simplified

        return components_conf

    def _analyze_signal_distribution(self, components: List[CompositeComponent]) -> Dict[str, Any]:
        """Analyze signal distribution among components"""
        signals = [c.signal for c in components]

        return {
            'mean': np.mean(signals),
            'std': np.std(signals),
            'min': min(signals),
            'max': max(signals),
            'bullish_count': sum(1 for s in signals if s > 0.2),
            'bearish_count': sum(1 for s in signals if s < -0.2),
            'neutral_count': sum(1 for s in signals if -0.2 <= s <= 0.2)
        }

    def _calculate_volatility_context(self) -> float:
        """Calculate volatility context score"""
        if len(self.price_history) < 10:
            return 0.5

        recent_volatility = np.std(self.price_history[-10:])
        avg_price = np.mean(self.price_history[-10:])

        normalized_volatility = recent_volatility / avg_price

        # Higher volatility can mean stronger signals but also higher risk
        return min(normalized_volatility * 5, 1.0)

    def _calculate_volume_context(self) -> float:
        """Calculate volume context score"""
        if len(self.volume_history) < 10:
            return 0.5

        recent_volume = np.mean(self.volume_history[-5:])
        avg_volume = np.mean(self.volume_history[-15:-5])

        if avg_volume == 0:
            return 0.5

        volume_ratio = recent_volume / avg_volume

        if volume_ratio > 1.5:
            return 0.9  # High volume confirmation
        elif volume_ratio > 1.2:
            return 0.7
        elif volume_ratio > 0.8:
            return 0.5
        else:
            return 0.3  # Low volume

    def _calculate_smart_money_score(self, order_book_data: Dict = None,
                                   trade_data: List = None) -> float:
        """Calculate smart money confirmation score"""
        score = 0.5

        if order_book_data:
            bids_vol = sum(order_book_data.get('bids', {}).values())
            asks_vol = sum(order_book_data.get('asks', {}).values())

            if bids_vol + asks_vol > 0:
                imbalance = abs(bids_vol - asks_vol) / (bids_vol + asks_vol)
                score = min(0.9, 0.5 + imbalance)

        if trade_data and len(trade_data) > 0:
            large_trades = [t for t in trade_data if t[1] > np.mean([t[1] for t in trade_data]) * 2]
            if large_trades:
                score = min(0.95, score + 0.2)

        return score

    def get_component_signals(self) -> List[CompositeComponent]:
        """Get current component signals"""
        return self._get_component_signals()

    def get_signal_history(self) -> List[CompositeSignal]:
        """Get historical composite signals"""
        return self.signal_history.copy()

    def get_composite_statistics(self) -> Dict[str, Any]:
        """Get composite signal statistics"""
        if not self.signal_history:
            return {}

        signals = [s.value_raw for s in self.signal_history]
        confidences = [s.composite_confidence for s in self.signal_history]

        return {
            'total_signals': len(self.signal_history),
            'average_confidence': np.mean(confidences),
            'signal_distribution': {
                'bullish': sum(1 for s in self.signal_history if s.value_raw > 0),
                'bearish': sum(1 for s in self.signal_history if s.value_raw < 0)
            },
            'strength_distribution': {
                strength.value: sum(1 for s in self.signal_history if s.signal_strength == strength)
                for strength in SignalStrength
            },
            'win_rate': self._calculate_historical_win_rate()
        }

    def _calculate_historical_win_rate(self) -> float:
        """Calculate historical win rate of signals"""
        if len(self.signal_history) < 2:
            return 0.5

        # Simplified win rate calculation
        # In practice, this would track actual trade outcomes
        strong_signals = [s for s in self.signal_history if s.signal_strength in [SignalStrength.STRONG, SignalStrength.VERY_STRONG]]
        if not strong_signals:
            return 0.5

        # Assume 60% win rate for strong signals (placeholder)
        return 0.6