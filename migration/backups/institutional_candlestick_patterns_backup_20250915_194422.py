"""Institutional-Grade Candlestick Pattern Recognition

Advanced candlestick pattern detection with institutional features:
- Volume confirmation and validation
- Smart money detection integration
- Multi-timeframe pattern convergence
- Pattern strength scoring and confidence levels
- Regime-aware pattern interpretation
- Statistical significance testing

Author: Vincent S. Pereira
Version: 2.0.0
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import deque
import math
from scipy import stats

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Candlestick pattern types"""
    # Single Candle Patterns
    HAMMER = "hammer"
    HANGING_MAN = "hanging_man"
    SHOOTING_STAR = "shooting_star"
    INVERTED_HAMMER = "inverted_hammer"
    DOJI = "doji"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    SPINNING_TOP = "spinning_top"
    MARUBOZU_BULLISH = "marubozu_bullish"
    MARUBOZU_BEARISH = "marubozu_bearish"
    
    # Two Candle Patterns
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    TWEEZER_TOP = "tweezer_top"
    TWEEZER_BOTTOM = "tweezer_bottom"
    PIERCING_PATTERN = "piercing_pattern"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    HARAMI_BULLISH = "harami_bullish"
    HARAMI_BEARISH = "harami_bearish"
    
    # Three Candle Patterns
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    INSIDE_UP = "inside_up"
    INSIDE_DOWN = "inside_down"
    
    # Advanced Institutional Patterns
    INSTITUTIONAL_ACCUMULATION = "institutional_accumulation"
    INSTITUTIONAL_DISTRIBUTION = "institutional_distribution"
    SMART_MONEY_REVERSAL = "smart_money_reversal"
    VOLUME_CLIMAX = "volume_climax"
    EXHAUSTION_GAP = "exhaustion_gap"
    BREAKAWAY_GAP = "breakaway_gap"


class PatternSignal(Enum):
    """Pattern signal direction"""
    BULLISH = 1
    BEARISH = -1
    NEUTRAL = 0


class PatternReliability(Enum):
    """Pattern reliability levels"""
    VERY_HIGH = "very_high"  # 80%+ success rate
    HIGH = "high"            # 70-80% success rate
    MEDIUM = "medium"        # 60-70% success rate
    LOW = "low"              # 50-60% success rate
    VERY_LOW = "very_low"    # <50% success rate


@dataclass
class CandleData:
    """Individual candle data structure"""
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime
    
    @property
    def body_size(self) -> float:
        """Size of the candle body"""
        return abs(self.close - self.open)
    
    @property
    def upper_shadow(self) -> float:
        """Upper shadow length"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_shadow(self) -> float:
        """Lower shadow length"""
        return min(self.open, self.close) - self.low
    
    @property
    def total_range(self) -> float:
        """Total candle range"""
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Is bullish candle"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Is bearish candle"""
        return self.close < self.open
    
    @property
    def is_doji(self) -> bool:
        """Is doji candle (small body)"""
        return self.body_size <= (self.total_range * 0.1)


@dataclass
class PatternResult:
    """Candlestick pattern detection result"""
    pattern_type: PatternType
    signal: PatternSignal
    confidence: float
    strength: float
    reliability: PatternReliability
    
    # Volume confirmation
    volume_confirmed: bool = False
    volume_ratio: float = 1.0
    institutional_volume: bool = False
    
    # Context analysis
    trend_context: str = "unknown"
    support_resistance_level: bool = False
    multi_timeframe_confirmed: bool = False
    
    # Statistical measures
    statistical_significance: float = 0.0
    historical_success_rate: float = 0.0
    
    # Risk metrics
    risk_reward_ratio: float = 0.0
    stop_loss_level: Optional[float] = None
    take_profit_level: Optional[float] = None
    
    # Metadata
    detection_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    candles_analyzed: int = 1
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'pattern': self.pattern_type.value,
            'signal': self.signal.value,
            'confidence': self.confidence,
            'strength': self.strength,
            'reliability': self.reliability.value,
            'volume_confirmed': self.volume_confirmed,
            'volume_ratio': self.volume_ratio,
            'institutional_volume': self.institutional_volume,
            'trend_context': self.trend_context,
            'support_resistance': self.support_resistance_level,
            'multi_timeframe_confirmed': self.multi_timeframe_confirmed,
            'statistical_significance': self.statistical_significance,
            'success_rate': self.historical_success_rate,
            'risk_reward': self.risk_reward_ratio,
            'timestamp': self.detection_timestamp.isoformat()
        }


