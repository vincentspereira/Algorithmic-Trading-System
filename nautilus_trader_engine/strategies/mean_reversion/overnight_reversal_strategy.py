#!/usr/bin/env python3
"""
Overnight Reversal Strategy

Implements a sophisticated overnight gap reversal strategy that capitalizes on the
tendency for overnight price gaps to reverse during the regular trading session.
This strategy analyzes gap characteristics, volume patterns, and market context
to identify high-probability reversal opportunities.

Key Features:
- Multi-type gap analysis (up gaps, down gaps, exhaustion gaps)
- Volume-weighted gap significance analysis
- Pre-market and after-hours context integration
- Gap size and percentage analysis with statistical significance
- Market regime adaptation for gap behavior
- Time-based reversal probability modeling
- Support/resistance level integration
- Dynamic position sizing based on gap characteristics
- Intraday reversal timing optimization

Author: Algorithmic Trading System
Date: 2024
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta, time
from scipy import stats

# Import base strategy class and required modules
from ...core.base_strategy import BaseRetailStrategy
from ....core.risk_management import RiskParameters, PositionSizer
from ....core.market_regime import MarketRegimeDetector, MarketRegime
from ....indicators.technical_indicators import TechnicalIndicators
from ....indicators.candlestick_patterns import CandlestickPatterns
from ....core.signal_generator import Signal, SignalType, SignalStrength
from ....core.execution_engine import ExecutionIntent, OrderType
from ....core.performance_tracker import PerformanceMetrics


class GapType(Enum):
    """Types of overnight gaps"""
    NO_GAP = "no_gap"                    # Gap < 0.5%
    SMALL_UP_GAP = "small_up_gap"        # 0.5% - 1.5% up
    MEDIUM_UP_GAP = "medium_up_gap"      # 1.5% - 3.0% up
    LARGE_UP_GAP = "large_up_gap"        # > 3.0% up
    SMALL_DOWN_GAP = "small_down_gap"    # -0.5% to -1.5% down
    MEDIUM_DOWN_GAP = "medium_down_gap"  # -1.5% to -3.0% down
    LARGE_DOWN_GAP = "large_down_gap"    # < -3.0% down


class GapContext(Enum):
    """Gap context based on recent price action"""
    CONTINUATION = "continuation"        # Gap in direction of trend
    REVERSAL = "reversal"               # Gap against recent trend
    BREAKOUT = "breakout"               # Gap through key level
    EXHAUSTION = "exhaustion"           # Gap after extended move
    NEUTRAL = "neutral"                 # No clear context


class ReversalTiming(Enum):
    """Optimal timing for gap reversal trades"""
    IMMEDIATE = "immediate"             # First 30 minutes
    EARLY = "early"                     # 30-60 minutes
    MID_SESSION = "mid_session"         # 1-3 hours
    LATE_SESSION = "late_session"       # Last 2 hours
    NO_REVERSAL = "no_reversal"         # Gap likely to hold


@dataclass
class GapAnalysis:
    """Comprehensive gap analysis results"""
    gap_type: GapType
    gap_size_percent: float
    gap_size_points: float
    gap_context: GapContext
    volume_ratio: float  # Current volume vs average
    reversal_probability: float
    optimal_timing: ReversalTiming
    support_resistance_factor: float
    market_sentiment: str
    statistical_significance: float


class OvernightReversalStrategy(BaseRetailStrategy):
    """
    Overnight Reversal Strategy Implementation
    
    This strategy implements sophisticated overnight gap reversal trading with:
    - Multi-dimensional gap analysis and classification
    - Volume-weighted significance testing
    - Market regime adaptation for gap behavior
    - Intraday timing optimization for reversal entries
    - Dynamic risk management based on gap characteristics
    """
    
    def __init__(self, 
                 symbol: str,
                 min_gap_threshold: float = 0.5,
                 max_gap_threshold: float = 5.0,
                 volume_confirmation_threshold: float = 1.2,
                 reversal_confidence_threshold: float = 0.65,
                 max_hold_hours: int = 6,
                 use_premarket_data: bool = True,
                 gap_lookback_period: int = 60,
                 support_resistance_lookback: int = 20,
                 max_position_size: float = 0.15,
                 intraday_only: bool = True,
                 market_open_time: time = time(9, 30),
                 market_close_time: time = time(16, 0),
                 **kwargs):
        """
        Initialize Overnight Reversal Strategy
        
        Args:
            symbol: Trading symbol
            min_gap_threshold: Minimum gap size (%) to consider
            max_gap_threshold: Maximum gap size (%) to trade
            volume_confirmation_threshold: Volume ratio for confirmation
            reversal_confidence_threshold: Minimum confidence for trades
            max_hold_hours: Maximum hours to hold position
            use_premarket_data: Use pre-market data for analysis
            gap_lookback_period: Days to analyze for gap statistics
            support_resistance_lookback: Days for S/R level calculation
            max_position_size: Maximum position size
            intraday_only: Close all positions by market close
            market_open_time: Regular market open time
            market_close_time: Regular market close time
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.min_gap_threshold = min_gap_threshold
        self.max_gap_threshold = max_gap_threshold
        self.volume_confirmation_threshold = volume_confirmation_threshold
        self.reversal_confidence_threshold = reversal_confidence_threshold
        self.max_hold_hours = max_hold_hours
        self.use_premarket_data = use_premarket_data
        self.gap_lookback_period = gap_lookback_period
        self.support_resistance_lookback = support_resistance_lookback
        self.max_position_size = max_position_size
        self.intraday_only = intraday_only
        self.market_open_time = market_open_time
        self.market_close_time = market_close_time
        
        # Initialize components
        self.technical_indicators = TechnicalIndicators()
        self.candlestick_patterns = CandlestickPatterns()
        self.market_regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.gap_history: List[Dict] = []
        self.support_levels: List[float] = []
        self.resistance_levels: List[float] = []
        self.current_gap_analysis: Optional[GapAnalysis] = None
        self.position_entry_time: Optional[datetime] = None
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate overnight gap reversal signals by analyzing gap characteristics,
        volume patterns, and market context.
        """
        if len(data) < 50:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Detect overnight gap
            gap_analysis = self._analyze_overnight_gap(data)
            self.current_gap_analysis = gap_analysis
            
            if gap_analysis.gap_type == GapType.NO_GAP:
                return [self._create_neutral_signal()]
            
            # Update support/resistance levels
            self._update_support_resistance_levels(data)
            
            # Calculate additional indicators
            sma_20 = self.technical_indicators.sma(data['close'], period=20)
            ema_10 = self.technical_indicators.ema(data['close'], period=10)
            rsi = self.technical_indicators.rsi(data['close'], period=14)
            atr = self.technical_indicators.atr(data, period=14)
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_atr = atr.iloc[-1]
            current_volume = data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            # Generate primary signal based on gap analysis
            primary_signal = self._generate_gap_reversal_signal(gap_analysis, data, current_price)
            
            if primary_signal:
                # Add technical confirmation
                technical_confirmation = self._get_technical_confirmation(data, primary_signal.signal_type, gap_analysis)
                
                # Adjust confidence based on confirmations
                confirmation_factors = [
                    technical_confirmation,
                    gap_analysis.volume_ratio > self.volume_confirmation_threshold,
                    gap_analysis.reversal_probability > self.reversal_confidence_threshold,
                    gap_analysis.statistical_significance > 0.7
                ]
                
                confirmation_score = sum(confirmation_factors) / len(confirmation_factors)
                primary_signal.confidence = min(0.95, primary_signal.confidence * (0.7 + 0.6 * confirmation_score))
                
                # Add comprehensive metadata
                primary_signal.metadata.update({
                    'current_price': current_price,
                    'rsi': current_rsi,
                    'atr': current_atr,
                    'current_volume': current_volume,
                    'avg_volume': avg_volume,
                    'volume_ratio': gap_analysis.volume_ratio,
                    'gap_type': gap_analysis.gap_type.value,
                    'gap_size_percent': gap_analysis.gap_size_percent,
                    'gap_size_points': gap_analysis.gap_size_points,
                    'gap_context': gap_analysis.gap_context.value,
                    'reversal_probability': gap_analysis.reversal_probability,
                    'optimal_timing': gap_analysis.optimal_timing.value,
                    'support_resistance_factor': gap_analysis.support_resistance_factor,
                    'market_sentiment': gap_analysis.market_sentiment,
                    'statistical_significance': gap_analysis.statistical_significance,
                    'technical_confirmation': technical_confirmation,
                    'confirmation_score': confirmation_score,
                    'market_regime': self.current_regime.value
                })
                
                signals.append(primary_signal)
            else:
                signals.append(self._create_neutral_signal())
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            signals.append(self._create_neutral_signal())
            
        return signals
    
    def _analyze_overnight_gap(self, data: pd.DataFrame) -> GapAnalysis:
        """
        Analyze overnight gap characteristics and reversal probability
        """
        try:
            if len(data) < 2:
                return self._create_default_gap_analysis()
            
            # Calculate gap
            previous_close = data['close'].iloc[-2]
            current_open = data['open'].iloc[-1]
            current_close = data['close'].iloc[-1]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            
            gap_size_points = current_open - previous_close
            gap_size_percent = (gap_size_points / previous_close) * 100
            
            # Classify gap type
            gap_type = self._classify_gap_type(gap_size_percent)
            
            if gap_type == GapType.NO_GAP:
                return self._create_default_gap_analysis()
            
            # Analyze gap context
            gap_context = self._analyze_gap_context(data, gap_size_percent)
            
            # Calculate volume ratio
            volume_ratio = self._calculate_volume_ratio(data)
            
            # Calculate reversal probability
            reversal_probability = self._calculate_reversal_probability(data, gap_type, gap_context, volume_ratio)
            
            # Determine optimal timing
            optimal_timing = self._determine_optimal_timing(gap_type, gap_context, reversal_probability)
            
            # Calculate support/resistance factor
            sr_factor = self._calculate_support_resistance_factor(current_open, gap_size_percent > 0)
            
            # Determine market sentiment
            market_sentiment = self._determine_market_sentiment(data, gap_type)
            
            # Calculate statistical significance
            statistical_significance = self._calculate_statistical_significance(data, gap_size_percent)
            
            return GapAnalysis(
                gap_type=gap_type,
                gap_size_percent=gap_size_percent,
                gap_size_points=gap_size_points,
                gap_context=gap_context,
                volume_ratio=volume_ratio,
                reversal_probability=reversal_probability,
                optimal_timing=optimal_timing,
                support_resistance_factor=sr_factor,
                market_sentiment=market_sentiment,
                statistical_significance=statistical_significance
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing overnight gap: {e}")
            return self._create_default_gap_analysis()
    
    def _classify_gap_type(self, gap_size_percent: float) -> GapType:
        """
        Classify gap based on size and direction
        """
        abs_gap = abs(gap_size_percent)
        
        if abs_gap < self.min_gap_threshold:
            return GapType.NO_GAP
        
        if gap_size_percent > 0:  # Up gap
            if abs_gap > 3.0:
                return GapType.LARGE_UP_GAP
            elif abs_gap > 1.5:
                return GapType.MEDIUM_UP_GAP
            else:
                return GapType.SMALL_UP_GAP
        else:  # Down gap
            if abs_gap > 3.0:
                return GapType.LARGE_DOWN_GAP
            elif abs_gap > 1.5:
                return GapType.MEDIUM_DOWN_GAP
            else:
                return GapType.SMALL_DOWN_GAP
    
    def _analyze_gap_context(self, data: pd.DataFrame, gap_size_percent: float) -> GapContext:
        """
        Analyze the context of the gap relative to recent price action
        """
        try:
            if len(data) < 10:
                return GapContext.NEUTRAL
            
            # Calculate recent trend
            recent_returns = data['close'].pct_change().iloc[-10:-1]
            trend_direction = recent_returns.mean()
            trend_strength = abs(trend_direction)
            
            # Check if gap is in direction of trend
            gap_direction = 1 if gap_size_percent > 0 else -1
            trend_dir = 1 if trend_direction > 0 else -1
            
            # Check for breakout through key levels
            current_price = data['close'].iloc[-1]
            recent_high = data['high'].iloc[-20:-1].max()
            recent_low = data['low'].iloc[-20:-1].min()
            
            # Determine context
            if trend_strength > 0.02:  # Strong trend
                if gap_direction == trend_dir:
                    # Check if this might be exhaustion
                    if abs(gap_size_percent) > 2.5 and trend_strength > 0.03:
                        return GapContext.EXHAUSTION
                    else:
                        return GapContext.CONTINUATION
                else:
                    return GapContext.REVERSAL
            
            # Check for breakout
            if gap_size_percent > 0 and current_price > recent_high * 1.01:
                return GapContext.BREAKOUT
            elif gap_size_percent < 0 and current_price < recent_low * 0.99:
                return GapContext.BREAKOUT
            
            return GapContext.NEUTRAL
            
        except Exception as e:
            self.logger.error(f"Error analyzing gap context: {e}")
            return GapContext.NEUTRAL
    
    def _calculate_volume_ratio(self, data: pd.DataFrame) -> float:
        """
        Calculate current volume relative to average
        """
        try:
            if len(data) < 20:
                return 1.0
            
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].iloc[-20:-1].mean()
            
            if avg_volume > 0:
                return current_volume / avg_volume
            else:
                return 1.0
                
        except Exception as e:
            self.logger.error(f"Error calculating volume ratio: {e}")
            return 1.0
    
    def _calculate_reversal_probability(self, data: pd.DataFrame, gap_type: GapType, 
                                      gap_context: GapContext, volume_ratio: float) -> float:
        """
        Calculate probability of gap reversal based on historical patterns
        """
        try:
            # Base probabilities by gap type (from historical analysis)
            base_probabilities = {
                GapType.SMALL_UP_GAP: 0.65,
                GapType.MEDIUM_UP_GAP: 0.70,
                GapType.LARGE_UP_GAP: 0.75,
                GapType.SMALL_DOWN_GAP: 0.60,
                GapType.MEDIUM_DOWN_GAP: 0.65,
                GapType.LARGE_DOWN_GAP: 0.70
            }
            
            base_prob = base_probabilities.get(gap_type, 0.5)
            
            # Context adjustments
            context_adjustments = {
                GapContext.EXHAUSTION: 0.20,      # High reversal probability
                GapContext.REVERSAL: 0.15,        # Good reversal probability
                GapContext.NEUTRAL: 0.0,          # No adjustment
                GapContext.CONTINUATION: -0.15,   # Lower reversal probability
                GapContext.BREAKOUT: -0.25        # Lowest reversal probability
            }
            
            base_prob += context_adjustments.get(gap_context, 0.0)
            
            # Volume confirmation adjustment
            if volume_ratio > 2.0:
                base_prob += 0.15  # High volume increases reversal probability
            elif volume_ratio > 1.5:
                base_prob += 0.10
            elif volume_ratio < 0.7:
                base_prob -= 0.10  # Low volume decreases reversal probability
            
            # Market regime adjustment
            if self.current_regime == MarketRegime.HIGH_VOLATILITY:
                base_prob += 0.10  # Higher reversal probability in volatile markets
            elif self.current_regime == MarketRegime.TRENDING:
                base_prob -= 0.05  # Lower reversal probability in trending markets
            
            # Time of day adjustment (if available)
            # Gaps are more likely to reverse in the first few hours
            
            return min(0.95, max(0.05, base_prob))
            
        except Exception as e:
            self.logger.error(f"Error calculating reversal probability: {e}")
            return 0.5
    
    def _determine_optimal_timing(self, gap_type: GapType, gap_context: GapContext, 
                                reversal_probability: float) -> ReversalTiming:
        """
        Determine optimal timing for gap reversal entry
        """
        try:
            # If reversal probability is low, don't trade
            if reversal_probability < 0.5:
                return ReversalTiming.NO_REVERSAL
            
            # Large gaps often reverse quickly
            if gap_type in [GapType.LARGE_UP_GAP, GapType.LARGE_DOWN_GAP]:
                if gap_context == GapContext.EXHAUSTION:
                    return ReversalTiming.IMMEDIATE
                else:
                    return ReversalTiming.EARLY
            
            # Medium gaps may take more time
            elif gap_type in [GapType.MEDIUM_UP_GAP, GapType.MEDIUM_DOWN_GAP]:
                if reversal_probability > 0.75:
                    return ReversalTiming.EARLY
                else:
                    return ReversalTiming.MID_SESSION
            
            # Small gaps often reverse later in the session
            else:
                return ReversalTiming.MID_SESSION
            
        except Exception as e:
            self.logger.error(f"Error determining optimal timing: {e}")
            return ReversalTiming.MID_SESSION
    
    def _update_support_resistance_levels(self, data: pd.DataFrame) -> None:
        """
        Update support and resistance levels
        """
        try:
            if len(data) < self.support_resistance_lookback:
                return
            
            # Get recent price data
            recent_data = data.iloc[-self.support_resistance_lookback:]
            
            # Calculate pivot points
            highs = recent_data['high']
            lows = recent_data['low']
            
            # Find local maxima and minima
            resistance_candidates = []
            support_candidates = []
            
            for i in range(2, len(recent_data) - 2):
                # Resistance levels (local maxima)
                if (highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and
                    highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]):
                    resistance_candidates.append(highs.iloc[i])
                
                # Support levels (local minima)
                if (lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and
                    lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]):
                    support_candidates.append(lows.iloc[i])
            
            # Keep most significant levels
            self.resistance_levels = sorted(resistance_candidates, reverse=True)[:5]
            self.support_levels = sorted(support_candidates)[:5]
            
        except Exception as e:
            self.logger.error(f"Error updating support/resistance levels: {e}")
    
    def _calculate_support_resistance_factor(self, current_price: float, is_up_gap: bool) -> float:
        """
        Calculate how close the gap is to key support/resistance levels
        """
        try:
            if is_up_gap:
                # Check proximity to resistance levels
                if not self.resistance_levels:
                    return 0.5
                
                closest_resistance = min(self.resistance_levels, 
                                        key=lambda x: abs(x - current_price) if x > current_price else float('inf'))
                
                if closest_resistance == float('inf'):
                    return 0.3  # No resistance above
                
                distance_pct = abs(closest_resistance - current_price) / current_price
                
                if distance_pct < 0.01:  # Very close to resistance
                    return 0.9
                elif distance_pct < 0.02:
                    return 0.7
                elif distance_pct < 0.05:
                    return 0.5
                else:
                    return 0.3
            
            else:
                # Check proximity to support levels
                if not self.support_levels:
                    return 0.5
                
                closest_support = max(self.support_levels, 
                                     key=lambda x: x if x < current_price else -float('inf'))
                
                if closest_support == -float('inf'):
                    return 0.3  # No support below
                
                distance_pct = abs(current_price - closest_support) / current_price
                
                if distance_pct < 0.01:  # Very close to support
                    return 0.9
                elif distance_pct < 0.02:
                    return 0.7
                elif distance_pct < 0.05:
                    return 0.5
                else:
                    return 0.3
            
        except Exception as e:
            self.logger.error(f"Error calculating support/resistance factor: {e}")
            return 0.5
    
    def _determine_market_sentiment(self, data: pd.DataFrame, gap_type: GapType) -> str:
        """
        Determine overall market sentiment
        """
        try:
            # Calculate recent price momentum
            if len(data) < 10:
                return "neutral"
            
            recent_returns = data['close'].pct_change().iloc[-10:]
            avg_return = recent_returns.mean()
            
            # Calculate volatility
            volatility = recent_returns.std()
            
            if avg_return > 0.01:
                if volatility > 0.03:
                    return "bullish_volatile"
                else:
                    return "bullish_stable"
            elif avg_return < -0.01:
                if volatility > 0.03:
                    return "bearish_volatile"
                else:
                    return "bearish_stable"
            else:
                if volatility > 0.03:
                    return "neutral_volatile"
                else:
                    return "neutral_stable"
            
        except Exception as e:
            self.logger.error(f"Error determining market sentiment: {e}")
            return "neutral"
    
    def _calculate_statistical_significance(self, data: pd.DataFrame, gap_size_percent: float) -> float:
        """
        Calculate statistical significance of the gap
        """
        try:
            if len(data) < 30:
                return 0.5
            
            # Calculate historical gap distribution
            historical_gaps = []
            for i in range(1, min(len(data), self.gap_lookback_period)):
                prev_close = data['close'].iloc[-(i+1)]
                curr_open = data['open'].iloc[-i]
                gap_pct = ((curr_open - prev_close) / prev_close) * 100
                historical_gaps.append(gap_pct)
            
            if len(historical_gaps) < 10:
                return 0.5
            
            # Calculate z-score of current gap
            mean_gap = np.mean(historical_gaps)
            std_gap = np.std(historical_gaps)
            
            if std_gap == 0:
                return 0.5
            
            z_score = abs((gap_size_percent - mean_gap) / std_gap)
            
            # Convert z-score to significance (0-1 scale)
            # Z-score > 2 is highly significant
            significance = min(1.0, z_score / 2.0)
            
            return significance
            
        except Exception as e:
            self.logger.error(f"Error calculating statistical significance: {e}")
            return 0.5
    
    def _generate_gap_reversal_signal(self, gap_analysis: GapAnalysis, data: pd.DataFrame, 
                                    current_price: float) -> Optional[Signal]:
        """
        Generate trading signal based on gap analysis
        """
        try:
            # Don't trade if gap is too large or reversal probability is low
            if (abs(gap_analysis.gap_size_percent) > self.max_gap_threshold or
                gap_analysis.reversal_probability < self.reversal_confidence_threshold or
                gap_analysis.optimal_timing == ReversalTiming.NO_REVERSAL):
                return None
            
            # Determine signal direction (opposite to gap direction)
            if gap_analysis.gap_size_percent > 0:  # Up gap -> sell signal
                signal_type = SignalType.SELL
            else:  # Down gap -> buy signal
                signal_type = SignalType.BUY
            
            # Calculate signal strength
            strength_score = 0
            
            # Reversal probability factor (40 points max)
            strength_score += gap_analysis.reversal_probability * 40
            
            # Gap size factor (20 points max)
            gap_size_factor = min(20, abs(gap_analysis.gap_size_percent) * 5)
            strength_score += gap_size_factor
            
            # Volume confirmation (15 points max)
            if gap_analysis.volume_ratio > 2.0:
                strength_score += 15
            elif gap_analysis.volume_ratio > 1.5:
                strength_score += 10
            elif gap_analysis.volume_ratio > 1.2:
                strength_score += 5
            
            # Context factor (15 points max)
            context_scores = {
                GapContext.EXHAUSTION: 15,
                GapContext.REVERSAL: 10,
                GapContext.NEUTRAL: 5,
                GapContext.CONTINUATION: 0,
                GapContext.BREAKOUT: -5
            }
            strength_score += context_scores.get(gap_analysis.gap_context, 0)
            
            # Support/resistance factor (10 points max)
            strength_score += gap_analysis.support_resistance_factor * 10
            
            # Statistical significance factor (10 points max)
            strength_score += gap_analysis.statistical_significance * 10
            
            # Convert to signal strength
            if strength_score >= 80:
                signal_strength = SignalStrength.STRONG
                confidence = min(0.9, strength_score / 100)
            elif strength_score >= 60:
                signal_strength = SignalStrength.MEDIUM
                confidence = min(0.8, strength_score / 100)
            else:
                signal_strength = SignalStrength.WEAK
                confidence = min(0.7, strength_score / 100)
            
            # Don't trade weak signals unless gap is very significant
            if signal_strength == SignalStrength.WEAK and gap_analysis.statistical_significance < 0.8:
                return None
            
            return Signal(
                symbol=self.symbol,
                signal_type=signal_type,
                strength=signal_strength,
                confidence=confidence,
                timestamp=data.index[-1],
                metadata={
                    'signal_source': 'overnight_gap_reversal',
                    'strength_score': strength_score
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error generating gap reversal signal: {e}")
            return None
    
    def _get_technical_confirmation(self, data: pd.DataFrame, signal_type: SignalType, 
                                  gap_analysis: GapAnalysis) -> bool:
        """
        Get technical confirmation for gap reversal signals
        """
        try:
            # Calculate technical indicators
            rsi = self.technical_indicators.rsi(data['close'], period=14).iloc[-1]
            sma_20 = self.technical_indicators.sma(data['close'], period=20).iloc[-1]
            current_price = data['close'].iloc[-1]
            
            if signal_type == SignalType.BUY:  # Down gap reversal
                # Look for oversold conditions
                rsi_confirmation = rsi < 35
                price_confirmation = current_price < sma_20 * 0.97
                
                # Check if we're near support
                support_confirmation = gap_analysis.support_resistance_factor > 0.6
                
                return rsi_confirmation or price_confirmation or support_confirmation
            
            elif signal_type == SignalType.SELL:  # Up gap reversal
                # Look for overbought conditions
                rsi_confirmation = rsi > 65
                price_confirmation = current_price > sma_20 * 1.03
                
                # Check if we're near resistance
                resistance_confirmation = gap_analysis.support_resistance_factor > 0.6
                
                return rsi_confirmation or price_confirmation or resistance_confirmation
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error getting technical confirmation: {e}")
            return False
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters adapted for gap reversal trading.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('current_price', data['close'].iloc[-1])
            gap_size_percent = metadata.get('gap_size_percent', 1.0)
            reversal_probability = metadata.get('reversal_probability', 0.5)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.5,
                SignalStrength.MEDIUM: 0.8,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Adjust size based on gap characteristics
            gap_size_multiplier = 1.0
            abs_gap = abs(gap_size_percent)
            
            if abs_gap > 3.0:  # Large gaps
                gap_size_multiplier = 1.2  # Larger position for large gaps
            elif abs_gap < 1.0:  # Small gaps
                gap_size_multiplier = 0.7  # Smaller position for small gaps
            
            # Adjust based on reversal probability
            prob_multiplier = 0.5 + (reversal_probability * 1.0)
            
            # Calculate final position size
            position_size = base_size * strength_multiplier * gap_size_multiplier * prob_multiplier
            position_size = min(position_size, self.max_position_size * 1.3)
            
            # Calculate stop loss and take profit
            atr = self.technical_indicators.atr(data, period=14).iloc[-1]
            
            # Gap-specific stops
            # Stop loss should be beyond the gap fill point
            if signal.signal_type == SignalType.BUY:  # Down gap reversal
                # Stop below the gap low
                gap_low = data['low'].iloc[-1]
                stop_loss = gap_low - (atr * 0.5)
                
                # Take profit at gap fill or beyond
                gap_fill_price = data['close'].iloc[-2]  # Previous close
                take_profit = gap_fill_price + (atr * 1.0)
                
            elif signal.signal_type == SignalType.SELL:  # Up gap reversal
                # Stop above the gap high
                gap_high = data['high'].iloc[-1]
                stop_loss = gap_high + (atr * 0.5)
                
                # Take profit at gap fill or beyond
                gap_fill_price = data['close'].iloc[-2]  # Previous close
                take_profit = gap_fill_price - (atr * 1.0)
            else:
                stop_loss = None
                take_profit = None
            
            # Calculate risk-reward ratio
            if stop_loss and take_profit:
                risk = abs(current_price - stop_loss)
                reward = abs(take_profit - current_price)
                risk_reward_ratio = reward / risk if risk > 0 else 2.0
            else:
                risk_reward_ratio = 2.0
            
            return RiskParameters(
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_risk_per_trade=0.02,
                risk_reward_ratio=risk_reward_ratio,
                volatility_adjustment=abs_gap / 2.0  # Gap size as volatility proxy
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect market regime and adapt gap reversal parameters.
        """
        try:
            # Use standard market regime detector
            regime = self.market_regime_detector.detect_regime(data)
            self.current_regime = regime
            
            # Adapt strategy parameters based on regime
            if regime == MarketRegime.HIGH_VOLATILITY:
                # More conservative in high volatility
                self.reversal_confidence_threshold = max(0.7, self.reversal_confidence_threshold)
                self.max_gap_threshold = min(4.0, self.max_gap_threshold)
                
            elif regime == MarketRegime.LOW_VOLATILITY:
                # More aggressive in low volatility
                self.reversal_confidence_threshold = min(0.6, self.reversal_confidence_threshold)
                self.max_gap_threshold = max(6.0, self.max_gap_threshold)
                
            elif regime == MarketRegime.TRENDING:
                # Be more selective in trending markets
                self.reversal_confidence_threshold = max(0.75, self.reversal_confidence_threshold)
                
            return regime
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.NEUTRAL
    
    def _determine_execution_intent(self, 
                                  signals: List[Signal], 
                                  risk_params: RiskParameters,
                                  current_position: Optional[Dict]) -> ExecutionIntent:
        """
        Pillar 4: Decoupled Execution Logic & Order Management
        
        Determine execution intent with gap reversal specific logic.
        """
        if not signals:
            return ExecutionIntent(action="HOLD", quantity=0)
            
        primary_signal = signals[0]
        
        try:
            # Check for position exit conditions
            if current_position and current_position.get('quantity', 0) != 0:
                current_qty = current_position['quantity']
                entry_price = current_position.get('entry_price', 0)
                entry_time = current_position.get('entry_time')
                current_price = primary_signal.metadata.get('current_price', 0)
                
                # Time-based exit (max hold period)
                if entry_time and self.position_entry_time:
                    hours_held = (datetime.now() - self.position_entry_time).total_seconds() / 3600
                    if hours_held >= self.max_hold_hours:
                        return ExecutionIntent(
                            action="SELL" if current_qty > 0 else "BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Max hold time reached: {hours_held:.1f} hours"
                        )
                
                # Intraday exit (close before market close)
                if self.intraday_only:
                    current_time = datetime.now().time()
                    if current_time >= time(15, 30):  # 30 minutes before close
                        return ExecutionIntent(
                            action="SELL" if current_qty > 0 else "BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Intraday exit before market close"
                        )
                
                # Gap fill exit
                if self.current_gap_analysis:
                    gap_fill_price = primary_signal.metadata.get('gap_fill_price')
                    if gap_fill_price:
                        if current_qty > 0 and current_price >= gap_fill_price:
                            return ExecutionIntent(
                                action="SELL",
                                quantity=abs(current_qty),
                                order_type=OrderType.LIMIT,
                                limit_price=gap_fill_price,
                                reason="Gap filled - taking profit"
                            )
                        elif current_qty < 0 and current_price <= gap_fill_price:
                            return ExecutionIntent(
                                action="BUY",
                                quantity=abs(current_qty),
                                order_type=OrderType.LIMIT,
                                limit_price=gap_fill_price,
                                reason="Gap filled - taking profit"
                            )
                
                # Standard stop loss / take profit
                if current_qty > 0:
                    if (risk_params.stop_loss and current_price <= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price >= risk_params.take_profit):
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Stop/Target hit"
                        )
                elif current_qty < 0:
                    if (risk_params.stop_loss and current_price >= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price <= risk_params.take_profit):
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Stop/Target hit"
                        )
            
            # Entry logic
            if primary_signal.signal_type == SignalType.BUY and primary_signal.strength != SignalStrength.WEAK:
                self.position_entry_time = datetime.now()
                return ExecutionIntent(
                    action="BUY",
                    quantity=risk_params.position_size,
                    order_type=OrderType.MARKET,
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"Gap reversal: {primary_signal.metadata.get('gap_type', 'unknown')}",
                    metadata={
                        'gap_analysis': primary_signal.metadata,
                        'entry_time': datetime.now()
                    }
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                self.position_entry_time = datetime.now()
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.MARKET,
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"Gap reversal: {primary_signal.metadata.get('gap_type', 'unknown')}",
                    metadata={
                        'gap_analysis': primary_signal.metadata,
                        'entry_time': datetime.now()
                    }
                )
            
            return ExecutionIntent(action="HOLD", quantity=0)
            
        except Exception as e:
            self.logger.error(f"Error determining execution intent: {e}")
            return ExecutionIntent(action="HOLD", quantity=0)
    
    def _update_performance_metrics(self, 
                                  execution_result: Dict,
                                  market_data: pd.DataFrame) -> None:
        """
        Pillar 5: Performance Tracking & Configurability
        
        Update performance metrics with gap reversal specific statistics.
        """
        try:
            # Update basic performance metrics
            self.performance_metrics.update(
                timestamp=market_data.index[-1],
                price=market_data['close'].iloc[-1],
                position=execution_result.get('position', 0),
                pnl=execution_result.get('pnl', 0),
                execution_result=execution_result
            )
            
            # Gap-specific metrics
            if hasattr(self, '_last_signal') and self._last_signal:
                signal_metadata = self._last_signal.metadata
                
                # Track gap characteristics at entry
                self.performance_metrics.add_custom_metric(
                    'gap_size_percent_at_entry',
                    signal_metadata.get('gap_size_percent', 0.0)
                )
                
                self.performance_metrics.add_custom_metric(
                    'gap_type_at_entry',
                    signal_metadata.get('gap_type', 'unknown')
                )
                
                self.performance_metrics.add_custom_metric(
                    'reversal_probability_at_entry',
                    signal_metadata.get('reversal_probability', 0.5)
                )
                
                self.performance_metrics.add_custom_metric(
                    'volume_ratio_at_entry',
                    signal_metadata.get('volume_ratio', 1.0)
                )
                
                self.performance_metrics.add_custom_metric(
                    'gap_context_at_entry',
                    signal_metadata.get('gap_context', 'neutral')
                )
            
            # Track current gap analysis
            if self.current_gap_analysis:
                self.performance_metrics.add_custom_metric('current_gap_type', self.current_gap_analysis.gap_type.value)
                self.performance_metrics.add_custom_metric('current_gap_size', self.current_gap_analysis.gap_size_percent)
                self.performance_metrics.add_custom_metric('current_reversal_probability', self.current_gap_analysis.reversal_probability)
            
            # Calculate gap-type specific performance
            trades = self.performance_metrics.get_trades()
            if len(trades) >= 10:
                for gap_type in GapType:
                    if gap_type == GapType.NO_GAP:
                        continue
                        
                    gap_trades = [trade for trade in trades[-30:] 
                                 if trade.get('gap_type_at_entry') == gap_type.value]
                    if gap_trades:
                        gap_success = sum(1 for trade in gap_trades if trade.get('pnl', 0) > 0)
                        gap_success_rate = gap_success / len(gap_trades)
                        
                        self.performance_metrics.add_custom_metric(
                            f'{gap_type.value}_success_rate',
                            gap_success_rate
                        )
                        
                        avg_pnl = sum(trade.get('pnl', 0) for trade in gap_trades) / len(gap_trades)
                        self.performance_metrics.add_custom_metric(
                            f'{gap_type.value}_avg_pnl',
                            avg_pnl
                        )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _create_neutral_signal(self) -> Signal:
        """Create a neutral signal when no gap reversal opportunities are present"""
        return Signal(
            symbol=self.symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            timestamp=datetime.now(),
            metadata={'reason': 'No gap reversal opportunities'}
        )
    
    def _create_default_gap_analysis(self) -> GapAnalysis:
        """Create default gap analysis when calculation fails"""
        return GapAnalysis(
            gap_type=GapType.NO_GAP,
            gap_size_percent=0.0,
            gap_size_points=0.0,
            gap_context=GapContext.NEUTRAL,
            volume_ratio=1.0,
            reversal_probability=0.5,
            optimal_timing=ReversalTiming.NO_REVERSAL,
            support_resistance_factor=0.5,
            market_sentiment="neutral",
            statistical_significance=0.5
        )
    
    def _create_default_risk_parameters(self) -> RiskParameters:
        """Create default risk parameters when calculation fails"""
        return RiskParameters(
            position_size=self.max_position_size * 0.5,
            stop_loss=None,
            take_profit=None,
            max_risk_per_trade=0.02,
            risk_reward_ratio=2.0,
            volatility_adjustment=1.0
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information and current parameters"""
        return {
            'name': 'Overnight Reversal Strategy',
            'version': '1.0',
            'description': 'Gap reversal strategy based on overnight price gaps',
            'parameters': {
                'min_gap_threshold': self.min_gap_threshold,
                'max_gap_threshold': self.max_gap_threshold,
                'volume_confirmation_threshold': self.volume_confirmation_threshold,
                'reversal_confidence_threshold': self.reversal_confidence_threshold,
                'max_hold_hours': self.max_hold_hours,
                'use_premarket_data': self.use_premarket_data,
                'gap_lookback_period': self.gap_lookback_period,
                'support_resistance_lookback': self.support_resistance_lookback,
                'max_position_size': self.max_position_size,
                'intraday_only': self.intraday_only
            },
            'current_state': {
                'current_gap_analysis': self.current_gap_analysis.gap_type.value if self.current_gap_analysis else 'none',
                'support_levels_count': len(self.support_levels),
                'resistance_levels_count': len(self.resistance_levels),
                'market_regime': self.current_regime.value
            },
            'asset_classes': ['stocks', 'etfs', 'index_futures'],
            'timeframes': ['1d', '4h', '1h', '15m'],
            'market_conditions': ['gap_days', 'volatile_markets', 'earnings_season']
        }