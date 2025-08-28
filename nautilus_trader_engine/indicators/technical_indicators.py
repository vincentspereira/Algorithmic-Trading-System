"""
Enhanced Technical Indicators Module

This module provides a comprehensive technical indicators library that integrates
TA-Lib as the primary indicator library with ta (Bukosabino) as secondary/fallback.
It includes Volume-Weighted indicators and provides comprehensive error handling
with graceful fallback between libraries.

Features:
- TA-Lib as primary indicator library
- ta (Bukosabino) as secondary/fallback
- Volume-Weighted indicators (VW SMA, VW MACD)
- Comprehensive error handling
- Performance comparisons
- Graceful fallback between libraries

Author: Vincent S. Pereira
Version: 2.0.0
"""

import pandas as pd
import numpy as np
import warnings
import time
from typing import Union, Optional, Tuple, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import TA-Lib, fall back to 'ta' library if not available
TALIB_AVAILABLE = False
TA_AVAILABLE = False

try:
    import talib
    TALIB_AVAILABLE = True
    logger.info("TA-Lib is available - using native TA-Lib functions")
except ImportError:
    logger.warning("TA-Lib not available - using fallback implementations")

try:
    import ta
    TA_AVAILABLE = True
    logger.info("'ta' library is available for fallback implementations")
except ImportError:
    logger.warning("Warning: Neither TA-Lib nor 'ta' library is available")

# Import existing fallback functions
try:
    from indicators_fallback import (
        SMA as fallback_SMA,
        EMA as fallback_EMA,
        RSI as fallback_RSI,
        MACD as fallback_MACD,
        BBANDS as fallback_BBANDS,
        STOCH as fallback_STOCH,
        IndicatorError,
        check_data
    )
    FALLBACK_AVAILABLE = True
    logger.info("Fallback indicators module available")
except ImportError:
    FALLBACK_AVAILABLE = False
    logger.warning("Fallback indicators module not available")


class IndicatorLibrary(Enum):
    """Available indicator libraries"""
    TALIB = "talib"
    TA = "ta"
    FALLBACK = "fallback"
    MANUAL = "manual"


@dataclass
class IndicatorResult:
    """Result container for indicator calculations"""
    values: np.ndarray
    library_used: IndicatorLibrary
    calculation_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None


