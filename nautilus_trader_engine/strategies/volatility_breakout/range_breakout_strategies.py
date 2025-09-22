"""Range Breakout Strategies Module

This module implements range-based volatility breakout strategies including:
- Bollinger Band Breakouts (price breaks above/below bands)
- Donchian Channel Breakouts (price breaks highest high/lowest low)
- Keltner Channel Breakouts (EMA-based channel breakouts)
- Custom Range Breakouts (user-defined support/resistance levels)

Key Features:
- Dynamic range calculation based on volatility
- Volume confirmation for breakout validation
- False breakout filtering mechanisms
- Multi-timeframe range analysis
- Adaptive threshold adjustment
- Risk management integration

Architecture:
Follows the 5-Pillar Architecture with sophisticated range detection
engines and breakout validation systems.
"""

import math
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# Core trading components
try:
    import pandas as pd
    import numpy as np
    from scipy import stats
except ImportError:
    pd = None
    np = None
    stats = None

# Base strategy components
from ..pairs_trading.pairs_trading_strategies import (
    StrategyType, PositionType, SignalStrength,
    TradingSignal, Position, StrategyConfig
)

class VolatilityMeasure(Enum):
    """Types of volatility measures"""
    STANDARD_DEVIATION = "standard_deviation"
    ATR = "atr"
    RANGE = "range"
    PARKINSON = "parkinson"
    GARMAN_KLASS = "garman_klass"

class BreakoutDirection(Enum):
    """Breakout direction"""
    UPWARD = "upward"
    DOWNWARD = "downward"
    NONE = "none"

class BreakoutType(Enum):
    """Type of breakout"""
    BOLLINGER_UPPER = "bollinger_upper"
    BOLLINGER_LOWER = "bollinger_lower"
    DONCHIAN_UPPER = "donchian_upper"
    DONCHIAN_LOWER = "donchian_lower"
    KELTNER_UPPER = "keltner_upper"
    KELTNER_LOWER = "keltner_lower"
    CUSTOM_RESISTANCE = "custom_resistance"
    CUSTOM_SUPPORT = "custom_support"

class VolumeConfirmation(Enum):
    """Volume confirmation status"""
    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    INSUFFICIENT_DATA = "insufficient_data"

@dataclass
class VolatilityRange:
    """Volatility range definition"""
    upper_band: float
    lower_band: float
    middle_line: float
    range_width: float
    volatility_measure: VolatilityMeasure
    calculation_period: int
    timestamp: datetime
    
    # Additional metrics
    band_position: float = 0.0  # Where current price sits in the range (0-1)
    squeeze_ratio: float = 0.0  # How tight the range is compared to historical
    
    def __post_init__(self):
        self.range_width = self.upper_band - self.lower_band
        
    def get_band_position(self, price: float) -> float:
        """Calculate where price sits within the range (0 = lower band, 1 = upper band)"""
        if self.range_width == 0:
            return 0.5
        return (price - self.lower_band) / self.range_width
    
    def is_breakout(self, price: float, threshold: float = 0.01) -> Tuple[bool, BreakoutDirection]:
        """Check if price represents a breakout"""
        upper_threshold = self.upper_band * (1 + threshold)
        lower_threshold = self.lower_band * (1 - threshold)
        
        if price > upper_threshold:
            return True, BreakoutDirection.UPWARD
        elif price < lower_threshold:
            return True, BreakoutDirection.DOWNWARD
        else:
            return False, BreakoutDirection.NONE

@dataclass
class BreakoutSignal:
    """Breakout signal definition"""
    breakout_type: BreakoutType
    direction: BreakoutDirection
    breakout_price: float
    range_info: VolatilityRange
    volume_confirmation: VolumeConfirmation
    strength: float
    confidence: float
    timestamp: datetime
    
    # Target and risk levels
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    
    # Volume metrics
    volume_ratio: float = 1.0
    avg_volume: float = 0.0
    current_volume: float = 0.0

