"""Base classes and utilities for volume-weighted technical indicators

Enhanced with high-frequency trading optimizations, robust error handling,
memory management, and performance monitoring for institutional-grade trading systems.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union
import logging
import time
import gc
import threading
from collections import deque
from functools import wraps
import warnings

import numpy as np
import pandas as pd

# Optional imports
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    talib = None

try:
    from nautilus_trader.model.data import Bar
    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False
    # Mock Bar class
    class Bar:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

logger = logging.getLogger(__name__)

# Performance optimization constants for HFT
HFT_MAX_MEMORY_ITEMS = 10000  # Maximum items to keep in memory
HFT_BATCH_SIZE = 1000  # Batch processing size
HFT_GC_THRESHOLD = 5000  # Garbage collection threshold
HFT_PERFORMANCE_WARNING_MS = 1.0  # Performance warning threshold

# Thread-local storage for HFT optimizations
_thread_local = threading.local()

def performance_monitor(func):
    """Decorator for monitoring indicator performance in HFT environments"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.perf_counter() - start_time
            
            # Track performance metrics
            if hasattr(self, 'calculation_times'):
                self.calculation_times.append(execution_time)
                
                # Memory management for HFT
                if len(self.calculation_times) > HFT_MAX_MEMORY_ITEMS:
                    self.calculation_times = self.calculation_times[-HFT_MAX_MEMORY_ITEMS//2:]
            
            # Performance warning for HFT
            if execution_time * 1000 > HFT_PERFORMANCE_WARNING_MS:
                logger.warning(f"{func.__name__} took {execution_time*1000:.2f}ms - may impact HFT performance")
            
            return result
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(f"Error in {func.__name__} after {execution_time*1000:.2f}ms: {str(e)}")
            if hasattr(self, 'error_count'):
                self.error_count += 1
            raise
    return wrapper

def robust_calculation(default_value=None, log_errors=True):
    """Decorator for robust error handling in indicator calculations"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except (ValueError, ZeroDivisionError, IndexError, TypeError) as e:
                if log_errors:
                    logger.warning(f"Calculation error in {func.__name__}: {str(e)} - using default value")
                if hasattr(self, 'error_count'):
                    self.error_count += 1
                return default_value
            except Exception as e:
                if log_errors:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
                if hasattr(self, 'error_count'):
                    self.error_count += 1
                raise
        return wrapper
    return decorator

def memory_efficient(max_items=HFT_MAX_MEMORY_ITEMS):
    """Decorator for memory-efficient data management in HFT environments"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            
            # Memory management for lists
            for attr_name in ['prices', 'volumes', 'results', 'timestamps']:
                if hasattr(self, attr_name):
                    attr_list = getattr(self, attr_name)
                    if isinstance(attr_list, list) and len(attr_list) > max_items:
                        # Keep only the most recent items
                        setattr(self, attr_name, attr_list[-max_items//2:])
            
            # Periodic garbage collection for HFT
            if hasattr(self, 'count') and self.count % HFT_GC_THRESHOLD == 0:
                gc.collect()
            
            return result
        return wrapper
    return decorator

class IndicatorType(Enum):
    """Enumeration of indicator types for categorization"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OSCILLATOR = "oscillator"
    CUSTOM = "custom"

class SignalType(Enum):
    """Enumeration of trading signal types"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class IndicatorConfig:
    """Enhanced configuration class for indicator parameters with HFT optimizations and validation"""
    
    def __init__(self, 
                 period: int = 14,
                 signal_threshold: float = 0.01,
                 outlier_threshold: float = 3.0,
                 normalize: bool = False,
                 adaptive: bool = False,
                 use_typical_price: bool = False,
                 signal_smoothing: int = 3,
                 # HFT-specific parameters
                 hft_mode: bool = False,
                 max_memory_items: int = HFT_MAX_MEMORY_ITEMS,
                 performance_monitoring: bool = True,
                 error_recovery: bool = True,
                 batch_processing: bool = False,
                 batch_size: int = HFT_BATCH_SIZE,
                 memory_optimization: bool = True,
                 thread_safe: bool = False,
                 **kwargs):
        
        # Validate basic parameters
        if period < 1:
            raise ValueError("Period must be positive")
        if signal_threshold < 0:
            raise ValueError("Signal threshold must be non-negative")
        if outlier_threshold < 0:
            raise ValueError("Outlier threshold must be non-negative")
        if signal_smoothing < 1:
            raise ValueError("Signal smoothing must be positive")
        
        # Validate HFT parameters
        if max_memory_items < 100:
            raise ValueError("Max memory items must be at least 100")
        if batch_size < 1:
            raise ValueError("Batch size must be positive")
        
        # Basic parameters
        self.period = period
        self.signal_threshold = signal_threshold
        self.outlier_threshold = outlier_threshold
        self.normalize = normalize
        self.adaptive = adaptive
        self.use_typical_price = use_typical_price
        self.signal_smoothing = signal_smoothing
        
        # HFT-specific parameters
        self.hft_mode = hft_mode
        self.max_memory_items = max_memory_items
        self.performance_monitoring = performance_monitoring
        self.error_recovery = error_recovery
        self.batch_processing = batch_processing
        self.batch_size = batch_size
        self.memory_optimization = memory_optimization
        self.thread_safe = thread_safe
        
        # Auto-enable optimizations in HFT mode
        if hft_mode:
            self.performance_monitoring = True
            self.error_recovery = True
            self.memory_optimization = True
            self.max_memory_items = min(max_memory_items, HFT_MAX_MEMORY_ITEMS)
        
        # Store additional parameters
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        logger.debug(f"Created IndicatorConfig (HFT={hft_mode}): {self.__dict__}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return self.__dict__.copy()
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'IndicatorConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)

class IndicatorResult:
    """Container for indicator calculation results"""
    
    def __init__(self, 
                 timestamp: datetime,
                 value: float,
                 signal: SignalType = None,
                 confidence: float = 0.0,
                 upper_band: float = None,
                 lower_band: float = None,
                 signal_line: float = None,
                 histogram: float = None,
                 metadata: Dict[str, Any] = None):
        
        self.timestamp = timestamp
        self.value = value
        self.signal = signal
        self.confidence = confidence
        self.upper_band = upper_band
        self.lower_band = lower_band
        self.signal_line = signal_line
        self.histogram = histogram
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        result = {
            'timestamp': self.timestamp,
            'value': self.value,
            'confidence': self.confidence,
            'metadata': self.metadata
        }
        
        if self.signal:
            result['signal'] = self.signal.value
        if self.upper_band is not None:
            result['upper_band'] = self.upper_band
        if self.lower_band is not None:
            result['lower_band'] = self.lower_band
        if self.signal_line is not None:
            result['signal_line'] = self.signal_line
        if self.histogram is not None:
            result['histogram'] = self.histogram
            
        return result

class VolumeWeightedIndicator(ABC):
    """Enhanced abstract base class for volume-weighted technical indicators with HFT optimizations"""
    
    def __init__(self, config: IndicatorConfig, name: str = None):
        self.config = config
        self.name = name or self.__class__.__name__
        self.indicator_type = IndicatorType.CUSTOM
        
        # Data storage - use deque for HFT performance if enabled
        if config.hft_mode and config.memory_optimization:
            self.prices = deque(maxlen=config.max_memory_items)
            self.volumes = deque(maxlen=config.max_memory_items)
            self.timestamps = deque(maxlen=config.max_memory_items)
            self.results = deque(maxlen=config.max_memory_items)
        else:
            self.prices: List[float] = []
            self.volumes: List[float] = []
            self.timestamps: List[datetime] = []
            self.results: List[IndicatorResult] = []
        
        # Calculation state
        self.initialized = False
        self.count = 0
        
        # Performance tracking
        self.calculation_times = deque(maxlen=config.max_memory_items) if config.hft_mode else []
        
        # Error tracking for robust operation
        self.error_count = 0
        self.last_error_time = None
        self.consecutive_errors = 0
        
        # HFT-specific attributes
        self.batch_buffer = [] if config.batch_processing else None
        self.last_gc_count = 0
        
        # Thread safety
        self._lock = threading.Lock() if config.thread_safe else None
        
        logger.debug(f"Initialized {self.name} (HFT={config.hft_mode}) with config: {config}")
    
    @performance_monitor
    @memory_efficient()
    @robust_calculation(default_value=None)
    @abstractmethod
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate indicator value for given price and volume with HFT optimizations"""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset indicator state"""
        pass
    
    @performance_monitor
    def update(self, bar: Bar) -> Optional[IndicatorResult]:
        """Update indicator with new bar data with thread safety"""
        if self._lock:
            with self._lock:
                return self._update_internal(bar)
        else:
            return self._update_internal(bar)
    
    def _update_internal(self, bar: Bar) -> Optional[IndicatorResult]:
        """Internal update method"""
        price = self._get_price_from_bar(bar)
        volume = float(bar.volume)
        timestamp = bar.ts_init
        
        # Batch processing for HFT
        if self.config.batch_processing and self.batch_buffer is not None:
            self.batch_buffer.append((price, volume, timestamp))
            if len(self.batch_buffer) >= self.config.batch_size:
                return self._process_batch()
            return None
        
        return self.calculate(price, volume, timestamp)
    
    def _process_batch(self) -> Optional[IndicatorResult]:
        """Process batched data points"""
        if not self.batch_buffer:
            return None
        
        results = []
        for price, volume, timestamp in self.batch_buffer:
            result = self.calculate(price, volume, timestamp)
            if result:
                results.append(result)
        
        self.batch_buffer.clear()
        return results[-1] if results else None
    
    def _get_price_from_bar(self, bar: Bar) -> float:
        """Extract price from bar based on configuration"""
        if self.config.use_typical_price:
            return (float(bar.high) + float(bar.low) + float(bar.close)) / 3.0
        else:
            return float(bar.close)
    
    def _add_data_point(self, price: float, volume: float, timestamp: datetime) -> None:
        """Add new data point to internal storage with memory management"""
        # Validate input data
        if not isinstance(price, (int, float)) or not isinstance(volume, (int, float)):
            logger.warning(f"Invalid data types: price={type(price)}, volume={type(volume)}")
            return
        
        if price <= 0 or volume < 0:
            logger.warning(f"Invalid data values: price={price}, volume={volume}")
            return
        
        self.prices.append(float(price))
        self.volumes.append(float(volume))
        self.timestamps.append(timestamp)
        self.count += 1
        
        # Memory management for non-HFT mode (HFT mode uses deque with maxlen)
        if not self.config.hft_mode or not self.config.memory_optimization:
            max_length = max(self.config.period * 3, 1000)  # Keep extra data for calculations
            if len(self.prices) > max_length:
                self.prices = self.prices[-max_length:]
                self.volumes = self.volumes[-max_length:]
                self.timestamps = self.timestamps[-max_length:]
        
        # Periodic garbage collection for HFT
        if self.config.hft_mode and self.count % HFT_GC_THRESHOLD == 0:
            current_gc_count = gc.get_count()[0]
            if current_gc_count - self.last_gc_count > HFT_GC_THRESHOLD:
                gc.collect()
                self.last_gc_count = current_gc_count
    
    def _calculate_volume_weighted_average(self, prices: List[float], volumes: List[float]) -> float:
        """Calculate volume-weighted average"""
        if not prices or not volumes or len(prices) != len(volumes):
            return 0.0
        
        total_volume = sum(volumes)
        if total_volume == 0:
            return sum(prices) / len(prices)  # Simple average if no volume
        
        weighted_sum = sum(p * v for p, v in zip(prices, volumes))
        return weighted_sum / total_volume
    
    def _calculate_volume_weighted_std(self, prices: List[float], volumes: List[float], mean: float = None) -> float:
        """Calculate volume-weighted standard deviation"""
        if not prices or not volumes or len(prices) != len(volumes):
            return 0.0
        
        if mean is None:
            mean = self._calculate_volume_weighted_average(prices, volumes)
        
        total_volume = sum(volumes)
        if total_volume == 0:
            return np.std(prices)  # Simple std if no volume
        
        weighted_variance = sum(v * (p - mean) ** 2 for p, v in zip(prices, volumes)) / total_volume
        return np.sqrt(weighted_variance)
    
    def _normalize_value(self, value: float, lookback_period: int = None) -> float:
        """Normalize value using z-score"""
        if not self.config.normalize or len(self.results) < 2:
            return value
        
        period = lookback_period or self.config.period
        recent_values = [r.value for r in self.results[-period:]]
        
        if len(recent_values) < 2:
            return value
        
        mean_val = np.mean(recent_values)
        std_val = np.std(recent_values)
        
        if std_val == 0:
            return 0.0
        
        return (value - mean_val) / std_val
    
    def _detect_outliers(self, values: List[float]) -> List[bool]:
        """Detect outliers using z-score method"""
        if len(values) < 3:
            return [False] * len(values)
        
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        if std_val == 0:
            return [False] * len(values)
        
        z_scores = [(v - mean_val) / std_val for v in values]
        return [abs(z) > self.config.outlier_threshold for z in z_scores]
    
    def _generate_signal(self, current_value: float, previous_value: float = None) -> Tuple[SignalType, float]:
        """Generate trading signal based on indicator values"""
        if previous_value is None or len(self.results) < 2:
            return SignalType.NEUTRAL, 0.0
        
        # Basic signal generation logic (can be overridden in subclasses)
        change = current_value - previous_value
        abs_change = abs(change)
        
        if abs_change < self.config.signal_threshold:
            return SignalType.NEUTRAL, 0.0
        
        confidence = min(abs_change / self.config.signal_threshold, 1.0)
        
        if change > 0:
            if confidence > 0.8:
                return SignalType.STRONG_BUY, confidence
            else:
                return SignalType.BUY, confidence
        else:
            if confidence > 0.8:
                return SignalType.STRONG_SELL, confidence
            else:
                return SignalType.SELL, confidence
    
    def _smooth_signal(self, signals: List[SignalType], window: int = None) -> SignalType:
        """Smooth signal using majority vote"""
        window = window or self.config.signal_smoothing
        if len(signals) < window:
            return signals[-1] if signals else SignalType.NEUTRAL
        
        recent_signals = signals[-window:]
        signal_counts = {}
        
        for signal in recent_signals:
            signal_counts[signal] = signal_counts.get(signal, 0) + 1
        
        return max(signal_counts, key=signal_counts.get)
    
    def get_latest_result(self) -> Optional[IndicatorResult]:
        """Get the most recent indicator result"""
        return self.results[-1] if self.results else None
    
    def get_results(self, count: int = None) -> List[IndicatorResult]:
        """Get recent indicator results"""
        if count is None:
            return self.results.copy()
        return self.results[-count:] if count > 0 else []
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to pandas DataFrame"""
        if not self.results:
            return pd.DataFrame()
        
        data = []
        for result in self.results:
            row = result.to_dict()
            data.append(row)
        
        df = pd.DataFrame(data)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics"""
        stats = {
            'total_calculations': self.count,
            'error_count': self.error_count,
            'consecutive_errors': self.consecutive_errors,
            'last_error_time': self.last_error_time,
            'initialized': self.initialized,
            'hft_mode': self.config.hft_mode,
            'memory_items': len(self.prices),
            'results_count': len(self.results)
        }
        
        if self.calculation_times:
            calc_times = list(self.calculation_times) if hasattr(self.calculation_times, 'maxlen') else self.calculation_times
            stats.update({
                'timing_samples': len(calc_times),
                'avg_calculation_time_ms': np.mean(calc_times) * 1000,
                'max_calculation_time_ms': np.max(calc_times) * 1000,
                'min_calculation_time_ms': np.min(calc_times) * 1000,
                'total_time_ms': np.sum(calc_times) * 1000,
                'p95_calculation_time_ms': np.percentile(calc_times, 95) * 1000,
                'p99_calculation_time_ms': np.percentile(calc_times, 99) * 1000
            })
        
        return stats
    
    def force_gc(self) -> None:
        """Force garbage collection for memory management"""
        if self.config.hft_mode:
            gc.collect()
            self.last_gc_count = gc.get_count()[0]
            logger.debug(f"{self.name}: Forced garbage collection")
    
    def get_memory_usage(self) -> Dict[str, int]:
        """Get current memory usage statistics"""
        return {
            'prices_count': len(self.prices),
            'volumes_count': len(self.volumes),
            'timestamps_count': len(self.timestamps),
            'results_count': len(self.results),
            'calculation_times_count': len(self.calculation_times),
            'batch_buffer_count': len(self.batch_buffer) if self.batch_buffer else 0
        }
    
    def __str__(self) -> str:
        hft_status = "HFT" if self.config.hft_mode else "STD"
        error_info = f", errors={self.error_count}" if self.error_count > 0 else ""
        return f"{self.name}({hft_status}, period={self.config.period}, count={self.count}{error_info})"
    
    def __repr__(self) -> str:
        return self.__str__()

class MultiValueIndicator(VolumeWeightedIndicator):
    """Enhanced base class for indicators that return multiple values with HFT optimizations"""
    
    @performance_monitor
    @robust_calculation(default_value={})
    @abstractmethod
    def calculate_values(self, price: float, volume: float, timestamp: datetime) -> Dict[str, float]:
        """Calculate multiple indicator values with error handling"""
        pass
    
    @performance_monitor
    @memory_efficient()
    def calculate(self, price: float, volume: float, timestamp: datetime) -> Optional[IndicatorResult]:
        """Calculate indicator with multiple values and enhanced error handling"""
        try:
            values = self.calculate_values(price, volume, timestamp)
            
            if not values:
                return None
            
            # Validate all values are numeric
            for key, value in values.items():
                if not isinstance(value, (int, float)) or np.isnan(value) or np.isinf(value):
                    logger.warning(f"Invalid value for {key}: {value}")
                    values[key] = 0.0
            
            # Use the main value as the primary indicator value
            main_value = values.get('main', list(values.values())[0])
            
            # Generate signal if we have previous results
            signal = SignalType.NEUTRAL
            confidence = 0.0
            if len(self.results) > 0:
                previous_value = self.results[-1].value
                signal, confidence = self._generate_signal(main_value, previous_value)
            
            result = IndicatorResult(
                timestamp=timestamp,
                value=main_value,
                signal=signal,
                confidence=confidence,
                metadata={'all_values': values}
            )
            
            # Set additional values if available
            if 'upper' in values:
                result.upper_band = values['upper']
            if 'lower' in values:
                result.lower_band = values['lower']
            if 'signal' in values:
                result.signal_line = values['signal']
            if 'histogram' in values:
                result.histogram = values['histogram']
            
            self.results.append(result)
            self._add_data_point(price, volume, timestamp)
            
            return result
            
        except Exception as e:
            self.error_count += 1
            self.consecutive_errors += 1
            self.last_error_time = timestamp
            logger.error(f"Error in {self.name}.calculate: {str(e)}")
            
            if self.config.error_recovery:
                return None
            else:
                raise

class AdaptiveIndicator(VolumeWeightedIndicator):
    """Enhanced base class for adaptive indicators with HFT-optimized parameter adjustment"""
    
    def __init__(self, config: IndicatorConfig, name: str = None):
        super().__init__(config, name)
        self.adaptive_period = config.period
        self.volatility_adjustment = 1.0
        self.trend_adjustment = 1.0
        
        # Adaptive calculation cache for HFT
        self.volatility_cache = deque(maxlen=100) if config.hft_mode else []
        self.trend_cache = deque(maxlen=100) if config.hft_mode else []
        self.last_adaptation_time = None
        self.adaptation_interval = 10  # Adapt every N calculations for HFT efficiency
    
    def _calculate_market_volatility(self, lookback: int = None) -> float:
        """Calculate recent market volatility"""
        lookback = lookback or self.config.period
        if len(self.prices) < lookback:
            return 1.0
        
        recent_prices = self.prices[-lookback:]
        returns = [np.log(recent_prices[i] / recent_prices[i-1]) for i in range(1, len(recent_prices))]
        
        if not returns:
            return 1.0
        
        return np.std(returns) * np.sqrt(252)  # Annualized volatility
    
    def _calculate_trend_strength(self, lookback: int = None) -> float:
        """Calculate trend strength"""
        lookback = lookback or self.config.period
        if len(self.prices) < lookback:
            return 0.0
        
        recent_prices = self.prices[-lookback:]
        
        # Linear regression slope as trend strength
        x = np.arange(len(recent_prices))
        slope, _ = np.polyfit(x, recent_prices, 1)
        
        # Normalize by price level
        return slope / np.mean(recent_prices) if np.mean(recent_prices) != 0 else 0.0
    
    @robust_calculation(default_value=None)
    def _adapt_parameters(self) -> None:
        """Adapt indicator parameters based on market conditions with HFT optimizations"""
        if not self.config.adaptive or len(self.prices) < self.config.period:
            return
        
        # Skip adaptation if too frequent (HFT optimization)
        if (self.config.hft_mode and self.last_adaptation_time and 
            self.count - self.last_adaptation_time < self.adaptation_interval):
            return
        
        try:
            volatility = self._calculate_market_volatility()
            trend_strength = abs(self._calculate_trend_strength())
            
            # Cache values for HFT
            if self.config.hft_mode:
                self.volatility_cache.append(volatility)
                self.trend_cache.append(trend_strength)
                
                # Use cached averages for smoother adaptation
                if len(self.volatility_cache) > 5:
                    volatility = np.mean(list(self.volatility_cache)[-5:])
                if len(self.trend_cache) > 5:
                    trend_strength = np.mean(list(self.trend_cache)[-5:])
            
            # Adjust period based on volatility (higher volatility = shorter period)
            base_period = self.config.period
            volatility_factor = max(0.5, min(2.0, 1.0 / (1.0 + volatility)))
            
            # Adjust based on trend strength (stronger trend = longer period)
            trend_factor = max(0.8, min(1.5, 1.0 + trend_strength))
            
            self.adaptive_period = int(base_period * volatility_factor * trend_factor)
            self.adaptive_period = max(3, min(base_period * 3, self.adaptive_period))
            
            self.volatility_adjustment = volatility_factor
            self.trend_adjustment = trend_factor
            self.last_adaptation_time = self.count
            
            logger.debug(f"{self.name}: Adapted period to {self.adaptive_period} (vol={volatility:.3f}, trend={trend_strength:.3f})")
            
        except Exception as e:
            logger.warning(f"Parameter adaptation failed for {self.name}: {str(e)}")
            # Reset to base values on error
            self.adaptive_period = self.config.period
            self.volatility_adjustment = 1.0
            self.trend_adjustment = 1.0

# Utility functions for indicator calculations
@robust_calculation(default_value=[])
def calculate_ema(values: List[float], period: int, alpha: float = None) -> List[float]:
    """Calculate Exponential Moving Average with error handling"""
    if not values or period < 1:
        return []
    
    # Validate input values
    clean_values = []
    for v in values:
        if isinstance(v, (int, float)) and not (np.isnan(v) or np.isinf(v)):
            clean_values.append(float(v))
        else:
            logger.warning(f"Invalid EMA input value: {v}")
            if clean_values:  # Use last valid value
                clean_values.append(clean_values[-1])
            else:
                clean_values.append(0.0)
    
    if not clean_values:
        return []
    
    if alpha is None:
        alpha = 2.0 / (period + 1)
    
    ema_values = [clean_values[0]]  # Start with first value
    
    for i in range(1, len(clean_values)):
        ema = alpha * clean_values[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(ema)
    
    return ema_values

@robust_calculation(default_value=[])
def calculate_sma(values: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average with error handling"""
    if not values or period < 1:
        return []
    
    # Validate and clean input values
    clean_values = []
    for v in values:
        if isinstance(v, (int, float)) and not (np.isnan(v) or np.isinf(v)):
            clean_values.append(float(v))
        else:
            logger.warning(f"Invalid SMA input value: {v}")
            if clean_values:  # Use last valid value
                clean_values.append(clean_values[-1])
            else:
                clean_values.append(0.0)
    
    if not clean_values:
        return []
    
    sma_values = []
    for i in range(len(clean_values)):
        if i < period - 1:
            sma_values.append(np.nan)
        else:
            window = clean_values[i - period + 1:i + 1]
            if window:  # Additional safety check
                sma_values.append(np.mean(window))
            else:
                sma_values.append(np.nan)
    
    return sma_values

@robust_calculation(default_value=[])
def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index using TA-Lib with error handling"""
    if len(prices) < period + 1:
        return [np.nan] * len(prices)
    
    try:
        # Clean and validate prices
        clean_prices = []
        for p in prices:
            if isinstance(p, (int, float)) and not (np.isnan(p) or np.isinf(p)) and p > 0:
                clean_prices.append(float(p))
            else:
                if clean_prices:  # Use last valid price
                    clean_prices.append(clean_prices[-1])
                else:
                    clean_prices.append(1.0)  # Default price
        
        if len(clean_prices) < period + 1:
            return [np.nan] * len(prices)
        
        prices_array = np.array(clean_prices, dtype=np.float64)
        rsi_values = talib.RSI(prices_array, timeperiod=period)
        
        # Ensure we return the same length as input
        result = rsi_values.tolist()
        if len(result) < len(prices):
            result = [np.nan] * (len(prices) - len(result)) + result
        
        return result
        
    except Exception as e:
        logger.error(f"RSI calculation failed: {str(e)}")
        return [np.nan] * len(prices)

@robust_calculation(default_value=([], [], []))
def calculate_macd(prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """Calculate MACD using TA-Lib with error handling"""
    if len(prices) < slow_period:
        nan_list = [np.nan] * len(prices)
        return nan_list, nan_list, nan_list
    
    try:
        # Clean and validate prices
        clean_prices = []
        for p in prices:
            if isinstance(p, (int, float)) and not (np.isnan(p) or np.isinf(p)) and p > 0:
                clean_prices.append(float(p))
            else:
                if clean_prices:  # Use last valid price
                    clean_prices.append(clean_prices[-1])
                else:
                    clean_prices.append(1.0)  # Default price
        
        if len(clean_prices) < slow_period:
            nan_list = [np.nan] * len(prices)
            return nan_list, nan_list, nan_list
        
        prices_array = np.array(clean_prices, dtype=np.float64)
        macd_line, signal_line, histogram = talib.MACD(prices_array, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
        
        # Ensure consistent length with input
        macd_list = macd_line.tolist()
        signal_list = signal_line.tolist()
        hist_list = histogram.tolist()
        
        # Pad with NaN if necessary
        target_len = len(prices)
        for lst in [macd_list, signal_list, hist_list]:
            while len(lst) < target_len:
                lst.insert(0, np.nan)
        
        return macd_list, signal_list, hist_list
        
    except Exception as e:
        logger.error(f"MACD calculation failed: {str(e)}")
        nan_list = [np.nan] * len(prices)
        return nan_list, nan_list, nan_list

@robust_calculation(default_value=([], [], []))
def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """Calculate Bollinger Bands using TA-Lib with error handling"""
    if len(prices) < period:
        nan_list = [np.nan] * len(prices)
        return nan_list, nan_list, nan_list
    
    try:
        # Clean and validate prices
        clean_prices = []
        for p in prices:
            if isinstance(p, (int, float)) and not (np.isnan(p) or np.isinf(p)) and p > 0:
                clean_prices.append(float(p))
            else:
                if clean_prices:  # Use last valid price
                    clean_prices.append(clean_prices[-1])
                else:
                    clean_prices.append(1.0)  # Default price
        
        if len(clean_prices) < period:
            nan_list = [np.nan] * len(prices)
            return nan_list, nan_list, nan_list
        
        # Validate std_dev parameter
        if std_dev <= 0:
            logger.warning(f"Invalid std_dev: {std_dev}, using default 2.0")
            std_dev = 2.0
        
        prices_array = np.array(clean_prices, dtype=np.float64)
        upper_band, middle_band, lower_band = talib.BBANDS(prices_array, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        
        # Ensure consistent length with input
        upper_list = upper_band.tolist()
        middle_list = middle_band.tolist()
        lower_list = lower_band.tolist()
        
        # Pad with NaN if necessary
        target_len = len(prices)
        for lst in [upper_list, middle_list, lower_list]:
            while len(lst) < target_len:
                lst.insert(0, np.nan)
        
        return upper_list, middle_list, lower_list
        
    except Exception as e:
        logger.error(f"Bollinger Bands calculation failed: {str(e)}")
        nan_list = [np.nan] * len(prices)
        return nan_list, nan_list, nan_list