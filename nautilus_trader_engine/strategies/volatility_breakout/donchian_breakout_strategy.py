"""Donchian Channel Breakout Strategy - Institutional Grade Implementation

This strategy implements Richard Donchian's Channel Breakout system with institutional-grade
enhancements and modern risk management following the 5-Pillar Architecture.

Core Logic:
- Donchian Channels formed by highest high and lowest low over N periods
- Long breakout when price exceeds upper channel
- Short breakout when price falls below lower channel
- Exit on opposite channel touch or time-based exit

Signals:
- Bullish: Price breaks above upper Donchian Channel with volume confirmation
- Bearish: Price breaks below lower Donchian Channel with volume confirmation
- Neutral: Price within channel or weak breakouts

Enhancements:
- Multi-timeframe channel analysis
- Volume-weighted channel calculations
- False breakout filtering
- Dynamic channel period optimization
- Volatility-adjusted position sizing

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

from ..BaseInstitutionalStrategy import (
    BaseInstitutionalStrategy, IndicatorSignal, RiskParameters, ExecutionIntent,
    SignalType, MarketRegime, ExecutionAction, ExecutionAlgorithm, ExecutionUrgency, TimeInForce
)
from ..indicators.traditional.volatility_indicators import VolatilityIndicators
from ..indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ..indicators.traditional.momentum_indicators import MomentumIndicators
from ..risk_management_utils import RiskManagementUtils
from ..execution_intent_utils import ExecutionIntentUtils


class DonchianBreakoutStrategy(BaseInstitutionalStrategy):
    """
    Donchian Channel Breakout Strategy implementing the 5-Pillar Architecture.
    
    This strategy trades breakouts from Donchian Channels with institutional-grade
    risk management and advanced filtering techniques.
    """
    
    def __init__(self, config_path: str, symbol: str, timeframe: str = "1D"):
        super().__init__(config_path, symbol, timeframe)
        
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        self.volatility_indicators = VolatilityIndicators()
        self.volume_weighted_indicators = VolumeWeightedIndicators()
        self.momentum_indicators = MomentumIndicators()
        self.risk_utils = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        # Donchian Channel parameters from config
        self.entry_period = self.config.get('entry_period', 20)  # Entry channel period
        self.exit_period = self.config.get('exit_period', 10)    # Exit channel period
        self.fast_period = self.config.get('fast_period', 10)    # Fast channel for confirmation
        self.slow_period = self.config.get('slow_period', 55)    # Slow channel for trend
        
        # Enhanced parameters
        self.volume_weighted_channels = self.config.get('volume_weighted_channels', True)
        self.multi_timeframe_analysis = self.config.get('multi_timeframe_analysis', True)
        self.false_breakout_filter = self.config.get('false_breakout_filter', True)
        self.momentum_confirmation = self.config.get('momentum_confirmation', True)
        
        # Breakout parameters
        self.min_breakout_distance = self.config.get('min_breakout_distance', 0.001)  # 0.1%
        self.breakout_volume_threshold = self.config.get('breakout_volume_threshold', 1.3)
        self.confirmation_periods = self.config.get('confirmation_periods', 2)
        self.max_days_in_position = self.config.get('max_days_in_position', 30)
        
        # Channel optimization parameters
        self.adaptive_periods = self.config.get('adaptive_periods', True)
        self.volatility_adjustment = self.config.get('volatility_adjustment', True)
        self.trend_filter = self.config.get('trend_filter', True)
        
        # Position state tracking
        self.position_state = {
            'in_position': False,
            'position_type': None,  # 'long' or 'short'
            'entry_date': None,
            'entry_price': None,
            'days_in_position': 0,
            'exit_channel_level': None,
            'highest_favorable': None,
            'lowest_favorable': None,
            'breakout_strength': 0.0,
            'channel_width_at_entry': 0.0,
            'successful_breakouts': 0,
            'failed_breakouts': 0,
            'channel_efficiency': []
        }
        
        self.logger.info(f"Donchian Breakout Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Donchian Channel breakout analysis.
        
        Signal Logic:
        1. Calculate multiple Donchian Channels (entry, exit, fast, slow)
        2. Detect breakouts with volume confirmation
        3. Apply false breakout filters
        4. Confirm with momentum indicators
        5. Multi-timeframe alignment
        """
        try:
            required_periods = max(self.slow_period * 2, 120)
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for Donchian Channel calculation")
            
            # Calculate Donchian Channels
            channels_data = self._calculate_donchian_channels(data)
            if channels_data is None:
                return self._create_neutral_signal("Donchian Channels calculation failed")
            
            # Detect breakout signals
            breakout_analysis = self._analyze_breakout_conditions(data, channels_data)
            
            # Check position management (if in position)
            position_signal = self._check_position_management(data, channels_data)
            
            # Get momentum confirmation
            momentum_confirmation = self._get_momentum_confirmation(data) if self.momentum_confirmation else 1.0
            
            # Volume analysis
            volume_confirmation = self._analyze_breakout_volume(data)
            
            # False breakout filter
            is_false_breakout = self._check_false_breakout(data, channels_data) if self.false_breakout_filter else False
            
            # Multi-timeframe confirmation
            mtf_confirmation = self._get_multi_timeframe_confirmation(data) if self.multi_timeframe_analysis else 1.0
            
            # Trend filter
            trend_alignment = self._check_trend_alignment(data, channels_data) if self.trend_filter else 1.0
            
            # Determine primary signal
            primary_signal = self._determine_primary_donchian_signal(
                breakout_analysis, position_signal, momentum_confirmation, 
                volume_confirmation, mtf_confirmation, trend_alignment
            )
            
            # Apply filters
            if is_false_breakout:
                primary_signal['confidence'] *= 0.4
                self.position_state['failed_breakouts'] += 1
            
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update position state
            self._update_position_state(data, breakout_analysis, primary_signal)
            
            # Create metadata
            metadata = {
                'channels_data': {
                    'entry_upper': channels_data['entry_upper'].iloc[-1],
                    'entry_lower': channels_data['entry_lower'].iloc[-1],
                    'exit_upper': channels_data['exit_upper'].iloc[-1],
                    'exit_lower': channels_data['exit_lower'].iloc[-1],
                    'fast_upper': channels_data['fast_upper'].iloc[-1],
                    'fast_lower': channels_data['fast_lower'].iloc[-1],
                    'slow_upper': channels_data['slow_upper'].iloc[-1],
                    'slow_lower': channels_data['slow_lower'].iloc[-1],
                    'channel_width': channels_data['channel_width'].iloc[-1]
                },
                'breakout_analysis': breakout_analysis,
                'position_signal': position_signal,
                'momentum_confirmation': momentum_confirmation,
                'volume_confirmation': volume_confirmation,
                'mtf_confirmation': mtf_confirmation,
                'trend_alignment': trend_alignment,
                'is_false_breakout': is_false_breakout,
                'position_state': self.position_state.copy(),
                'price': data['close'].iloc[-1]
            }
            
            return IndicatorSignal(
                raw_value=primary_signal['raw_value'],
                signal_type=primary_signal['signal_type'],
                confidence=primary_signal['confidence'],
                strength=primary_signal['strength'],
                timeframe=self.timeframe,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error generating Donchian Breakout signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_donchian_channels(self, data: pd.DataFrame) -> Optional[Dict[str, pd.Series]]:
        """
        Calculate multiple Donchian Channels with optional volume weighting.
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            volume = data['volume']
            
            channels = {}
            
            # Define channel periods
            periods = {
                'entry': self.entry_period,
                'exit': self.exit_period,
                'fast': self.fast_period,
                'slow': self.slow_period
            }
            
            for name, period in periods.items():
                if self.volume_weighted_channels:
                    # Volume-weighted channel calculation (approximation)
                    # Weight recent prices more heavily if they had higher volume
                    volume_weights = volume.rolling(period).apply(
                        lambda x: x / x.sum() if x.sum() > 0 else pd.Series([1/len(x)] * len(x), index=x.index)
                    )
                    
                    # Calculate weighted highs and lows
                    weighted_highs = (high * volume).rolling(period).sum() / volume.rolling(period).sum()
                    weighted_lows = (low * volume).rolling(period).sum() / volume.rolling(period).sum()
                    
                    # Adjust with traditional channels for stability
                    traditional_upper = high.rolling(period).max()
                    traditional_lower = low.rolling(period).min()
                    
                    # Blend weighted and traditional (70% traditional, 30% weighted)
                    upper_channel = traditional_upper * 0.7 + weighted_highs * 0.3
                    lower_channel = traditional_lower * 0.7 + weighted_lows * 0.3
                else:
                    # Traditional Donchian Channels
                    upper_channel = high.rolling(period).max()
                    lower_channel = low.rolling(period).min()
                
                channels[f'{name}_upper'] = upper_channel
                channels[f'{name}_lower'] = lower_channel
                channels[f'{name}_middle'] = (upper_channel + lower_channel) / 2
            
            # Calculate channel width (normalized)
            channels['channel_width'] = (
                (channels['entry_upper'] - channels['entry_lower']) / channels['entry_middle']
            )
            
            # Channel efficiency (how often price touches channels)
            channels['efficiency'] = self._calculate_channel_efficiency(data, channels)
            
            # Adaptive period adjustment (if enabled)
            if self.adaptive_periods:
                channels['optimal_period'] = self._calculate_optimal_period(data)
            
            return channels
            
        except Exception as e:
            self.logger.error(f"Error calculating Donchian channels: {e}")
            return None
    
    def _calculate_channel_efficiency(self, data: pd.DataFrame, channels: Dict[str, pd.Series]) -> pd.Series:
        """
        Calculate channel efficiency - how often price touches the channels.
        """
        try:
            high = data['high']
            low = data['low']
            
            upper_touches = (high >= channels['entry_upper']).astype(int)
            lower_touches = (low <= channels['entry_lower']).astype(int)
            
            # Rolling efficiency over last 50 periods
            efficiency = (upper_touches + lower_touches).rolling(50).mean()
            
            return efficiency
            
        except Exception as e:
            self.logger.warning(f"Error calculating channel efficiency: {e}")
            return pd.Series([0.5] * len(data), index=data.index)
    
    def _calculate_optimal_period(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate optimal channel period based on recent volatility.
        """
        try:
            close = data['close']
            
            # Calculate rolling volatility
            returns = close.pct_change()
            volatility = returns.rolling(20).std()
            
            # Adjust period based on volatility
            # High volatility -> shorter periods, Low volatility -> longer periods
            volatility_percentile = volatility.rolling(100).rank(pct=True)
            
            # Scale between min and max periods
            min_period = max(5, self.entry_period // 2)
            max_period = self.entry_period * 2
            
            optimal_period = min_period + (max_period - min_period) * (1 - volatility_percentile)
            
            return optimal_period.fillna(self.entry_period)
            
        except Exception as e:
            self.logger.warning(f"Error calculating optimal period: {e}")
            return pd.Series([self.entry_period] * len(data), index=data.index)
    
    def _analyze_breakout_conditions(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Analyze current breakout conditions.
        """
        try:
            close = data['close']
            high = data['high']
            low = data['low']
            
            if len(close) < 3:
                return {'breakout_type': None, 'strength': 0.0}
            
            current_price = close.iloc[-1]
            current_high = high.iloc[-1]
            current_low = low.iloc[-1]
            
            entry_upper = channels_data['entry_upper'].iloc[-1]
            entry_lower = channels_data['entry_lower'].iloc[-1]
            entry_middle = channels_data['entry_middle'].iloc[-1]
            
            # Check for breakouts
            bullish_breakout = current_high > entry_upper
            bearish_breakout = current_low < entry_lower
            
            if not (bullish_breakout or bearish_breakout):
                return {'breakout_type': None, 'strength': 0.0}
            
            # Calculate breakout strength
            if bullish_breakout:
                breakout_distance = (current_price - entry_upper) / entry_upper
                breakout_type = 'bullish'
                # Check if it's a new high
                is_new_high = current_high >= high.rolling(self.slow_period).max().iloc[-1]
            else:
                breakout_distance = (entry_lower - current_price) / entry_lower
                breakout_type = 'bearish'
                # Check if it's a new low
                is_new_high = current_low <= low.rolling(self.slow_period).min().iloc[-1]
            
            # Normalize breakout strength
            breakout_strength = min(breakout_distance * 100, 1.0)
            
            # Check breakout persistence
            persistence_periods = self._check_breakout_persistence(data, channels_data, breakout_type)
            
            # Channel width analysis
            channel_width = channels_data['channel_width'].iloc[-1]
            channel_width_percentile = channels_data['channel_width'].rolling(100).rank(pct=True).iloc[-1]
            
            # Multi-channel confirmation
            fast_confirmation = self._check_fast_channel_confirmation(data, channels_data, breakout_type)
            slow_confirmation = self._check_slow_channel_confirmation(data, channels_data, breakout_type)
            
            return {
                'breakout_type': breakout_type,
                'strength': breakout_strength,
                'distance': breakout_distance,
                'persistence': persistence_periods,
                'is_new_extreme': is_new_high,
                'channel_width': channel_width,
                'channel_width_percentile': channel_width_percentile,
                'fast_confirmation': fast_confirmation,
                'slow_confirmation': slow_confirmation,
                'breakout_quality': self._assess_breakout_quality(data, channels_data, breakout_type)
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing breakout conditions: {e}")
            return {'breakout_type': None, 'strength': 0.0}
    
    def _check_breakout_persistence(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series], 
                                   breakout_type: str) -> int:
        """
        Check how many periods the breakout has persisted.
        """
        try:
            close = data['close']
            entry_upper = channels_data['entry_upper']
            entry_lower = channels_data['entry_lower']
            
            persistence = 0
            for i in range(len(close) - 1, max(0, len(close) - 10), -1):
                if breakout_type == 'bullish' and close.iloc[i] > entry_upper.iloc[i]:
                    persistence += 1
                elif breakout_type == 'bearish' and close.iloc[i] < entry_lower.iloc[i]:
                    persistence += 1
                else:
                    break
            
            return persistence
            
        except Exception as e:
            self.logger.warning(f"Error checking breakout persistence: {e}")
            return 0
    
    def _check_fast_channel_confirmation(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series], 
                                        breakout_type: str) -> bool:
        """
        Check if fast channel confirms the breakout.
        """
        try:
            close = data['close']
            current_price = close.iloc[-1]
            
            fast_upper = channels_data['fast_upper'].iloc[-1]
            fast_lower = channels_data['fast_lower'].iloc[-1]
            
            if breakout_type == 'bullish':
                return current_price > fast_upper
            else:
                return current_price < fast_lower
                
        except Exception as e:
            self.logger.warning(f"Error checking fast channel confirmation: {e}")
            return False
    
    def _check_slow_channel_confirmation(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series], 
                                        breakout_type: str) -> bool:
        """
        Check if slow channel confirms the trend direction.
        """
        try:
            close = data['close']
            current_price = close.iloc[-1]
            
            slow_middle = channels_data['slow_middle'].iloc[-1]
            
            if breakout_type == 'bullish':
                return current_price > slow_middle
            else:
                return current_price < slow_middle
                
        except Exception as e:
            self.logger.warning(f"Error checking slow channel confirmation: {e}")
            return False
    
    def _assess_breakout_quality(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series], 
                                breakout_type: str) -> float:
        """
        Assess the quality of the breakout based on multiple factors.
        """
        try:
            quality_score = 0.5  # Base quality
            
            # Factor 1: Channel efficiency
            efficiency = channels_data.get('efficiency', pd.Series([0.5] * len(data)))
            if len(efficiency) > 0:
                current_efficiency = efficiency.iloc[-1]
                if 0.1 <= current_efficiency <= 0.3:  # Optimal range
                    quality_score += 0.2
            
            # Factor 2: Channel width
            channel_width_percentile = channels_data['channel_width'].rolling(100).rank(pct=True).iloc[-1]
            if channel_width_percentile > 0.3:  # Not too narrow
                quality_score += 0.1
            
            # Factor 3: Time since last breakout
            if hasattr(self, 'position_state') and self.position_state:
                if self.position_state.get('days_in_position', 0) == 0:  # Fresh breakout
                    quality_score += 0.1
            
            # Factor 4: Volume confirmation (will be checked separately)
            # Factor 5: Historical success rate
            if hasattr(self, 'position_state') and self.position_state:
                total_breakouts = (self.position_state.get('successful_breakouts', 0) + 
                                 self.position_state.get('failed_breakouts', 0))
                if total_breakouts > 0:
                    success_rate = self.position_state.get('successful_breakouts', 0) / total_breakouts
                    quality_score += (success_rate - 0.5) * 0.2
            
            return max(0.1, min(1.0, quality_score))
            
        except Exception as e:
            self.logger.warning(f"Error assessing breakout quality: {e}")
            return 0.5
    
    def _check_position_management(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series]) -> Optional[Dict[str, Any]]:
        """
        Check position management signals if currently in a position.
        """
        try:
            if not self.position_state.get('in_position', False):
                return None
            
            close = data['close']
            current_price = close.iloc[-1]
            
            position_type = self.position_state.get('position_type')
            entry_price = self.position_state.get('entry_price', current_price)
            days_in_position = self.position_state.get('days_in_position', 0)
            
            exit_upper = channels_data['exit_upper'].iloc[-1]
            exit_lower = channels_data['exit_lower'].iloc[-1]
            
            # Check exit conditions
            should_exit = False
            exit_reason = None
            
            # Exit channel touch
            if position_type == 'long' and current_price <= exit_lower:
                should_exit = True
                exit_reason = 'exit_channel_touch'
            elif position_type == 'short' and current_price >= exit_upper:
                should_exit = True
                exit_reason = 'exit_channel_touch'
            
            # Time-based exit
            elif days_in_position >= self.max_days_in_position:
                should_exit = True
                exit_reason = 'time_exit'
            
            # Profit target (optional)
            profit_target_multiplier = self.config.get('profit_target_multiplier', 3.0)
            channel_width_at_entry = self.position_state.get('channel_width_at_entry', 0.02)
            
            if position_type == 'long':
                profit_target = entry_price * (1 + channel_width_at_entry * profit_target_multiplier)
                if current_price >= profit_target:
                    should_exit = True
                    exit_reason = 'profit_target'
            elif position_type == 'short':
                profit_target = entry_price * (1 - channel_width_at_entry * profit_target_multiplier)
                if current_price <= profit_target:
                    should_exit = True
                    exit_reason = 'profit_target'
            
            if should_exit:
                return {
                    'action': 'exit',
                    'reason': exit_reason,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'days_held': days_in_position,
                    'unrealized_pnl': self._calculate_unrealized_pnl(current_price, entry_price, position_type)
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error checking position management: {e}")
            return None
    
    def _calculate_unrealized_pnl(self, current_price: float, entry_price: float, position_type: str) -> float:
        """
        Calculate unrealized P&L for current position.
        """
        try:
            if position_type == 'long':
                return (current_price - entry_price) / entry_price
            else:
                return (entry_price - current_price) / entry_price
        except:
            return 0.0
    
    def _get_momentum_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get momentum confirmation for breakout signals.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            close = data['close']
            volume = data['volume']
            
            confirmations = []
            
            # RSI confirmation
            rsi = self.momentum_indicators.rsi(close, period=14)
            if len(rsi) > 0:
                current_rsi = rsi.iloc[-1]
                if 30 <= current_rsi <= 70:  # Not extreme
                    confirmations.append(1)
                elif current_rsi > 80 or current_rsi < 20:
                    confirmations.append(-0.5)  # Very extreme
                else:
                    confirmations.append(0.5)  # Moderately extreme
            
            # MACD confirmation
            macd_data = self.momentum_indicators.macd(close)
            if macd_data and len(macd_data['macd']) > 1:
                macd_line = macd_data['macd']
                signal_line = macd_data['signal']
                histogram = macd_data['histogram']
                
                # MACD direction
                if macd_line.iloc[-1] > signal_line.iloc[-1]:
                    confirmations.append(1)
                else:
                    confirmations.append(-1)
                
                # MACD momentum
                if len(histogram) > 1 and histogram.iloc[-1] > histogram.iloc[-2]:
                    confirmations.append(0.5)
                else:
                    confirmations.append(-0.5)
            
            # Price momentum
            if len(close) >= 10:
                price_momentum = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10]
                if abs(price_momentum) > 0.02:  # Significant momentum
                    confirmations.append(1 if price_momentum > 0 else -1)
                else:
                    confirmations.append(0)
            
            # Calculate confirmation multiplier
            if confirmations:
                avg_confirmation = np.mean(confirmations)
                return max(0.7, min(1.3, 1.0 + (avg_confirmation * 0.3)))
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error getting momentum confirmation: {e}")
            return 1.0
    
    def _analyze_breakout_volume(self, data: pd.DataFrame) -> float:
        """
        Analyze volume confirmation for breakouts.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            volume = data['volume']
            current_volume = volume.iloc[-1]
            
            # Multiple volume averages
            volume_ma_5 = volume.rolling(5).mean().iloc[-1]
            volume_ma_20 = volume.rolling(20).mean().iloc[-1]
            volume_ma_50 = volume.rolling(50).mean().iloc[-1] if len(volume) >= 50 else volume_ma_20
            
            # Volume confirmation score
            if current_volume > volume_ma_20 * self.breakout_volume_threshold:
                confirmation = 1.3  # Strong volume
            elif current_volume > volume_ma_5 * 1.2:
                confirmation = 1.1  # Good volume
            elif current_volume > volume_ma_50:
                confirmation = 1.0  # Average volume
            elif current_volume < volume_ma_20 * 0.6:
                confirmation = 0.6  # Weak volume
            else:
                confirmation = 0.8  # Below average volume
            
            return min(confirmation, 1.5)
            
        except Exception as e:
            self.logger.warning(f"Error analyzing breakout volume: {e}")
            return 1.0
    
    def _check_false_breakout(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series]) -> bool:
        """
        Check if the current breakout might be a false breakout.
        """
        try:
            if len(data) < 10:
                return False
            
            close = data['close']
            volume = data['volume']
            entry_upper = channels_data['entry_upper']
            entry_lower = channels_data['entry_lower']
            
            # Check for recent failed breakouts
            failed_breakouts = 0
            for i in range(max(1, len(close) - 15), len(close) - 1):
                if i <= 0:
                    continue
                
                # Check if price broke out but then reversed quickly
                if (close.iloc[i] > entry_upper.iloc[i] and 
                    close.iloc[i+1] <= entry_upper.iloc[i+1] * 0.995) or \
                   (close.iloc[i] < entry_lower.iloc[i] and 
                    close.iloc[i+1] >= entry_lower.iloc[i+1] * 1.005):
                    failed_breakouts += 1
            
            if failed_breakouts >= 3:  # Too many recent failures
                return True
            
            # Check volume
            current_volume = volume.iloc[-1]
            avg_volume = volume.rolling(20).mean().iloc[-1]
            
            if current_volume < avg_volume * 0.7:  # Very low volume
                return True
            
            # Check breakout distance
            current_price = close.iloc[-1]
            entry_upper_current = entry_upper.iloc[-1]
            entry_lower_current = entry_lower.iloc[-1]
            
            if current_price > entry_upper_current:
                breakout_distance = (current_price - entry_upper_current) / entry_upper_current
            elif current_price < entry_lower_current:
                breakout_distance = (entry_lower_current - current_price) / entry_lower_current
            else:
                return False  # No breakout
            
            if breakout_distance < self.min_breakout_distance:  # Too small breakout
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking false breakout: {e}")
            return False
    
    def _get_multi_timeframe_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get multi-timeframe confirmation (simplified).
        """
        try:
            if len(data) < 100:
                return 1.0
            
            close = data['close']
            
            # Check multiple timeframe trends
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean()
            sma_100 = close.rolling(100).mean()
            
            current_price = close.iloc[-1]
            
            # Count aligned trends
            aligned_trends = 0
            total_trends = 0
            
            if current_price > sma_20.iloc[-1]:
                aligned_trends += 1
            total_trends += 1
            
            if current_price > sma_50.iloc[-1]:
                aligned_trends += 1
            total_trends += 1
            
            if current_price > sma_100.iloc[-1]:
                aligned_trends += 1
            total_trends += 1
            
            # Trend alignment score
            alignment_ratio = aligned_trends / total_trends
            
            if alignment_ratio >= 0.67:  # 2/3 or more aligned
                return 1.2
            elif alignment_ratio >= 0.33:  # 1/3 aligned
                return 1.0
            else:  # No alignment
                return 0.8
                
        except Exception as e:
            self.logger.warning(f"Error getting multi-timeframe confirmation: {e}")
            return 1.0
    
    def _check_trend_alignment(self, data: pd.DataFrame, channels_data: Dict[str, pd.Series]) -> float:
        """
        Check if breakout aligns with longer-term trend.
        """
        try:
            close = data['close']
            slow_middle = channels_data['slow_middle']
            
            if len(close) < self.slow_period:
                return 1.0
            
            current_price = close.iloc[-1]
            slow_middle_current = slow_middle.iloc[-1]
            
            # Check trend direction
            if len(slow_middle) >= 10:
                trend_direction = slow_middle.iloc[-1] - slow_middle.iloc[-10]
                
                if trend_direction > 0 and current_price > slow_middle_current:
                    return 1.2  # Bullish trend alignment
                elif trend_direction < 0 and current_price < slow_middle_current:
                    return 1.2  # Bearish trend alignment
                else:
                    return 0.9  # Counter-trend
            
            return 1.0
            
        except Exception as e:
            self.logger.warning(f"Error checking trend alignment: {e}")
            return 1.0
    
    def _determine_primary_donchian_signal(self, breakout_analysis: Dict[str, Any], 
                                         position_signal: Optional[Dict[str, Any]],
                                         momentum_confirmation: float, volume_confirmation: float,
                                         mtf_confirmation: float, trend_alignment: float) -> Dict[str, Any]:
        """
        Determine the primary Donchian breakout signal.
        """
        try:
            # Handle position management first
            if position_signal and position_signal.get('action') == 'exit':
                return {
                    'signal_type': SignalType.NEUTRAL,  # Exit signal handled separately
                    'raw_value': 0.0,
                    'confidence': 0.8,
                    'strength': 0.5,
                    'source': 'position_exit'
                }
            
            # No breakout signal
            if not breakout_analysis.get('breakout_type'):
                return {
                    'signal_type': SignalType.NEUTRAL,
                    'raw_value': 0.0,
                    'confidence': 0.2,
                    'strength': 0.1,
                    'source': 'no_breakout'
                }
            
            # Calculate signal strength
            base_strength = breakout_analysis['strength']
            persistence_bonus = min(breakout_analysis.get('persistence', 0) / 3.0, 0.3)
            quality_bonus = breakout_analysis.get('breakout_quality', 0.5) * 0.2
            
            # Confirmation bonuses
            fast_conf_bonus = 0.1 if breakout_analysis.get('fast_confirmation', False) else 0
            slow_conf_bonus = 0.1 if breakout_analysis.get('slow_confirmation', False) else 0
            new_extreme_bonus = 0.1 if breakout_analysis.get('is_new_extreme', False) else 0
            
            signal_strength = (base_strength + persistence_bonus + quality_bonus + 
                             fast_conf_bonus + slow_conf_bonus + new_extreme_bonus) * \
                            momentum_confirmation * volume_confirmation * mtf_confirmation * trend_alignment
            
            # Determine confidence
            base_confidence = 0.6
            if breakout_analysis.get('persistence', 0) >= 2:
                base_confidence += 0.1
            if volume_confirmation > 1.2:
                base_confidence += 0.1
            if breakout_analysis.get('fast_confirmation', False):
                base_confidence += 0.05
            if breakout_analysis.get('slow_confirmation', False):
                base_confidence += 0.05
            
            confidence = min(base_confidence, 0.9)
            
            # Determine signal type
            breakout_type = breakout_analysis['breakout_type']
            
            if breakout_type == 'bullish':
                if signal_strength > 0.8:
                    signal_type = SignalType.STRONG_BULLISH
                else:
                    signal_type = SignalType.BULLISH
                raw_value = signal_strength
            else:
                if signal_strength > 0.8:
                    signal_type = SignalType.STRONG_BEARISH
                else:
                    signal_type = SignalType.BEARISH
                raw_value = -signal_strength
            
            return {
                'signal_type': signal_type,
                'raw_value': raw_value,
                'confidence': confidence,
                'strength': signal_strength,
                'source': 'breakout'
            }
            
        except Exception as e:
            self.logger.warning(f"Error determining primary Donchian signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_position_state(self, data: pd.DataFrame, breakout_analysis: Dict[str, Any], 
                              primary_signal: Dict[str, Any]) -> None:
        """
        Update internal position state tracking.
        """
        try:
            current_price = data['close'].iloc[-1]
            
            # Update days in position
            if self.position_state.get('in_position', False):
                self.position_state['days_in_position'] += 1
                
                # Update favorable price tracking
                position_type = self.position_state.get('position_type')
                if position_type == 'long':
                    if (self.position_state.get('highest_favorable') is None or 
                        current_price > self.position_state['highest_favorable']):
                        self.position_state['highest_favorable'] = current_price
                elif position_type == 'short':
                    if (self.position_state.get('lowest_favorable') is None or 
                        current_price < self.position_state['lowest_favorable']):
                        self.position_state['lowest_favorable'] = current_price
            
            # Handle new positions
            if (primary_signal['source'] == 'breakout' and 
                primary_signal['signal_type'] != SignalType.NEUTRAL and
                not self.position_state.get('in_position', False)):
                
                self.position_state['in_position'] = True
                self.position_state['entry_date'] = datetime.now()
                self.position_state['entry_price'] = current_price
                self.position_state['days_in_position'] = 0
                
                if primary_signal['signal_type'] in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                    self.position_state['position_type'] = 'long'
                    self.position_state['highest_favorable'] = current_price
                    self.position_state['lowest_favorable'] = None
                else:
                    self.position_state['position_type'] = 'short'
                    self.position_state['lowest_favorable'] = current_price
                    self.position_state['highest_favorable'] = None
                
                self.position_state['breakout_strength'] = breakout_analysis.get('strength', 0.0)
                self.position_state['channel_width_at_entry'] = breakout_analysis.get('channel_width', 0.02)
            
            # Handle position exits
            elif primary_signal['source'] == 'position_exit':
                if self.position_state.get('in_position', False):
                    # Determine if it was successful
                    entry_price = self.position_state.get('entry_price', current_price)
                    position_type = self.position_state.get('position_type')
                    
                    if position_type == 'long':
                        was_successful = current_price > entry_price
                    else:
                        was_successful = current_price < entry_price
                    
                    if was_successful:
                        self.position_state['successful_breakouts'] += 1
                    else:
                        self.position_state['failed_breakouts'] += 1
                
                # Reset position state
                self.position_state['in_position'] = False
                self.position_state['position_type'] = None
                self.position_state['entry_date'] = None
                self.position_state['entry_price'] = None
                self.position_state['days_in_position'] = 0
                self.position_state['highest_favorable'] = None
                self.position_state['lowest_favorable'] = None
            
        except Exception as e:
            self.logger.warning(f"Error updating position state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using Donchian analysis.
        
        Risk Logic:
        1. Position sizing based on channel width and breakout strength
        2. Stop loss using exit channel or ATR
        3. Take profit at channel width multiples
        4. Trailing stop using channel expansion
        """
        try:
            current_price = data['close'].iloc[-1]
            channels_data = signal.metadata.get('channels_data', {})
            breakout_analysis = signal.metadata.get('breakout_analysis', {})
            
            # Calculate ATR for additional risk metrics
            high = data['high']
            low = data['low']
            close = data['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Base position size
            base_position = self.config.get('base_position_size', 1000)
            
            # Adjust position size based on channel width and breakout quality
            channel_width = channels_data.get('channel_width', 0.02)
            breakout_strength = breakout_analysis.get('strength', 0.5)
            breakout_quality = breakout_analysis.get('breakout_quality', 0.5)
            
            # Volatility adjustment (wider channels = smaller positions)
            volatility_multiplier = max(0.5, min(1.5, 1.0 / (channel_width * 50)))
            quality_multiplier = 0.7 + (breakout_quality * 0.6)  # 0.7x to 1.3x
            strength_multiplier = 0.8 + (breakout_strength * 0.4)  # 0.8x to 1.2x
            
            position_size = base_position * volatility_multiplier * quality_multiplier * strength_multiplier
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss and take profit calculation
            exit_upper = channels_data.get('exit_upper', current_price * 1.02)
            exit_lower = channels_data.get('exit_lower', current_price * 0.98)
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions
                stop_loss_price = min(exit_lower, current_price - (atr * 2))
                # Take profit at channel width multiple
                take_profit_price = current_price + (channel_width * current_price * 2)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions
                stop_loss_price = max(exit_upper, current_price + (atr * 2))
                # Take profit at channel width multiple
                take_profit_price = current_price - (channel_width * current_price * 2)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using channel width
            trailing_stop_distance = max(atr * 1.5, channel_width * current_price * 0.5)
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=self.config.get('max_position_size', 5000),
                account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
                volatility_adjustment=volatility_multiplier,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime using channel analysis.
        
        Regime Logic:
        1. Channel width for volatility assessment
        2. Breakout frequency for trending vs ranging
        3. Price position within channels
        """
        try:
            if len(data) < self.slow_period:
                return MarketRegime.UNKNOWN
            
            channels_data = self._calculate_donchian_channels(data)
            if not channels_data:
                return MarketRegime.UNKNOWN
            
            # Channel width analysis
            channel_width = channels_data['channel_width']
            channel_width_percentile = channel_width.rolling(100).rank(pct=True).iloc[-1]
            
            # Price position analysis
            close = data['close']
            entry_upper = channels_data['entry_upper']
            entry_lower = channels_data['entry_lower']
            entry_middle = channels_data['entry_middle']
            
            current_price = close.iloc[-1]
            current_upper = entry_upper.iloc[-1]
            current_lower = entry_lower.iloc[-1]
            current_middle = entry_middle.iloc[-1]
            
            # Breakout frequency
            recent_breakouts = 0
            for i in range(max(0, len(close) - 20), len(close)):
                if (close.iloc[i] > entry_upper.iloc[i] or 
                    close.iloc[i] < entry_lower.iloc[i]):
                    recent_breakouts += 1
            
            breakout_frequency = recent_breakouts / 20.0
            
            # Determine regime
            if channel_width_percentile < 0.2:
                return MarketRegime.LOW_VOLATILITY
            elif channel_width_percentile > 0.8:
                return MarketRegime.HIGH_VOLATILITY
            elif breakout_frequency > 0.3:  # Frequent breakouts
                if current_price > current_middle:
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on Donchian breakout signals.
        
        Execution Logic:
        1. Strong breakouts get immediate market orders
        2. Weak breakouts get limit orders
        3. High-quality breakouts get VWAP execution
        """
        try:
            if signal.signal_type == SignalType.NEUTRAL:
                return None
            
            # Handle position exits first
            position_signal = signal.metadata.get('position_signal')
            if position_signal and position_signal.get('action') == 'exit':
                # Determine exit action
                position_type = self.position_state.get('position_type')
                if position_type == 'long':
                    action = ExecutionAction.EXIT_LONG
                elif position_type == 'short':
                    action = ExecutionAction.EXIT_SHORT
                else:
                    return None
                
                return ExecutionIntent(
                    action=action,
                    symbol=self.symbol,
                    quantity=risk_params.position_size,
                    algorithm=ExecutionAlgorithm.MARKET,
                    urgency=ExecutionUrgency.HIGH,
                    time_in_force=TimeInForce.IOC,
                    limit_price=None,
                    stop_price=None,
                    metadata={
                        'strategy': 'Donchian_Breakout',
                        'exit_reason': position_signal.get('reason'),
                        'days_held': position_signal.get('days_held', 0),
                        'unrealized_pnl': position_signal.get('unrealized_pnl', 0.0)
                    }
                )
            
            # Handle new entries
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                action = ExecutionAction.ENTER_LONG
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                action = ExecutionAction.ENTER_SHORT
            else:
                return None
            
            # Determine execution parameters
            breakout_analysis = signal.metadata.get('breakout_analysis', {})
            breakout_strength = breakout_analysis.get('strength', 0.5)
            breakout_quality = breakout_analysis.get('breakout_quality', 0.5)
            volume_confirmation = signal.metadata.get('volume_confirmation', 1.0)
            
            if signal.signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH]:
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif breakout_quality > 0.7 and volume_confirmation > 1.2:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.MEDIUM
            elif signal.strength > 0.6:
                algorithm = ExecutionAlgorithm.TWAP
                urgency = ExecutionUrgency.MEDIUM
            else:
                algorithm = ExecutionAlgorithm.LIMIT
                urgency = ExecutionUrgency.LOW
            
            return ExecutionIntent(
                action=action,
                symbol=self.symbol,
                quantity=risk_params.position_size,
                algorithm=algorithm,
                urgency=urgency,
                time_in_force=TimeInForce.GTC,
                limit_price=None,
                stop_price=risk_params.stop_loss_price,
                metadata={
                    'strategy': 'Donchian_Breakout',
                    'signal_confidence': signal.confidence,
                    'breakout_strength': breakout_strength,
                    'breakout_quality': breakout_quality,
                    'channels_data': signal.metadata.get('channels_data'),
                    'take_profit': risk_params.take_profit_price,
                    'trailing_stop': risk_params.trailing_stop_distance
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error determining execution intent: {e}")
            return None
    
    def _update_performance_metrics(self, execution_result: Dict[str, Any]) -> None:
        """
        PILLAR 5: Update strategy performance metrics.
        
        Tracks:
        1. Donchian-specific performance metrics
        2. Breakout success rates
        3. Channel efficiency analysis
        """
        try:
            if execution_result.get('status') == 'filled':
                pnl = execution_result.get('pnl', 0.0)
                breakout_strength = execution_result.get('metadata', {}).get('breakout_strength', 0.5)
                breakout_quality = execution_result.get('metadata', {}).get('breakout_quality', 0.5)
                
                # Update general performance metrics
                self.performance_metrics.total_trades += 1
                self.performance_metrics.total_return += pnl
                
                if pnl > 0:
                    self.performance_metrics.winning_trades += 1
                    self.performance_metrics.average_win = (
                        (self.performance_metrics.average_win * (self.performance_metrics.winning_trades - 1) + pnl) /
                        self.performance_metrics.winning_trades
                    )
                    self.performance_metrics.largest_win = max(self.performance_metrics.largest_win, pnl)
                    
                    # Update successful breakouts
                    if hasattr(self, 'position_state'):
                        self.position_state['successful_breakouts'] += 1
                else:
                    self.performance_metrics.losing_trades += 1
                    self.performance_metrics.average_loss = (
                        (self.performance_metrics.average_loss * (self.performance_metrics.losing_trades - 1) + abs(pnl)) /
                        self.performance_metrics.losing_trades
                    )
                    self.performance_metrics.largest_loss = max(self.performance_metrics.largest_loss, abs(pnl))
                
                # Calculate win rate and profit factor
                if self.performance_metrics.total_trades > 0:
                    self.performance_metrics.win_rate = (
                        self.performance_metrics.winning_trades / self.performance_metrics.total_trades
                    )
                
                if self.performance_metrics.losing_trades > 0 and self.performance_metrics.average_loss > 0:
                    total_wins = self.performance_metrics.winning_trades * self.performance_metrics.average_win
                    total_losses = self.performance_metrics.losing_trades * self.performance_metrics.average_loss
                    self.performance_metrics.profit_factor = total_wins / total_losses
                
                self.logger.info(
                    f"Donchian Breakout Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Breakout Strength: {breakout_strength:.2f}, "
                    f"Breakout Quality: {breakout_quality:.2f}, "
                    f"In Position: {self.position_state['in_position']}, "
                    f"Position Type: {self.position_state.get('position_type', 'None')}, "
                    f"Days in Position: {self.position_state.get('days_in_position', 0)}, "
                    f"Successful Breakouts: {self.position_state.get('successful_breakouts', 0)}, "
                    f"Failed Breakouts: {self.position_state.get('failed_breakouts', 0)}"
                )
                
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _create_neutral_signal(self, reason: str) -> IndicatorSignal:
        """Create a neutral signal with given reason"""
        return IndicatorSignal(
            raw_value=0.0,
            signal_type=SignalType.NEUTRAL,
            confidence=0.0,
            strength=0.0,
            timeframe=self.timeframe,
            timestamp=datetime.now(),
            metadata={'reason': reason}
        )
    
    def _create_default_risk_parameters(self) -> RiskParameters:
        """Create default risk parameters in case of calculation errors"""
        return RiskParameters(
            position_size=1000,
            stop_loss_price=None,
            take_profit_price=None,
            trailing_stop_distance=None,
            max_position_size=5000,
            account_risk_percentage=0.02,
            volatility_adjustment=1.0,
            portfolio_correlation_adjustment=1.0
        )