class TechnicalIndicators:
    """Enhanced technical indicators class with multiple library support"""
    
    def __init__(self, prefer_talib: bool = True):
        self.prefer_talib = prefer_talib
        self.performance_stats = {}
        
    def _benchmark_calculation(self, func, *args, **kwargs) -> Tuple[Any, float]:
        """Benchmark indicator calculation time"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        return result, end_time - start_time
    
    def _safe_calculate(self, primary_func, fallback_func, *args, **kwargs) -> IndicatorResult:
        """Safely calculate indicator with fallback"""
        errors = []
        
        # Try primary function first
        try:
            result, calc_time = self._benchmark_calculation(primary_func, *args, **kwargs)
            return IndicatorResult(
                values=result,
                library_used=IndicatorLibrary.TALIB if primary_func.__module__ == 'talib' else IndicatorLibrary.TA,
                calculation_time=calc_time,
                success=True,
                metadata={"method": "primary"}
            )
        except Exception as e:
            errors.append(f"Primary: {str(e)}")
        
        # Try fallback function
        try:
            result, calc_time = self._benchmark_calculation(fallback_func, *args, **kwargs)
            return IndicatorResult(
                values=result,
                library_used=IndicatorLibrary.FALLBACK,
                calculation_time=calc_time,
                success=True,
                metadata={"method": "fallback", "primary_error": errors[0] if errors else None}
            )
        except Exception as e:
            errors.append(f"Fallback: {str(e)}")
        
        # Return error result
        return IndicatorResult(
            values=np.array([]),
            library_used=IndicatorLibrary.MANUAL,
            calculation_time=0.0,
            success=False,
            error_message="; ".join(errors)
        )
    
    def SMA(self, close: Union[pd.Series, np.ndarray], timeperiod: int = 30) -> IndicatorResult:
        """Simple Moving Average with enhanced error handling"""
        close = check_data(close, timeperiod) if FALLBACK_AVAILABLE else np.array(close)
        
        if TALIB_AVAILABLE and self.prefer_talib:
            primary_func = lambda: talib.SMA(close, timeperiod=timeperiod)
        elif TA_AVAILABLE:
            primary_func = lambda: ta.trend.sma_indicator(pd.Series(close), window=timeperiod).values
        else:
            primary_func = lambda: self._manual_sma(close, timeperiod)
        
        fallback_func = fallback_SMA if FALLBACK_AVAILABLE else lambda: self._manual_sma(close, timeperiod)
        
        return self._safe_calculate(primary_func, fallback_func, close, timeperiod)
    
    def EMA(self, close: Union[pd.Series, np.ndarray], timeperiod: int = 30) -> IndicatorResult:
        """Exponential Moving Average with enhanced error handling"""
        close = check_data(close, timeperiod) if FALLBACK_AVAILABLE else np.array(close)
        
        if TALIB_AVAILABLE and self.prefer_talib:
            primary_func = lambda: talib.EMA(close, timeperiod=timeperiod)
        elif TA_AVAILABLE:
            primary_func = lambda: ta.trend.ema_indicator(pd.Series(close), window=timeperiod).values
        else:
            primary_func = lambda: self._manual_ema(close, timeperiod)
        
        fallback_func = fallback_EMA if FALLBACK_AVAILABLE else lambda: self._manual_ema(close, timeperiod)
        
        return self._safe_calculate(primary_func, fallback_func, close, timeperiod)
    
    def RSI(self, close: Union[pd.Series, np.ndarray], timeperiod: int = 14) -> IndicatorResult:
        """Relative Strength Index with enhanced error handling"""
        close = check_data(close, timeperiod + 1) if FALLBACK_AVAILABLE else np.array(close)
        
        if TALIB_AVAILABLE and self.prefer_talib:
            primary_func = lambda: talib.RSI(close, timeperiod=timeperiod)
        elif TA_AVAILABLE:
            primary_func = lambda: ta.momentum.rsi(pd.Series(close), window=timeperiod).values
        else:
            primary_func = lambda: self._manual_rsi(close, timeperiod)
        
        fallback_func = fallback_RSI if FALLBACK_AVAILABLE else lambda: self._manual_rsi(close, timeperiod)
        
        return self._safe_calculate(primary_func, fallback_func, close, timeperiod)
    
    def MACD(self, close: Union[pd.Series, np.ndarray], 
             fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9) -> IndicatorResult:
        """MACD with enhanced error handling"""
        close = check_data(close, slowperiod) if FALLBACK_AVAILABLE else np.array(close)
        
        if TALIB_AVAILABLE and self.prefer_talib:
            primary_func = lambda: talib.MACD(close, fastperiod=fastperiod, 
                                            slowperiod=slowperiod, signalperiod=signalperiod)
        elif TA_AVAILABLE:
            def ta_macd():
                df = pd.DataFrame({'close': close})
                macd_line = ta.trend.macd(df['close'], window_fast=fastperiod, window_slow=slowperiod).values
                macd_signal = ta.trend.macd_signal(df['close'], window_fast=fastperiod, 
                                                 window_slow=slowperiod, window_sign=signalperiod).values
                macd_hist = ta.trend.macd_diff(df['close'], window_fast=fastperiod, 
                                             window_slow=slowperiod, window_sign=signalperiod).values
                return macd_line, macd_signal, macd_hist
            primary_func = ta_macd
        else:
            primary_func = lambda: self._manual_macd(close, fastperiod, slowperiod, signalperiod)
        
        fallback_func = (fallback_MACD if FALLBACK_AVAILABLE else 
                        lambda: self._manual_macd(close, fastperiod, slowperiod, signalperiod))
        
        return self._safe_calculate(primary_func, fallback_func, close, fastperiod, slowperiod, signalperiod)
    
    def BBANDS(self, close: Union[pd.Series, np.ndarray], 
               timeperiod: int = 20, nbdevup: float = 2.0, nbdevdn: float = 2.0) -> IndicatorResult:
        """Bollinger Bands with enhanced error handling"""
        close = check_data(close, timeperiod) if FALLBACK_AVAILABLE else np.array(close)
        
        if TALIB_AVAILABLE and self.prefer_talib:
            primary_func = lambda: talib.BBANDS(close, timeperiod=timeperiod, 
                                              nbdevup=nbdevup, nbdevdn=nbdevdn)
        elif TA_AVAILABLE:
            def ta_bbands():
                df = pd.DataFrame({'close': close})
                upper = ta.volatility.bollinger_hband(df['close'], window=timeperiod, window_dev=nbdevup).values
                middle = ta.volatility.bollinger_mavg(df['close'], window=timeperiod).values
                lower = ta.volatility.bollinger_lband(df['close'], window=timeperiod, window_dev=nbdevdn).values
                return upper, middle, lower
            primary_func = ta_bbands
        else:
            primary_func = lambda: self._manual_bbands(close, timeperiod, nbdevup, nbdevdn)
        
        fallback_func = (fallback_BBANDS if FALLBACK_AVAILABLE else 
                        lambda: self._manual_bbands(close, timeperiod, nbdevup, nbdevdn))
        
        return self._safe_calculate(primary_func, fallback_func, close, timeperiod, nbdevup, nbdevdn)
    
    # Volume-Weighted Indicators
    def VW_SMA(self, close: Union[pd.Series, np.ndarray], 
               volume: Union[pd.Series, np.ndarray], timeperiod: int = 30) -> IndicatorResult:
        """Volume-Weighted Simple Moving Average"""
        try:
            close = np.array(close)
            volume = np.array(volume)
            
            if len(close) != len(volume):
                raise ValueError("Close and volume arrays must have the same length")
            
            start_time = time.perf_counter()
            
            # Calculate volume-weighted prices
            vw_prices = close * volume
            result = np.full(len(close), np.nan)
            
            for i in range(timeperiod - 1, len(close)):
                period_vw_prices = vw_prices[i - timeperiod + 1:i + 1]
                period_volumes = volume[i - timeperiod + 1:i + 1]
                
                total_volume = np.sum(period_volumes)
                if total_volume > 0:
                    result[i] = np.sum(period_vw_prices) / total_volume
            
            calc_time = time.perf_counter() - start_time
            
            return IndicatorResult(
                values=result,
                library_used=IndicatorLibrary.MANUAL,
                calculation_time=calc_time,
                success=True,
                metadata={"indicator": "VW_SMA", "timeperiod": timeperiod}
            )
            
        except Exception as e:
            return IndicatorResult(
                values=np.array([]),
                library_used=IndicatorLibrary.MANUAL,
                calculation_time=0.0,
                success=False,
                error_message=str(e)
            )
    
    def VW_MACD(self, close: Union[pd.Series, np.ndarray], 
                volume: Union[pd.Series, np.ndarray],
                fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9) -> IndicatorResult:
        """Volume-Weighted MACD"""
        try:
            # Calculate volume-weighted EMAs
            vw_ema_fast = self._volume_weighted_ema(close, volume, fastperiod)
            vw_ema_slow = self._volume_weighted_ema(close, volume, slowperiod)
            
            # MACD line
            macd_line = vw_ema_fast - vw_ema_slow
            
            # Signal line (EMA of MACD line)
            macd_signal = self._simple_ema(macd_line, signalperiod)
            
            # Histogram
            macd_hist = macd_line - macd_signal
            
            return IndicatorResult(
                values=(macd_line, macd_signal, macd_hist),
                library_used=IndicatorLibrary.MANUAL,
                calculation_time=0.0,  # Would need to benchmark
                success=True,
                metadata={"indicator": "VW_MACD", "fastperiod": fastperiod, 
                         "slowperiod": slowperiod, "signalperiod": signalperiod}
            )
            
        except Exception as e:
            return IndicatorResult(
                values=np.array([]),
                library_used=IndicatorLibrary.MANUAL,
                calculation_time=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _volume_weighted_ema(self, close: np.ndarray, volume: np.ndarray, period: int) -> np.ndarray:
        """Calculate volume-weighted EMA"""
        alpha = 2.0 / (period + 1.0)
        result = np.full(len(close), np.nan)
        
        # Initialize with volume-weighted average of first period
        if len(close) >= period:
            initial_vw_sum = np.sum(close[:period] * volume[:period])
            initial_vol_sum = np.sum(volume[:period])
            if initial_vol_sum > 0:
                result[period - 1] = initial_vw_sum / initial_vol_sum
        
        # Calculate VW EMA
        for i in range(period, len(close)):
            if volume[i] > 0 and not np.isnan(result[i - 1]):
                # Weight the alpha by volume
                volume_weight = volume[i] / np.mean(volume[max(0, i - period):i + 1])
                adjusted_alpha = alpha * volume_weight
                adjusted_alpha = min(adjusted_alpha, 1.0)  # Cap at 1.0
                
                result[i] = adjusted_alpha * close[i] + (1 - adjusted_alpha) * result[i - 1]
        
        return result
    
    def _simple_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Simple EMA calculation"""
        alpha = 2.0 / (period + 1.0)
        result = np.full(len(data), np.nan)
        
        # Find first valid value
        valid_idx = np.where(~np.isnan(data))[0]
        if len(valid_idx) == 0:
            return result
        
        start_idx = valid_idx[0]
        result[start_idx] = data[start_idx]
        
        for i in range(start_idx + 1, len(data)):
            if not np.isnan(data[i]):
                result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        
        return result
    
    # Manual implementations for fallback
    def _manual_sma(self, close: np.ndarray, timeperiod: int) -> np.ndarray:
        """Manual SMA calculation"""
        result = np.full(len(close), np.nan)
        for i in range(timeperiod - 1, len(close)):
            result[i] = np.mean(close[i - timeperiod + 1:i + 1])
        return result
    
    def _manual_ema(self, close: np.ndarray, timeperiod: int) -> np.ndarray:
        """Manual EMA calculation"""
        alpha = 2.0 / (timeperiod + 1.0)
        result = np.full(len(close), np.nan)
        result[timeperiod - 1] = np.mean(close[:timeperiod])
        
        for i in range(timeperiod, len(close)):
            result[i] = alpha * close[i] + (1 - alpha) * result[i - 1]
        
        return result
    
    def _manual_rsi(self, close: np.ndarray, timeperiod: int) -> np.ndarray:
        """Manual RSI calculation"""
        delta = np.diff(close)
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.full(len(close), np.nan)
        avg_loss = np.full(len(close), np.nan)
        
        avg_gain[timeperiod] = np.mean(gain[:timeperiod])
        avg_loss[timeperiod] = np.mean(loss[:timeperiod])
        
        for i in range(timeperiod + 1, len(close)):
            avg_gain[i] = (avg_gain[i-1] * (timeperiod - 1) + gain[i-1]) / timeperiod
            avg_loss[i] = (avg_loss[i-1] * (timeperiod - 1) + loss[i-1]) / timeperiod
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _manual_macd(self, close: np.ndarray, fastperiod: int, slowperiod: int, signalperiod: int) -> Tuple:
        """Manual MACD calculation"""
        ema_fast = self._manual_ema(close, fastperiod)
        ema_slow = self._manual_ema(close, slowperiod)
        macd_line = ema_fast - ema_slow
        macd_signal = self._manual_ema(macd_line, signalperiod)
        macd_hist = macd_line - macd_signal
        
        return macd_line, macd_signal, macd_hist
    
    def _manual_bbands(self, close: np.ndarray, timeperiod: int, nbdevup: float, nbdevdn: float) -> Tuple:
        """Manual Bollinger Bands calculation"""
        sma = self._manual_sma(close, timeperiod)
        std = np.full(len(close), np.nan)
        
        for i in range(timeperiod - 1, len(close)):
            std[i] = np.std(close[i - timeperiod + 1:i + 1])
        
        upper = sma + (std * nbdevup)
        lower = sma - (std * nbdevdn)
        
        return upper, sma, lower
    
    def get_performance_comparison(self, close: np.ndarray, iterations: int = 100) -> Dict[str, Dict]:
        """Compare performance of different indicator libraries"""
        results = {}
        
        # Test data
        test_close = close[-100:] if len(close) > 100 else close
        
        indicators_to_test = [
            ("SMA", lambda: self.SMA(test_close, 20)),
            ("EMA", lambda: self.EMA(test_close, 20)),
            ("RSI", lambda: self.RSI(test_close, 14)),
        ]
        
        for name, func in indicators_to_test:
            times = []
            success_count = 0
            
            for _ in range(iterations):
                try:
                    result = func()
                    if result.success:
                        times.append(result.calculation_time)
                        success_count += 1
                except Exception:
                    pass
            
            if times:
                results[name] = {
                    "avg_time": np.mean(times),
                    "min_time": np.min(times),
                    "max_time": np.max(times),
                    "success_rate": success_count / iterations,
                    "library_used": result.library_used.value if 'result' in locals() else "unknown"
                }
        
        return results
    
    def get_library_status(self) -> Dict[str, Any]:
        """Get status of available indicator libraries"""
        return {
            "talib_available": TALIB_AVAILABLE,
            "ta_available": TA_AVAILABLE,
            "fallback_available": FALLBACK_AVAILABLE,
            "preferred_library": "talib" if self.prefer_talib and TALIB_AVAILABLE else "ta",
            "supported_indicators": [
                "SMA", "EMA", "RSI", "MACD", "BBANDS", "STOCH",
                "VW_SMA", "VW_MACD"  # Volume-weighted indicators
            ]
        }


