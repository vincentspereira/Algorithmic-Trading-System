"""Signal Generation Pillar

Advanced multi-timeframe signal generation with technical analysis,
candlestick pattern recognition, and volume confirmation.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators


logger = logging.getLogger(__name__)

class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_WEAK = 0.2
    WEAK = 0.4
    MODERATE = 0.6
    STRONG = 0.8
    VERY_STRONG = 1.0

class SignalType(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"

class TimeFrame(Enum):
    """Supported timeframes"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

@dataclass
class MultiTimeframeSignal:
    """Multi-timeframe signal with confirmation"""
    symbol: str
    primary_timeframe: TimeFrame
    primary_signal: SignalType
    primary_strength: float
    confirmation_signals: Dict[TimeFrame, Tuple[SignalType, float]] = field(default_factory=dict)
    volume_confirmation: bool = False
    pattern_confirmation: Optional[str] = None
    indicators: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_consensus_signal(self) -> Tuple[SignalType, float]:
        """Calculate consensus signal across timeframes"""
        all_signals = [(self.primary_signal, self.primary_strength * 2)]  # Weight primary more
        all_signals.extend([(sig, strength) for sig, strength in self.confirmation_signals.values()])
        
        # Calculate weighted average
        buy_weight = sum(strength for sig, strength in all_signals if sig in [SignalType.BUY, SignalType.STRONG_BUY])
        sell_weight = sum(strength for sig, strength in all_signals if sig in [SignalType.SELL, SignalType.STRONG_SELL])
        
        total_weight = buy_weight + sell_weight
        if total_weight == 0:
            return SignalType.HOLD, 0.0
            
        if buy_weight > sell_weight:
            strength = buy_weight / total_weight
            signal = SignalType.STRONG_BUY if strength > 0.8 else SignalType.BUY
        else:
            strength = sell_weight / total_weight
            signal = SignalType.STRONG_SELL if strength > 0.8 else SignalType.SELL
            
        return signal, strength

