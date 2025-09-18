"""Turtle Trading Strategy - Institutional Grade Implementation

This strategy implements the famous Turtle Trading system developed by Richard Dennis
with institutional-grade enhancements and modern risk management.

Core Logic:
- Dual breakout system (System 1: 20-day, System 2: 55-day)
- Position sizing based on True Range (N)
- Pyramid adding on favorable moves
- Stop loss based on 2N rule
- Volume-weighted breakout confirmation
- Modern portfolio theory enhancements

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..BaseInstitutionalStrategy import (
    BaseInstitutionalStrategy, IndicatorSignal, RiskParameters, ExecutionIntent,
    SignalType, MarketRegime, ExecutionAction, ExecutionAlgorithm, ExecutionUrgency, TimeInForce
)
from ..indicators.traditional.volatility_indicators import VolatilityIndicators
from ..indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ..indicators.traditional.trend_indicators import TrendIndicators
from ..risk_management_utils import RiskManagementUtils
from ..execution_intent_utils import ExecutionIntentUtils


class TurtleTradingStrategy(BaseInstitutionalStrategy):
    """
    Turtle Trading Strategy implementing the 5-Pillar Architecture.
    
    This strategy implements the original Turtle Trading rules with modern
    institutional enhancements and sophisticated risk management.
    """
    
    def __init__(self, config_path: str, symbol: str, timeframe: str = "1D"):
        super().__init__(config_path, symbol, timeframe)
        
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        self.volatility_indicators = VolatilityIndicators()
        self.volume_indicators = VolumeWeightedIndicators()
        self.trend_indicators = TrendIndicators()
        self.risk_utils = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        # Turtle Trading parameters from config
        self.system1_entry_period = self.config.get('system1_entry_period', 20)  # System 1: 20-day breakout
        self.system1_exit_period = self.config.get('system1_exit_period', 10)   # System 1: 10-day exit
        self.system2_entry_period = self.config.get('system2_entry_period', 55) # System 2: 55-day breakout
        self.system2_exit_period = self.config.get('system2_exit_period', 20)   # System 2: 20-day exit
        
        self.n_period = self.config.get('n_period', 20)  # True Range period for N calculation
        self.stop_loss_n_multiple = self.config.get('stop_loss_n_multiple', 2.0)  # 2N stop loss
        self.pyramid_n_multiple = self.config.get('pyramid_n_multiple', 0.5)  # 0.5N for pyramid adds
        self.max_pyramid_units = self.config.get('max_pyramid_units', 4)  # Maximum 4 units
        
        self.use_system1 = self.config.get('use_system1', True)
        self.use_system2 = self.config.get('use_system2', True)
        self.volume_confirmation = self.config.get('volume_confirmation', True)
        self.modern_enhancements = self.config.get('modern_enhancements', True)
        
        # Turtle state tracking
        self.turtle_state = {
            'current_position': 0,  # Number of units held
            'entry_prices': [],     # Prices of each unit
            'last_entry_price': None,
            'current_n': 0.0,       # Current N value (volatility measure)
            'system1_last_breakout': None,
            'system2_last_breakout': None,
            'trend_direction': 'neutral'
        }
        
        self.logger.info(f"Turtle Trading Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Turtle Trading rules.
        
        Signal Logic:
        1. Calculate N (True Range-based volatility)
        2. System 1: 20-day breakout entry, 10-day breakout exit
        3. System 2: 55-day breakout entry, 20-day breakout exit
        4. Volume-weighted breakout confirmation
        5. Pyramid adding opportunities
        """
        try:
            required_periods = max(self.system2_entry_period, self.n_period) + 5
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for Turtle calculation")
            
            # Calculate N (volatility measure)
            current_n = self._calculate_n(data)
            if current_n is None:
                return self._create_neutral_signal("N calculation failed")
            
            self.turtle_state['current_n'] = current_n
            
            # Calculate breakout levels
            breakout_levels = self._calculate_breakout_levels(data)
            
            current_price = data['close'].iloc[-1]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            
            # Check for breakout signals
            system1_signal = self._check_system1_signal(data, breakout_levels, current_price, current_high, current_low)
            system2_signal = self._check_system2_signal(data, breakout_levels, current_price, current_high, current_low)
            
            # Volume confirmation
            volume_conf = self._get_volume_breakout_confirmation(data) if self.volume_confirmation else 1.0
            
            # Check for pyramid opportunities
            pyramid_signal = self._check_pyramid_opportunity(current_price)
            
            # Determine primary signal
            primary_signal = self._determine_primary_signal(system1_signal, system2_signal, pyramid_signal)
            
            # Apply modern enhancements
            if self.modern_enhancements:
                primary_signal = self._apply_modern_enhancements(data, primary_signal)
            
            # Apply volume confirmation
            primary_signal['confidence'] *= volume_conf
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Create metadata
            metadata = {
                'current_n': current_n,
                'breakout_levels': breakout_levels,
                'system1_signal': system1_signal,
                'system2_signal': system2_signal,
                'pyramid_signal': pyramid_signal,
                'volume_confirmation': volume_conf,
                'turtle_state': self.turtle_state.copy(),
                'price': current_price
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
            self.logger.error(f"Error generating Turtle Trading signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_n(self, data: pd.DataFrame) -> Optional[float]:
        """
        Calculate N - the Turtle's measure of volatility (True Range).
        
        N = Average True Range over the past 20 days
        """
        try:
            if len(data) < self.n_period + 1:
                return None
            
            # Calculate True Range
            high = data['high']
            low = data['low']
            close = data['close']
            
            # True Range = max(H-L, H-C_prev, C_prev-L)
            prev_close = close.shift(1)
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # N = Simple Moving Average of True Range
            n_value = true_range.rolling(window=self.n_period).mean().iloc[-1]
            
            return n_value
            
        except Exception as e:
            self.logger.error(f"Error calculating N: {e}")
            return None
    
    def _calculate_breakout_levels(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate breakout levels for both systems.
        """
        try:
            levels = {}
            
            # System 1 levels
            if len(data) >= self.system1_entry_period:
                levels['system1_entry_high'] = data['high'].rolling(self.system1_entry_period).max().iloc[-1]
                levels['system1_entry_low'] = data['low'].rolling(self.system1_entry_period).min().iloc[-1]
            
            if len(data) >= self.system1_exit_period:
                levels['system1_exit_high'] = data['high'].rolling(self.system1_exit_period).max().iloc[-1]
                levels['system1_exit_low'] = data['low'].rolling(self.system1_exit_period).min().iloc[-1]
            
            # System 2 levels
            if len(data) >= self.system2_entry_period:
                levels['system2_entry_high'] = data['high'].rolling(self.system2_entry_period).max().iloc[-1]
                levels['system2_entry_low'] = data['low'].rolling(self.system2_entry_period).min().iloc[-1]
            
            if len(data) >= self.system2_exit_period:
                levels['system2_exit_high'] = data['high'].rolling(self.system2_exit_period).max().iloc[-1]
                levels['system2_exit_low'] = data['low'].rolling(self.system2_exit_period).min().iloc[-1]
            
            return levels
            
        except Exception as e:
            self.logger.error(f"Error calculating breakout levels: {e}")
            return {}
    
    def _check_system1_signal(self, data: pd.DataFrame, levels: Dict[str, float], 
                             current_price: float, current_high: float, current_low: float) -> Dict[str, Any]:
        """
        Check System 1 signals (20-day entry, 10-day exit).
        """
        try:
            if not self.use_system1:
                return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
            signal = {'type': 'none', 'strength': 0.0, 'confidence': 0.5}
            
            # Entry signals
            if 'system1_entry_high' in levels and current_high > levels['system1_entry_high']:
                # Bullish breakout
                breakout_strength = (current_high - levels['system1_entry_high']) / levels['system1_entry_high']
                signal = {
                    'type': 'bullish_entry',
                    'strength': min(breakout_strength * 100, 1.0),
                    'confidence': 0.7,
                    'breakout_level': levels['system1_entry_high']
                }
                self.turtle_state['system1_last_breakout'] = 'bullish'
                
            elif 'system1_entry_low' in levels and current_low < levels['system1_entry_low']:
                # Bearish breakout
                breakout_strength = (levels['system1_entry_low'] - current_low) / levels['system1_entry_low']
                signal = {
                    'type': 'bearish_entry',
                    'strength': min(breakout_strength * 100, 1.0),
                    'confidence': 0.7,
                    'breakout_level': levels['system1_entry_low']
                }
                self.turtle_state['system1_last_breakout'] = 'bearish'
            
            # Exit signals (only if we have a position)
            elif self.turtle_state['current_position'] != 0:
                if ('system1_exit_low' in levels and 
                    self.turtle_state['current_position'] > 0 and 
                    current_low < levels['system1_exit_low']):
                    # Exit long position
                    signal = {
                        'type': 'exit_long',
                        'strength': 0.8,
                        'confidence': 0.9,
                        'exit_level': levels['system1_exit_low']
                    }
                    
                elif ('system1_exit_high' in levels and 
                      self.turtle_state['current_position'] < 0 and 
                      current_high > levels['system1_exit_high']):
                    # Exit short position
                    signal = {
                        'type': 'exit_short',
                        'strength': 0.8,
                        'confidence': 0.9,
                        'exit_level': levels['system1_exit_high']
                    }
            
            return signal
            
        except Exception as e:
            self.logger.warning(f"Error checking System 1 signal: {e}")
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
    
    def _check_system2_signal(self, data: pd.DataFrame, levels: Dict[str, float], 
                             current_price: float, current_high: float, current_low: float) -> Dict[str, Any]:
        """
        Check System 2 signals (55-day entry, 20-day exit).
        """
        try:
            if not self.use_system2:
                return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
            signal = {'type': 'none', 'strength': 0.0, 'confidence': 0.5}
            
            # System 2 only enters if System 1 last signal was a loser
            # For simplicity, we'll always allow System 2 entries in this implementation
            
            # Entry signals
            if 'system2_entry_high' in levels and current_high > levels['system2_entry_high']:
                # Bullish breakout
                breakout_strength = (current_high - levels['system2_entry_high']) / levels['system2_entry_high']
                signal = {
                    'type': 'bullish_entry',
                    'strength': min(breakout_strength * 100, 1.0),
                    'confidence': 0.8,  # Higher confidence for longer-term breakout
                    'breakout_level': levels['system2_entry_high']
                }
                self.turtle_state['system2_last_breakout'] = 'bullish'
                
            elif 'system2_entry_low' in levels and current_low < levels['system2_entry_low']:
                # Bearish breakout
                breakout_strength = (levels['system2_entry_low'] - current_low) / levels['system2_entry_low']
                signal = {
                    'type': 'bearish_entry',
                    'strength': min(breakout_strength * 100, 1.0),
                    'confidence': 0.8,
                    'breakout_level': levels['system2_entry_low']
                }
                self.turtle_state['system2_last_breakout'] = 'bearish'
            
            # Exit signals
            elif self.turtle_state['current_position'] != 0:
                if ('system2_exit_low' in levels and 
                    self.turtle_state['current_position'] > 0 and 
                    current_low < levels['system2_exit_low']):
                    # Exit long position
                    signal = {
                        'type': 'exit_long',
                        'strength': 0.9,
                        'confidence': 0.95,
                        'exit_level': levels['system2_exit_low']
                    }
                    
                elif ('system2_exit_high' in levels and 
                      self.turtle_state['current_position'] < 0 and 
                      current_high > levels['system2_exit_high']):
                    # Exit short position
                    signal = {
                        'type': 'exit_short',
                        'strength': 0.9,
                        'confidence': 0.95,
                        'exit_level': levels['system2_exit_high']
                    }
            
            return signal
            
        except Exception as e:
            self.logger.warning(f"Error checking System 2 signal: {e}")
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
    
    def _check_pyramid_opportunity(self, current_price: float) -> Dict[str, Any]:
        """
        Check for pyramid adding opportunities.
        
        Turtles add to winning positions every 0.5N move in their favor.
        """
        try:
            if (self.turtle_state['current_position'] == 0 or 
                self.turtle_state['current_position'] >= self.max_pyramid_units or
                self.turtle_state['last_entry_price'] is None or
                self.turtle_state['current_n'] == 0):
                return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
            last_entry = self.turtle_state['last_entry_price']
            n_value = self.turtle_state['current_n']
            pyramid_threshold = n_value * self.pyramid_n_multiple
            
            if self.turtle_state['current_position'] > 0:  # Long position
                if current_price >= last_entry + pyramid_threshold:
                    # Add to long position
                    move_strength = (current_price - last_entry) / pyramid_threshold
                    return {
                        'type': 'add_long',
                        'strength': min(move_strength, 1.0),
                        'confidence': 0.6,
                        'pyramid_level': self.turtle_state['current_position'] + 1
                    }
            
            elif self.turtle_state['current_position'] < 0:  # Short position
                if current_price <= last_entry - pyramid_threshold:
                    # Add to short position
                    move_strength = (last_entry - current_price) / pyramid_threshold
                    return {
                        'type': 'add_short',
                        'strength': min(move_strength, 1.0),
                        'confidence': 0.6,
                        'pyramid_level': abs(self.turtle_state['current_position']) + 1
                    }
            
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
        except Exception as e:
            self.logger.warning(f"Error checking pyramid opportunity: {e}")
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
    
    def _get_volume_breakout_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get volume confirmation for breakout signals.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].rolling(20).mean().iloc[-1]
            
            if avg_volume == 0:
                return 1.0
            
            volume_ratio = current_volume / avg_volume
            
            # Strong volume confirmation
            if volume_ratio > 1.5:
                return min(1.0 + (volume_ratio - 1.5) * 0.2, 1.4)
            # Weak volume
            elif volume_ratio < 0.7:
                return 0.8
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _determine_primary_signal(self, system1: Dict[str, Any], system2: Dict[str, Any], 
                                 pyramid: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the primary signal from all systems.
        """
        try:
            # Priority: Exit signals > Pyramid signals > Entry signals
            
            # Check for exit signals first
            if system1['type'] in ['exit_long', 'exit_short']:
                return {
                    'signal_type': SignalType.STRONG_BEARISH if system1['type'] == 'exit_long' else SignalType.STRONG_BULLISH,
                    'raw_value': -system1['strength'] if system1['type'] == 'exit_long' else system1['strength'],
                    'confidence': system1['confidence'],
                    'strength': system1['strength'],
                    'source': 'system1_exit'
                }
            
            if system2['type'] in ['exit_long', 'exit_short']:
                return {
                    'signal_type': SignalType.STRONG_BEARISH if system2['type'] == 'exit_long' else SignalType.STRONG_BULLISH,
                    'raw_value': -system2['strength'] if system2['type'] == 'exit_long' else system2['strength'],
                    'confidence': system2['confidence'],
                    'strength': system2['strength'],
                    'source': 'system2_exit'
                }
            
            # Check for pyramid signals
            if pyramid['type'] in ['add_long', 'add_short']:
                return {
                    'signal_type': SignalType.BULLISH if pyramid['type'] == 'add_long' else SignalType.BEARISH,
                    'raw_value': pyramid['strength'] if pyramid['type'] == 'add_long' else -pyramid['strength'],
                    'confidence': pyramid['confidence'],
                    'strength': pyramid['strength'],
                    'source': 'pyramid'
                }
            
            # Check for entry signals (System 2 has priority over System 1)
            if system2['type'] in ['bullish_entry', 'bearish_entry']:
                return {
                    'signal_type': SignalType.STRONG_BULLISH if system2['type'] == 'bullish_entry' else SignalType.STRONG_BEARISH,
                    'raw_value': system2['strength'] if system2['type'] == 'bullish_entry' else -system2['strength'],
                    'confidence': system2['confidence'],
                    'strength': system2['strength'],
                    'source': 'system2_entry'
                }
            
            if system1['type'] in ['bullish_entry', 'bearish_entry']:
                return {
                    'signal_type': SignalType.BULLISH if system1['type'] == 'bullish_entry' else SignalType.BEARISH,
                    'raw_value': system1['strength'] if system1['type'] == 'bullish_entry' else -system1['strength'],
                    'confidence': system1['confidence'],
                    'strength': system1['strength'],
                    'source': 'system1_entry'
                }
            
            # No signal
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'none'
            }
            
        except Exception as e:
            self.logger.warning(f"Error determining primary signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _apply_modern_enhancements(self, data: pd.DataFrame, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply modern enhancements to the classic Turtle system.
        """
        try:
            # Trend filter using longer-term moving average
            if len(data) >= 100:
                ma_100 = data['close'].rolling(100).mean().iloc[-1]
                current_price = data['close'].iloc[-1]
                
                # Enhance bullish signals in uptrend, reduce in downtrend
                if signal['signal_type'] in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                    if current_price > ma_100:
                        signal['confidence'] *= 1.2  # Enhance bullish in uptrend
                    else:
                        signal['confidence'] *= 0.8  # Reduce bullish in downtrend
                
                elif signal['signal_type'] in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                    if current_price < ma_100:
                        signal['confidence'] *= 1.2  # Enhance bearish in downtrend
                    else:
                        signal['confidence'] *= 0.8  # Reduce bearish in uptrend
            
            # Volatility adjustment
            if len(data) >= 20:
                returns = data['close'].pct_change().iloc[-20:]
                current_vol = returns.std()
                long_vol = data['close'].pct_change().iloc[-60:].std() if len(data) >= 60 else current_vol
                
                if long_vol > 0:
                    vol_ratio = current_vol / long_vol
                    
                    # Reduce confidence in high volatility environments
                    if vol_ratio > 1.5:
                        signal['confidence'] *= 0.9
                    # Increase confidence in stable environments
                    elif vol_ratio < 0.7:
                        signal['confidence'] *= 1.1
            
            return signal
            
        except Exception as e:
            self.logger.warning(f"Error applying modern enhancements: {e}")
            return signal
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using Turtle rules.
        
        Risk Logic:
        1. Position size based on N and account risk (1% rule)
        2. Stop loss at 2N from entry
        3. Pyramid adding every 0.5N
        4. Maximum 4 units per position
        """
        try:
            current_price = data['close'].iloc[-1]
            current_n = signal.metadata.get('current_n', 0.01)
            
            account_value = self.config.get('account_value', 100000)
            account_risk_pct = self.config.get('account_risk_percentage', 0.01)  # 1% risk per trade
            
            # Calculate unit size based on N
            # Unit Size = 1% of Account / N
            max_risk_amount = account_value * account_risk_pct
            unit_size = max_risk_amount / current_n if current_n > 0 else 1000
            
            # Adjust for current position (if adding to existing position)
            current_units = abs(self.turtle_state.get('current_position', 0))
            remaining_units = self.max_pyramid_units - current_units
            
            if remaining_units <= 0:
                position_size = 0  # No more units allowed
            else:
                position_size = min(unit_size, self.config.get('max_position_size', 5000))
            
            # Stop loss calculation (2N rule)
            stop_distance = current_n * self.stop_loss_n_multiple
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                stop_loss_price = current_price - stop_distance
                # Take profit at 3N (optional)
                take_profit_price = current_price + (current_n * 3.0)
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                stop_loss_price = current_price + stop_distance
                take_profit_price = current_price - (current_n * 3.0)
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop distance (use N)
            trailing_stop_distance = current_n
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=unit_size * self.max_pyramid_units,
                account_risk_percentage=account_risk_pct,
                volatility_adjustment=1.0,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime for strategy adaptation.
        
        Regime Logic:
        1. Use breakout consistency for trend identification
        2. N-based volatility for regime classification
        3. Trend strength analysis
        """
        try:
            current_n = self.turtle_state.get('current_n', 0.0)
            
            if len(data) < 60:
                return MarketRegime.UNKNOWN
            
            # Calculate trend strength using breakout levels
            breakout_levels = self._calculate_breakout_levels(data)
            current_price = data['close'].iloc[-1]
            
            # Analyze trend consistency
            ma_20 = data['close'].rolling(20).mean().iloc[-1]
            ma_55 = data['close'].rolling(55).mean().iloc[-1]
            
            # Volatility regime based on N
            historical_n = []
            for i in range(min(20, len(data) - self.n_period)):
                n_val = self._calculate_n(data.iloc[:-i] if i > 0 else data)
                if n_val is not None:
                    historical_n.append(n_val)
            
            if historical_n:
                avg_n = np.mean(historical_n)
                vol_ratio = current_n / avg_n if avg_n > 0 else 1.0
            else:
                vol_ratio = 1.0
            
            # Determine regime
            if current_price > ma_55 and ma_20 > ma_55:
                if vol_ratio > 1.5:
                    return MarketRegime.TRENDING_UP  # Strong uptrend with high vol
                else:
                    return MarketRegime.TRENDING_UP
            elif current_price < ma_55 and ma_20 < ma_55:
                if vol_ratio > 1.5:
                    return MarketRegime.TRENDING_DOWN  # Strong downtrend with high vol
                else:
                    return MarketRegime.TRENDING_DOWN
            elif vol_ratio > 2.0:
                return MarketRegime.HIGH_VOLATILITY
            elif vol_ratio < 0.5:
                return MarketRegime.LOW_VOLATILITY
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on Turtle rules.
        
        Execution Logic:
        1. Breakout entries get immediate execution
        2. Pyramid adds get patient execution
        3. Exits get urgent execution
        """
        try:
            # Determine action based on signal
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                action = ExecutionAction.ENTER_LONG
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                action = ExecutionAction.ENTER_SHORT
            else:
                return None
            
            # Determine execution parameters based on signal source
            signal_source = signal.metadata.get('source', 'unknown')
            
            if 'exit' in signal_source:
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif 'pyramid' in signal_source:
                algorithm = ExecutionAlgorithm.LIMIT
                urgency = ExecutionUrgency.LOW
            elif signal.signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH]:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            else:
                algorithm = ExecutionAlgorithm.TWAP
                urgency = ExecutionUrgency.MEDIUM
            
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
                    'strategy': 'Turtle_Trading',
                    'signal_confidence': signal.confidence,
                    'signal_source': signal_source,
                    'current_n': signal.metadata.get('current_n'),
                    'turtle_state': signal.metadata.get('turtle_state'),
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
        1. Turtle-specific performance metrics
        2. System 1 vs System 2 performance
        3. Pyramid effectiveness
        4. N-based risk metrics
        """
        try:
            if execution_result.get('status') == 'filled':
                pnl = execution_result.get('pnl', 0.0)
                
                # Update turtle state based on execution
                action = execution_result.get('action')
                quantity = execution_result.get('quantity', 0)
                price = execution_result.get('fill_price', 0)
                
                if action in ['ENTER_LONG', 'ADD_LONG']:
                    self.turtle_state['current_position'] += 1
                    self.turtle_state['entry_prices'].append(price)
                    self.turtle_state['last_entry_price'] = price
                    self.turtle_state['trend_direction'] = 'bullish'
                elif action in ['ENTER_SHORT', 'ADD_SHORT']:
                    self.turtle_state['current_position'] -= 1
                    self.turtle_state['entry_prices'].append(price)
                    self.turtle_state['last_entry_price'] = price
                    self.turtle_state['trend_direction'] = 'bearish'
                elif action in ['EXIT_LONG', 'EXIT_SHORT']:
                    self.turtle_state['current_position'] = 0
                    self.turtle_state['entry_prices'] = []
                    self.turtle_state['last_entry_price'] = None
                    self.turtle_state['trend_direction'] = 'neutral'
                
                # Update performance metrics
                self.performance_metrics.total_trades += 1
                self.performance_metrics.total_return += pnl
                
                if pnl > 0:
                    self.performance_metrics.winning_trades += 1
                    self.performance_metrics.average_win = (
                        (self.performance_metrics.average_win * (self.performance_metrics.winning_trades - 1) + pnl) /
                        self.performance_metrics.winning_trades
                    )
                    self.performance_metrics.largest_win = max(self.performance_metrics.largest_win, pnl)
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
                    f"Turtle Trading Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Current Position: {self.turtle_state['current_position']} units"
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
            account_risk_percentage=0.01,
            volatility_adjustment=1.0,
            portfolio_correlation_adjustment=1.0
        )