"""
Enhanced Volume-Weighted Technical Indicators - Phase 5 Enterprise Feature
Advanced technical analysis indicators incorporating volume data, candlestick patterns, and price adjustments

This module extends the original volume-weighted indicators with:
- Integration with candlestick pattern recognition
- Price adjustment capabilities for corporate actions
- Enhanced technical indicators from the comprehensive library
- Pattern-based volume weighting
- Multi-timeframe analysis
- Advanced market structure indicators
"""

import numpy as np
import pandas as pd
from typing import Union, Optional, Tuple, Dict, List
import warnings
from dataclasses import dataclass
from datetime import datetime, date

# Import the new indicator modules
from .volume_weighted import VolumeWeightedIndicators, MarketData
from .candle_patterns import apply_candle_patterns, apply_candle_properties
from .adjusted_prices import calculate_adjusted_ohlc

# Suppress pandas warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)


@dataclass
class EnhancedMarketData:
    """Enhanced container for market data with additional features"""
    open: pd.Series
    high: pd.Series
    low: pd.Series
    close: pd.Series
    volume: pd.Series
    adjusted_close: Optional[pd.Series] = None
    stock_splits: Optional[pd.Series] = None
    dividends: Optional[pd.Series] = None
    
    def __post_init__(self):
        """Validate and process data"""
        lengths = [len(self.open), len(self.high), len(self.low), len(self.close), len(self.volume)]
        if len(set(lengths)) > 1:
            raise ValueError("All price and volume series must have the same length")
        
        # Apply price adjustments if corporate actions are provided
        if self.stock_splits is not None and self.dividends is not None:
            df = pd.DataFrame({
                'Open': self.open,
                'High': self.high,
                'Low': self.low,
                'Close': self.close,
                'Stock Splits': self.stock_splits,
                'Dividends': self.dividends
            })
            adjusted_df = calculate_adjusted_ohlc(df, adjustment="both")
            self.adjusted_close = adjusted_df['Adj Close']
    
    def to_market_data(self) -> MarketData:
        """Convert to standard MarketData object"""
        return MarketData(
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume
        )


