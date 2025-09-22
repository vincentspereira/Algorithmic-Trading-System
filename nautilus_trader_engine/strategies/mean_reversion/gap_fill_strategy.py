#!/usr/bin/env python3
"""
Gap Fill Mean Reversion Strategy

Implements a sophisticated gap fill strategy that capitalizes on the statistical tendency
of price gaps to fill over time. This strategy identifies significant gaps and trades
the mean reversion back to fill these gaps.

Key Features:
- Multi-type gap detection (breakaway, runaway, exhaustion, common)
- Volume-weighted gap significance analysis
- Time-based gap fill probability modeling
- Support/resistance level integration
- Market regime adaptation for gap trading
- Dynamic position sizing based on gap size and probability
- False gap filtering using technical confirmation
- Risk management with gap-specific stops

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
from datetime import datetime, timedelta

# Import base strategy class and required modules
from ...core.base_strategy import BaseRetailStrategy
from ...architecture.pillars.risk_management import RiskParameters
from ...utils.risk_management_utils import PositionSizer
from ...architecture.pillars.market_regime_detection import MarketRegimeDetector, MarketRegime
from ...indicators.technical_indicators import TechnicalIndicators
from ...indicators.candlestick_patterns import CandlestickPatterns
from ...architecture.pillars.signal_generation import Signal, SignalType, SignalStrength
from ...architecture.pillars.execution_intent import ExecutionIntent, OrderType
from ...utils.performance_tracker import PerformanceMetrics


class GapType(Enum):
    """Types of price gaps"""
    BREAKAWAY = "breakaway"  # Gap at start of new trend
    RUNAWAY = "runaway"      # Gap in middle of trend (continuation)
    EXHAUSTION = "exhaustion" # Gap at end of trend
    COMMON = "common"        # Gap in sideways market
    OVERNIGHT = "overnight"   # Regular overnight gap


@dataclass
class Gap:
    """Gap information structure"""
    gap_type: GapType
    gap_size: float
    gap_percentage: float
    gap_start: float
    gap_end: float
    gap_date: datetime
    volume_ratio: float
    fill_probability: float
    days_since_gap: int
    is_filled: bool = False
    fill_date: Optional[datetime] = None


class GapFillStrategy(BaseRetailStrategy):
    """
    Gap Fill Mean Reversion Strategy Implementation
    
    This strategy implements sophisticated gap fill trading with:
    - Multi-type gap detection and classification
    - Volume-weighted gap significance analysis
    - Time-based fill probability modeling
    - Support/resistance integration for enhanced signals
    - Market regime adaptation for optimal gap trading
    """
    
    def __init__(self, 
                 symbol: str,
                 min_gap_percentage: float = 1.0,
                 max_gap_percentage: float = 10.0,
                 min_volume_ratio: float = 1.5,
                 max_days_to_fill: int = 20,
                 gap_fill_threshold: float = 0.8,
                 use_support_resistance: bool = True,
                 trend_filter: bool = True,
                 max_position_size: float = 0.15,
                 stop_loss_gap_ratio: float = 0.3,
                 profit_target_ratio: float = 2.0,
                 **kwargs):
        """
        Initialize Gap Fill Strategy
        
        Args:
            symbol: Trading symbol
            min_gap_percentage: Minimum gap size to consider (default: 1.0%)
            max_gap_percentage: Maximum gap size to trade (default: 10.0%)
            min_volume_ratio: Minimum volume ratio for gap significance
            max_days_to_fill: Maximum days to wait for gap fill
            gap_fill_threshold: Percentage of gap that needs to be filled (0.8 = 80%)
            use_support_resistance: Use S/R levels for enhanced signals
            trend_filter: Filter gaps against longer-term trend
            max_position_size: Maximum position size as fraction of portfolio
            stop_loss_gap_ratio: Stop loss as ratio of gap size
            profit_target_ratio: Risk/reward ratio for profit targets
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.min_gap_percentage = min_gap_percentage
        self.max_gap_percentage = max_gap_percentage
        self.min_volume_ratio = min_volume_ratio
        self.max_days_to_fill = max_days_to_fill
        self.gap_fill_threshold = gap_fill_threshold
        self.use_support_resistance = use_support_resistance
        self.trend_filter = trend_filter
        self.max_position_size = max_position_size
        self.stop_loss_gap_ratio = stop_loss_gap_ratio
        self.profit_target_ratio = profit_target_ratio
        
        # Initialize components
        self.technical_indicators = TechnicalIndicators()
        self.candlestick_patterns = CandlestickPatterns()
        self.market_regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.active_gaps: List[Gap] = []
        self.support_levels: List[float] = []
        self.resistance_levels: List[float] = []
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate gap fill signals by detecting significant gaps and analyzing
        their fill probability based on historical patterns and market context.
        """
        if len(data) < 50:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Update support/resistance levels
            if self.use_support_resistance:
                self._update_support_resistance_levels(data)
            
            # Detect new gaps
            new_gaps = self._detect_gaps(data)
            
            # Update active gaps list
            self._update_active_gaps(data, new_gaps)
            
            # Calculate additional indicators
            sma_20 = self.technical_indicators.sma(data['close'], period=20)
            ema_50 = self.technical_indicators.ema(data['close'], period=50)
            rsi = self.technical_indicators.rsi(data['close'], period=14)
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            atr = self.technical_indicators.atr(data, period=14)
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_atr = atr.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            
            # Trend context
            trend_bullish = current_price > current_ema_50
            trend_bearish = current_price < current_ema_50
            
            # Analyze active gaps for trading opportunities
            best_signal = None
            best_confidence = 0
            
            for gap in self.active_gaps:
                if gap.is_filled or gap.days_since_gap > self.max_days_to_fill:
                    continue
                
                # Calculate gap fill signal
                signal = self._analyze_gap_fill_opportunity(gap, data, current_price)
                
                if signal and signal.confidence > best_confidence:
                    best_signal = signal
                    best_confidence = signal.confidence
            
            # If no gap signal, check for new gap opportunities
            if not best_signal and new_gaps:
                for gap in new_gaps:
                    signal = self._analyze_new_gap_opportunity(gap, data, current_price)
                    if signal and signal.confidence > best_confidence:
                        best_signal = signal
                        best_confidence = signal.confidence
            
            # Add market context to signal
            if best_signal:
                best_signal.metadata.update({
                    'current_price': current_price,
                    'rsi': current_rsi,
                    'sma_20': current_sma_20,
                    'ema_50': current_ema_50,
                    'volume_ratio': current_volume / avg_volume,
                    'atr': current_atr,
                    'trend_bullish': trend_bullish,
                    'trend_bearish': trend_bearish,
                    'market_regime': self.current_regime.value,
                    'active_gaps_count': len([g for g in self.active_gaps if not g.is_filled]),
                    'support_levels': self.support_levels[-3:] if self.support_levels else [],
                    'resistance_levels': self.resistance_levels[-3:] if self.resistance_levels else []
                })
                
                signals.append(best_signal)
            else:
                signals.append(self._create_neutral_signal())
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            signals.append(self._create_neutral_signal())
            
        return signals
    
    def _detect_gaps(self, data: pd.DataFrame) -> List[Gap]:
        """
        Detect price gaps in the data
        """
        gaps = []
        
        try:
            if len(data) < 2:
                return gaps
            
            # Calculate volume moving average for significance
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            
            for i in range(1, len(data)):
                prev_close = data['close'].iloc[i-1]
                current_open = data['open'].iloc[i]
                current_high = data['high'].iloc[i]
                current_low = data['low'].iloc[i]
                current_close = data['close'].iloc[i]
                current_volume = data['volume'].iloc[i]
                avg_volume = volume_sma.iloc[i] if not pd.isna(volume_sma.iloc[i]) else current_volume
                
                # Check for gap up
                if current_low > prev_close:
                    gap_size = current_low - prev_close
                    gap_percentage = (gap_size / prev_close) * 100
                    
                    if (self.min_gap_percentage <= gap_percentage <= self.max_gap_percentage and
                        current_volume / avg_volume >= self.min_volume_ratio):
                        
                        gap_type = self._classify_gap_type(data, i, gap_percentage, True)
                        fill_probability = self._calculate_fill_probability(gap_type, gap_percentage, current_volume / avg_volume)
                        
                        gap = Gap(
                            gap_type=gap_type,
                            gap_size=gap_size,
                            gap_percentage=gap_percentage,
                            gap_start=prev_close,
                            gap_end=current_low,
                            gap_date=data.index[i],
                            volume_ratio=current_volume / avg_volume,
                            fill_probability=fill_probability,
                            days_since_gap=0
                        )
                        gaps.append(gap)
                
                # Check for gap down
                elif current_high < prev_close:
                    gap_size = prev_close - current_high
                    gap_percentage = (gap_size / prev_close) * 100
                    
                    if (self.min_gap_percentage <= gap_percentage <= self.max_gap_percentage and
                        current_volume / avg_volume >= self.min_volume_ratio):
                        
                        gap_type = self._classify_gap_type(data, i, gap_percentage, False)
                        fill_probability = self._calculate_fill_probability(gap_type, gap_percentage, current_volume / avg_volume)
                        
                        gap = Gap(
                            gap_type=gap_type,
                            gap_size=gap_size,
                            gap_percentage=gap_percentage,
                            gap_start=prev_close,
                            gap_end=current_high,
                            gap_date=data.index[i],
                            volume_ratio=current_volume / avg_volume,
                            fill_probability=fill_probability,
                            days_since_gap=0
                        )
                        gaps.append(gap)
            
            return gaps
            
        except Exception as e:
            self.logger.error(f"Error detecting gaps: {e}")
            return []
    
    def _classify_gap_type(self, data: pd.DataFrame, gap_index: int, gap_percentage: float, is_gap_up: bool) -> GapType:
        """
        Classify the type of gap based on market context
        """
        try:
            # Look at trend context before gap
            if gap_index >= 10:
                pre_gap_data = data.iloc[gap_index-10:gap_index]
                trend_slope = (pre_gap_data['close'].iloc[-1] - pre_gap_data['close'].iloc[0]) / len(pre_gap_data)
                
                # Calculate recent volatility
                recent_returns = pre_gap_data['close'].pct_change().std()
                
                # Classify based on trend and gap characteristics
                if gap_percentage > 5.0:  # Large gaps
                    if abs(trend_slope) > pre_gap_data['close'].iloc[0] * 0.001:  # Strong trend
                        if (is_gap_up and trend_slope > 0) or (not is_gap_up and trend_slope < 0):
                            return GapType.RUNAWAY  # Gap in direction of trend
                        else:
                            return GapType.EXHAUSTION  # Gap against trend (potential reversal)
                    else:
                        return GapType.BREAKAWAY  # Gap from consolidation
                else:
                    if recent_returns < 0.02:  # Low volatility
                        return GapType.COMMON  # Regular gap in calm market
                    else:
                        return GapType.OVERNIGHT  # Regular overnight gap
            
            return GapType.OVERNIGHT  # Default for insufficient data
            
        except Exception as e:
            self.logger.error(f"Error classifying gap type: {e}")
            return GapType.COMMON
    
    def _calculate_fill_probability(self, gap_type: GapType, gap_percentage: float, volume_ratio: float) -> float:
        """
        Calculate probability of gap fill based on historical patterns
        """
        try:
            # Base probabilities by gap type (from historical analysis)
            base_probabilities = {
                GapType.COMMON: 0.85,      # High fill probability
                GapType.OVERNIGHT: 0.75,   # Good fill probability
                GapType.BREAKAWAY: 0.45,   # Lower fill probability (trend start)
                GapType.RUNAWAY: 0.30,     # Low fill probability (trend continuation)
                GapType.EXHAUSTION: 0.70   # Good fill probability (trend end)
            }
            
            base_prob = base_probabilities.get(gap_type, 0.6)
            
            # Adjust for gap size (smaller gaps more likely to fill)
            size_adjustment = max(0.1, 1.0 - (gap_percentage - 1.0) / 10.0)
            
            # Adjust for volume (higher volume gaps less likely to fill immediately)
            volume_adjustment = max(0.5, 1.0 - (volume_ratio - 1.0) / 5.0)
            
            # Market regime adjustment
            regime_adjustment = {
                MarketRegime.BULL: 1.0,
                MarketRegime.BEAR: 1.0,
                MarketRegime.SIDEWAYS: 1.2,  # Gaps fill more in sideways markets
                MarketRegime.HIGH_VOLATILITY: 0.8,
                MarketRegime.LOW_VOLATILITY: 1.1
            }.get(self.current_regime, 1.0)
            
            final_probability = base_prob * size_adjustment * volume_adjustment * regime_adjustment
            return min(0.95, max(0.05, final_probability))
            
        except Exception as e:
            self.logger.error(f"Error calculating fill probability: {e}")
            return 0.5
    
    def _update_active_gaps(self, data: pd.DataFrame, new_gaps: List[Gap]) -> None:
        """
        Update the list of active gaps and check for fills
        """
        try:
            current_date = data.index[-1]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            
            # Add new gaps
            for gap in new_gaps:
                self.active_gaps.append(gap)
            
            # Update existing gaps
            for gap in self.active_gaps:
                if not gap.is_filled:
                    # Update days since gap
                    gap.days_since_gap = (current_date - gap.gap_date).days
                    
                    # Check if gap is filled
                    if gap.gap_start > gap.gap_end:  # Gap down
                        fill_level = gap.gap_start - (gap.gap_size * (1 - self.gap_fill_threshold))
                        if current_high >= fill_level:
                            gap.is_filled = True
                            gap.fill_date = current_date
                    else:  # Gap up
                        fill_level = gap.gap_start + (gap.gap_size * (1 - self.gap_fill_threshold))
                        if current_low <= fill_level:
                            gap.is_filled = True
                            gap.fill_date = current_date
            
            # Remove old gaps
            self.active_gaps = [gap for gap in self.active_gaps 
                              if gap.days_since_gap <= self.max_days_to_fill * 2]  # Keep for analysis
            
        except Exception as e:
            self.logger.error(f"Error updating active gaps: {e}")
    
    def _analyze_gap_fill_opportunity(self, gap: Gap, data: pd.DataFrame, current_price: float) -> Optional[Signal]:
        """
        Analyze a gap for fill trading opportunity
        """
        try:
            # Calculate distance to gap
            if gap.gap_start > gap.gap_end:  # Gap down - trade long to fill
                distance_to_gap = abs(current_price - gap.gap_start) / gap.gap_size
                signal_type = SignalType.BUY
                target_price = gap.gap_start
            else:  # Gap up - trade short to fill
                distance_to_gap = abs(current_price - gap.gap_start) / gap.gap_size
                signal_type = SignalType.SELL
                target_price = gap.gap_start
            
            # Only trade if we're reasonably close to the gap
            if distance_to_gap > 3.0:  # Too far from gap
                return None
            
            # Calculate signal strength based on multiple factors
            strength_score = 0
            
            # Gap fill probability
            strength_score += gap.fill_probability * 40
            
            # Time decay (fresher gaps are better)
            time_factor = max(0.1, 1.0 - gap.days_since_gap / self.max_days_to_fill)
            strength_score += time_factor * 20
            
            # Distance factor (closer to gap is better)
            distance_factor = max(0.1, 1.0 - distance_to_gap / 3.0)
            strength_score += distance_factor * 20
            
            # Gap type factor
            type_scores = {
                GapType.COMMON: 15,
                GapType.OVERNIGHT: 12,
                GapType.EXHAUSTION: 10,
                GapType.BREAKAWAY: 5,
                GapType.RUNAWAY: 3
            }
            strength_score += type_scores.get(gap.gap_type, 5)
            
            # Support/resistance confirmation
            if self.use_support_resistance:
                if signal_type == SignalType.BUY:
                    # Check if current price is near support
                    near_support = any(abs(current_price - level) / current_price < 0.02 
                                     for level in self.support_levels)
                    if near_support:
                        strength_score += 10
                else:
                    # Check if current price is near resistance
                    near_resistance = any(abs(current_price - level) / current_price < 0.02 
                                        for level in self.resistance_levels)
                    if near_resistance:
                        strength_score += 10
            
            # Trend filter
            if self.trend_filter:
                ema_50 = self.technical_indicators.ema(data['close'], period=50).iloc[-1]
                if signal_type == SignalType.BUY and current_price < ema_50:
                    strength_score -= 10  # Against trend
                elif signal_type == SignalType.SELL and current_price > ema_50:
                    strength_score -= 10  # Against trend
            
            # Convert to signal strength
            if strength_score >= 70:
                signal_strength = SignalStrength.STRONG
                confidence = min(0.9, strength_score / 100)
            elif strength_score >= 50:
                signal_strength = SignalStrength.MEDIUM
                confidence = min(0.75, strength_score / 100)
            else:
                signal_strength = SignalStrength.WEAK
                confidence = min(0.6, strength_score / 100)
            
            # Don't trade weak signals
            if signal_strength == SignalStrength.WEAK:
                return None
            
            return Signal(
                symbol=self.symbol,
                signal_type=signal_type,
                strength=signal_strength,
                confidence=confidence,
                timestamp=data.index[-1],
                metadata={
                    'gap_type': gap.gap_type.value,
                    'gap_size': gap.gap_size,
                    'gap_percentage': gap.gap_percentage,
                    'gap_start': gap.gap_start,
                    'gap_end': gap.gap_end,
                    'gap_date': gap.gap_date,
                    'days_since_gap': gap.days_since_gap,
                    'fill_probability': gap.fill_probability,
                    'target_price': target_price,
                    'distance_to_gap': distance_to_gap,
                    'strength_score': strength_score,
                    'time_factor': time_factor,
                    'distance_factor': distance_factor
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing gap fill opportunity: {e}")
            return None
    
    def _analyze_new_gap_opportunity(self, gap: Gap, data: pd.DataFrame, current_price: float) -> Optional[Signal]:
        """
        Analyze a newly formed gap for immediate trading opportunity
        """
        try:
            # For new gaps, we typically want to fade them (trade against the gap)
            # This is different from gap fill trading
            
            # Only trade high-probability gap types
            if gap.gap_type in [GapType.RUNAWAY, GapType.BREAKAWAY]:
                return None  # Don't fade strong trend gaps
            
            # Calculate signal based on gap characteristics
            if gap.gap_start > gap.gap_end:  # Gap down - potential bounce
                signal_type = SignalType.BUY
            else:  # Gap up - potential fade
                signal_type = SignalType.SELL
            
            # Calculate signal strength
            strength_score = 0
            
            # Gap size factor (moderate gaps are best for fading)
            if 1.5 <= gap.gap_percentage <= 4.0:
                strength_score += 30
            elif gap.gap_percentage > 6.0:
                strength_score -= 20  # Too large to fade safely
            
            # Volume factor (excessive volume suggests continuation)
            if gap.volume_ratio > 3.0:
                strength_score -= 15  # Too much volume
            elif 1.5 <= gap.volume_ratio <= 2.5:
                strength_score += 15  # Good volume confirmation
            
            # Market regime factor
            if self.current_regime == MarketRegime.SIDEWAYS:
                strength_score += 20  # Gaps fade better in sideways markets
            elif self.current_regime == MarketRegime.HIGH_VOLATILITY:
                strength_score -= 10  # Risky in volatile markets
            
            # RSI confirmation
            rsi = self.technical_indicators.rsi(data['close'], period=14).iloc[-1]
            if signal_type == SignalType.BUY and rsi < 30:
                strength_score += 15  # Oversold bounce
            elif signal_type == SignalType.SELL and rsi > 70:
                strength_score += 15  # Overbought fade
            
            # Convert to signal strength
            if strength_score >= 60:
                signal_strength = SignalStrength.STRONG
                confidence = min(0.85, strength_score / 100)
            elif strength_score >= 40:
                signal_strength = SignalStrength.MEDIUM
                confidence = min(0.7, strength_score / 100)
            else:
                return None  # Don't trade weak new gap signals
            
            return Signal(
                symbol=self.symbol,
                signal_type=signal_type,
                strength=signal_strength,
                confidence=confidence,
                timestamp=data.index[-1],
                metadata={
                    'gap_type': gap.gap_type.value,
                    'gap_size': gap.gap_size,
                    'gap_percentage': gap.gap_percentage,
                    'gap_start': gap.gap_start,
                    'gap_end': gap.gap_end,
                    'gap_date': gap.gap_date,
                    'fill_probability': gap.fill_probability,
                    'strength_score': strength_score,
                    'trade_type': 'gap_fade',
                    'rsi': rsi
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing new gap opportunity: {e}")
            return None
    
    def _update_support_resistance_levels(self, data: pd.DataFrame) -> None:
        """
        Update support and resistance levels using pivot points and volume
        """
        try:
            if len(data) < 20:
                return
            
            # Calculate pivot points from recent data
            recent_data = data.iloc[-50:] if len(data) >= 50 else data
            
            # Find swing highs and lows
            highs = []
            lows = []
            
            for i in range(2, len(recent_data) - 2):
                # Swing high
                if (recent_data['high'].iloc[i] > recent_data['high'].iloc[i-1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i-2] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+1] and
                    recent_data['high'].iloc[i] > recent_data['high'].iloc[i+2]):
                    highs.append(recent_data['high'].iloc[i])
                
                # Swing low
                if (recent_data['low'].iloc[i] < recent_data['low'].iloc[i-1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i-2] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+1] and
                    recent_data['low'].iloc[i] < recent_data['low'].iloc[i+2]):
                    lows.append(recent_data['low'].iloc[i])
            
            # Update resistance levels (from swing highs)
            if highs:
                # Cluster similar levels
                clustered_highs = self._cluster_levels(highs)
                self.resistance_levels = sorted(clustered_highs, reverse=True)[:5]
            
            # Update support levels (from swing lows)
            if lows:
                # Cluster similar levels
                clustered_lows = self._cluster_levels(lows)
                self.support_levels = sorted(clustered_lows)[-5:]
            
        except Exception as e:
            self.logger.error(f"Error updating support/resistance levels: {e}")
    
    def _cluster_levels(self, levels: List[float], threshold: float = 0.02) -> List[float]:
        """
        Cluster similar price levels together
        """
        if not levels:
            return []
        
        clustered = []
        sorted_levels = sorted(levels)
        
        current_cluster = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] <= threshold:
                current_cluster.append(level)
            else:
                # Finish current cluster
                clustered.append(np.mean(current_cluster))
                current_cluster = [level]
        
        # Add final cluster
        if current_cluster:
            clustered.append(np.mean(current_cluster))
        
        return clustered
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters based on gap characteristics,
        fill probability, and market conditions.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('current_price', data['close'].iloc[-1])
            gap_size = metadata.get('gap_size', 0)
            gap_percentage = metadata.get('gap_percentage', 0)
            fill_probability = metadata.get('fill_probability', 0.5)
            target_price = metadata.get('target_price', current_price)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.4,
                SignalStrength.MEDIUM: 0.7,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Adjust size based on fill probability
            probability_multiplier = min(1.5, fill_probability * 1.5)
            
            # Adjust size based on gap size (smaller gaps = larger positions)
            gap_size_multiplier = max(0.5, 1.0 - (gap_percentage - 1.0) / 10.0)
            
            # Market regime adjustment
            regime_multiplier = {
                MarketRegime.BULL: 1.0,
                MarketRegime.BEAR: 1.0,
                MarketRegime.SIDEWAYS: 1.2,  # Gap fill works best in sideways markets
                MarketRegime.HIGH_VOLATILITY: 0.7,
                MarketRegime.LOW_VOLATILITY: 1.1
            }.get(self.current_regime, 1.0)
            
            # Calculate final position size
            position_size = (base_size * strength_multiplier * probability_multiplier * 
                           gap_size_multiplier * regime_multiplier)
            position_size = min(position_size, self.max_position_size * 1.3)
            
            # Calculate stop loss and take profit levels
            if signal.signal_type == SignalType.BUY:
                # Stop loss below gap or based on gap size
                gap_based_stop = current_price - (gap_size * self.stop_loss_gap_ratio)
                
                # ATR-based stop as backup
                atr = self.technical_indicators.atr(data, period=14).iloc[-1]
                atr_stop = current_price - (atr * 2.0)
                
                stop_loss = max(gap_based_stop, atr_stop)  # Use closer stop
                
                # Take profit at gap fill level or based on risk/reward
                if target_price and target_price > current_price:
                    take_profit = target_price
                else:
                    risk_amount = current_price - stop_loss
                    take_profit = current_price + (risk_amount * self.profit_target_ratio)
                
            elif signal.signal_type == SignalType.SELL:
                # Stop loss above gap or based on gap size
                gap_based_stop = current_price + (gap_size * self.stop_loss_gap_ratio)
                
                # ATR-based stop as backup
                atr = self.technical_indicators.atr(data, period=14).iloc[-1]
                atr_stop = current_price + (atr * 2.0)
                
                stop_loss = min(gap_based_stop, atr_stop)  # Use closer stop
                
                # Take profit at gap fill level or based on risk/reward
                if target_price and target_price < current_price:
                    take_profit = target_price
                else:
                    risk_amount = stop_loss - current_price
                    take_profit = current_price - (risk_amount * self.profit_target_ratio)
                    
            else:
                stop_loss = None
                take_profit = None
            
            return RiskParameters(
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_risk_per_trade=0.025,  # Slightly higher for gap trading
                risk_reward_ratio=self.profit_target_ratio,
                volatility_adjustment=gap_percentage / 10.0  # Gap size as volatility proxy
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect current market regime and adapt gap trading parameters accordingly.
        """
        try:
            # Use market regime detector
            regime = self.market_regime_detector.detect_regime(data)
            self.current_regime = regime
            
            # Adapt strategy parameters based on regime
            if regime == MarketRegime.HIGH_VOLATILITY:
                # In high volatility, be more selective with gaps
                self.min_gap_percentage = max(1.5, self.min_gap_percentage)
                self.min_volume_ratio = max(2.0, self.min_volume_ratio)
            elif regime == MarketRegime.LOW_VOLATILITY:
                # In low volatility, can trade smaller gaps
                self.min_gap_percentage = min(0.8, self.min_gap_percentage)
                self.min_volume_ratio = max(1.2, self.min_volume_ratio)
            elif regime == MarketRegime.SIDEWAYS:
                # Sideways markets are ideal for gap fill trading
                self.max_days_to_fill = min(30, self.max_days_to_fill + 5)
            
            # Log regime changes
            if hasattr(self, '_previous_regime') and self._previous_regime != regime:
                self.logger.info(f"Market regime changed from {self._previous_regime.value} to {regime.value}")
            
            self._previous_regime = regime
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
        
        Determine execution intent based on gap fill signals and current position.
        """
        if not signals:
            return ExecutionIntent(action="HOLD", quantity=0)
            
        primary_signal = signals[0]
        
        try:
            # Check if we should exit current position
            if current_position and current_position.get('quantity', 0) != 0:
                current_qty = current_position['quantity']
                entry_price = current_position.get('entry_price', 0)
                current_price = primary_signal.metadata.get('current_price', 0)
                
                # Check for gap fill completion
                target_price = current_position.get('target_price')
                if target_price:
                    if current_qty > 0 and current_price >= target_price * 0.95:  # 95% of gap filled
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Gap fill target reached"
                        )
                    elif current_qty < 0 and current_price <= target_price * 1.05:  # 95% of gap filled
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Gap fill target reached"
                        )
                
                # Standard stop loss / take profit
                if current_qty > 0:
                    if (risk_params.stop_loss and current_price <= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price >= risk_params.take_profit):
                        pnl_pct = (current_price - entry_price) / entry_price
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
                elif current_qty < 0:
                    if (risk_params.stop_loss and current_price >= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price <= risk_params.take_profit):
                        pnl_pct = (entry_price - current_price) / entry_price
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
            
            # Entry logic
            if primary_signal.signal_type == SignalType.BUY and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="BUY",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('current_price') * 0.999,
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"Gap fill opportunity: {primary_signal.metadata.get('gap_type', 'unknown')}",
                    metadata={'target_price': primary_signal.metadata.get('target_price')}
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('current_price') * 1.001,
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"Gap fill opportunity: {primary_signal.metadata.get('gap_type', 'unknown')}",
                    metadata={'target_price': primary_signal.metadata.get('target_price')}
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
        
        Update strategy performance metrics with gap-specific statistics.
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
                    'gap_type_at_entry',
                    signal_metadata.get('gap_type', 'unknown')
                )
                
                self.performance_metrics.add_custom_metric(
                    'gap_size_at_entry',
                    signal_metadata.get('gap_percentage', 0)
                )
                
                self.performance_metrics.add_custom_metric(
                    'fill_probability_at_entry',
                    signal_metadata.get('fill_probability', 0.5)
                )
                
                self.performance_metrics.add_custom_metric(
                    'days_since_gap_at_entry',
                    signal_metadata.get('days_since_gap', 0)
                )
            
            # Track active gaps statistics
            active_gaps_count = len([g for g in self.active_gaps if not g.is_filled])
            self.performance_metrics.add_custom_metric('active_gaps_count', active_gaps_count)
            
            # Calculate gap fill success rate
            filled_gaps = [g for g in self.active_gaps if g.is_filled]
            if len(self.active_gaps) > 0:
                fill_rate = len(filled_gaps) / len(self.active_gaps)
                self.performance_metrics.add_custom_metric('gap_fill_rate', fill_rate)
            
            # Track gap type performance
            trades = self.performance_metrics.get_trades()
            if len(trades) >= 10:
                for gap_type in GapType:
                    type_trades = [trade for trade in trades[-20:] 
                                 if trade.get('gap_type_at_entry') == gap_type.value]
                    if type_trades:
                        type_success = sum(1 for trade in type_trades if trade.get('pnl', 0) > 0)
                        type_success_rate = type_success / len(type_trades)
                        
                        self.performance_metrics.add_custom_metric(
                            f'{gap_type.value}_success_rate',
                            type_success_rate
                        )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _create_neutral_signal(self) -> Signal:
        """Create a neutral signal when no gap opportunities are present"""
        return Signal(
            symbol=self.symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            timestamp=datetime.now(),
            metadata={'reason': 'No gap fill opportunities'}
        )
    
    def _create_default_risk_parameters(self) -> RiskParameters:
        """Create default risk parameters when calculation fails"""
        return RiskParameters(
            position_size=self.max_position_size * 0.5,
            stop_loss=None,
            take_profit=None,
            max_risk_per_trade=0.025,
            risk_reward_ratio=self.profit_target_ratio,
            volatility_adjustment=0.5
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information and current parameters"""
        return {
            'name': 'Gap Fill Mean Reversion Strategy',
            'version': '1.0',
            'description': 'Mean reversion strategy based on price gap fill probability',
            'parameters': {
                'min_gap_percentage': self.min_gap_percentage,
                'max_gap_percentage': self.max_gap_percentage,
                'min_volume_ratio': self.min_volume_ratio,
                'max_days_to_fill': self.max_days_to_fill,
                'gap_fill_threshold': self.gap_fill_threshold,
                'use_support_resistance': self.use_support_resistance,
                'trend_filter': self.trend_filter,
                'max_position_size': self.max_position_size,
                'stop_loss_gap_ratio': self.stop_loss_gap_ratio,
                'profit_target_ratio': self.profit_target_ratio
            },
            'current_state': {
                'market_regime': self.current_regime.value,
                'active_gaps_count': len([g for g in self.active_gaps if not g.is_filled]),
                'support_levels_count': len(self.support_levels),
                'resistance_levels_count': len(self.resistance_levels)
            },
            'asset_classes': ['stocks', 'etfs', 'futures'],
            'timeframes': ['1d', '4h', '1h'],  # Works best on daily and intraday
            'market_conditions': ['sideways', 'post_earnings', 'post_news']
        }