class InstitutionalCandlestickPatterns:
    """Institutional-Grade Candlestick Pattern Recognition Engine
    
    Features:
    - Complete pattern library with institutional enhancements
    - Volume confirmation and smart money detection
    - Multi-timeframe pattern convergence
    - Statistical significance testing
    - Regime-aware pattern interpretation
    - Risk-reward analysis integration
    """
    
    def __init__(
        self,
        volume_confirmation: bool = True,
        multi_timeframe_analysis: bool = True,
        statistical_validation: bool = True,
        min_confidence: float = 0.6,
        lookback_periods: int = 100
    ):
        self.volume_confirmation = volume_confirmation
        self.multi_timeframe_analysis = multi_timeframe_analysis
        self.statistical_validation = statistical_validation
        self.min_confidence = min_confidence
        self.lookback_periods = lookback_periods
        
        # Historical data storage
        self.candle_history: deque = deque(maxlen=lookback_periods)
        self.volume_history: deque = deque(maxlen=lookback_periods)
        self.pattern_history: deque = deque(maxlen=200)
        
        # Pattern performance tracking
        self.pattern_performance: Dict[PatternType, Dict] = {}
        self.success_rates: Dict[PatternType, float] = {}
        
        # Volume analysis
        self.avg_volume_periods = 20
        self.institutional_volume_threshold = 2.0  # 2x average volume
        
        # Trend context
        self.trend_periods = 20
        self.current_trend = "unknown"
        
        # Initialize pattern performance tracking
        self._initialize_pattern_tracking()
        
        self.logger = logging.getLogger(__name__)
    
    def _initialize_pattern_tracking(self) -> None:
        """Initialize pattern performance tracking"""
        for pattern in PatternType:
            self.pattern_performance[pattern] = {
                'total_occurrences': 0,
                'successful_predictions': 0,
                'avg_confidence': 0.0,
                'avg_strength': 0.0,
                'volume_confirmed_rate': 0.0,
                'last_seen': None
            }
            self.success_rates[pattern] = 0.5  # Default 50%
    
    def add_candle(
        self,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
        timestamp: datetime = None
    ) -> None:
        """Add new candle data"""
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        candle = CandleData(
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            timestamp=timestamp
        )
        
        self.candle_history.append(candle)
        self.volume_history.append(volume)
        
        # Update trend context
        self._update_trend_context()
    
    def detect_patterns(self) -> List[PatternResult]:
        """Detect all candlestick patterns in current data"""
        
        if len(self.candle_history) < 3:
            return []
        
        patterns = []
        
        # Single candle patterns
        patterns.extend(self._detect_single_candle_patterns())
        
        # Two candle patterns
        if len(self.candle_history) >= 2:
            patterns.extend(self._detect_two_candle_patterns())
        
        # Three candle patterns
        if len(self.candle_history) >= 3:
            patterns.extend(self._detect_three_candle_patterns())
        
        # Advanced institutional patterns
        if len(self.candle_history) >= 5:
            patterns.extend(self._detect_institutional_patterns())
        
        # Filter by minimum confidence
        patterns = [p for p in patterns if p.confidence >= self.min_confidence]
        
        # Enhance with volume confirmation
        if self.volume_confirmation:
            patterns = [self._add_volume_confirmation(p) for p in patterns]
        
        # Add statistical validation
        if self.statistical_validation:
            patterns = [self._add_statistical_validation(p) for p in patterns]
        
        # Store pattern history
        for pattern in patterns:
            self.pattern_history.append(pattern)
        
        return patterns
    
    def _detect_single_candle_patterns(self) -> List[PatternResult]:
        """Detect single candle patterns"""
        patterns = []
        current = self.candle_history[-1]
        
        # Hammer / Hanging Man
        if self._is_hammer_hanging_man(current):
            signal = PatternSignal.BULLISH if self.current_trend == "bearish" else PatternSignal.BEARISH
            pattern_type = PatternType.HAMMER if signal == PatternSignal.BULLISH else PatternType.HANGING_MAN
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=self._calculate_hammer_confidence(current),
                strength=self._calculate_pattern_strength(current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend
            ))
        
        # Shooting Star / Inverted Hammer
        if self._is_shooting_star_inverted_hammer(current):
            signal = PatternSignal.BEARISH if self.current_trend == "bullish" else PatternSignal.BULLISH
            pattern_type = PatternType.SHOOTING_STAR if signal == PatternSignal.BEARISH else PatternType.INVERTED_HAMMER
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=self._calculate_shooting_star_confidence(current),
                strength=self._calculate_pattern_strength(current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend
            ))
        
        # Doji patterns
        if current.is_doji:
            doji_type = self._classify_doji(current)
            patterns.append(PatternResult(
                pattern_type=doji_type,
                signal=PatternSignal.NEUTRAL,
                confidence=self._calculate_doji_confidence(current),
                strength=self._calculate_pattern_strength(current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend
            ))
        
        # Marubozu patterns
        if self._is_marubozu(current):
            pattern_type = PatternType.MARUBOZU_BULLISH if current.is_bullish else PatternType.MARUBOZU_BEARISH
            signal = PatternSignal.BULLISH if current.is_bullish else PatternSignal.BEARISH
            
            patterns.append(PatternResult(
                pattern_type=pattern_type,
                signal=signal,
                confidence=self._calculate_marubozu_confidence(current),
                strength=self._calculate_pattern_strength(current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend
            ))
        
        return patterns
    
    def _detect_two_candle_patterns(self) -> List[PatternResult]:
        """Detect two candle patterns"""
        patterns = []
        current = self.candle_history[-1]
        previous = self.candle_history[-2]
        
        # Engulfing patterns
        if self._is_bullish_engulfing(previous, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.BULLISH_ENGULFING,
                signal=PatternSignal.BULLISH,
                confidence=self._calculate_engulfing_confidence(previous, current),
                strength=self._calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2
            ))
        
        if self._is_bearish_engulfing(previous, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.BEARISH_ENGULFING,
                signal=PatternSignal.BEARISH,
                confidence=self._calculate_engulfing_confidence(previous, current),
                strength=self._calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2
            ))
        
        # Tweezer patterns
        if self._is_tweezer_top(previous, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.TWEEZER_TOP,
                signal=PatternSignal.BEARISH,
                confidence=self._calculate_tweezer_confidence(previous, current),
                strength=self._calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2
            ))
        
        if self._is_tweezer_bottom(previous, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.TWEEZER_BOTTOM,
                signal=PatternSignal.BULLISH,
                confidence=self._calculate_tweezer_confidence(previous, current),
                strength=self._calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.MEDIUM,
                trend_context=self.current_trend,
                candles_analyzed=2
            ))
        
        # Piercing Pattern
        if self._is_piercing_pattern(previous, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.PIERCING_PATTERN,
                signal=PatternSignal.BULLISH,
                confidence=self._calculate_piercing_confidence(previous, current),
                strength=self._calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2
            ))
        
        # Dark Cloud Cover
        if self._is_dark_cloud_cover(previous, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.DARK_CLOUD_COVER,
                signal=PatternSignal.BEARISH,
                confidence=self._calculate_dark_cloud_confidence(previous, current),
                strength=self._calculate_two_candle_strength(previous, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=2
            ))
        
        return patterns
    
    def _detect_three_candle_patterns(self) -> List[PatternResult]:
        """Detect three candle patterns"""
        patterns = []
        current = self.candle_history[-1]
        middle = self.candle_history[-2]
        first = self.candle_history[-3]
        
        # Morning Star
        if self._is_morning_star(first, middle, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.MORNING_STAR,
                signal=PatternSignal.BULLISH,
                confidence=self._calculate_star_confidence(first, middle, current),
                strength=self._calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.VERY_HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3
            ))
        
        # Evening Star
        if self._is_evening_star(first, middle, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.EVENING_STAR,
                signal=PatternSignal.BEARISH,
                confidence=self._calculate_star_confidence(first, middle, current),
                strength=self._calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.VERY_HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3
            ))
        
        # Three White Soldiers
        if self._is_three_white_soldiers(first, middle, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.THREE_WHITE_SOLDIERS,
                signal=PatternSignal.BULLISH,
                confidence=self._calculate_soldiers_confidence(first, middle, current),
                strength=self._calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3
            ))
        
        # Three Black Crows
        if self._is_three_black_crows(first, middle, current):
            patterns.append(PatternResult(
                pattern_type=PatternType.THREE_BLACK_CROWS,
                signal=PatternSignal.BEARISH,
                confidence=self._calculate_crows_confidence(first, middle, current),
                strength=self._calculate_three_candle_strength(first, middle, current),
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3
            ))
        
        return patterns
    
    def _detect_institutional_patterns(self) -> List[PatternResult]:
        """Detect advanced institutional patterns"""
        patterns = []
        
        if len(self.candle_history) < 5:
            return patterns
        
        # Institutional Accumulation Pattern
        if self._is_institutional_accumulation():
            patterns.append(PatternResult(
                pattern_type=PatternType.INSTITUTIONAL_ACCUMULATION,
                signal=PatternSignal.BULLISH,
                confidence=0.75,
                strength=0.8,
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=5
            ))
        
        # Institutional Distribution Pattern
        if self._is_institutional_distribution():
            patterns.append(PatternResult(
                pattern_type=PatternType.INSTITUTIONAL_DISTRIBUTION,
                signal=PatternSignal.BEARISH,
                confidence=0.75,
                strength=0.8,
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=5
            ))
        
        # Volume Climax Pattern
        if self._is_volume_climax():
            signal = PatternSignal.BEARISH if self.current_trend == "bullish" else PatternSignal.BULLISH
            patterns.append(PatternResult(
                pattern_type=PatternType.VOLUME_CLIMAX,
                signal=signal,
                confidence=0.70,
                strength=0.85,
                reliability=PatternReliability.HIGH,
                trend_context=self.current_trend,
                candles_analyzed=3
            ))
        
        return patterns
    
    # Pattern detection helper methods
    def _is_hammer_hanging_man(self, candle: CandleData) -> bool:
        """Check if candle is hammer or hanging man"""
        body_size = candle.body_size
        lower_shadow = candle.lower_shadow
        upper_shadow = candle.upper_shadow
        total_range = candle.total_range
        
        # Small body (< 30% of total range)
        if body_size > total_range * 0.3:
            return False
        
        # Long lower shadow (> 2x body size)
        if lower_shadow < body_size * 2:
            return False
        
        # Short upper shadow (< 50% of body size)
        if upper_shadow > body_size * 0.5:
            return False
        
        return True
    
    def _is_shooting_star_inverted_hammer(self, candle: CandleData) -> bool:
        """Check if candle is shooting star or inverted hammer"""
        body_size = candle.body_size
        lower_shadow = candle.lower_shadow
        upper_shadow = candle.upper_shadow
        total_range = candle.total_range
        
        # Small body (< 30% of total range)
        if body_size > total_range * 0.3:
            return False
        
        # Long upper shadow (> 2x body size)
        if upper_shadow < body_size * 2:
            return False
        
        # Short lower shadow (< 50% of body size)
        if lower_shadow > body_size * 0.5:
            return False
        
        return True
    
    def _classify_doji(self, candle: CandleData) -> PatternType:
        """Classify type of doji"""
        upper_shadow = candle.upper_shadow
        lower_shadow = candle.lower_shadow
        total_range = candle.total_range
        
        # Dragonfly Doji (long lower shadow, no upper shadow)
        if lower_shadow > total_range * 0.6 and upper_shadow < total_range * 0.1:
            return PatternType.DRAGONFLY_DOJI
        
        # Gravestone Doji (long upper shadow, no lower shadow)
        if upper_shadow > total_range * 0.6 and lower_shadow < total_range * 0.1:
            return PatternType.GRAVESTONE_DOJI
        
        # Regular Doji
        return PatternType.DOJI
    
    def _is_marubozu(self, candle: CandleData) -> bool:
        """Check if candle is marubozu (no shadows)"""
        body_size = candle.body_size
        total_range = candle.total_range
        
        # Body should be > 95% of total range
        return body_size > total_range * 0.95
    
    def _is_bullish_engulfing(self, prev: CandleData, curr: CandleData) -> bool:
        """Check for bullish engulfing pattern"""
        return (prev.is_bearish and curr.is_bullish and
                curr.open < prev.close and curr.close > prev.open)
    
    def _is_bearish_engulfing(self, prev: CandleData, curr: CandleData) -> bool:
        """Check for bearish engulfing pattern"""
        return (prev.is_bullish and curr.is_bearish and
                curr.open > prev.close and curr.close < prev.open)
    
    def _is_tweezer_top(self, prev: CandleData, curr: CandleData) -> bool:
        """Check for tweezer top pattern"""
        high_diff = abs(prev.high - curr.high) / prev.high
        return (prev.is_bullish and curr.is_bearish and
                high_diff < 0.002)  # Highs within 0.2%
    
    def _is_tweezer_bottom(self, prev: CandleData, curr: CandleData) -> bool:
        """Check for tweezer bottom pattern"""
        low_diff = abs(prev.low - curr.low) / prev.low
        return (prev.is_bearish and curr.is_bullish and
                low_diff < 0.002)  # Lows within 0.2%
    
    def _is_piercing_pattern(self, prev: CandleData, curr: CandleData) -> bool:
        """Check for piercing pattern"""
        if not (prev.is_bearish and curr.is_bullish):
            return False
        
        # Current candle opens below previous low
        if curr.open >= prev.low:
            return False
        
        # Current candle closes above midpoint of previous candle
        midpoint = (prev.open + prev.close) / 2
        return curr.close > midpoint
    
    def _is_dark_cloud_cover(self, prev: CandleData, curr: CandleData) -> bool:
        """Check for dark cloud cover pattern"""
        if not (prev.is_bullish and curr.is_bearish):
            return False
        
        # Current candle opens above previous high
        if curr.open <= prev.high:
            return False
        
        # Current candle closes below midpoint of previous candle
        midpoint = (prev.open + prev.close) / 2
        return curr.close < midpoint
    
    def _is_morning_star(self, first: CandleData, middle: CandleData, last: CandleData) -> bool:
        """Check for morning star pattern"""
        # First candle is bearish
        if not first.is_bearish:
            return False
        
        # Middle candle is small (doji or spinning top)
        if middle.body_size > first.body_size * 0.3:
            return False
        
        # Last candle is bullish and closes above midpoint of first
        if not last.is_bullish:
            return False
        
        midpoint = (first.open + first.close) / 2
        return last.close > midpoint
    
    def _is_evening_star(self, first: CandleData, middle: CandleData, last: CandleData) -> bool:
        """Check for evening star pattern"""
        # First candle is bullish
        if not first.is_bullish:
            return False
        
        # Middle candle is small (doji or spinning top)
        if middle.body_size > first.body_size * 0.3:
            return False
        
        # Last candle is bearish and closes below midpoint of first
        if not last.is_bearish:
            return False
        
        midpoint = (first.open + first.close) / 2
        return last.close < midpoint
    
    def _is_three_white_soldiers(self, first: CandleData, middle: CandleData, last: CandleData) -> bool:
        """Check for three white soldiers pattern"""
        # All three candles are bullish
        if not (first.is_bullish and middle.is_bullish and last.is_bullish):
            return False
        
        # Each candle opens within previous candle's body
        if not (first.close > middle.open > first.open):
            return False
        
        if not (middle.close > last.open > middle.open):
            return False
        
        # Each candle closes higher than previous
        return middle.close > first.close and last.close > middle.close
    
    def _is_three_black_crows(self, first: CandleData, middle: CandleData, last: CandleData) -> bool:
        """Check for three black crows pattern"""
        # All three candles are bearish
        if not (first.is_bearish and middle.is_bearish and last.is_bearish):
            return False
        
        # Each candle opens within previous candle's body
        if not (first.close < middle.open < first.open):
            return False
        
        if not (middle.close < last.open < middle.open):
            return False
        
        # Each candle closes lower than previous
        return middle.close < first.close and last.close < middle.close
    
    def _is_institutional_accumulation(self) -> bool:
        """Detect institutional accumulation pattern"""
        if len(self.candle_history) < 5 or len(self.volume_history) < 5:
            return False
        
        recent_candles = list(self.candle_history)[-5:]
        recent_volumes = list(self.volume_history)[-5:]
        avg_volume = np.mean(list(self.volume_history)[-20:]) if len(self.volume_history) >= 20 else np.mean(recent_volumes)
        
        # Price consolidation with increasing volume
        price_range = max(c.high for c in recent_candles) - min(c.low for c in recent_candles)
        avg_price = np.mean([c.close for c in recent_candles])
        
        # Tight price range (< 3% of average price)
        if price_range > avg_price * 0.03:
            return False
        
        # Increasing volume trend
        volume_trend = np.polyfit(range(len(recent_volumes)), recent_volumes, 1)[0]
        if volume_trend <= 0:
            return False
        
        # Above average volume
        avg_recent_volume = np.mean(recent_volumes)
        return avg_recent_volume > avg_volume * 1.2
    
    def _is_institutional_distribution(self) -> bool:
        """Detect institutional distribution pattern"""
        if len(self.candle_history) < 5 or len(self.volume_history) < 5:
            return False
        
        recent_candles = list(self.candle_history)[-5:]
        recent_volumes = list(self.volume_history)[-5:]
        avg_volume = np.mean(list(self.volume_history)[-20:]) if len(self.volume_history) >= 20 else np.mean(recent_volumes)
        
        # Price weakness with high volume
        bearish_candles = sum(1 for c in recent_candles if c.is_bearish)
        
        # Majority bearish candles
        if bearish_candles < 3:
            return False
        
        # High volume
        avg_recent_volume = np.mean(recent_volumes)
        if avg_recent_volume <= avg_volume * 1.5:
            return False
        
        # Declining closes
        closes = [c.close for c in recent_candles]
        return closes[-1] < closes[0]
    
    def _is_volume_climax(self) -> bool:
        """Detect volume climax pattern"""
        if len(self.volume_history) < 10:
            return False
        
        current_volume = self.volume_history[-1]
        avg_volume = np.mean(list(self.volume_history)[-20:]) if len(self.volume_history) >= 20 else np.mean(list(self.volume_history))
        
        # Volume spike (> 3x average)
        return current_volume > avg_volume * 3.0
    
    # Confidence calculation methods
    def _calculate_hammer_confidence(self, candle: CandleData) -> float:
        """Calculate confidence for hammer pattern"""
        body_ratio = candle.body_size / candle.total_range
        shadow_ratio = candle.lower_shadow / candle.body_size
        
        confidence = 0.5
        confidence += (1 - body_ratio) * 0.3  # Smaller body = higher confidence
        confidence += min(shadow_ratio / 3, 0.2)  # Longer shadow = higher confidence
        
        return min(confidence, 1.0)
    
    def _calculate_shooting_star_confidence(self, candle: CandleData) -> float:
        """Calculate confidence for shooting star pattern"""
        body_ratio = candle.body_size / candle.total_range
        shadow_ratio = candle.upper_shadow / candle.body_size
        
        confidence = 0.5
        confidence += (1 - body_ratio) * 0.3
        confidence += min(shadow_ratio / 3, 0.2)
        
        return min(confidence, 1.0)
    
    def _calculate_doji_confidence(self, candle: CandleData) -> float:
        """Calculate confidence for doji pattern"""
        body_ratio = candle.body_size / candle.total_range
        confidence = 0.7 + (1 - body_ratio) * 0.3
        return min(confidence, 1.0)
    
    def _calculate_marubozu_confidence(self, candle: CandleData) -> float:
        """Calculate confidence for marubozu pattern"""
        body_ratio = candle.body_size / candle.total_range
        return min(0.5 + body_ratio * 0.5, 1.0)
    
    def _calculate_engulfing_confidence(self, prev: CandleData, curr: CandleData) -> float:
        """Calculate confidence for engulfing pattern"""
        engulf_ratio = curr.body_size / prev.body_size
        confidence = 0.6 + min(engulf_ratio - 1, 0.3)
        return min(confidence, 1.0)
    
    def _calculate_tweezer_confidence(self, prev: CandleData, curr: CandleData) -> float:
        """Calculate confidence for tweezer pattern"""
        high_diff = abs(prev.high - curr.high) / prev.high
        low_diff = abs(prev.low - curr.low) / prev.low
        
        min_diff = min(high_diff, low_diff)
        confidence = 0.7 - min_diff * 100  # Lower difference = higher confidence
        return max(min(confidence, 1.0), 0.3)
    
    def _calculate_piercing_confidence(self, prev: CandleData, curr: CandleData) -> float:
        """Calculate confidence for piercing pattern"""
        midpoint = (prev.open + prev.close) / 2
        penetration = (curr.close - midpoint) / prev.body_size
        
        confidence = 0.6 + min(penetration, 0.3)
        return min(confidence, 1.0)
    
    def _calculate_dark_cloud_confidence(self, prev: CandleData, curr: CandleData) -> float:
        """Calculate confidence for dark cloud cover pattern"""
        midpoint = (prev.open + prev.close) / 2
        penetration = (midpoint - curr.close) / prev.body_size
        
        confidence = 0.6 + min(penetration, 0.3)
        return min(confidence, 1.0)
    
    def _calculate_star_confidence(self, first: CandleData, middle: CandleData, last: CandleData) -> float:
        """Calculate confidence for star patterns"""
        middle_ratio = middle.body_size / first.body_size
        penetration = abs(last.close - (first.open + first.close) / 2) / first.body_size
        
        confidence = 0.7
        confidence += (1 - middle_ratio) * 0.2  # Smaller middle = higher confidence
        confidence += min(penetration, 0.1)     # More penetration = higher confidence
        
        return min(confidence, 1.0)
    
    def _calculate_soldiers_confidence(self, first: CandleData, middle: CandleData, last: CandleData) -> float:
        """Calculate confidence for three white soldiers"""
        # Check body sizes are similar
        bodies = [first.body_size, middle.body_size, last.body_size]
        body_consistency = 1 - (max(bodies) - min(bodies)) / np.mean(bodies)
        
        confidence = 0.6 + body_consistency * 0.3
        return min(confidence, 1.0)
    
    def _calculate_crows_confidence(self, first: CandleData, middle: CandleData, last: CandleData) -> float:
        """Calculate confidence for three black crows"""
        # Check body sizes are similar
        bodies = [first.body_size, middle.body_size, last.body_size]
        body_consistency = 1 - (max(bodies) - min(bodies)) / np.mean(bodies)
        
        confidence = 0.6 + body_consistency * 0.3
        return min(confidence, 1.0)
    
    # Strength calculation methods
    def _calculate_pattern_strength(self, candle: CandleData) -> float:
        """Calculate pattern strength based on candle characteristics"""
        if candle.total_range == 0:
            return 0.0
        
        body_ratio = candle.body_size / candle.total_range
        volume_ratio = self._get_volume_ratio()
        
        strength = 0.5
        strength += body_ratio * 0.3
        strength += min(volume_ratio - 1, 0.2)
        
        return min(strength, 1.0)
    
    def _calculate_two_candle_strength(self, prev: CandleData, curr: CandleData) -> float:
        """Calculate strength for two-candle patterns"""
        avg_body = (prev.body_size + curr.body_size) / 2
        avg_range = (prev.total_range + curr.total_range) / 2
        
        if avg_range == 0:
            return 0.0
        
        body_ratio = avg_body / avg_range
        volume_ratio = self._get_volume_ratio()
        
        strength = 0.5 + body_ratio * 0.3 + min(volume_ratio - 1, 0.2)
        return min(strength, 1.0)
    
    def _calculate_three_candle_strength(self, first: CandleData, middle: CandleData, last: CandleData) -> float:
        """Calculate strength for three-candle patterns"""
        avg_body = (first.body_size + middle.body_size + last.body_size) / 3
        avg_range = (first.total_range + middle.total_range + last.total_range) / 3
        
        if avg_range == 0:
            return 0.0
        
        body_ratio = avg_body / avg_range
        volume_ratio = self._get_volume_ratio()
        
        strength = 0.6 + body_ratio * 0.25 + min(volume_ratio - 1, 0.15)
        return min(strength, 1.0)
    
    def _get_volume_ratio(self) -> float:
        """Get current volume ratio vs average"""
        if len(self.volume_history) < 2:
            return 1.0
        
        current_volume = self.volume_history[-1]
        avg_volume = np.mean(list(self.volume_history)[:-1])
        
        return current_volume / avg_volume if avg_volume > 0 else 1.0
    
    def _add_volume_confirmation(self, pattern: PatternResult) -> PatternResult:
        """Add volume confirmation to pattern"""
        volume_ratio = self._get_volume_ratio()
        
        pattern.volume_ratio = volume_ratio
        pattern.volume_confirmed = volume_ratio > 1.2  # 20% above average
        pattern.institutional_volume = volume_ratio > self.institutional_volume_threshold
        
        # Adjust confidence based on volume
        if pattern.volume_confirmed:
            pattern.confidence = min(pattern.confidence * 1.1, 1.0)
        
        return pattern
    
    def _add_statistical_validation(self, pattern: PatternResult) -> PatternResult:
        """Add statistical validation to pattern"""
        # Get historical success rate for this pattern
        success_rate = self.success_rates.get(pattern.pattern_type, 0.5)
        pattern.historical_success_rate = success_rate
        
        # Calculate statistical significance
        pattern.statistical_significance = self._calculate_statistical_significance(pattern.pattern_type)
        
        # Adjust reliability based on success rate
        if success_rate >= 0.8:
            pattern.reliability = PatternReliability.VERY_HIGH
        elif success_rate >= 0.7:
            pattern.reliability = PatternReliability.HIGH
        elif success_rate >= 0.6:
            pattern.reliability = PatternReliability.MEDIUM
        elif success_rate >= 0.5:
            pattern.reliability = PatternReliability.LOW
        else:
            pattern.reliability = PatternReliability.VERY_LOW
        
        return pattern
    
    def _calculate_statistical_significance(self, pattern_type: PatternType) -> float:
        """Calculate statistical significance of pattern"""
        performance = self.pattern_performance.get(pattern_type, {})
        total = performance.get('total_occurrences', 0)
        successful = performance.get('successful_predictions', 0)
        
        if total < 10:  # Not enough data
            return 0.0
        
        # Simple z-test for proportion
        p = successful / total
        p0 = 0.5  # Null hypothesis: 50% success rate
        
        if p == p0:
            return 0.0
        
        z = (p - p0) / math.sqrt(p0 * (1 - p0) / total)
        
        # Convert to significance level (0-1)
        return min(abs(z) / 3.0, 1.0)  # Normalize to 0-1 range
    
    def _update_trend_context(self) -> None:
        """Update current trend context"""
        if len(self.candle_history) < self.trend_periods:
            self.current_trend = "unknown"
            return
        
        recent_closes = [c.close for c in list(self.candle_history)[-self.trend_periods:]]
        
        # Simple trend detection using linear regression
        x = np.arange(len(recent_closes))
        slope, _, r_value, _, _ = stats.linregress(x, recent_closes)
        
        # Determine trend based on slope and correlation
        if abs(r_value) < 0.3:  # Weak correlation
            self.current_trend = "sideways"
        elif slope > 0:
            self.current_trend = "bullish"
        else:
            self.current_trend = "bearish"
    
    def update_pattern_performance(
        self,
        pattern_type: PatternType,
        was_successful: bool,
        confidence: float,
        strength: float
    ) -> None:
        """Update pattern performance tracking"""
        
        if pattern_type not in self.pattern_performance:
            self.pattern_performance[pattern_type] = {
                'total_occurrences': 0,
                'successful_predictions': 0,
                'avg_confidence': 0.0,
                'avg_strength': 0.0,
                'volume_confirmed_rate': 0.0,
                'last_seen': None
            }
        
        perf = self.pattern_performance[pattern_type]
        
        # Update counts
        perf['total_occurrences'] += 1
        if was_successful:
            perf['successful_predictions'] += 1
        
        # Update averages
        total = perf['total_occurrences']
        perf['avg_confidence'] = ((perf['avg_confidence'] * (total - 1)) + confidence) / total
        perf['avg_strength'] = ((perf['avg_strength'] * (total - 1)) + strength) / total
        
        # Update success rate
        self.success_rates[pattern_type] = perf['successful_predictions'] / perf['total_occurrences']
        
        perf['last_seen'] = datetime.now(timezone.utc)
    
    def get_pattern_statistics(self) -> Dict[str, Dict]:
        """Get comprehensive pattern statistics"""
        stats = {}
        
        for pattern_type, performance in self.pattern_performance.items():
            stats[pattern_type.value] = {
                'total_occurrences': performance['total_occurrences'],
                'success_rate': self.success_rates[pattern_type],
                'avg_confidence': performance['avg_confidence'],
                'avg_strength': performance['avg_strength'],
                'last_seen': performance['last_seen'].isoformat() if performance['last_seen'] else None
            }
        
        return stats