def create_indicator_engine(prefer_talib: bool = True) -> TechnicalIndicators:
    """Factory function to create indicator engine"""
    return TechnicalIndicators(prefer_talib=prefer_talib)


def test_enhanced_indicators():
    """Test enhanced indicators with sample data"""
    print("Testing Enhanced Technical Indicators...")
    print("=" * 50)
    
    # Create indicator engine
    indicators = TechnicalIndicators(prefer_talib=True)
    
    # Print library status
    status = indicators.get_library_status()
    print("Library Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    print()
    
    # Generate sample data
    np.random.seed(42)
    prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    volumes = np.random.randint(1000, 10000, 200)
    
    # Test standard indicators
    print("Testing Standard Indicators:")
    
    sma_result = indicators.SMA(prices, 20)
    print(f"SMA(20): Success={sma_result.success}, Library={sma_result.library_used.value}, "
          f"Time={sma_result.calculation_time:.6f}s")
    
    ema_result = indicators.EMA(prices, 20)
    print(f"EMA(20): Success={ema_result.success}, Library={ema_result.library_used.value}, "
          f"Time={ema_result.calculation_time:.6f}s")
    
    rsi_result = indicators.RSI(prices, 14)
    print(f"RSI(14): Success={rsi_result.success}, Library={rsi_result.library_used.value}, "
          f"Time={rsi_result.calculation_time:.6f}s")
    
    # Test volume-weighted indicators
    print("\nTesting Volume-Weighted Indicators:")
    
    vw_sma_result = indicators.VW_SMA(prices, volumes, 20)
    print(f"VW_SMA(20): Success={vw_sma_result.success}, "
          f"Time={vw_sma_result.calculation_time:.6f}s")
    
    vw_macd_result = indicators.VW_MACD(prices, volumes)
    print(f"VW_MACD: Success={vw_macd_result.success}")
    
    # Performance comparison
    print("\nPerformance Comparison:")
    perf_results = indicators.get_performance_comparison(prices, iterations=50)
    for indicator, stats in perf_results.items():
        print(f"{indicator}: Avg={stats['avg_time']:.6f}s, Success Rate={stats['success_rate']:.2%}")
    
    print("\nEnhanced indicators test completed!")


if __name__ == "__main__":
    test_enhanced_indicators()