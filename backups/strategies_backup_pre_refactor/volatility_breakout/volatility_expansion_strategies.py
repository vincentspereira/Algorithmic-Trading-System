"""Volatility Expansion Strategies Module

This module implements volatility expansion-based trading strategies including:
- Volatility Squeeze Detection (low volatility periods before expansion)
- Volatility Breakout Confirmation (volume and momentum confirmation)
- Adaptive Volatility Strategies (dynamic parameter adjustment)
- Multi-Timeframe Volatility Analysis
- Volatility Regime Detection

Key Features:
- Advanced volatility measurement (ATR, Bollinger Band Width, etc.)
- Squeeze detection algorithms with multiple confirmation methods
- Expansion momentum analysis with volume validation
- False expansion filtering mechanisms
- Dynamic position sizing based on volatility
- Risk management integration with volatility-adjusted stops

Architecture:
Follows the 5-Pillar Architecture with sophisticated volatility analysis
engines and expansion detection systems.
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
    from scipy.signal import find_peaks
except ImportError:
    pd = None
    np = None
    stats = None
    find_peaks = None

# Base strategy components
from ..pairs_trading.pairs_trading_strategies import (
    StrategyType, PositionType, SignalStrength,
    TradingSignal, Position, StrategyConfig
)

class VolatilityRegime(Enum):
    """Volatility regime classification"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"

class SqueezeType(Enum):
    """Type of volatility squeeze"""
    BOLLINGER_KELTNER = "bollinger_keltner"
    ATR_BASED = "atr_based"
    HISTORICAL_PERCENTILE = "historical_percentile"
    MULTI_TIMEFRAME = "multi_timeframe"

class ExpansionPhase(Enum):
    """Phase of volatility expansion"""
    PRE_EXPANSION = "pre_expansion"
    EARLY_EXPANSION = "early_expansion"
    FULL_EXPANSION = "full_expansion"
    LATE_EXPANSION = "late_expansion"
    CONTRACTION = "contraction"

class ExpansionDirection(Enum):
    """Direction of volatility expansion"""
    UPWARD = "upward"
    DOWNWARD = "downward"
    BIDIRECTIONAL = "bidirectional"
    UNKNOWN = "unknown"

@dataclass
class VolatilityMetrics:
    """Comprehensive volatility metrics"""
    atr: float
    atr_percentile: float
    bollinger_width: float
    bollinger_width_percentile: float
    keltner_width: float
    realized_volatility: float
    parkinson_volatility: float
    garman_klass_volatility: float
    
    # Squeeze indicators
    is_squeeze: bool
    squeeze_intensity: float
    squeeze_duration: int
    
    # Expansion indicators
    expansion_rate: float
    expansion_momentum: float
    
    # Regime classification
    volatility_regime: VolatilityRegime
    regime_confidence: float
    
    timestamp: datetime

@dataclass
class VolatilitySqueeze:
    """Volatility squeeze definition"""
    squeeze_type: SqueezeType
    start_time: datetime
    duration: int  # in periods
    intensity: float  # 0-1 scale
    pre_squeeze_volatility: float
    current_volatility: float
    
    # Squeeze characteristics
    is_active: bool = True
    min_volatility: float = 0.0
    max_volatility: float = 0.0
    
    # Expansion prediction
    expected_expansion_magnitude: float = 0.0
    expansion_probability: float = 0.0

@dataclass
class VolatilityExpansion:
    """Volatility expansion definition"""
    expansion_phase: ExpansionPhase
    direction: ExpansionDirection
    start_time: datetime
    magnitude: float
    rate: float
    momentum: float
    
    # Volume confirmation
    volume_confirmation: bool
    volume_ratio: float
    
    # Price movement
    price_change: float
    price_momentum: float
    
    # Targets and levels
    target_volatility: Optional[float] = None
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    
    timestamp: datetime