class EnhancedVolumeWeightedIndicators:
    """
    Enhanced volume-weighted indicators with pattern recognition and advanced features
    """
    
    @staticmethod
    def pattern_weighted_vwap(data: EnhancedMarketData, pattern_boost: float = 1.5) -> pd.Series:
        """
        Volume-Weighted Average Price with candlestick pattern weighting
        
        Args:
            data: Enhanced market data
            pattern_boost: Multiplier for volume when significant patterns are detected
            
        Returns:
            Pattern-weighted VWAP
        """
        # Create DataFrame for pattern analysis
        df = pd.DataFrame({
            'Mid_Open': data.open,
            'Mid_High': data.high,
            'Mid_Low': data.low,
            'Mid_Close': data.close,
            'Volume': data.volume
        })
        
        # Apply candlestick pattern recognition
        df_patterns = apply_candle_patterns(df)
        
        # Identify significant patterns (reversal patterns get higher weight)
        significant_patterns = (
            df_patterns['Hanging_Man'] | 
            df_patterns['Shooting_Star'] |
            df_patterns['Engulfing'] |
            df_patterns['Morning_Star'] |
            df_patterns['Evening_Star']
        )
        
        # Adjust volume based on pattern significance
        adjusted_volume = data.volume.copy()
        adjusted_volume[significant_patterns] *= pattern_boost
        
        # Calculate pattern-weighted VWAP
        typical_price = (data.high + data.low + data.close) / 3
        return (typical_price * adjusted_volume).cumsum() / adjusted_volume.cumsum()
    
    @staticmethod
    def technical_indicator_enhanced_vw_sma(data: EnhancedMarketData, window: int, 
                                          trend_sensitivity: float = 0.2) -> pd.Series:
        """
        Volume-weighted SMA enhanced with technical indicators for trend strength
        
        Args:
            data: Enhanced market data
            window: Period for calculation
            trend_sensitivity: Sensitivity to trend strength (0-1)
            
        Returns:
            Enhanced VW SMA
        """
        # Calculate base VW SMA
        base_vw_sma = VolumeWeightedIndicators.vw_sma(data.close, data.volume, window)
        
        # Use technical indicators from the comprehensive library
        df = pd.DataFrame({
            'Mid_Open': data.open,
            'Mid_High': data.high,
            'Mid_Low': data.low,
            'Mid_Close': data.close,
            'Volume': data.volume
        })
        
        # Import functions from technical_indicators module
        from . import technical_indicators as ti
        
        # Calculate RSI for trend strength
        df = ti.RSI(df, n=14)
        rsi = df['RSI14']
        
        # Calculate ATR for volatility adjustment
        df = ti.ATR(df, n=14)
        atr = df['ATR14']
        
        # Normalize RSI to determine trend strength (0.5 = neutral)
        trend_strength = abs(rsi - 50) / 50  # 0 to 1 scale
        
        # Calculate regular SMA for comparison
        regular_sma = data.close.rolling(window=window).mean()
        
        # Blend based on trend strength
        trend_weight = trend_strength * trend_sensitivity
        enhanced_sma = base_vw_sma * (1 - trend_weight) + regular_sma * trend_weight
        
        return enhanced_sma
    
    @staticmethod
    def volatility_adjusted_vw_indicators(data: EnhancedMarketData, base_window: int = 21) -> Dict[str, pd.Series]:
        """
        Volume-weighted indicators adjusted for volatility using comprehensive ATR
        
        Args:
            data: Enhanced market data
            base_window: Base period for calculations
            
        Returns:
            Dictionary of volatility-adjusted indicators
        """
        # Create DataFrame for technical analysis
        df = pd.DataFrame({
            'Mid_Open': data.open,
            'Mid_High': data.high,
            'Mid_Low': data.low,
            'Mid_Close': data.close,
            'Volume': data.volume
        })
        
        # Import functions from technical_indicators module
        from . import technical_indicators as ti
        
        # Calculate Volume Weighted ATR
        df = ti.VW_ATR(df, n=base_window)
        vw_atr = df[f'VW_ATR{base_window}']
        
        # Calculate ATR percentage for volatility measurement
        atr_pct = (vw_atr / data.close) * 100
        
        # Adjust window sizes based on volatility
        volatility_multiplier = 1 + (atr_pct / 100)  # 1.0 to ~1.5 typically
        adjusted_window = (base_window * volatility_multiplier).round().astype(int)
        
        indicators = {}
        
        # Calculate indicators with adjusted windows
        for i in range(len(data.close)):
            if i < base_window:
                continue
                
            window = max(adjusted_window.iloc[i], 5)  # Minimum window of 5
            start_idx = max(0, i - window + 1)
            
            # Volume-weighted SMA with adjusted window
            price_slice = data.close.iloc[start_idx:i+1]
            volume_slice = data.volume.iloc[start_idx:i+1]
            
            if len(price_slice) > 0 and volume_slice.sum() > 0:
                vw_value = (price_slice * volume_slice).sum() / volume_slice.sum()
            else:
                vw_value = data.close.iloc[i]
            
            if 'vw_sma_volatility_adjusted' not in indicators:
                indicators['vw_sma_volatility_adjusted'] = pd.Series(index=data.close.index, dtype=float)
            indicators['vw_sma_volatility_adjusted'].iloc[i] = vw_value
        
        # Add VW ATR to results
        indicators['vw_atr'] = vw_atr
        indicators['atr_percent'] = atr_pct
        
        return indicators
    
    @staticmethod
    def multi_timeframe_vw_analysis(data: EnhancedMarketData, 
                                   timeframes: List[int] = [5, 13, 21, 55]) -> Dict[str, pd.Series]:
        """
        Multi-timeframe volume-weighted analysis with technical indicators
        
        Args:
            data: Enhanced market data
            timeframes: List of timeframe periods
            
        Returns:
            Dictionary of multi-timeframe indicators
        """
        indicators = {}
        
        # Create DataFrame for technical analysis
        df = pd.DataFrame({
            'Mid_Open': data.open,
            'Mid_High': data.high,
            'Mid_Low': data.low,
            'Mid_Close': data.close,
            'Volume': data.volume
        })
        
        # Import functions from technical_indicators module
        from . import technical_indicators as ti
        
        for tf in timeframes:
            # Volume-weighted indicators for each timeframe
            indicators[f'vw_sma_{tf}'] = VolumeWeightedIndicators.vw_sma(data.close, data.volume, tf)
            indicators[f'vw_ema_{tf}'] = VolumeWeightedIndicators.vw_ema(data.close, data.volume, tf)
            
            # Volume-weighted Bollinger Bands using OHLC
            df_bb = ti.VW_BollingerBands_OHLC(df.copy(), n=tf)
            indicators[f'vw_bb_sma_{tf}'] = df_bb[f'VW_BB_SMA{tf}']
            indicators[f'vw_bb_upper_{tf}'] = df_bb['VW_BB_Upper']
            indicators[f'vw_bb_lower_{tf}'] = df_bb['VW_BB_Lower']
            
            # Volume-weighted RSI
            df_rsi = ti.RSI(df.copy(), n=tf)
            indicators[f'rsi_{tf}'] = df_rsi[f'RSI{tf}']
            
            # Volume-weighted Keltner Channels
            df_kc = ti.VW_KeltnerChannels(df.copy(), n=tf)
            indicators[f'vw_kc_ema_{tf}'] = df_kc[f'VW_KC_EMA{tf}']
            indicators[f'vw_kc_upper_{tf}'] = df_kc['VW_KC_Upper']
            indicators[f'vw_kc_lower_{tf}'] = df_kc['VW_KC_Lower']
        
        return indicators
    
    @staticmethod
    def pattern_strength_volume_weighting(data: EnhancedMarketData) -> Dict[str, pd.Series]:
        """
        Calculate volume weighting based on candlestick pattern strength
        
        Args:
            data: Enhanced market data
            
        Returns:
            Dictionary of pattern-strength weighted indicators
        """
        # Create DataFrame for pattern analysis
        df = pd.DataFrame({
            'Mid_Open': data.open,
            'Mid_High': data.high,
            'Mid_Low': data.low,
            'Mid_Close': data.close,
            'Volume': data.volume
        })
        
        # Apply candlestick pattern recognition
        df_patterns = apply_candle_patterns(df)
        
        indicators = {}
        
        # Calculate pattern strength scores
        pattern_strength = pd.Series(0.0, index=data.close.index)
        
        # Assign strength scores to different patterns
        pattern_weights = {
            'Hanging_Man': 0.8,
            'Shooting_Star': 0.8,
            'Spinning_Top': 0.3,
            'Marubozu': 0.6,
            'Engulfing': 0.9,
            'Tweezer_Top': 0.7,
            'Tweezer_Bottom': 0.7,
            'Morning_Star': 1.0,
            'Evening_Star': 1.0
        }
        
        for pattern, weight in pattern_weights.items():
            if pattern in df_patterns.columns:
                pattern_strength += df_patterns[pattern] * weight
        
        # Normalize pattern strength (0-1 scale)
        pattern_strength = np.clip(pattern_strength, 0, 1)
        
        # Apply pattern strength to volume weighting
        base_volume_weight = 1.0
        max_volume_boost = 2.0
        
        volume_multiplier = base_volume_weight + (pattern_strength * (max_volume_boost - base_volume_weight))
        adjusted_volume = data.volume * volume_multiplier
        
        # Calculate pattern-strength weighted indicators
        indicators['pattern_strength'] = pattern_strength
        indicators['volume_multiplier'] = volume_multiplier
        indicators['pattern_vw_sma_21'] = VolumeWeightedIndicators.vw_sma(data.close, adjusted_volume, 21)
        indicators['pattern_vw_ema_13'] = VolumeWeightedIndicators.vw_ema(data.close, adjusted_volume, 13)
        
        # Pattern-weighted VWAP
        typical_price = (data.high + data.low + data.close) / 3
        indicators['pattern_vwap'] = (typical_price * adjusted_volume).cumsum() / adjusted_volume.cumsum()
        
        return indicators
    
    @staticmethod
    def comprehensive_market_analysis(data: EnhancedMarketData) -> Dict[str, pd.Series]:
        """
        Comprehensive market analysis combining all enhanced features
        
        Args:
            data: Enhanced market data
            
        Returns:
            Dictionary of comprehensive market indicators
        """
        indicators = {}
        
        # Create DataFrame for comprehensive analysis
        df = pd.DataFrame({
            'Mid_Open': data.open,
            'Mid_High': data.high,
            'Mid_Low': data.low,
            'Mid_Close': data.close,
            'Volume': data.volume
        })
        
        # Import functions from technical_indicators module
        from . import technical_indicators as ti
        
        # 1. Pattern-weighted VWAP
        indicators['pattern_vwap'] = EnhancedVolumeWeightedIndicators.pattern_weighted_vwap(data)
        
        # 2. Technical indicator enhanced VW SMA
        indicators['enhanced_vw_sma_21'] = EnhancedVolumeWeightedIndicators.technical_indicator_enhanced_vw_sma(data, 21)
        
        # 3. Volatility-adjusted indicators
        vol_indicators = EnhancedVolumeWeightedIndicators.volatility_adjusted_vw_indicators(data)
        indicators.update(vol_indicators)
        
        # 4. Multi-timeframe analysis
        mtf_indicators = EnhancedVolumeWeightedIndicators.multi_timeframe_vw_analysis(data)
        indicators.update(mtf_indicators)
        
        # 5. Pattern strength volume weighting
        pattern_indicators = EnhancedVolumeWeightedIndicators.pattern_strength_volume_weighting(data)
        indicators.update(pattern_indicators)
        
        # 6. Advanced technical indicators from the library
        # Volume Weighted Bollinger Bands with High-Low midpoint
        df_bb_hl = ti.VW_BollingerBands_HL(df.copy())
        indicators['vw_bb_hl_sma'] = df_bb_hl['VW_BB_HL_SMA20']
        indicators['vw_bb_hl_upper'] = df_bb_hl['VW_BB_HL_Upper']
        indicators['vw_bb_hl_lower'] = df_bb_hl['VW_BB_HL_Lower']
        
        # Volume Weighted Standard Deviation
        df_sd = ti.VW_StandardDeviation_HL(df.copy())
        indicators['vw_standard_deviation'] = df_sd['VW_SD20']
        indicators['vw_sd_sma'] = df_sd['VW_SD20_SMA10']
        
        # Volume Weighted ATR Percent
        df_atrp = ti.VW_ATRP(df.copy())
        indicators['vw_atrp'] = df_atrp['VW_ATRP14']
        indicators['vw_atrp_sma'] = df_atrp['VW_ATRP14_SMA10']
        
        # Normalized Volume Weighted ATRP
        df_natrp = ti.Normalised_VW_ATRP(df.copy())
        indicators['normalized_vw_atrp'] = df_natrp['Norm_VW_ATRP14']
        indicators['normalized_vw_atrp_sma'] = df_natrp['Norm_VW_ATRP14_SMA10']
        
        # Volume Weighted Keltner Channels with SMA
        df_kc_sma = ti.VW_KeltnerChannels_SMA(df.copy())
        indicators['vw_kc_sma_upper'] = df_kc_sma['VW_KC_SMA_Upper']
        indicators['vw_kc_sma_lower'] = df_kc_sma['VW_KC_SMA_Lower']
        
        # RSI variations
        df_rsi_ohlc = ti.RSI_OHLC(df.copy())
        indicators['rsi_ohlc'] = df_rsi_ohlc['RSI14_OHLC']
        indicators['rsi_ohlc_sma'] = df_rsi_ohlc['RSI14_OHLC_SMA10']
        
        df_rsi_hl = ti.RSI_HL(df.copy())
        indicators['rsi_hl'] = df_rsi_hl['RSI14_HL']
        indicators['rsi_hl_sma'] = df_rsi_hl['RSI14_HL_SMA10']
        
        # 7. Original volume-weighted indicators for comparison
        market_data = data.to_market_data()
        indicators['original_vw_sma_21'] = VolumeWeightedIndicators.vw_sma(data.close, data.volume, 21)
        indicators['original_vw_ema_13'] = VolumeWeightedIndicators.vw_ema(data.close, data.volume, 13)
        indicators['original_vw_mfi'] = VolumeWeightedIndicators.vw_mfi(market_data)
        
        # MACD with HLC average
        hlc_avg = VolumeWeightedIndicators.hlc_average(data.high, data.low, data.close)
        macd_line, signal_line, histogram = VolumeWeightedIndicators.vw_macd(hlc_avg, data.volume)
        indicators['vw_macd'] = macd_line
        indicators['vw_macd_signal'] = signal_line
        indicators['vw_macd_histogram'] = histogram
        
        return indicators
    
    @staticmethod
    def adjusted_price_indicators(data: EnhancedMarketData) -> Dict[str, pd.Series]:
        """
        Calculate indicators using adjusted prices for corporate actions
        
        Args:
            data: Enhanced market data with adjustment information
            
        Returns:
            Dictionary of adjusted price indicators
        """
        indicators = {}
        
        if data.adjusted_close is not None:
            # Use adjusted close for calculations
            adjusted_data = EnhancedMarketData(
                open=data.open,  # Could also adjust open, high, low if needed
                high=data.high,
                low=data.low,
                close=data.adjusted_close,
                volume=data.volume
            )
            
            # Calculate indicators with adjusted prices
            indicators['adjusted_vw_sma_21'] = VolumeWeightedIndicators.vw_sma(
                data.adjusted_close, data.volume, 21
            )
            indicators['adjusted_vw_ema_13'] = VolumeWeightedIndicators.vw_ema(
                data.adjusted_close, data.volume, 13
            )
            
            # Adjusted VWAP
            typical_price_adj = (data.high + data.low + data.adjusted_close) / 3
            indicators['adjusted_vwap'] = (typical_price_adj * data.volume).cumsum() / data.volume.cumsum()
            
            # Pattern analysis with adjusted prices
            df_adj = pd.DataFrame({
                'Mid_Open': data.open,
                'Mid_High': data.high,
                'Mid_Low': data.low,
                'Mid_Close': data.adjusted_close,
                'Volume': data.volume
            })
            
            df_patterns_adj = apply_candle_patterns(df_adj)
            indicators['adjusted_pattern_count'] = (
                df_patterns_adj[['Hanging_Man', 'Shooting_Star', 'Engulfing', 
                               'Morning_Star', 'Evening_Star']].sum(axis=1)
            )
        
        return indicators


