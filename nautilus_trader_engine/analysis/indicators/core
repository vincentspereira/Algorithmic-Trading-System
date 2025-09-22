"""Consolidated Technical Indicators Module

This module provides unified implementations of technical indicators,
consolidating redundant implementations across the codebase.
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import cupy as cp
    CUDA_AVAILABLE = True
except ImportError:
    CUDA_AVAILABLE = False
    cp = None

try:
    from numba import jit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    jit = lambda *args, **kwargs: lambda f: f


class IndicatorEngine(Enum):
    """Available computation engines for indicators"""
    PANDAS = "pandas"
    NUMBA = "numba"
    CUDA = "cuda"
    AUTO = "auto"


@dataclass
class IndicatorResult:
    """Result container for technical indicators"""
    value: Union[pd.Series, np.ndarray]
    signal: str
    strength: float
    metadata: Optional[Dict[str, Any]] = None


class ConsolidatedIndicators:
    """Unified technical indicators with multiple computation backends"""
    
    @staticmethod
    def _alpha(period: int) -> float:
        """Calculate alpha for EMA calculations"""
        return 1.0 / period
    
    @staticmethod
    def _safe_last(series: pd.Series) -> float:
        """Safely get last value from series"""
        return series.iloc[-1] if len(series) > 0 and pd.notna(series.iloc[-1]) else np.nan
    
    @staticmethod
    def _choose_engine(data_size: int, engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorEngine:
        """Choose optimal computation engine based on data size and availability"""
        if engine != IndicatorEngine.AUTO:
            return engine
        
        if data_size > 10000 and CUDA_AVAILABLE:
            return IndicatorEngine.CUDA
        elif data_size > 1000 and NUMBA_AVAILABLE:
            return IndicatorEngine.NUMBA
        else:
            return IndicatorEngine.PANDAS
    
    @staticmethod
    def rsi(close: Union[pd.Series, np.ndarray], 
            period: int = 14, 
            engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Relative Strength Index with multiple computation backends
        
        Args:
            close: Price series
            period: RSI period (default 14)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with RSI values, signal, and strength
        """
        if isinstance(close, pd.Series):
            data_size = len(close)
            chosen_engine = ConsolidatedIndicators._choose_engine(data_size, engine)
            
            if chosen_engine == IndicatorEngine.CUDA and CUDA_AVAILABLE:
                return ConsolidatedIndicators._rsi_cuda(close, period)
            elif chosen_engine == IndicatorEngine.NUMBA and NUMBA_AVAILABLE:
                return ConsolidatedIndicators._rsi_numba(close, period)
            else:
                return ConsolidatedIndicators._rsi_pandas(close, period)
        else:
            # Convert numpy array to pandas series for consistency
            close_series = pd.Series(close)
            return ConsolidatedIndicators.rsi(close_series, period, engine)
    
    @staticmethod
    def _rsi_pandas(close: pd.Series, period: int = 14) -> IndicatorResult:
        """Pandas-based RSI implementation"""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        alpha = ConsolidatedIndicators._alpha(period)
        avg_gain = gain.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
        
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        
        last_rsi = ConsolidatedIndicators._safe_last(rsi)
        signal = "neutral"
        if np.isfinite(last_rsi):
            if last_rsi > 70:
                signal = "sell"
            elif last_rsi < 30:
                signal = "buy"
        
        strength = 0.0 if not np.isfinite(last_rsi) else abs(last_rsi - 50.0) / 50.0
        
        return IndicatorResult(
            value=rsi,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period}
        )
    
    @staticmethod
    def _rsi_numba(close: pd.Series, period: int = 14) -> IndicatorResult:
        """Numba-accelerated RSI implementation"""
        if not NUMBA_AVAILABLE:
            return ConsolidatedIndicators._rsi_pandas(close, period)
        
        prices = close.values
        rsi_values = ConsolidatedIndicators._rsi_numba_kernel(prices, period)
        
        # Create result series with proper index
        rsi_series = pd.Series(index=close.index[period:], data=rsi_values)
        
        last_rsi = ConsolidatedIndicators._safe_last(rsi_series)
        signal = "neutral"
        if np.isfinite(last_rsi):
            if last_rsi > 70:
                signal = "sell"
            elif last_rsi < 30:
                signal = "buy"
        
        strength = 0.0 if not np.isfinite(last_rsi) else abs(last_rsi - 50.0) / 50.0
        
        return IndicatorResult(
            value=rsi_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "numba", "period": period}
        )
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def _rsi_numba_kernel(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Numba JIT kernel for RSI calculation"""
        n = len(prices)
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        
        # Calculate initial averages
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        rsi = np.empty(n - period, dtype=np.float64)
        
        for i in range(len(rsi)):
            if i == 0:
                rs = avg_gain / (avg_loss + 1e-10)
            else:
                # Exponential moving average
                alpha = 1.0 / period
                avg_gain = alpha * gains[period + i - 1] + (1 - alpha) * avg_gain
                avg_loss = alpha * losses[period + i - 1] + (1 - alpha) * avg_loss
                rs = avg_gain / (avg_loss + 1e-10)
            
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))
        
        return rsi
    
    @staticmethod
    def _rsi_cuda(close: pd.Series, period: int = 14) -> IndicatorResult:
        """CUDA-accelerated RSI implementation"""
        if not CUDA_AVAILABLE:
            return ConsolidatedIndicators._rsi_numba(close, period)
        
        prices_gpu = cp.asarray(close.values)
        rsi_values = ConsolidatedIndicators._rsi_cuda_kernel(prices_gpu, period)
        rsi_cpu = cp.asnumpy(rsi_values)
        
        # Create result series with proper index
        rsi_series = pd.Series(index=close.index[period:], data=rsi_cpu)
        
        last_rsi = ConsolidatedIndicators._safe_last(rsi_series)
        signal = "neutral"
        if np.isfinite(last_rsi):
            if last_rsi > 70:
                signal = "sell"
            elif last_rsi < 30:
                signal = "buy"
        
        strength = 0.0 if not np.isfinite(last_rsi) else abs(last_rsi - 50.0) / 50.0
        
        return IndicatorResult(
            value=rsi_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "cuda", "period": period}
        )
    
    @staticmethod
    def _rsi_cuda_kernel(prices, period: int = 14):
        """CUDA kernel for RSI calculation"""
        # Calculate price changes
        deltas = cp.diff(prices)
        
        # Separate gains and losses
        gains = cp.where(deltas > 0, deltas, 0)
        losses = cp.where(deltas < 0, -deltas, 0)
        
        # Calculate average gains and losses using exponential moving average
        alpha = 1.0 / period
        n = len(gains)
        
        avg_gains = cp.zeros(n)
        avg_losses = cp.zeros(n)
        
        # Initialize first values
        avg_gains[period-1] = cp.mean(gains[:period])
        avg_losses[period-1] = cp.mean(losses[:period])
        
        # Calculate exponential moving averages
        for i in range(period, n):
            avg_gains[i] = alpha * gains[i] + (1 - alpha) * avg_gains[i-1]
            avg_losses[i] = alpha * losses[i] + (1 - alpha) * avg_losses[i-1]
        
        # Calculate RSI
        rs = avg_gains[period-1:] / (avg_losses[period-1:] + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def vw_rsi(close: pd.Series, volume: pd.Series, period: int = 14, 
               engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted RSI
        
        Args:
            close: Price series
            volume: Volume series
            period: RSI period (default 14)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with volume-weighted RSI values
        """
        # Compute volume-weighted price using EMA ratio
        alpha = ConsolidatedIndicators._alpha(period)
        numerator = (close * volume).ewm(alpha=alpha, adjust=False, min_periods=1).mean()
        denominator = volume.ewm(alpha=alpha, adjust=False, min_periods=1).mean()
        vw_price = numerator / denominator.replace(0, np.nan)
        
        # Apply RSI to volume-weighted price
        result = ConsolidatedIndicators.rsi(vw_price, period, engine)
        result.metadata = result.metadata or {}
        result.metadata.update({"volume_weighted": True})
        
        return result
    
    @staticmethod
    def macd(close: Union[pd.Series, np.ndarray], 
             fast: int = 12, slow: int = 26, signal_period: int = 9,
             engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Moving Average Convergence Divergence (MACD)
        
        Args:
            close: Price series
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with MACD line, signal line, and histogram
        """
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        
        data_size = len(close)
        chosen_engine = ConsolidatedIndicators._choose_engine(data_size, engine)
        
        if chosen_engine == IndicatorEngine.NUMBA and NUMBA_AVAILABLE:
            return ConsolidatedIndicators._macd_numba(close, fast, slow, signal_period)
        else:
            return ConsolidatedIndicators._macd_pandas(close, fast, slow, signal_period)
    
    @staticmethod
    def _macd_pandas(close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> IndicatorResult:
        """Pandas-based MACD implementation"""
        alpha_fast = ConsolidatedIndicators._alpha(fast)
        alpha_slow = ConsolidatedIndicators._alpha(slow)
        alpha_signal = ConsolidatedIndicators._alpha(signal_period)
        
        ema_fast = close.ewm(alpha=alpha_fast, adjust=False, min_periods=1).mean()
        ema_slow = close.ewm(alpha=alpha_slow, adjust=False, min_periods=1).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(alpha=alpha_signal, adjust=False, min_periods=1).mean()
        histogram = macd_line - signal_line
        
        last_macd = ConsolidatedIndicators._safe_last(macd_line)
        last_signal = ConsolidatedIndicators._safe_last(signal_line)
        last_histogram = ConsolidatedIndicators._safe_last(histogram)
        
        signal = "neutral"
        if np.isfinite(last_macd) and np.isfinite(last_signal):
            if last_macd > last_signal and last_histogram > 0:
                signal = "buy"
            elif last_macd < last_signal and last_histogram < 0:
                signal = "sell"
        
        strength = 0.0 if not np.isfinite(last_histogram) else min(abs(last_histogram) / abs(last_macd + 1e-10), 1.0)
        
        return IndicatorResult(
            value=pd.DataFrame({
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }),
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "fast": fast, "slow": slow, "signal_period": signal_period}
        )
    
    @staticmethod
    def _macd_numba(close: pd.Series, fast: int = 12, slow: int = 26, signal_period: int = 9) -> IndicatorResult:
        """Numba-accelerated MACD implementation"""
        if not NUMBA_AVAILABLE:
            return ConsolidatedIndicators._macd_pandas(close, fast, slow, signal_period)
        
        prices = close.values
        macd_data = ConsolidatedIndicators._macd_numba_kernel(prices, fast, slow, signal_period)
        
        macd_df = pd.DataFrame({
            'macd': macd_data[0],
            'signal': macd_data[1],
            'histogram': macd_data[2]
        }, index=close.index)
        
        last_macd = macd_data[0][-1] if len(macd_data[0]) > 0 else np.nan
        last_signal = macd_data[1][-1] if len(macd_data[1]) > 0 else np.nan
        last_histogram = macd_data[2][-1] if len(macd_data[2]) > 0 else np.nan
        
        signal = "neutral"
        if np.isfinite(last_macd) and np.isfinite(last_signal):
            if last_macd > last_signal and last_histogram > 0:
                signal = "buy"
            elif last_macd < last_signal and last_histogram < 0:
                signal = "sell"
        
        strength = 0.0 if not np.isfinite(last_histogram) else min(abs(last_histogram) / abs(last_macd + 1e-10), 1.0)
        
        return IndicatorResult(
            value=macd_df,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "numba", "fast": fast, "slow": slow, "signal_period": signal_period}
        )
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def _macd_numba_kernel(prices: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Numba JIT kernel for MACD calculation"""
        n = len(prices)
        
        # Calculate EMAs
        alpha_fast = 1.0 / fast
        alpha_slow = 1.0 / slow
        alpha_signal = 1.0 / signal_period
        
        ema_fast = np.empty(n)
        ema_slow = np.empty(n)
        
        # Initialize first values
        ema_fast[0] = prices[0]
        ema_slow[0] = prices[0]
        
        # Calculate EMAs
        for i in range(1, n):
            ema_fast[i] = alpha_fast * prices[i] + (1 - alpha_fast) * ema_fast[i-1]
            ema_slow[i] = alpha_slow * prices[i] + (1 - alpha_slow) * ema_slow[i-1]
        
        # Calculate MACD line
        macd_line = ema_fast - ema_slow
        
        # Calculate signal line
        signal_line = np.empty(n)
        signal_line[0] = macd_line[0]
        
        for i in range(1, n):
            signal_line[i] = alpha_signal * macd_line[i] + (1 - alpha_signal) * signal_line[i-1]
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def vw_macd(close: pd.Series, volume: pd.Series, 
                fast: int = 12, slow: int = 26, signal_period: int = 9,
                engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted MACD
        
        Args:
            close: Price series
            volume: Volume series
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal_period: Signal line EMA period (default 9)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with volume-weighted MACD
        """
        # Compute volume-weighted price
        alpha_fast = ConsolidatedIndicators._alpha(fast)
        alpha_slow = ConsolidatedIndicators._alpha(slow)
        
        # Volume-weighted fast EMA
        num_fast = (close * volume).ewm(alpha=alpha_fast, adjust=False, min_periods=1).mean()
        den_fast = volume.ewm(alpha=alpha_fast, adjust=False, min_periods=1).mean()
        vw_ema_fast = num_fast / den_fast.replace(0, np.nan)
        
        # Volume-weighted slow EMA
        num_slow = (close * volume).ewm(alpha=alpha_slow, adjust=False, min_periods=1).mean()
        den_slow = volume.ewm(alpha=alpha_slow, adjust=False, min_periods=1).mean()
        vw_ema_slow = num_slow / den_slow.replace(0, np.nan)
        
        # Apply MACD to volume-weighted EMAs
        vw_macd_line = vw_ema_fast - vw_ema_slow
        alpha_signal = ConsolidatedIndicators._alpha(signal_period)
        vw_signal_line = vw_macd_line.ewm(alpha=alpha_signal, adjust=False, min_periods=1).mean()
        vw_histogram = vw_macd_line - vw_signal_line
        
        last_macd = ConsolidatedIndicators._safe_last(vw_macd_line)
        last_signal = ConsolidatedIndicators._safe_last(vw_signal_line)
        last_histogram = ConsolidatedIndicators._safe_last(vw_histogram)
        
        signal = "neutral"
        if np.isfinite(last_macd) and np.isfinite(last_signal):
            if last_macd > last_signal and last_histogram > 0:
                signal = "buy"
            elif last_macd < last_signal and last_histogram < 0:
                signal = "sell"
        
        strength = 0.0 if not np.isfinite(last_histogram) else min(abs(last_histogram) / abs(last_macd + 1e-10), 1.0)
        
        return IndicatorResult(
            value=pd.DataFrame({
                'macd': vw_macd_line,
                'signal': vw_signal_line,
                'histogram': vw_histogram
            }),
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "volume_weighted": True, "fast": fast, "slow": slow, "signal_period": signal_period}
        )
    
    @staticmethod
    def bollinger_bands(close: Union[pd.Series, np.ndarray], 
                       window: int = 20, num_std: float = 2.0,
                       engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Bollinger Bands
        
        Args:
            close: Price series
            window: Moving average window (default 20)
            num_std: Number of standard deviations (default 2.0)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with upper band, middle band (SMA), and lower band
        """
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        
        data_size = len(close)
        chosen_engine = ConsolidatedIndicators._choose_engine(data_size, engine)
        
        if chosen_engine == IndicatorEngine.CUDA and CUDA_AVAILABLE:
            return ConsolidatedIndicators._bollinger_bands_cuda(close, window, num_std)
        elif chosen_engine == IndicatorEngine.NUMBA and NUMBA_AVAILABLE:
            return ConsolidatedIndicators._bollinger_bands_numba(close, window, num_std)
        else:
            return ConsolidatedIndicators._bollinger_bands_pandas(close, window, num_std)
    
    @staticmethod
    def _bollinger_bands_pandas(close: pd.Series, window: int = 20, num_std: float = 2.0) -> IndicatorResult:
        """Pandas-based Bollinger Bands implementation"""
        sma = close.rolling(window=window, min_periods=window).mean()
        std = close.rolling(window=window, min_periods=window).std()
        
        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)
        
        last_close = ConsolidatedIndicators._safe_last(close)
        last_upper = ConsolidatedIndicators._safe_last(upper_band)
        last_lower = ConsolidatedIndicators._safe_last(lower_band)
        last_sma = ConsolidatedIndicators._safe_last(sma)
        
        signal = "neutral"
        strength = 0.0
        
        if all(np.isfinite([last_close, last_upper, last_lower, last_sma])):
            band_width = last_upper - last_lower
            if last_close >= last_upper:
                signal = "sell"
                strength = min((last_close - last_upper) / band_width, 1.0)
            elif last_close <= last_lower:
                signal = "buy"
                strength = min((last_lower - last_close) / band_width, 1.0)
            else:
                # Calculate position within bands for strength
                position = (last_close - last_lower) / band_width
                strength = abs(position - 0.5) * 2  # 0 at center, 1 at edges
        
        return IndicatorResult(
            value=pd.DataFrame({
                'upper': upper_band,
                'middle': sma,
                'lower': lower_band
            }),
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "window": window, "num_std": num_std}
        )
    
    @staticmethod
    def _bollinger_bands_numba(close: pd.Series, window: int = 20, num_std: float = 2.0) -> IndicatorResult:
        """Numba-accelerated Bollinger Bands implementation"""
        if not NUMBA_AVAILABLE:
            return ConsolidatedIndicators._bollinger_bands_pandas(close, window, num_std)
        
        prices = close.values
        bb_data = ConsolidatedIndicators._bollinger_bands_numba_kernel(prices, window, num_std)
        
        bb_df = pd.DataFrame({
            'upper': bb_data[0],
            'middle': bb_data[1],
            'lower': bb_data[2]
        }, index=close.index[window-1:])
        
        last_close = prices[-1]
        last_upper = bb_data[0][-1] if len(bb_data[0]) > 0 else np.nan
        last_lower = bb_data[2][-1] if len(bb_data[2]) > 0 else np.nan
        last_middle = bb_data[1][-1] if len(bb_data[1]) > 0 else np.nan
        
        signal = "neutral"
        strength = 0.0
        
        if all(np.isfinite([last_close, last_upper, last_lower, last_middle])):
            band_width = last_upper - last_lower
            if last_close >= last_upper:
                signal = "sell"
                strength = min((last_close - last_upper) / band_width, 1.0)
            elif last_close <= last_lower:
                signal = "buy"
                strength = min((last_lower - last_close) / band_width, 1.0)
            else:
                position = (last_close - last_lower) / band_width
                strength = abs(position - 0.5) * 2
        
        return IndicatorResult(
            value=bb_df,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "numba", "window": window, "num_std": num_std}
        )
    
    @staticmethod
    @jit(nopython=True, cache=True)
    def _bollinger_bands_numba_kernel(prices: np.ndarray, window: int = 20, num_std: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Numba JIT kernel for Bollinger Bands calculation"""
        n = len(prices)
        result_len = n - window + 1
        
        upper_band = np.empty(result_len)
        middle_band = np.empty(result_len)
        lower_band = np.empty(result_len)
        
        for i in range(result_len):
            window_data = prices[i:i + window]
            mean_val = np.mean(window_data)
            std_val = np.std(window_data)
            
            middle_band[i] = mean_val
            upper_band[i] = mean_val + (std_val * num_std)
            lower_band[i] = mean_val - (std_val * num_std)
        
        return upper_band, middle_band, lower_band
    
    @staticmethod
    def sma(close: Union[pd.Series, np.ndarray], period: int = 20,
            engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Simple Moving Average
        
        Args:
            close: Price series
            period: SMA period (default 20)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with SMA values, signal, and strength
        """
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        
        sma_series = close.rolling(window=period, min_periods=1).mean()
        last_close = ConsolidatedIndicators._safe_last(close)
        last_sma = ConsolidatedIndicators._safe_last(sma_series)
        
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_sma) and last_sma != 0:
            if last_close > last_sma:
                signal = "buy"
            elif last_close < last_sma:
                signal = "sell"
        
        strength = 0.0 if not np.isfinite(last_sma) or last_sma == 0 else abs(last_close - last_sma) / abs(last_sma)
        
        return IndicatorResult(
            value=sma_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period}
        )
    
    @staticmethod
    def vwma(close: Union[pd.Series, np.ndarray], volume: Union[pd.Series, np.ndarray], 
             period: int = 20, engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted Moving Average
        
        Args:
            close: Price series
            volume: Volume series
            period: VWMA period (default 20)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with VWMA values, signal, and strength
        """
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        if isinstance(volume, np.ndarray):
            volume = pd.Series(volume)
        
        vol_sum = volume.rolling(window=period, min_periods=1).sum()
        pv_sum = (close * volume).rolling(window=period, min_periods=1).sum()
        vwma_series = pv_sum / vol_sum.replace(0, np.nan)
        
        last_close = ConsolidatedIndicators._safe_last(close)
        last_vwma = ConsolidatedIndicators._safe_last(vwma_series)
        
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_vwma):
            signal = "buy" if last_close > last_vwma else "sell" if last_close < last_vwma else "neutral"
        
        strength = 0.0 if not np.isfinite(last_vwma) or last_vwma == 0 else abs(last_close - last_vwma) / abs(last_vwma)
        
        return IndicatorResult(
            value=vwma_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period, "volume_weighted": True}
        )
    
    @staticmethod
    def vw_ema(close: Union[pd.Series, np.ndarray], volume: Union[pd.Series, np.ndarray], 
               period: int = 20, engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted Exponential Moving Average
        
        Args:
            close: Price series
            volume: Volume series
            period: EMA period (default 20)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with VW EMA values, signal, and strength
        """
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        if isinstance(volume, np.ndarray):
            volume = pd.Series(volume)
        
        alpha = ConsolidatedIndicators._calculate_alpha(period)
        
        # Volume-weighted price calculation
        vw_price = (close * volume).ewm(alpha=alpha, adjust=False).mean() / volume.ewm(alpha=alpha, adjust=False).mean()
        
        last_close = ConsolidatedIndicators._safe_last(close)
        last_vw_ema = ConsolidatedIndicators._safe_last(vw_price)
        
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_vw_ema):
            signal = "buy" if last_close > last_vw_ema else "sell" if last_close < last_vw_ema else "neutral"
        
        strength = 0.0 if not np.isfinite(last_vw_ema) or last_vw_ema == 0 else abs(last_close - last_vw_ema) / abs(last_vw_ema)
        
        return IndicatorResult(
            value=vw_price,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period, "volume_weighted": True}
        )
    
    @staticmethod
    def atr(high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], 
            close: Union[pd.Series, np.ndarray], period: int = 14,
            engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Average True Range
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            period: ATR period (default 14)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with ATR values, signal, and strength
        """
        if isinstance(high, np.ndarray):
            high = pd.Series(high)
        if isinstance(low, np.ndarray):
            low = pd.Series(low)
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        
        # True Range calculation
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr_series = true_range.ewm(span=period, adjust=False).mean()
        
        last_atr = ConsolidatedIndicators._safe_last(atr_series)
        last_close = ConsolidatedIndicators._safe_last(close)
        
        # ATR signal based on volatility level
        signal = "neutral"
        strength = 0.0
        
        if np.isfinite(last_atr) and np.isfinite(last_close) and last_close > 0:
            atr_pct = last_atr / last_close
            if atr_pct > 0.03:  # High volatility
                signal = "high_volatility"
                strength = min(atr_pct / 0.05, 1.0)
            elif atr_pct < 0.01:  # Low volatility
                signal = "low_volatility"
                strength = min((0.01 - atr_pct) / 0.01, 1.0)
        
        return IndicatorResult(
            value=atr_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period}
        )
    
    @staticmethod
    def vw_atr(high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], 
               close: Union[pd.Series, np.ndarray], volume: Union[pd.Series, np.ndarray],
               period: int = 14, engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted Average True Range
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            volume: Volume series
            period: ATR period (default 14)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with VW ATR values, signal, and strength
        """
        if isinstance(high, np.ndarray):
            high = pd.Series(high)
        if isinstance(low, np.ndarray):
            low = pd.Series(low)
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        if isinstance(volume, np.ndarray):
            volume = pd.Series(volume)
        
        # True Range calculation
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Volume-weighted ATR
        alpha = ConsolidatedIndicators._calculate_alpha(period)
        vw_atr_series = (true_range * volume).ewm(alpha=alpha, adjust=False).mean() / volume.ewm(alpha=alpha, adjust=False).mean()
        
        last_vw_atr = ConsolidatedIndicators._safe_last(vw_atr_series)
        last_close = ConsolidatedIndicators._safe_last(close)
        
        # VW ATR signal based on volume-weighted volatility
        signal = "neutral"
        strength = 0.0
        
        if np.isfinite(last_vw_atr) and np.isfinite(last_close) and last_close > 0:
            vw_atr_pct = last_vw_atr / last_close
            if vw_atr_pct > 0.03:  # High volume-weighted volatility
                signal = "high_volatility"
                strength = min(vw_atr_pct / 0.05, 1.0)
            elif vw_atr_pct < 0.01:  # Low volume-weighted volatility
                signal = "low_volatility"
                strength = min((0.01 - vw_atr_pct) / 0.01, 1.0)
        
        return IndicatorResult(
            value=vw_atr_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period, "volume_weighted": True}
        )
    
    @staticmethod
    def vw_atrp(high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], 
                close: Union[pd.Series, np.ndarray], volume: Union[pd.Series, np.ndarray],
                period: int = 14, engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted Average True Range Percentage (Normalized ATR)
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            volume: Volume series
            period: ATR period (default 14)
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with VW ATRP values, signal, and strength
        """
        vw_atr_result = ConsolidatedIndicators.vw_atr(high, low, close, volume, period, engine)
        
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        
        # Normalize ATR by close price to get percentage
        vw_atrp_series = (vw_atr_result.value / close) * 100
        
        last_vw_atrp = ConsolidatedIndicators._safe_last(vw_atrp_series)
        
        # ATRP signal based on normalized volatility
        signal = "neutral"
        strength = 0.0
        
        if np.isfinite(last_vw_atrp):
            if last_vw_atrp > 3.0:  # High normalized volatility (>3%)
                signal = "high_volatility"
                strength = min(last_vw_atrp / 5.0, 1.0)
            elif last_vw_atrp < 1.0:  # Low normalized volatility (<1%)
                signal = "low_volatility"
                strength = min((1.0 - last_vw_atrp) / 1.0, 1.0)
        
        return IndicatorResult(
            value=vw_atrp_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "period": period, "volume_weighted": True, "normalized": True}
        )
    
    @staticmethod
    def vwap(high: Union[pd.Series, np.ndarray], low: Union[pd.Series, np.ndarray], 
             close: Union[pd.Series, np.ndarray], volume: Union[pd.Series, np.ndarray],
             engine: IndicatorEngine = IndicatorEngine.AUTO) -> IndicatorResult:
        """Volume-Weighted Average Price
        
        Args:
            high: High price series
            low: Low price series
            close: Close price series
            volume: Volume series
            engine: Computation engine to use
            
        Returns:
            IndicatorResult with VWAP values, signal, and strength
        """
        if isinstance(high, np.ndarray):
            high = pd.Series(high)
        if isinstance(low, np.ndarray):
            low = pd.Series(low)
        if isinstance(close, np.ndarray):
            close = pd.Series(close)
        if isinstance(volume, np.ndarray):
            volume = pd.Series(volume)
        
        # Typical price calculation
        typical_price = (high + low + close) / 3
        
        # VWAP calculation
        cumulative_pv = (typical_price * volume).cumsum()
        cumulative_volume = volume.cumsum()
        vwap_series = cumulative_pv / cumulative_volume.replace(0, np.nan)
        
        last_close = ConsolidatedIndicators._safe_last(close)
        last_vwap = ConsolidatedIndicators._safe_last(vwap_series)
        
        signal = "neutral"
        if np.isfinite(last_close) and np.isfinite(last_vwap):
            signal = "buy" if last_close > last_vwap else "sell" if last_close < last_vwap else "neutral"
        
        strength = 0.0 if not np.isfinite(last_vwap) or last_vwap == 0 else abs(last_close - last_vwap) / abs(last_vwap)
        
        return IndicatorResult(
            value=vwap_series,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "pandas", "volume_weighted": True}
        )
    
    @staticmethod
    def _bollinger_bands_cuda(close: pd.Series, window: int = 20, num_std: float = 2.0) -> IndicatorResult:
        """CUDA-accelerated Bollinger Bands implementation"""
        if not CUDA_AVAILABLE:
            return ConsolidatedIndicators._bollinger_bands_numba(close, window, num_std)
        
        prices_gpu = cp.asarray(close.values)
        bb_data = ConsolidatedIndicators._bollinger_bands_cuda_kernel(prices_gpu, window, num_std)
        
        # Convert back to CPU
        upper_cpu = cp.asnumpy(bb_data[0])
        middle_cpu = cp.asnumpy(bb_data[1])
        lower_cpu = cp.asnumpy(bb_data[2])
        
        bb_df = pd.DataFrame({
            'upper': upper_cpu,
            'middle': middle_cpu,
            'lower': lower_cpu
        }, index=close.index[window-1:])
        
        last_close = close.iloc[-1]
        last_upper = upper_cpu[-1] if len(upper_cpu) > 0 else np.nan
        last_lower = lower_cpu[-1] if len(lower_cpu) > 0 else np.nan
        last_middle = middle_cpu[-1] if len(middle_cpu) > 0 else np.nan
        
        signal = "neutral"
        strength = 0.0
        
        if all(np.isfinite([last_close, last_upper, last_lower, last_middle])):
            band_width = last_upper - last_lower
            if last_close >= last_upper:
                signal = "sell"
                strength = min((last_close - last_upper) / band_width, 1.0)
            elif last_close <= last_lower:
                signal = "buy"
                strength = min((last_lower - last_close) / band_width, 1.0)
            else:
                position = (last_close - last_lower) / band_width
                strength = abs(position - 0.5) * 2
        
        return IndicatorResult(
            value=bb_df,
            signal=signal,
            strength=float(np.clip(strength, 0.0, 1.0)),
            metadata={"engine": "cuda", "window": window, "num_std": num_std}
        )
    
    @staticmethod
    def _bollinger_bands_cuda_kernel(prices, window: int = 20, num_std: float = 2.0):
        """CUDA kernel for Bollinger Bands calculation"""
        n = len(prices)
        result_len = n - window + 1
        
        # Calculate moving average
        kernel = cp.ones(window, dtype=prices.dtype) / window
        middle_band = cp.convolve(prices, kernel, mode='valid')
        
        # Calculate rolling standard deviation
        upper_band = cp.empty(result_len)
        lower_band = cp.empty(result_len)
        
        for i in range(result_len):
            window_data = prices[i:i + window]
            std_val = cp.std(window_data)
            upper_band[i] = middle_band[i] + (std_val * num_std)
            lower_band[i] = middle_band[i] - (std_val * num_std)
        
        return upper_band, middle_band, lower_band