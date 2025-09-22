"""ATR Breakout Strategy - Institutional Grade Implementation

This strategy implements Average True Range (ATR) based breakout system with institutional-grade
enhancements and modern risk management following the 5-Pillar Architecture.

Core Logic:
- ATR measures true volatility of price movements
- Breakout signals when price moves beyond ATR-based thresholds
- Dynamic position sizing based on volatility
- Adaptive ATR periods based on market conditions

Signals:
- Bullish: Price breaks above previous close + (ATR * multiplier)
- Bearish: Price breaks below previous close - (ATR * multiplier)
- Neutral: Price within ATR bands or weak breakouts

Enhancements:
- Volume-weighted ATR calculations
- Multi-timeframe ATR analysis
- Volatility regime detection
- False breakout filtering
- Dynamic ATR multipliers

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

from ..core.base_institutional_strategy import (
    BaseInstitutionalStrategy, IndicatorSignal, RiskParameters, ExecutionIntent,
    SignalType, MarketRegime, ExecutionAction, ExecutionAlgorithm, ExecutionUrgency, TimeInForce
)
from ..indicators.traditional.volatility_indicators import VolatilityIndicators
from ..indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ..indicators.traditional.momentum_indicators import MomentumIndicators
from ..utils.risk_management_utils import RiskManagementUtils
from ..utils.execution_intent_utils import ExecutionIntentUtils


class ATRBreakoutStrategy(BaseInstitutionalStrategy):
    """
    ATR Breakout Strategy implementing the 5-Pillar Architecture.
    
    This strategy trades volatility breakouts using Average True Range with institutional-grade
    risk management and adaptive parameters.
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
        
        # ATR parameters from config
        self.atr_period = self.config.get('atr_period', 14)  # ATR calculation period
        self.atr_multiplier = self.config.get('atr_multiplier', 2.0)  # Breakout threshold multiplier
        self.fast_atr_period = self.config.get('fast_atr_period', 7)  # Fast ATR for confirmation
        self.slow_atr_period = self.config.get('slow_atr_period', 21)  # Slow ATR for trend
        
        # Enhanced parameters
        self.volume_weighted_atr = self.config.get('volume_weighted_atr', True)
        self.adaptive_multiplier = self.config.get('adaptive_multiplier', True)
        self.multi_timeframe_analysis = self.config.get('multi_timeframe_analysis', True)
        self.volatility_regime_detection = self.config.get('volatility_regime_detection', True)
        
        # Breakout parameters
        self.min_breakout_strength = self.config.get('min_breakout_strength', 0.5)
        self.breakout_volume_threshold = self.config.get('breakout_volume_threshold', 1.2)
        self.confirmation_periods = self.config.get('confirmation_periods', 2)
        self.max_days_in_position = self.config.get('max_days_in_position', 20)
        
        # Volatility regime parameters
        self.low_vol_threshold = self.config.get('low_vol_threshold', 0.3)  # 30th percentile
        self.high_vol_threshold = self.config.get('high_vol_threshold', 0.7)  # 70th percentile
        self.regime_lookback = self.config.get('regime_lookback', 50)
        
        # False breakout filter parameters
        self.false_breakout_filter = self.config.get('false_breakout_filter', True)
        self.reversion_threshold = self.config.get('reversion_threshold', 0.5)  # 50% reversion
        self.reversion_periods = self.config.get('reversion_periods', 3)
        
        # Position state tracking
        self.position_state = {
            'in_position': False,
            'position_type': None,  # 'long' or 'short'
            'entry_date': None,
            'entry_price': None,
            'entry_atr': None,
            'days_in_position': 0,
            'highest_favorable': None,
            'lowest_favorable': None,
            'breakout_strength': 0.0,
            'volatility_regime': 'normal',
            'successful_breakouts': 0,
            'failed_breakouts': 0,
            'atr_efficiency': []
        }
        
        self.logger.info(f"ATR Breakout Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using ATR breakout analysis.
        
        Signal Logic:
        1. Calculate multiple ATR periods (fast, normal, slow)
        2. Detect volatility breakouts beyond ATR thresholds
        3. Apply volume confirmation
        4. Filter false breakouts
        5. Multi-timeframe volatility alignment
        """
        try:
            required_periods = max(self.slow_atr_period * 2, 60)
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for ATR calculation")
            
            # Calculate ATR indicators
            atr_data = self._calculate_atr_indicators(data)
            if atr_data is None:
                return self._create_neutral_signal("ATR calculation failed")
            
            # Detect breakout signals
            breakout_analysis = self._analyze_atr_breakout_conditions(data, atr_data)
            
            # Check position management (if in position)
            position_signal = self._check_position_management(data, atr_data)
            
            # Get momentum confirmation
            momentum_confirmation = self._get_momentum_confirmation(data)
            
            # Volume analysis
            volume_confirmation = self._analyze_breakout_volume(data)
            
            # Volatility regime analysis
            volatility_regime = self._detect_volatility_regime(data, atr_data)
            
            # False breakout filter
            is_false_breakout = self._check_false_breakout(data, atr_data) if self.false_breakout_filter else False
            
            # Multi-timeframe confirmation
            mtf_confirmation = self._get_multi_timeframe_confirmation(data, atr_data) if self.multi_timeframe_analysis else 1.0
            
            # Determine primary signal
            primary_signal = self._determine_primary_atr_signal(
                breakout_analysis, position_signal, momentum_confirmation, 
                volume_confirmation, volatility_regime, mtf_confirmation
            )
            
            # Apply filters
            if is_false_breakout:
                primary_signal['confidence'] *= 0.3
                self.position_state['failed_breakouts'] += 1
            
            # Volatility regime adjustments
            if volatility_regime['regime'] == 'low_volatility':
                primary_signal['confidence'] *= 0.8  # Reduce confidence in low vol
            elif volatility_regime['regime'] == 'high_volatility':
                primary_signal['confidence'] *= 1.1  # Increase confidence in high vol
            
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update position state
            self._update_position_state(data, breakout_analysis, primary_signal, volatility_regime)
            
            # Create metadata
            metadata = {
                'atr_data': {
                    'atr': atr_data['atr'].iloc[-1],
                    'fast_atr': atr_data['fast_atr'].iloc[-1],
                    'slow_atr': atr_data['slow_atr'].iloc[-1],
                    'vw_atr': atr_data.get('vw_atr', {}).get('value', atr_data['atr'].iloc[-1]) if isinstance(atr_data.get('vw_atr'), dict) else atr_data.get('vw_atr', atr_data['atr'].iloc[-1]),
                    'upper_band': atr_data['upper_band'].iloc[-1],
                    'lower_band': atr_data['lower_band'].iloc[-1],
                    'adaptive_multiplier': atr_data.get('adaptive_multiplier', self.atr_multiplier)
                },
                'breakout_analysis': breakout_analysis,
                'position_signal': position_signal,
                'momentum_confirmation': momentum_confirmation,
                'volume_confirmation': volume_confirmation,
                'volatility_regime': volatility_regime,
                'mtf_confirmation': mtf_confirmation,
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
            self.logger.error(f"Error generating ATR Breakout signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_atr_indicators(self, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Calculate ATR indicators with various enhancements.
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            volume = data['volume']
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Standard ATR calculations
            atr = true_range.rolling(self.atr_period).mean()
            fast_atr = true_range.rolling(self.fast_atr_period).mean()
            slow_atr = true_range.rolling(self.slow_atr_period).mean()
            
            # Volume-weighted ATR (if enabled)
            vw_atr = None
            if self.volume_weighted_atr:
                try:
                    vw_atr = self.volume_weighted_indicators.vw_atr(
                        high=high, low=low, close=close, volume=volume, period=self.atr_period
                    )
                except Exception as e:
                    self.logger.warning(f"Volume-weighted ATR calculation failed: {e}")
                    vw_atr = atr  # Fallback to standard ATR
            
            # Adaptive multiplier (if enabled)
            adaptive_multiplier = self.atr_multiplier
            if self.adaptive_multiplier:
                adaptive_multiplier = self._calculate_adaptive_multiplier(data, atr)
            
            # Calculate breakout bands
            upper_band = close.shift(1) + (atr * adaptive_multiplier)
            lower_band = close.shift(1) - (atr * adaptive_multiplier)
            
            # ATR percentile for regime detection
            atr_percentile = atr.rolling(self.regime_lookback).rank(pct=True)
            
            # ATR efficiency (how often ATR bands are touched)
            atr_efficiency = self._calculate_atr_efficiency(data, upper_band, lower_band)
            
            # ATR trend (increasing or decreasing volatility)
            atr_trend = self._calculate_atr_trend(atr)
            
            return {
                'atr': atr,
                'fast_atr': fast_atr,
                'slow_atr': slow_atr,
                'vw_atr': vw_atr,
                'true_range': true_range,
                'upper_band': upper_band,
                'lower_band': lower_band,
                'adaptive_multiplier': adaptive_multiplier,
                'atr_percentile': atr_percentile,
                'atr_efficiency': atr_efficiency,
                'atr_trend': atr_trend
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR indicators: {e}")
            return None
    
    def _calculate_adaptive_multiplier(self, data: pd.DataFrame, atr: pd.Series) -> float:
        """
        Calculate adaptive ATR multiplier based on market conditions.
        """
        try:
            close = data['close']
            
            # Calculate recent volatility
            returns = close.pct_change()
            recent_vol = returns.rolling(20).std().iloc[-1]
            
            # Calculate ATR percentile
            atr_percentile = atr.rolling(50).rank(pct=True).iloc[-1]
            
            # Base multiplier
            base_multiplier = self.atr_multiplier
            
            # Adjust based on volatility regime
            if atr_percentile < 0.3:  # Low volatility
                multiplier = base_multiplier * 0.8  # Reduce threshold
            elif atr_percentile > 0.7:  # High volatility
                multiplier = base_multiplier * 1.2  # Increase threshold
            else:
                multiplier = base_multiplier
            
            # Additional adjustment based on recent price action
            if recent_vol > 0.02:  # High recent volatility
                multiplier *= 1.1
            elif recent_vol < 0.01:  # Low recent volatility
                multiplier *= 0.9
            
            return max(1.0, min(4.0, multiplier))  # Constrain between 1.0 and 4.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating adaptive multiplier: {e}")
            return self.atr_multiplier
    
    def _calculate_atr_efficiency(self, data: pd.DataFrame, upper_band: pd.Series, lower_band: pd.Series) -> pd.Series:
        """
        Calculate ATR efficiency - how often price touches the bands.
        """
        try:
            high = data['high']
            low = data['low']
            
            upper_touches = (high >= upper_band).astype(int)
            lower_touches = (low <= lower_band).astype(int)
            
            # Rolling efficiency over last 30 periods
            efficiency = (upper_touches + lower_touches).rolling(30).mean()
            
            return efficiency
            
        except Exception as e:
            self.logger.warning(f"Error calculating ATR efficiency: {e}")
            return pd.Series([0.1] * len(data), index=data.index)
    
    def _calculate_atr_trend(self, atr: pd.Series) -> pd.Series:
        """
        Calculate ATR trend to detect increasing/decreasing volatility.
        """
        try:
            # ATR slope over last 10 periods
            atr_slope = atr.rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == 10 else 0)
            
            return atr_slope
            
        except Exception as e:
            self.logger.warning(f"Error calculating ATR trend: {e}")
            return pd.Series([0.0] * len(atr), index=atr.index)
    
    def _analyze_atr_breakout_conditions(self, data: pd.DataFrame, atr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze current ATR breakout conditions.
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
            
            upper_band = atr_data['upper_band'].iloc[-1]
            lower_band = atr_data['lower_band'].iloc[-1]
            current_atr = atr_data['atr'].iloc[-1]
            
            # Check for breakouts
            bullish_breakout = current_high > upper_band
            bearish_breakout = current_low < lower_band
            
            if not (bullish_breakout or bearish_breakout):
                return {'breakout_type': None, 'strength': 0.0}
            
            # Calculate breakout strength
            if bullish_breakout:
                breakout_distance = (current_price - upper_band) / current_atr
                breakout_type = 'bullish'
                reference_price = upper_band
            else:
                breakout_distance = (lower_band - current_price) / current_atr
                breakout_type = 'bearish'
                reference_price = lower_band
            
            # Normalize breakout strength (0 to 1)
            breakout_strength = min(breakout_distance, 1.0)
            
            # Check breakout persistence
            persistence_periods = self._check_atr_breakout_persistence(data, atr_data, breakout_type)
            
            # ATR regime analysis
            atr_percentile = atr_data['atr_percentile'].iloc[-1]
            atr_efficiency = atr_data['atr_efficiency'].iloc[-1]
            atr_trend = atr_data['atr_trend'].iloc[-1]
            
            # Multi-ATR confirmation
            fast_atr_confirmation = self._check_fast_atr_confirmation(data, atr_data, breakout_type)
            slow_atr_confirmation = self._check_slow_atr_confirmation(data, atr_data, breakout_type)
            
            # Breakout quality assessment
            breakout_quality = self._assess_atr_breakout_quality(
                data, atr_data, breakout_type, breakout_strength, persistence_periods
            )
            
            return {
                'breakout_type': breakout_type,
                'strength': breakout_strength,
                'distance': breakout_distance,
                'persistence': persistence_periods,
                'reference_price': reference_price,
                'atr_percentile': atr_percentile,
                'atr_efficiency': atr_efficiency,
                'atr_trend': atr_trend,
                'fast_atr_confirmation': fast_atr_confirmation,
                'slow_atr_confirmation': slow_atr_confirmation,
                'breakout_quality': breakout_quality,
                'adaptive_multiplier': atr_data.get('adaptive_multiplier', self.atr_multiplier)
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing ATR breakout conditions: {e}")
            return {'breakout_type': None, 'strength': 0.0}
    
    def _check_atr_breakout_persistence(self, data: pd.DataFrame, atr_data: Dict[str, Any], 
                                       breakout_type: str) -> int:
        """
        Check how many periods the ATR breakout has persisted.
        """
        try:
            close = data['close']
            upper_band = atr_data['upper_band']
            lower_band = atr_data['lower_band']
            
            persistence = 0
            for i in range(len(close) - 1, max(0, len(close) - 10), -1):
                if breakout_type == 'bullish' and close.iloc[i] > upper_band.iloc[i]:
                    persistence += 1
                elif breakout_type == 'bearish' and close.iloc[i] < lower_band.iloc[i]:
                    persistence += 1
                else:
                    break
            
            return persistence
            
        except Exception as e:
            self.logger.warning(f"Error checking ATR breakout persistence: {e}")
            return 0
    
    def _check_fast_atr_confirmation(self, data: pd.DataFrame, atr_data: Dict[str, Any], 
                                    breakout_type: str) -> bool:
        """
        Check if fast ATR confirms the breakout direction.
        """
        try:
            close = data['close']
            current_price = close.iloc[-1]
            previous_close = close.iloc[-2]
            
            fast_atr = atr_data['fast_atr'].iloc[-1]
            
            if breakout_type == 'bullish':
                fast_upper = previous_close + (fast_atr * self.atr_multiplier * 0.8)
                return current_price > fast_upper
            else:
                fast_lower = previous_close - (fast_atr * self.atr_multiplier * 0.8)
                return current_price < fast_lower
                
        except Exception as e:
            self.logger.warning(f"Error checking fast ATR confirmation: {e}")
            return False
    
    def _check_slow_atr_confirmation(self, data: pd.DataFrame, atr_data: Dict[str, Any], 
                                    breakout_type: str) -> bool:
        """
        Check if slow ATR confirms the volatility trend.
        """
        try:
            fast_atr = atr_data['fast_atr'].iloc[-1]
            slow_atr = atr_data['slow_atr'].iloc[-1]
            
            # Fast ATR should be higher than slow ATR for confirmed volatility expansion
            return fast_atr > slow_atr * 1.05
                
        except Exception as e:
            self.logger.warning(f"Error checking slow ATR confirmation: {e}")
            return False
    
    def _assess_atr_breakout_quality(self, data: pd.DataFrame, atr_data: Dict[str, Any], 
                                    breakout_type: str, breakout_strength: float, 
                                    persistence_periods: int) -> float:
        """
        Assess the quality of the ATR breakout based on multiple factors.
        """
        try:
            quality_score = 0.5  # Base quality
            
            # Factor 1: Breakout strength
            if breakout_strength > 0.7:
                quality_score += 0.2
            elif breakout_strength > 0.4:
                quality_score += 0.1
            
            # Factor 2: Persistence
            if persistence_periods >= 3:
                quality_score += 0.2
            elif persistence_periods >= 2:
                quality_score += 0.1
            
            # Factor 3: ATR efficiency
            atr_efficiency = atr_data['atr_efficiency'].iloc[-1]
            if 0.05 <= atr_efficiency <= 0.2:  # Optimal range
                quality_score += 0.15
            
            # Factor 4: ATR trend (expanding volatility is better)
            atr_trend = atr_data['atr_trend'].iloc[-1]
            if atr_trend > 0:  # Increasing volatility
                quality_score += 0.1
            
            # Factor 5: ATR percentile
            atr_percentile = atr_data['atr_percentile'].iloc[-1]
            if 0.3 <= atr_percentile <= 0.8:  # Not extreme
                quality_score += 0.1
            
            # Factor 6: Historical success rate
            if hasattr(self, 'position_state') and self.position_state:
                total_breakouts = (self.position_state.get('successful_breakouts', 0) + 
                                 self.position_state.get('failed_breakouts', 0))
                if total_breakouts > 0:
                    success_rate = self.position_state.get('successful_breakouts', 0) / total_breakouts
                    quality_score += (success_rate - 0.5) * 0.2
            
            return max(0.1, min(1.0, quality_score))
            
        except Exception as e:
            self.logger.warning(f"Error assessing ATR breakout quality: {e}")
            return 0.5
    
    def _check_position_management(self, data: pd.DataFrame, atr_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
            entry_atr = self.position_state.get('entry_atr', atr_data['atr'].iloc[-1])
            days_in_position = self.position_state.get('days_in_position', 0)
            
            current_atr = atr_data['atr'].iloc[-1]
            
            # Check exit conditions
            should_exit = False
            exit_reason = None
            
            # ATR-based stop loss
            stop_multiplier = self.config.get('stop_loss_atr_multiplier', 1.5)
            if position_type == 'long':
                stop_loss_price = entry_price - (entry_atr * stop_multiplier)
                if current_price <= stop_loss_price:
                    should_exit = True
                    exit_reason = 'atr_stop_loss'
            elif position_type == 'short':
                stop_loss_price = entry_price + (entry_atr * stop_multiplier)
                if current_price >= stop_loss_price:
                    should_exit = True
                    exit_reason = 'atr_stop_loss'
            
            # Time-based exit
            if not should_exit and days_in_position >= self.max_days_in_position:
                should_exit = True
                exit_reason = 'time_exit'
            
            # Volatility contraction exit
            if not should_exit:
                volatility_contraction_threshold = self.config.get('volatility_contraction_threshold', 0.7)
                if current_atr < entry_atr * volatility_contraction_threshold:
                    should_exit = True
                    exit_reason = 'volatility_contraction'
            
            # Profit target (ATR-based)
            if not should_exit:
                profit_target_multiplier = self.config.get('profit_target_atr_multiplier', 3.0)
                if position_type == 'long':
                    profit_target = entry_price + (entry_atr * profit_target_multiplier)
                    if current_price >= profit_target:
                        should_exit = True
                        exit_reason = 'profit_target'
                elif position_type == 'short':
                    profit_target = entry_price - (entry_atr * profit_target_multiplier)
                    if current_price <= profit_target:
                        should_exit = True
                        exit_reason = 'profit_target'
            
            if should_exit:
                return {
                    'action': 'exit',
                    'reason': exit_reason,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'entry_atr': entry_atr,
                    'current_atr': current_atr,
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
        Get momentum confirmation for ATR breakout signals.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            close = data['close']
            
            confirmations = []
            
            # Price momentum
            if len(close) >= 5:
                short_momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5]
                if abs(short_momentum) > 0.01:  # Significant momentum
                    confirmations.append(1 if short_momentum > 0 else -1)
                else:
                    confirmations.append(0)
            
            # RSI confirmation (not extreme)
            try:
                rsi = self.momentum_indicators.rsi(close, period=14)
                if len(rsi) > 0:
                    current_rsi = rsi.iloc[-1]
                    if 35 <= current_rsi <= 65:  # Not extreme
                        confirmations.append(1)
                    elif current_rsi > 75 or current_rsi < 25:
                        confirmations.append(-0.5)  # Very extreme
                    else:
                        confirmations.append(0.5)  # Moderately extreme
            except:
                pass
            
            # Moving average alignment
            if len(close) >= 20:
                sma_10 = close.rolling(10).mean().iloc[-1]
                sma_20 = close.rolling(20).mean().iloc[-1]
                current_price = close.iloc[-1]
                
                if current_price > sma_10 > sma_20:
                    confirmations.append(1)  # Bullish alignment
                elif current_price < sma_10 < sma_20:
                    confirmations.append(-1)  # Bearish alignment
                else:
                    confirmations.append(0)  # Mixed
            
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
        Analyze volume confirmation for ATR breakouts.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            volume = data['volume']
            current_volume = volume.iloc[-1]
            
            # Multiple volume averages
            volume_ma_10 = volume.rolling(10).mean().iloc[-1]
            volume_ma_20 = volume.rolling(20).mean().iloc[-1]
            
            # Volume confirmation score
            if current_volume > volume_ma_20 * self.breakout_volume_threshold:
                confirmation = 1.2  # Strong volume
            elif current_volume > volume_ma_10 * 1.1:
                confirmation = 1.1  # Good volume
            elif current_volume > volume_ma_20:
                confirmation = 1.0  # Average volume
            elif current_volume < volume_ma_20 * 0.7:
                confirmation = 0.7  # Weak volume
            else:
                confirmation = 0.9  # Below average volume
            
            return min(confirmation, 1.3)
            
        except Exception as e:
            self.logger.warning(f"Error analyzing breakout volume: {e}")
            return 1.0
    
    def _detect_volatility_regime(self, data: pd.DataFrame, atr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect current volatility regime.
        """
        try:
            atr_percentile = atr_data['atr_percentile'].iloc[-1]
            atr_trend = atr_data['atr_trend'].iloc[-1]
            atr_efficiency = atr_data['atr_efficiency'].iloc[-1]
            
            # Determine regime
            if atr_percentile < self.low_vol_threshold:
                regime = 'low_volatility'
                regime_strength = (self.low_vol_threshold - atr_percentile) / self.low_vol_threshold
            elif atr_percentile > self.high_vol_threshold:
                regime = 'high_volatility'
                regime_strength = (atr_percentile - self.high_vol_threshold) / (1.0 - self.high_vol_threshold)
            else:
                regime = 'normal_volatility'
                regime_strength = 0.5
            
            # Volatility trend
            if atr_trend > 0.0001:  # Increasing volatility
                trend_direction = 'expanding'
            elif atr_trend < -0.0001:  # Decreasing volatility
                trend_direction = 'contracting'
            else:
                trend_direction = 'stable'
            
            return {
                'regime': regime,
                'strength': regime_strength,
                'trend_direction': trend_direction,
                'atr_percentile': atr_percentile,
                'atr_trend': atr_trend,
                'atr_efficiency': atr_efficiency
            }
            
        except Exception as e:
            self.logger.warning(f"Error detecting volatility regime: {e}")
            return {
                'regime': 'normal_volatility',
                'strength': 0.5,
                'trend_direction': 'stable',
                'atr_percentile': 0.5,
                'atr_trend': 0.0,
                'atr_efficiency': 0.1
            }
    
    def _check_false_breakout(self, data: pd.DataFrame, atr_data: Dict[str, Any]) -> bool:
        """
        Check if the current breakout might be a false breakout.
        """
        try:
            if len(data) < 10:
                return False
            
            close = data['close']
            upper_band = atr_data['upper_band']
            lower_band = atr_data['lower_band']
            
            # Check for recent failed breakouts
            failed_breakouts = 0
            for i in range(max(1, len(close) - 10), len(close) - 1):
                if i <= 0:
                    continue
                
                # Check if price broke out but then reverted quickly
                if (close.iloc[i] > upper_band.iloc[i] and 
                    close.iloc[i+1] <= upper_band.iloc[i+1] * (1 - self.reversion_threshold * 0.01)) or \
                   (close.iloc[i] < lower_band.iloc[i] and 
                    close.iloc[i+1] >= lower_band.iloc[i+1] * (1 + self.reversion_threshold * 0.01)):
                    failed_breakouts += 1
            
            if failed_breakouts >= 2:  # Too many recent failures
                return True
            
            # Check current breakout strength
            current_price = close.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_atr = atr_data['atr'].iloc[-1]
            
            if current_price > current_upper:
                breakout_strength = (current_price - current_upper) / current_atr
            elif current_price < current_lower:
                breakout_strength = (current_lower - current_price) / current_atr
            else:
                return False  # No breakout
            
            if breakout_strength < self.min_breakout_strength:  # Too weak breakout
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking false breakout: {e}")
            return False
    
    def _get_multi_timeframe_confirmation(self, data: pd.DataFrame, atr_data: Dict[str, Any]) -> float:
        """
        Get multi-timeframe volatility confirmation.
        """
        try:
            if len(data) < 50:
                return 1.0
            
            # Calculate ATR for different periods
            close = data['close']
            high = data['high']
            low = data['low']
            
            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Different timeframe ATRs
            atr_short = true_range.rolling(7).mean()
            atr_medium = true_range.rolling(14).mean()
            atr_long = true_range.rolling(28).mean()
            
            # Check alignment
            current_short = atr_short.iloc[-1]
            current_medium = atr_medium.iloc[-1]
            current_long = atr_long.iloc[-1]
            
            # Volatility expansion alignment
            if current_short > current_medium > current_long:
                return 1.2  # Strong expansion
            elif current_short > current_medium:
                return 1.1  # Moderate expansion
            elif current_short < current_medium < current_long:
                return 0.8  # Contraction
            else:
                return 1.0  # Mixed
                
        except Exception as e:
            self.logger.warning(f"Error getting multi-timeframe confirmation: {e}")
            return 1.0
    
    def _determine_primary_atr_signal(self, breakout_analysis: Dict[str, Any], 
                                     position_signal: Optional[Dict[str, Any]],
                                     momentum_confirmation: float, volume_confirmation: float,
                                     volatility_regime: Dict[str, Any], mtf_confirmation: float) -> Dict[str, Any]:
        """
        Determine the primary ATR breakout signal.
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
            fast_atr_bonus = 0.1 if breakout_analysis.get('fast_atr_confirmation', False) else 0
            slow_atr_bonus = 0.1 if breakout_analysis.get('slow_atr_confirmation', False) else 0
            
            # Volatility regime bonus
            regime_bonus = 0
            if volatility_regime['regime'] == 'high_volatility' and volatility_regime['trend_direction'] == 'expanding':
                regime_bonus = 0.15
            elif volatility_regime['regime'] == 'normal_volatility':
                regime_bonus = 0.05
            
            signal_strength = (base_strength + persistence_bonus + quality_bonus + 
                             fast_atr_bonus + slow_atr_bonus + regime_bonus) * \
                            momentum_confirmation * volume_confirmation * mtf_confirmation
            
            # Determine confidence
            base_confidence = 0.6
            if breakout_analysis.get('persistence', 0) >= 2:
                base_confidence += 0.1
            if volume_confirmation > 1.15:
                base_confidence += 0.1
            if breakout_analysis.get('fast_atr_confirmation', False):
                base_confidence += 0.05
            if breakout_analysis.get('slow_atr_confirmation', False):
                base_confidence += 0.05
            if volatility_regime['regime'] == 'high_volatility':
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
                'source': 'atr_breakout'
            }
            
        except Exception as e:
            self.logger.warning(f"Error determining primary ATR signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_position_state(self, data: pd.DataFrame, breakout_analysis: Dict[str, Any], 
                              primary_signal: Dict[str, Any], volatility_regime: Dict[str, Any]) -> None:
        """
        Update internal position state tracking.
        """
        try:
            current_price = data['close'].iloc[-1]
            current_atr = breakout_analysis.get('distance', 0.0)  # Use breakout distance as proxy
            
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
            if (primary_signal['source'] == 'atr_breakout' and 
                primary_signal['signal_type'] != SignalType.NEUTRAL and
                not self.position_state.get('in_position', False)):
                
                self.position_state['in_position'] = True
                self.position_state['entry_date'] = datetime.now()
                self.position_state['entry_price'] = current_price
                self.position_state['entry_atr'] = current_atr
                self.position_state['days_in_position'] = 0
                self.position_state['volatility_regime'] = volatility_regime['regime']
                
                if primary_signal['signal_type'] in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                    self.position_state['position_type'] = 'long'
                    self.position_state['highest_favorable'] = current_price
                    self.position_state['lowest_favorable'] = None
                else:
                    self.position_state['position_type'] = 'short'
                    self.position_state['lowest_favorable'] = current_price
                    self.position_state['highest_favorable'] = None
                
                self.position_state['breakout_strength'] = breakout_analysis.get('strength', 0.0)
            
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
                self.position_state['entry_atr'] = None
                self.position_state['days_in_position'] = 0
                self.position_state['highest_favorable'] = None
                self.position_state['lowest_favorable'] = None
                self.position_state['volatility_regime'] = 'normal'
            
        except Exception as e:
            self.logger.warning(f"Error updating position state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using ATR analysis.
        
        Risk Logic:
        1. Position sizing based on ATR and volatility regime
        2. Stop loss using ATR multiples
        3. Take profit at ATR-based targets
        4. Trailing stop using ATR expansion
        """
        try:
            current_price = data['close'].iloc[-1]
            atr_data = signal.metadata.get('atr_data', {})
            breakout_analysis = signal.metadata.get('breakout_analysis', {})
            volatility_regime = signal.metadata.get('volatility_regime', {})
            
            current_atr = atr_data.get('atr', current_price * 0.02)
            
            # Base position size
            base_position = self.config.get('base_position_size', 1000)
            
            # Adjust position size based on volatility and breakout quality
            breakout_strength = breakout_analysis.get('strength', 0.5)
            breakout_quality = breakout_analysis.get('breakout_quality', 0.5)
            
            # Volatility adjustment (higher volatility = smaller positions)
            volatility_multiplier = 1.0
            regime = volatility_regime.get('regime', 'normal_volatility')
            if regime == 'high_volatility':
                volatility_multiplier = 0.7  # Reduce size in high vol
            elif regime == 'low_volatility':
                volatility_multiplier = 1.2  # Increase size in low vol
            
            quality_multiplier = 0.7 + (breakout_quality * 0.6)  # 0.7x to 1.3x
            strength_multiplier = 0.8 + (breakout_strength * 0.4)  # 0.8x to 1.2x
            
            position_size = base_position * volatility_multiplier * quality_multiplier * strength_multiplier
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss and take profit calculation
            stop_loss_multiplier = self.config.get('stop_loss_atr_multiplier', 1.5)
            take_profit_multiplier = self.config.get('profit_target_atr_multiplier', 3.0)
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions
                stop_loss_price = current_price - (current_atr * stop_loss_multiplier)
                take_profit_price = current_price + (current_atr * take_profit_multiplier)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions
                stop_loss_price = current_price + (current_atr * stop_loss_multiplier)
                take_profit_price = current_price - (current_atr * take_profit_multiplier)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using ATR
            trailing_stop_distance = current_atr * self.config.get('trailing_stop_atr_multiplier', 1.0)
            
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
        PILLAR 3: Determine current market regime using ATR analysis.
        
        Regime Logic:
        1. ATR percentile for volatility assessment
        2. ATR trend for volatility direction
        3. Price action relative to volatility bands
        """
        try:
            if len(data) < self.slow_atr_period:
                return MarketRegime.UNKNOWN
            
            atr_data = self._calculate_atr_indicators(data)
            if not atr_data:
                return MarketRegime.UNKNOWN
            
            volatility_regime = self._detect_volatility_regime(data, atr_data)
            
            # Map volatility regime to market regime
            regime = volatility_regime['regime']
            trend_direction = volatility_regime['trend_direction']
            
            if regime == 'low_volatility':
                return MarketRegime.LOW_VOLATILITY
            elif regime == 'high_volatility':
                if trend_direction == 'expanding':
                    return MarketRegime.HIGH_VOLATILITY
                else:
                    return MarketRegime.VOLATILE_SIDEWAYS
            else:
                # Normal volatility - check price trend
                close = data['close']
                sma_20 = close.rolling(20).mean()
                
                if len(sma_20) >= 2:
                    if sma_20.iloc[-1] > sma_20.iloc[-2]:
                        return MarketRegime.TRENDING_UP
                    elif sma_20.iloc[-1] < sma_20.iloc[-2]:
                        return MarketRegime.TRENDING_DOWN
                    else:
                        return MarketRegime.RANGING
                else:
                    return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on ATR breakout signals.
        
        Execution Logic:
        1. Strong breakouts in high volatility get market orders
        2. Normal breakouts get VWAP execution
        3. Weak breakouts get limit orders
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
                        'strategy': 'ATR_Breakout',
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
            volatility_regime = signal.metadata.get('volatility_regime', {})
            breakout_strength = breakout_analysis.get('strength', 0.5)
            breakout_quality = breakout_analysis.get('breakout_quality', 0.5)
            volume_confirmation = signal.metadata.get('volume_confirmation', 1.0)
            
            # Execution algorithm selection
            if (signal.signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH] and
                volatility_regime.get('regime') == 'high_volatility'):
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif breakout_quality > 0.7 and volume_confirmation > 1.15:
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
                    'strategy': 'ATR_Breakout',
                    'signal_confidence': signal.confidence,
                    'breakout_strength': breakout_strength,
                    'breakout_quality': breakout_quality,
                    'volatility_regime': volatility_regime,
                    'atr_data': signal.metadata.get('atr_data'),
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
        1. ATR-specific performance metrics
        2. Volatility regime performance
        3. Breakout success rates by regime
        """
        try:
            if execution_result.get('status') == 'filled':
                pnl = execution_result.get('pnl', 0.0)
                trade_metadata = execution_result.get('metadata', {})
                
                # Update basic metrics
                self.performance_metrics['total_trades'] += 1
                self.performance_metrics['total_pnl'] += pnl
                
                if pnl > 0:
                    self.performance_metrics['winning_trades'] += 1
                    self.performance_metrics['total_wins_pnl'] += pnl
                else:
                    self.performance_metrics['losing_trades'] += 1
                    self.performance_metrics['total_losses_pnl'] += abs(pnl)
                
                # ATR-specific metrics
                volatility_regime = trade_metadata.get('volatility_regime', {})
                regime = volatility_regime.get('regime', 'normal_volatility')
                
                regime_key = f'{regime}_trades'
                if regime_key not in self.performance_metrics:
                    self.performance_metrics[regime_key] = 0
                    self.performance_metrics[f'{regime}_pnl'] = 0.0
                
                self.performance_metrics[regime_key] += 1
                self.performance_metrics[f'{regime}_pnl'] += pnl
                
                # Breakout quality metrics
                breakout_quality = trade_metadata.get('breakout_quality', 0.5)
                if breakout_quality > 0.7:
                    self.performance_metrics['high_quality_breakouts'] = \
                        self.performance_metrics.get('high_quality_breakouts', 0) + 1
                    self.performance_metrics['high_quality_pnl'] = \
                        self.performance_metrics.get('high_quality_pnl', 0.0) + pnl
                
                # Update win rate
                if self.performance_metrics['total_trades'] > 0:
                    self.performance_metrics['win_rate'] = \
                        self.performance_metrics['winning_trades'] / self.performance_metrics['total_trades']
                
                # Update average metrics
                if self.performance_metrics['winning_trades'] > 0:
                    self.performance_metrics['avg_win'] = \
                        self.performance_metrics['total_wins_pnl'] / self.performance_metrics['winning_trades']
                
                if self.performance_metrics['losing_trades'] > 0:
                    self.performance_metrics['avg_loss'] = \
                        self.performance_metrics['total_losses_pnl'] / self.performance_metrics['losing_trades']
                
                # Profit factor
                if self.performance_metrics['total_losses_pnl'] > 0:
                    self.performance_metrics['profit_factor'] = \
                        self.performance_metrics['total_wins_pnl'] / self.performance_metrics['total_losses_pnl']
                
                self.logger.info(f"Updated ATR Breakout performance: {self.performance_metrics}")
                
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _create_neutral_signal(self, reason: str) -> IndicatorSignal:
        """Create a neutral signal with given reason."""
        return IndicatorSignal(
            raw_value=0.0,
            signal_type=SignalType.NEUTRAL,
            confidence=0.1,
            strength=0.0,
            timeframe=self.timeframe,
            timestamp=datetime.now(),
            metadata={'reason': reason, 'strategy': 'ATR_Breakout'}
        )
    
    def _create_default_risk_parameters(self) -> RiskParameters:
        """Create default risk parameters when calculation fails."""
        return RiskParameters(
            position_size=self.config.get('base_position_size', 1000),
            stop_loss_price=None,
            take_profit_price=None,
            trailing_stop_distance=None,
            max_position_size=self.config.get('max_position_size', 5000),
            account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
            volatility_adjustment=1.0,
            portfolio_correlation_adjustment=1.0
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get comprehensive strategy information."""
        return {
            'name': 'ATR Breakout Strategy',
            'version': '1.0.0',
            'description': 'Volatility breakout strategy using Average True Range with institutional enhancements',
            'parameters': {
                'atr_period': self.atr_period,
                'atr_multiplier': self.atr_multiplier,
                'fast_atr_period': self.fast_atr_period,
                'slow_atr_period': self.slow_atr_period,
                'volume_weighted_atr': self.volume_weighted_atr,
                'adaptive_multiplier': self.adaptive_multiplier,
                'multi_timeframe_analysis': self.multi_timeframe_analysis,
                'volatility_regime_detection': self.volatility_regime_detection
            },
            'position_state': self.position_state.copy(),
            'performance_metrics': self.performance_metrics.copy()
        }