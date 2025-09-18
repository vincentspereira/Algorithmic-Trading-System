"""Supertrend Strategy - Institutional Grade Implementation

This strategy implements the Supertrend indicator with institutional-grade
enhancements and modern risk management following the 5-Pillar Architecture.

Core Logic:
- Basic Upper Band = (High + Low) / 2 + (Multiplier × ATR)
- Basic Lower Band = (High + Low) / 2 - (Multiplier × ATR)
- Final Upper Band = Basic Upper Band < Previous Final Upper Band OR Previous Close > Previous Final Upper Band ? Basic Upper Band : Previous Final Upper Band
- Final Lower Band = Basic Lower Band > Previous Final Lower Band OR Previous Close < Previous Final Lower Band ? Basic Lower Band : Previous Final Lower Band
- Supertrend = Close <= Final Lower Band ? Final Lower Band : Final Upper Band
- Trend = Close <= Final Lower Band ? 1 (Up) : -1 (Down)

Enhancements:
- Volume-weighted ATR calculations
- Multi-timeframe confirmation
- Dynamic multiplier adjustment
- Trend strength analysis
- False breakout filtering

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
from ..indicators.traditional.trend_indicators import TrendIndicators
from ..risk_management_utils import RiskManagementUtils
from ..execution_intent_utils import ExecutionIntentUtils


class SupertrendStrategy(BaseInstitutionalStrategy):
    """
    Supertrend Strategy implementing the 5-Pillar Architecture.
    
    This strategy uses the Supertrend indicator with volume-weighted enhancements
    and sophisticated trend analysis for institutional-grade performance.
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
        
        # Supertrend parameters from config
        self.atr_period = self.config.get('atr_period', 14)
        self.multiplier = self.config.get('multiplier', 3.0)
        self.dynamic_multiplier = self.config.get('dynamic_multiplier', True)
        
        # Enhanced parameters
        self.volume_weighted_atr = self.config.get('volume_weighted_atr', True)
        self.multi_timeframe = self.config.get('multi_timeframe', True)
        self.false_breakout_filter = self.config.get('false_breakout_filter', True)
        self.trend_strength_analysis = self.config.get('trend_strength_analysis', True)
        
        # Signal strength thresholds
        self.strong_signal_threshold = self.config.get('strong_signal_threshold', 0.7)
        self.weak_signal_threshold = self.config.get('weak_signal_threshold', 0.3)
        
        # Supertrend state tracking
        self.supertrend_state = {
            'current_trend': 'neutral',
            'trend_changes': 0,
            'trend_duration': 0,
            'last_trend_change': None,
            'supertrend_value': 0.0,
            'trend_strength': 0.0,
            'false_signals': 0
        }
        
        self.logger.info(f"Supertrend Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Supertrend analysis.
        
        Signal Logic:
        1. Calculate Supertrend indicator with volume-weighted ATR
        2. Detect trend changes and validate with filters
        3. Analyze trend strength and momentum
        4. Apply multi-timeframe confirmation
        5. Filter false breakouts
        """
        try:
            required_periods = max(self.atr_period * 3, 50)
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for Supertrend calculation")
            
            # Calculate Supertrend components
            supertrend_data = self._calculate_supertrend(data)
            if supertrend_data is None:
                return self._create_neutral_signal("Supertrend calculation failed")
            
            current_price = data['close'].iloc[-1]
            current_supertrend = supertrend_data['supertrend'].iloc[-1]
            current_trend = supertrend_data['trend'].iloc[-1]
            
            # Detect trend changes
            trend_change_signal = self._detect_trend_change(supertrend_data)
            
            # Analyze trend strength
            trend_strength = self._analyze_trend_strength(data, supertrend_data) if self.trend_strength_analysis else 0.5
            
            # Check for false breakout
            is_false_breakout = self._check_false_breakout(data, supertrend_data) if self.false_breakout_filter else False
            
            # Multi-timeframe confirmation
            mtf_confirmation = self._get_multi_timeframe_confirmation(data) if self.multi_timeframe else 1.0
            
            # Volume confirmation
            volume_confirmation = self._get_volume_confirmation(data)
            
            # Determine primary signal
            primary_signal = self._determine_primary_supertrend_signal(
                trend_change_signal, trend_strength, current_trend, current_price, current_supertrend
            )
            
            # Apply filters and confirmations
            if is_false_breakout:
                primary_signal['confidence'] *= 0.3  # Heavily penalize false breakouts
                self.supertrend_state['false_signals'] += 1
            
            primary_signal['confidence'] *= mtf_confirmation * volume_confirmation
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update Supertrend state
            self._update_supertrend_state(supertrend_data, trend_change_signal, trend_strength)
            
            # Create metadata
            metadata = {
                'supertrend_data': {
                    'supertrend_value': current_supertrend,
                    'trend': current_trend,
                    'atr': supertrend_data['atr'].iloc[-1],
                    'upper_band': supertrend_data['upper_band'].iloc[-1],
                    'lower_band': supertrend_data['lower_band'].iloc[-1]
                },
                'trend_change_signal': trend_change_signal,
                'trend_strength': trend_strength,
                'is_false_breakout': is_false_breakout,
                'mtf_confirmation': mtf_confirmation,
                'volume_confirmation': volume_confirmation,
                'supertrend_state': self.supertrend_state.copy(),
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
            self.logger.error(f"Error generating Supertrend signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_supertrend(self, data: pd.DataFrame) -> Optional[Dict[str, pd.Series]]:
        """
        Calculate Supertrend indicator with volume-weighted enhancements.
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            volume = data['volume']
            
            # Calculate ATR (volume-weighted if enabled)
            if self.volume_weighted_atr:
                atr = self.volume_indicators.atr(high, low, close, volume, period=self.atr_period)
            else:
                atr = self.volatility_indicators.atr(high, low, close, period=self.atr_period)
            
            # Calculate typical price (HL2)
            typical_price = (high + low) / 2
            
            # Dynamic multiplier adjustment based on volatility
            if self.dynamic_multiplier:
                volatility_ratio = atr / close
                # Adjust multiplier: higher volatility = lower multiplier (tighter bands)
                dynamic_mult = self.multiplier * (1 - volatility_ratio.rolling(20).mean() * 2)
                dynamic_mult = dynamic_mult.clip(lower=self.multiplier * 0.5, upper=self.multiplier * 1.5)
            else:
                dynamic_mult = pd.Series([self.multiplier] * len(data), index=data.index)
            
            # Calculate basic bands
            basic_upper_band = typical_price + (dynamic_mult * atr)
            basic_lower_band = typical_price - (dynamic_mult * atr)
            
            # Initialize final bands
            final_upper_band = pd.Series(index=data.index, dtype=float)
            final_lower_band = pd.Series(index=data.index, dtype=float)
            supertrend = pd.Series(index=data.index, dtype=float)
            trend = pd.Series(index=data.index, dtype=int)
            
            # Calculate final bands and supertrend
            for i in range(len(data)):
                if i == 0:
                    final_upper_band.iloc[i] = basic_upper_band.iloc[i]
                    final_lower_band.iloc[i] = basic_lower_band.iloc[i]
                else:
                    # Final Upper Band
                    if (basic_upper_band.iloc[i] < final_upper_band.iloc[i-1] or 
                        close.iloc[i-1] > final_upper_band.iloc[i-1]):
                        final_upper_band.iloc[i] = basic_upper_band.iloc[i]
                    else:
                        final_upper_band.iloc[i] = final_upper_band.iloc[i-1]
                    
                    # Final Lower Band
                    if (basic_lower_band.iloc[i] > final_lower_band.iloc[i-1] or 
                        close.iloc[i-1] < final_lower_band.iloc[i-1]):
                        final_lower_band.iloc[i] = basic_lower_band.iloc[i]
                    else:
                        final_lower_band.iloc[i] = final_lower_band.iloc[i-1]
                
                # Determine Supertrend and Trend
                if i == 0:
                    if close.iloc[i] <= final_lower_band.iloc[i]:
                        supertrend.iloc[i] = final_lower_band.iloc[i]
                        trend.iloc[i] = 1  # Uptrend
                    else:
                        supertrend.iloc[i] = final_upper_band.iloc[i]
                        trend.iloc[i] = -1  # Downtrend
                else:
                    if (supertrend.iloc[i-1] == final_upper_band.iloc[i-1] and 
                        close.iloc[i] <= final_lower_band.iloc[i]):
                        supertrend.iloc[i] = final_lower_band.iloc[i]
                        trend.iloc[i] = 1  # Uptrend
                    elif (supertrend.iloc[i-1] == final_lower_band.iloc[i-1] and 
                          close.iloc[i] >= final_upper_band.iloc[i]):
                        supertrend.iloc[i] = final_upper_band.iloc[i]
                        trend.iloc[i] = -1  # Downtrend
                    else:
                        supertrend.iloc[i] = supertrend.iloc[i-1]
                        trend.iloc[i] = trend.iloc[i-1]
            
            return {
                'supertrend': supertrend,
                'trend': trend,
                'upper_band': final_upper_band,
                'lower_band': final_lower_band,
                'atr': atr,
                'basic_upper': basic_upper_band,
                'basic_lower': basic_lower_band,
                'multiplier': dynamic_mult
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating Supertrend: {e}")
            return None
    
    def _detect_trend_change(self, supertrend_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Detect trend changes in Supertrend indicator.
        """
        try:
            trend = supertrend_data['trend']
            
            if len(trend) < 3:
                return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
            current_trend = trend.iloc[-1]
            previous_trend = trend.iloc[-2]
            
            # Check for trend change
            if current_trend != previous_trend:
                # Calculate trend change strength based on price distance from Supertrend
                supertrend_value = supertrend_data['supertrend'].iloc[-1]
                current_price = supertrend_data['supertrend'].index[-1]  # This needs to be fixed
                
                # For now, use a simple strength calculation
                strength = 0.8  # High strength for trend changes
                confidence = 0.7
                
                if current_trend == 1:  # Changed to uptrend
                    return {
                        'type': 'bullish_change',
                        'strength': strength,
                        'confidence': confidence,
                        'previous_trend': previous_trend,
                        'current_trend': current_trend
                    }
                else:  # Changed to downtrend
                    return {
                        'type': 'bearish_change',
                        'strength': strength,
                        'confidence': confidence,
                        'previous_trend': previous_trend,
                        'current_trend': current_trend
                    }
            else:
                # No trend change - check for trend continuation strength
                trend_duration = self._calculate_trend_duration(trend)
                
                if trend_duration > 5:  # Strong trend continuation
                    continuation_strength = min(trend_duration / 20, 0.6)  # Max 0.6 strength
                    
                    if current_trend == 1:
                        return {
                            'type': 'bullish_continuation',
                            'strength': continuation_strength,
                            'confidence': 0.5,
                            'trend_duration': trend_duration
                        }
                    else:
                        return {
                            'type': 'bearish_continuation',
                            'strength': continuation_strength,
                            'confidence': 0.5,
                            'trend_duration': trend_duration
                        }
                else:
                    return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
        except Exception as e:
            self.logger.warning(f"Error detecting trend change: {e}")
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
    
    def _calculate_trend_duration(self, trend: pd.Series) -> int:
        """
        Calculate the duration of the current trend.
        """
        try:
            if len(trend) < 2:
                return 0
            
            current_trend = trend.iloc[-1]
            duration = 1
            
            for i in range(len(trend) - 2, -1, -1):
                if trend.iloc[i] == current_trend:
                    duration += 1
                else:
                    break
            
            return duration
            
        except Exception as e:
            self.logger.warning(f"Error calculating trend duration: {e}")
            return 0
    
    def _analyze_trend_strength(self, data: pd.DataFrame, 
                               supertrend_data: Dict[str, pd.Series]) -> float:
        """
        Analyze the strength of the current trend.
        """
        try:
            close = data['close']
            supertrend = supertrend_data['supertrend']
            trend = supertrend_data['trend']
            
            if len(close) < 20:
                return 0.5
            
            current_trend = trend.iloc[-1]
            
            # Calculate price distance from Supertrend
            price_distance = abs(close.iloc[-1] - supertrend.iloc[-1]) / close.iloc[-1]
            
            # Calculate trend consistency over last 10 periods
            recent_trend = trend.iloc[-10:]
            trend_consistency = (recent_trend == current_trend).sum() / len(recent_trend)
            
            # Calculate momentum using price change
            price_momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] if len(close) >= 5 else 0
            
            # Normalize momentum based on trend direction
            if current_trend == 1:  # Uptrend
                momentum_strength = max(0, price_momentum) * 10  # Positive momentum is good
            else:  # Downtrend
                momentum_strength = max(0, -price_momentum) * 10  # Negative momentum is good
            
            # Combine factors
            strength = (
                price_distance * 2 +  # Distance from Supertrend (max ~0.2)
                trend_consistency * 0.5 +  # Trend consistency (max 0.5)
                min(momentum_strength, 0.3)  # Momentum (max 0.3)
            )
            
            return min(strength, 1.0)
            
        except Exception as e:
            self.logger.warning(f"Error analyzing trend strength: {e}")
            return 0.5
    
    def _check_false_breakout(self, data: pd.DataFrame, 
                             supertrend_data: Dict[str, pd.Series]) -> bool:
        """
        Check if the current signal might be a false breakout.
        """
        try:
            if len(data) < 10:
                return False
            
            trend = supertrend_data['trend']
            close = data['close']
            volume = data['volume']
            
            # Check if trend just changed
            if len(trend) >= 2 and trend.iloc[-1] != trend.iloc[-2]:
                # Check volume confirmation
                current_volume = volume.iloc[-1]
                avg_volume = volume.rolling(10).mean().iloc[-1]
                
                if current_volume < avg_volume * 0.8:  # Low volume breakout
                    return True
                
                # Check price action - if price immediately reverses
                if len(close) >= 3:
                    price_change_1 = close.iloc[-1] - close.iloc[-2]
                    price_change_2 = close.iloc[-2] - close.iloc[-3]
                    
                    # If price changes direction immediately after trend change
                    if (price_change_1 > 0 and price_change_2 < 0) or (price_change_1 < 0 and price_change_2 > 0):
                        return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking false breakout: {e}")
            return False
    
    def _get_multi_timeframe_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get multi-timeframe confirmation using longer-term trend analysis.
        """
        try:
            if len(data) < 100:
                return 1.0
            
            # Use longer-term moving averages as proxy for higher timeframe
            ma_20 = data['close'].rolling(20).mean().iloc[-1]
            ma_50 = data['close'].rolling(50).mean().iloc[-1]
            ma_100 = data['close'].rolling(100).mean().iloc[-1]
            current_price = data['close'].iloc[-1]
            
            # Check alignment
            if current_price > ma_20 > ma_50 > ma_100:
                return 1.3  # Strong bullish alignment
            elif current_price < ma_20 < ma_50 < ma_100:
                return 1.3  # Strong bearish alignment
            elif (current_price > ma_20 > ma_50) or (current_price > ma_20 > ma_100):
                return 1.1  # Partial bullish alignment
            elif (current_price < ma_20 < ma_50) or (current_price < ma_20 < ma_100):
                return 1.1  # Partial bearish alignment
            else:
                return 0.9  # No clear alignment
                
        except Exception as e:
            self.logger.warning(f"Error calculating multi-timeframe confirmation: {e}")
            return 1.0
    
    def _get_volume_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get volume confirmation for Supertrend signals.
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
                return min(1.0 + (volume_ratio - 1.5) * 0.1, 1.2)
            # Weak volume
            elif volume_ratio < 0.7:
                return 0.8
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _determine_primary_supertrend_signal(self, trend_change_signal: Dict[str, Any], 
                                           trend_strength: float, current_trend: int,
                                           current_price: float, supertrend_value: float) -> Dict[str, Any]:
        """
        Determine the primary Supertrend signal.
        """
        try:
            # Priority: Trend changes > Strong continuations > Weak signals
            
            if trend_change_signal['type'] in ['bullish_change', 'bearish_change']:
                # Strong trend change signals
                signal_strength = trend_change_signal['strength'] * trend_strength
                
                return {
                    'signal_type': SignalType.STRONG_BULLISH if trend_change_signal['type'] == 'bullish_change' else SignalType.STRONG_BEARISH,
                    'raw_value': signal_strength if trend_change_signal['type'] == 'bullish_change' else -signal_strength,
                    'confidence': trend_change_signal['confidence'],
                    'strength': signal_strength,
                    'source': 'trend_change'
                }
            
            elif trend_change_signal['type'] in ['bullish_continuation', 'bearish_continuation']:
                # Trend continuation signals
                if trend_strength > self.strong_signal_threshold:
                    signal_strength = trend_change_signal['strength'] * trend_strength
                    
                    return {
                        'signal_type': SignalType.BULLISH if trend_change_signal['type'] == 'bullish_continuation' else SignalType.BEARISH,
                        'raw_value': signal_strength if trend_change_signal['type'] == 'bullish_continuation' else -signal_strength,
                        'confidence': trend_change_signal['confidence'],
                        'strength': signal_strength,
                        'source': 'trend_continuation'
                    }
            
            # Position-based signals (weaker)
            price_distance = abs(current_price - supertrend_value) / current_price if current_price > 0 else 0
            
            if current_trend == 1 and current_price > supertrend_value:
                # Price above Supertrend in uptrend
                return {
                    'signal_type': SignalType.BULLISH,
                    'raw_value': min(price_distance * 10, 0.5),
                    'confidence': 0.4,
                    'strength': min(price_distance * 10, 0.5),
                    'source': 'position_based'
                }
            elif current_trend == -1 and current_price < supertrend_value:
                # Price below Supertrend in downtrend
                return {
                    'signal_type': SignalType.BEARISH,
                    'raw_value': -min(price_distance * 10, 0.5),
                    'confidence': 0.4,
                    'strength': min(price_distance * 10, 0.5),
                    'source': 'position_based'
                }
            
            # No clear signal
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'none'
            }
            
        except Exception as e:
            self.logger.warning(f"Error determining primary Supertrend signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_supertrend_state(self, supertrend_data: Dict[str, pd.Series], 
                                trend_change_signal: Dict[str, Any], trend_strength: float) -> None:
        """
        Update internal Supertrend state tracking.
        """
        try:
            current_trend = supertrend_data['trend'].iloc[-1]
            current_supertrend = supertrend_data['supertrend'].iloc[-1]
            
            # Update trend
            if current_trend == 1:
                self.supertrend_state['current_trend'] = 'bullish'
            elif current_trend == -1:
                self.supertrend_state['current_trend'] = 'bearish'
            else:
                self.supertrend_state['current_trend'] = 'neutral'
            
            # Update trend changes
            if trend_change_signal['type'] in ['bullish_change', 'bearish_change']:
                self.supertrend_state['trend_changes'] += 1
                self.supertrend_state['last_trend_change'] = datetime.now()
                self.supertrend_state['trend_duration'] = 1
            else:
                self.supertrend_state['trend_duration'] += 1
            
            # Update values
            self.supertrend_state['supertrend_value'] = current_supertrend
            self.supertrend_state['trend_strength'] = trend_strength
            
        except Exception as e:
            self.logger.warning(f"Error updating Supertrend state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using Supertrend levels.
        
        Risk Logic:
        1. Use Supertrend value as dynamic stop loss
        2. Position sizing based on ATR and trend strength
        3. Take profit at multiple ATR levels
        4. Trailing stop using Supertrend updates
        """
        try:
            current_price = data['close'].iloc[-1]
            supertrend_data = signal.metadata.get('supertrend_data', {})
            trend_strength = signal.metadata.get('trend_strength', 0.5)
            
            if not supertrend_data:
                return self._create_default_risk_parameters()
            
            supertrend_value = supertrend_data['supertrend_value']
            atr_value = supertrend_data['atr']
            current_trend = supertrend_data['trend']
            
            # Base position size
            base_position = self.config.get('base_position_size', 1000)
            
            # Adjust position size based on trend strength and ATR
            strength_multiplier = 0.5 + (trend_strength * 0.5)  # 0.5x to 1.0x
            volatility_adjustment = min(2.0, max(0.5, 1.0 / (atr_value / current_price * 100)))  # Inverse volatility
            
            position_size = base_position * strength_multiplier * volatility_adjustment
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss and take profit calculation
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions, use Supertrend as stop loss
                stop_loss_price = supertrend_value
                # Take profit at 2x ATR above entry
                take_profit_price = current_price + (atr_value * 2)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions, use Supertrend as stop loss
                stop_loss_price = supertrend_value
                # Take profit at 2x ATR below entry
                take_profit_price = current_price - (atr_value * 2)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using ATR
            trailing_stop_distance = atr_value * 1.5
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=self.config.get('max_position_size', 5000),
                account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
                volatility_adjustment=volatility_adjustment,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime using Supertrend analysis.
        
        Regime Logic:
        1. Trend direction and strength
        2. Trend duration and consistency
        3. Volatility levels (ATR)
        4. Trend change frequency
        """
        try:
            if len(data) < 50:
                return MarketRegime.UNKNOWN
            
            supertrend_data = self._calculate_supertrend(data)
            if not supertrend_data:
                return MarketRegime.UNKNOWN
            
            current_trend = supertrend_data['trend'].iloc[-1]
            atr = supertrend_data['atr'].iloc[-1]
            current_price = data['close'].iloc[-1]
            
            # Calculate trend strength and duration
            trend_strength = self._analyze_trend_strength(data, supertrend_data)
            trend_duration = self._calculate_trend_duration(supertrend_data['trend'])
            
            # Calculate volatility level
            volatility_ratio = atr / current_price if current_price > 0 else 0
            
            # Count trend changes in recent period
            recent_trends = supertrend_data['trend'].iloc[-20:] if len(supertrend_data['trend']) >= 20 else supertrend_data['trend']
            trend_changes = sum(1 for i in range(1, len(recent_trends)) if recent_trends.iloc[i] != recent_trends.iloc[i-1])
            
            # Determine regime
            if trend_strength > 0.7 and trend_duration > 10:
                if current_trend == 1:
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            elif volatility_ratio > 0.03:  # High volatility (3%+ ATR)
                return MarketRegime.HIGH_VOLATILITY
            elif volatility_ratio < 0.01:  # Low volatility (1%- ATR)
                return MarketRegime.LOW_VOLATILITY
            elif trend_changes > 5:  # Frequent trend changes
                return MarketRegime.RANGING
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on Supertrend signals.
        
        Execution Logic:
        1. Trend change signals get immediate execution
        2. Strong continuation signals get VWAP execution
        3. Weak signals get patient limit orders
        """
        try:
            if signal.signal_type == SignalType.NEUTRAL:
                return None
            
            # Determine action
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                action = ExecutionAction.ENTER_LONG
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                action = ExecutionAction.ENTER_SHORT
            else:
                return None
            
            # Determine execution parameters based on signal source
            signal_source = signal.metadata.get('source', 'unknown')
            
            if signal_source == 'trend_change':
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif signal_source == 'trend_continuation' and signal.strength > 0.6:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            elif signal_source == 'trend_continuation':
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
                    'strategy': 'Supertrend',
                    'signal_confidence': signal.confidence,
                    'signal_source': signal_source,
                    'supertrend_state': signal.metadata.get('supertrend_state'),
                    'supertrend_data': signal.metadata.get('supertrend_data'),
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
        1. Supertrend-specific performance metrics
        2. Trend change vs continuation performance
        3. False signal tracking
        """
        try:
            if execution_result.get('status') == 'filled':
                pnl = execution_result.get('pnl', 0.0)
                signal_source = execution_result.get('metadata', {}).get('signal_source', 'unknown')
                
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
                    f"Supertrend Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Signal Source: {signal_source}, "
                    f"Trend: {self.supertrend_state['current_trend']}, "
                    f"Trend Changes: {self.supertrend_state['trend_changes']}, "
                    f"False Signals: {self.supertrend_state['false_signals']}"
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