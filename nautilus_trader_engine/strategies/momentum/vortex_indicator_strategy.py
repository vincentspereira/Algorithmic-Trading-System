"""Vortex Indicator Strategy - Institutional Grade Implementation

This strategy implements the Vortex Indicator (VI) with institutional-grade
enhancements and modern risk management following the 5-Pillar Architecture.

Core Logic:
- True Range (TR) = max(High - Low, abs(High - Previous Close), abs(Low - Previous Close))
- Vortex Movement (VM+) = abs(High - Previous Low)
- Vortex Movement (VM-) = abs(Low - Previous High)
- VI+ = sum(VM+, n) / sum(TR, n)
- VI- = sum(VM-, n) / sum(TR, n)

Signals:
- Bullish: VI+ crosses above VI-
- Bearish: VI- crosses above VI+
- Trend Strength: Difference between VI+ and VI-

Enhancements:
- Volume-weighted vortex calculations
- Multi-period analysis (14, 21, 28)
- Divergence detection
- Trend strength filtering
- False signal reduction

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


class VortexIndicatorStrategy(BaseInstitutionalStrategy):
    """
    Vortex Indicator Strategy implementing the 5-Pillar Architecture.
    
    This strategy uses the Vortex Indicator with volume-weighted enhancements
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
        
        # Vortex Indicator parameters from config
        self.vi_period = self.config.get('vi_period', 14)
        self.vi_periods = self.config.get('vi_periods', [14, 21, 28])  # Multi-period analysis
        
        # Enhanced parameters
        self.volume_weighted = self.config.get('volume_weighted', True)
        self.divergence_detection = self.config.get('divergence_detection', True)
        self.trend_strength_filter = self.config.get('trend_strength_filter', True)
        self.false_signal_filter = self.config.get('false_signal_filter', True)
        
        # Signal thresholds
        self.crossover_threshold = self.config.get('crossover_threshold', 0.02)  # Minimum difference for crossover
        self.trend_strength_threshold = self.config.get('trend_strength_threshold', 0.1)
        self.strong_signal_threshold = self.config.get('strong_signal_threshold', 0.7)
        
        # Vortex state tracking
        self.vortex_state = {
            'current_trend': 'neutral',
            'vi_plus': 0.0,
            'vi_minus': 0.0,
            'trend_strength': 0.0,
            'crossovers': 0,
            'last_crossover': None,
            'false_signals': 0,
            'divergences': 0
        }
        
        self.logger.info(f"Vortex Indicator Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Vortex Indicator analysis.
        
        Signal Logic:
        1. Calculate Vortex Indicator (VI+ and VI-) for multiple periods
        2. Detect crossovers and validate with filters
        3. Analyze trend strength and momentum
        4. Check for divergences
        5. Apply false signal filtering
        """
        try:
            required_periods = max(max(self.vi_periods) * 2, 50)
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for Vortex Indicator calculation")
            
            # Calculate Vortex Indicators for multiple periods
            vortex_data = self._calculate_vortex_indicators(data)
            if not vortex_data:
                return self._create_neutral_signal("Vortex Indicator calculation failed")
            
            # Detect crossovers
            crossover_signals = self._detect_vortex_crossovers(vortex_data)
            
            # Analyze trend strength
            trend_strength = self._analyze_vortex_trend_strength(vortex_data) if self.trend_strength_filter else 0.5
            
            # Check for divergences
            divergence_signal = self._detect_vortex_divergence(data, vortex_data) if self.divergence_detection else None
            
            # Check for false signals
            is_false_signal = self._check_false_vortex_signal(data, vortex_data, crossover_signals) if self.false_signal_filter else False
            
            # Volume confirmation
            volume_confirmation = self._get_volume_confirmation(data)
            
            # Multi-period consensus
            period_consensus = self._get_multi_period_consensus(vortex_data)
            
            # Determine primary signal
            primary_signal = self._determine_primary_vortex_signal(
                crossover_signals, trend_strength, divergence_signal, period_consensus
            )
            
            # Apply filters and confirmations
            if is_false_signal:
                primary_signal['confidence'] *= 0.3  # Heavily penalize false signals
                self.vortex_state['false_signals'] += 1
            
            primary_signal['confidence'] *= volume_confirmation
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update Vortex state
            self._update_vortex_state(vortex_data, crossover_signals, trend_strength, divergence_signal)
            
            # Create metadata
            metadata = {
                'vortex_data': {
                    'vi_plus': vortex_data[self.vi_period]['vi_plus'].iloc[-1],
                    'vi_minus': vortex_data[self.vi_period]['vi_minus'].iloc[-1],
                    'trend_strength': trend_strength,
                    'periods': list(vortex_data.keys())
                },
                'crossover_signals': crossover_signals,
                'divergence_signal': divergence_signal,
                'is_false_signal': is_false_signal,
                'volume_confirmation': volume_confirmation,
                'period_consensus': period_consensus,
                'vortex_state': self.vortex_state.copy(),
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
            self.logger.error(f"Error generating Vortex Indicator signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_vortex_indicators(self, data: pd.DataFrame) -> Optional[Dict[int, Dict[str, pd.Series]]]:
        """
        Calculate Vortex Indicators for multiple periods.
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            volume = data['volume'] if self.volume_weighted else None
            
            vortex_data = {}
            
            for period in self.vi_periods:
                # Calculate True Range
                tr = self._calculate_true_range(high, low, close)
                
                # Calculate Vortex Movements
                vm_plus = abs(high - low.shift(1))
                vm_minus = abs(low - high.shift(1))
                
                if self.volume_weighted and volume is not None:
                    # Volume-weighted calculations
                    vm_plus_weighted = vm_plus * volume
                    vm_minus_weighted = vm_minus * volume
                    tr_weighted = tr * volume
                    
                    # Calculate volume-weighted sums
                    vm_plus_sum = vm_plus_weighted.rolling(period).sum()
                    vm_minus_sum = vm_minus_weighted.rolling(period).sum()
                    tr_sum = tr_weighted.rolling(period).sum()
                    
                    # Normalize by volume
                    volume_sum = volume.rolling(period).sum()
                    vm_plus_sum = vm_plus_sum / volume_sum
                    vm_minus_sum = vm_minus_sum / volume_sum
                    tr_sum = tr_sum / volume_sum
                else:
                    # Standard calculations
                    vm_plus_sum = vm_plus.rolling(period).sum()
                    vm_minus_sum = vm_minus.rolling(period).sum()
                    tr_sum = tr.rolling(period).sum()
                
                # Calculate Vortex Indicators
                vi_plus = vm_plus_sum / tr_sum
                vi_minus = vm_minus_sum / tr_sum
                
                # Handle division by zero
                vi_plus = vi_plus.fillna(1.0)
                vi_minus = vi_minus.fillna(1.0)
                
                vortex_data[period] = {
                    'vi_plus': vi_plus,
                    'vi_minus': vi_minus,
                    'vm_plus': vm_plus_sum,
                    'vm_minus': vm_minus_sum,
                    'tr': tr_sum,
                    'difference': vi_plus - vi_minus
                }
            
            return vortex_data
            
        except Exception as e:
            self.logger.error(f"Error calculating Vortex Indicators: {e}")
            return None
    
    def _calculate_true_range(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Calculate True Range.
        """
        try:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            return tr.fillna(0)
            
        except Exception as e:
            self.logger.warning(f"Error calculating True Range: {e}")
            return pd.Series([0] * len(high), index=high.index)
    
    def _detect_vortex_crossovers(self, vortex_data: Dict[int, Dict[str, pd.Series]]) -> Dict[str, Any]:
        """
        Detect crossovers in Vortex Indicators.
        """
        try:
            crossovers = {}
            
            for period, data in vortex_data.items():
                vi_plus = data['vi_plus']
                vi_minus = data['vi_minus']
                
                if len(vi_plus) < 3:
                    continue
                
                # Current and previous values
                current_plus = vi_plus.iloc[-1]
                current_minus = vi_minus.iloc[-1]
                prev_plus = vi_plus.iloc[-2]
                prev_minus = vi_minus.iloc[-2]
                
                # Check for crossovers with threshold
                difference = abs(current_plus - current_minus)
                
                if (prev_plus <= prev_minus and current_plus > current_minus and 
                    difference > self.crossover_threshold):
                    # Bullish crossover
                    crossovers[period] = {
                        'type': 'bullish_crossover',
                        'strength': min(difference * 5, 1.0),  # Scale difference to strength
                        'confidence': 0.8,
                        'vi_plus': current_plus,
                        'vi_minus': current_minus
                    }
                    
                elif (prev_plus >= prev_minus and current_plus < current_minus and 
                      difference > self.crossover_threshold):
                    # Bearish crossover
                    crossovers[period] = {
                        'type': 'bearish_crossover',
                        'strength': min(difference * 5, 1.0),
                        'confidence': 0.8,
                        'vi_plus': current_plus,
                        'vi_minus': current_minus
                    }
                    
                else:
                    # No crossover or below threshold
                    if current_plus > current_minus:
                        trend_type = 'bullish_continuation'
                    else:
                        trend_type = 'bearish_continuation'
                    
                    crossovers[period] = {
                        'type': trend_type,
                        'strength': min(difference * 2, 0.5),  # Lower strength for continuation
                        'confidence': 0.4,
                        'vi_plus': current_plus,
                        'vi_minus': current_minus
                    }
            
            return crossovers
            
        except Exception as e:
            self.logger.warning(f"Error detecting Vortex crossovers: {e}")
            return {}
    
    def _analyze_vortex_trend_strength(self, vortex_data: Dict[int, Dict[str, pd.Series]]) -> float:
        """
        Analyze trend strength using Vortex Indicators.
        """
        try:
            strengths = []
            
            for period, data in vortex_data.items():
                vi_plus = data['vi_plus']
                vi_minus = data['vi_minus']
                difference = data['difference']
                
                if len(difference) < 10:
                    continue
                
                # Current trend strength
                current_diff = abs(difference.iloc[-1])
                
                # Trend consistency over last 10 periods
                recent_diffs = difference.iloc[-10:]
                consistency = (recent_diffs.apply(lambda x: 1 if x > 0 else -1).rolling(5).mean().abs().mean())
                
                # Combine current strength and consistency
                period_strength = (current_diff * 2 + consistency * 0.5) / 2.5
                strengths.append(min(period_strength, 1.0))
            
            return np.mean(strengths) if strengths else 0.5
            
        except Exception as e:
            self.logger.warning(f"Error analyzing Vortex trend strength: {e}")
            return 0.5
    
    def _detect_vortex_divergence(self, data: pd.DataFrame, 
                                 vortex_data: Dict[int, Dict[str, pd.Series]]) -> Optional[Dict[str, Any]]:
        """
        Detect divergences between price and Vortex Indicators.
        """
        try:
            if len(data) < 20:
                return None
            
            close = data['close']
            primary_vi = vortex_data[self.vi_period]
            vi_difference = primary_vi['difference']
            
            # Look for divergences over last 20 periods
            lookback = min(20, len(close))
            recent_close = close.iloc[-lookback:]
            recent_vi_diff = vi_difference.iloc[-lookback:]
            
            # Price trend (simple linear regression slope)
            price_x = np.arange(len(recent_close))
            price_slope = np.polyfit(price_x, recent_close.values, 1)[0]
            
            # VI difference trend
            vi_slope = np.polyfit(price_x, recent_vi_diff.values, 1)[0]
            
            # Normalize slopes
            price_slope_norm = price_slope / recent_close.mean() if recent_close.mean() != 0 else 0
            vi_slope_norm = vi_slope / abs(recent_vi_diff.mean()) if recent_vi_diff.mean() != 0 else 0
            
            # Check for divergence
            if price_slope_norm > 0.001 and vi_slope_norm < -0.001:  # Price up, VI down
                return {
                    'type': 'bearish_divergence',
                    'strength': min(abs(price_slope_norm - vi_slope_norm) * 100, 1.0),
                    'confidence': 0.6
                }
            elif price_slope_norm < -0.001 and vi_slope_norm > 0.001:  # Price down, VI up
                return {
                    'type': 'bullish_divergence',
                    'strength': min(abs(price_slope_norm - vi_slope_norm) * 100, 1.0),
                    'confidence': 0.6
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error detecting Vortex divergence: {e}")
            return None
    
    def _check_false_vortex_signal(self, data: pd.DataFrame, vortex_data: Dict[int, Dict[str, pd.Series]], 
                                  crossover_signals: Dict[str, Any]) -> bool:
        """
        Check if the current Vortex signal might be false.
        """
        try:
            if len(data) < 10:
                return False
            
            # Check if there are recent crossovers (whipsaws)
            primary_vi = vortex_data[self.vi_period]
            vi_plus = primary_vi['vi_plus']
            vi_minus = primary_vi['vi_minus']
            
            if len(vi_plus) < 5:
                return False
            
            # Count crossovers in last 5 periods
            recent_crossovers = 0
            for i in range(len(vi_plus) - 5, len(vi_plus) - 1):
                if i <= 0:
                    continue
                
                curr_trend = 1 if vi_plus.iloc[i] > vi_minus.iloc[i] else -1
                prev_trend = 1 if vi_plus.iloc[i-1] > vi_minus.iloc[i-1] else -1
                
                if curr_trend != prev_trend:
                    recent_crossovers += 1
            
            if recent_crossovers >= 2:  # Too many recent crossovers
                return True
            
            # Check volume confirmation
            volume = data['volume']
            current_volume = volume.iloc[-1]
            avg_volume = volume.rolling(10).mean().iloc[-1]
            
            if current_volume < avg_volume * 0.7:  # Low volume signal
                return True
            
            # Check if VI values are too close (indecisive)
            current_diff = abs(vi_plus.iloc[-1] - vi_minus.iloc[-1])
            if current_diff < self.crossover_threshold * 0.5:
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking false Vortex signal: {e}")
            return False
    
    def _get_volume_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get volume confirmation for Vortex signals.
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
                return min(1.0 + (volume_ratio - 1.5) * 0.1, 1.3)
            # Weak volume
            elif volume_ratio < 0.7:
                return 0.7
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _get_multi_period_consensus(self, vortex_data: Dict[int, Dict[str, pd.Series]]) -> float:
        """
        Get consensus across multiple Vortex periods.
        """
        try:
            bullish_count = 0
            bearish_count = 0
            total_periods = len(vortex_data)
            
            for period, data in vortex_data.items():
                vi_plus = data['vi_plus'].iloc[-1]
                vi_minus = data['vi_minus'].iloc[-1]
                
                if vi_plus > vi_minus:
                    bullish_count += 1
                else:
                    bearish_count += 1
            
            # Calculate consensus strength
            if bullish_count > bearish_count:
                consensus = bullish_count / total_periods
            else:
                consensus = bearish_count / total_periods
            
            # Scale consensus to multiplier (0.8 to 1.2)
            return 0.8 + (consensus - 0.5) * 0.8
            
        except Exception as e:
            self.logger.warning(f"Error calculating multi-period consensus: {e}")
            return 1.0
    
    def _determine_primary_vortex_signal(self, crossover_signals: Dict[str, Any], 
                                        trend_strength: float, divergence_signal: Optional[Dict[str, Any]],
                                        period_consensus: float) -> Dict[str, Any]:
        """
        Determine the primary Vortex signal.
        """
        try:
            # Priority: Crossovers > Divergences > Continuations
            
            # Check for crossovers in primary period
            primary_crossover = crossover_signals.get(self.vi_period, {})
            
            if primary_crossover.get('type') in ['bullish_crossover', 'bearish_crossover']:
                # Strong crossover signals
                signal_strength = primary_crossover['strength'] * trend_strength * period_consensus
                
                return {
                    'signal_type': SignalType.STRONG_BULLISH if primary_crossover['type'] == 'bullish_crossover' else SignalType.STRONG_BEARISH,
                    'raw_value': signal_strength if primary_crossover['type'] == 'bullish_crossover' else -signal_strength,
                    'confidence': primary_crossover['confidence'],
                    'strength': signal_strength,
                    'source': 'crossover'
                }
            
            # Check for divergences
            if divergence_signal:
                signal_strength = divergence_signal['strength'] * trend_strength
                
                return {
                    'signal_type': SignalType.BULLISH if divergence_signal['type'] == 'bullish_divergence' else SignalType.BEARISH,
                    'raw_value': signal_strength if divergence_signal['type'] == 'bullish_divergence' else -signal_strength,
                    'confidence': divergence_signal['confidence'],
                    'strength': signal_strength,
                    'source': 'divergence'
                }
            
            # Check for strong continuations
            if primary_crossover.get('type') in ['bullish_continuation', 'bearish_continuation']:
                if trend_strength > self.strong_signal_threshold:
                    signal_strength = primary_crossover['strength'] * trend_strength * period_consensus
                    
                    return {
                        'signal_type': SignalType.BULLISH if primary_crossover['type'] == 'bullish_continuation' else SignalType.BEARISH,
                        'raw_value': signal_strength if primary_crossover['type'] == 'bullish_continuation' else -signal_strength,
                        'confidence': primary_crossover['confidence'],
                        'strength': signal_strength,
                        'source': 'continuation'
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
            self.logger.warning(f"Error determining primary Vortex signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_vortex_state(self, vortex_data: Dict[int, Dict[str, pd.Series]], 
                            crossover_signals: Dict[str, Any], trend_strength: float,
                            divergence_signal: Optional[Dict[str, Any]]) -> None:
        """
        Update internal Vortex state tracking.
        """
        try:
            primary_vi = vortex_data[self.vi_period]
            
            # Update current values
            self.vortex_state['vi_plus'] = primary_vi['vi_plus'].iloc[-1]
            self.vortex_state['vi_minus'] = primary_vi['vi_minus'].iloc[-1]
            self.vortex_state['trend_strength'] = trend_strength
            
            # Update trend
            if self.vortex_state['vi_plus'] > self.vortex_state['vi_minus']:
                self.vortex_state['current_trend'] = 'bullish'
            else:
                self.vortex_state['current_trend'] = 'bearish'
            
            # Update crossovers
            primary_crossover = crossover_signals.get(self.vi_period, {})
            if primary_crossover.get('type') in ['bullish_crossover', 'bearish_crossover']:
                self.vortex_state['crossovers'] += 1
                self.vortex_state['last_crossover'] = datetime.now()
            
            # Update divergences
            if divergence_signal:
                self.vortex_state['divergences'] += 1
            
        except Exception as e:
            self.logger.warning(f"Error updating Vortex state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using Vortex analysis.
        
        Risk Logic:
        1. Position sizing based on trend strength and VI difference
        2. Stop loss using ATR and VI levels
        3. Take profit at multiple ATR levels
        4. Trailing stop based on VI changes
        """
        try:
            current_price = data['close'].iloc[-1]
            vortex_data = signal.metadata.get('vortex_data', {})
            trend_strength = vortex_data.get('trend_strength', 0.5)
            
            # Calculate ATR for stop loss
            atr = self.volatility_indicators.atr(data['high'], data['low'], data['close'], period=14).iloc[-1]
            
            # Base position size
            base_position = self.config.get('base_position_size', 1000)
            
            # Adjust position size based on trend strength and VI difference
            vi_plus = vortex_data.get('vi_plus', 1.0)
            vi_minus = vortex_data.get('vi_minus', 1.0)
            vi_difference = abs(vi_plus - vi_minus)
            
            strength_multiplier = 0.5 + (trend_strength * 0.5)  # 0.5x to 1.0x
            vi_multiplier = 0.8 + (vi_difference * 2)  # 0.8x to 1.2x (assuming max diff of 0.2)
            vi_multiplier = min(vi_multiplier, 1.2)
            
            position_size = base_position * strength_multiplier * vi_multiplier
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss and take profit calculation
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions
                stop_loss_price = current_price - (atr * 2)
                take_profit_price = current_price + (atr * 3)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions
                stop_loss_price = current_price + (atr * 2)
                take_profit_price = current_price - (atr * 3)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using ATR
            trailing_stop_distance = atr * 1.5
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=self.config.get('max_position_size', 5000),
                account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
                volatility_adjustment=vi_multiplier,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime using Vortex analysis.
        
        Regime Logic:
        1. VI difference and trend strength
        2. Crossover frequency
        3. Volatility levels
        4. Trend consistency
        """
        try:
            if len(data) < 50:
                return MarketRegime.UNKNOWN
            
            vortex_data = self._calculate_vortex_indicators(data)
            if not vortex_data:
                return MarketRegime.UNKNOWN
            
            primary_vi = vortex_data[self.vi_period]
            vi_plus = primary_vi['vi_plus']
            vi_minus = primary_vi['vi_minus']
            vi_difference = primary_vi['difference']
            
            # Calculate trend strength and consistency
            trend_strength = self._analyze_vortex_trend_strength(vortex_data)
            
            # Count crossovers in recent period
            crossovers = 0
            for i in range(max(1, len(vi_plus) - 20), len(vi_plus)):
                if i <= 0:
                    continue
                curr_trend = 1 if vi_plus.iloc[i] > vi_minus.iloc[i] else -1
                prev_trend = 1 if vi_plus.iloc[i-1] > vi_minus.iloc[i-1] else -1
                if curr_trend != prev_trend:
                    crossovers += 1
            
            # Calculate volatility
            atr = self.volatility_indicators.atr(data['high'], data['low'], data['close'], period=14).iloc[-1]
            volatility_ratio = atr / data['close'].iloc[-1] if data['close'].iloc[-1] > 0 else 0
            
            # Determine regime
            current_vi_diff = abs(vi_difference.iloc[-1])
            
            if trend_strength > 0.7 and current_vi_diff > 0.1:
                if vi_plus.iloc[-1] > vi_minus.iloc[-1]:
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            elif volatility_ratio > 0.03:  # High volatility
                return MarketRegime.HIGH_VOLATILITY
            elif volatility_ratio < 0.01:  # Low volatility
                return MarketRegime.LOW_VOLATILITY
            elif crossovers > 3:  # Frequent crossovers
                return MarketRegime.RANGING
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on Vortex signals.
        
        Execution Logic:
        1. Crossover signals get immediate execution
        2. Divergence signals get VWAP execution
        3. Continuation signals get patient limit orders
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
            
            if signal_source == 'crossover':
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif signal_source == 'divergence':
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.MEDIUM
            elif signal_source == 'continuation' and signal.strength > 0.6:
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
                    'strategy': 'Vortex_Indicator',
                    'signal_confidence': signal.confidence,
                    'signal_source': signal_source,
                    'vortex_state': signal.metadata.get('vortex_state'),
                    'vortex_data': signal.metadata.get('vortex_data'),
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
        1. Vortex-specific performance metrics
        2. Crossover vs divergence performance
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
                    f"Vortex Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Signal Source: {signal_source}, "
                    f"Trend: {self.vortex_state['current_trend']}, "
                    f"Crossovers: {self.vortex_state['crossovers']}, "
                    f"False Signals: {self.vortex_state['false_signals']}, "
                    f"Divergences: {self.vortex_state['divergences']}"
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