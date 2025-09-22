#!/usr/bin/env python3
"""
Turnaround Tuesday Strategy - Seasonality-Based with Candlestick Pattern Confirmation

This strategy implements the "Turnaround Tuesday" phenomenon - the statistical tendency
for markets to reverse on Tuesdays after Monday declines. The strategy is enhanced with:
- Volume-weighted candlestick pattern confirmation
- Market regime adaptation
- Dynamic position sizing based on volatility
- Comprehensive risk management

Follows the 5-Pillar Institutional Architecture:
1. Signal Generation & Augmentation
2. Dynamic Risk & Money Management
3. Market Regime Adaptation
4. Decoupled Execution Logic & Order Management
5. Performance Tracking & Configurability

Author: Algorithmic Trading System
Date: 2024
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from abc import ABC, abstractmethod

# Import base strategy and utilities
from ..core.base_institutional_strategy import (
    BaseInstitutionalStrategy, SignalType, MarketRegime, 
    PositionSide, ExecutionUrgency, TimeInForce, OrderType,
    StrategySignal, RiskMetrics, PerformanceMetrics, StrategyState
)
from ..utils.risk_management_utils import (
    calculate_position_size, calculate_stop_loss, calculate_take_profit,
    calculate_var, calculate_sharpe_ratio, calculate_max_drawdown
)
from ..utils.execution_intent_utils import (
    create_execution_intent, ExecutionIntent, MarketCondition
)
from ..core.strategy_config_schema import StrategyConfig, load_strategy_config


class WeekdayType(Enum):
    """Weekday enumeration for seasonality analysis"""
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4


class CandlestickPattern(Enum):
    """Enhanced candlestick patterns for reversal confirmation"""
    HAMMER = "hammer"
    INVERTED_HAMMER = "inverted_hammer"
    BULLISH_ENGULFING = "bullish_engulfing"
    PIERCING_PATTERN = "piercing_pattern"
    MORNING_STAR = "morning_star"
    DOJI = "doji"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    SPINNING_TOP = "spinning_top"
    NONE = "none"


@dataclass
class SeasonalityMetrics:
    """Seasonality analysis metrics"""
    monday_decline: bool = False
    monday_decline_magnitude: float = 0.0
    tuesday_probability: float = 0.0
    historical_tuesday_performance: float = 0.0
    consecutive_declines: int = 0
    volume_confirmation: float = 0.0
    market_stress_level: float = 0.0


@dataclass
class CandlestickAnalysis:
    """Candlestick pattern analysis results"""
    pattern: CandlestickPattern = CandlestickPattern.NONE
    strength: float = 0.0
    volume_confirmation: float = 0.0
    trend_context: str = "neutral"
    reliability_score: float = 0.0


class TurnaroundTuesdayStrategy(BaseInstitutionalStrategy):
    """
    Turnaround Tuesday Strategy Implementation
    
    This strategy capitalizes on the statistical tendency for markets to reverse
    on Tuesdays after Monday declines, enhanced with candlestick pattern confirmation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.min_monday_decline = config.get('min_monday_decline', -0.005)  # -0.5%
        self.max_monday_decline = config.get('max_monday_decline', -0.03)   # -3.0%
        self.volume_threshold = config.get('volume_threshold', 1.2)         # 20% above average
        self.pattern_confirmation_weight = config.get('pattern_confirmation_weight', 0.3)
        self.seasonality_lookback = config.get('seasonality_lookback', 252)  # 1 year
        self.min_probability_threshold = config.get('min_probability_threshold', 0.55)
        
        # Risk management parameters
        self.max_position_size = config.get('max_position_size', 0.02)      # 2% of portfolio
        self.stop_loss_pct = config.get('stop_loss_pct', 0.015)             # 1.5%
        self.take_profit_pct = config.get('take_profit_pct', 0.025)         # 2.5%
        self.max_holding_days = config.get('max_holding_days', 3)           # Exit by Friday
        
        # Market regime parameters
        self.volatility_lookback = config.get('volatility_lookback', 20)
        self.trend_lookback = config.get('trend_lookback', 50)
        
        # Internal state
        self.seasonality_metrics = SeasonalityMetrics()
        self.candlestick_analysis = CandlestickAnalysis()
        self.historical_tuesday_data = []
        
        self.logger.info(f"Initialized Turnaround Tuesday Strategy with config: {config}")
    
    def generate_signals(self, data: pd.DataFrame) -> List[StrategySignal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate trading signals based on:
        1. Monday decline detection
        2. Seasonality analysis
        3. Candlestick pattern confirmation
        4. Volume analysis
        """
        if len(data) < max(self.seasonality_lookback, self.trend_lookback):
            return []
        
        signals = []
        current_time = data.index[-1]
        
        # Check if today is Tuesday
        if current_time.weekday() != WeekdayType.TUESDAY.value:
            return signals
        
        try:
            # Analyze Monday's performance
            monday_analysis = self._analyze_monday_performance(data)
            
            # Perform seasonality analysis
            seasonality_score = self._calculate_seasonality_score(data)
            
            # Analyze candlestick patterns
            pattern_analysis = self._analyze_candlestick_patterns(data)
            
            # Calculate volume confirmation
            volume_score = self._calculate_volume_confirmation(data)
            
            # Generate signal if conditions are met
            if (monday_analysis['decline_detected'] and 
                seasonality_score > self.min_probability_threshold):
                
                # Calculate signal strength
                signal_strength = self._calculate_signal_strength(
                    monday_analysis, seasonality_score, pattern_analysis, volume_score
                )
                
                if signal_strength > 0.5:  # Minimum threshold for signal generation
                    signal = StrategySignal(
                        timestamp=current_time,
                        signal_type=SignalType.ENTRY_LONG,
                        strength=signal_strength,
                        confidence=min(seasonality_score, 0.95),
                        metadata={
                            'monday_decline': monday_analysis['decline_magnitude'],
                            'seasonality_score': seasonality_score,
                            'pattern': pattern_analysis.pattern.value,
                            'pattern_strength': pattern_analysis.strength,
                            'volume_confirmation': volume_score,
                            'strategy_type': 'turnaround_tuesday'
                        }
                    )
                    signals.append(signal)
                    
                    self.logger.info(
                        f"Turnaround Tuesday signal generated: strength={signal_strength:.3f}, "
                        f"confidence={signal.confidence:.3f}"
                    )
            
            # Check for exit conditions
            exit_signals = self._check_exit_conditions(data)
            signals.extend(exit_signals)
            
        except Exception as e:
            self.logger.error(f"Error in signal generation: {e}")
        
        return signals
    
    def _analyze_monday_performance(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze Monday's market performance"""
        try:
            # Get last Monday's data
            current_date = data.index[-1]
            
            # Find Monday (assuming we're on Tuesday)
            monday_idx = None
            for i in range(1, min(5, len(data))):
                check_date = data.index[-i]
                if check_date.weekday() == WeekdayType.MONDAY.value:
                    monday_idx = -i
                    break
            
            if monday_idx is None:
                return {'decline_detected': False, 'decline_magnitude': 0.0}
            
            monday_data = data.iloc[monday_idx]
            prev_friday_close = data.iloc[monday_idx - 1]['close']
            
            # Calculate Monday's performance
            monday_return = (monday_data['close'] - prev_friday_close) / prev_friday_close
            
            # Check if decline meets criteria
            decline_detected = (
                monday_return <= self.min_monday_decline and 
                monday_return >= self.max_monday_decline
            )
            
            # Calculate additional metrics
            intraday_volatility = (monday_data['high'] - monday_data['low']) / monday_data['open']
            volume_ratio = monday_data['volume'] / data['volume'].rolling(20).mean().iloc[monday_idx]
            
            return {
                'decline_detected': decline_detected,
                'decline_magnitude': monday_return,
                'intraday_volatility': intraday_volatility,
                'volume_ratio': volume_ratio,
                'monday_close': monday_data['close']
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing Monday performance: {e}")
            return {'decline_detected': False, 'decline_magnitude': 0.0}
    
    def _calculate_seasonality_score(self, data: pd.DataFrame) -> float:
        """Calculate seasonality-based probability score"""
        try:
            # Analyze historical Tuesday performance after Monday declines
            lookback_data = data.tail(self.seasonality_lookback)
            tuesday_performances = []
            
            for i in range(2, len(lookback_data)):
                current_date = lookback_data.index[i]
                
                if current_date.weekday() == WeekdayType.TUESDAY.value:
                    # Check if previous day was Monday with decline
                    monday_idx = i - 1
                    if (monday_idx >= 1 and 
                        lookback_data.index[monday_idx].weekday() == WeekdayType.MONDAY.value):
                        
                        friday_close = lookback_data.iloc[monday_idx - 1]['close']
                        monday_close = lookback_data.iloc[monday_idx]['close']
                        tuesday_close = lookback_data.iloc[i]['close']
                        
                        monday_return = (monday_close - friday_close) / friday_close
                        tuesday_return = (tuesday_close - monday_close) / monday_close
                        
                        # Only consider cases where Monday declined
                        if monday_return < 0:
                            tuesday_performances.append(tuesday_return)
            
            if len(tuesday_performances) < 10:  # Minimum sample size
                return 0.5  # Neutral probability
            
            # Calculate probability of positive Tuesday return
            positive_tuesdays = sum(1 for ret in tuesday_performances if ret > 0)
            probability = positive_tuesdays / len(tuesday_performances)
            
            # Calculate average Tuesday return magnitude
            avg_tuesday_return = np.mean(tuesday_performances)
            
            # Adjust probability based on magnitude
            magnitude_adjustment = min(abs(avg_tuesday_return) * 10, 0.1)
            adjusted_probability = probability + magnitude_adjustment
            
            return min(adjusted_probability, 0.95)
            
        except Exception as e:
            self.logger.error(f"Error calculating seasonality score: {e}")
            return 0.5
    
    def _analyze_candlestick_patterns(self, data: pd.DataFrame) -> CandlestickAnalysis:
        """Analyze candlestick patterns for reversal confirmation"""
        try:
            if len(data) < 3:
                return CandlestickAnalysis()
            
            # Get recent candles
            current = data.iloc[-1]
            prev1 = data.iloc[-2]
            prev2 = data.iloc[-3] if len(data) >= 3 else None
            
            # Calculate candle properties
            body_size = abs(current['close'] - current['open'])
            total_range = current['high'] - current['low']
            upper_shadow = current['high'] - max(current['open'], current['close'])
            lower_shadow = min(current['open'], current['close']) - current['low']
            
            # Avoid division by zero
            if total_range == 0:
                return CandlestickAnalysis()
            
            body_ratio = body_size / total_range
            upper_shadow_ratio = upper_shadow / total_range
            lower_shadow_ratio = lower_shadow / total_range
            
            # Pattern detection
            pattern = CandlestickPattern.NONE
            strength = 0.0
            
            # Hammer pattern (bullish reversal)
            if (lower_shadow_ratio > 0.6 and body_ratio < 0.3 and upper_shadow_ratio < 0.1):
                pattern = CandlestickPattern.HAMMER
                strength = 0.8
            
            # Doji patterns
            elif body_ratio < 0.1:
                if lower_shadow_ratio > 0.6:
                    pattern = CandlestickPattern.DRAGONFLY_DOJI
                    strength = 0.7
                elif upper_shadow_ratio > 0.6:
                    pattern = CandlestickPattern.GRAVESTONE_DOJI
                    strength = 0.3  # Bearish, lower strength for long signal
                else:
                    pattern = CandlestickPattern.DOJI
                    strength = 0.5
            
            # Bullish engulfing (requires previous candle)
            elif (current['close'] > current['open'] and prev1['close'] < prev1['open'] and
                  current['close'] > prev1['open'] and current['open'] < prev1['close']):
                pattern = CandlestickPattern.BULLISH_ENGULFING
                strength = 0.9
            
            # Spinning top
            elif (body_ratio < 0.3 and upper_shadow_ratio > 0.3 and lower_shadow_ratio > 0.3):
                pattern = CandlestickPattern.SPINNING_TOP
                strength = 0.4
            
            # Volume confirmation
            volume_avg = data['volume'].rolling(20).mean().iloc[-1]
            volume_confirmation = min(current['volume'] / volume_avg, 2.0) / 2.0
            
            # Trend context
            sma_20 = data['close'].rolling(20).mean().iloc[-1]
            trend_context = "bullish" if current['close'] > sma_20 else "bearish"
            
            # Calculate reliability score
            reliability_score = (strength * 0.6 + volume_confirmation * 0.4)
            
            return CandlestickAnalysis(
                pattern=pattern,
                strength=strength,
                volume_confirmation=volume_confirmation,
                trend_context=trend_context,
                reliability_score=reliability_score
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing candlestick patterns: {e}")
            return CandlestickAnalysis()
    
    def _calculate_volume_confirmation(self, data: pd.DataFrame) -> float:
        """Calculate volume-based confirmation score"""
        try:
            if len(data) < 20:
                return 0.5
            
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            
            # Volume ratio (capped at 3x for normalization)
            volume_ratio = min(current_volume / avg_volume, 3.0)
            
            # Normalize to 0-1 scale
            volume_score = (volume_ratio - 1.0) / 2.0
            volume_score = max(0.0, min(1.0, volume_score))
            
            return volume_score
            
        except Exception as e:
            self.logger.error(f"Error calculating volume confirmation: {e}")
            return 0.5
    
    def _calculate_signal_strength(self, monday_analysis: Dict, seasonality_score: float,
                                 pattern_analysis: CandlestickAnalysis, volume_score: float) -> float:
        """Calculate overall signal strength"""
        try:
            # Base strength from Monday decline magnitude
            decline_strength = min(abs(monday_analysis['decline_magnitude']) / 0.02, 1.0)
            
            # Seasonality component
            seasonality_component = (seasonality_score - 0.5) * 2  # Normalize to 0-1
            
            # Pattern confirmation component
            pattern_component = pattern_analysis.reliability_score * self.pattern_confirmation_weight
            
            # Volume confirmation component
            volume_component = volume_score * 0.2
            
            # Combine components
            total_strength = (
                decline_strength * 0.3 +
                seasonality_component * 0.4 +
                pattern_component * 0.2 +
                volume_component * 0.1
            )
            
            return max(0.0, min(1.0, total_strength))
            
        except Exception as e:
            self.logger.error(f"Error calculating signal strength: {e}")
            return 0.0
    
    def _check_exit_conditions(self, data: pd.DataFrame) -> List[StrategySignal]:
        """Check for exit conditions"""
        signals = []
        
        if not self.strategy_state.current_position:
            return signals
        
        current_time = data.index[-1]
        current_price = data['close'].iloc[-1]
        position = self.strategy_state.current_position
        
        try:
            # Time-based exit (hold maximum 3 days, exit by Friday)
            entry_time = position.entry_time
            days_held = (current_time - entry_time).days
            
            # Exit on Friday or after max holding period
            if (current_time.weekday() == 4 or  # Friday
                days_held >= self.max_holding_days):
                
                signal = StrategySignal(
                    timestamp=current_time,
                    signal_type=SignalType.EXIT_LONG,
                    strength=0.8,
                    confidence=0.9,
                    metadata={
                        'exit_reason': 'time_based',
                        'days_held': days_held,
                        'weekday': current_time.weekday()
                    }
                )
                signals.append(signal)
            
            # Price-based exits (stop-loss/take-profit)
            elif position.side == PositionSide.LONG:
                entry_price = position.entry_price
                
                # Stop-loss
                if current_price <= entry_price * (1 - self.stop_loss_pct):
                    signal = StrategySignal(
                        timestamp=current_time,
                        signal_type=SignalType.EXIT_LONG,
                        strength=1.0,
                        confidence=1.0,
                        metadata={
                            'exit_reason': 'stop_loss',
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'loss_pct': (current_price - entry_price) / entry_price
                        }
                    )
                    signals.append(signal)
                
                # Take-profit
                elif current_price >= entry_price * (1 + self.take_profit_pct):
                    signal = StrategySignal(
                        timestamp=current_time,
                        signal_type=SignalType.EXIT_LONG,
                        strength=0.9,
                        confidence=0.95,
                        metadata={
                            'exit_reason': 'take_profit',
                            'entry_price': entry_price,
                            'current_price': current_price,
                            'profit_pct': (current_price - entry_price) / entry_price
                        }
                    )
                    signals.append(signal)
        
        except Exception as e:
            self.logger.error(f"Error checking exit conditions: {e}")
        
        return signals
    
    def calculate_position_size(self, signal: StrategySignal, data: pd.DataFrame,
                              portfolio_value: float, current_positions: Dict) -> float:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size based on:
        1. Signal strength and confidence
        2. Market volatility
        3. Portfolio risk limits
        4. Seasonality confidence
        """
        try:
            if len(data) < self.volatility_lookback:
                return 0.0
            
            # Base position size
            base_size = self.max_position_size * portfolio_value
            
            # Adjust for signal strength and confidence
            signal_adjustment = signal.strength * signal.confidence
            
            # Volatility adjustment
            returns = data['close'].pct_change().dropna()
            volatility = returns.rolling(self.volatility_lookback).std().iloc[-1]
            vol_adjustment = max(0.5, min(1.5, 0.02 / volatility))  # Target 2% volatility
            
            # Seasonality confidence adjustment
            seasonality_score = signal.metadata.get('seasonality_score', 0.5)
            seasonality_adjustment = min(seasonality_score / 0.6, 1.2)  # Cap at 20% increase
            
            # Calculate final position size
            position_size = (
                base_size * 
                signal_adjustment * 
                vol_adjustment * 
                seasonality_adjustment
            )
            
            # Apply portfolio-level risk limits
            max_portfolio_risk = portfolio_value * 0.05  # 5% max risk per trade
            position_size = min(position_size, max_portfolio_risk)
            
            self.logger.info(
                f"Position size calculated: ${position_size:.2f} "
                f"(signal_adj={signal_adjustment:.3f}, vol_adj={vol_adjustment:.3f}, "
                f"seasonality_adj={seasonality_adjustment:.3f})"
            )
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def detect_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect current market regime based on:
        1. Volatility levels
        2. Trend strength
        3. Market stress indicators
        4. Seasonality patterns
        """
        try:
            if len(data) < max(self.volatility_lookback, self.trend_lookback):
                return MarketRegime.NORMAL
            
            # Calculate volatility metrics
            returns = data['close'].pct_change().dropna()
            current_vol = returns.rolling(self.volatility_lookback).std().iloc[-1]
            vol_percentile = (returns.rolling(252).std().rank(pct=True).iloc[-1] 
                            if len(returns) >= 252 else 0.5)
            
            # Calculate trend metrics
            sma_short = data['close'].rolling(20).mean().iloc[-1]
            sma_long = data['close'].rolling(self.trend_lookback).mean().iloc[-1]
            current_price = data['close'].iloc[-1]
            
            trend_strength = abs(sma_short - sma_long) / sma_long
            
            # Market stress indicators
            volume_stress = (data['volume'].rolling(20).mean().iloc[-1] / 
                           data['volume'].rolling(60).mean().iloc[-1])
            
            # Determine regime
            if vol_percentile > 0.8 or volume_stress > 1.5:
                regime = MarketRegime.HIGH_VOLATILITY
            elif vol_percentile < 0.2 and trend_strength < 0.02:
                regime = MarketRegime.LOW_VOLATILITY
            elif trend_strength > 0.05:
                regime = MarketRegime.TRENDING
            else:
                regime = MarketRegime.NORMAL
            
            self.logger.debug(
                f"Market regime detected: {regime.value} "
                f"(vol_pct={vol_percentile:.3f}, trend_str={trend_strength:.3f})"
            )
            
            return regime
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.NORMAL
    
    def create_execution_intent(self, signal: StrategySignal, position_size: float,
                              data: pd.DataFrame) -> Optional[ExecutionIntent]:
        """
        Pillar 4: Decoupled Execution Logic & Order Management
        
        Create execution intent based on:
        1. Signal characteristics
        2. Market conditions
        3. Urgency requirements
        4. Seasonality timing
        """
        try:
            current_price = data['close'].iloc[-1]
            
            # Determine market condition
            volume_ratio = (data['volume'].iloc[-1] / 
                          data['volume'].rolling(20).mean().iloc[-1])
            
            if volume_ratio > 1.5:
                market_condition = MarketCondition.HIGH_VOLUME
            elif volume_ratio < 0.7:
                market_condition = MarketCondition.LOW_VOLUME
            else:
                market_condition = MarketCondition.NORMAL
            
            # Determine execution urgency (Tuesday strategy needs timely execution)
            urgency = ExecutionUrgency.MEDIUM  # Balance between speed and price
            
            # Set time in force (day order for seasonality strategy)
            time_in_force = TimeInForce.DAY
            
            # Calculate limit price with small buffer
            if signal.signal_type in [SignalType.ENTRY_LONG]:
                limit_price = current_price * 1.001  # 0.1% above market
            else:
                limit_price = current_price * 0.999  # 0.1% below market
            
            # Create execution intent
            intent = create_execution_intent(
                signal=signal,
                quantity=position_size / current_price,  # Convert to shares
                current_price=current_price,
                market_condition=market_condition,
                urgency=urgency,
                time_in_force=time_in_force,
                order_type=OrderType.LIMIT,
                limit_price=limit_price
            )
            
            self.logger.info(
                f"Execution intent created: {intent.order_type.value} order for "
                f"{intent.quantity:.0f} shares at ${intent.limit_price:.2f}"
            )
            
            return intent
            
        except Exception as e:
            self.logger.error(f"Error creating execution intent: {e}")
            return None
    
    def calculate_performance_metrics(self, trades: List[Dict], 
                                    data: pd.DataFrame) -> PerformanceMetrics:
        """
        Pillar 5: Performance Tracking & Configurability
        
        Calculate comprehensive performance metrics including:
        1. Traditional metrics (Sharpe, Sortino, etc.)
        2. Seasonality-specific metrics
        3. Pattern recognition accuracy
        4. Risk-adjusted returns
        """
        try:
            if not trades:
                return PerformanceMetrics()
            
            # Calculate basic metrics
            returns = [trade.get('return', 0.0) for trade in trades]
            total_return = sum(returns)
            avg_return = np.mean(returns) if returns else 0.0
            
            # Win rate and profit factor
            winning_trades = [r for r in returns if r > 0]
            losing_trades = [r for r in returns if r < 0]
            
            win_rate = len(winning_trades) / len(returns) if returns else 0.0
            avg_win = np.mean(winning_trades) if winning_trades else 0.0
            avg_loss = abs(np.mean(losing_trades)) if losing_trades else 0.0
            profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) if losing_trades else float('inf')
            
            # Risk metrics
            returns_std = np.std(returns) if len(returns) > 1 else 0.0
            sharpe_ratio = (avg_return / returns_std) if returns_std > 0 else 0.0
            
            # Seasonality-specific metrics
            tuesday_trades = [trade for trade in trades 
                            if trade.get('entry_day') == WeekdayType.TUESDAY.value]
            tuesday_win_rate = (len([t for t in tuesday_trades if t.get('return', 0) > 0]) / 
                              len(tuesday_trades)) if tuesday_trades else 0.0
            
            # Pattern recognition accuracy
            pattern_trades = [trade for trade in trades 
                            if trade.get('pattern') != CandlestickPattern.NONE.value]
            pattern_accuracy = (len([t for t in pattern_trades if t.get('return', 0) > 0]) / 
                              len(pattern_trades)) if pattern_trades else 0.0
            
            # Maximum drawdown
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0.0
            
            return PerformanceMetrics(
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=len(trades),
                metadata={
                    'avg_return_per_trade': avg_return,
                    'avg_win': avg_win,
                    'avg_loss': avg_loss,
                    'tuesday_win_rate': tuesday_win_rate,
                    'pattern_accuracy': pattern_accuracy,
                    'volatility': returns_std,
                    'tuesday_trades': len(tuesday_trades),
                    'pattern_trades': len(pattern_trades)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics()


# Example configuration
EXAMPLE_CONFIG = {
    "strategy_name": "TurnaroundTuesdayStrategy",
    "strategy_type": "seasonality",
    "timeframe": "1D",
    "min_monday_decline": -0.005,
    "max_monday_decline": -0.03,
    "volume_threshold": 1.2,
    "pattern_confirmation_weight": 0.3,
    "seasonality_lookback": 252,
    "min_probability_threshold": 0.55,
    "max_position_size": 0.02,
    "stop_loss_pct": 0.015,
    "take_profit_pct": 0.025,
    "max_holding_days": 3,
    "volatility_lookback": 20,
    "trend_lookback": 50,
    "risk_management": {
        "max_portfolio_risk": 0.05,
        "position_sizing_method": "volatility_adjusted",
        "correlation_adjustment": True
    },
    "execution": {
        "order_type": "limit",
        "urgency": "medium",
        "time_in_force": "day",
        "slippage_tolerance": 0.001
    }
}


if __name__ == "__main__":
    # Example usage and testing
    import yfinance as yf
    
    # Create sample data
    symbol = "SPY"
    data = yf.download(symbol, start="2023-01-01", end="2024-01-01")
    data.columns = [col.lower() for col in data.columns]
    
    # Initialize strategy
    strategy = TurnaroundTuesdayStrategy(EXAMPLE_CONFIG)
    
    print(f"\n=== Turnaround Tuesday Strategy Test ===")
    print(f"Testing with {symbol} data from {data.index[0].date()} to {data.index[-1].date()}")
    print(f"Total data points: {len(data)}")
    
    # Test signal generation
    signals = strategy.generate_signals(data)
    print(f"\nGenerated {len(signals)} signals")
    
    for i, signal in enumerate(signals[:5]):  # Show first 5 signals
        print(f"Signal {i+1}: {signal.signal_type.value} at {signal.timestamp.date()}, "
              f"strength={signal.strength:.3f}, confidence={signal.confidence:.3f}")
        if signal.metadata:
            print(f"  Metadata: {signal.metadata}")
    
    # Test market regime detection
    regime = strategy.detect_market_regime(data)
    print(f"\nCurrent market regime: {regime.value}")
    
    # Test position sizing
    if signals:
        test_signal = signals[0]
        portfolio_value = 100000
        position_size = strategy.calculate_position_size(
            test_signal, data, portfolio_value, {}
        )
        print(f"\nPosition size for test signal: ${position_size:.2f}")
        
        # Test execution intent
        intent = strategy.create_execution_intent(test_signal, position_size, data)
        if intent:
            print(f"Execution intent: {intent.order_type.value} {intent.quantity:.0f} shares")
    
    # Test performance calculation with mock trades
    mock_trades = [
        {'return': 0.015, 'entry_day': 1, 'pattern': 'hammer'},
        {'return': -0.008, 'entry_day': 1, 'pattern': 'doji'},
        {'return': 0.022, 'entry_day': 1, 'pattern': 'bullish_engulfing'},
        {'return': 0.012, 'entry_day': 1, 'pattern': 'none'},
        {'return': -0.005, 'entry_day': 1, 'pattern': 'spinning_top'}
    ]
    
    performance = strategy.calculate_performance_metrics(mock_trades, data)
    print(f"\nPerformance Metrics:")
    print(f"Total Return: {performance.total_return:.3f}")
    print(f"Win Rate: {performance.win_rate:.3f}")
    print(f"Sharpe Ratio: {performance.sharpe_ratio:.3f}")
    print(f"Profit Factor: {performance.profit_factor:.3f}")
    print(f"Max Drawdown: {performance.max_drawdown:.3f}")
    
    if performance.metadata:
        print(f"Tuesday Win Rate: {performance.metadata.get('tuesday_win_rate', 0):.3f}")
        print(f"Pattern Accuracy: {performance.metadata.get('pattern_accuracy', 0):.3f}")
    
    print(f"\n=== Strategy Test Complete ===")
    print(f"\nKey Features Demonstrated:")
    print(f"✓ 5-Pillar Architecture Implementation")
    print(f"✓ Seasonality-based signal generation")
    print(f"✓ Candlestick pattern confirmation")
    print(f"✓ Volume-weighted analysis")
    print(f"✓ Dynamic risk management")
    print(f"✓ Market regime adaptation")
    print(f"✓ Comprehensive performance tracking")
    print(f"✓ Institutional-grade execution logic")

"""
Turnaround Tuesday Strategy - Key Features:

1. **Seasonality Focus**: Capitalizes on the statistical "Turnaround Tuesday" phenomenon
2. **Pattern Confirmation**: Enhanced with volume-weighted candlestick pattern analysis
3. **Risk Management**: Dynamic position sizing with volatility adjustment
4. **Time-based Exits**: Maximum 3-day holding period, exit by Friday
5. **Market Regime Awareness**: Adapts to different market conditions
6. **Institutional Architecture**: Full compliance with 5-Pillar framework
7. **Performance Tracking**: Specialized metrics for seasonality strategies
8. **Volume Analysis**: Comprehensive volume confirmation scoring
9. **Probability-based**: Uses historical analysis for signal confidence
10. **Professional Execution**: Sophisticated order management and timing

This strategy demonstrates how traditional market anomalies can be enhanced
with modern technical analysis and institutional-grade risk management.
"""