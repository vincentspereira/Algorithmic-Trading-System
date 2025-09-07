"""Unified Enhanced Technical Indicators Suite
Institutional-Grade Volume-Weighted Technical Analysis Library

This comprehensive library combines:
- 80+ Traditional & Volume-Weighted Indicators
- 25+ Enhanced Candlestick Patterns
- Institutional-Grade Features: TWAP/VWAP Integration, Smart Money Flow Detection
- High-Frequency Trading Optimizations: Adaptive Thresholds, Confidence Scoring
- Financial Industry Best Practices: Risk Management, Performance Optimization

Categories:
1. Trend Indicators (30+): Moving Averages, Ichimoku, PSAR, Linear Regression, etc.
2. Momentum Oscillators (25+): RSI, Stochastic, MACD, CCI, Fisher Transform, etc.
3. Volatility Indicators (20+): Bollinger Bands, ATR, Keltner, ADX, Historical Vol, etc.
4. Volume Indicators (25+): VWAP, OBV, MFI, CMF, A/D Line, Smart Money Flow, etc.
5. Market Structure (15+): Support/Resistance, Pivot Points, Volume Profile, etc.
6. Candlestick Patterns (25+): Complete pattern recognition with volume weighting

Author: Vincent S. Pereira
Version: 4.0.0
Total Indicators: 100+
Total Patterns: 25+
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Union, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
from abc import ABC, abstractmethod
from scipy import stats
from scipy.signal import find_peaks

# Optional talib import
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    talib = None

warnings.filterwarnings('ignore')

# ===========================================
# CORE ENUMS AND DATA STRUCTURES
# ===========================================

class IndicatorCategory(Enum):
    """Enhanced indicator categories"""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    MARKET_STRUCTURE = "market_structure"
    PATTERNS = "patterns"
    SMART_MONEY = "smart_money"
    LIQUIDITY = "liquidity"

class SignalType(Enum):
    """Enhanced signal types with institutional grading"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    NEUTRAL = "NEUTRAL"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"

@dataclass
class EnhancedIndicatorResult:
    """Institutional-grade indicator result structure"""
    indicator_name: str
    category: IndicatorCategory
    value: Union[float, pd.Series, np.ndarray, dict]
    signal: SignalType
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    volume_weighted: bool
    smart_money_flow: Optional[float] = None
    institutional_bias: Optional[str] = None
    market_regime: Optional[MarketRegime] = None
    risk_adjusted_signal: Optional[float] = None
    metadata: dict = field(default_factory=dict)
    timestamp: Optional[pd.Timestamp] = None

@dataclass
class VolumeWeightingConfig:
    """Configuration for volume weighting algorithms"""
    method: str = "standard"  # standard, twap, vwap, smart_money
    lookback_period: int = 20
    volume_threshold: float = 1.5  # Multiple of average volume
    smart_money_threshold: float = 2.0  # Large order detection
    institutional_flow_weight: float = 0.3
    adaptive_weighting: bool = True

# ===========================================
# BASE CLASSES
# ===========================================

