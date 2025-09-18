"""Rate of Change (ROC) Momentum Strategy - Institutional Grade Implementation

This strategy implements a sophisticated Rate of Change momentum system
with institutional-grade enhancements and multi-period analysis.

Core Logic:
- Uses multiple ROC periods for comprehensive momentum analysis
- Volume-weighted ROC calculations for institutional flow confirmation
- Momentum divergence detection for reversal signals
- Adaptive thresholds based on market volatility
- Cross-asset momentum correlation analysis

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
from ..indicators.traditional.momentum_indicators import MomentumIndicators
from ..indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ..indicators.traditional.volatility_indicators import VolatilityIndicators
from ..risk_management_utils import RiskManagementUtils
from ..execution_intent_utils import ExecutionIntentUtils


class ROCMomentumStrategy(BaseInstitutionalStrategy):
    """
    Rate of Change Momentum Strategy implementing the 5-Pillar Architecture.
    
    This strategy uses multiple ROC periods to identify momentum shifts
    and generate high-probability trading signals with institutional enhancements.
    """
    
    def __init__(self, config_path: str, symbol: str, timeframe: str = "1D"):
        super().__init__(config_path, symbol, timeframe)
        
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        self.momentum_indicators = MomentumIndicators()
        self.volume_indicators = VolumeWeightedIndicators()
        self.volatility_indicators = VolatilityIndicators()
        self.risk_utils = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        # Strategy-specific parameters from config
        self.roc_periods = self.config.get('roc_periods', [5, 10, 20, 50])  # Multiple ROC periods
        self.primary_roc_period = self.config.get('primary_roc_period', 20)
        self.momentum_threshold = self.config.get('momentum_threshold', 0.02)  # 2% threshold
        self.strong_momentum_threshold = self.config.get('strong_momentum_threshold', 0.05)  # 5% threshold
        self.volume_confirmation_period = self.config.get('volume_confirmation_period', 20)
        self.divergence_lookback = self.config.get('divergence_lookback', 10)
        self.adaptive_thresholds = self.config.get('adaptive_thresholds', True)
        self.cross_period_confirmation = self.config.get('cross_period_confirmation', True)
        
        # ROC state tracking
        self.roc_history = {period: [] for period in self.roc_periods}
        self.momentum_state = {
            'current_momentum': 0.0,
            'momentum_direction': 'neutral',
            'momentum_strength': 0.0,
            'divergence_detected': False
        }
        
        self.logger.info(f"ROC Momentum Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using multi-period ROC analysis.
        
        Signal Logic:
        1. Calculate ROC for multiple periods
        2. Identify momentum acceleration/deceleration
        3. Volume-weighted momentum confirmation
        4. Momentum divergence detection
        5. Cross-period momentum alignment
        """
        try:
            if len(data) < max(self.roc_periods) + 10:
                return self._create_neutral_signal("Insufficient data for ROC calculation")
            
            # Calculate multi-period ROC values
            roc_values = self._calculate_multi_period_roc(data)
            
            if not roc_values:
                return self._create_neutral_signal("ROC calculation failed")
            
            # Get primary ROC for main signal
            primary_roc = roc_values[self.primary_roc_period]
            current_roc = primary_roc.iloc[-1]
            prev_roc = primary_roc.iloc[-2] if len(primary_roc) > 1 else 0
            
            # Calculate ROC momentum (rate of change of ROC)
            roc_momentum = current_roc - prev_roc
            
            # Volume-weighted ROC confirmation
            vw_roc = self._calculate_volume_weighted_roc(data, self.primary_roc_period)
            volume_confirmation = self._get_volume_confirmation(current_roc, vw_roc)
            
            # Cross-period momentum analysis
            cross_period_signal = self._analyze_cross_period_momentum(roc_values)
            
            # Momentum divergence detection
            divergence_signal = self._detect_momentum_divergence(data, primary_roc)
            
            # Adaptive threshold calculation
            adaptive_threshold = self._calculate_adaptive_threshold(data) if self.adaptive_thresholds else self.momentum_threshold
            strong_threshold = adaptive_threshold * 2.5
            
            # Determine signal type and strength
            signal_type, base_confidence, strength = self._determine_roc_signal(
                current_roc, roc_momentum, adaptive_threshold, strong_threshold
            )
            
            # Apply confirmations and adjustments
            confidence = base_confidence * volume_confirmation * cross_period_signal['confidence']
            
            # Divergence adjustment
            if divergence_signal['detected']:
                if divergence_signal['type'] == 'bullish':
                    if signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                        confidence *= 0.5  # Reduce bearish confidence on bullish divergence
                    elif signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                        confidence *= 1.3  # Enhance bullish confidence
                elif divergence_signal['type'] == 'bearish':
                    if signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                        confidence *= 0.5  # Reduce bullish confidence on bearish divergence
                    elif signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                        confidence *= 1.3  # Enhance bearish confidence
            
            confidence = max(0.1, min(1.0, confidence))
            
            # Update momentum state
            self._update_momentum_state(current_roc, roc_momentum, divergence_signal)
            
            # Create metadata
            metadata = {
                'primary_roc': current_roc,
                'roc_momentum': roc_momentum,
                'adaptive_threshold': adaptive_threshold,
                'volume_confirmation': volume_confirmation,
                'cross_period_signal': cross_period_signal,
                'divergence_signal': divergence_signal,
                'roc_values': {str(k): v.iloc[-1] for k, v in roc_values.items()},
                'momentum_state': self.momentum_state.copy(),
                'price': data['close'].iloc[-1]
            }
            
            return IndicatorSignal(
                raw_value=current_roc,
                signal_type=signal_type,
                confidence=confidence,
                strength=strength,
                timeframe=self.timeframe,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error generating ROC momentum signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_multi_period_roc(self, data: pd.DataFrame) -> Dict[int, pd.Series]:
        """
        Calculate ROC for multiple periods.
        
        ROC = ((Current Price - Price N periods ago) / Price N periods ago) * 100
        """
        try:
            roc_values = {}
            close_prices = data['close']
            
            for period in self.roc_periods:
                if len(close_prices) > period:
                    # Calculate ROC
                    roc = ((close_prices - close_prices.shift(period)) / close_prices.shift(period)) * 100
                    roc_values[period] = roc.fillna(0)
                    
                    # Update history for trend analysis
                    if len(self.roc_history[period]) > 100:  # Keep last 100 values
                        self.roc_history[period] = self.roc_history[period][-99:]
                    
                    if not roc.empty:
                        self.roc_history[period].append(roc.iloc[-1])
            
            return roc_values
            
        except Exception as e:
            self.logger.error(f"Error calculating multi-period ROC: {e}")
            return {}
    
    def _calculate_volume_weighted_roc(self, data: pd.DataFrame, period: int) -> float:
        """
        Calculate volume-weighted ROC for institutional flow confirmation.
        """
        try:
            if len(data) <= period:
                return 0.0
            
            # Calculate volume-weighted average price for current and past periods
            current_vwap = (data['close'] * data['volume']).iloc[-period:].sum() / data['volume'].iloc[-period:].sum()
            past_vwap = (data['close'] * data['volume']).iloc[-period*2:-period].sum() / data['volume'].iloc[-period*2:-period].sum()
            
            if past_vwap == 0:
                return 0.0
            
            vw_roc = ((current_vwap - past_vwap) / past_vwap) * 100
            return vw_roc
            
        except Exception as e:
            self.logger.warning(f"Error calculating volume-weighted ROC: {e}")
            return 0.0
    
    def _get_volume_confirmation(self, price_roc: float, volume_roc: float) -> float:
        """
        Get volume confirmation factor based on price vs volume ROC alignment.
        """
        try:
            if abs(volume_roc) < 0.01:  # Very low volume ROC
                return 0.8
            
            # Check if price and volume ROC are aligned
            if (price_roc > 0 and volume_roc > 0) or (price_roc < 0 and volume_roc < 0):
                # Aligned - good confirmation
                alignment_strength = min(abs(volume_roc) / max(abs(price_roc), 0.01), 2.0)
                return min(1.0 + (alignment_strength * 0.2), 1.4)
            else:
                # Divergent - weak confirmation
                return 0.7
                
        except Exception as e:
            self.logger.warning(f"Error calculating volume confirmation: {e}")
            return 1.0
    
    def _analyze_cross_period_momentum(self, roc_values: Dict[int, pd.Series]) -> Dict[str, Any]:
        """
        Analyze momentum across different periods for confirmation.
        """
        try:
            if not self.cross_period_confirmation or len(roc_values) < 2:
                return {'signal': 'neutral', 'confidence': 1.0, 'alignment': 0.5}
            
            # Get current ROC values for all periods
            current_rocs = {period: roc.iloc[-1] for period, roc in roc_values.items() if not roc.empty}
            
            if len(current_rocs) < 2:
                return {'signal': 'neutral', 'confidence': 1.0, 'alignment': 0.5}
            
            # Analyze momentum alignment
            positive_count = sum(1 for roc in current_rocs.values() if roc > 0)
            negative_count = sum(1 for roc in current_rocs.values() if roc < 0)
            total_count = len(current_rocs)
            
            alignment_ratio = max(positive_count, negative_count) / total_count
            
            # Determine cross-period signal
            if alignment_ratio >= 0.75:  # Strong alignment
                if positive_count > negative_count:
                    signal = 'bullish'
                    confidence = 1.0 + (alignment_ratio - 0.75) * 0.8  # Up to 1.2x
                else:
                    signal = 'bearish'
                    confidence = 1.0 + (alignment_ratio - 0.75) * 0.8
            elif alignment_ratio >= 0.6:  # Moderate alignment
                if positive_count > negative_count:
                    signal = 'weak_bullish'
                    confidence = 1.0
                else:
                    signal = 'weak_bearish'
                    confidence = 1.0
            else:  # Poor alignment
                signal = 'neutral'
                confidence = 0.8
            
            # Calculate momentum strength gradient (short vs long term)
            short_term_avg = np.mean([roc for period, roc in current_rocs.items() if period <= 20])
            long_term_avg = np.mean([roc for period, roc in current_rocs.items() if period > 20])
            
            gradient = short_term_avg - long_term_avg if long_term_avg != 0 else 0
            
            return {
                'signal': signal,
                'confidence': min(confidence, 1.4),
                'alignment': alignment_ratio,
                'gradient': gradient,
                'short_term_avg': short_term_avg,
                'long_term_avg': long_term_avg
            }
            
        except Exception as e:
            self.logger.warning(f"Error analyzing cross-period momentum: {e}")
            return {'signal': 'neutral', 'confidence': 1.0, 'alignment': 0.5}
    
    def _detect_momentum_divergence(self, data: pd.DataFrame, roc_series: pd.Series) -> Dict[str, Any]:
        """
        Detect momentum divergence between price and ROC.
        """
        try:
            if len(data) < self.divergence_lookback * 2 or len(roc_series) < self.divergence_lookback * 2:
                return {'detected': False, 'type': None, 'strength': 0.0}
            
            # Get recent price and ROC data
            recent_prices = data['close'].iloc[-self.divergence_lookback:]
            recent_roc = roc_series.iloc[-self.divergence_lookback:]
            
            # Calculate price trend (linear regression slope)
            price_x = np.arange(len(recent_prices))
            price_slope = np.polyfit(price_x, recent_prices.values, 1)[0]
            
            # Calculate ROC trend
            roc_x = np.arange(len(recent_roc))
            roc_slope = np.polyfit(roc_x, recent_roc.values, 1)[0]
            
            # Normalize slopes for comparison
            price_trend = 1 if price_slope > 0 else -1 if price_slope < 0 else 0
            roc_trend = 1 if roc_slope > 0 else -1 if roc_slope < 0 else 0
            
            # Detect divergence
            if price_trend != roc_trend and price_trend != 0 and roc_trend != 0:
                if price_trend > 0 and roc_trend < 0:
                    # Price up, momentum down = bearish divergence
                    divergence_type = 'bearish'
                elif price_trend < 0 and roc_trend > 0:
                    # Price down, momentum up = bullish divergence
                    divergence_type = 'bullish'
                else:
                    return {'detected': False, 'type': None, 'strength': 0.0}
                
                # Calculate divergence strength
                strength = min(abs(price_slope) * abs(roc_slope) * 1000, 1.0)
                
                return {
                    'detected': True,
                    'type': divergence_type,
                    'strength': strength,
                    'price_slope': price_slope,
                    'roc_slope': roc_slope
                }
            
            return {'detected': False, 'type': None, 'strength': 0.0}
            
        except Exception as e:
            self.logger.warning(f"Error detecting momentum divergence: {e}")
            return {'detected': False, 'type': None, 'strength': 0.0}
    
    def _calculate_adaptive_threshold(self, data: pd.DataFrame) -> float:
        """
        Calculate adaptive ROC threshold based on recent volatility.
        """
        try:
            # Calculate recent volatility
            returns = data['close'].pct_change().iloc[-20:]
            current_vol = returns.std()
            
            # Calculate longer-term volatility
            long_returns = data['close'].pct_change().iloc[-60:]
            long_vol = long_returns.std()
            
            if long_vol == 0:
                return self.momentum_threshold
            
            # Adjust threshold based on volatility regime
            vol_ratio = current_vol / long_vol
            
            # Scale base threshold by volatility
            base_threshold = self.momentum_threshold
            
            if vol_ratio > 1.5:  # High volatility
                adaptive_threshold = base_threshold * (1 + (vol_ratio - 1) * 0.5)
            elif vol_ratio < 0.7:  # Low volatility
                adaptive_threshold = base_threshold * vol_ratio
            else:
                adaptive_threshold = base_threshold
            
            # Ensure reasonable bounds
            return max(0.005, min(adaptive_threshold, 0.1))  # 0.5% to 10%
            
        except Exception as e:
            self.logger.warning(f"Error calculating adaptive threshold: {e}")
            return self.momentum_threshold
    
    def _determine_roc_signal(self, current_roc: float, roc_momentum: float, 
                             threshold: float, strong_threshold: float) -> tuple:
        """
        Determine signal type based on ROC values and momentum.
        """
        try:
            # Strong signals
            if current_roc > strong_threshold and roc_momentum > 0:
                return SignalType.STRONG_BULLISH, 0.9, min(abs(current_roc) / strong_threshold, 1.0)
            elif current_roc < -strong_threshold and roc_momentum < 0:
                return SignalType.STRONG_BEARISH, 0.9, min(abs(current_roc) / strong_threshold, 1.0)
            
            # Regular signals
            elif current_roc > threshold:
                confidence = 0.7 if roc_momentum > 0 else 0.5
                strength = min(abs(current_roc) / strong_threshold, 0.8)
                return SignalType.BULLISH, confidence, strength
            elif current_roc < -threshold:
                confidence = 0.7 if roc_momentum < 0 else 0.5
                strength = min(abs(current_roc) / strong_threshold, 0.8)
                return SignalType.BEARISH, confidence, strength
            
            # Weak signals
            elif current_roc > threshold * 0.5:
                return SignalType.WEAK_BULLISH, 0.4, min(abs(current_roc) / threshold, 0.6)
            elif current_roc < -threshold * 0.5:
                return SignalType.WEAK_BEARISH, 0.4, min(abs(current_roc) / threshold, 0.6)
            
            # Neutral
            else:
                return SignalType.NEUTRAL, 0.2, 0.1
                
        except Exception as e:
            self.logger.warning(f"Error determining ROC signal: {e}")
            return SignalType.NEUTRAL, 0.2, 0.1
    
    def _update_momentum_state(self, current_roc: float, roc_momentum: float, 
                              divergence_signal: Dict[str, Any]) -> None:
        """
        Update internal momentum state tracking.
        """
        try:
            self.momentum_state['current_momentum'] = current_roc
            self.momentum_state['momentum_strength'] = abs(current_roc)
            
            if current_roc > self.momentum_threshold:
                self.momentum_state['momentum_direction'] = 'bullish'
            elif current_roc < -self.momentum_threshold:
                self.momentum_state['momentum_direction'] = 'bearish'
            else:
                self.momentum_state['momentum_direction'] = 'neutral'
            
            self.momentum_state['divergence_detected'] = divergence_signal.get('detected', False)
            
        except Exception as e:
            self.logger.warning(f"Error updating momentum state: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters.
        
        Risk Logic:
        1. Position size based on momentum strength
        2. Stop loss based on recent volatility
        3. Take profit based on momentum target
        4. Trailing stop using ROC momentum
        """
        try:
            current_price = data['close'].iloc[-1]
            current_roc = signal.metadata.get('primary_roc', 0.0)
            momentum_strength = abs(current_roc)
            
            account_risk_pct = self.config.get('account_risk_percentage', 0.02)
            base_position_size = self.config.get('base_position_size', 1000)
            
            # Position sizing based on momentum strength and confidence
            momentum_multiplier = 0.5 + (momentum_strength / self.strong_momentum_threshold)
            confidence_multiplier = 0.5 + signal.confidence
            
            position_size = base_position_size * momentum_multiplier * confidence_multiplier
            
            max_position = self.config.get('max_position_size', 5000)
            position_size = min(position_size, max_position)
            
            # Calculate volatility-based stop loss
            returns = data['close'].pct_change().iloc[-20:]
            volatility = returns.std()
            
            # Stop loss distance based on volatility and momentum
            base_stop_distance = volatility * 2.0  # 2 standard deviations
            momentum_adjustment = 1.0 + (momentum_strength * 0.5)  # Wider stops for strong momentum
            stop_distance = base_stop_distance * momentum_adjustment
            
            # Calculate stop loss price
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH, SignalType.WEAK_BULLISH]:
                stop_loss_price = current_price * (1 - stop_distance)
                # Take profit based on momentum target
                tp_multiplier = 2.0 + signal.strength  # 2x to 3x risk/reward
                take_profit_price = current_price * (1 + (stop_distance * tp_multiplier))
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH, SignalType.WEAK_BEARISH]:
                stop_loss_price = current_price * (1 + stop_distance)
                tp_multiplier = 2.0 + signal.strength
                take_profit_price = current_price * (1 - (stop_distance * tp_multiplier))
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop based on ROC momentum
            trailing_stop_distance = stop_distance * 0.7  # Tighter trailing
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=max_position,
                account_risk_percentage=account_risk_pct,
                volatility_adjustment=momentum_adjustment,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime for strategy adaptation.
        
        Regime Logic:
        1. Use multi-period ROC for regime identification
        2. Momentum consistency analysis
        3. Volatility regime detection
        """
        try:
            # Calculate multi-period ROC
            roc_values = self._calculate_multi_period_roc(data)
            
            if not roc_values:
                return MarketRegime.UNKNOWN
            
            # Analyze momentum across periods
            current_rocs = [roc.iloc[-1] for roc in roc_values.values() if not roc.empty]
            
            if not current_rocs:
                return MarketRegime.UNKNOWN
            
            # Calculate momentum statistics
            avg_momentum = np.mean(current_rocs)
            momentum_consistency = sum(1 for roc in current_rocs if np.sign(roc) == np.sign(avg_momentum)) / len(current_rocs)
            momentum_strength = np.mean([abs(roc) for roc in current_rocs])
            
            # Calculate volatility
            returns = data['close'].pct_change().iloc[-20:]
            current_vol = returns.std()
            avg_vol = data['close'].pct_change().iloc[-60:].std()
            
            # Determine regime
            if momentum_consistency > 0.8 and momentum_strength > self.strong_momentum_threshold:
                if avg_momentum > 0:
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            elif current_vol > avg_vol * 1.5:
                return MarketRegime.HIGH_VOLATILITY
            elif current_vol < avg_vol * 0.7:
                return MarketRegime.LOW_VOLATILITY
            elif momentum_consistency < 0.4:
                return MarketRegime.CHOPPY
            else:
                return MarketRegime.RANGING
                
        except Exception as e:
            self.logger.error(f"Error checking market regime: {e}")
            return MarketRegime.UNKNOWN
    
    def _determine_execution_intent(self, signal: IndicatorSignal, 
                                  risk_params: RiskParameters) -> Optional[ExecutionIntent]:
        """
        PILLAR 4: Determine execution intent based on signal and risk parameters.
        
        Execution Logic:
        1. Strong momentum gets aggressive execution
        2. Divergence signals get patient execution
        3. Cross-period alignment affects urgency
        """
        try:
            # Determine action based on signal
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH, SignalType.WEAK_BULLISH]:
                action = ExecutionAction.ENTER_LONG
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH, SignalType.WEAK_BEARISH]:
                action = ExecutionAction.ENTER_SHORT
            else:
                return None
            
            # Determine execution parameters
            momentum_strength = signal.metadata.get('momentum_state', {}).get('momentum_strength', 0.0)
            divergence_detected = signal.metadata.get('divergence_signal', {}).get('detected', False)
            cross_period_alignment = signal.metadata.get('cross_period_signal', {}).get('alignment', 0.5)
            
            if signal.signal_type in [SignalType.STRONG_BULLISH, SignalType.STRONG_BEARISH]:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            elif momentum_strength > self.momentum_threshold and cross_period_alignment > 0.7:
                algorithm = ExecutionAlgorithm.TWAP
                urgency = ExecutionUrgency.MEDIUM
            elif divergence_detected:
                algorithm = ExecutionAlgorithm.LIMIT
                urgency = ExecutionUrgency.LOW
            else:
                algorithm = ExecutionAlgorithm.LIMIT
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
                    'strategy': 'ROC_Momentum',
                    'signal_confidence': signal.confidence,
                    'momentum_strength': momentum_strength,
                    'divergence_detected': divergence_detected,
                    'cross_period_alignment': cross_period_alignment,
                    'primary_roc': signal.metadata.get('primary_roc'),
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
        1. ROC-specific performance metrics
        2. Momentum efficiency
        3. Divergence signal accuracy
        4. Multi-period analysis effectiveness
        """
        try:
            if execution_result.get('status') == 'filled':
                pnl = execution_result.get('pnl', 0.0)
                
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
                    f"ROC Momentum Performance - Trades: {self.performance_metrics.total_trades}, "
                    f"Win Rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total Return: {self.performance_metrics.total_return:.2f}"
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