class TechnicalIndicators:
    """Enhanced technical indicators with volume weighting"""
    
    @staticmethod
    def volume_weighted_sma(price: pd.Series, volume: pd.Series, period: int) -> pd.Series:
        """Volume-weighted Simple Moving Average"""
        return (price * volume).rolling(period).sum() / volume.rolling(period).sum()
    
    @staticmethod
    def volume_weighted_ema(price: pd.Series, volume: pd.Series, period: int) -> pd.Series:
        """Volume-weighted Exponential Moving Average"""
        alpha = 2.0 / (period + 1)
        vw_price = price * volume
        return vw_price.ewm(alpha=alpha).mean() / volume.ewm(alpha=alpha).mean()
    
    @staticmethod
    def enhanced_rsi(price: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
        """Volume-weighted RSI with proper gain/loss calculation"""
        delta = price.diff()
        vw_delta = delta * volume
        
        gain = vw_delta.where(vw_delta > 0, 0).rolling(period).mean()
        loss = (-vw_delta.where(vw_delta < 0, 0)).rolling(period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def enhanced_macd(price: pd.Series, volume: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Volume-weighted MACD"""
        ema_fast = TechnicalIndicators.volume_weighted_ema(price, volume, fast)
        ema_slow = TechnicalIndicators.volume_weighted_ema(price, volume, slow)
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands_with_volume(price: pd.Series, volume: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Volume-weighted Bollinger Bands"""
        vw_sma = TechnicalIndicators.volume_weighted_sma(price, volume, period)
        std = price.rolling(period).std()
        upper_band = vw_sma + (std * std_dev)
        lower_band = vw_sma - (std * std_dev)
        return upper_band, vw_sma, lower_band
    
    @staticmethod
    def money_flow_index(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
        """Money Flow Index"""
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(period).sum()
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(period).sum()
        
        money_ratio = positive_flow / negative_flow
        return 100 - (100 / (1 + money_ratio))

class CandlestickPatterns:
    """Candlestick pattern recognition with volume confirmation"""
    
    @staticmethod
    def is_hammer(open_price: float, high: float, low: float, close: float, volume: float, avg_volume: float) -> Tuple[bool, float]:
        """Detect hammer pattern with volume confirmation"""
        body = abs(close - open_price)
        upper_shadow = high - max(open_price, close)
        lower_shadow = min(open_price, close) - low
        
        # Hammer criteria
        is_hammer = (
            lower_shadow >= 2 * body and
            upper_shadow <= 0.1 * body and
            body > 0
        )
        
        # Volume confirmation
        volume_confirmed = volume > 1.2 * avg_volume
        confidence = 0.7 if is_hammer else 0.0
        if volume_confirmed:
            confidence += 0.2
            
        return is_hammer, confidence
    
    @staticmethod
    def is_engulfing(prev_open: float, prev_close: float, curr_open: float, curr_close: float, volume: float, avg_volume: float) -> Tuple[bool, str, float]:
        """Detect bullish/bearish engulfing pattern"""
        prev_body = abs(prev_close - prev_open)
        curr_body = abs(curr_close - curr_open)
        
        # Bullish engulfing
        bullish_engulfing = (
            prev_close < prev_open and  # Previous candle bearish
            curr_close > curr_open and  # Current candle bullish
            curr_open < prev_close and  # Current opens below previous close
            curr_close > prev_open and  # Current closes above previous open
            curr_body > prev_body       # Current body larger
        )
        
        # Bearish engulfing
        bearish_engulfing = (
            prev_close > prev_open and  # Previous candle bullish
            curr_close < curr_open and  # Current candle bearish
            curr_open > prev_close and  # Current opens above previous close
            curr_close < prev_open and  # Current closes below previous open
            curr_body > prev_body       # Current body larger
        )
        
        volume_confirmed = volume > 1.3 * avg_volume
        confidence = 0.0
        pattern_type = "none"
        
        if bullish_engulfing:
            pattern_type = "bullish_engulfing"
            confidence = 0.8 if volume_confirmed else 0.6
        elif bearish_engulfing:
            pattern_type = "bearish_engulfing"
            confidence = 0.8 if volume_confirmed else 0.6
            
        return bullish_engulfing or bearish_engulfing, pattern_type, confidence

class SignalGenerator:
    """Advanced signal generation with multi-timeframe analysis"""
    
    def __init__(self, primary_timeframe: TimeFrame = TimeFrame.H1, confirmation_timeframes: List[TimeFrame] = None):
        self.primary_timeframe = primary_timeframe
        self.confirmation_timeframes = confirmation_timeframes or [TimeFrame.H4, TimeFrame.D1]
        self.indicators = TechnicalIndicators()
        self.patterns = CandlestickPatterns()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    async def generate_signal(self, symbol: str, data: Dict[TimeFrame, pd.DataFrame]) -> MultiTimeframeSignal:
        """Generate multi-timeframe signal with confirmation"""
        try:
            # Generate primary signal
            primary_data = data[self.primary_timeframe]
            primary_signal, primary_strength = await self._analyze_timeframe(primary_data)
            
            # Generate confirmation signals
            confirmation_tasks = []
            for tf in self.confirmation_timeframes:
                if tf in data:
                    task = asyncio.create_task(self._analyze_timeframe_async(data[tf]))
                    confirmation_tasks.append((tf, task))
            
            confirmation_signals = {}
            for tf, task in confirmation_tasks:
                try:
                    signal, strength = await task
                    confirmation_signals[tf] = (signal, strength)
                except Exception as e:
                    logger.warning(f"Failed to analyze {tf} for {symbol}: {e}")
            
            # Volume and pattern analysis
            volume_confirmed = self._check_volume_confirmation(primary_data)
            pattern = self._detect_patterns(primary_data)
            
            # Calculate indicators
            indicators = self._calculate_indicators(primary_data)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(
                primary_strength, confirmation_signals, volume_confirmed, pattern
            )
            
            return MultiTimeframeSignal(
                symbol=symbol,
                primary_timeframe=self.primary_timeframe,
                primary_signal=primary_signal,
                primary_strength=primary_strength,
                confirmation_signals=confirmation_signals,
                volume_confirmation=volume_confirmed,
                pattern_confirmation=pattern,
                indicators=indicators,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            return MultiTimeframeSignal(
                symbol=symbol,
                primary_timeframe=self.primary_timeframe,
                primary_signal=SignalType.HOLD,
                primary_strength=0.0
            )
    
    async def _analyze_timeframe(self, data: pd.DataFrame) -> Tuple[SignalType, float]:
        """Analyze single timeframe data"""
        if len(data) < 50:
            return SignalType.HOLD, 0.0
            
        # Calculate indicators
        close = data['close']
        volume = data['volume']
        high = data['high']
        low = data['low']
        
        # RSI analysis
        rsi = self.indicators.enhanced_rsi(close, volume, 14)
        current_rsi = rsi.iloc[-1]
        
        # MACD analysis
        macd_line, signal_line, histogram = self.indicators.enhanced_macd(close, volume)
        macd_signal = "bullish" if histogram.iloc[-1] > 0 and histogram.iloc[-2] <= 0 else "bearish" if histogram.iloc[-1] < 0 and histogram.iloc[-2] >= 0 else "neutral"
        
        # Bollinger Bands analysis
        upper_bb, middle_bb, lower_bb = self.indicators.bollinger_bands_with_volume(close, volume)
        bb_position = (close.iloc[-1] - lower_bb.iloc[-1]) / (upper_bb.iloc[-1] - lower_bb.iloc[-1])
        
        # Money Flow Index
        mfi = self.indicators.money_flow_index(high, low, close, volume)
        current_mfi = mfi.iloc[-1]
        
        # Signal logic
        buy_signals = 0
        sell_signals = 0
        signal_strength = 0.0
        
        # RSI signals
        if current_rsi < 30:
            buy_signals += 1
            signal_strength += 0.2
        elif current_rsi > 70:
            sell_signals += 1
            signal_strength += 0.2
            
        # MACD signals
        if macd_signal == "bullish":
            buy_signals += 1
            signal_strength += 0.25
        elif macd_signal == "bearish":
            sell_signals += 1
            signal_strength += 0.25
            
        # Bollinger Bands signals
        if bb_position < 0.2:
            buy_signals += 1
            signal_strength += 0.2
        elif bb_position > 0.8:
            sell_signals += 1
            signal_strength += 0.2
            
        # MFI signals
        if current_mfi < 20:
            buy_signals += 1
            signal_strength += 0.15
        elif current_mfi > 80:
            sell_signals += 1
            signal_strength += 0.15
            
        # Determine final signal
        if buy_signals > sell_signals:
            signal_type = SignalType.STRONG_BUY if signal_strength > 0.6 else SignalType.BUY
        elif sell_signals > buy_signals:
            signal_type = SignalType.STRONG_SELL if signal_strength > 0.6 else SignalType.SELL
        else:
            signal_type = SignalType.HOLD
            signal_strength = 0.0
            
        return signal_type, min(signal_strength, 1.0)
    
    async def _analyze_timeframe_async(self, data: pd.DataFrame) -> Tuple[SignalType, float]:
        """Async wrapper for timeframe analysis"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, lambda: asyncio.run(self._analyze_timeframe(data)))
    
    def _check_volume_confirmation(self, data: pd.DataFrame) -> bool:
        """Check if current volume confirms the signal"""
        if len(data) < 20:
            return False
            
        current_volume = data['volume'].iloc[-1]
        avg_volume = data['volume'].rolling(20).mean().iloc[-1]
        
        return current_volume > 1.2 * avg_volume
    
    def _detect_patterns(self, data: pd.DataFrame) -> Optional[str]:
        """Detect candlestick patterns"""
        if len(data) < 2:
            return None
            
        current = data.iloc[-1]
        previous = data.iloc[-2]
        avg_volume = data['volume'].rolling(20).mean().iloc[-1]
        
        # Check for hammer
        is_hammer, hammer_confidence = self.patterns.is_hammer(
            current['open'], current['high'], current['low'], current['close'],
            current['volume'], avg_volume
        )
        
        if is_hammer and hammer_confidence > 0.7:
            return "hammer"
            
        # Check for engulfing
        is_engulfing, pattern_type, engulfing_confidence = self.patterns.is_engulfing(
            previous['open'], previous['close'], current['open'], current['close'],
            current['volume'], avg_volume
        )
        
        if is_engulfing and engulfing_confidence > 0.7:
            return pattern_type
            
        return None
    
    def _calculate_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate current indicator values"""
        if len(data) < 50:
            return {}
            
        close = data['close']
        volume = data['volume']
        high = data['high']
        low = data['low']
        
        indicators = {}
        
        try:
            # RSI
            rsi = self.indicators.enhanced_rsi(close, volume, 14)
            indicators['rsi'] = rsi.iloc[-1]
            
            # MACD
            macd_line, signal_line, histogram = self.indicators.enhanced_macd(close, volume)
            indicators['macd'] = macd_line.iloc[-1]
            indicators['macd_signal'] = signal_line.iloc[-1]
            indicators['macd_histogram'] = histogram.iloc[-1]
            
            # Bollinger Bands
            upper_bb, middle_bb, lower_bb = self.indicators.bollinger_bands_with_volume(close, volume)
            indicators['bb_upper'] = upper_bb.iloc[-1]
            indicators['bb_middle'] = middle_bb.iloc[-1]
            indicators['bb_lower'] = lower_bb.iloc[-1]
            
            # MFI
            mfi = self.indicators.money_flow_index(high, low, close, volume)
            indicators['mfi'] = mfi.iloc[-1]
            
        except Exception as e:
            logger.warning(f"Error calculating indicators: {e}")
            
        return indicators
    
    def _calculate_confidence(self, primary_strength: float, confirmation_signals: Dict[TimeFrame, Tuple[SignalType, float]], 
                            volume_confirmed: bool, pattern: Optional[str]) -> float:
        """Calculate overall signal confidence"""
        confidence = primary_strength * 0.4  # Base confidence from primary timeframe
        
        # Add confirmation from other timeframes
        if confirmation_signals:
            confirmation_weight = 0.3 / len(confirmation_signals)
            for signal_type, strength in confirmation_signals.values():
                if signal_type != SignalType.HOLD:
                    confidence += strength * confirmation_weight
        
        # Volume confirmation bonus
        if volume_confirmed:
            confidence += 0.15
            
        # Pattern confirmation bonus
        if pattern:
            confidence += 0.15
            
        return min(confidence, 1.0)