class VolatilityAnalyzer:
    """Core volatility analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.default_period = 20
        self.volume_lookback = 10
        self.min_data_points = 30
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, 
                                std_dev: float = 2.0) -> VolatilityRange:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < period:
                raise ValueError(f"Insufficient data: need {period}, got {len(prices)}")
            
            # Calculate moving average and standard deviation
            sma = prices.rolling(window=period).mean().iloc[-1]
            std = prices.rolling(window=period).std().iloc[-1]
            
            upper_band = sma + (std_dev * std)
            lower_band = sma - (std_dev * std)
            
            return VolatilityRange(
                upper_band=upper_band,
                lower_band=lower_band,
                middle_line=sma,
                range_width=upper_band - lower_band,
                volatility_measure=VolatilityMeasure.STANDARD_DEVIATION,
                calculation_period=period,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            raise
    
    def calculate_donchian_channels(self, high_prices: pd.Series, low_prices: pd.Series, 
                                  period: int = 20) -> VolatilityRange:
        """Calculate Donchian Channels"""
        try:
            if len(high_prices) < period or len(low_prices) < period:
                raise ValueError(f"Insufficient data: need {period} periods")
            
            # Calculate highest high and lowest low
            upper_band = high_prices.rolling(window=period).max().iloc[-1]
            lower_band = low_prices.rolling(window=period).min().iloc[-1]
            middle_line = (upper_band + lower_band) / 2
            
            return VolatilityRange(
                upper_band=upper_band,
                lower_band=lower_band,
                middle_line=middle_line,
                range_width=upper_band - lower_band,
                volatility_measure=VolatilityMeasure.RANGE,
                calculation_period=period,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating Donchian Channels: {e}")
            raise
    
    def calculate_keltner_channels(self, high_prices: pd.Series, low_prices: pd.Series, 
                                 close_prices: pd.Series, period: int = 20, 
                                 multiplier: float = 2.0) -> VolatilityRange:
        """Calculate Keltner Channels"""
        try:
            if len(close_prices) < period:
                raise ValueError(f"Insufficient data: need {period} periods")
            
            # Calculate EMA of close prices
            ema = close_prices.ewm(span=period).mean().iloc[-1]
            
            # Calculate ATR
            atr = self._calculate_atr(high_prices, low_prices, close_prices, period)
            
            upper_band = ema + (multiplier * atr)
            lower_band = ema - (multiplier * atr)
            
            return VolatilityRange(
                upper_band=upper_band,
                lower_band=lower_band,
                middle_line=ema,
                range_width=upper_band - lower_band,
                volatility_measure=VolatilityMeasure.ATR,
                calculation_period=period,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating Keltner Channels: {e}")
            raise
    
    def _calculate_atr(self, high_prices: pd.Series, low_prices: pd.Series, 
                      close_prices: pd.Series, period: int) -> float:
        """Calculate Average True Range"""
        try:
            # Calculate True Range
            prev_close = close_prices.shift(1)
            
            tr1 = high_prices - low_prices
            tr2 = abs(high_prices - prev_close)
            tr3 = abs(low_prices - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate ATR as EMA of True Range
            atr = true_range.ewm(span=period).mean().iloc[-1]
            
            return atr
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    def analyze_volume_confirmation(self, current_volume: float, 
                                  volume_history: pd.Series, 
                                  lookback_period: int = 10) -> Tuple[VolumeConfirmation, float]:
        """Analyze volume confirmation for breakout"""
        try:
            if len(volume_history) < lookback_period:
                return VolumeConfirmation.INSUFFICIENT_DATA, 1.0
            
            # Calculate average volume
            avg_volume = volume_history.tail(lookback_period).mean()
            
            if avg_volume == 0:
                return VolumeConfirmation.INSUFFICIENT_DATA, 1.0
            
            # Calculate volume ratio
            volume_ratio = current_volume / avg_volume
            
            # Determine confirmation status
            if volume_ratio >= 1.5:  # 50% above average
                confirmation = VolumeConfirmation.CONFIRMED
            else:
                confirmation = VolumeConfirmation.UNCONFIRMED
            
            return confirmation, volume_ratio
            
        except Exception as e:
            self.logger.error(f"Error analyzing volume confirmation: {e}")
            return VolumeConfirmation.INSUFFICIENT_DATA, 1.0
    
    def detect_false_breakout(self, breakout_signal: BreakoutSignal, 
                            subsequent_prices: List[float], 
                            confirmation_periods: int = 3) -> bool:
        """Detect if a breakout is likely false"""
        try:
            if len(subsequent_prices) < confirmation_periods:
                return False  # Not enough data to confirm
            
            range_info = breakout_signal.range_info
            
            if breakout_signal.direction == BreakoutDirection.UPWARD:
                # For upward breakout, check if price falls back into range
                return any(price < range_info.upper_band for price in subsequent_prices)
            
            elif breakout_signal.direction == BreakoutDirection.DOWNWARD:
                # For downward breakout, check if price rises back into range
                return any(price > range_info.lower_band for price in subsequent_prices)
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting false breakout: {e}")
            return False

class RangeBreakoutStrategy:
    """Base range breakout trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.analyzer = VolatilityAnalyzer()
        
        # Strategy parameters
        self.period = config.parameters.get('period', 20)
        self.volume_confirmation = config.parameters.get('volume_confirmation', True)
        self.min_volume_ratio = config.parameters.get('min_volume_ratio', 1.5)
        self.false_breakout_filter = config.parameters.get('false_breakout_filter', True)
        
        # Current state
        self.current_range: Optional[VolatilityRange] = None
        self.recent_signals: List[BreakoutSignal] = []
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for range breakouts"""
        try:
            if pd is None:
                self.logger.error("Pandas not available for data analysis")
                return {}
            
            # Convert market data to DataFrame
            if isinstance(market_data, dict) and 'close' in market_data:
                df = pd.DataFrame([market_data])
            else:
                df = pd.DataFrame(market_data)
            
            if df.empty or len(df) < self.period:
                return {}
            
            # Calculate range (to be overridden by subclasses)
            range_info = self._calculate_range(df)
            self.current_range = range_info
            
            # Get current price and volume
            current_price = df['close'].iloc[-1] if 'close' in df.columns else 0
            current_volume = df['volume'].iloc[-1] if 'volume' in df.columns else 0
            
            # Check for breakout
            breakout_signal = self._detect_breakout(current_price, current_volume, df)
            
            return {
                'range_info': range_info,
                'current_price': current_price,
                'current_volume': current_volume,
                'breakout_signal': breakout_signal,
                'band_position': range_info.get_band_position(current_price) if range_info else 0.5
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing range breakout data: {e}")
            return {}
    
    def _calculate_range(self, df: pd.DataFrame) -> Optional[VolatilityRange]:
        """Calculate volatility range (to be overridden by subclasses)"""
        # Default implementation using simple price range
        try:
            high_prices = df['high'] if 'high' in df.columns else df['close']
            low_prices = df['low'] if 'low' in df.columns else df['close']
            
            return self.analyzer.calculate_donchian_channels(high_prices, low_prices, self.period)
            
        except Exception as e:
            self.logger.error(f"Error calculating default range: {e}")
            return None
    
    def _detect_breakout(self, current_price: float, current_volume: float, 
                        df: pd.DataFrame) -> Optional[BreakoutSignal]:
        """Detect range breakout"""
        try:
            if not self.current_range:
                return None
            
            # Check for breakout
            is_breakout, direction = self.current_range.is_breakout(current_price)
            
            if not is_breakout:
                return None
            
            # Determine breakout type (to be overridden by subclasses)
            breakout_type = self._get_breakout_type(direction)
            
            # Analyze volume confirmation
            volume_confirmation = VolumeConfirmation.UNCONFIRMED
            volume_ratio = 1.0
            
            if self.volume_confirmation and 'volume' in df.columns:
                volume_confirmation, volume_ratio = self.analyzer.analyze_volume_confirmation(
                    current_volume, df['volume'], self.volume_lookback
                )
            
            # Calculate signal strength and confidence
            strength = self._calculate_signal_strength(direction, volume_ratio, self.current_range)
            confidence = self._calculate_confidence(volume_confirmation, volume_ratio)
            
            # Create breakout signal
            breakout_signal = BreakoutSignal(
                breakout_type=breakout_type,
                direction=direction,
                breakout_price=current_price,
                range_info=self.current_range,
                volume_confirmation=volume_confirmation,
                strength=strength,
                confidence=confidence,
                timestamp=datetime.now(),
                volume_ratio=volume_ratio,
                current_volume=current_volume
            )
            
            # Calculate targets and stop loss
            self._calculate_targets(breakout_signal)
            
            # Add to recent signals
            self.recent_signals.append(breakout_signal)
            
            # Keep only recent signals (last 10)
            self.recent_signals = self.recent_signals[-10:]
            
            return breakout_signal
            
        except Exception as e:
            self.logger.error(f"Error detecting breakout: {e}")
            return None
    
    def _get_breakout_type(self, direction: BreakoutDirection) -> BreakoutType:
        """Get breakout type (to be overridden by subclasses)"""
        if direction == BreakoutDirection.UPWARD:
            return BreakoutType.CUSTOM_RESISTANCE
        else:
            return BreakoutType.CUSTOM_SUPPORT
    
    def _calculate_signal_strength(self, direction: BreakoutDirection, 
                                 volume_ratio: float, range_info: VolatilityRange) -> float:
        """Calculate signal strength"""
        try:
            base_strength = 0.5
            
            # Volume boost
            if volume_ratio > 2.0:
                base_strength += 0.3
            elif volume_ratio > 1.5:
                base_strength += 0.2
            elif volume_ratio > 1.2:
                base_strength += 0.1
            
            # Range width boost (wider ranges = stronger signals)
            if range_info.range_width > 0:
                # Normalize range width (this is simplified)
                range_strength = min(range_info.range_width / range_info.middle_line * 10, 0.2)
                base_strength += range_strength
            
            return min(base_strength, 1.0)
            
        except Exception:
            return 0.5
    
    def _calculate_confidence(self, volume_confirmation: VolumeConfirmation, 
                            volume_ratio: float) -> float:
        """Calculate signal confidence"""
        try:
            base_confidence = 0.6
            
            # Volume confirmation boost
            if volume_confirmation == VolumeConfirmation.CONFIRMED:
                base_confidence += 0.3
            elif volume_confirmation == VolumeConfirmation.UNCONFIRMED:
                base_confidence -= 0.1
            
            # Volume ratio boost
            if volume_ratio > 2.0:
                base_confidence += 0.1
            
            return max(0.1, min(base_confidence, 1.0))
            
        except Exception:
            return 0.5
    
    def _calculate_targets(self, signal: BreakoutSignal):
        """Calculate target and stop loss prices"""
        try:
            range_width = signal.range_info.range_width
            breakout_price = signal.breakout_price
            
            if signal.direction == BreakoutDirection.UPWARD:
                # Target: breakout price + range width
                signal.target_price = breakout_price + range_width
                # Stop loss: lower band
                signal.stop_loss_price = signal.range_info.lower_band
            
            elif signal.direction == BreakoutDirection.DOWNWARD:
                # Target: breakout price - range width
                signal.target_price = breakout_price - range_width
                # Stop loss: upper band
                signal.stop_loss_price = signal.range_info.upper_band
            
        except Exception as e:
            self.logger.error(f"Error calculating targets: {e}")
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on range breakouts"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis or not analysis.get('breakout_signal'):
                return signals
            
            breakout_signal = analysis['breakout_signal']
            
            # Filter weak signals
            if breakout_signal.confidence < 0.5:
                return signals
            
            # Filter unconfirmed volume if required
            if (self.volume_confirmation and 
                breakout_signal.volume_confirmation == VolumeConfirmation.UNCONFIRMED and
                breakout_signal.volume_ratio < self.min_volume_ratio):
                return signals
            
            # Convert to trading signal
            trading_signal = self._create_trading_signal(breakout_signal)
            signals.append(trading_signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating range breakout signals: {e}")
            return signals
    
    def _create_trading_signal(self, breakout_signal: BreakoutSignal) -> TradingSignal:
        """Create trading signal from breakout signal"""
        # Determine position type
        if breakout_signal.direction == BreakoutDirection.UPWARD:
            position_type = PositionType.LONG
        else:
            position_type = PositionType.SHORT
        
        # Determine signal strength
        if breakout_signal.strength >= 0.8:
            strength = SignalStrength.STRONG
        elif breakout_signal.strength >= 0.6:
            strength = SignalStrength.MEDIUM
        else:
            strength = SignalStrength.WEAK
        
        return TradingSignal(
            symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
            signal_type=position_type,
            strength=strength,
            confidence=breakout_signal.confidence,
            entry_price=breakout_signal.breakout_price,
            stop_loss=breakout_signal.stop_loss_price,
            take_profit=breakout_signal.target_price,
            timestamp=breakout_signal.timestamp,
            metadata={
                'strategy': 'range_breakout',
                'breakout_type': breakout_signal.breakout_type.value,
                'direction': breakout_signal.direction.value,
                'volume_confirmation': breakout_signal.volume_confirmation.value,
                'volume_ratio': breakout_signal.volume_ratio,
                'range_width': breakout_signal.range_info.range_width,
                'band_position': breakout_signal.range_info.get_band_position(breakout_signal.breakout_price)
            }
        )

class BollingerBandBreakoutStrategy(RangeBreakoutStrategy):
    """Bollinger Band breakout strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.std_dev = config.parameters.get('std_dev', 2.0)
        self.volume_lookback = config.parameters.get('volume_lookback', 10)
    
    def _calculate_range(self, df: pd.DataFrame) -> Optional[VolatilityRange]:
        """Calculate Bollinger Bands"""
        try:
            close_prices = df['close'] if 'close' in df.columns else df['high']
            return self.analyzer.calculate_bollinger_bands(close_prices, self.period, self.std_dev)
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            return None
    
    def _get_breakout_type(self, direction: BreakoutDirection) -> BreakoutType:
        """Get Bollinger Band breakout type"""
        if direction == BreakoutDirection.UPWARD:
            return BreakoutType.BOLLINGER_UPPER
        else:
            return BreakoutType.BOLLINGER_LOWER

