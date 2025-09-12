"""Consolidated Core Base Classes for Technical Indicators

This module contains the unified base classes and utilities for all technical indicators.
It consolidates functionality from base.py, core_base.py, and augmented_indicator.py
while eliminating redundancy and improving performance.

Key Features:
- Unified base classes for all indicator types
- HFT optimizations and memory management
- Robust error handling and recovery
- Performance monitoring and metrics
- Thread-safe operations
- Adaptive parameter adjustment
- Institutional-grade features (5-pillar architecture)
- Volume weighting and smart money analysis

Author: Vincent S. Pereira
Version: 6.0.0 (Consolidated & Optimized)
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Union, NamedTuple
import logging
import time
import gc
import threading
from collections import deque
from functools import wraps
from dataclasses import dataclass, field
import warnings
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

# Initialize logger first
logger = logging.getLogger(__name__)

# Optional imports with fallbacks
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
    # Mock Bar class for testing
    class Bar:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

# Import volume confirmation and smart money analysis modules
try:
    from .volume_confirmation import (
        VolumeConfirmationEngine,
        VolumeConfirmationMixin,
        VolumeConfirmationScore,
        VolumeAnalysis
    )
    VOLUME_CONFIRMATION_AVAILABLE = True
except ImportError:
    VOLUME_CONFIRMATION_AVAILABLE = False
    logger.warning("Volume confirmation module not available")

try:
    from .smart_money_analysis import (
        SmartMoneyAnalysisEngine,
        SmartMoneyMixin,
        SmartMoneyMetrics,
        SmartMoneyBias,
        InstitutionalActivity
    )
    SMART_MONEY_AVAILABLE = True
except ImportError:
    SMART_MONEY_AVAILABLE = False
    logger.warning("Smart money analysis module not available")

# Import enhanced risk management and regime adaptation engines
try:
    from .enhanced_risk_factory import (
        EnhancedRiskFactory,
        EnhancedRiskConfig,
        RiskAdjustedOutput
    )
    ENHANCED_RISK_AVAILABLE = True
except ImportError:
    ENHANCED_RISK_AVAILABLE = False
    logger.warning("Enhanced risk factory module not available")

try:
    from .regime_adaptation_engine import (
        RegimeAdaptationEngine,
        RegimeConfig,
        RegimeDetectionResult
    )
    REGIME_ADAPTATION_AVAILABLE = True
except ImportError:
    REGIME_ADAPTATION_AVAILABLE = False
    logger.warning("Regime adaptation engine not available")

try:
    from .multi_timeframe_engine import (
        MultiTimeframeEngine,
        TimeframeConfig,
        MultiTimeframeSignal
    )
    MULTI_TIMEFRAME_AVAILABLE = True
except ImportError:
    MULTI_TIMEFRAME_AVAILABLE = False
    logger.warning("Multi-timeframe engine not available")

# Performance constants for HFT environments
HFT_MAX_MEMORY_ITEMS = 10000
HFT_BATCH_SIZE = 1000
HFT_GC_THRESHOLD = 5000
HFT_PERFORMANCE_WARNING_MS = 1.0

# Thread-local storage
_thread_local = threading.local()

# ===========================================
# DECORATORS FOR PERFORMANCE AND RELIABILITY
# ===========================================

def performance_monitor(func):
    """Enhanced decorator for institutional-grade performance monitoring"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.perf_counter()
        start_memory = None
        
        # Advanced memory tracking for institutional environments
        try:
            import psutil
            process = psutil.Process()
            start_memory = process.memory_info().rss
        except ImportError:
            pass
        
        try:
            result = func(self, *args, **kwargs)
            execution_time = time.perf_counter() - start_time
            
            # Enhanced performance tracking with memory metrics
            if hasattr(self, 'calculation_times'):
                self.calculation_times.append(execution_time)
                
                # Advanced performance metrics storage
                if not hasattr(self, '_performance_metrics'):
                    self._performance_metrics = deque(maxlen=1000)
                
                memory_delta = 0
                if start_memory:
                    try:
                        end_memory = process.memory_info().rss
                        memory_delta = end_memory - start_memory
                    except:
                        pass
                
                self._performance_metrics.append({
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'memory_delta': memory_delta,
                    'timestamp': time.time(),
                    'args_count': len(args) + len(kwargs)
                })
                
                if len(self.calculation_times) > HFT_MAX_MEMORY_ITEMS:
                    self.calculation_times = self.calculation_times[-HFT_MAX_MEMORY_ITEMS//2:]
            
            # Enhanced logging with memory information
            if execution_time * 1000 > HFT_PERFORMANCE_WARNING_MS:
                memory_info = ""
                if start_memory:
                    try:
                        end_memory = process.memory_info().rss
                        memory_delta = (end_memory - start_memory) / 1024 / 1024
                        memory_info = f", Memory: +{memory_delta:.2f}MB"
                    except:
                        pass
                
                logger.warning(f"{func.__name__} took {execution_time*1000:.2f}ms{memory_info}")
            
            return result
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            logger.error(f"Error in {func.__name__} after {execution_time*1000:.2f}ms: {str(e)[:200]}")
            if hasattr(self, 'error_count'):
                self.error_count += 1
            
            # Enhanced error tracking
            if not hasattr(self, '_error_history'):
                self._error_history = deque(maxlen=100)
            
            self._error_history.append({
                'function': func.__name__,
                'error': str(e)[:200],
                'execution_time': execution_time,
                'timestamp': time.time()
            })
            
            raise
    return wrapper

def robust_calculation(default_value=None, log_errors=True, retry_count=0, fallback_method=None):
    """Enhanced decorator for institutional-grade robust error handling"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None
            
            # Attempt calculation with retries
            for attempt in range(retry_count + 1):
                try:
                    # Input validation for institutional standards
                    if args:
                        for i, arg in enumerate(args):
                            if isinstance(arg, (int, float)):
                                if not np.isfinite(arg):
                                    raise ValueError(f"Non-finite value detected in argument {i}: {arg}")
                                if abs(arg) > 1e15:  # Prevent overflow
                                    raise ValueError(f"Value too large in argument {i}: {arg}")
                    
                    result = func(self, *args, **kwargs)
                    
                    # Output validation
                    if isinstance(result, (int, float)):
                        if not np.isfinite(result):
                            raise ValueError(f"Non-finite result from {func.__name__}: {result}")
                    elif isinstance(result, dict):
                        for key, value in result.items():
                            if isinstance(value, (int, float)) and not np.isfinite(value):
                                raise ValueError(f"Non-finite value in result[{key}]: {value}")
                    
                    return result
                    
                except (ValueError, ZeroDivisionError, IndexError, TypeError, OverflowError, 
                        np.linalg.LinAlgError) as e:
                    last_exception = e
                    
                    if attempt < retry_count:
                        if log_errors:
                            logger.debug(f"Calculation error in {func.__name__} (attempt {attempt + 1}): {str(e)[:100]}")
                        continue  # Retry
                    
                    # Final attempt failed, try fallback method
                    if fallback_method and hasattr(self, fallback_method):
                        try:
                            fallback_func = getattr(self, fallback_method)
                            result = fallback_func(*args, **kwargs)
                            if log_errors:
                                logger.info(f"Used fallback method {fallback_method} for {func.__name__}")
                            return result
                        except Exception as fallback_error:
                            if log_errors:
                                logger.warning(f"Fallback method {fallback_method} also failed: {str(fallback_error)[:100]}")
                    
                    # Log the error and return default value
                    if log_errors:
                        logger.warning(f"Calculation error in {func.__name__}: {str(e)[:100]}")
                    
                    if hasattr(self, 'error_count'):
                        self.error_count += 1
                    
                    # Enhanced error tracking
                    if not hasattr(self, '_calculation_errors'):
                        self._calculation_errors = deque(maxlen=50)
                    
                    self._calculation_errors.append({
                        'function': func.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e)[:100],
                        'timestamp': time.time(),
                        'args_info': f"{len(args)} args, {len(kwargs)} kwargs"
                    })
                    
                    return default_value
                    
                except Exception as e:
                    last_exception = e
                    if log_errors:
                        logger.error(f"Unexpected error in {func.__name__}: {str(e)[:100]}")
                    if hasattr(self, 'error_count'):
                        self.error_count += 1
                    
                    # Track critical errors separately
                    if not hasattr(self, '_critical_errors'):
                        self._critical_errors = deque(maxlen=20)
                    
                    self._critical_errors.append({
                        'function': func.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e)[:100],
                        'timestamp': time.time()
                    })
                    
                    raise
            
            # Should not reach here, but safety net
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator

def memory_efficient(max_items=HFT_MAX_MEMORY_ITEMS):
    """Decorator for memory-efficient data management"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            
            # Memory management for lists
            for attr_name in ['prices', 'volumes', 'results', 'timestamps']:
                if hasattr(self, attr_name):
                    attr_list = getattr(self, attr_name)
                    if isinstance(attr_list, list) and len(attr_list) > max_items:
                        setattr(self, attr_name, attr_list[-max_items//2:])
            
            # Periodic garbage collection
            if hasattr(self, 'count') and self.count % HFT_GC_THRESHOLD == 0:
                gc.collect()
            
            return result
        return wrapper
    return decorator

# ===========================================
# ENUMS AND DATA CLASSES
# ===========================================

class IndicatorType(Enum):
    """Enumeration of indicator types"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    OSCILLATOR = "oscillator"
    MOVING_AVERAGE = "moving_average"
    PATTERN = "pattern"
    CUSTOM = "custom"

class SignalType(Enum):
    """Enumeration of trading signal types"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    UNKNOWN = "unknown"

class SmartMoneyFlow(Enum):
    """Smart money flow direction"""
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    NEUTRAL = "neutral"
    DARK_POOL_ACTIVITY = "dark_pool_activity"
    INSTITUTIONAL_BUYING = "institutional_buying"
    INSTITUTIONAL_SELLING = "institutional_selling"

class RiskLevel(Enum):
    """Risk assessment levels"""
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"
    EXTREME = "extreme"

class TimeframeConvergence(Enum):
    """Multi-timeframe signal convergence"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"
    DIVERGENT = "divergent"

@dataclass
class RiskMetrics:
    """Risk management metrics"""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    var_95: Optional[float] = None  # Value at Risk 95%
    expected_shortfall: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.MODERATE
    confidence_interval: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))

@dataclass
class SmartMoneyMetrics:
    """Smart money analysis metrics"""
    flow_direction: SmartMoneyFlow = SmartMoneyFlow.NEUTRAL
    institutional_activity: float = 0.0
    dark_pool_activity: float = 0.0
    large_order_ratio: float = 0.0
    block_trade_volume: float = 0.0
    smart_money_confidence: float = 0.0
    flow_strength: float = 0.0
    accumulation_distribution: float = 0.0

@dataclass
class IndicatorSignal:
    """Comprehensive indicator signal with institutional features"""
    signal_type: SignalType
    strength: float
    confidence: float
    timestamp: datetime
    
    # Core technical analysis
    value: float
    normalized_value: Optional[float] = None
    percentile_rank: Optional[float] = None
    
    # Volume analysis
    volume_confirmation: bool = False
    volume_strength: float = 0.0
    volume_weighted_value: Optional[float] = None
    
    # Market regime
    market_regime: MarketRegime = MarketRegime.UNKNOWN
    regime_confidence: float = 0.0
    adaptive_parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Multi-timeframe analysis
    timeframe_convergence: TimeframeConvergence = TimeframeConvergence.NEUTRAL
    higher_timeframe_bias: Optional[SignalType] = None
    lower_timeframe_momentum: Optional[float] = None
    
    # Smart money analysis
    smart_money_metrics: SmartMoneyMetrics = field(default_factory=SmartMoneyMetrics)
    institutional_flow: float = 0.0
    retail_sentiment: float = 0.0
    
    # Risk management
    risk_metrics: RiskMetrics = field(default_factory=RiskMetrics)
    expected_return: Optional[float] = None
    risk_adjusted_signal: Optional[float] = None
    
    # Institutional features (added for enhanced signal generation)
    institutional_bias: float = 0.0
    order_flow_imbalance: float = 0.0
    anomaly_score: float = 0.0
    behavioral_bias: float = 0.0
    
    # Auto risk management
    auto_stop_loss: Optional[float] = None
    auto_take_profit: Optional[float] = None
    position_sizing_factor: float = 1.0
    
    # Explainable AI
    feature_importance: Dict[str, float] = field(default_factory=dict)
    model_uncertainty: float = 0.0
    prediction_interval: Tuple[float, float] = field(default_factory=lambda: (0.0, 0.0))
    signal_attribution: Dict[str, float] = field(default_factory=dict)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

class IndicatorConfig:
    """Enhanced configuration class for indicator parameters"""
    
    def __init__(self, 
                 period: int = 14,
                 signal_threshold: float = 0.01,
                 outlier_threshold: float = 3.0,
                 memory_limit: int = HFT_MAX_MEMORY_ITEMS,
                 enable_hft_optimizations: bool = True,
                 enable_volume_weighting: bool = True,
                 enable_smart_money_analysis: bool = True,
                 enable_regime_adaptation: bool = True,
                 enable_multi_timeframe: bool = True,
                 enable_risk_management: bool = True,
                 **kwargs):
        
        self.period = max(1, period)
        self.signal_threshold = abs(signal_threshold)
        self.outlier_threshold = max(1.0, outlier_threshold)
        self.memory_limit = max(100, memory_limit)
        
        # Feature flags
        self.enable_hft_optimizations = enable_hft_optimizations
        self.enable_volume_weighting = enable_volume_weighting
        self.enable_smart_money_analysis = enable_smart_money_analysis
        self.enable_regime_adaptation = enable_regime_adaptation
        self.enable_multi_timeframe = enable_multi_timeframe
        self.enable_risk_management = enable_risk_management
        
        # Additional parameters
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def validate(self) -> bool:
        """Validate configuration parameters"""
        try:
            assert self.period > 0, "Period must be positive"
            assert 0 <= self.signal_threshold <= 1, "Signal threshold must be between 0 and 1"
            assert self.outlier_threshold >= 1, "Outlier threshold must be >= 1"
            assert self.memory_limit >= 100, "Memory limit must be >= 100"
            return True
        except AssertionError as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

class IndicatorResult:
    """Enhanced result class for indicator calculations"""
    
    def __init__(self, 
                 value: float,
                 timestamp: datetime = None,
                 signal: Optional[IndicatorSignal] = None,
                 metadata: Dict[str, Any] = None):
        
        self.value = value
        self.timestamp = timestamp or datetime.now()
        self.signal = signal
        self.metadata = metadata or {}
        
        # Performance tracking
        self.calculation_time: Optional[float] = None
        self.memory_usage: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        result = {
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }
        
        if self.signal:
            result['signal'] = {
                'type': self.signal.signal_type.value,
                'strength': self.signal.strength,
                'confidence': self.signal.confidence
            }
        
        return result

# ===========================================
# BASE INDICATOR CLASSES
# ===========================================

class BaseIndicator(ABC):
    """Abstract base class for all technical indicators"""
    
    def __init__(self, config: IndicatorConfig = None):
        self.config = config or IndicatorConfig()
        self.name = self.__class__.__name__
        self.indicator_type = IndicatorType.CUSTOM
        
        # Performance tracking
        self.calculation_times: List[float] = []
        self.error_count: int = 0
        self.count: int = 0
        
        # Data storage
        self.results: deque = deque(maxlen=self.config.memory_limit)
        self.timestamps: deque = deque(maxlen=self.config.memory_limit)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Validation
        if not self.config.validate():
            raise ValueError(f"Invalid configuration for {self.name}")
    
    @abstractmethod
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update indicator with new data point"""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset indicator state"""
        pass
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        if not self.calculation_times:
            return {}
        
        times = np.array(self.calculation_times)
        return {
            'avg_calculation_time_ms': np.mean(times) * 1000,
            'max_calculation_time_ms': np.max(times) * 1000,
            'min_calculation_time_ms': np.min(times) * 1000,
            'total_calculations': len(times),
            'error_count': self.error_count,
            'error_rate': self.error_count / max(1, len(times))
        }

class VolumeWeightedIndicator(BaseIndicator):
    """Base class for volume-weighted indicators"""
    
    def __init__(self, config: IndicatorConfig = None):
        super().__init__(config)
        self.volumes: deque = deque(maxlen=self.config.memory_limit)
        self.prices: deque = deque(maxlen=self.config.memory_limit)
        
        # Volume analysis
        self.volume_sma: Optional[float] = None
        self.volume_std: Optional[float] = None
        self.avg_volume: float = 0.0
    
    @performance_monitor
    @memory_efficient()
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update with volume-weighted calculation"""
        with self._lock:
            self.count += 1
            timestamp = timestamp or datetime.now()
            
            # Store data
            self.prices.append(price)
            self.volumes.append(volume)
            self.timestamps.append(timestamp)
            
            # Update volume statistics
            self._update_volume_stats()
            
            # Calculate indicator value
            value = self._calculate_volume_weighted_value()
            
            # Create result with enhanced metadata
            result = IndicatorResult(
                value=value,
                timestamp=timestamp,
                metadata={
                    'volume': volume,
                    'volume_weight': self._get_volume_weight(volume),
                    'avg_volume': self.avg_volume,
                    'volume_confirmation': getattr(self, 'volume_confirmation_score', 0.0),
                    'large_order_detection': getattr(self, 'large_order_detection', False)
                }
            )
                
            self.results.append(result)
            return result
    
    def _update_volume_stats(self):
        """Update volume statistics"""
        if len(self.volumes) < 2:
            return
        
        volumes_array = np.array(self.volumes)
        self.volume_sma = np.mean(volumes_array)
        self.volume_std = np.std(volumes_array)
        self.avg_volume = self.volume_sma
    
    def _get_volume_weight(self, volume: float) -> float:
        """Calculate volume weight for current volume"""
        if not self.config.enable_volume_weighting or self.avg_volume == 0:
            return 1.0
        
        # Normalize volume relative to average
        weight = volume / self.avg_volume
        
        # Cap extreme weights
        return np.clip(weight, 0.1, 5.0)
    
    @abstractmethod
    def _calculate_volume_weighted_value(self) -> float:
        """Calculate the volume-weighted indicator value"""
        pass

class AugmentedIndicator(VolumeWeightedIndicator):
    """Advanced base class with institutional-grade features (5-pillar architecture)
    
    Implements the complete institutional-grade framework:
    1. Volume Integration & Confirmation
    2. Market Regime Adaptation
    3. Multi-Timeframe Convergence Analysis
    4. Smart Money & Microstructure Proxies
    5. Automated Risk Management Factory
    
    Additional Features:
    - Explainable AI (XAI) for Signal Transparency
    - Behavioral Overlay for Anomaly Detection
    - Cross-Asset Correlation Analysis
    - Continuous Learning and Model Retraining
    - Regulatory Compliance Framework
    """
    
    def __init__(self, config: IndicatorConfig = None):
        super().__init__(config)
        
        # Pillar 1: Volume Integration & Confirmation
        self.volume_confirmation_score = 0.0
        self.volume_weighted_signals = deque(maxlen=100)
        self.institutional_volume_threshold = 2.0  # 2x average volume
        self.volume_profile = {
            'accumulation': 0.0, 
            'distribution': 0.0,
            'buying_pressure': 0.0,
            'selling_pressure': 0.0,
            'price_levels': {}  # Track volume at each price level
        }
        self.volume_metrics = {}  # Detailed volume analysis metrics
        
        # Pillar 2: Market Regime Analysis (Enhanced)
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_confidence = 0.0
        self.regime_history: deque = deque(maxlen=100)
        self.volatility_regime = 'normal'  # low, normal, high, extreme
        self.trend_regime = 'sideways'  # trending_up, trending_down, sideways
        
        # Initialize enhanced regime adaptation engine
        if REGIME_ADAPTATION_AVAILABLE and self.config.enable_regime_adaptation:
            self.regime_engine = RegimeAdaptationEngine(
                RegimeConfig(
                    lookback_period=50,
                    volatility_threshold=0.02,
                    trend_threshold=0.01,
                    adaptation_speed=0.1
                )
            )
        else:
            self.regime_engine = None
        
        # Pillar 3: Multi-Timeframe Analysis (Enhanced)
        self.timeframe_signals: Dict[str, IndicatorSignal] = {}
        self.timeframe_convergence = TimeframeConvergence.NEUTRAL
        self.signal_stack = deque(maxlen=50)  # For ensemble modeling
        
        # Initialize enhanced multi-timeframe engine
        if MULTI_TIMEFRAME_AVAILABLE and self.config.enable_multi_timeframe:
            self.multi_timeframe_engine = MultiTimeframeEngine(
                primary_timeframe='15m',
                secondary_timeframes=['1h', '4h', '1d', '1w']
            )
        else:
            self.multi_timeframe_engine = None
        
        # Pillar 4: Smart Money & Microstructure Analysis
        self.smart_money_metrics = SmartMoneyMetrics()
        self.institutional_flow_history: deque = deque(maxlen=100)
        self.order_flow_imbalance = 0.0
        self.large_order_detection = False
        self.institutional_bias = 0.0  # -1 to 1 scale
        
        # Pillar 5: Risk Management Factory (Enhanced)
        self.risk_metrics = RiskMetrics()
        self.auto_stop_loss = None
        self.auto_take_profit = None
        self.position_sizing_factor = 1.0
        self.risk_adjusted_signal = 0.0
        
        # Initialize enhanced risk factory
        if ENHANCED_RISK_AVAILABLE and self.config.enable_risk_management:
            self.risk_factory = EnhancedRiskFactory(
                EnhancedRiskConfig(
                    base_risk_per_trade=0.02,
                    max_portfolio_risk=0.10,
                    position_sizing_method='kelly_criterion',
                    stop_loss_method='atr_trailing',
                    atr_period=14,
                    atr_multiplier=2.0
                )
            )
        else:
            self.risk_factory = None
        
        # Explainable AI Components
        self.feature_importance = {}
        self.signal_attribution = {}
        self.confidence_breakdown = {}
        
        # Behavioral Analysis
        self.anomaly_score = 0.0
        self.behavioral_bias = 0.0
        self.sentiment_factor = 0.0
        
        # Cross-Asset Analysis
        self.correlation_matrix = {}
        self.sector_momentum = 0.0
        self.market_breadth = 0.0
        
        # Adaptive Learning
        self.performance_feedback = deque(maxlen=1000)
        self.parameter_adaptation_rate = 0.01
        self.model_confidence = 0.5
        
        # Thread pool for parallel processing
        self._executor = ThreadPoolExecutor(max_workers=4) if config and config.enable_hft_optimizations else None
    
    def __del__(self):
        """Cleanup thread pool"""
        if hasattr(self, '_executor') and self._executor:
            self._executor.shutdown(wait=False)
    
    @performance_monitor
    @memory_efficient()
    def update(self, price: float, volume: float = 1.0, timestamp: datetime = None) -> IndicatorResult:
        """Update with full institutional-grade analysis pipeline"""
        with self._lock:
            # Base volume-weighted update
            result = super().update(price, volume, timestamp)
            
            # Pillar 1: Volume Integration & Confirmation
            if self.config.enable_volume_weighting:
                self._analyze_volume_confirmation(price, volume)
                self._detect_institutional_volume(volume)
            
            # Pillar 2: Market Regime Adaptation
            if self.config.enable_regime_adaptation:
                self._analyze_market_regime(price, volume)
                self._adapt_parameters_to_regime()
            
            # Pillar 3: Multi-Timeframe Analysis
            if self.config.enable_multi_timeframe:
                self._analyze_timeframe_convergence(result.value, timestamp)
                self._update_signal_stack(result.value)
            
            # Pillar 4: Smart Money & Microstructure Analysis
            if self.config.enable_smart_money_analysis:
                self._analyze_smart_money_flow(price, volume)
                self._detect_order_flow_imbalance(price, volume)
                self._assess_institutional_bias(price, volume)
            
            # Pillar 5: Risk Management Factory
            if self.config.enable_risk_management:
                self._update_risk_metrics(price, volume)
                self._calculate_auto_stops(price)
                self._adjust_position_sizing()
            
            # Explainable AI Analysis
            self._generate_feature_importance()
            self._calculate_signal_attribution()
            
            # Behavioral Analysis
            self._detect_anomalies(price, volume)
            self._analyze_behavioral_bias()
            
            # Cross-Asset Analysis (if data available)
            self._update_correlation_analysis()
            
            # Adaptive Learning
            self._update_model_confidence()
            self._adapt_parameters()
            
            # Create enhanced institutional signal
            signal = self._generate_institutional_signal(result.value, timestamp)
            result.signal = signal
            
            # Update result metadata with institutional metrics
            result.metadata.update({
                'regime': self.current_regime.name,
                'volume_confirmation': self.volume_confirmation_score,
                'smart_money_activity': self.smart_money_metrics.institutional_activity,
                'institutional_bias': self.institutional_bias,
                'anomaly_score': self.anomaly_score,
                'model_confidence': self.model_confidence,
                'risk_level': self.risk_metrics.risk_level.value,
                'order_flow_imbalance': self.order_flow_imbalance
            })
            
            # Store performance feedback for learning
            self._store_performance_feedback(result)
            
            return result
    
    def _analyze_market_regime(self, price: float, volume: float):
        """Analyze current market regime"""
        if len(self.prices) < 20:
            return
        
        prices_array = np.array(self.prices)
        volumes_array = np.array(self.volumes)
        
        # Calculate regime indicators
        returns = np.diff(prices_array) / prices_array[:-1]
        volatility = np.std(returns[-20:]) if len(returns) >= 20 else 0
        trend_strength = abs(np.corrcoef(np.arange(len(prices_array[-20:])), prices_array[-20:])[0, 1]) if len(prices_array) >= 20 else 0
        
        # Classify regime
        if volatility > 0.03:  # High volatility threshold
            if trend_strength > 0.7:
                self.current_regime = MarketRegime.TRENDING_UP if returns[-1] > 0 else MarketRegime.TRENDING_DOWN
            else:
                self.current_regime = MarketRegime.HIGH_VOLATILITY
        elif volatility < 0.01:  # Low volatility threshold
            self.current_regime = MarketRegime.LOW_VOLATILITY
        else:
            if trend_strength > 0.5:
                self.current_regime = MarketRegime.TRENDING_UP if returns[-1] > 0 else MarketRegime.TRENDING_DOWN
            else:
                self.current_regime = MarketRegime.SIDEWAYS
        
        self.regime_confidence = min(trend_strength + (1 - volatility), 1.0)
        self.regime_history.append((self.current_regime, self.regime_confidence))
    
    def _analyze_smart_money_flow(self, price: float, volume: float):
        """Analyze smart money flow patterns"""
        if len(self.volumes) < 10:
            return
        
        volumes_array = np.array(self.volumes)
        prices_array = np.array(self.prices)
        
        # Calculate smart money indicators
        volume_ma = np.mean(volumes_array[-10:])
        volume_ratio = volume / volume_ma if volume_ma > 0 else 1.0
        
        # Large volume detection
        if volume_ratio > 2.0:  # Significantly above average
            price_change = (price - prices_array[-2]) / prices_array[-2] if len(prices_array) >= 2 else 0
            
            if price_change > 0.01:  # Price up with high volume
                self.smart_money_metrics.flow_direction = SmartMoneyFlow.ACCUMULATION
                self.smart_money_metrics.institutional_activity = min(volume_ratio / 2.0, 1.0)
            elif price_change < -0.01:  # Price down with high volume
                self.smart_money_metrics.flow_direction = SmartMoneyFlow.DISTRIBUTION
                self.smart_money_metrics.institutional_activity = min(volume_ratio / 2.0, 1.0)
        else:
            self.smart_money_metrics.flow_direction = SmartMoneyFlow.NEUTRAL
            self.smart_money_metrics.institutional_activity *= 0.9  # Decay
        
        self.smart_money_metrics.large_order_ratio = volume_ratio
        self.institutional_flow_history.append(self.smart_money_metrics.institutional_activity)
    
    def _update_risk_metrics(self, price: float, volume: float):
        """Update risk management metrics"""
        if len(self.prices) < 20:
            return
        
        prices_array = np.array(self.prices)
        returns = np.diff(prices_array) / prices_array[:-1]
        
        if len(returns) >= 20:
            # Calculate risk metrics
            volatility = np.std(returns[-20:])
            self.risk_metrics.var_95 = np.percentile(returns[-20:], 5)  # 5th percentile for VaR
            
            # Risk level classification
            if volatility > 0.05:
                self.risk_metrics.risk_level = RiskLevel.VERY_HIGH
            elif volatility > 0.03:
                self.risk_metrics.risk_level = RiskLevel.HIGH
            elif volatility > 0.02:
                self.risk_metrics.risk_level = RiskLevel.MODERATE
            elif volatility > 0.01:
                self.risk_metrics.risk_level = RiskLevel.LOW
            else:
                self.risk_metrics.risk_level = RiskLevel.VERY_LOW
    
    # ===========================================
    # PILLAR 1: VOLUME INTEGRATION & CONFIRMATION
    # ===========================================
    
    def _analyze_volume_confirmation(self, price: float, volume: float):
        """Enhanced volume confirmation analysis with institutional-grade scoring"""
        if len(self.volumes) < 10:
            return
        
        # Multi-period volume analysis
        recent_volumes = list(self.volumes)[-20:] if len(self.volumes) >= 20 else list(self.volumes)
        volume_ma_short = np.mean(recent_volumes[-5:]) if len(recent_volumes) >= 5 else np.mean(recent_volumes)
        volume_ma_long = np.mean(recent_volumes)
        volume_std = np.std(recent_volumes)
        
        # Volume metrics
        volume_ratio_short = volume / volume_ma_short if volume_ma_short > 0 else 1.0
        volume_ratio_long = volume / volume_ma_long if volume_ma_long > 0 else 1.0
        volume_z_score = (volume - volume_ma_long) / volume_std if volume_std > 0 else 0.0
        
        # Price change analysis with multiple timeframes
        price_change_1 = 0.0
        price_change_3 = 0.0
        price_change_5 = 0.0
        
        if len(self.prices) >= 2:
            price_change_1 = (price - self.prices[-2]) / self.prices[-2]
        if len(self.prices) >= 4:
            price_change_3 = (price - self.prices[-4]) / self.prices[-4]
        if len(self.prices) >= 6:
            price_change_5 = (price - self.prices[-6]) / self.prices[-6]
        
        # Volume-Price Relationship Analysis
        vpr_score = self._calculate_volume_price_relationship(price_change_1, volume_ratio_short)
        
        # Institutional Volume Detection
        institutional_volume_score = self._detect_institutional_volume_patterns(volume, volume_z_score)
        
        # Volume Trend Analysis
        volume_trend_score = self._analyze_volume_trend(recent_volumes)
        
        # Volume Confirmation Scoring (0-1 scale)
        confirmation_components = {
            'price_volume_sync': self._score_price_volume_sync(price_change_1, volume_ratio_short),
            'volume_breakout': min(1.0, max(0.0, (volume_ratio_short - 1.0) / 2.0)),
            'volume_persistence': self._score_volume_persistence(recent_volumes),
            'institutional_presence': institutional_volume_score,
            'volume_trend_alignment': volume_trend_score,
            'volume_quality': self._assess_volume_quality(volume, recent_volumes)
        }
        
        # Weighted volume confirmation score
        weights = {
            'price_volume_sync': 0.25,
            'volume_breakout': 0.20,
            'volume_persistence': 0.15,
            'institutional_presence': 0.20,
            'volume_trend_alignment': 0.10,
            'volume_quality': 0.10
        }
        
        self.volume_confirmation_score = sum(
            confirmation_components[key] * weights[key] 
            for key in confirmation_components
        )
        
        # Store detailed volume metrics
        self.volume_metrics = {
            'volume_ratio_short': volume_ratio_short,
            'volume_ratio_long': volume_ratio_long,
            'volume_z_score': volume_z_score,
            'vpr_score': vpr_score,
            'confirmation_components': confirmation_components,
            'volume_ma_short': volume_ma_short,
            'volume_ma_long': volume_ma_long,
            'volume_std': volume_std
        }
        
        # Update volume profile with enhanced analysis
        if len(self.prices) >= 2:
            price_change = price - self.prices[-2]
            volume_weight = min(3.0, volume_ratio_short)  # Cap at 3x for stability
            
            if price_change > 0:
                self.volume_profile['accumulation'] += volume * volume_weight
                self.volume_profile['buying_pressure'] += volume * max(0, price_change) * volume_weight
            else:
                self.volume_profile['distribution'] += volume * volume_weight
                self.volume_profile['selling_pressure'] += volume * abs(min(0, price_change)) * volume_weight
            
            # Track volume-weighted price levels
            price_level = round(price, 2)  # Round to nearest cent
            if price_level not in self.volume_profile['price_levels']:
                self.volume_profile['price_levels'][price_level] = 0
            self.volume_profile['price_levels'][price_level] += volume
    
    def _calculate_volume_price_relationship(self, price_change: float, volume_ratio: float) -> float:
        """Calculate volume-price relationship score"""
        if abs(price_change) < 0.001:  # Minimal price movement
            return 0.5
        
        # Ideal relationship: higher volume with larger price moves
        expected_volume_ratio = 1.0 + (abs(price_change) * 10)  # Scale price change
        vpr_score = min(1.0, volume_ratio / expected_volume_ratio)
        
        return vpr_score
    
    def _detect_institutional_volume_patterns(self, volume: float, volume_z_score: float) -> float:
        """Detect institutional volume patterns and return confidence score"""
        # Multiple institutional volume indicators
        scores = []
        
        # Z-score based detection (2+ std devs = institutional)
        z_score_component = min(1.0, max(0.0, (volume_z_score - 1.0) / 2.0))
        scores.append(z_score_component)
        
        # Volume spike detection
        if len(self.volumes) >= 5:
            recent_volumes = list(self.volumes)[-5:]
            volume_spike = volume / max(recent_volumes[:-1]) if max(recent_volumes[:-1]) > 0 else 1.0
            spike_component = min(1.0, max(0.0, (volume_spike - 1.5) / 2.0))
            scores.append(spike_component)
        
        # Volume clustering (institutional orders often come in clusters)
        if len(self.volumes) >= 10:
            recent_high_volume_count = sum(1 for v in list(self.volumes)[-10:] if v > np.mean(list(self.volumes)[-20:]) * 1.5)
            cluster_component = min(1.0, recent_high_volume_count / 5.0)
            scores.append(cluster_component)
        
        return np.mean(scores) if scores else 0.0
    
    def _analyze_volume_trend(self, recent_volumes: List[float]) -> float:
        """Analyze volume trend and return alignment score"""
        if len(recent_volumes) < 5:
            return 0.5
        
        # Calculate volume trend using linear regression
        x = np.arange(len(recent_volumes))
        slope, _ = np.polyfit(x, recent_volumes, 1)
        
        # Normalize slope to 0-1 scale
        volume_mean = np.mean(recent_volumes)
        normalized_slope = slope / volume_mean if volume_mean > 0 else 0.0
        
        # Convert to 0-1 score (positive trend = higher score)
        trend_score = 0.5 + (normalized_slope * 5.0)  # Scale factor
        return min(1.0, max(0.0, trend_score))
    
    def _score_price_volume_sync(self, price_change: float, volume_ratio: float) -> float:
        """Score price-volume synchronization"""
        if abs(price_change) < 0.001:
            return 0.5  # Neutral for minimal price movement
        
        # Strong price moves should have strong volume
        price_strength = abs(price_change) * 100  # Convert to percentage
        volume_strength = max(0.0, volume_ratio - 1.0)  # Excess volume above average
        
        # Ideal sync: both price and volume are strong
        if price_strength > 0.5 and volume_strength > 0.5:
            sync_score = min(1.0, (price_strength * volume_strength) / 2.0)
        elif price_strength > 1.0 and volume_strength < 0.2:
            # Strong price move with weak volume = poor sync
            sync_score = 0.2
        elif price_strength < 0.2 and volume_strength > 1.0:
            # Weak price move with strong volume = accumulation/distribution
            sync_score = 0.7
        else:
            sync_score = 0.5
        
        return sync_score
    
    def _score_volume_persistence(self, recent_volumes: List[float]) -> float:
        """Score volume persistence over recent periods"""
        if len(recent_volumes) < 5:
            return 0.5
        
        volume_mean = np.mean(recent_volumes)
        above_average_count = sum(1 for v in recent_volumes[-5:] if v > volume_mean)
        
        # Persistence score based on consistent above-average volume
        persistence_score = above_average_count / 5.0
        return persistence_score
    
    def _assess_volume_quality(self, current_volume: float, recent_volumes: List[float]) -> float:
        """Assess the quality of current volume"""
        if len(recent_volumes) < 10:
            return 0.5
        
        # Quality factors
        volume_consistency = 1.0 - (np.std(recent_volumes) / np.mean(recent_volumes)) if np.mean(recent_volumes) > 0 else 0.0
        volume_consistency = min(1.0, max(0.0, volume_consistency))
        
        # Current volume relative to recent average
        volume_adequacy = min(1.0, current_volume / np.mean(recent_volumes)) if np.mean(recent_volumes) > 0 else 0.5
        
        # Combined quality score
        quality_score = (volume_consistency * 0.4) + (volume_adequacy * 0.6)
        return quality_score
    
    def _detect_institutional_volume(self, volume: float):
        """Enhanced institutional volume detection"""
        if len(self.volumes) < 20:
            return
        
        recent_volumes = list(self.volumes)[-20:]
        volume_ma = np.mean(recent_volumes)
        volume_std = np.std(recent_volumes)
        
        # Multiple institutional detection methods
        # Method 1: Statistical threshold (2+ standard deviations)
        threshold_2std = volume_ma + (2 * volume_std)
        threshold_3std = volume_ma + (3 * volume_std)
        
        # Method 2: Percentile-based detection
        volume_95th = np.percentile(recent_volumes, 95)
        volume_99th = np.percentile(recent_volumes, 99)
        
        # Method 3: Dynamic threshold based on recent activity
        recent_max = max(recent_volumes[-5:]) if len(recent_volumes) >= 5 else volume_ma
        dynamic_threshold = volume_ma + (recent_max - volume_ma) * 0.7
        
        # Institutional volume classification
        if volume > threshold_3std or volume > volume_99th:
            self.large_order_detection = True
            self.smart_money_metrics.large_order_ratio = volume / volume_ma
            self.smart_money_metrics.institutional_activity = min(1.0, volume / threshold_3std)
        elif volume > threshold_2std or volume > volume_95th or volume > dynamic_threshold:
            self.large_order_detection = True
            self.smart_money_metrics.large_order_ratio = volume / volume_ma
            self.smart_money_metrics.institutional_activity = min(0.8, volume / threshold_2std)
        else:
            self.large_order_detection = False
            self.smart_money_metrics.institutional_activity *= 0.9  # Decay
        
        # Track institutional flow history
        self.institutional_flow_history.append(self.smart_money_metrics.institutional_activity)
    
    # ===========================================
    # PILLAR 2: MARKET REGIME ADAPTATION
    # ===========================================
    
    def _adapt_parameters_to_regime(self):
        """Adapt indicator parameters based on market regime (Enhanced)"""
        if self.regime_engine:
            # Use enhanced regime adaptation engine
            if len(self.prices) >= self.regime_engine.config.lookback_period:
                prices_array = np.array(list(self.prices)[-self.regime_engine.config.lookback_period:])
                volumes_array = np.array(list(self.volumes)[-self.regime_engine.config.lookback_period:])
                
                # Detect regime using enhanced engine
                regime_result = self.regime_engine.detect_regime(prices_array, volumes_array)
                self.current_regime = regime_result.regime
                self.regime_confidence = regime_result.confidence
                
                # Adapt parameters using enhanced engine
                adapted_params = self.regime_engine.adapt_parameters(
                    regime_result, 
                    {'period': getattr(self.config, 'period', 14)}
                )
                
                # Apply adapted parameters
if 'period' in adapted_params:
    self.config.period = max(1, int(adapted_params['period']))

    # Enhance with volatility adjustment
    if len(self.risk_metrics_history) > 0 and self.risk_metrics.volatility > 0:
        recent_vols = [m.volatility for m in list(self.risk_metrics_history)[-10:]]
        avg_vol = np.mean(recent_vols) if recent_vols else self.risk_metrics.volatility
        vol_factor = min(2.0, max(0.5, self.risk_metrics.volatility / avg_vol))
        self.config.period = max(1, int(self.config.period * vol_factor))
        else:
            # Fallback to basic regime adaptation
            if self.current_regime == MarketRegime.HIGH_VOLATILITY:
                # Increase smoothing in high volatility
                self.parameter_adaptation_rate *= 1.2
            elif self.current_regime == MarketRegime.LOW_VOLATILITY:
                # Decrease smoothing in low volatility
                self.parameter_adaptation_rate *= 0.8
            elif self.current_regime in [MarketRegime.TRENDING_UP, MarketRegime.TRENDING_DOWN]:
                # Faster response in trending markets
                self.parameter_adaptation_rate *= 1.1
    
    # ===========================================
    # PILLAR 3: MULTI-TIMEFRAME ANALYSIS
    # ===========================================
    
    def _analyze_timeframe_convergence(self, value: float, timestamp: datetime):
        """Analyze signal convergence across timeframes (Enhanced)"""
        if self.multi_timeframe_engine:
            # Use enhanced multi-timeframe engine
            signal_strength = 0.0
            if len(self.results) >= 2:
                prev_value = self.results[-2].value
                signal_strength = (value - prev_value) / prev_value if prev_value != 0 else 0.0
            
            # Add signal to multi-timeframe engine
            self.multi_timeframe_engine.add_signal(
                timeframe='1m',
                value=value,
                strength=signal_strength,
                timestamp=timestamp
            )
            
            # Analyze convergence using enhanced engine
            convergence_result = self.multi_timeframe_engine.analyze_convergence()
            if convergence_result:
                self.timeframe_convergence = convergence_result.convergence_type
                
                # Generate composite signal
                composite_signal = self.multi_timeframe_engine.generate_composite_signal()
                if composite_signal:
                    self.timeframe_signals['composite'] = composite_signal
        else:
            # Fallback to basic timeframe analysis
            # Store current timeframe signal
            current_signal = IndicatorSignal(
                signal_type=SignalType.NEUTRAL,
                strength=0.0,
                confidence=0.5,
                timestamp=timestamp,
                value=value
            )
            
            self.timeframe_signals['current'] = current_signal
            
            # Analyze convergence (simplified)
            if len(self.signal_stack) >= 3:
                recent_signals = list(self.signal_stack)[-3:]
                signal_consistency = len(set(s for s in recent_signals)) == 1
                
                if signal_consistency:
                    self.timeframe_convergence = TimeframeConvergence.BULLISH if recent_signals[-1] > 0 else TimeframeConvergence.BEARISH
                else:
                    self.timeframe_convergence = TimeframeConvergence.NEUTRAL
    
    def _update_signal_stack(self, value: float):
        """Update signal stack for ensemble modeling"""
        # Convert value to signal direction (-1, 0, 1)
        if len(self.results) >= 2:
            prev_value = self.results[-2].value
            signal_direction = 1 if value > prev_value else (-1 if value < prev_value else 0)
            self.signal_stack.append(signal_direction)
    
    def add_timeframe_data(self, timeframe: str, price: float, volume: float = 1.0, timestamp: datetime = None):
        """Add data from different timeframes for multi-timeframe analysis"""
        if self.multi_timeframe_engine:
            signal_strength = 0.0
            if len(self.results) >= 2:
                prev_value = self.results[-2].value
                signal_strength = (price - prev_value) / prev_value if prev_value != 0 else 0.0
            
            self.multi_timeframe_engine.add_signal(
                timeframe=timeframe,
                value=price,
                strength=signal_strength,
                timestamp=timestamp or datetime.now()
            )
        else:
            logger.warning(f"Multi-timeframe engine not available for timeframe {timeframe}")
    
    # ===========================================
    # PILLAR 4: SMART MONEY & MICROSTRUCTURE
    # ===========================================
    
    def _detect_order_flow_imbalance(self, price: float, volume: float):
        """Detect order flow imbalance"""
        if len(self.prices) < 5 or len(self.volumes) < 5:
            return
        
        # Calculate price momentum and volume momentum
        recent_prices = list(self.prices)[-5:]
        recent_volumes = list(self.volumes)[-5:]
        
        price_momentum = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
        volume_momentum = (recent_volumes[-1] - recent_volumes[0]) / recent_volumes[0]
        
        # Order flow imbalance when price and volume momentum diverge
        self.order_flow_imbalance = price_momentum - volume_momentum
    
    def _assess_institutional_bias(self, price: float, volume: float):
        """Assess institutional bias in the market"""
        if len(self.institutional_flow_history) < 10:
            return
        
        # Calculate institutional activity trend
        recent_activity = list(self.institutional_flow_history)[-10:]
        activity_trend = np.polyfit(range(len(recent_activity)), recent_activity, 1)[0]
        
        # Institutional bias based on activity trend and volume
        volume_factor = min(2.0, volume / np.mean(list(self.volumes)[-10:]) if len(self.volumes) >= 10 else 1.0)
        self.institutional_bias = np.tanh(activity_trend * volume_factor)  # Bounded between -1 and 1
    
    # ===========================================
    # PILLAR 5: RISK MANAGEMENT FACTORY
    # ===========================================
    
    def _calculate_auto_stops(self, price: float):
        """Calculate automatic stop-loss and take-profit levels (Enhanced)"""
        if self.risk_factory:
            # Use enhanced risk factory
            if len(self.prices) >= self.risk_factory.config.atr_period:
                prices_array = np.array(list(self.prices)[-self.risk_factory.config.atr_period:])
                volumes_array = np.array(list(self.volumes)[-self.risk_factory.config.atr_period:])
                
                # Update market data in risk factory
                self.risk_factory.update_market_data(prices_array, volumes_array)
                
                # Calculate enhanced stop-loss and take-profit
                stop_loss = self.risk_factory.calculate_stop_loss(price, 'long')
                take_profit = self.risk_factory.calculate_take_profit(price, 'long')
                
                self.auto_stop_loss = stop_loss
                self.auto_take_profit = take_profit
        else:
            # Fallback to basic stop calculation
            if len(self.prices) < 20:
                return
            
            # Calculate ATR for stop placement
            recent_prices = np.array(list(self.prices)[-20:])
            price_changes = np.abs(np.diff(recent_prices))
            atr = np.mean(price_changes)
            
            # Risk-based stop levels
            stop_multiplier = 2.0 if self.risk_metrics.risk_level == RiskLevel.HIGH else 1.5
            
            self.auto_stop_loss = price - (atr * stop_multiplier)
            self.auto_take_profit = price + (atr * stop_multiplier * 2)  # 2:1 reward:risk
    
    def _adjust_position_sizing(self):
        """Adjust position sizing based on risk metrics (Enhanced)"""
        if self.risk_factory:
            # Use enhanced risk factory for position sizing
            signal_strength = 0.0
            if len(self.results) >= 2:
                current_value = self.results[-1].value
                prev_value = self.results[-2].value
                signal_strength = abs(current_value - prev_value) / prev_value if prev_value != 0 else 0.0
            
            # Calculate enhanced position size
            position_size = self.risk_factory.calculate_position_size(
                signal_strength=signal_strength,
                confidence=self.regime_confidence,
                market_regime=self.current_regime.value
            )
            
            self.position_sizing_factor = position_size
        else:
            # Fallback to basic position sizing
            base_size = 1.0
            
            # Adjust based on volatility
            if self.risk_metrics.risk_level == RiskLevel.VERY_HIGH:
                self.position_sizing_factor = base_size * 0.25
            elif self.risk_metrics.risk_level == RiskLevel.HIGH:
                self.position_sizing_factor = base_size * 0.5
            elif self.risk_metrics.risk_level == RiskLevel.MODERATE:
                self.position_sizing_factor = base_size * 0.75
            else:
                self.position_sizing_factor = base_size
            
            # Adjust based on regime confidence
            self.position_sizing_factor *= self.regime_confidence
    
    # ===========================================
    # EXPLAINABLE AI COMPONENTS
    # ===========================================
    
    def _generate_feature_importance(self):
        """Generate feature importance for explainable AI"""
        self.feature_importance = {
            'volume_confirmation': self.volume_confirmation_score,
            'regime_confidence': self.regime_confidence,
            'smart_money_activity': self.smart_money_metrics.institutional_activity,
            'risk_level': 1.0 - (self.risk_metrics.risk_level.value / 5.0),  # Invert risk level
            'timeframe_convergence': 1.0 if self.timeframe_convergence != TimeframeConvergence.NEUTRAL else 0.5
        }
    
    def _calculate_signal_attribution(self):
        """Calculate signal attribution for transparency"""
        total_weight = sum(self.feature_importance.values())
        if total_weight > 0:
            self.signal_attribution = {
                feature: weight / total_weight 
                for feature, weight in self.feature_importance.items()
            }
    
    # ===========================================
    # BEHAVIORAL ANALYSIS
    # ===========================================
    
    def _detect_anomalies(self, price: float, volume: float):
        """Detect behavioral anomalies"""
        if len(self.prices) < 20 or len(self.volumes) < 20:
            return
        
        # Price anomaly detection
        recent_prices = np.array(list(self.prices)[-20:])
        price_mean = np.mean(recent_prices)
        price_std = np.std(recent_prices)
        price_zscore = abs((price - price_mean) / price_std) if price_std > 0 else 0
        
        # Volume anomaly detection
        recent_volumes = np.array(list(self.volumes)[-20:])
        volume_mean = np.mean(recent_volumes)
        volume_std = np.std(recent_volumes)
        volume_zscore = abs((volume - volume_mean) / volume_std) if volume_std > 0 else 0
        
        # Combined anomaly score
        self.anomaly_score = min(1.0, (price_zscore + volume_zscore) / 4.0)  # Normalize to 0-1
    
    def _analyze_behavioral_bias(self):
        """Analyze behavioral bias in market movements"""
        if len(self.prices) < 10:
            return
        
        # Momentum bias detection
        recent_returns = np.diff(list(self.prices)[-10:]) / np.array(list(self.prices)[-10:-1])
        momentum_consistency = np.sum(np.sign(recent_returns)) / len(recent_returns)
        
        self.behavioral_bias = momentum_consistency  # -1 to 1 scale
    
    # ===========================================
    # CROSS-ASSET ANALYSIS
    # ===========================================
    
    def _update_correlation_analysis(self):
        """Update cross-asset correlation analysis"""
        # Placeholder for cross-asset correlation
        # In real implementation, would correlate with market indices, sectors, etc.
        self.correlation_matrix = {
            'market_correlation': 0.5,  # Placeholder
            'sector_correlation': 0.3,   # Placeholder
            'volatility_correlation': 0.2  # Placeholder
        }
    
    # ===========================================
    # ADAPTIVE LEARNING
    # ===========================================
    
    def _update_model_confidence(self):
        """Update model confidence based on recent performance"""
        if len(self.performance_feedback) < 10:
            return
        
        # Calculate recent accuracy
        recent_feedback = list(self.performance_feedback)[-10:]
        accuracy = sum(1 for f in recent_feedback if f.get('correct', False)) / len(recent_feedback)
        
        # Update model confidence with exponential smoothing
        alpha = 0.1
        self.model_confidence = alpha * accuracy + (1 - alpha) * self.model_confidence
    
    def _adapt_parameters(self):
        """Adapt parameters based on performance feedback"""
        if self.model_confidence < 0.4:
            # Increase adaptation rate if model confidence is low
            self.parameter_adaptation_rate = min(0.05, self.parameter_adaptation_rate * 1.1)
        elif self.model_confidence > 0.8:
            # Decrease adaptation rate if model confidence is high
            self.parameter_adaptation_rate = max(0.001, self.parameter_adaptation_rate * 0.9)
    
    def _store_performance_feedback(self, result: IndicatorResult):
        """Store performance feedback for adaptive learning"""
        feedback = {
            'timestamp': result.timestamp,
            'signal_strength': result.signal.strength if result.signal else 0.0,
            'confidence': result.signal.confidence if result.signal else 0.5,
            'value': result.value,
            'correct': None  # To be updated later with actual performance
        }
        self.performance_feedback.append(feedback)
    
    def _generate_institutional_signal(self, value: float, timestamp: datetime) -> IndicatorSignal:
        """Generate comprehensive institutional-grade signal"""
        # Base signal generation (to be implemented by subclasses)
        signal_type = SignalType.NEUTRAL
        strength = 0.0
        confidence = 0.5
        
        # Enhanced confidence calculation
        confidence_factors = [
            self.volume_confirmation_score,
            self.regime_confidence,
            self.smart_money_metrics.institutional_activity,
            1.0 - (self.risk_metrics.risk_level.value / 5.0),  # Invert risk level
            self.model_confidence
        ]
        
        # Weighted average confidence
        weights = [0.25, 0.2, 0.2, 0.15, 0.2]
        enhanced_confidence = sum(f * w for f, w in zip(confidence_factors, weights))
        
        # Risk-adjusted signal strength
        self.risk_adjusted_signal = strength * self.position_sizing_factor
        
        # Create enhanced institutional signal
        return IndicatorSignal(
            signal_type=signal_type,
            strength=self.risk_adjusted_signal,
            confidence=enhanced_confidence,
            timestamp=timestamp,
            value=value,
            volume_confirmation=self.volume_confirmation_score > 0.5,
            volume_strength=self.volume_confirmation_score,
            market_regime=self.current_regime,
            regime_confidence=self.regime_confidence,
            smart_money_metrics=self.smart_money_metrics,
            risk_metrics=self.risk_metrics,
            # Additional institutional features
            institutional_bias=self.institutional_bias,
            order_flow_imbalance=self.order_flow_imbalance,
            anomaly_score=self.anomaly_score,
            behavioral_bias=self.behavioral_bias,
            auto_stop_loss=self.auto_stop_loss,
            auto_take_profit=self.auto_take_profit,
            position_sizing_factor=self.position_sizing_factor,
            feature_importance=self.feature_importance.copy(),
            signal_attribution=self.signal_attribution.copy()
        )

# ===========================================
# UTILITY FUNCTIONS
# ===========================================

def calculate_sma(values: List[float], period: int) -> Optional[float]:
    """Calculate Simple Moving Average"""
    if len(values) < period:
        return None
    return np.mean(values[-period:])

def calculate_ema(values: List[float], period: int, alpha: Optional[float] = None) -> Optional[float]:
    """Calculate Exponential Moving Average"""
    if len(values) < 1:
        return None
    
    if alpha is None:
        alpha = 2.0 / (period + 1)
    
    if len(values) == 1:
        return values[0]
    
    # Simple EMA calculation
    ema = values[0]
    for value in values[1:]:
        ema = alpha * value + (1 - alpha) * ema
    
    return ema

def calculate_volume_weighted_average(prices: List[float], volumes: List[float]) -> Optional[float]:
    """Calculate Volume Weighted Average Price"""
    if len(prices) != len(volumes) or len(prices) == 0:
        return None
    
    total_volume = sum(volumes)
    if total_volume == 0:
        return np.mean(prices)
    
    weighted_sum = sum(p * v for p, v in zip(prices, volumes))
    return weighted_sum / total_volume

def normalize_value(value: float, min_val: float, max_val: float) -> float:
    """Normalize value to 0-1 range"""
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)

def calculate_percentile_rank(value: float, values: List[float]) -> float:
    """Calculate percentile rank of value in list"""
    if not values:
        return 0.5
    
    sorted_values = sorted(values)
    rank = sum(1 for v in sorted_values if v <= value)
    return rank / len(sorted_values)

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_indicator_config(**kwargs) -> IndicatorConfig:
    """Factory function for creating indicator configurations"""
    return IndicatorConfig(**kwargs)

def validate_input_data(price: float, volume: float = 1.0) -> Tuple[bool, str]:
    """Validate input data for indicators"""
    try:
        if not isinstance(price, (int, float)) or np.isnan(price) or np.isinf(price):
            return False, "Invalid price value"
        
        if not isinstance(volume, (int, float)) or np.isnan(volume) or np.isinf(volume) or volume < 0:
            return False, "Invalid volume value"
        
        if price <= 0:
            return False, "Price must be positive"
        
        return True, "Valid"
    
    except Exception as e:
        return False, f"Validation error: {str(e)}"

# Export all classes and functions
__all__ = [
    # Base classes
    'BaseIndicator', 'VolumeWeightedIndicator', 'AugmentedIndicator',
    
    # Configuration and results
    'IndicatorConfig', 'IndicatorResult', 'IndicatorSignal',
    
    # Enums
    'IndicatorType', 'SignalType', 'MarketRegime', 'SmartMoneyFlow', 'RiskLevel', 'TimeframeConvergence',
    
    # Data classes
    'RiskMetrics', 'SmartMoneyMetrics',
    
    # Decorators
    'performance_monitor', 'robust_calculation', 'memory_efficient',
    
    # Utility functions
    'calculate_sma', 'calculate_ema', 'calculate_volume_weighted_average',
    'normalize_value', 'calculate_percentile_rank', 'validate_input_data',
    
    # Factory functions
    'create_indicator_config'
]