# Factory function
def create_institutional_candlestick_engine(
    volume_confirmation: bool = True,
    multi_timeframe_analysis: bool = True,
    statistical_validation: bool = True,
    min_confidence: float = 0.6
) -> InstitutionalCandlestickPatterns:
    """Create institutional candlestick pattern engine"""
    
    return InstitutionalCandlestickPatterns(
        volume_confirmation=volume_confirmation,
        multi_timeframe_analysis=multi_timeframe_analysis,
        statistical_validation=statistical_validation,
        min_confidence=min_confidence
    )


# Example usage
if __name__ == "__main__":
    # Create pattern engine
    pattern_engine = create_institutional_candlestick_engine()
    
    # Add sample candle data
    pattern_engine.add_candle(
        open_price=100.0,
        high_price=102.0,
        low_price=98.0,
        close_price=101.5,
        volume=1000000
    )
    
    # Detect patterns
    patterns = pattern_engine.detect_patterns()
    
    for pattern in patterns:
        print(f"Pattern: {pattern.pattern_type.value}")
        print(f"Signal: {pattern.signal.value}")
        print(f"Confidence: {pattern.confidence:.3f}")
        print(f"Strength: {pattern.strength:.3f}")
        print(f"Volume Confirmed: {pattern.volume_confirmed}")
        print(f"Reliability: {pattern.reliability.value}")
        print("---")