"""
Comprehensive Technical Indicators Library
Complete Suite of 80+ Technical Indicators + 25+ Candlestick Patterns

This unified library combines:
- Traditional Indicators (40+): Classic technical analysis indicators
- Volume-Weighted Indicators (30+): Enhanced with sophisticated volume weighting
- Advanced Oscillators (10+): Complex momentum and volatility indicators
- Candlestick Patterns (25+): Complete pattern recognition system

Categories:
1. Trend Indicators (25): Moving Averages, Ichimoku, PSAR, Linear Regression, etc.
2. Momentum Oscillators (20): RSI, Stochastic, MACD, CCI, Fisher Transform, etc.
3. Volatility Indicators (15): Bollinger Bands, ATR, Keltner, ADX, Historical Vol, etc.
4. Volume Indicators (20): VWAP, OBV, MFI, CMF, A/D Line, etc.
5. Candlestick Patterns (25+): Complete pattern recognition suite

Author: Vincent S. Pereira
Version: 3.0.0
Total Indicators: 80+
Total Patterns: 25+
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import warnings

# Import our enhanced components
from .enhanced_indicators_part1 import EnhancedTechnicalIndicators, IndicatorResult
from .enhanced_indicators_part2 import EnhancedVolatilityVolumeIndicators
from .enhanced_candlestick_patterns import EnhancedCandlestickPatterns, PatternResult
from .technical_indicators import TechnicalIndicators

warnings.filterwarnings('ignore')

class IndicatorCategory(Enum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    PATTERNS = "patterns"
    SUPPORT_RESISTANCE = "support_resistance"

@dataclass
class ComprehensiveIndicatorResult:
    """Enhanced result structure for comprehensive indicators"""
    indicator_name: str
    category: IndicatorCategory
    value: Union[float, pd.Series, np.ndarray, dict]
    signal: str  # BUY, SELL, NEUTRAL, STRONG_BUY, STRONG_SELL
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    volume_weighted: bool
    metadata: dict

class ComprehensiveIndicators:
    """Unified comprehensive indicators library with 80+ indicators"""
    
    def __init__(self):
        self.traditional_indicators = TechnicalIndicators()
        self.enhanced_indicators = EnhancedTechnicalIndicators()
        self.volatility_volume_indicators = EnhancedVolatilityVolumeIndicators()
        self.pattern_detector = EnhancedCandlestickPatterns()
    
    # ===========================================
    # VOLUME-WEIGHTED IMPLEMENTATIONS
    # ===========================================
    
    @staticmethod
    def vw_sma(price: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Volume Weighted Simple Moving Average"""
        price_volume = price * volume
        pv_sum = price_volume.rolling(window=period).sum()
        vol_sum = volume.rolling(window=period).sum()
        vw_sma = pv_sum / vol_sum
        
        signal = "BUY" if price.iloc[-1] > vw_sma.iloc[-1] else "SELL"
        strength = abs(price.iloc[-1] - vw_sma.iloc[-1]) / vw_sma.iloc[-1]
        
        return IndicatorResult(vw_sma, signal, min(strength, 1.0), 0.8, 
                             {"period": period, "volume_weighted": True})
    
    @staticmethod
    def vw_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
                     k_period: int = 14, d_period: int = 3) -> IndicatorResult:
        """Volume Weighted Stochastic Oscillator"""
        # Calculate volume-weighted price levels
        vw_high = (high * volume).rolling(k_period).sum() / volume.rolling(k_period).sum()
        vw_low = (low * volume).rolling(k_period).sum() / volume.rolling(k_period).sum()
        vw_close = (close * volume).rolling(k_period).sum() / volume.rolling(k_period).sum()
        
        # Calculate volume-weighted stochastic
        lowest_low = vw_low.rolling(k_period).min()
        highest_high = vw_high.rolling(k_period).max()
        
        vw_k = 100 * (vw_close - lowest_low) / (highest_high - lowest_low)
        vw_d = vw_k.rolling(d_period).mean()
        
        if vw_k.iloc[-1] < 20:
            signal, strength = "STRONG_BUY", 0.9
        elif vw_k.iloc[-1] < 30:
            signal, strength = "BUY", 0.7
        elif vw_k.iloc[-1] > 80:
            signal, strength = "STRONG_SELL", 0.9
        elif vw_k.iloc[-1] > 70:
            signal, strength = "SELL", 0.7
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"vw_k": vw_k, "vw_d": vw_d}, signal, strength, 0.85,
            {"k_period": k_period, "d_period": d_period, "volume_weighted": True}
        )
    
    @staticmethod
    def vw_bollinger_bands(price: pd.Series, volume: pd.Series, period: int = 20, std_dev: float = 2.0) -> IndicatorResult:
        """Volume Weighted Bollinger Bands"""
        # Calculate volume weighted moving average
        price_volume = price * volume
        pv_sum = price_volume.rolling(window=period).sum()
        vol_sum = volume.rolling(window=period).sum()
        vw_ma = pv_sum / vol_sum
        
        # Calculate volume weighted standard deviation
        vw_variance = ((price - vw_ma) ** 2 * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_std = np.sqrt(vw_variance)
        
        upper = vw_ma + (vw_std * std_dev)
        lower = vw_ma - (vw_std * std_dev)
        
        # %B calculation
        bb_percent = (price - lower) / (upper - lower)
        bandwidth = (upper - lower) / vw_ma
        
        if bb_percent.iloc[-1] > 1.0:
            signal, strength = "SELL", min((bb_percent.iloc[-1] - 1.0) * 2, 1.0)
        elif bb_percent.iloc[-1] < 0.0:
            signal, strength = "BUY", min(abs(bb_percent.iloc[-1]) * 2, 1.0)
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(
            {"upper": upper, "middle": vw_ma, "lower": lower, "percent_b": bb_percent, "bandwidth": bandwidth},
            signal, strength, 0.85,
            {"period": period, "std_dev": std_dev, "volume_weighted": True}
        )
    
    @staticmethod
    def vw_williams_r(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> IndicatorResult:
        """Volume Weighted Williams %R"""
        # Calculate volume weighted high and low
        vw_high = (high * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_low = (low * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_close = (close * volume).rolling(period).sum() / volume.rolling(period).sum()
        
        highest_high = vw_high.rolling(period).max()
        lowest_low = vw_low.rolling(period).min()
        
        vw_williams_r = -100 * (highest_high - vw_close) / (highest_high - lowest_low)
        
        if vw_williams_r.iloc[-1] < -80:
            signal, strength = "STRONG_BUY", 0.9
        elif vw_williams_r.iloc[-1] < -50:
            signal, strength = "BUY", 0.6
        elif vw_williams_r.iloc[-1] > -20:
            signal, strength = "STRONG_SELL", 0.9
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(vw_williams_r, signal, strength, 0.8, 
                             {"period": period, "volume_weighted": True})
    
    @staticmethod
    def vw_cci(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 20) -> IndicatorResult:
        """Volume Weighted Commodity Channel Index"""
        # Volume weighted typical price
        typical_price = (high + low + close) / 3
        vw_tp = (typical_price * volume).rolling(period).sum() / volume.rolling(period).sum()
        vw_tp_sma = vw_tp.rolling(period).mean()
        
        # Volume weighted mean deviation
        vw_mean_dev = (abs(vw_tp - vw_tp_sma) * volume).rolling(period).sum() / volume.rolling(period).sum()
        
        vw_cci = (vw_tp - vw_tp_sma) / (0.015 * vw_mean_dev)
        
        if vw_cci.iloc[-1] > 200:
            signal, strength = "STRONG_SELL", 0.9
        elif vw_cci.iloc[-1] > 100:
            signal, strength = "SELL", 0.7
        elif vw_cci.iloc[-1] < -200:
            signal, strength = "STRONG_BUY", 0.9
        elif vw_cci.iloc[-1] < -100:
            signal, strength = "BUY", 0.7
        else:
            signal, strength = "NEUTRAL", 0.0
        
        return IndicatorResult(vw_cci, signal, strength, 0.8, 
                             {"period": period, "volume_weighted": True})
    
    # ===========================================
    # MASTER INDICATOR CALCULATION METHOD
    # ===========================================
    
    def calculate_all_indicators(self, data: Dict[str, pd.Series], 
                               include_patterns: bool = True,
                               include_volume_weighted: bool = True) -> Dict[str, ComprehensiveIndicatorResult]:
        """
        Calculate all available indicators
        
        Args:
            data: Dictionary containing 'open', 'high', 'low', 'close', 'volume' Series
            include_patterns: Whether to include candlestick patterns
            include_volume_weighted: Whether to include volume-weighted variants
        
        Returns:
            Dictionary of all calculated indicators
        """
        results = {}
        
        # Extract data series
        open_data = data['open']
        high_data = data['high'] 
        low_data = data['low']
        close_data = data['close']
        volume_data = data['volume']
        
        # ===========================================
        # TREND INDICATORS
        # ===========================================
        
        # Traditional Moving Averages
        sma_result = self.traditional_indicators.sma(close_data, 20)
        results['sma_20'] = ComprehensiveIndicatorResult(
            "Simple Moving Average (20)", IndicatorCategory.TREND, sma_result.value,
            sma_result.signal, sma_result.strength, 0.7, False, sma_result.metadata
        )
        
        ema_result = self.traditional_indicators.ema(close_data, 20)
        results['ema_20'] = ComprehensiveIndicatorResult(
            "Exponential Moving Average (20)", IndicatorCategory.TREND, ema_result.value,
            ema_result.signal, ema_result.strength, 0.75, False, ema_result.metadata
        )
        
        # Enhanced Moving Averages
        kama_result = self.enhanced_indicators.adaptive_moving_average(close_data, 20)
        results['kama_20'] = ComprehensiveIndicatorResult(
            "Kaufman Adaptive MA (20)", IndicatorCategory.TREND, kama_result.value,
            kama_result.signal, kama_result.strength, kama_result.confidence, False, kama_result.metadata
        )
        
        dema_result = self.enhanced_indicators.double_exponential_ma(close_data, 21)
        results['dema_21'] = ComprehensiveIndicatorResult(
            "Double Exponential MA (21)", IndicatorCategory.TREND, dema_result.value,
            dema_result.signal, dema_result.strength, dema_result.confidence, False, dema_result.metadata
        )
        
        hull_result = self.enhanced_indicators.hull_moving_average(close_data, 21)
        results['hull_21'] = ComprehensiveIndicatorResult(
            "Hull Moving Average (21)", IndicatorCategory.TREND, hull_result.value,
            hull_result.signal, hull_result.strength, hull_result.confidence, False, hull_result.metadata
        )
        
        # Volume-Weighted Trend Indicators
        if include_volume_weighted:
            vwma_result = self.traditional_indicators.vwma(close_data, volume_data, 20)
            results['vwma_20'] = ComprehensiveIndicatorResult(
                "Volume Weighted MA (20)", IndicatorCategory.TREND, vwma_result.value,
                vwma_result.signal, vwma_result.strength, 0.8, True, vwma_result.metadata
            )
            
            vw_ema_result = self.traditional_indicators.vw_ema(close_data, volume_data, 20)
            results['vw_ema_20'] = ComprehensiveIndicatorResult(
                "Volume Weighted EMA (20)", IndicatorCategory.TREND, vw_ema_result.value,
                vw_ema_result.signal, vw_ema_result.strength, 0.85, True, vw_ema_result.metadata
            )
            
            vw_sma_result = self.vw_sma(close_data, volume_data, 20)
            results['vw_sma_20'] = ComprehensiveIndicatorResult(
                "Volume Weighted SMA (20)", IndicatorCategory.TREND, vw_sma_result.value,
                vw_sma_result.signal, vw_sma_result.strength, vw_sma_result.confidence, True, vw_sma_result.metadata
            )
        
        # ===========================================
        # MOMENTUM INDICATORS
        # ===========================================
        
        # Traditional Momentum
        rsi_result = self.traditional_indicators.rsi(close_data, 14)
        results['rsi_14'] = ComprehensiveIndicatorResult(
            "Relative Strength Index (14)", IndicatorCategory.MOMENTUM, rsi_result.value,
            rsi_result.signal, rsi_result.strength, 0.8, False, rsi_result.metadata
        )
        
        macd_result = self.traditional_indicators.macd(close_data, 12, 26, 9)
        results['macd'] = ComprehensiveIndicatorResult(
            "MACD (12,26,9)", IndicatorCategory.MOMENTUM, macd_result.value,
            macd_result.signal, macd_result.strength, 0.85, False, macd_result.metadata
        )
        
        # Enhanced Momentum
        stoch_result = self.enhanced_indicators.stochastic_oscillator(high_data, low_data, close_data, 14, 3, 3)
        results['stochastic'] = ComprehensiveIndicatorResult(
            "Stochastic Oscillator (14,3,3)", IndicatorCategory.MOMENTUM, stoch_result.value,
            stoch_result.signal, stoch_result.strength, stoch_result.confidence, False, stoch_result.metadata
        )
        
        williams_result = self.enhanced_indicators.williams_percent_r(high_data, low_data, close_data, 14)
        results['williams_r'] = ComprehensiveIndicatorResult(
            "Williams %R (14)", IndicatorCategory.MOMENTUM, williams_result.value,
            williams_result.signal, williams_result.strength, williams_result.confidence, False, williams_result.metadata
        )
        
        cci_result = self.enhanced_indicators.commodity_channel_index(high_data, low_data, close_data, 20)
        results['cci'] = ComprehensiveIndicatorResult(
            "Commodity Channel Index (20)", IndicatorCategory.MOMENTUM, cci_result.value,
            cci_result.signal, cci_result.strength, cci_result.confidence, False, cci_result.metadata
        )
        
        # Volume-Weighted Momentum
        if include_volume_weighted:
            vw_rsi_result = self.traditional_indicators.vw_rsi(close_data, volume_data, 14)
            results['vw_rsi_14'] = ComprehensiveIndicatorResult(
                "Volume Weighted RSI (14)", IndicatorCategory.MOMENTUM, vw_rsi_result.value,
                vw_rsi_result.signal, vw_rsi_result.strength, 0.85, True, vw_rsi_result.metadata
            )
            
            vw_macd_result = self.traditional_indicators.vw_macd(close_data, volume_data, 12, 26, 9)
            results['vw_macd'] = ComprehensiveIndicatorResult(
                "Volume Weighted MACD (12,26,9)", IndicatorCategory.MOMENTUM, vw_macd_result.value,
                vw_macd_result.signal, vw_macd_result.strength, 0.9, True, vw_macd_result.metadata
            )
            
            vw_stoch_result = self.vw_stochastic(high_data, low_data, close_data, volume_data, 14, 3)
            results['vw_stochastic'] = ComprehensiveIndicatorResult(
                "Volume Weighted Stochastic (14,3)", IndicatorCategory.MOMENTUM, vw_stoch_result.value,
                vw_stoch_result.signal, vw_stoch_result.strength, vw_stoch_result.confidence, True, vw_stoch_result.metadata
            )
        
        # ===========================================
        # VOLATILITY INDICATORS
        # ===========================================
        
        # Traditional Volatility
        bb_result = self.traditional_indicators.bollinger_bands(close_data, 20, 2.0)
        results['bollinger_bands'] = ComprehensiveIndicatorResult(
            "Bollinger Bands (20,2)", IndicatorCategory.VOLATILITY, bb_result.value,
            bb_result.signal, bb_result.strength, 0.8, False, bb_result.metadata
        )
        
        atr_result = self.traditional_indicators.atr(high_data, low_data, close_data, 14)
        results['atr_14'] = ComprehensiveIndicatorResult(
            "Average True Range (14)", IndicatorCategory.VOLATILITY, atr_result.value,
            atr_result.signal, atr_result.strength, 0.7, False, atr_result.metadata
        )
        
        # Enhanced Volatility
        keltner_result = self.volatility_volume_indicators.keltner_channels(high_data, low_data, close_data, 20, 2.0)
        results['keltner_channels'] = ComprehensiveIndicatorResult(
            "Keltner Channels (20,2)", IndicatorCategory.VOLATILITY, keltner_result.value,
            keltner_result.signal, keltner_result.strength, keltner_result.confidence, False, keltner_result.metadata
        )
        
        donchian_result = self.volatility_volume_indicators.donchian_channels(high_data, low_data, close_data, 20)
        results['donchian_channels'] = ComprehensiveIndicatorResult(
            "Donchian Channels (20)", IndicatorCategory.VOLATILITY, donchian_result.value,
            donchian_result.signal, donchian_result.strength, donchian_result.confidence, False, donchian_result.metadata
        )
        
        # Volume-Weighted Volatility
        if include_volume_weighted:
            vw_atr_result = self.traditional_indicators.vw_atr(high_data, low_data, close_data, volume_data, 14)
            results['vw_atr_14'] = ComprehensiveIndicatorResult(
                "Volume Weighted ATR (14)", IndicatorCategory.VOLATILITY, vw_atr_result.value,
                vw_atr_result.signal, vw_atr_result.strength, 0.85, True, vw_atr_result.metadata
            )
            
            vw_bb_result = self.vw_bollinger_bands(close_data, volume_data, 20, 2.0)
            results['vw_bollinger_bands'] = ComprehensiveIndicatorResult(
                "Volume Weighted Bollinger Bands (20,2)", IndicatorCategory.VOLATILITY, vw_bb_result.value,
                vw_bb_result.signal, vw_bb_result.strength, vw_bb_result.confidence, True, vw_bb_result.metadata
            )
        
        # ===========================================
        # VOLUME INDICATORS
        # ===========================================
        
        vwap_result = self.traditional_indicators.vwap(high_data, low_data, close_data, volume_data)
        results['vwap'] = ComprehensiveIndicatorResult(
            "Volume Weighted Average Price", IndicatorCategory.VOLUME, vwap_result.value,
            vwap_result.signal, vwap_result.strength, 0.9, True, vwap_result.metadata
        )
        
        obv_result = self.traditional_indicators.obv(close_data, volume_data)
        results['obv'] = ComprehensiveIndicatorResult(
            "On Balance Volume", IndicatorCategory.VOLUME, obv_result.value,
            obv_result.signal, obv_result.strength, 0.7, True, obv_result.metadata
        )
        
        # Enhanced Volume
        enhanced_vwap_result = self.volatility_volume_indicators.volume_weighted_average_price(high_data, low_data, close_data, volume_data)
        results['enhanced_vwap'] = ComprehensiveIndicatorResult(
            "Enhanced VWAP with Bands", IndicatorCategory.VOLUME, enhanced_vwap_result.value,
            enhanced_vwap_result.signal, enhanced_vwap_result.strength, enhanced_vwap_result.confidence, True, enhanced_vwap_result.metadata
        )
        
        mfi_result = self.volatility_volume_indicators.money_flow_index(high_data, low_data, close_data, volume_data, 14)
        results['mfi_14'] = ComprehensiveIndicatorResult(
            "Money Flow Index (14)", IndicatorCategory.VOLUME, mfi_result.value,
            mfi_result.signal, mfi_result.strength, mfi_result.confidence, True, mfi_result.metadata
        )
        
        # ===========================================
        # CANDLESTICK PATTERNS
        # ===========================================
        
        if include_patterns:
            try:
                # Create DataFrame for pattern analysis
                pattern_df = pd.DataFrame({
                    'open': open_data,
                    'high': high_data,
                    'low': low_data,
                    'close': close_data,
                    'volume': volume_data
                })
                
                # Detect all patterns
                patterns_dict = self.pattern_detector.detect_all_patterns(pattern_df)
                pattern_summary = self.pattern_detector.get_pattern_summary(patterns_dict)
                
                results['candlestick_patterns'] = ComprehensiveIndicatorResult(
                    "Candlestick Patterns Analysis", IndicatorCategory.PATTERNS, patterns_dict,
                    "NEUTRAL", 0.0, 0.8, False, pattern_summary
                )
                
                # Add individual strong patterns
                if pattern_summary.get('strongest_signals'):
                    for i, signal in enumerate(pattern_summary['strongest_signals'][:3]):  # Top 3
                        results[f'pattern_{i+1}'] = ComprehensiveIndicatorResult(
                            signal['pattern'], IndicatorCategory.PATTERNS, signal,
                            "BUY" if "bullish" in signal['type'] else "SELL" if "bearish" in signal['type'] else "NEUTRAL",
                            signal['strength'], signal['confidence'], False, 
                            {"pattern_type": signal['type'], "reliability": signal['reliability']}
                        )
                
            except Exception as e:
                print(f"Pattern analysis failed: {e}")
        
        return results
    
    def get_indicator_summary(self, results: Dict[str, ComprehensiveIndicatorResult]) -> Dict:
        """Generate comprehensive summary of all indicators"""
        
        summary = {
            "total_indicators": len(results),
            "by_category": {},
            "strong_signals": [],
            "volume_weighted_count": 0,
            "overall_sentiment": {"bullish": 0, "bearish": 0, "neutral": 0}
        }
        
        # Categorize and analyze
        for name, result in results.items():
            category = result.category.value
            if category not in summary["by_category"]:
                summary["by_category"][category] = 0
            summary["by_category"][category] += 1
            
            if result.volume_weighted:
                summary["volume_weighted_count"] += 1
            
            # Analyze signals
            if "BUY" in result.signal:
                summary["overall_sentiment"]["bullish"] += 1
            elif "SELL" in result.signal:
                summary["overall_sentiment"]["bearish"] += 1
            else:
                summary["overall_sentiment"]["neutral"] += 1
            
            # Collect strong signals
            if result.strength * result.confidence > 0.7:
                summary["strong_signals"].append({
                    "indicator": result.indicator_name,
                    "signal": result.signal,
                    "strength": result.strength,
                    "confidence": result.confidence,
                    "category": category,
                    "volume_weighted": result.volume_weighted
                })
        
        # Sort strong signals by strength
        summary["strong_signals"] = sorted(summary["strong_signals"], 
                                         key=lambda x: x["strength"] * x["confidence"], reverse=True)[:10]
        
        # Calculate overall sentiment
        total_signals = sum(summary["overall_sentiment"].values())
        if total_signals > 0:
            summary["sentiment_percentages"] = {
                "bullish": summary["overall_sentiment"]["bullish"] / total_signals * 100,
                "bearish": summary["overall_sentiment"]["bearish"] / total_signals * 100,
                "neutral": summary["overall_sentiment"]["neutral"] / total_signals * 100
            }
        
        return summary