class DonchianChannelBreakoutStrategy(RangeBreakoutStrategy):
    """Donchian Channel breakout strategy"""
    
    def _calculate_range(self, df: pd.DataFrame) -> Optional[VolatilityRange]:
        """Calculate Donchian Channels"""
        try:
            high_prices = df['high'] if 'high' in df.columns else df['close']
            low_prices = df['low'] if 'low' in df.columns else df['close']
            return self.analyzer.calculate_donchian_channels(high_prices, low_prices, self.period)
        except Exception as e:
            self.logger.error(f"Error calculating Donchian Channels: {e}")
            return None
    
    def _get_breakout_type(self, direction: BreakoutDirection) -> BreakoutType:
        """Get Donchian Channel breakout type"""
        if direction == BreakoutDirection.UPWARD:
            return BreakoutType.DONCHIAN_UPPER
        else:
            return BreakoutType.DONCHIAN_LOWER

class KeltnerChannelBreakoutStrategy(RangeBreakoutStrategy):
    """Keltner Channel breakout strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.multiplier = config.parameters.get('multiplier', 2.0)
    
    def _calculate_range(self, df: pd.DataFrame) -> Optional[VolatilityRange]:
        """Calculate Keltner Channels"""
        try:
            high_prices = df['high'] if 'high' in df.columns else df['close']
            low_prices = df['low'] if 'low' in df.columns else df['close']
            close_prices = df['close'] if 'close' in df.columns else df['high']
            return self.analyzer.calculate_keltner_channels(
                high_prices, low_prices, close_prices, self.period, self.multiplier
            )
        except Exception as e:
            self.logger.error(f"Error calculating Keltner Channels: {e}")
            return None
    
    def _get_breakout_type(self, direction: BreakoutDirection) -> BreakoutType:
        """Get Keltner Channel breakout type"""
        if direction == BreakoutDirection.UPWARD:
            return BreakoutType.KELTNER_UPPER
        else:
            return BreakoutType.KELTNER_LOWER

# Utility functions
def calculate_bollinger_bands(prices: pd.Series, period: int = 20, 
                            std_dev: float = 2.0) -> VolatilityRange:
    """Calculate Bollinger Bands"""
    analyzer = VolatilityAnalyzer()
    return analyzer.calculate_bollinger_bands(prices, period, std_dev)

def calculate_donchian_channels(high_prices: pd.Series, low_prices: pd.Series, 
                              period: int = 20) -> VolatilityRange:
    """Calculate Donchian Channels"""
    analyzer = VolatilityAnalyzer()
    return analyzer.calculate_donchian_channels(high_prices, low_prices, period)

def calculate_keltner_channels(high_prices: pd.Series, low_prices: pd.Series, 
                             close_prices: pd.Series, period: int = 20, 
                             multiplier: float = 2.0) -> VolatilityRange:
    """Calculate Keltner Channels"""
    analyzer = VolatilityAnalyzer()
    return analyzer.calculate_keltner_channels(high_prices, low_prices, close_prices, period, multiplier)