"""On-Balance Volume (OBV) Trend Strategy - Institutional Grade Implementation

This strategy implements the On-Balance Volume indicator with institutional-grade
enhancements and modern risk management following the 5-Pillar Architecture.

Core Logic:
- OBV = Previous OBV + Volume (if Close > Previous Close)
- OBV = Previous OBV - Volume (if Close < Previous Close)
- OBV = Previous OBV (if Close = Previous Close)

Signals:
- Bullish: OBV trending up with price confirmation
- Bearish: OBV trending down with price confirmation
- Divergence: OBV and price moving in opposite directions

Enhancements:
- Multi-timeframe OBV analysis
- Volume-weighted moving averages of OBV
- Divergence detection with strength scoring
- Trend confirmation using multiple periods
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
from ..indicators.traditional.volume_indicators import VolumeIndicators
from ..indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ..indicators.traditional.trend_indicators import TrendIndicators
from ..risk_management_utils import RiskManagementUtils
from ..execution_intent_utils import ExecutionIntentUtils


class OBVTrendStrategy(BaseInstitutionalStrategy):
    """
    On-Balance Volume Trend Strategy implementing the 5-Pillar Architecture.
    
    This strategy uses OBV with volume-weighted enhancements and sophisticated
    divergence analysis for institutional-grade performance.
    """
    
    def __init__(self, config_path: str, symbol: str, timeframe: str = "1D"):
        super().__init__(config_path, symbol, timeframe)
        
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        self.volume_indicators = VolumeIndicators()
        self.volume_weighted_indicators = VolumeWeightedIndicators()
        self.trend_indicators = TrendIndicators()
        self.risk_utils = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        # OBV parameters from config
        self.obv_ma_period = self.config.get('obv_ma_period', 20)
        self.obv_ma_periods = self.config.get('obv_ma_periods', [10, 20, 50])  # Multi-period analysis
        
        # Enhanced parameters
        self.volume_weighted_ma = self.config.get('volume_weighted_ma', True)
        self.divergence_detection = self.config.get('divergence_detection', True)
        self.trend_confirmation = self.config.get('trend_confirmation', True)
        self.false_breakout_filter = self.config.get('false_breakout_filter', True)
        
        # Signal thresholds
        self.trend_threshold = self.config.get('trend_threshold', 0.02)  # Minimum trend slope
        self.divergence_threshold = self.config.get('divergence_threshold', 0.05)
        self.confirmation_periods = self.config.get('confirmation_periods', 3)
        self.strong_signal_threshold = self.config.get('strong_signal_threshold', 0.7)
        
        # OBV state tracking
        self.obv_state = {
            'current_obv': 0.0,
            'obv_trend': 'neutral',
            'price_trend': 'neutral',
            'divergences': 0,
            'confirmations': 0,
            'false_breakouts': 0,
            'last_signal': None,
            'trend_strength': 0.0
        }
        
        self.logger.info(f"OBV Trend Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using OBV analysis.
        
        Signal Logic:
        1. Calculate OBV and its moving averages
        2. Analyze OBV trend direction and strength
        3. Check for price-OBV divergences
        4. Confirm signals with multiple periods
        5. Filter false breakouts
        """
        try:
            required_periods = max(max(self.obv_ma_periods) * 2, 60)
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for OBV calculation")
            
            # Calculate OBV and related indicators
            obv_data = self._calculate_obv_indicators(data)
            if obv_data is None:
                return self._create_neutral_signal("OBV calculation failed")
            
            # Analyze OBV trend
            obv_trend_analysis = self._analyze_obv_trend(obv_data)
            
            # Check for divergences
            divergence_signal = self._detect_obv_divergence(data, obv_data) if self.divergence_detection else None
            
            # Get trend confirmation
            trend_confirmation = self._get_trend_confirmation(data, obv_data) if self.trend_confirmation else 1.0
            
            # Check for false breakouts
            is_false_breakout = self._check_false_obv_breakout(data, obv_data) if self.false_breakout_filter else False
            
            # Volume analysis
            volume_strength = self._analyze_volume_strength(data)
            
            # Multi-period consensus
            period_consensus = self._get_multi_period_obv_consensus(obv_data)
            
            # Determine primary signal
            primary_signal = self._determine_primary_obv_signal(
                obv_trend_analysis, divergence_signal, trend_confirmation, period_consensus
            )
            
            # Apply filters and confirmations
            if is_false_breakout:
                primary_signal['confidence'] *= 0.4  # Heavily penalize false breakouts
                self.obv_state['false_breakouts'] += 1
            
            primary_signal['confidence'] *= volume_strength
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update OBV state
            self._update_obv_state(obv_data, obv_trend_analysis, divergence_signal, trend_confirmation)
            
            # Create metadata
            metadata = {
                'obv_data': {
                    'current_obv': obv_data['obv'].iloc[-1],
                    'obv_ma': obv_data['obv_ma'].iloc[-1],
                    'obv_slope': obv_trend_analysis['slope'],
                    'periods': self.obv_ma_periods
                },
                'trend_analysis': obv_trend_analysis,
                'divergence_signal': divergence_signal,
                'trend_confirmation': trend_confirmation,
                'is_false_breakout': is_false_breakout,
                'volume_strength': volume_strength,
                'period_consensus': period_consensus,
                'obv_state': self.obv_state.copy(),
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
            self.logger.error(f"Error generating OBV signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_obv_indicators(self, data: pd.DataFrame) -> Optional[Dict[str, pd.Series]]:
        """
        Calculate OBV and related indicators.
        """
        try:
            close = data['close']
            volume = data['volume']
            
            # Calculate basic OBV
            obv = self._calculate_obv(close, volume)
            
            # Calculate OBV moving averages for different periods
            obv_mas = {}
            for period in self.obv_ma_periods:
                if self.volume_weighted_ma:
                    # Volume-weighted moving average of OBV
                    obv_mas[period] = self.volume_weighted_indicators.vw_sma(
                        obv, volume, period
                    )
                else:
                    # Simple moving average of OBV
                    obv_mas[period] = obv.rolling(period).mean()
            
            # Primary OBV MA
            obv_ma = obv_mas[self.obv_ma_period]
            
            # OBV rate of change
            obv_roc = obv.pct_change(periods=self.obv_ma_period).fillna(0)
            
            # OBV momentum (difference from MA)
            obv_momentum = obv - obv_ma
            
            # Normalized OBV (for comparison across different scales)
            obv_normalized = (obv - obv.rolling(50).mean()) / obv.rolling(50).std()
            obv_normalized = obv_normalized.fillna(0)
            
            return {
                'obv': obv,
                'obv_ma': obv_ma,
                'obv_mas': obv_mas,
                'obv_roc': obv_roc,
                'obv_momentum': obv_momentum,
                'obv_normalized': obv_normalized
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating OBV indicators: {e}")
            return None
    
    def _calculate_obv(self, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Calculate On-Balance Volume.
        """
        try:
            obv = pd.Series(index=close.index, dtype=float)
            obv.iloc[0] = volume.iloc[0]  # Initialize with first volume
            
            for i in range(1, len(close)):
                if close.iloc[i] > close.iloc[i-1]:
                    # Price up: add volume
                    obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
                elif close.iloc[i] < close.iloc[i-1]:
                    # Price down: subtract volume
                    obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
                else:
                    # Price unchanged: OBV unchanged
                    obv.iloc[i] = obv.iloc[i-1]
            
            return obv
            
        except Exception as e:
            self.logger.warning(f"Error calculating OBV: {e}")
            return pd.Series([0] * len(close), index=close.index)
    
    def _analyze_obv_trend(self, obv_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Analyze OBV trend direction and strength.
        """
        try:
            obv = obv_data['obv']
            obv_ma = obv_data['obv_ma']
            
            if len(obv) < 20:
                return {'direction': 'neutral', 'strength': 0.0, 'slope': 0.0}
            
            # Calculate trend slope using linear regression
            lookback = min(20, len(obv))
            recent_obv = obv.iloc[-lookback:]
            x = np.arange(len(recent_obv))
            
            # OBV slope
            obv_slope = np.polyfit(x, recent_obv.values, 1)[0]
            
            # Normalize slope by average OBV value
            avg_obv = abs(recent_obv.mean())
            normalized_slope = obv_slope / avg_obv if avg_obv > 0 else 0
            
            # Determine trend direction
            if normalized_slope > self.trend_threshold:
                direction = 'bullish'
                strength = min(abs(normalized_slope) * 10, 1.0)  # Scale to 0-1
            elif normalized_slope < -self.trend_threshold:
                direction = 'bearish'
                strength = min(abs(normalized_slope) * 10, 1.0)
            else:
                direction = 'neutral'
                strength = 0.2
            
            # Check OBV vs MA relationship
            current_obv = obv.iloc[-1]
            current_ma = obv_ma.iloc[-1]
            
            ma_relationship = 'above' if current_obv > current_ma else 'below'
            
            # Calculate trend consistency
            recent_slopes = []
            for i in range(max(1, len(obv) - 10), len(obv)):
                if i >= 5:
                    mini_obv = obv.iloc[i-5:i+1]
                    mini_x = np.arange(len(mini_obv))
                    mini_slope = np.polyfit(mini_x, mini_obv.values, 1)[0]
                    recent_slopes.append(mini_slope)
            
            # Trend consistency (how often slopes agree with main trend)
            if recent_slopes:
                if direction == 'bullish':
                    consistency = sum(1 for s in recent_slopes if s > 0) / len(recent_slopes)
                elif direction == 'bearish':
                    consistency = sum(1 for s in recent_slopes if s < 0) / len(recent_slopes)
                else:
                    consistency = 0.5
            else:
                consistency = 0.5
            
            return {
                'direction': direction,
                'strength': strength,
                'slope': normalized_slope,
                'ma_relationship': ma_relationship,
                'consistency': consistency,
                'raw_slope': obv_slope
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing OBV trend: {e}")
            return {'direction': 'neutral', 'strength': 0.0, 'slope': 0.0}
    
    def _detect_obv_divergence(self, data: pd.DataFrame, 
                              obv_data: Dict[str, pd.Series]) -> Optional[Dict[str, Any]]:
        """
        Detect divergences between price and OBV.
        """
        try:
            if len(data) < 30:
                return None
            
            close = data['close']
            obv = obv_data['obv']
            
            # Look for divergences over last 20 periods
            lookback = min(20, len(close))
            recent_close = close.iloc[-lookback:]
            recent_obv = obv.iloc[-lookback:]
            
            # Calculate price and OBV trends (linear regression slopes)
            x = np.arange(len(recent_close))
            
            price_slope = np.polyfit(x, recent_close.values, 1)[0]
            obv_slope = np.polyfit(x, recent_obv.values, 1)[0]
            
            # Normalize slopes
            price_slope_norm = price_slope / recent_close.mean() if recent_close.mean() != 0 else 0
            obv_slope_norm = obv_slope / abs(recent_obv.mean()) if recent_obv.mean() != 0 else 0
            
            # Check for significant divergence
            divergence_threshold = self.divergence_threshold
            
            if (price_slope_norm > divergence_threshold and 
                obv_slope_norm < -divergence_threshold):  # Price up, OBV down
                
                strength = min(abs(price_slope_norm - obv_slope_norm) * 5, 1.0)
                return {
                    'type': 'bearish_divergence',
                    'strength': strength,
                    'confidence': 0.7,
                    'price_slope': price_slope_norm,
                    'obv_slope': obv_slope_norm
                }
                
            elif (price_slope_norm < -divergence_threshold and 
                  obv_slope_norm > divergence_threshold):  # Price down, OBV up
                
                strength = min(abs(price_slope_norm - obv_slope_norm) * 5, 1.0)
                return {
                    'type': 'bullish_divergence',
                    'strength': strength,
                    'confidence': 0.7,
                    'price_slope': price_slope_norm,
                    'obv_slope': obv_slope_norm
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Error detecting OBV divergence: {e}")
            return None
    
    def _get_trend_confirmation(self, data: pd.DataFrame, 
                               obv_data: Dict[str, pd.Series]) -> float:
        """
        Get trend confirmation using multiple indicators.
        """
        try:
            confirmations = []
            
            # Price trend confirmation
            close = data['close']
            if len(close) >= 20:
                price_sma_short = close.rolling(10).mean()
                price_sma_long = close.rolling(20).mean()
                
                if price_sma_short.iloc[-1] > price_sma_long.iloc[-1]:
                    confirmations.append(1)  # Bullish price trend
                else:
                    confirmations.append(-1)  # Bearish price trend
            
            # Volume trend confirmation
            volume = data['volume']
            if len(volume) >= 20:
                volume_ma = volume.rolling(20).mean()
                current_volume = volume.iloc[-1]
                
                if current_volume > volume_ma.iloc[-1] * 1.2:
                    confirmations.append(1)  # High volume
                elif current_volume < volume_ma.iloc[-1] * 0.8:
                    confirmations.append(-1)  # Low volume
                else:
                    confirmations.append(0)  # Normal volume
            
            # OBV MA confirmation
            obv = obv_data['obv']
            obv_ma = obv_data['obv_ma']
            
            if obv.iloc[-1] > obv_ma.iloc[-1]:
                confirmations.append(1)  # OBV above MA
            else:
                confirmations.append(-1)  # OBV below MA
            
            # Calculate confirmation strength
            if confirmations:
                avg_confirmation = np.mean(confirmations)
                # Convert to multiplier (0.7 to 1.3)
                return 1.0 + (avg_confirmation * 0.3)
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error getting trend confirmation: {e}")
            return 1.0
    
    def _check_false_obv_breakout(self, data: pd.DataFrame, 
                                 obv_data: Dict[str, pd.Series]) -> bool:
        """
        Check if the current OBV signal might be a false breakout.
        """
        try:
            if len(data) < 10:
                return False
            
            obv = obv_data['obv']
            obv_ma = obv_data['obv_ma']
            
            if len(obv) < 10:
                return False
            
            # Check for recent whipsaws (OBV crossing MA multiple times)
            crossovers = 0
            for i in range(max(1, len(obv) - 5), len(obv)):
                if i <= 0:
                    continue
                
                curr_above = obv.iloc[i] > obv_ma.iloc[i]
                prev_above = obv.iloc[i-1] > obv_ma.iloc[i-1]
                
                if curr_above != prev_above:
                    crossovers += 1
            
            if crossovers >= 2:  # Too many recent crossovers
                return True
            
            # Check volume confirmation
            volume = data['volume']
            current_volume = volume.iloc[-1]
            avg_volume = volume.rolling(10).mean().iloc[-1]
            
            if current_volume < avg_volume * 0.6:  # Very low volume
                return True
            
            # Check if OBV change is too small
            obv_change = abs(obv.iloc[-1] - obv.iloc[-2])
            avg_obv_change = abs(obv.diff()).rolling(10).mean().iloc[-1]
            
            if obv_change < avg_obv_change * 0.3:  # Very small OBV change
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking false OBV breakout: {e}")
            return False
    
    def _analyze_volume_strength(self, data: pd.DataFrame) -> float:
        """
        Analyze current volume strength.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            volume = data['volume']
            current_volume = volume.iloc[-1]
            
            # Compare to different averages
            volume_ma_5 = volume.rolling(5).mean().iloc[-1]
            volume_ma_20 = volume.rolling(20).mean().iloc[-1]
            
            # Volume strength score
            if current_volume > volume_ma_5 * 1.5:
                strength = 1.3  # Very high volume
            elif current_volume > volume_ma_20 * 1.2:
                strength = 1.1  # High volume
            elif current_volume < volume_ma_20 * 0.7:
                strength = 0.8  # Low volume
            else:
                strength = 1.0  # Normal volume
            
            return min(strength, 1.5)  # Cap at 1.5x
            
        except Exception as e:
            self.logger.warning(f"Error analyzing volume strength: {e}")
            return 1.0
    
    def _get_multi_period_obv_consensus(self, obv_data: Dict[str, pd.Series]) -> float:
        """
        Get consensus across multiple OBV MA periods.
        """
        try:
            obv = obv_data['obv']
            obv_mas = obv_data['obv_mas']
            
            bullish_count = 0
            bearish_count = 0
            total_periods = len(obv_mas)
            
            current_obv = obv.iloc[-1]
            
            for period, ma in obv_mas.items():
                if current_obv > ma.iloc[-1]:
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
            self.logger.warning(f"Error calculating multi-period OBV consensus: {e}")
            return 1.0
    
    def _determine_primary_obv_signal(self, trend_analysis: Dict[str, Any], 
                                     divergence_signal: Optional[Dict[str, Any]],
                                     trend_confirmation: float, period_consensus: float) -> Dict[str, Any]:
        """
        Determine the primary OBV signal.
        """
        try:
            # Priority: Divergences > Strong Trends > Weak Trends
            
            # Check for divergences first
            if divergence_signal:
                signal_strength = divergence_signal['strength'] * trend_confirmation
                
                return {
                    'signal_type': SignalType.BULLISH if divergence_signal['type'] == 'bullish_divergence' else SignalType.BEARISH,
                    'raw_value': signal_strength if divergence_signal['type'] == 'bullish_divergence' else -signal_strength,
                    'confidence': divergence_signal['confidence'],
                    'strength': signal_strength,
                    'source': 'divergence'
                }
            
            # Check for strong trend signals
            trend_direction = trend_analysis['direction']
            trend_strength = trend_analysis['strength']
            trend_consistency = trend_analysis.get('consistency', 0.5)
            
            if trend_direction in ['bullish', 'bearish'] and trend_strength > 0.5:
                # Strong trend signal
                signal_strength = trend_strength * trend_consistency * trend_confirmation * period_consensus
                
                if trend_strength > self.strong_signal_threshold:
                    signal_type = SignalType.STRONG_BULLISH if trend_direction == 'bullish' else SignalType.STRONG_BEARISH
                else:
                    signal_type = SignalType.BULLISH if trend_direction == 'bullish' else SignalType.BEARISH
                
                return {
                    'signal_type': signal_type,
                    'raw_value': signal_strength if trend_direction == 'bullish' else -signal_strength,
                    'confidence': 0.7,
                    'strength': signal_strength,
                    'source': 'trend'
                }
            
            # Weak or neutral signal
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'none'
            }
            
        except Exception as e:
            self.logger.warning(f"Error determining primary OBV signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_obv_state(self, obv_data: Dict[str, pd.Series], trend_analysis: Dict[str, Any],
                         divergence_signal: Optional[Dict[str, Any]], trend_confirmation: float) -> None:
        """
        Update internal OBV state tracking.
        """
        try:
            # Update current values
            self.obv_state['current_obv'] = obv_data['obv'].iloc[-1]
            self.obv_state['obv_trend'] = trend_analysis['direction']
            self.obv_state['trend_strength'] = trend_analysis['strength']
            
            # Update price trend (simple)
            if trend_confirmation > 1.1:
                self.obv_state['price_trend'] = 'bullish'
            elif trend_confirmation < 0.9:
                self.obv_state['price_trend'] = 'bearish'
            else:
                self.obv_state['price_trend'] = 'neutral'
            
            # Update divergences
            if divergence_signal:
                self.obv_state['divergences'] += 1
            
            # Update confirmations
            if abs(trend_confirmation - 1.0) > 0.1:
                self.obv_state['confirmations'] += 1
            
            # Update last signal
            self.obv_state['last_signal'] = datetime.now()
            
        except Exception as e:
            self.logger.warning(f"Error updating OBV state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using OBV analysis.
        
        Risk Logic:
        1. Position sizing based on OBV trend strength and volume
        2. Stop loss using ATR and OBV support/resistance
        3. Take profit at multiple levels based on OBV momentum
        4. Trailing stop based on OBV trend changes
        """
        try:
            current_price = data['close'].iloc[-1]
            obv_data = signal.metadata.get('obv_data', {})
            trend_analysis = signal.metadata.get('trend_analysis', {})
            
            trend_strength = trend_analysis.get('strength', 0.5)
            volume_strength = signal.metadata.get('volume_strength', 1.0)
            
            # Calculate ATR for stop loss
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
            
            # Adjust position size based on trend strength and volume
            strength_multiplier = 0.6 + (trend_strength * 0.4)  # 0.6x to 1.0x
            volume_multiplier = min(volume_strength, 1.3)  # Cap at 1.3x
            
            position_size = base_position * strength_multiplier * volume_multiplier
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss and take profit calculation
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions
                stop_loss_price = current_price - (atr * 2.5)
                take_profit_price = current_price + (atr * 4)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions
                stop_loss_price = current_price + (atr * 2.5)
                take_profit_price = current_price - (atr * 4)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using ATR
            trailing_stop_distance = atr * 2
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=self.config.get('max_position_size', 5000),
                account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
                volatility_adjustment=volume_multiplier,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime using OBV analysis.
        
        Regime Logic:
        1. OBV trend strength and consistency
        2. Volume patterns
        3. Price-OBV relationship
        4. Volatility levels
        """
        try:
            if len(data) < 50:
                return MarketRegime.UNKNOWN
            
            obv_data = self._calculate_obv_indicators(data)
            if not obv_data:
                return MarketRegime.UNKNOWN
            
            trend_analysis = self._analyze_obv_trend(obv_data)
            
            # Calculate volatility
            close = data['close']
            returns = close.pct_change().dropna()
            volatility = returns.rolling(20).std().iloc[-1] * np.sqrt(252)  # Annualized
            
            # Volume analysis
            volume = data['volume']
            volume_trend = volume.rolling(20).mean().iloc[-1] / volume.rolling(50).mean().iloc[-1]
            
            # Determine regime
            trend_strength = trend_analysis['strength']
            trend_direction = trend_analysis['direction']
            trend_consistency = trend_analysis.get('consistency', 0.5)
            
            if trend_strength > 0.7 and trend_consistency > 0.7:
                if trend_direction == 'bullish':
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            elif volatility > 0.3:  # High volatility
                return MarketRegime.HIGH_VOLATILITY
            elif volatility < 0.15:  # Low volatility
                return MarketRegime.LOW_VOLATILITY
            elif volume_trend < 0.8:  # Low volume environment
                return MarketRegime.LOW_VOLATILITY
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on OBV signals.
        
        Execution Logic:
        1. Divergence signals get VWAP execution
        2. Strong trend signals get TWAP execution
        3. Weak signals get limit orders
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
            
            if signal_source == 'divergence':
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.MEDIUM
            elif signal.signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH]:
                algorithm = ExecutionAlgorithm.TWAP
                urgency = ExecutionUrgency.HIGH
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
                    'strategy': 'OBV_Trend',
                    'signal_confidence': signal.confidence,
                    'signal_source': signal_source,
                    'obv_state': signal.metadata.get('obv_state'),
                    'obv_data': signal.metadata.get('obv_data'),
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
        1. OBV-specific performance metrics
        2. Divergence vs trend performance
        3. Volume-based performance analysis
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
                    f"OBV Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Signal Source: {signal_source}, "
                    f"OBV Trend: {self.obv_state['obv_trend']}, "
                    f"Price Trend: {self.obv_state['price_trend']}, "
                    f"Divergences: {self.obv_state['divergences']}, "
                    f"False Breakouts: {self.obv_state['false_breakouts']}"
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