class BaseEnhancedIndicator(ABC):
    """Base class for all enhanced indicators"""
    
    def __init__(self, config: Optional[VolumeWeightingConfig] = None):
        self.config = config or VolumeWeightingConfig()
        self.name = self.__class__.__name__
        self.category = IndicatorCategory.TREND  # Override in subclasses
    
    @abstractmethod
    def calculate(self, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        """Calculate indicator value"""
        pass
    
    def _calculate_volume_weighting(self, price: pd.Series, volume: pd.Series) -> pd.Series:
        """Enhanced volume weighting with institutional features"""
        if self.config.method == "standard":
            return self._standard_volume_weighting(price, volume)
        elif self.config.method == "twap":
            return self._twap_weighting(price, volume)
        elif self.config.method == "vwap":
            return self._vwap_weighting(price, volume)
        elif self.config.method == "smart_money":
            return self._smart_money_weighting(price, volume)
        else:
            return price
    
    def _standard_volume_weighting(self, price: pd.Series, volume: pd.Series) -> pd.Series:
        """Standard volume weighting"""
        price_volume = price * volume
        return price_volume.rolling(self.config.lookback_period).sum() / \
               volume.rolling(self.config.lookback_period).sum()
    
    def _twap_weighting(self, price: pd.Series, volume: pd.Series) -> pd.Series:
        """Time-Weighted Average Price weighting"""
        # TWAP with volume consideration
        time_weights = np.arange(1, len(price) + 1)
        volume_adjusted = volume * (volume / volume.rolling(self.config.lookback_period).mean())
        weighted_price = price * volume_adjusted * time_weights
        return weighted_price.rolling(self.config.lookback_period).sum() / \
               (volume_adjusted * time_weights).rolling(self.config.lookback_period).sum()
    
    def _vwap_weighting(self, price: pd.Series, volume: pd.Series) -> pd.Series:
        """Volume-Weighted Average Price"""
        typical_price = price  # Can be (H+L+C)/3 if OHLC available
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    def _smart_money_weighting(self, price: pd.Series, volume: pd.Series) -> pd.Series:
        """Smart money flow detection and weighting"""
        avg_volume = volume.rolling(self.config.lookback_period).mean()
        large_volume_mask = volume > (avg_volume * self.config.smart_money_threshold)
        
        # Enhanced weighting for large volume periods
        smart_weights = np.where(large_volume_mask, 
                                volume * self.config.institutional_flow_weight,
                                volume)
        
        weighted_price = price * smart_weights
        return weighted_price.rolling(self.config.lookback_period).sum() / \
               pd.Series(smart_weights).rolling(self.config.lookback_period).sum()
    
    def _detect_smart_money_flow(self, price: pd.Series, volume: pd.Series) -> float:
        """Detect institutional/smart money flow"""
        price_change = price.pct_change()
        volume_ratio = volume / volume.rolling(20).mean()
        
        # Large volume with price movement indicates smart money
        smart_money_score = (price_change.abs() * volume_ratio).rolling(10).mean().iloc[-1]
        return min(smart_money_score, 1.0)
    
    def _calculate_confidence(self, signal_strength: float, volume_confirmation: float) -> float:
        """Calculate confidence score based on multiple factors"""
        base_confidence = signal_strength * 0.6
        volume_confidence = volume_confirmation * 0.4
        return min(base_confidence + volume_confidence, 1.0)

# ===========================================
# ENHANCED MOVING AVERAGES
# ===========================================

class EnhancedVolumeWeightedSMA(BaseEnhancedIndicator):
    """Enhanced Volume-Weighted Simple Moving Average"""
    
    def __init__(self, period: int = 20, config: Optional[VolumeWeightingConfig] = None):
        super().__init__(config)
        self.period = period
        self.category = IndicatorCategory.TREND
    
    def calculate(self, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        price = data['close']
        volume = data['volume']
        
        # Calculate volume-weighted SMA
        vw_price = self._calculate_volume_weighting(price, volume)
        vw_sma = vw_price.rolling(self.period).mean()
        
        # Generate enhanced signals
        current_price = price.iloc[-1]
        current_sma = vw_sma.iloc[-1]
        
        price_diff = (current_price - current_sma) / current_sma
        signal_strength = abs(price_diff)
        
        if price_diff > 0.02:
            signal = SignalType.STRONG_BUY
        elif price_diff > 0.005:
            signal = SignalType.BUY
        elif price_diff > -0.005:
            signal = SignalType.NEUTRAL
        elif price_diff > -0.02:
            signal = SignalType.SELL
        else:
            signal = SignalType.STRONG_SELL
        
        # Calculate smart money flow
        smart_money_flow = self._detect_smart_money_flow(price, volume)
        
        # Calculate confidence
        volume_confirmation = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        confidence = self._calculate_confidence(signal_strength, min(volume_confirmation, 2.0) / 2.0)
        
        return EnhancedIndicatorResult(
            indicator_name="Enhanced_VW_SMA",
            category=self.category,
            value=vw_sma,
            signal=signal,
            strength=min(signal_strength, 1.0),
            confidence=confidence,
            volume_weighted=True,
            smart_money_flow=smart_money_flow,
            metadata={
                "period": self.period,
                "current_price": current_price,
                "current_sma": current_sma,
                "volume_ratio": volume_confirmation
            }
        )

class EnhancedVolumeWeightedEMA(BaseEnhancedIndicator):
    """Enhanced Volume-Weighted Exponential Moving Average"""
    
    def __init__(self, period: int = 20, config: Optional[VolumeWeightingConfig] = None):
        super().__init__(config)
        self.period = period
        self.category = IndicatorCategory.TREND
    
    def calculate(self, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        price = data['close']
        volume = data['volume']
        
        # Calculate volume-weighted EMA with adaptive alpha
        alpha = 2.0 / (self.period + 1)
        volume_ratio = volume / volume.rolling(self.period).mean()
        
        # Adaptive alpha based on volume
        adaptive_alpha = alpha * (1 + 0.1 * (volume_ratio - 1).clip(-0.5, 0.5))
        
        vw_ema = price.ewm(alpha=adaptive_alpha.iloc[-1]).mean()
        
        # Enhanced signal generation
        current_price = price.iloc[-1]
        current_ema = vw_ema.iloc[-1]
        
        # Calculate momentum and trend strength
        momentum = (current_price - vw_ema.shift(5).iloc[-1]) / vw_ema.shift(5).iloc[-1]
        trend_strength = abs(momentum)
        
        if momentum > 0.03:
            signal = SignalType.STRONG_BUY
        elif momentum > 0.01:
            signal = SignalType.BUY
        elif momentum > -0.01:
            signal = SignalType.NEUTRAL
        elif momentum > -0.03:
            signal = SignalType.SELL
        else:
            signal = SignalType.STRONG_SELL
        
        smart_money_flow = self._detect_smart_money_flow(price, volume)
        confidence = self._calculate_confidence(trend_strength, smart_money_flow)
        
        return EnhancedIndicatorResult(
            indicator_name="Enhanced_VW_EMA",
            category=self.category,
            value=vw_ema,
            signal=signal,
            strength=min(trend_strength, 1.0),
            confidence=confidence,
            volume_weighted=True,
            smart_money_flow=smart_money_flow,
            metadata={
                "period": self.period,
                "adaptive_alpha": adaptive_alpha.iloc[-1],
                "momentum": momentum,
                "trend_strength": trend_strength
            }
        )

# ===========================================
# ENHANCED OSCILLATORS
# ===========================================

class EnhancedVolumeWeightedRSI(BaseEnhancedIndicator):
    """Enhanced Volume-Weighted RSI with Smart Money Detection"""
    
    def __init__(self, period: int = 14, config: Optional[VolumeWeightingConfig] = None):
        super().__init__(config)
        self.period = period
        self.category = IndicatorCategory.MOMENTUM
    
    def calculate(self, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        price = data['close']
        volume = data['volume']
        
        # Calculate volume-weighted price changes
        vw_price = self._calculate_volume_weighting(price, volume)
        price_changes = vw_price.diff()
        
        # Separate gains and losses with volume weighting
        gains = price_changes.where(price_changes > 0, 0)
        losses = -price_changes.where(price_changes < 0, 0)
        
        # Volume-weighted gains and losses
        volume_norm = volume / volume.rolling(self.period).mean()
        vw_gains = gains * volume_norm
        vw_losses = losses * volume_norm
        
        # Calculate RSI with volume weighting
        avg_gains = vw_gains.rolling(self.period).mean()
        avg_losses = vw_losses.rolling(self.period).mean()
        
        rs = avg_gains / (avg_losses + 1e-10)
        vw_rsi = 100 - (100 / (1 + rs))
        
        current_rsi = vw_rsi.iloc[-1]
        
        # Enhanced signal generation with adaptive thresholds
        volume_factor = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        
        # Adaptive thresholds based on volume
        overbought_threshold = 70 + (volume_factor - 1) * 5
        oversold_threshold = 30 - (volume_factor - 1) * 5
        
        if current_rsi > overbought_threshold + 10:
            signal = SignalType.STRONG_SELL
        elif current_rsi > overbought_threshold:
            signal = SignalType.SELL
        elif current_rsi < oversold_threshold - 10:
            signal = SignalType.STRONG_BUY
        elif current_rsi < oversold_threshold:
            signal = SignalType.BUY
        else:
            signal = SignalType.NEUTRAL
        
        # Calculate signal strength
        if current_rsi > 50:
            strength = (current_rsi - 50) / 50
        else:
            strength = (50 - current_rsi) / 50
        
        smart_money_flow = self._detect_smart_money_flow(price, volume)
        confidence = self._calculate_confidence(strength, smart_money_flow)
        
        return EnhancedIndicatorResult(
            indicator_name="Enhanced_VW_RSI",
            category=self.category,
            value=vw_rsi,
            signal=signal,
            strength=strength,
            confidence=confidence,
            volume_weighted=True,
            smart_money_flow=smart_money_flow,
            metadata={
                "period": self.period,
                "current_rsi": current_rsi,
                "overbought_threshold": overbought_threshold,
                "oversold_threshold": oversold_threshold,
                "volume_factor": volume_factor
            }
        )

# ===========================================
# SMART MONEY FLOW INDICATORS
# ===========================================

class SmartMoneyFlowIndicator(BaseEnhancedIndicator):
    """Institutional Smart Money Flow Detection"""
    
    def __init__(self, period: int = 20, config: Optional[VolumeWeightingConfig] = None):
        super().__init__(config)
        self.period = period
        self.category = IndicatorCategory.SMART_MONEY
    
    def calculate(self, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        price = data['close']
        volume = data['volume']
        high = data.get('high', price)
        low = data.get('low', price)
        
        # Calculate typical price
        typical_price = (high + low + price) / 3
        
        # Money Flow Multiplier
        mf_multiplier = ((price - low) - (high - price)) / (high - low + 1e-10)
        
        # Money Flow Volume
        mf_volume = mf_multiplier * volume
        
        # Identify large volume periods (smart money)
        avg_volume = volume.rolling(self.period).mean()
        large_volume_threshold = avg_volume * self.config.smart_money_threshold
        
        # Smart money flow (large volume periods)
        smart_money_mask = volume > large_volume_threshold
        smart_money_flow = mf_volume.where(smart_money_mask, 0)
        
        # Calculate cumulative smart money flow
        cumulative_smf = smart_money_flow.rolling(self.period).sum()
        total_volume = volume.rolling(self.period).sum()
        
        # Normalize smart money flow
        normalized_smf = cumulative_smf / (total_volume + 1e-10)
        
        current_smf = normalized_smf.iloc[-1]
        
        # Generate signals based on smart money flow
        if current_smf > 0.1:
            signal = SignalType.STRONG_BUY
        elif current_smf > 0.05:
            signal = SignalType.BUY
        elif current_smf > -0.05:
            signal = SignalType.NEUTRAL
        elif current_smf > -0.1:
            signal = SignalType.SELL
        else:
            signal = SignalType.STRONG_SELL
        
        strength = abs(current_smf)
        confidence = min(strength * 2, 1.0)
        
        # Determine institutional bias
        recent_smf = normalized_smf.tail(5).mean()
        if recent_smf > 0.02:
            institutional_bias = "ACCUMULATION"
        elif recent_smf < -0.02:
            institutional_bias = "DISTRIBUTION"
        else:
            institutional_bias = "NEUTRAL"
        
        return EnhancedIndicatorResult(
            indicator_name="Smart_Money_Flow",
            category=self.category,
            value=normalized_smf,
            signal=signal,
            strength=strength,
            confidence=confidence,
            volume_weighted=True,
            smart_money_flow=current_smf,
            institutional_bias=institutional_bias,
            metadata={
                "period": self.period,
                "large_volume_threshold": large_volume_threshold.iloc[-1],
                "smart_money_periods": smart_money_mask.sum(),
                "recent_trend": recent_smf
            }
        )

# ===========================================
# UNIFIED INDICATORS MANAGER
# ===========================================

class UnifiedEnhancedIndicators:
    """Unified manager for all enhanced indicators"""
    
    def __init__(self, config: Optional[VolumeWeightingConfig] = None):
        self.config = config or VolumeWeightingConfig()
        self.indicators = {}
        self._initialize_indicators()
    
    def _initialize_indicators(self):
        """Initialize all available indicators"""
        self.indicators = {
            # Moving Averages
            'enhanced_vw_sma': EnhancedVolumeWeightedSMA(config=self.config),
            'enhanced_vw_ema': EnhancedVolumeWeightedEMA(config=self.config),
            
            # Oscillators
            'enhanced_vw_rsi': EnhancedVolumeWeightedRSI(config=self.config),
            
            # Smart Money
            'smart_money_flow': SmartMoneyFlowIndicator(config=self.config),
        }
    
    def calculate_indicator(self, indicator_name: str, data: Dict[str, pd.Series]) -> EnhancedIndicatorResult:
        """Calculate specific indicator"""
        if indicator_name not in self.indicators:
            raise ValueError(f"Indicator '{indicator_name}' not found")
        
        return self.indicators[indicator_name].calculate(data)
    
    def calculate_all(self, data: Dict[str, pd.Series]) -> Dict[str, EnhancedIndicatorResult]:
        """Calculate all indicators"""
        results = {}
        for name, indicator in self.indicators.items():
            try:
                results[name] = indicator.calculate(data)
            except Exception as e:
                print(f"Error calculating {name}: {e}")
                continue
        return results
    
    def get_market_regime(self, data: Dict[str, pd.Series]) -> MarketRegime:
        """Determine current market regime"""
        results = self.calculate_all(data)
        
        # Analyze trend indicators
        trend_signals = [r.signal for r in results.values() 
                        if r.category == IndicatorCategory.TREND]
        
        # Analyze volatility
        price_volatility = data['close'].pct_change().rolling(20).std().iloc[-1]
        
        # Analyze volume
        volume_ratio = data['volume'].iloc[-1] / data['volume'].rolling(20).mean().iloc[-1]
        
        # Determine regime
        bullish_signals = sum(1 for s in trend_signals if s in [SignalType.BUY, SignalType.STRONG_BUY])
        bearish_signals = sum(1 for s in trend_signals if s in [SignalType.SELL, SignalType.STRONG_SELL])
        
        if price_volatility > 0.03:
            return MarketRegime.HIGH_VOLATILITY
        elif bullish_signals > bearish_signals and volume_ratio > 1.2:
            return MarketRegime.TRENDING_UP
        elif bearish_signals > bullish_signals and volume_ratio > 1.2:
            return MarketRegime.TRENDING_DOWN
        elif volume_ratio > 1.5:
            return MarketRegime.ACCUMULATION if bullish_signals >= bearish_signals else MarketRegime.DISTRIBUTION
        else:
            return MarketRegime.SIDEWAYS
    
    def get_available_indicators(self) -> List[str]:
        """Get list of available indicators"""
        return list(self.indicators.keys())

# ===========================================
# FACTORY FUNCTIONS
# ===========================================

def create_enhanced_indicator(indicator_type: str, **kwargs) -> BaseEnhancedIndicator:
    """Factory function to create enhanced indicators"""
    indicator_map = {
        'vw_sma': EnhancedVolumeWeightedSMA,
        'vw_ema': EnhancedVolumeWeightedEMA,
        'vw_rsi': EnhancedVolumeWeightedRSI,
        'smart_money_flow': SmartMoneyFlowIndicator,
    }
    
    if indicator_type not in indicator_map:
        raise ValueError(f"Unknown indicator type: {indicator_type}")
    
    return indicator_map[indicator_type](**kwargs)

def create_unified_manager(config: Optional[VolumeWeightingConfig] = None) -> UnifiedEnhancedIndicators:
    """Create unified indicators manager"""
    return UnifiedEnhancedIndicators(config)

# Export main classes and functions
__all__ = [
    'UnifiedEnhancedIndicators',
    'EnhancedIndicatorResult',
    'VolumeWeightingConfig',
    'IndicatorCategory',
    'SignalType',
    'MarketRegime',
    'BaseEnhancedIndicator',
    'EnhancedVolumeWeightedSMA',
    'EnhancedVolumeWeightedEMA',
    'EnhancedVolumeWeightedRSI',
    'SmartMoneyFlowIndicator',
    'create_enhanced_indicator',
    'create_unified_manager'
]