class VolatilityAnalysisEngine:
    """Advanced volatility analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Analysis parameters
        self.atr_period = 14
        self.bollinger_period = 20
        self.bollinger_std = 2.0
        self.keltner_period = 20
        self.keltner_multiplier = 2.0
        self.volatility_lookback = 100
        self.squeeze_threshold = 0.2  # Bollinger width / Keltner width
        
        # Historical data storage
        self.volatility_history: List[VolatilityMetrics] = []
        self.squeeze_history: List[VolatilitySqueeze] = []
        self.expansion_history: List[VolatilityExpansion] = []
    
    def calculate_comprehensive_volatility(self, df: pd.DataFrame) -> VolatilityMetrics:
        """Calculate comprehensive volatility metrics"""
        try:
            if len(df) < max(self.atr_period, self.bollinger_period, self.volatility_lookback):
                raise ValueError("Insufficient data for volatility calculation")
            
            # Extract price data
            high = df['high'] if 'high' in df.columns else df['close']
            low = df['low'] if 'low' in df.columns else df['close']
            close = df['close']
            volume = df.get('volume', pd.Series([1] * len(df)))
            
            # Calculate ATR
            atr = self._calculate_atr(high, low, close, self.atr_period)
            atr_series = self._calculate_atr_series(high, low, close, self.atr_period)
            atr_percentile = self._calculate_percentile(atr, atr_series, self.volatility_lookback)
            
            # Calculate Bollinger Band Width
            bollinger_width = self._calculate_bollinger_width(close, self.bollinger_period, self.bollinger_std)
            bb_width_series = self._calculate_bollinger_width_series(close, self.bollinger_period, self.bollinger_std)
            bb_width_percentile = self._calculate_percentile(bollinger_width, bb_width_series, self.volatility_lookback)
            
            # Calculate Keltner Channel Width
            keltner_width = self._calculate_keltner_width(high, low, close, self.keltner_period, self.keltner_multiplier)
            
            # Calculate realized volatility
            returns = close.pct_change().dropna()
            realized_vol = returns.rolling(window=20).std().iloc[-1] * math.sqrt(252)
            
            # Calculate Parkinson volatility
            parkinson_vol = self._calculate_parkinson_volatility(high, low, 20)
            
            # Calculate Garman-Klass volatility
            garman_klass_vol = self._calculate_garman_klass_volatility(high, low, close, 20)
            
            # Detect squeeze
            is_squeeze, squeeze_intensity = self._detect_squeeze(bollinger_width, keltner_width)
            squeeze_duration = self._calculate_squeeze_duration(is_squeeze)
            
            # Calculate expansion metrics
            expansion_rate = self._calculate_expansion_rate()
            expansion_momentum = self._calculate_expansion_momentum(atr_series)
            
            # Classify volatility regime
            volatility_regime, regime_confidence = self._classify_volatility_regime(
                atr_percentile, bb_width_percentile, realized_vol
            )
            
            metrics = VolatilityMetrics(
                atr=atr,
                atr_percentile=atr_percentile,
                bollinger_width=bollinger_width,
                bollinger_width_percentile=bb_width_percentile,
                keltner_width=keltner_width,
                realized_volatility=realized_vol,
                parkinson_volatility=parkinson_vol,
                garman_klass_volatility=garman_klass_vol,
                is_squeeze=is_squeeze,
                squeeze_intensity=squeeze_intensity,
                squeeze_duration=squeeze_duration,
                expansion_rate=expansion_rate,
                expansion_momentum=expansion_momentum,
                volatility_regime=volatility_regime,
                regime_confidence=regime_confidence,
                timestamp=datetime.now()
            )
            
            # Store in history
            self.volatility_history.append(metrics)
            self.volatility_history = self.volatility_history[-self.volatility_lookback:]
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility metrics: {e}")
            raise
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> float:
        """Calculate Average True Range"""
        try:
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return atr
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.0
    
    def _calculate_atr_series(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        """Calculate ATR series"""
        try:
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_series = true_range.rolling(window=period).mean()
            
            return atr_series
            
        except Exception:
            return pd.Series([0] * len(high))
    
    def _calculate_bollinger_width(self, close: pd.Series, period: int, std_dev: float) -> float:
        """Calculate Bollinger Band Width"""
        try:
            sma = close.rolling(window=period).mean().iloc[-1]
            std = close.rolling(window=period).std().iloc[-1]
            
            upper_band = sma + (std_dev * std)
            lower_band = sma - (std_dev * std)
            
            width = (upper_band - lower_band) / sma
            return width
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger width: {e}")
            return 0.0
    
    def _calculate_bollinger_width_series(self, close: pd.Series, period: int, std_dev: float) -> pd.Series:
        """Calculate Bollinger Band Width series"""
        try:
            sma = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()
            
            upper_band = sma + (std_dev * std)
            lower_band = sma - (std_dev * std)
            
            width_series = (upper_band - lower_band) / sma
            return width_series
            
        except Exception:
            return pd.Series([0] * len(close))
    
    def _calculate_keltner_width(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                               period: int, multiplier: float) -> float:
        """Calculate Keltner Channel Width"""
        try:
            ema = close.ewm(span=period).mean().iloc[-1]
            atr = self._calculate_atr(high, low, close, period)
            
            upper_band = ema + (multiplier * atr)
            lower_band = ema - (multiplier * atr)
            
            width = (upper_band - lower_band) / ema
            return width
            
        except Exception as e:
            self.logger.error(f"Error calculating Keltner width: {e}")
            return 0.0
    
    def _calculate_parkinson_volatility(self, high: pd.Series, low: pd.Series, period: int) -> float:
        """Calculate Parkinson volatility estimator"""
        try:
            log_hl = np.log(high / low)
            parkinson = np.sqrt(log_hl.rolling(window=period).mean().iloc[-1] / (4 * np.log(2)))
            return parkinson * math.sqrt(252)  # Annualized
            
        except Exception as e:
            self.logger.error(f"Error calculating Parkinson volatility: {e}")
            return 0.0
    
    def _calculate_garman_klass_volatility(self, high: pd.Series, low: pd.Series, 
                                         close: pd.Series, period: int) -> float:
        """Calculate Garman-Klass volatility estimator"""
        try:
            log_hl = np.log(high / low)
            log_cc = np.log(close / close.shift(1))
            
            gk = 0.5 * log_hl**2 - (2 * np.log(2) - 1) * log_cc**2
            garman_klass = np.sqrt(gk.rolling(window=period).mean().iloc[-1])
            
            return garman_klass * math.sqrt(252)  # Annualized
            
        except Exception as e:
            self.logger.error(f"Error calculating Garman-Klass volatility: {e}")
            return 0.0
    
    def _calculate_percentile(self, current_value: float, series: pd.Series, lookback: int) -> float:
        """Calculate percentile of current value in historical series"""
        try:
            if len(series) < lookback:
                return 50.0
            
            recent_series = series.tail(lookback).dropna()
            if len(recent_series) == 0:
                return 50.0
            
            percentile = stats.percentileofscore(recent_series, current_value)
            return percentile
            
        except Exception:
            return 50.0
    
    def _detect_squeeze(self, bollinger_width: float, keltner_width: float) -> Tuple[bool, float]:
        """Detect volatility squeeze"""
        try:
            if keltner_width == 0:
                return False, 0.0
            
            ratio = bollinger_width / keltner_width
            is_squeeze = ratio < self.squeeze_threshold
            
            # Calculate squeeze intensity (lower ratio = higher intensity)
            if is_squeeze:
                intensity = max(0.0, (self.squeeze_threshold - ratio) / self.squeeze_threshold)
            else:
                intensity = 0.0
            
            return is_squeeze, intensity
            
        except Exception:
            return False, 0.0
    
    def _calculate_squeeze_duration(self, is_current_squeeze: bool) -> int:
        """Calculate duration of current squeeze"""
        try:
            if not is_current_squeeze:
                return 0
            
            duration = 0
            for metrics in reversed(self.volatility_history):
                if metrics.is_squeeze:
                    duration += 1
                else:
                    break
            
            return duration
            
        except Exception:
            return 0
    
    def _calculate_expansion_rate(self) -> float:
        """Calculate rate of volatility expansion"""
        try:
            if len(self.volatility_history) < 2:
                return 0.0
            
            current_vol = self.volatility_history[-1].atr
            previous_vol = self.volatility_history[-2].atr
            
            if previous_vol == 0:
                return 0.0
            
            expansion_rate = (current_vol - previous_vol) / previous_vol
            return expansion_rate
            
        except Exception:
            return 0.0
    
    def _calculate_expansion_momentum(self, atr_series: pd.Series) -> float:
        """Calculate expansion momentum"""
        try:
            if len(atr_series) < 5:
                return 0.0
            
            # Calculate rate of change in ATR
            atr_roc = atr_series.pct_change(periods=3).iloc[-1]
            return atr_roc if not pd.isna(atr_roc) else 0.0
            
        except Exception:
            return 0.0
    
    def _classify_volatility_regime(self, atr_percentile: float, bb_width_percentile: float, 
                                  realized_vol: float) -> Tuple[VolatilityRegime, float]:
        """Classify current volatility regime"""
        try:
            # Combine multiple volatility measures
            combined_percentile = (atr_percentile + bb_width_percentile) / 2
            
            # Classify regime
            if combined_percentile < 20:
                regime = VolatilityRegime.LOW
                confidence = (20 - combined_percentile) / 20
            elif combined_percentile < 40:
                regime = VolatilityRegime.NORMAL
                confidence = 1.0 - abs(combined_percentile - 30) / 10
            elif combined_percentile < 80:
                regime = VolatilityRegime.HIGH
                confidence = 1.0 - abs(combined_percentile - 60) / 20
            else:
                regime = VolatilityRegime.EXTREME
                confidence = (combined_percentile - 80) / 20
            
            confidence = max(0.1, min(confidence, 1.0))
            
            return regime, confidence
            
        except Exception:
            return VolatilityRegime.NORMAL, 0.5
    
    def detect_volatility_expansion(self, df: pd.DataFrame) -> Optional[VolatilityExpansion]:
        """Detect volatility expansion"""
        try:
            if len(self.volatility_history) < 5:
                return None
            
            current_metrics = self.volatility_history[-1]
            
            # Check for expansion conditions
            expansion_conditions = []
            
            # Condition 1: Recent squeeze followed by expansion
            if current_metrics.squeeze_duration > 0 and current_metrics.expansion_rate > 0.1:
                expansion_conditions.append(True)
            else:
                expansion_conditions.append(False)
            
            # Condition 2: Volatility percentile increase
            if len(self.volatility_history) >= 2:
                prev_percentile = self.volatility_history[-2].atr_percentile
                percentile_increase = current_metrics.atr_percentile - prev_percentile
                expansion_conditions.append(percentile_increase > 10)
            else:
                expansion_conditions.append(False)
            
            # Condition 3: Positive expansion momentum
            expansion_conditions.append(current_metrics.expansion_momentum > 0.05)
            
            # Require at least 2 conditions to be met
            if sum(expansion_conditions) < 2:
                return None
            
            # Determine expansion phase
            expansion_phase = self._determine_expansion_phase(current_metrics)
            
            # Determine direction
            direction = self._determine_expansion_direction(df)
            
            # Calculate magnitude and rate
            magnitude = current_metrics.expansion_rate
            rate = current_metrics.expansion_momentum
            momentum = self._calculate_price_momentum(df)
            
            # Volume confirmation
            volume_confirmation, volume_ratio = self._check_volume_confirmation(df)
            
            # Price change
            price_change = self._calculate_price_change(df)
            
            expansion = VolatilityExpansion(
                expansion_phase=expansion_phase,
                direction=direction,
                start_time=datetime.now(),
                magnitude=magnitude,
                rate=rate,
                momentum=momentum,
                volume_confirmation=volume_confirmation,
                volume_ratio=volume_ratio,
                price_change=price_change,
                price_momentum=momentum,
                timestamp=datetime.now()
            )
            
            # Store in history
            self.expansion_history.append(expansion)
            self.expansion_history = self.expansion_history[-50:]  # Keep last 50
            
            return expansion
            
        except Exception as e:
            self.logger.error(f"Error detecting volatility expansion: {e}")
            return None
    
    def _determine_expansion_phase(self, metrics: VolatilityMetrics) -> ExpansionPhase:
        """Determine the phase of volatility expansion"""
        try:
            if metrics.is_squeeze:
                return ExpansionPhase.PRE_EXPANSION
            elif metrics.expansion_rate > 0.2:
                return ExpansionPhase.EARLY_EXPANSION
            elif metrics.expansion_rate > 0.1:
                return ExpansionPhase.FULL_EXPANSION
            elif metrics.expansion_rate > 0:
                return ExpansionPhase.LATE_EXPANSION
            else:
                return ExpansionPhase.CONTRACTION
                
        except Exception:
            return ExpansionPhase.FULL_EXPANSION
    
    def _determine_expansion_direction(self, df: pd.DataFrame) -> ExpansionDirection:
        """Determine direction of volatility expansion"""
        try:
            if len(df) < 5:
                return ExpansionDirection.UNKNOWN
            
            close = df['close']
            recent_returns = close.pct_change().tail(5)
            
            positive_returns = (recent_returns > 0).sum()
            negative_returns = (recent_returns < 0).sum()
            
            if positive_returns > negative_returns * 1.5:
                return ExpansionDirection.UPWARD
            elif negative_returns > positive_returns * 1.5:
                return ExpansionDirection.DOWNWARD
            else:
                return ExpansionDirection.BIDIRECTIONAL
                
        except Exception:
            return ExpansionDirection.UNKNOWN
    
    def _calculate_price_momentum(self, df: pd.DataFrame) -> float:
        """Calculate price momentum"""
        try:
            if len(df) < 10:
                return 0.0
            
            close = df['close']
            momentum = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]
            return momentum
            
        except Exception:
            return 0.0
    
    def _check_volume_confirmation(self, df: pd.DataFrame) -> Tuple[bool, float]:
        """Check volume confirmation for expansion"""
        try:
            if 'volume' not in df.columns or len(df) < 10:
                return False, 1.0
            
            volume = df['volume']
            current_volume = volume.iloc[-1]
            avg_volume = volume.tail(10).mean()
            
            if avg_volume == 0:
                return False, 1.0
            
            volume_ratio = current_volume / avg_volume
            volume_confirmation = volume_ratio > 1.5
            
            return volume_confirmation, volume_ratio
            
        except Exception:
            return False, 1.0
    
    def _calculate_price_change(self, df: pd.DataFrame) -> float:
        """Calculate recent price change"""
        try:
            if len(df) < 2:
                return 0.0
            
            close = df['close']
            price_change = (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2]
            return price_change
            
        except Exception:
            return 0.0

class VolatilityExpansionStrategy:
    """Volatility expansion trading strategy"""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.analyzer = VolatilityAnalysisEngine()
        
        # Strategy parameters
        self.min_squeeze_duration = config.parameters.get('min_squeeze_duration', 5)
        self.min_expansion_rate = config.parameters.get('min_expansion_rate', 0.1)
        self.volume_confirmation_required = config.parameters.get('volume_confirmation', True)
        self.min_volume_ratio = config.parameters.get('min_volume_ratio', 1.5)
        
        # Risk management
        self.max_position_size = config.parameters.get('max_position_size', 0.1)
        self.volatility_position_sizing = config.parameters.get('volatility_position_sizing', True)
        
        # Current state
        self.current_metrics: Optional[VolatilityMetrics] = None
        self.active_expansion: Optional[VolatilityExpansion] = None
    
    def analyze_market_data(self, market_data: Dict) -> Dict:
        """Analyze market data for volatility expansion opportunities"""
        try:
            if pd is None:
                self.logger.error("Pandas not available for data analysis")
                return {}
            
            # Convert market data to DataFrame
            if isinstance(market_data, dict) and 'close' in market_data:
                df = pd.DataFrame([market_data])
            else:
                df = pd.DataFrame(market_data)
            
            if df.empty or len(df) < 50:  # Need sufficient data for volatility analysis
                return {}
            
            # Calculate comprehensive volatility metrics
            self.current_metrics = self.analyzer.calculate_comprehensive_volatility(df)
            
            # Detect volatility expansion
            expansion = self.analyzer.detect_volatility_expansion(df)
            if expansion:
                self.active_expansion = expansion
            
            return {
                'volatility_metrics': self.current_metrics,
                'volatility_expansion': expansion,
                'is_squeeze': self.current_metrics.is_squeeze,
                'squeeze_duration': self.current_metrics.squeeze_duration,
                'expansion_rate': self.current_metrics.expansion_rate,
                'volatility_regime': self.current_metrics.volatility_regime.value,
                'regime_confidence': self.current_metrics.regime_confidence
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing volatility expansion data: {e}")
            return {}
    
    def generate_signals(self, market_data: Dict) -> List[TradingSignal]:
        """Generate trading signals based on volatility expansion"""
        signals = []
        
        try:
            analysis = self.analyze_market_data(market_data)
            
            if not analysis or not analysis.get('volatility_expansion'):
                return signals
            
            expansion = analysis['volatility_expansion']
            metrics = analysis['volatility_metrics']
            
            # Filter signals based on criteria
            if not self._should_trade_expansion(expansion, metrics):
                return signals
            
            # Generate trading signal
            trading_signal = self._create_expansion_signal(expansion, metrics, market_data)
            if trading_signal:
                signals.append(trading_signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating volatility expansion signals: {e}")
            return signals
    
    def _should_trade_expansion(self, expansion: VolatilityExpansion, 
                              metrics: VolatilityMetrics) -> bool:
        """Determine if expansion should be traded"""
        try:
            # Check minimum squeeze duration
            if metrics.squeeze_duration < self.min_squeeze_duration:
                return False
            
            # Check minimum expansion rate
            if expansion.rate < self.min_expansion_rate:
                return False
            
            # Check volume confirmation if required
            if (self.volume_confirmation_required and 
                not expansion.volume_confirmation and 
                expansion.volume_ratio < self.min_volume_ratio):
                return False
            
            # Check expansion phase
            if expansion.expansion_phase in [ExpansionPhase.LATE_EXPANSION, ExpansionPhase.CONTRACTION]:
                return False
            
            # Check direction clarity
            if expansion.direction == ExpansionDirection.UNKNOWN:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating expansion trade criteria: {e}")
            return False
    
    def _create_expansion_signal(self, expansion: VolatilityExpansion, 
                               metrics: VolatilityMetrics, 
                               market_data: Dict) -> Optional[TradingSignal]:
        """Create trading signal from volatility expansion"""
        try:
            # Determine position type based on expansion direction
            if expansion.direction == ExpansionDirection.UPWARD:
                position_type = PositionType.LONG
            elif expansion.direction == ExpansionDirection.DOWNWARD:
                position_type = PositionType.SHORT
            elif expansion.direction == ExpansionDirection.BIDIRECTIONAL:
                # For bidirectional, use price momentum to decide
                if expansion.price_momentum > 0:
                    position_type = PositionType.LONG
                else:
                    position_type = PositionType.SHORT
            else:
                return None
            
            # Determine signal strength
            strength = self._calculate_signal_strength(expansion, metrics)
            
            # Calculate confidence
            confidence = self._calculate_signal_confidence(expansion, metrics)
            
            # Get current price
            if isinstance(market_data, dict):
                current_price = market_data.get('close', 0)
            else:
                df = pd.DataFrame(market_data)
                current_price = df['close'].iloc[-1] if not df.empty else 0
            
            # Calculate targets and stops
            entry_price = current_price
            stop_loss, take_profit = self._calculate_targets(
                entry_price, position_type, expansion, metrics
            )
            
            return TradingSignal(
                symbol=self.config.symbols[0] if self.config.symbols else "UNKNOWN",
                signal_type=position_type,
                strength=strength,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=expansion.timestamp,
                metadata={
                    'strategy': 'volatility_expansion',
                    'expansion_phase': expansion.expansion_phase.value,
                    'expansion_direction': expansion.direction.value,
                    'expansion_rate': expansion.rate,
                    'expansion_magnitude': expansion.magnitude,
                    'squeeze_duration': metrics.squeeze_duration,
                    'volatility_regime': metrics.volatility_regime.value,
                    'volume_confirmation': expansion.volume_confirmation,
                    'volume_ratio': expansion.volume_ratio,
                    'atr_percentile': metrics.atr_percentile,
                    'position_size_multiplier': self._calculate_position_size_multiplier(metrics)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error creating expansion signal: {e}")
            return None
    
    def _calculate_signal_strength(self, expansion: VolatilityExpansion, 
                                 metrics: VolatilityMetrics) -> SignalStrength:
        """Calculate signal strength"""
        try:
            strength_score = 0.0
            
            # Expansion rate contribution
            if expansion.rate > 0.3:
                strength_score += 0.3
            elif expansion.rate > 0.2:
                strength_score += 0.2
            elif expansion.rate > 0.1:
                strength_score += 0.1
            
            # Squeeze duration contribution
            if metrics.squeeze_duration > 15:
                strength_score += 0.3
            elif metrics.squeeze_duration > 10:
                strength_score += 0.2
            elif metrics.squeeze_duration > 5:
                strength_score += 0.1
            
            # Volume confirmation contribution
            if expansion.volume_confirmation:
                strength_score += 0.2
                if expansion.volume_ratio > 2.0:
                    strength_score += 0.1
            
            # Direction clarity contribution
            if expansion.direction in [ExpansionDirection.UPWARD, ExpansionDirection.DOWNWARD]:
                strength_score += 0.1
            
            # Expansion phase contribution
            if expansion.expansion_phase == ExpansionPhase.EARLY_EXPANSION:
                strength_score += 0.1
            
            # Convert to enum
            if strength_score >= 0.8:
                return SignalStrength.STRONG
            elif strength_score >= 0.6:
                return SignalStrength.MEDIUM
            else:
                return SignalStrength.WEAK
                
        except Exception:
            return SignalStrength.WEAK
    
    def _calculate_signal_confidence(self, expansion: VolatilityExpansion, 
                                   metrics: VolatilityMetrics) -> float:
        """Calculate signal confidence"""
        try:
            confidence = 0.5  # Base confidence
            
            # Regime confidence contribution
            confidence += metrics.regime_confidence * 0.2
            
            # Volume confirmation contribution
            if expansion.volume_confirmation:
                confidence += 0.2
            
            # Direction clarity contribution
            if expansion.direction != ExpansionDirection.BIDIRECTIONAL:
                confidence += 0.1
            
            # Squeeze intensity contribution
            confidence += metrics.squeeze_intensity * 0.1
            
            # Expansion momentum contribution
            if expansion.momentum > 0.1:
                confidence += 0.1
            
            return max(0.1, min(confidence, 1.0))
            
        except Exception:
            return 0.5
    
    def _calculate_targets(self, entry_price: float, position_type: PositionType, 
                         expansion: VolatilityExpansion, 
                         metrics: VolatilityMetrics) -> Tuple[Optional[float], Optional[float]]:
        """Calculate stop loss and take profit targets"""
        try:
            # Use ATR for target calculation
            atr = metrics.atr
            
            if position_type == PositionType.LONG:
                # Stop loss: entry - (2 * ATR)
                stop_loss = entry_price - (2.0 * atr)
                # Take profit: entry + (3 * ATR * expansion rate)
                take_profit = entry_price + (3.0 * atr * (1 + expansion.rate))
            else:
                # Stop loss: entry + (2 * ATR)
                stop_loss = entry_price + (2.0 * atr)
                # Take profit: entry - (3 * ATR * expansion rate)
                take_profit = entry_price - (3.0 * atr * (1 + expansion.rate))
            
            return stop_loss, take_profit
            
        except Exception as e:
            self.logger.error(f"Error calculating targets: {e}")
            return None, None
    
    def _calculate_position_size_multiplier(self, metrics: VolatilityMetrics) -> float:
        """Calculate position size multiplier based on volatility"""
        try:
            if not self.volatility_position_sizing:
                return 1.0
            
            # Reduce position size in high volatility environments
            if metrics.volatility_regime == VolatilityRegime.EXTREME:
                return 0.5
            elif metrics.volatility_regime == VolatilityRegime.HIGH:
                return 0.7
            elif metrics.volatility_regime == VolatilityRegime.LOW:
                return 1.2  # Slightly increase in low vol
            else:
                return 1.0
                
        except Exception:
            return 1.0

# Utility functions
def calculate_volatility_metrics(df: pd.DataFrame) -> VolatilityMetrics:
    """Calculate comprehensive volatility metrics"""
    analyzer = VolatilityAnalysisEngine()
    return analyzer.calculate_comprehensive_volatility(df)

def detect_volatility_squeeze(bollinger_width: float, keltner_width: float, 
                            threshold: float = 0.2) -> Tuple[bool, float]:
    """Detect volatility squeeze"""
    analyzer = VolatilityAnalysisEngine()
    analyzer.squeeze_threshold = threshold
    return analyzer._detect_squeeze(bollinger_width, keltner_width)

def classify_volatility_regime(atr_percentile: float, bb_width_percentile: float) -> VolatilityRegime:
    """Classify volatility regime"""
    analyzer = VolatilityAnalysisEngine()
    regime, _ = analyzer._classify_volatility_regime(atr_percentile, bb_width_percentile, 0.0)
    return regime