"""Bollinger Band Squeeze Breakout Strategy - Institutional Grade Implementation

This strategy implements the Bollinger Band Squeeze concept with institutional-grade
enhancements and modern risk management following the 5-Pillar Architecture.

Core Logic:
- Squeeze occurs when Bollinger Bands contract (low volatility)
- Breakout occurs when price moves outside bands with volume confirmation
- Direction determined by momentum indicators and volume analysis

Signals:
- Bullish: Upward breakout from squeeze with volume confirmation
- Bearish: Downward breakout from squeeze with volume confirmation
- Neutral: During squeeze periods or weak breakouts

Enhancements:
- Multi-timeframe squeeze detection
- Volume-weighted Bollinger Bands
- Keltner Channel confirmation
- False breakout filtering
- Dynamic band width analysis

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


class BollingerSqueezeStrategy(BaseInstitutionalStrategy):
    """
    Bollinger Band Squeeze Breakout Strategy implementing the 5-Pillar Architecture.
    
    This strategy identifies low volatility periods (squeezes) and trades the
    subsequent breakouts with institutional-grade risk management.
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
        
        # Bollinger Band parameters from config
        self.bb_period = self.config.get('bb_period', 20)
        self.bb_std_dev = self.config.get('bb_std_dev', 2.0)
        self.kc_period = self.config.get('kc_period', 20)
        self.kc_multiplier = self.config.get('kc_multiplier', 1.5)
        
        # Enhanced parameters
        self.volume_weighted_bands = self.config.get('volume_weighted_bands', True)
        self.multi_timeframe_analysis = self.config.get('multi_timeframe_analysis', True)
        self.false_breakout_filter = self.config.get('false_breakout_filter', True)
        self.momentum_confirmation = self.config.get('momentum_confirmation', True)
        
        # Squeeze detection parameters
        self.squeeze_threshold = self.config.get('squeeze_threshold', 0.95)  # BB inside KC ratio
        self.min_squeeze_periods = self.config.get('min_squeeze_periods', 3)
        self.max_squeeze_periods = self.config.get('max_squeeze_periods', 50)
        
        # Breakout parameters
        self.breakout_volume_threshold = self.config.get('breakout_volume_threshold', 1.5)
        self.momentum_threshold = self.config.get('momentum_threshold', 0.6)
        self.confirmation_periods = self.config.get('confirmation_periods', 2)
        
        # Squeeze state tracking
        self.squeeze_state = {
            'in_squeeze': False,
            'squeeze_periods': 0,
            'squeeze_start': None,
            'last_breakout': None,
            'breakout_direction': None,
            'false_breakouts': 0,
            'successful_breakouts': 0,
            'band_width_history': [],
            'volume_profile': []
        }
        
        self.logger.info(f"Bollinger Squeeze Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Bollinger Band Squeeze analysis.
        
        Signal Logic:
        1. Detect squeeze conditions (BB inside KC)
        2. Monitor squeeze duration and intensity
        3. Identify breakout with volume confirmation
        4. Confirm direction with momentum indicators
        5. Filter false breakouts
        """
        try:
            required_periods = max(self.bb_period * 3, 60)
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for Bollinger Squeeze calculation")
            
            # Calculate Bollinger Bands and Keltner Channels
            bands_data = self._calculate_bands_indicators(data)
            if bands_data is None:
                return self._create_neutral_signal("Bands calculation failed")
            
            # Detect squeeze conditions
            squeeze_analysis = self._analyze_squeeze_conditions(bands_data)
            
            # Check for breakout signals
            breakout_signal = self._detect_breakout_signal(data, bands_data, squeeze_analysis)
            
            # Get momentum confirmation
            momentum_confirmation = self._get_momentum_confirmation(data) if self.momentum_confirmation else 1.0
            
            # Check for false breakouts
            is_false_breakout = self._check_false_breakout(data, bands_data) if self.false_breakout_filter else False
            
            # Volume analysis
            volume_confirmation = self._analyze_breakout_volume(data)
            
            # Multi-timeframe analysis (if enabled)
            mtf_confirmation = self._get_multi_timeframe_confirmation(data) if self.multi_timeframe_analysis else 1.0
            
            # Determine primary signal
            primary_signal = self._determine_primary_squeeze_signal(
                squeeze_analysis, breakout_signal, momentum_confirmation, volume_confirmation, mtf_confirmation
            )
            
            # Apply filters and confirmations
            if is_false_breakout:
                primary_signal['confidence'] *= 0.3  # Heavily penalize false breakouts
                self.squeeze_state['false_breakouts'] += 1
            
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update squeeze state
            self._update_squeeze_state(squeeze_analysis, breakout_signal, is_false_breakout)
            
            # Create metadata
            metadata = {
                'bands_data': {
                    'bb_upper': bands_data['bb_upper'].iloc[-1],
                    'bb_lower': bands_data['bb_lower'].iloc[-1],
                    'bb_middle': bands_data['bb_middle'].iloc[-1],
                    'kc_upper': bands_data['kc_upper'].iloc[-1],
                    'kc_lower': bands_data['kc_lower'].iloc[-1],
                    'band_width': bands_data['band_width'].iloc[-1]
                },
                'squeeze_analysis': squeeze_analysis,
                'breakout_signal': breakout_signal,
                'momentum_confirmation': momentum_confirmation,
                'volume_confirmation': volume_confirmation,
                'mtf_confirmation': mtf_confirmation,
                'is_false_breakout': is_false_breakout,
                'squeeze_state': self.squeeze_state.copy(),
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
            self.logger.error(f"Error generating Bollinger Squeeze signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_bands_indicators(self, data: pd.DataFrame) -> Optional[Dict[str, pd.Series]]:
        """
        Calculate Bollinger Bands and Keltner Channels.
        """
        try:
            close = data['close']
            high = data['high']
            low = data['low']
            volume = data['volume']
            
            # Calculate Bollinger Bands
            if self.volume_weighted_bands:
                # Volume-weighted moving average
                bb_middle = self.volume_weighted_indicators.vw_sma(close, volume, self.bb_period)
                # Volume-weighted standard deviation (approximation)
                vw_variance = self.volume_weighted_indicators.vw_sma(
                    (close - bb_middle) ** 2, volume, self.bb_period
                )
                bb_std = np.sqrt(vw_variance)
            else:
                # Traditional Bollinger Bands
                bb_middle = close.rolling(self.bb_period).mean()
                bb_std = close.rolling(self.bb_period).std()
            
            bb_upper = bb_middle + (bb_std * self.bb_std_dev)
            bb_lower = bb_middle - (bb_std * self.bb_std_dev)
            
            # Calculate Keltner Channels
            kc_middle = close.rolling(self.kc_period).mean()
            
            # True Range for Keltner Channels
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(self.kc_period).mean()
            
            kc_upper = kc_middle + (atr * self.kc_multiplier)
            kc_lower = kc_middle - (atr * self.kc_multiplier)
            
            # Calculate band width (normalized)
            band_width = (bb_upper - bb_lower) / bb_middle
            
            # Calculate squeeze indicator (BB inside KC)
            squeeze_indicator = ((bb_upper <= kc_upper) & (bb_lower >= kc_lower)).astype(int)
            
            # Band width percentile (for relative squeeze strength)
            band_width_percentile = band_width.rolling(100).rank(pct=True)
            
            return {
                'bb_upper': bb_upper,
                'bb_middle': bb_middle,
                'bb_lower': bb_lower,
                'bb_std': bb_std,
                'kc_upper': kc_upper,
                'kc_middle': kc_middle,
                'kc_lower': kc_lower,
                'atr': atr,
                'band_width': band_width,
                'squeeze_indicator': squeeze_indicator,
                'band_width_percentile': band_width_percentile
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating bands indicators: {e}")
            return None
    
    def _analyze_squeeze_conditions(self, bands_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Analyze current squeeze conditions and characteristics.
        """
        try:
            squeeze_indicator = bands_data['squeeze_indicator']
            band_width = bands_data['band_width']
            band_width_percentile = bands_data['band_width_percentile']
            
            if len(squeeze_indicator) < 10:
                return {'in_squeeze': False, 'squeeze_strength': 0.0}
            
            # Current squeeze status
            current_squeeze = squeeze_indicator.iloc[-1] == 1
            
            # Count consecutive squeeze periods
            consecutive_squeeze = 0
            for i in range(len(squeeze_indicator) - 1, -1, -1):
                if squeeze_indicator.iloc[i] == 1:
                    consecutive_squeeze += 1
                else:
                    break
            
            # Squeeze strength (based on band width percentile)
            current_percentile = band_width_percentile.iloc[-1]
            squeeze_strength = 1.0 - current_percentile if current_percentile else 0.5
            
            # Squeeze duration analysis
            squeeze_duration_score = 0.0
            if consecutive_squeeze >= self.min_squeeze_periods:
                # Optimal squeeze duration (not too short, not too long)
                if consecutive_squeeze <= 15:
                    squeeze_duration_score = consecutive_squeeze / 15.0
                elif consecutive_squeeze <= self.max_squeeze_periods:
                    squeeze_duration_score = 1.0 - ((consecutive_squeeze - 15) / (self.max_squeeze_periods - 15)) * 0.5
                else:
                    squeeze_duration_score = 0.5  # Very long squeezes are less reliable
            
            # Band width trend (is volatility still contracting?)
            if len(band_width) >= 5:
                recent_band_widths = band_width.iloc[-5:]
                band_width_trend = 'contracting' if recent_band_widths.iloc[-1] < recent_band_widths.iloc[0] else 'expanding'
            else:
                band_width_trend = 'neutral'
            
            # Historical squeeze performance
            squeeze_quality = self._assess_squeeze_quality(bands_data)
            
            return {
                'in_squeeze': current_squeeze,
                'consecutive_periods': consecutive_squeeze,
                'squeeze_strength': squeeze_strength,
                'duration_score': squeeze_duration_score,
                'band_width_trend': band_width_trend,
                'current_band_width': band_width.iloc[-1],
                'band_width_percentile': current_percentile,
                'squeeze_quality': squeeze_quality,
                'ready_for_breakout': (consecutive_squeeze >= self.min_squeeze_periods and 
                                     squeeze_strength > 0.3 and 
                                     band_width_trend == 'expanding')
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing squeeze conditions: {e}")
            return {'in_squeeze': False, 'squeeze_strength': 0.0}
    
    def _assess_squeeze_quality(self, bands_data: Dict[str, pd.Series]) -> float:
        """
        Assess the quality of the current squeeze based on historical patterns.
        """
        try:
            squeeze_indicator = bands_data['squeeze_indicator']
            band_width = bands_data['band_width']
            
            if len(squeeze_indicator) < 50:
                return 0.5  # Default quality
            
            # Find recent squeeze periods
            squeeze_periods = []
            current_period = 0
            
            for i in range(len(squeeze_indicator)):
                if squeeze_indicator.iloc[i] == 1:
                    current_period += 1
                else:
                    if current_period > 0:
                        squeeze_periods.append(current_period)
                        current_period = 0
            
            if current_period > 0:
                squeeze_periods.append(current_period)
            
            # Quality factors
            quality_score = 0.5
            
            # Factor 1: Squeeze duration distribution
            if squeeze_periods:
                avg_duration = np.mean(squeeze_periods)
                if 5 <= avg_duration <= 20:  # Optimal range
                    quality_score += 0.2
            
            # Factor 2: Band width consistency during squeezes
            recent_squeezes = squeeze_indicator.iloc[-50:]
            if recent_squeezes.sum() > 10:  # Enough squeeze data
                squeeze_band_widths = band_width.iloc[-50:][recent_squeezes == 1]
                if len(squeeze_band_widths) > 5:
                    width_consistency = 1.0 - squeeze_band_widths.std() / squeeze_band_widths.mean()
                    quality_score += width_consistency * 0.2
            
            # Factor 3: Recent performance (if available)
            if hasattr(self, 'squeeze_state') and self.squeeze_state:
                success_rate = 0.5
                if (self.squeeze_state['successful_breakouts'] + self.squeeze_state['false_breakouts']) > 0:
                    success_rate = (self.squeeze_state['successful_breakouts'] / 
                                  (self.squeeze_state['successful_breakouts'] + self.squeeze_state['false_breakouts']))
                quality_score += (success_rate - 0.5) * 0.3
            
            return max(0.1, min(1.0, quality_score))
            
        except Exception as e:
            self.logger.warning(f"Error assessing squeeze quality: {e}")
            return 0.5
    
    def _detect_breakout_signal(self, data: pd.DataFrame, bands_data: Dict[str, pd.Series], 
                               squeeze_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Detect breakout signals from squeeze conditions.
        """
        try:
            if not squeeze_analysis.get('ready_for_breakout', False):
                return None
            
            close = data['close']
            bb_upper = bands_data['bb_upper']
            bb_lower = bands_data['bb_lower']
            
            if len(close) < 3:
                return None
            
            current_price = close.iloc[-1]
            prev_price = close.iloc[-2]
            
            current_bb_upper = bb_upper.iloc[-1]
            current_bb_lower = bb_lower.iloc[-1]
            prev_bb_upper = bb_upper.iloc[-2]
            prev_bb_lower = bb_lower.iloc[-2]
            
            # Detect breakouts
            bullish_breakout = (prev_price <= prev_bb_upper and current_price > current_bb_upper)
            bearish_breakout = (prev_price >= prev_bb_lower and current_price < current_bb_lower)
            
            if not (bullish_breakout or bearish_breakout):
                return None
            
            # Calculate breakout strength
            if bullish_breakout:
                breakout_distance = (current_price - current_bb_upper) / current_bb_upper
                direction = 'bullish'
            else:
                breakout_distance = (current_bb_lower - current_price) / current_bb_lower
                direction = 'bearish'
            
            # Normalize breakout strength
            breakout_strength = min(breakout_distance * 100, 1.0)  # Cap at 1.0
            
            # Check breakout persistence (has it been sustained?)
            persistence_periods = 0
            for i in range(len(close) - 1, max(0, len(close) - 5), -1):
                if direction == 'bullish' and close.iloc[i] > bb_upper.iloc[i]:
                    persistence_periods += 1
                elif direction == 'bearish' and close.iloc[i] < bb_lower.iloc[i]:
                    persistence_periods += 1
                else:
                    break
            
            persistence_score = min(persistence_periods / 3.0, 1.0)
            
            return {
                'direction': direction,
                'strength': breakout_strength,
                'persistence': persistence_score,
                'breakout_distance': breakout_distance,
                'squeeze_duration': squeeze_analysis.get('consecutive_periods', 0),
                'squeeze_strength': squeeze_analysis.get('squeeze_strength', 0.0)
            }
            
        except Exception as e:
            self.logger.warning(f"Error detecting breakout signal: {e}")
            return None
    
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
                if 30 <= current_rsi <= 70:  # Not overbought/oversold
                    confirmations.append(1)
                elif current_rsi > 70 or current_rsi < 30:
                    confirmations.append(-0.5)  # Slight negative
                else:
                    confirmations.append(0)
            
            # MACD confirmation
            macd_data = self.momentum_indicators.macd(close)
            if macd_data and len(macd_data['macd']) > 1:
                macd_line = macd_data['macd']
                signal_line = macd_data['signal']
                
                if macd_line.iloc[-1] > signal_line.iloc[-1]:
                    confirmations.append(1)  # Bullish MACD
                else:
                    confirmations.append(-1)  # Bearish MACD
            
            # Volume momentum
            if len(volume) >= 10:
                volume_ma = volume.rolling(10).mean()
                current_volume = volume.iloc[-1]
                
                if current_volume > volume_ma.iloc[-1] * 1.2:
                    confirmations.append(1)  # High volume
                elif current_volume < volume_ma.iloc[-1] * 0.8:
                    confirmations.append(-0.5)  # Low volume
                else:
                    confirmations.append(0)  # Normal volume
            
            # Calculate confirmation multiplier
            if confirmations:
                avg_confirmation = np.mean(confirmations)
                # Convert to multiplier (0.7 to 1.3)
                return max(0.7, min(1.3, 1.0 + (avg_confirmation * 0.3)))
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error getting momentum confirmation: {e}")
            return 1.0
    
    def _check_false_breakout(self, data: pd.DataFrame, bands_data: Dict[str, pd.Series]) -> bool:
        """
        Check if the current breakout might be a false breakout.
        """
        try:
            if len(data) < 10:
                return False
            
            close = data['close']
            volume = data['volume']
            bb_upper = bands_data['bb_upper']
            bb_lower = bands_data['bb_lower']
            
            # Check for recent failed breakouts
            failed_breakouts = 0
            for i in range(max(1, len(close) - 10), len(close) - 1):
                if i <= 0:
                    continue
                
                # Check if price broke out but then reversed
                if (close.iloc[i] > bb_upper.iloc[i] and close.iloc[i+1] <= bb_upper.iloc[i+1]) or \
                   (close.iloc[i] < bb_lower.iloc[i] and close.iloc[i+1] >= bb_lower.iloc[i+1]):
                    failed_breakouts += 1
            
            if failed_breakouts >= 2:  # Too many recent failed breakouts
                return True
            
            # Check volume confirmation
            current_volume = volume.iloc[-1]
            avg_volume = volume.rolling(20).mean().iloc[-1]
            
            if current_volume < avg_volume * 0.8:  # Low volume breakout
                return True
            
            # Check if breakout is too small
            current_price = close.iloc[-1]
            bb_middle = bands_data['bb_middle'].iloc[-1]
            
            breakout_distance = abs(current_price - bb_middle) / bb_middle
            if breakout_distance < 0.005:  # Less than 0.5% from middle
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking false breakout: {e}")
            return False
    
    def _analyze_breakout_volume(self, data: pd.DataFrame) -> float:
        """
        Analyze volume confirmation for breakouts.
        """
        try:
            if len(data) < 20:
                return 1.0
            
            volume = data['volume']
            current_volume = volume.iloc[-1]
            
            # Compare to different averages
            volume_ma_5 = volume.rolling(5).mean().iloc[-1]
            volume_ma_20 = volume.rolling(20).mean().iloc[-1]
            
            # Volume confirmation score
            if current_volume > volume_ma_20 * self.breakout_volume_threshold:
                confirmation = 1.3  # Strong volume confirmation
            elif current_volume > volume_ma_5 * 1.2:
                confirmation = 1.1  # Moderate volume confirmation
            elif current_volume < volume_ma_20 * 0.7:
                confirmation = 0.7  # Weak volume
            else:
                confirmation = 1.0  # Normal volume
            
            return min(confirmation, 1.5)  # Cap at 1.5x
            
        except Exception as e:
            self.logger.warning(f"Error analyzing breakout volume: {e}")
            return 1.0
    
    def _get_multi_timeframe_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get multi-timeframe confirmation (simplified version).
        """
        try:
            # This is a simplified version - in practice, you'd analyze multiple timeframes
            if len(data) < 50:
                return 1.0
            
            close = data['close']
            
            # Check longer-term trend
            sma_50 = close.rolling(50).mean()
            current_price = close.iloc[-1]
            
            if current_price > sma_50.iloc[-1]:
                return 1.1  # Bullish longer-term trend
            else:
                return 0.9  # Bearish longer-term trend
                
        except Exception as e:
            self.logger.warning(f"Error getting multi-timeframe confirmation: {e}")
            return 1.0
    
    def _determine_primary_squeeze_signal(self, squeeze_analysis: Dict[str, Any], 
                                        breakout_signal: Optional[Dict[str, Any]],
                                        momentum_confirmation: float, volume_confirmation: float,
                                        mtf_confirmation: float) -> Dict[str, Any]:
        """
        Determine the primary squeeze breakout signal.
        """
        try:
            # No signal during squeeze or without breakout
            if not breakout_signal:
                return {
                    'signal_type': SignalType.NEUTRAL,
                    'raw_value': 0.0,
                    'confidence': 0.2,
                    'strength': 0.1,
                    'source': 'no_breakout'
                }
            
            # Calculate signal strength
            base_strength = breakout_signal['strength']
            persistence_bonus = breakout_signal['persistence'] * 0.3
            squeeze_quality_bonus = squeeze_analysis.get('squeeze_quality', 0.5) * 0.2
            
            signal_strength = (base_strength + persistence_bonus + squeeze_quality_bonus) * \
                            momentum_confirmation * volume_confirmation * mtf_confirmation
            
            # Determine signal type and confidence
            direction = breakout_signal['direction']
            squeeze_duration = breakout_signal.get('squeeze_duration', 0)
            
            # Confidence based on squeeze quality and confirmations
            base_confidence = 0.6
            if squeeze_duration >= self.min_squeeze_periods:
                base_confidence += 0.1
            if breakout_signal['persistence'] > 0.5:
                base_confidence += 0.1
            if volume_confirmation > 1.2:
                base_confidence += 0.1
            
            confidence = min(base_confidence, 0.9)
            
            # Determine signal type
            if direction == 'bullish':
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
            self.logger.warning(f"Error determining primary squeeze signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_squeeze_state(self, squeeze_analysis: Dict[str, Any], 
                            breakout_signal: Optional[Dict[str, Any]], is_false_breakout: bool) -> None:
        """
        Update internal squeeze state tracking.
        """
        try:
            # Update squeeze status
            self.squeeze_state['in_squeeze'] = squeeze_analysis.get('in_squeeze', False)
            self.squeeze_state['squeeze_periods'] = squeeze_analysis.get('consecutive_periods', 0)
            
            # Track squeeze start/end
            if self.squeeze_state['in_squeeze'] and self.squeeze_state['squeeze_start'] is None:
                self.squeeze_state['squeeze_start'] = datetime.now()
            elif not self.squeeze_state['in_squeeze']:
                self.squeeze_state['squeeze_start'] = None
            
            # Track breakouts
            if breakout_signal:
                self.squeeze_state['last_breakout'] = datetime.now()
                self.squeeze_state['breakout_direction'] = breakout_signal['direction']
                
                if is_false_breakout:
                    self.squeeze_state['false_breakouts'] += 1
                else:
                    self.squeeze_state['successful_breakouts'] += 1
            
            # Update band width history (keep last 100)
            current_band_width = squeeze_analysis.get('current_band_width', 0.0)
            self.squeeze_state['band_width_history'].append(current_band_width)
            if len(self.squeeze_state['band_width_history']) > 100:
                self.squeeze_state['band_width_history'].pop(0)
            
        except Exception as e:
            self.logger.warning(f"Error updating squeeze state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using squeeze analysis.
        
        Risk Logic:
        1. Position sizing based on squeeze quality and breakout strength
        2. Stop loss using band levels and ATR
        3. Take profit at multiple levels based on historical breakout moves
        4. Trailing stop based on band expansion
        """
        try:
            current_price = data['close'].iloc[-1]
            bands_data = signal.metadata.get('bands_data', {})
            breakout_signal = signal.metadata.get('breakout_signal')
            squeeze_analysis = signal.metadata.get('squeeze_analysis', {})
            
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
            
            # Adjust position size based on squeeze quality and breakout strength
            squeeze_quality = squeeze_analysis.get('squeeze_quality', 0.5)
            breakout_strength = breakout_signal.get('strength', 0.5) if breakout_signal else 0.5
            
            quality_multiplier = 0.7 + (squeeze_quality * 0.3)  # 0.7x to 1.0x
            strength_multiplier = 0.8 + (breakout_strength * 0.4)  # 0.8x to 1.2x
            
            position_size = base_position * quality_multiplier * strength_multiplier
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss and take profit calculation
            bb_upper = bands_data.get('bb_upper', current_price * 1.02)
            bb_lower = bands_data.get('bb_lower', current_price * 0.98)
            bb_middle = bands_data.get('bb_middle', current_price)
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions - stop below lower band or middle band
                stop_loss_price = min(bb_lower, current_price - (atr * 2))
                # Take profit at upper band extension
                band_width = bb_upper - bb_lower
                take_profit_price = current_price + (band_width * 1.5)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions - stop above upper band or middle band
                stop_loss_price = max(bb_upper, current_price + (atr * 2))
                # Take profit at lower band extension
                band_width = bb_upper - bb_lower
                take_profit_price = current_price - (band_width * 1.5)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using band expansion
            trailing_stop_distance = max(atr * 1.5, (bb_upper - bb_lower) * 0.3)
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=self.config.get('max_position_size', 5000),
                account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
                volatility_adjustment=strength_multiplier,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime using volatility analysis.
        
        Regime Logic:
        1. Squeeze periods indicate low volatility
        2. Breakout periods indicate high volatility
        3. Band width percentiles for relative volatility
        4. Volume patterns for market participation
        """
        try:
            if len(data) < 50:
                return MarketRegime.UNKNOWN
            
            bands_data = self._calculate_bands_indicators(data)
            if not bands_data:
                return MarketRegime.UNKNOWN
            
            squeeze_analysis = self._analyze_squeeze_conditions(bands_data)
            
            # Current volatility state
            band_width_percentile = bands_data['band_width_percentile'].iloc[-1]
            in_squeeze = squeeze_analysis.get('in_squeeze', False)
            
            # Volume analysis
            volume = data['volume']
            volume_ma = volume.rolling(20).mean()
            current_volume_ratio = volume.iloc[-1] / volume_ma.iloc[-1]
            
            # Price trend analysis
            close = data['close']
            sma_20 = close.rolling(20).mean()
            sma_50 = close.rolling(50).mean()
            
            # Determine regime
            if in_squeeze or band_width_percentile < 0.2:
                return MarketRegime.LOW_VOLATILITY
            elif band_width_percentile > 0.8:
                return MarketRegime.HIGH_VOLATILITY
            elif close.iloc[-1] > sma_20.iloc[-1] > sma_50.iloc[-1]:
                return MarketRegime.TRENDING_UP
            elif close.iloc[-1] < sma_20.iloc[-1] < sma_50.iloc[-1]:
                return MarketRegime.TRENDING_DOWN
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on squeeze breakout signals.
        
        Execution Logic:
        1. Strong breakouts get immediate market orders
        2. Weak breakouts get limit orders near bands
        3. High-quality squeezes get TWAP execution
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
            
            # Determine execution parameters based on signal strength and source
            breakout_signal = signal.metadata.get('breakout_signal')
            squeeze_analysis = signal.metadata.get('squeeze_analysis', {})
            
            squeeze_quality = squeeze_analysis.get('squeeze_quality', 0.5)
            breakout_strength = breakout_signal.get('strength', 0.5) if breakout_signal else 0.5
            
            if signal.signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH]:
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif squeeze_quality > 0.7 and breakout_strength > 0.6:
                algorithm = ExecutionAlgorithm.TWAP
                urgency = ExecutionUrgency.MEDIUM
            elif signal.strength > 0.5:
                algorithm = ExecutionAlgorithm.VWAP
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
                    'strategy': 'Bollinger_Squeeze',
                    'signal_confidence': signal.confidence,
                    'squeeze_quality': squeeze_quality,
                    'breakout_strength': breakout_strength,
                    'squeeze_state': signal.metadata.get('squeeze_state'),
                    'bands_data': signal.metadata.get('bands_data'),
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
        1. Squeeze-specific performance metrics
        2. Breakout success rates
        3. False breakout analysis
        """
        try:
            if execution_result.get('status') == 'filled':
                pnl = execution_result.get('pnl', 0.0)
                squeeze_quality = execution_result.get('metadata', {}).get('squeeze_quality', 0.5)
                breakout_strength = execution_result.get('metadata', {}).get('breakout_strength', 0.5)
                
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
                    if hasattr(self, 'squeeze_state'):
                        self.squeeze_state['successful_breakouts'] += 1
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
                    f"Bollinger Squeeze Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Squeeze Quality: {squeeze_quality:.2f}, "
                    f"Breakout Strength: {breakout_strength:.2f}, "
                    f"In Squeeze: {self.squeeze_state['in_squeeze']}, "
                    f"Squeeze Periods: {self.squeeze_state['squeeze_periods']}, "
                    f"Successful Breakouts: {self.squeeze_state['successful_breakouts']}, "
                    f"False Breakouts: {self.squeeze_state['false_breakouts']}"
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