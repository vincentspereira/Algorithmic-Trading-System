"""Ichimoku Cloud Strategy - Institutional Grade Implementation

This strategy implements the Ichimoku Kinko Hyo (Equilibrium Chart) system
with institutional-grade enhancements and modern risk management.

Core Logic:
- Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
- Kijun-sen (Base Line): (26-period high + 26-period low) / 2
- Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, plotted 26 periods ahead
- Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, plotted 26 periods ahead
- Chikou Span (Lagging Span): Close price plotted 26 periods behind
- Kumo (Cloud): Area between Senkou Span A and B

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


class IchimokuCloudStrategy(BaseInstitutionalStrategy):
    """
    Ichimoku Cloud Strategy implementing the 5-Pillar Architecture.
    
    This strategy implements the complete Ichimoku system with modern
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
        
        # Ichimoku parameters from config
        self.tenkan_period = self.config.get('tenkan_period', 9)    # Conversion Line
        self.kijun_period = self.config.get('kijun_period', 26)     # Base Line
        self.senkou_b_period = self.config.get('senkou_b_period', 52)  # Leading Span B
        self.displacement = self.config.get('displacement', 26)      # Cloud displacement
        
        # Enhanced parameters
        self.volume_confirmation = self.config.get('volume_confirmation', True)
        self.multi_timeframe = self.config.get('multi_timeframe', True)
        self.cloud_thickness_filter = self.config.get('cloud_thickness_filter', True)
        self.chikou_confirmation = self.config.get('chikou_confirmation', True)
        
        # Signal strength thresholds
        self.strong_signal_threshold = self.config.get('strong_signal_threshold', 0.7)
        self.weak_signal_threshold = self.config.get('weak_signal_threshold', 0.3)
        
        # Ichimoku state tracking
        self.ichimoku_state = {
            'current_trend': 'neutral',
            'cloud_color': 'neutral',  # 'bullish', 'bearish', 'neutral'
            'price_vs_cloud': 'inside',  # 'above', 'below', 'inside'
            'tenkan_kijun_cross': None,
            'last_signal_time': None,
            'signal_strength': 0.0
        }
        
        self.logger.info(f"Ichimoku Cloud Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Ichimoku Cloud analysis.
        
        Signal Logic:
        1. Calculate all Ichimoku components
        2. Analyze price position relative to cloud
        3. Check Tenkan-sen/Kijun-sen crossovers
        4. Evaluate Chikou Span confirmation
        5. Apply volume and multi-timeframe filters
        """
        try:
            required_periods = max(self.senkou_b_period, self.displacement) + 10
            if len(data) < required_periods:
                return self._create_neutral_signal("Insufficient data for Ichimoku calculation")
            
            # Calculate Ichimoku components
            ichimoku_data = self._calculate_ichimoku_components(data)
            if ichimoku_data is None:
                return self._create_neutral_signal("Ichimoku calculation failed")
            
            current_price = data['close'].iloc[-1]
            
            # Analyze cloud characteristics
            cloud_analysis = self._analyze_cloud_characteristics(ichimoku_data, current_price)
            
            # Check Tenkan-Kijun crossover signals
            crossover_signal = self._check_tenkan_kijun_crossover(ichimoku_data)
            
            # Check price vs cloud signals
            cloud_breakout_signal = self._check_cloud_breakout(ichimoku_data, current_price)
            
            # Chikou Span confirmation
            chikou_confirmation = self._get_chikou_confirmation(data, ichimoku_data) if self.chikou_confirmation else 1.0
            
            # Volume confirmation
            volume_conf = self._get_volume_confirmation(data) if self.volume_confirmation else 1.0
            
            # Multi-timeframe confirmation
            mtf_confirmation = self._get_multi_timeframe_confirmation(data) if self.multi_timeframe else 1.0
            
            # Determine primary signal
            primary_signal = self._determine_primary_ichimoku_signal(
                crossover_signal, cloud_breakout_signal, cloud_analysis
            )
            
            # Apply confirmations
            primary_signal['confidence'] *= chikou_confirmation * volume_conf * mtf_confirmation
            primary_signal['confidence'] = max(0.1, min(1.0, primary_signal['confidence']))
            
            # Update Ichimoku state
            self._update_ichimoku_state(ichimoku_data, current_price, primary_signal)
            
            # Create metadata
            metadata = {
                'ichimoku_components': ichimoku_data,
                'cloud_analysis': cloud_analysis,
                'crossover_signal': crossover_signal,
                'cloud_breakout_signal': cloud_breakout_signal,
                'chikou_confirmation': chikou_confirmation,
                'volume_confirmation': volume_conf,
                'mtf_confirmation': mtf_confirmation,
                'ichimoku_state': self.ichimoku_state.copy(),
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
            self.logger.error(f"Error generating Ichimoku signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_ichimoku_components(self, data: pd.DataFrame) -> Optional[Dict[str, pd.Series]]:
        """
        Calculate all Ichimoku components.
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            
            # Tenkan-sen (Conversion Line)
            tenkan_high = high.rolling(window=self.tenkan_period).max()
            tenkan_low = low.rolling(window=self.tenkan_period).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2
            
            # Kijun-sen (Base Line)
            kijun_high = high.rolling(window=self.kijun_period).max()
            kijun_low = low.rolling(window=self.kijun_period).min()
            kijun_sen = (kijun_high + kijun_low) / 2
            
            # Senkou Span A (Leading Span A)
            senkou_span_a = (tenkan_sen + kijun_sen) / 2
            
            # Senkou Span B (Leading Span B)
            senkou_b_high = high.rolling(window=self.senkou_b_period).max()
            senkou_b_low = low.rolling(window=self.senkou_b_period).min()
            senkou_span_b = (senkou_b_high + senkou_b_low) / 2
            
            # Chikou Span (Lagging Span) - Close price shifted back
            chikou_span = close.shift(-self.displacement)
            
            # Cloud boundaries (for current analysis, we use non-displaced values)
            cloud_top = pd.concat([senkou_span_a, senkou_span_b], axis=1).max(axis=1)
            cloud_bottom = pd.concat([senkou_span_a, senkou_span_b], axis=1).min(axis=1)
            
            return {
                'tenkan_sen': tenkan_sen,
                'kijun_sen': kijun_sen,
                'senkou_span_a': senkou_span_a,
                'senkou_span_b': senkou_span_b,
                'chikou_span': chikou_span,
                'cloud_top': cloud_top,
                'cloud_bottom': cloud_bottom
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating Ichimoku components: {e}")
            return None
    
    def _analyze_cloud_characteristics(self, ichimoku_data: Dict[str, pd.Series], 
                                     current_price: float) -> Dict[str, Any]:
        """
        Analyze cloud characteristics and price position.
        """
        try:
            current_cloud_top = ichimoku_data['cloud_top'].iloc[-1]
            current_cloud_bottom = ichimoku_data['cloud_bottom'].iloc[-1]
            senkou_a = ichimoku_data['senkou_span_a'].iloc[-1]
            senkou_b = ichimoku_data['senkou_span_b'].iloc[-1]
            
            # Cloud thickness (relative to price)
            cloud_thickness = abs(current_cloud_top - current_cloud_bottom)
            thickness_ratio = cloud_thickness / current_price if current_price > 0 else 0
            
            # Cloud color (bullish if Senkou A > Senkou B)
            cloud_color = 'bullish' if senkou_a > senkou_b else 'bearish'
            
            # Price position relative to cloud
            if current_price > current_cloud_top:
                price_position = 'above'
                distance_from_cloud = (current_price - current_cloud_top) / current_price
            elif current_price < current_cloud_bottom:
                price_position = 'below'
                distance_from_cloud = (current_cloud_bottom - current_price) / current_price
            else:
                price_position = 'inside'
                distance_from_cloud = 0.0
            
            # Cloud trend (is cloud moving up or down?)
            if len(ichimoku_data['cloud_top']) >= 5:
                cloud_slope = (
                    ichimoku_data['cloud_top'].iloc[-1] - ichimoku_data['cloud_top'].iloc[-5]
                ) / 5
                cloud_trend = 'rising' if cloud_slope > 0 else 'falling' if cloud_slope < 0 else 'flat'
            else:
                cloud_trend = 'unknown'
            
            return {
                'cloud_color': cloud_color,
                'price_position': price_position,
                'distance_from_cloud': distance_from_cloud,
                'thickness_ratio': thickness_ratio,
                'cloud_trend': cloud_trend,
                'cloud_top': current_cloud_top,
                'cloud_bottom': current_cloud_bottom,
                'is_thick_cloud': thickness_ratio > 0.02  # 2% threshold
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing cloud characteristics: {e}")
            return {
                'cloud_color': 'neutral',
                'price_position': 'unknown',
                'distance_from_cloud': 0.0,
                'thickness_ratio': 0.0,
                'cloud_trend': 'unknown',
                'is_thick_cloud': False
            }
    
    def _check_tenkan_kijun_crossover(self, ichimoku_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Check for Tenkan-sen and Kijun-sen crossover signals.
        """
        try:
            tenkan = ichimoku_data['tenkan_sen']
            kijun = ichimoku_data['kijun_sen']
            
            if len(tenkan) < 3 or len(kijun) < 3:
                return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
            # Current and previous values
            tenkan_curr = tenkan.iloc[-1]
            tenkan_prev = tenkan.iloc[-2]
            kijun_curr = kijun.iloc[-1]
            kijun_prev = kijun.iloc[-2]
            
            # Check for crossover
            bullish_cross = (tenkan_prev <= kijun_prev) and (tenkan_curr > kijun_curr)
            bearish_cross = (tenkan_prev >= kijun_prev) and (tenkan_curr < kijun_curr)
            
            if bullish_cross:
                # Calculate crossover strength
                cross_magnitude = abs(tenkan_curr - kijun_curr) / kijun_curr if kijun_curr > 0 else 0
                return {
                    'type': 'bullish_cross',
                    'strength': min(cross_magnitude * 100, 1.0),
                    'confidence': 0.7,
                    'tenkan': tenkan_curr,
                    'kijun': kijun_curr
                }
            elif bearish_cross:
                cross_magnitude = abs(tenkan_curr - kijun_curr) / kijun_curr if kijun_curr > 0 else 0
                return {
                    'type': 'bearish_cross',
                    'strength': min(cross_magnitude * 100, 1.0),
                    'confidence': 0.7,
                    'tenkan': tenkan_curr,
                    'kijun': kijun_curr
                }
            else:
                # Check for trend continuation (both lines trending in same direction)
                tenkan_trend = tenkan_curr - tenkan_prev
                kijun_trend = kijun_curr - kijun_prev
                
                if tenkan_trend > 0 and kijun_trend > 0 and tenkan_curr > kijun_curr:
                    return {
                        'type': 'bullish_continuation',
                        'strength': 0.4,
                        'confidence': 0.5,
                        'tenkan': tenkan_curr,
                        'kijun': kijun_curr
                    }
                elif tenkan_trend < 0 and kijun_trend < 0 and tenkan_curr < kijun_curr:
                    return {
                        'type': 'bearish_continuation',
                        'strength': 0.4,
                        'confidence': 0.5,
                        'tenkan': tenkan_curr,
                        'kijun': kijun_curr
                    }
                else:
                    return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
        except Exception as e:
            self.logger.warning(f"Error checking Tenkan-Kijun crossover: {e}")
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
    
    def _check_cloud_breakout(self, ichimoku_data: Dict[str, pd.Series], 
                             current_price: float) -> Dict[str, Any]:
        """
        Check for cloud breakout signals.
        """
        try:
            cloud_top = ichimoku_data['cloud_top']
            cloud_bottom = ichimoku_data['cloud_bottom']
            
            if len(cloud_top) < 3 or len(cloud_bottom) < 3:
                return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
            
            current_top = cloud_top.iloc[-1]
            current_bottom = cloud_bottom.iloc[-1]
            prev_top = cloud_top.iloc[-2]
            prev_bottom = cloud_bottom.iloc[-2]
            
            # Check for breakouts
            if current_price > current_top and current_price <= prev_top:
                # Bullish breakout above cloud
                breakout_strength = (current_price - current_top) / current_top if current_top > 0 else 0
                return {
                    'type': 'bullish_breakout',
                    'strength': min(breakout_strength * 50, 1.0),
                    'confidence': 0.8,
                    'breakout_level': current_top
                }
            elif current_price < current_bottom and current_price >= prev_bottom:
                # Bearish breakout below cloud
                breakout_strength = (current_bottom - current_price) / current_bottom if current_bottom > 0 else 0
                return {
                    'type': 'bearish_breakout',
                    'strength': min(breakout_strength * 50, 1.0),
                    'confidence': 0.8,
                    'breakout_level': current_bottom
                }
            elif current_price > current_top:
                # Price above cloud (bullish territory)
                distance = (current_price - current_top) / current_price
                return {
                    'type': 'above_cloud',
                    'strength': min(distance * 10, 0.6),
                    'confidence': 0.6,
                    'distance': distance
                }
            elif current_price < current_bottom:
                # Price below cloud (bearish territory)
                distance = (current_bottom - current_price) / current_price
                return {
                    'type': 'below_cloud',
                    'strength': min(distance * 10, 0.6),
                    'confidence': 0.6,
                    'distance': distance
                }
            else:
                # Price inside cloud (neutral/consolidation)
                return {
                    'type': 'inside_cloud',
                    'strength': 0.1,
                    'confidence': 0.2
                }
            
        except Exception as e:
            self.logger.warning(f"Error checking cloud breakout: {e}")
            return {'type': 'none', 'strength': 0.0, 'confidence': 0.0}
    
    def _get_chikou_confirmation(self, data: pd.DataFrame, 
                                ichimoku_data: Dict[str, pd.Series]) -> float:
        """
        Get Chikou Span confirmation.
        
        Chikou Span should be above/below price from 26 periods ago for confirmation.
        """
        try:
            if len(data) < self.displacement + 5:
                return 1.0
            
            current_close = data['close'].iloc[-1]
            past_close = data['close'].iloc[-(self.displacement + 1)]
            
            # Chikou span is current close plotted 26 periods back
            # So we compare current close with price from 26 periods ago
            
            if current_close > past_close:
                # Bullish Chikou confirmation
                confirmation_strength = (current_close - past_close) / past_close if past_close > 0 else 0
                return min(1.0 + confirmation_strength, 1.3)
            elif current_close < past_close:
                # Bearish Chikou confirmation (for bearish signals)
                confirmation_strength = (past_close - current_close) / past_close if past_close > 0 else 0
                return min(1.0 + confirmation_strength, 1.3)
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating Chikou confirmation: {e}")
            return 1.0
    
    def _get_volume_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get volume confirmation for Ichimoku signals.
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
                return min(1.0 + (volume_ratio - 1.5) * 0.15, 1.3)
            # Weak volume
            elif volume_ratio < 0.7:
                return 0.85
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _get_multi_timeframe_confirmation(self, data: pd.DataFrame) -> float:
        """
        Get multi-timeframe confirmation by analyzing higher timeframe trend.
        
        This is a simplified version - in practice, you'd analyze actual higher timeframe data.
        """
        try:
            if len(data) < 100:
                return 1.0
            
            # Use longer-term moving averages as proxy for higher timeframe
            ma_50 = data['close'].rolling(50).mean().iloc[-1]
            ma_100 = data['close'].rolling(100).mean().iloc[-1]
            current_price = data['close'].iloc[-1]
            
            # Check alignment
            if current_price > ma_50 > ma_100:
                return 1.2  # Strong bullish alignment
            elif current_price < ma_50 < ma_100:
                return 1.2  # Strong bearish alignment
            elif current_price > ma_50 or current_price > ma_100:
                return 1.1  # Partial bullish alignment
            elif current_price < ma_50 or current_price < ma_100:
                return 1.1  # Partial bearish alignment
            else:
                return 0.9  # No clear alignment
                
        except Exception as e:
            self.logger.warning(f"Error calculating multi-timeframe confirmation: {e}")
            return 1.0
    
    def _determine_primary_ichimoku_signal(self, crossover_signal: Dict[str, Any], 
                                          cloud_signal: Dict[str, Any], 
                                          cloud_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine the primary Ichimoku signal from all components.
        """
        try:
            # Priority: Strong crossovers > Cloud breakouts > Trend continuation
            
            # Strong crossover signals
            if crossover_signal['type'] in ['bullish_cross', 'bearish_cross']:
                # Enhance signal if it aligns with cloud
                confidence_boost = 1.0
                if (crossover_signal['type'] == 'bullish_cross' and 
                    cloud_analysis['cloud_color'] == 'bullish' and 
                    cloud_analysis['price_position'] == 'above'):
                    confidence_boost = 1.3
                elif (crossover_signal['type'] == 'bearish_cross' and 
                      cloud_analysis['cloud_color'] == 'bearish' and 
                      cloud_analysis['price_position'] == 'below'):
                    confidence_boost = 1.3
                
                return {
                    'signal_type': SignalType.STRONG_BULLISH if crossover_signal['type'] == 'bullish_cross' else SignalType.STRONG_BEARISH,
                    'raw_value': crossover_signal['strength'] if crossover_signal['type'] == 'bullish_cross' else -crossover_signal['strength'],
                    'confidence': min(crossover_signal['confidence'] * confidence_boost, 1.0),
                    'strength': crossover_signal['strength'],
                    'source': 'tenkan_kijun_cross'
                }
            
            # Cloud breakout signals
            if cloud_signal['type'] in ['bullish_breakout', 'bearish_breakout']:
                # Enhance if cloud is thick (more significant)
                confidence_boost = 1.2 if cloud_analysis['is_thick_cloud'] else 1.0
                
                return {
                    'signal_type': SignalType.STRONG_BULLISH if cloud_signal['type'] == 'bullish_breakout' else SignalType.STRONG_BEARISH,
                    'raw_value': cloud_signal['strength'] if cloud_signal['type'] == 'bullish_breakout' else -cloud_signal['strength'],
                    'confidence': min(cloud_signal['confidence'] * confidence_boost, 1.0),
                    'strength': cloud_signal['strength'],
                    'source': 'cloud_breakout'
                }
            
            # Trend continuation signals
            if crossover_signal['type'] in ['bullish_continuation', 'bearish_continuation']:
                # Only if price is in favorable cloud position
                if ((crossover_signal['type'] == 'bullish_continuation' and 
                     cloud_analysis['price_position'] == 'above') or
                    (crossover_signal['type'] == 'bearish_continuation' and 
                     cloud_analysis['price_position'] == 'below')):
                    
                    return {
                        'signal_type': SignalType.BULLISH if crossover_signal['type'] == 'bullish_continuation' else SignalType.BEARISH,
                        'raw_value': crossover_signal['strength'] if crossover_signal['type'] == 'bullish_continuation' else -crossover_signal['strength'],
                        'confidence': crossover_signal['confidence'],
                        'strength': crossover_signal['strength'],
                        'source': 'trend_continuation'
                    }
            
            # Position-based signals (weaker)
            if cloud_signal['type'] in ['above_cloud', 'below_cloud']:
                return {
                    'signal_type': SignalType.BULLISH if cloud_signal['type'] == 'above_cloud' else SignalType.BEARISH,
                    'raw_value': cloud_signal['strength'] if cloud_signal['type'] == 'above_cloud' else -cloud_signal['strength'],
                    'confidence': cloud_signal['confidence'],
                    'strength': cloud_signal['strength'],
                    'source': 'cloud_position'
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
            self.logger.warning(f"Error determining primary Ichimoku signal: {e}")
            return {
                'signal_type': SignalType.NEUTRAL,
                'raw_value': 0.0,
                'confidence': 0.2,
                'strength': 0.1,
                'source': 'error'
            }
    
    def _update_ichimoku_state(self, ichimoku_data: Dict[str, pd.Series], 
                              current_price: float, signal: Dict[str, Any]) -> None:
        """
        Update internal Ichimoku state tracking.
        """
        try:
            # Update cloud color
            senkou_a = ichimoku_data['senkou_span_a'].iloc[-1]
            senkou_b = ichimoku_data['senkou_span_b'].iloc[-1]
            self.ichimoku_state['cloud_color'] = 'bullish' if senkou_a > senkou_b else 'bearish'
            
            # Update price vs cloud position
            cloud_top = ichimoku_data['cloud_top'].iloc[-1]
            cloud_bottom = ichimoku_data['cloud_bottom'].iloc[-1]
            
            if current_price > cloud_top:
                self.ichimoku_state['price_vs_cloud'] = 'above'
            elif current_price < cloud_bottom:
                self.ichimoku_state['price_vs_cloud'] = 'below'
            else:
                self.ichimoku_state['price_vs_cloud'] = 'inside'
            
            # Update trend
            if signal['signal_type'] in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                self.ichimoku_state['current_trend'] = 'bullish'
            elif signal['signal_type'] in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                self.ichimoku_state['current_trend'] = 'bearish'
            
            # Update signal strength and timing
            self.ichimoku_state['signal_strength'] = signal['strength']
            if signal['source'] != 'none':
                self.ichimoku_state['last_signal_time'] = datetime.now()
            
        except Exception as e:
            self.logger.warning(f"Error updating Ichimoku state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters using Ichimoku levels.
        
        Risk Logic:
        1. Use Kijun-sen as dynamic stop loss
        2. Position sizing based on cloud thickness
        3. Take profit at cloud boundaries
        4. Volatility-adjusted position sizing
        """
        try:
            current_price = data['close'].iloc[-1]
            ichimoku_data = signal.metadata.get('ichimoku_components', {})
            cloud_analysis = signal.metadata.get('cloud_analysis', {})
            
            if not ichimoku_data:
                return self._create_default_risk_parameters()
            
            kijun_sen = ichimoku_data['kijun_sen'].iloc[-1]
            cloud_top = ichimoku_data['cloud_top'].iloc[-1]
            cloud_bottom = ichimoku_data['cloud_bottom'].iloc[-1]
            
            # Base position size
            base_position = self.config.get('base_position_size', 1000)
            
            # Adjust position size based on cloud thickness (thicker cloud = more confidence)
            thickness_ratio = cloud_analysis.get('thickness_ratio', 0.01)
            thickness_multiplier = min(1.0 + thickness_ratio * 10, 1.5)  # Max 50% increase
            
            # Adjust for signal strength
            strength_multiplier = 0.5 + (signal.strength * 0.5)  # 0.5x to 1.0x based on strength
            
            position_size = base_position * thickness_multiplier * strength_multiplier
            position_size = min(position_size, self.config.get('max_position_size', 5000))
            
            # Stop loss calculation
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                # For long positions, use Kijun-sen or cloud bottom as stop
                stop_loss_price = min(kijun_sen, cloud_bottom)
                # Take profit at next cloud boundary or 2x risk
                risk_amount = current_price - stop_loss_price
                take_profit_price = current_price + (risk_amount * 2)
                
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                # For short positions, use Kijun-sen or cloud top as stop
                stop_loss_price = max(kijun_sen, cloud_top)
                # Take profit at next cloud boundary or 2x risk
                risk_amount = stop_loss_price - current_price
                take_profit_price = current_price - (risk_amount * 2)
                
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop using Kijun-sen
            trailing_stop_distance = abs(current_price - kijun_sen) if kijun_sen else None
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=self.config.get('max_position_size', 5000),
                account_risk_percentage=self.config.get('account_risk_percentage', 0.02),
                volatility_adjustment=thickness_multiplier,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime using Ichimoku analysis.
        
        Regime Logic:
        1. Cloud color and thickness for trend strength
        2. Price position relative to cloud
        3. Tenkan-Kijun relationship
        4. Overall trend consistency
        """
        try:
            if len(data) < max(self.senkou_b_period, self.displacement) + 10:
                return MarketRegime.UNKNOWN
            
            ichimoku_data = self._calculate_ichimoku_components(data)
            if not ichimoku_data:
                return MarketRegime.UNKNOWN
            
            current_price = data['close'].iloc[-1]
            cloud_analysis = self._analyze_cloud_characteristics(ichimoku_data, current_price)
            
            tenkan = ichimoku_data['tenkan_sen'].iloc[-1]
            kijun = ichimoku_data['kijun_sen'].iloc[-1]
            
            # Determine regime based on multiple factors
            if (cloud_analysis['cloud_color'] == 'bullish' and 
                cloud_analysis['price_position'] == 'above' and 
                tenkan > kijun and 
                cloud_analysis['is_thick_cloud']):
                return MarketRegime.TRENDING_UP
                
            elif (cloud_analysis['cloud_color'] == 'bearish' and 
                  cloud_analysis['price_position'] == 'below' and 
                  tenkan < kijun and 
                  cloud_analysis['is_thick_cloud']):
                return MarketRegime.TRENDING_DOWN
                
            elif cloud_analysis['price_position'] == 'inside':
                if cloud_analysis['is_thick_cloud']:
                    return MarketRegime.RANGING
                else:
                    return MarketRegime.LOW_VOLATILITY
                    
            elif not cloud_analysis['is_thick_cloud']:
                return MarketRegime.HIGH_VOLATILITY
                
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on Ichimoku signals.
        
        Execution Logic:
        1. Strong crossover signals get immediate execution
        2. Cloud breakouts get VWAP execution
        3. Trend continuation gets patient execution
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
            
            if signal_source == 'tenkan_kijun_cross':
                algorithm = ExecutionAlgorithm.MARKET
                urgency = ExecutionUrgency.HIGH
            elif signal_source == 'cloud_breakout':
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
                    'strategy': 'Ichimoku_Cloud',
                    'signal_confidence': signal.confidence,
                    'signal_source': signal_source,
                    'ichimoku_state': signal.metadata.get('ichimoku_state'),
                    'cloud_analysis': signal.metadata.get('cloud_analysis'),
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
        1. Ichimoku-specific performance metrics
        2. Signal source effectiveness
        3. Cloud-based performance analysis
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
                    f"Ichimoku Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}, "
                    f"Signal Source: {signal_source}, "
                    f"Cloud State: {self.ichimoku_state['cloud_color']}, "
                    f"Price Position: {self.ichimoku_state['price_vs_cloud']}"
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