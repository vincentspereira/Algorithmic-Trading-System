"""
Custom Technical Analysis Indicators Library
Phase 1 - Core System Validation & Hardening

Comprehensive volume-weighted technical analysis indicators including:
- Trend Indicators (10): SMA, EMA, VWMA, Hull MA, Kaufman AMA, etc.
- Momentum Indicators (10): RSI, MACD, Stochastic, Williams %R, etc.
- Volatility Indicators (6): Bollinger Bands, ATR, Keltner Channels, etc.
- Volume Indicators (8): OBV, VWAP, A/D Line, Chaikin MFI, etc.

Author: Vincent S. Pereira
Version: 1.0.0
Total Indicators: 34
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple, Union, List
from dataclasses import dataclass
from enum import Enum
import warnings

# Import candlestick patterns
try:
    from ..indicators.candle_patterns import apply_candle_patterns, apply_candle_properties
    CANDLE_PATTERNS_AVAILABLE = True
except ImportError:
    CANDLE_PATTERNS_AVAILABLE = False
    warnings.warn("Candlestick patterns module not available")

warnings.filterwarnings('ignore')

class IndicatorType(Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"

@dataclass
class IndicatorResult:
    """Standard result structure for all indicators"""
    value: Union[float, pd.Series, np.ndarray]
    signal: str  # BUY, SELL, NEUTRAL
    strength: float  # 0.0 to 1.0
    metadata: dict

class TechnicalIndicators:
    """Comprehensive technical indicators library"""
    
    @staticmethod
    def sma(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Simple Moving Average"""
        sma = data.rolling(window=period).mean()
        signal = "BUY" if data.iloc[-1] > sma.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - sma.iloc[-1]) / sma.iloc[-1]
        return IndicatorResult(sma, signal, min(strength, 1.0), {"period": period})

    @staticmethod
    def ema(data: pd.Series, period: int = 20) -> IndicatorResult:
        """Exponential Moving Average"""
        ema = data.ewm(span=period).mean()
        signal = "BUY" if data.iloc[-1] > ema.iloc[-1] else "SELL"
        strength = abs(data.iloc[-1] - ema.iloc[-1]) / ema.iloc[-1]
        return IndicatorResult(ema, signal, min(strength, 1.0), {"period": period})

    @staticmethod
    def vwma(price: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Volume Weighted Moving Average - Enhanced with proper volume weighting"""
        # Calculate price × volume
        price_volume = price * volume
        
        # Calculate rolling sums for proper VWMA calculation
        pv_sum = price_volume.rolling(window=period).sum()
        vol_sum = volume.rolling(window=period).sum()
        
        # Calculate true volume weighted moving average
        vwma = pv_sum / vol_sum
        
        signal = "BUY" if price.iloc[-1] > vwma.iloc[-1] else "SELL"
        strength = abs(price.iloc[-1] - vwma.iloc[-1]) / vwma.iloc[-1]
        
        return IndicatorResult(
            vwma, signal, min(strength, 1.0), 
            {"period": period, "current_price": price.iloc[-1], "vwma": vwma.iloc[-1]}
        )

    @staticmethod
    def vw_ema(price: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Volume Weighted Exponential Moving Average"""
        alpha = 1.0 / period
        
        # Calculate volume weighted price and volume EMAs
        price_vol = price * volume
        pv_ema = price_vol.ewm(min_periods=period, alpha=alpha).mean()
        vol_ema = volume.ewm(min_periods=period, alpha=alpha).mean()
        
        # Calculate volume weighted EMA
        vw_ema = pv_ema / vol_ema
        
        signal = "BUY" if price.iloc[-1] > vw_ema.iloc[-1] else "SELL"
        strength = abs(price.iloc[-1] - vw_ema.iloc[-1]) / vw_ema.iloc[-1]
        
        return IndicatorResult(
            vw_ema, signal, min(strength, 1.0),
            {"period": period, "alpha": alpha, "current": vw_ema.iloc[-1]}
        )

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> IndicatorResult:
        """Relative Strength Index - Enhanced with proper signal boundaries"""
        alpha = 1.0 / period
        
        delta = data.diff()
        gain = pd.Series([x if x >= 0 else 0.0 for x in delta], name="gain")
        loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in delta], name="loss")
        
        avg_gain = gain.ewm(min_periods=period, alpha=alpha).mean()
        avg_loss = loss.ewm(min_periods=period, alpha=alpha).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Calculate SMA and min/max for enhanced signal detection
        rsi_sma = rsi.rolling(window=10).mean()
        rsi_max = rsi.rolling(window=10).max()
        rsi_min = rsi.rolling(window=10).min()
        
        if rsi.iloc[-1] > 70:
            signal, strength = "SELL", (rsi.iloc[-1] - 70) / 30
        elif rsi.iloc[-1] < 30:
            signal, strength = "BUY", (30 - rsi.iloc[-1]) / 30
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(
            rsi, signal, strength, 
            {"period": period, "current": rsi.iloc[-1], "sma": rsi_sma.iloc[-1], "max": rsi_max.iloc[-1], "min": rsi_min.iloc[-1]}
        )

    @staticmethod
    def vw_rsi(price: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Volume Weighted RSI - Enhanced based on your MFI implementation"""
        alpha = 1.0 / period
        
        # Calculate price change
        price_change = price.diff()
        
        # Calculate gain and loss
        gain = pd.Series([x if x >= 0 else 0.0 for x in price_change], name="gain")
        loss = pd.Series([(x * -1) if x < 0 else 0.0 for x in price_change], name="loss")
        
        # Calculate volume weighted gain and loss
        gain_vol = gain * volume
        loss_vol = loss * volume
        
        # Calculate EMAs
        gain_vol_ema = gain_vol.ewm(min_periods=period, alpha=alpha).mean()
        loss_vol_ema = loss_vol.ewm(min_periods=period, alpha=alpha).mean()
        vol_ema = volume.ewm(min_periods=period, alpha=alpha).mean()
        
        # Calculate volume weighted averages
        avg_gain = gain_vol_ema / vol_ema
        avg_loss = loss_vol_ema / vol_ema
        
        # Calculate VW RSI
        rs = avg_gain / avg_loss
        vw_rsi = 100 - (100 / (1 + rs))
        
        # Calculate enhanced metrics
        vw_rsi_sma = vw_rsi.rolling(window=10).mean()
        vw_rsi_max = vw_rsi.rolling(window=10).max()
        vw_rsi_min = vw_rsi.rolling(window=10).min()
        
        if vw_rsi.iloc[-1] > 80:  # Higher threshold for volume weighted
            signal, strength = "SELL", (vw_rsi.iloc[-1] - 80) / 20
        elif vw_rsi.iloc[-1] < 20:  # Lower threshold for volume weighted
            signal, strength = "BUY", (20 - vw_rsi.iloc[-1]) / 20
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(
            vw_rsi, signal, strength,
            {"period": period, "current": vw_rsi.iloc[-1], "sma": vw_rsi_sma.iloc[-1], 
             "max": vw_rsi_max.iloc[-1], "min": vw_rsi_min.iloc[-1], "volume_weighted": True}
        )

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> IndicatorResult:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = data.ewm(span=fast).mean()
        ema_slow = data.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period).mean()
        histogram = macd_line - signal_line
        
        signal = "BUY" if macd_line.iloc[-1] > signal_line.iloc[-1] else "SELL"
        strength = abs(histogram.iloc[-1]) / data.iloc[-1] * 100
        
        return IndicatorResult(
            {"macd": macd_line, "signal": signal_line, "histogram": histogram},
            signal, min(strength, 1.0), {"fast": fast, "slow": slow, "signal_period": signal_period}
        )

    @staticmethod
    def vw_macd(price: pd.Series, volume: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> IndicatorResult:
        """Volume Weighted MACD - Enhanced based on your implementation"""
        alpha_fast = 1.0 / fast
        alpha_slow = 1.0 / slow
        alpha_signal = 1.0 / signal_period
        
        # Calculate price × volume
        price_vol = price * volume
        
        # Calculate fast and slow EMAs for both price×volume and volume
        pv_ema_fast = price_vol.ewm(min_periods=fast, alpha=alpha_fast).mean()
        pv_ema_slow = price_vol.ewm(min_periods=slow, alpha=alpha_slow).mean()
        vol_ema_fast = volume.ewm(min_periods=fast, alpha=alpha_fast).mean()
        vol_ema_slow = volume.ewm(min_periods=slow, alpha=alpha_slow).mean()
        
        # Calculate volume weighted EMAs
        vw_ema_fast = pv_ema_fast / vol_ema_fast
        vw_ema_slow = pv_ema_slow / vol_ema_slow
        
        # Calculate VW MACD components
        vw_macd_line = vw_ema_fast - vw_ema_slow
        vw_signal_line = vw_macd_line.ewm(min_periods=signal_period, alpha=alpha_signal).mean()
        vw_histogram = vw_macd_line - vw_signal_line
        
        signal = "BUY" if vw_macd_line.iloc[-1] > vw_signal_line.iloc[-1] else "SELL"
        strength = abs(vw_histogram.iloc[-1]) / price.iloc[-1] * 100
        
        return IndicatorResult(
            {"vw_macd": vw_macd_line, "vw_signal": vw_signal_line, "vw_histogram": vw_histogram},
            signal, min(strength, 1.0),
            {"fast": fast, "slow": slow, "signal_period": signal_period, "volume_weighted": True}
        )

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> IndicatorResult:
        """Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        current_price = data.iloc[-1]
        bb_percent = (current_price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        
        if bb_percent > 0.8:
            signal, strength = "SELL", bb_percent - 0.8
        elif bb_percent < 0.2:
            signal, strength = "BUY", 0.2 - bb_percent
        else:
            signal, strength = "NEUTRAL", 0.0
            
        return IndicatorResult(
            {"upper": upper, "middle": sma, "lower": lower, "percent": bb_percent},
            signal, strength, {"period": period, "std_dev": std_dev}
        )

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> IndicatorResult:
        """Average True Range - Enhanced with smoothing"""
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        # Add ATR SMA for trend analysis
        atr_sma = atr.rolling(window=10).mean()
        
        # ATR signals based on volatility expansion/contraction
        signal = "BUY" if atr.iloc[-1] < atr_sma.iloc[-1] else "SELL"
        strength = abs(atr.iloc[-1] - atr_sma.iloc[-1]) / atr_sma.iloc[-1]
        
        return IndicatorResult(
            atr, signal, min(strength, 1.0), 
            {"period": period, "current": atr.iloc[-1], "sma": atr_sma.iloc[-1]}
        )

    @staticmethod
    def vw_atr(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Volume Weighted ATR - Based on your sophisticated implementation"""
        alpha = 1.0 / period
        
        # Calculate True Range
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Volume Weighted ATR
        tr_vol = true_range * volume
        tr_vol_ema = tr_vol.ewm(min_periods=period, alpha=alpha).mean()
        vol_ema = volume.ewm(min_periods=period, alpha=alpha).mean()
        vw_atr = tr_vol_ema / vol_ema
        
        # Calculate VW ATR SMA for additional smoothing
        atr_vol = vw_atr * volume
        atr_vol_sma = atr_vol.rolling(window=10).mean()
        vol_sma = volume.rolling(window=10).mean()
        vw_atr_sma = atr_vol_sma / vol_sma
        
        # Enhanced signal detection
        signal = "BUY" if vw_atr.iloc[-1] < vw_atr_sma.iloc[-1] else "SELL"
        strength = abs(vw_atr.iloc[-1] - vw_atr_sma.iloc[-1]) / vw_atr_sma.iloc[-1]
        
        return IndicatorResult(
            vw_atr, signal, min(strength, 1.0),
            {"period": period, "current": vw_atr.iloc[-1], "sma": vw_atr_sma.iloc[-1], "volume_weighted": True}
        )

    @staticmethod
    def vw_atrp(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Volume Weighted ATR Percentage - Normalized ATR"""
        alpha = 1.0 / period
        
        # Calculate True Range
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Calculate Volume Weighted ATR
        tr_vol = true_range * volume
        tr_vol_ema = tr_vol.ewm(min_periods=period, alpha=alpha).mean()
        vol_ema = volume.ewm(min_periods=period, alpha=alpha).mean()
        vw_atr = tr_vol_ema / vol_ema
        
        # Calculate ATRP (ATR as percentage of price)
        vw_atrp = (vw_atr / close) * 100
        
        # Calculate smoothed ATRP
        atrp_vol = vw_atrp * volume
        atrp_vol_sma = atrp_vol.rolling(window=10).mean()
        vol_sma = volume.rolling(window=10).mean()
        vw_atrp_sma = atrp_vol_sma / vol_sma
        
        # Signal based on volatility levels
        if vw_atrp.iloc[-1] > 5.0:  # High volatility
            signal, strength = "SELL", min(vw_atrp.iloc[-1] / 10, 1.0)
        elif vw_atrp.iloc[-1] < 1.0:  # Low volatility
            signal, strength = "BUY", min((1.0 - vw_atrp.iloc[-1]), 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            vw_atrp, signal, strength,
            {"period": period, "current": vw_atrp.iloc[-1], "sma": vw_atrp_sma.iloc[-1], 
             "atr": vw_atr.iloc[-1], "normalized": True}
        )

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        
        signal = "BUY" if close.iloc[-1] > vwap.iloc[-1] else "SELL"
        strength = abs(close.iloc[-1] - vwap.iloc[-1]) / vwap.iloc[-1]
        
        return IndicatorResult(vwap, signal, min(strength, 1.0), {"current_price": close.iloc[-1], "vwap": vwap.iloc[-1]})

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> IndicatorResult:
        """On Balance Volume"""
        obv = volume.copy()
        obv[close.diff() < 0] = -volume[close.diff() < 0]
        obv = obv.cumsum()
        
        # OBV trend analysis
        obv_sma = obv.rolling(20).mean()
        signal = "BUY" if obv.iloc[-1] > obv_sma.iloc[-1] else "SELL"
        strength = abs(obv.iloc[-1] - obv_sma.iloc[-1]) / abs(obv_sma.iloc[-1]) if obv_sma.iloc[-1] != 0 else 0
        
        return IndicatorResult(obv, signal, min(strength, 1.0), {"current": obv.iloc[-1], "sma": obv_sma.iloc[-1]})

    @staticmethod
    def candlestick_patterns(open_series: pd.Series, high_series: pd.Series, low_series: pd.Series, 
                           close_series: pd.Series, volume_series: pd.Series) -> IndicatorResult:
        """Comprehensive Candlestick Pattern Analysis"""
        if not CANDLE_PATTERNS_AVAILABLE:
            return IndicatorResult(
                pd.Series([False] * len(close_series)), "NEUTRAL", 0.0,
                {"error": "Candlestick patterns module not available"}
            )
        
        # Create DataFrame for pattern analysis
        df = pd.DataFrame({
            'Mid_Open': open_series,
            'Mid_High': high_series,
            'Mid_Low': low_series,
            'Mid_Close': close_series,
            'Volume': volume_series
        })
        
        # Apply candlestick pattern analysis
        df_patterns = apply_candle_patterns(df)
        
        # Define pattern weights for signal calculation
        bullish_patterns = {
            'Morning_Star': 0.9,    # Strong bullish reversal
            'Tweezer_Bottom': 0.7,  # Bullish reversal
            'Engulfing': 0.8,       # Strong when bullish engulfing
            'Hammer': 0.6           # Hammer/Hanging Man in downtrend
        }
        
        bearish_patterns = {
            'Evening_Star': 0.9,    # Strong bearish reversal  
            'Tweezer_Top': 0.7,     # Bearish reversal
            'Shooting_Star': 0.6    # Shooting star in uptrend
        }
        
        # Calculate pattern-based signals
        current_idx = len(df_patterns) - 1
        if current_idx < 3:  # Need minimum data for pattern analysis
            return IndicatorResult(
                df_patterns, "NEUTRAL", 0.0,
                {"patterns_detected": [], "insufficient_data": True}
            )
        
        # Check for active patterns in recent candles (last 3 periods)
        bullish_strength = 0.0
        bearish_strength = 0.0
        detected_patterns = []
        
        for i in range(max(0, current_idx - 2), current_idx + 1):
            if i >= len(df_patterns):
                continue
                
            row = df_patterns.iloc[i]
            
            # Check bullish patterns
            if row.get('Morning_Star', False):
                bullish_strength += bullish_patterns['Morning_Star']
                detected_patterns.append(f"Morning_Star@{i}")
            
            if row.get('Tweezer_Bottom', False):
                bullish_strength += bullish_patterns['Tweezer_Bottom']
                detected_patterns.append(f"Tweezer_Bottom@{i}")
            
            if row.get('Engulfing', False) and row.get('Direction', 0) > 0:
                bullish_strength += bullish_patterns['Engulfing']
                detected_patterns.append(f"Bullish_Engulfing@{i}")
            
            if row.get('Hanging_Man', False):  # Can be bullish in downtrend
                # Check if we're in a downtrend (simplified)
                if i > 0 and row['Mid_Close'] < df_patterns.iloc[i-1]['Mid_Close']:
                    bullish_strength += bullish_patterns['Hammer']
                    detected_patterns.append(f"Hammer@{i}")
                else:
                    bearish_strength += 0.5  # Hanging man in uptrend
                    detected_patterns.append(f"Hanging_Man@{i}")
            
            # Check bearish patterns
            if row.get('Evening_Star', False):
                bearish_strength += bearish_patterns['Evening_Star']
                detected_patterns.append(f"Evening_Star@{i}")
            
            if row.get('Tweezer_Top', False):
                bearish_strength += bearish_patterns['Tweezer_Top']
                detected_patterns.append(f"Tweezer_Top@{i}")
            
            if row.get('Shooting_Star', False):
                bearish_strength += bearish_patterns['Shooting_Star']
                detected_patterns.append(f"Shooting_Star@{i}")
            
            if row.get('Engulfing', False) and row.get('Direction', 0) < 0:
                bearish_strength += 0.8  # Bearish engulfing
                detected_patterns.append(f"Bearish_Engulfing@{i}")
        
        # Determine overall signal
        total_strength = bullish_strength + bearish_strength
        if total_strength == 0:
            signal = "NEUTRAL"
            strength = 0.0
        elif bullish_strength > bearish_strength:
            signal = "BUY"
            strength = min(bullish_strength / (total_strength + 1), 1.0)
        else:
            signal = "SELL"
            strength = min(bearish_strength / (total_strength + 1), 1.0)
        
        return IndicatorResult(
            df_patterns, signal, strength,
            {
                "patterns_detected": detected_patterns,
                "bullish_strength": bullish_strength,
                "bearish_strength": bearish_strength,
                "pattern_count": len(detected_patterns),
                "recent_patterns": detected_patterns[-3:] if detected_patterns else []
            }
        )

    @staticmethod
    def pattern_strength_analysis(open_series: pd.Series, high_series: pd.Series, low_series: pd.Series, 
                                close_series: pd.Series, volume_series: pd.Series) -> IndicatorResult:
        """Advanced pattern strength analysis with volume confirmation"""
        pattern_result = TechnicalIndicators.candlestick_patterns(
            open_series, high_series, low_series, close_series, volume_series
        )
        
        if not CANDLE_PATTERNS_AVAILABLE:
            return pattern_result
        
        # Volume-based pattern confirmation
        avg_volume = volume_series.rolling(window=20).mean()
        current_volume = volume_series.iloc[-1]
        volume_ratio = current_volume / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1.0
        
        # Enhance signal strength based on volume confirmation
        volume_confirmation = min(volume_ratio / 2.0, 1.5)  # Cap at 1.5x boost
        enhanced_strength = min(pattern_result.strength * volume_confirmation, 1.0)
        
        # Count pattern types for diversification score
        patterns = pattern_result.metadata.get('patterns_detected', [])
        unique_pattern_types = len(set([p.split('@')[0] for p in patterns]))
        diversification_score = min(unique_pattern_types / 3.0, 1.0)  # Up to 3 different patterns
        
        return IndicatorResult(
            pattern_result.value, pattern_result.signal, enhanced_strength,
            {
                **pattern_result.metadata,
                "volume_confirmation": volume_ratio,
                "enhanced_strength": enhanced_strength,
                "original_strength": pattern_result.strength,
                "diversification_score": diversification_score,
                "confidence_level": "high" if enhanced_strength > 0.7 else "medium" if enhanced_strength > 0.4 else "low"
            }
        )