# Convenience functions for enhanced indicator combinations
def calculate_all_enhanced_indicators(data: EnhancedMarketData) -> Dict[str, pd.Series]:
    """
    Calculate all enhanced volume-weighted indicators
    
    Args:
        data: Enhanced market data
        
    Returns:
        Dictionary containing all enhanced indicators
    """
    return EnhancedVolumeWeightedIndicators.comprehensive_market_analysis(data)


def calculate_pattern_based_indicators(data: EnhancedMarketData) -> Dict[str, pd.Series]:
    """
    Calculate pattern-based volume-weighted indicators
    
    Args:
        data: Enhanced market data
        
    Returns:
        Dictionary containing pattern-based indicators
    """
    return EnhancedVolumeWeightedIndicators.pattern_strength_volume_weighting(data)


def calculate_technical_enhanced_indicators(data: EnhancedMarketData) -> Dict[str, pd.Series]:
    """
    Calculate technical indicator enhanced volume-weighted indicators
    
    Args:
        data: Enhanced market data
        
    Returns:
        Dictionary containing technical enhanced indicators
    """
    indicators = {}
    
    # Multi-timeframe analysis
    mtf_indicators = EnhancedVolumeWeightedIndicators.multi_timeframe_vw_analysis(data)
    indicators.update(mtf_indicators)
    
    # Volatility-adjusted indicators
    vol_indicators = EnhancedVolumeWeightedIndicators.volatility_adjusted_vw_indicators(data)
    indicators.update(vol_indicators)
    
    # Adjusted price indicators (if available)
    adj_indicators = EnhancedVolumeWeightedIndicators.adjusted_price_indicators(data)
    indicators.update(adj_indicators)
    
    return indicators