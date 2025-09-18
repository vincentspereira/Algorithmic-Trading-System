"""Parabolic SAR Strategy - Institutional Grade Implementation

This strategy implements J. Welles Wilder's Parabolic Stop and Reverse (SAR) system
with institutional-grade enhancements and volume-weighted confirmations.

Core Logic:
- Uses Parabolic SAR for trend identification and stop loss placement
- Volume-weighted price confirmation for institutional flow
- Dynamic acceleration factor adjustment based on volatility
- Multi-timeframe SAR alignment for higher confidence
- Adaptive position sizing based on SAR distance

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
import json

from ..BaseInstitutionalStrategy import (
    BaseInstitutionalStrategy, IndicatorSignal, RiskParameters, ExecutionIntent,
    SignalType, MarketRegime, ExecutionAction, ExecutionAlgorithm, ExecutionUrgency, TimeInForce
)
from ..indicators.traditional.trend_indicators import TrendIndicators
from ..indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ..indicators.traditional.volatility_indicators import VolatilityIndicators
from ..risk_management_utils import RiskManagementUtils
from ..execution_intent_utils import ExecutionIntentUtils


class ParabolicSARStrategy(BaseInstitutionalStrategy):
    """
    Parabolic SAR Strategy implementing the 5-Pillar Architecture.
    
    This strategy uses the Parabolic SAR indicator for trend following
    with built-in stop loss functionality and institutional enhancements.
    """
    
    def __init__(self, config_path: str, symbol: str, timeframe: str = "1D"):
        super().__init__(config_path, symbol, timeframe)
        
    def _initialize_strategy(self) -> None:
        """Initialize strategy-specific components"""
        self.trend_indicators = TrendIndicators()
        self.volume_indicators = VolumeWeightedIndicators()
        self.volatility_indicators = VolatilityIndicators()
        self.risk_utils = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        # Strategy-specific parameters from config
        self.initial_af = self.config.get('sar_initial_af', 0.02)  # Initial acceleration factor
        self.max_af = self.config.get('sar_max_af', 0.20)  # Maximum acceleration factor
        self.af_increment = self.config.get('sar_af_increment', 0.02)  # AF increment
        self.volume_confirmation_period = self.config.get('volume_confirmation_period', 20)
        self.volatility_adjustment = self.config.get('volatility_adjustment', True)
        self.multi_timeframe = self.config.get('multi_timeframe_confirmation', True)
        
        # SAR state tracking
        self.sar_state = {
            'trend': None,  # 'up' or 'down'
            'af': self.initial_af,
            'ep': None,  # Extreme point
            'sar': None  # Current SAR value
        }
        
        self.logger.info(f"Parabolic SAR Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using Parabolic SAR.
        
        Signal Logic:
        1. SAR flip from above to below price = bullish signal
        2. SAR flip from below to above price = bearish signal
        3. Volume-weighted price confirmation
        4. Volatility-adjusted acceleration factor
        5. Multi-timeframe SAR alignment
        """
        try:
            if len(data) < 20:
                return self._create_neutral_signal("Insufficient data for SAR calculation")
            
            # Calculate Parabolic SAR
            sar_result = self._calculate_parabolic_sar(data)
            
            if sar_result is None:
                return self._create_neutral_signal("SAR calculation failed")
            
            current_price = data['close'].iloc[-1]
            current_sar = sar_result['sar'].iloc[-1]
            prev_sar = sar_result['sar'].iloc[-2] if len(sar_result) > 1 else current_sar
            
            # Determine current trend based on SAR position
            current_trend = 'up' if current_price > current_sar else 'down'
            prev_trend = 'up' if data['close'].iloc[-2] > prev_sar else 'down'
            
            # Detect SAR reversals (trend changes)
            sar_reversal = current_trend != prev_trend
            
            # Calculate SAR distance for signal strength
            sar_distance_pct = abs(current_price - current_sar) / current_price
            
            # Volume-weighted price confirmation
            vw_price = self.volume_indicators.vw_ema(
                data['close'], data['volume'], period=self.volume_confirmation_period
            )
            volume_confirmation = 1.0 if current_price > vw_price.iloc[-1] else 0.8
            
            # Multi-timeframe confirmation (simplified)
            mtf_confirmation = self._get_multi_timeframe_confirmation(data) if self.multi_timeframe else 1.0
            
            # Volatility adjustment for acceleration factor
            volatility_factor = self._calculate_volatility_adjustment(data)
            
            # Determine signal type and strength
            if sar_reversal and current_trend == 'up':
                # Bullish reversal
                if sar_distance_pct > 0.02:  # Strong reversal
                    signal_type = SignalType.STRONG_BULLISH
                    base_confidence = 0.8
                else:
                    signal_type = SignalType.BULLISH
                    base_confidence = 0.6
                
                strength = min(sar_distance_pct * 50, 1.0)  # Scale distance to strength
                raw_value = sar_distance_pct
                
            elif sar_reversal and current_trend == 'down':
                # Bearish reversal
                if sar_distance_pct > 0.02:
                    signal_type = SignalType.STRONG_BEARISH
                    base_confidence = 0.8
                else:
                    signal_type = SignalType.BEARISH
                    base_confidence = 0.6
                
                strength = min(sar_distance_pct * 50, 1.0)
                raw_value = -sar_distance_pct
                
            elif current_trend == 'up' and sar_distance_pct > 0.01:
                # Continuation of uptrend
                signal_type = SignalType.WEAK_BULLISH
                base_confidence = 0.4
                strength = min(sar_distance_pct * 25, 0.7)
                raw_value = sar_distance_pct * 0.5
                
            elif current_trend == 'down' and sar_distance_pct > 0.01:
                # Continuation of downtrend
                signal_type = SignalType.WEAK_BEARISH
                base_confidence = 0.4
                strength = min(sar_distance_pct * 25, 0.7)
                raw_value = -sar_distance_pct * 0.5
                
            else:
                # No clear signal
                signal_type = SignalType.NEUTRAL
                base_confidence = 0.2
                strength = 0.1
                raw_value = 0.0
            
            # Apply confirmations
            confidence = base_confidence * volume_confirmation * mtf_confirmation * volatility_factor
            confidence = max(0.1, min(1.0, confidence))
            
            # Create metadata
            metadata = {
                'sar_value': current_sar,
                'sar_distance_pct': sar_distance_pct,
                'current_trend': current_trend,
                'sar_reversal': sar_reversal,
                'volume_confirmation': volume_confirmation,
                'mtf_confirmation': mtf_confirmation,
                'volatility_factor': volatility_factor,
                'acceleration_factor': self.sar_state['af'],
                'price': current_price
            }
            
            return IndicatorSignal(
                raw_value=raw_value,
                signal_type=signal_type,
                confidence=confidence,
                strength=strength,
                timeframe=self.timeframe,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error generating Parabolic SAR signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_parabolic_sar(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Calculate Parabolic SAR with dynamic acceleration factor.
        
        This is a simplified implementation. In production, you might want to use
        TA-Lib's SAR function or implement the full algorithm.
        """
        try:
            # Use TA-Lib if available, otherwise implement basic version
            try:
                import talib
                sar_values = talib.SAR(
                    data['high'].values, 
                    data['low'].values, 
                    acceleration=self.initial_af, 
                    maximum=self.max_af
                )
                
                return pd.DataFrame({
                    'sar': sar_values
                }, index=data.index)
                
            except ImportError:
                # Fallback implementation
                return self._calculate_sar_fallback(data)
                
        except Exception as e:
            self.logger.error(f"Error calculating Parabolic SAR: {e}")
            return None
    
    def _calculate_sar_fallback(self, data: pd.DataFrame) -> pd.DataFrame:
        """Fallback SAR calculation if TA-Lib is not available"""
        try:
            high = data['high'].values
            low = data['low'].values
            close = data['close'].values
            
            sar = np.zeros(len(data))
            trend = np.zeros(len(data))
            af = np.full(len(data), self.initial_af)
            ep = np.zeros(len(data))
            
            # Initialize
            sar[0] = low[0]
            trend[0] = 1  # 1 for up, -1 for down
            ep[0] = high[0]
            
            for i in range(1, len(data)):
                # Previous values
                prev_sar = sar[i-1]
                prev_trend = trend[i-1]
                prev_af = af[i-1]
                prev_ep = ep[i-1]
                
                # Calculate new SAR
                sar[i] = prev_sar + prev_af * (prev_ep - prev_sar)
                
                # Check for trend reversal
                if prev_trend == 1:  # Uptrend
                    if low[i] <= sar[i]:
                        # Trend reversal to downtrend
                        trend[i] = -1
                        sar[i] = prev_ep
                        ep[i] = low[i]
                        af[i] = self.initial_af
                    else:
                        # Continue uptrend
                        trend[i] = 1
                        if high[i] > prev_ep:
                            ep[i] = high[i]
                            af[i] = min(prev_af + self.af_increment, self.max_af)
                        else:
                            ep[i] = prev_ep
                            af[i] = prev_af
                        
                        # SAR cannot be above previous two lows
                        sar[i] = min(sar[i], low[i-1])
                        if i > 1:
                            sar[i] = min(sar[i], low[i-2])
                
                else:  # Downtrend
                    if high[i] >= sar[i]:
                        # Trend reversal to uptrend
                        trend[i] = 1
                        sar[i] = prev_ep
                        ep[i] = high[i]
                        af[i] = self.initial_af
                    else:
                        # Continue downtrend
                        trend[i] = -1
                        if low[i] < prev_ep:
                            ep[i] = low[i]
                            af[i] = min(prev_af + self.af_increment, self.max_af)
                        else:
                            ep[i] = prev_ep
                            af[i] = prev_af
                        
                        # SAR cannot be below previous two highs
                        sar[i] = max(sar[i], high[i-1])
                        if i > 1:
                            sar[i] = max(sar[i], high[i-2])
            
            return pd.DataFrame({
                'sar': sar,
                'trend': trend,
                'af': af,
                'ep': ep
            }, index=data.index)
            
        except Exception as e:
            self.logger.error(f"Error in SAR fallback calculation: {e}")
            return pd.DataFrame({'sar': [data['close'].iloc[-1]] * len(data)}, index=data.index)
    
    def _get_multi_timeframe_confirmation(self, data: pd.DataFrame) -> float:
        """Get multi-timeframe SAR confirmation (simplified)"""
        try:
            # This is a simplified version - in practice, you'd analyze higher timeframes
            # For now, we'll use a longer period SAR as proxy for higher timeframe
            
            if len(data) < 50:
                return 1.0
            
            # Calculate SAR with different parameters (proxy for higher timeframe)
            longer_sar = self._calculate_parabolic_sar(data.iloc[-50:])
            
            if longer_sar is None:
                return 1.0
            
            current_price = data['close'].iloc[-1]
            longer_sar_value = longer_sar['sar'].iloc[-1]
            
            # Check if both timeframes agree on trend direction
            short_trend = 'up' if current_price > self._calculate_parabolic_sar(data.iloc[-20:])['sar'].iloc[-1] else 'down'
            long_trend = 'up' if current_price > longer_sar_value else 'down'
            
            return 1.2 if short_trend == long_trend else 0.8
            
        except Exception as e:
            self.logger.warning(f"Error in multi-timeframe confirmation: {e}")
            return 1.0
    
    def _calculate_volatility_adjustment(self, data: pd.DataFrame) -> float:
        """Calculate volatility adjustment factor for SAR parameters"""
        try:
            if not self.volatility_adjustment:
                return 1.0
            
            # Calculate recent volatility
            returns = data['close'].pct_change().iloc[-20:]
            current_vol = returns.std()
            
            # Calculate longer-term volatility
            long_returns = data['close'].pct_change().iloc[-60:]
            long_vol = long_returns.std()
            
            if long_vol == 0:
                return 1.0
            
            # Volatility ratio
            vol_ratio = current_vol / long_vol
            
            # Adjust confidence based on volatility regime
            if vol_ratio > 1.5:  # High volatility
                return 0.8  # Reduce confidence
            elif vol_ratio < 0.7:  # Low volatility
                return 1.1  # Increase confidence
            else:
                return 1.0
                
        except Exception as e:
            self.logger.warning(f"Error calculating volatility adjustment: {e}")
            return 1.0
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters.
        
        Risk Logic:
        1. Use SAR value as natural stop loss
        2. Position size based on SAR distance
        3. Dynamic take profit based on trend strength
        4. Trailing stop using SAR updates
        """
        try:
            current_price = data['close'].iloc[-1]
            sar_value = signal.metadata.get('sar_value', current_price)
            sar_distance_pct = signal.metadata.get('sar_distance_pct', 0.02)
            
            account_risk_pct = self.config.get('account_risk_percentage', 0.02)
            base_position_size = self.config.get('base_position_size', 1000)
            
            # Position sizing based on SAR distance (risk per share)
            risk_per_share = abs(current_price - sar_value)
            account_value = self.config.get('account_value', 100000)
            max_risk_amount = account_value * account_risk_pct
            
            # Calculate position size based on risk
            if risk_per_share > 0:
                risk_based_size = max_risk_amount / risk_per_share
            else:
                risk_based_size = base_position_size
            
            # Apply signal strength multiplier
            strength_multiplier = 0.5 + (signal.strength * 1.5)
            position_size = min(risk_based_size * strength_multiplier, base_position_size * 2)
            
            max_position = self.config.get('max_position_size', 5000)
            position_size = min(position_size, max_position)
            
            # Stop loss is the SAR value
            stop_loss_price = sar_value
            
            # Take profit based on SAR distance and trend strength
            tp_multiplier = 2.0 + signal.strength  # 2x to 3x risk/reward
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH, SignalType.WEAK_BULLISH]:
                take_profit_price = current_price + (risk_per_share * tp_multiplier)
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH, SignalType.WEAK_BEARISH]:
                take_profit_price = current_price - (risk_per_share * tp_multiplier)
            else:
                take_profit_price = None
            
            # Trailing stop distance (SAR naturally trails)
            trailing_stop_distance = risk_per_share
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=max_position,
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
        1. Use SAR trend consistency for regime identification
        2. Volatility analysis for market conditions
        3. Trend strength based on SAR distance
        """
        try:
            # Calculate SAR for regime analysis
            sar_result = self._calculate_parabolic_sar(data)
            
            if sar_result is None:
                return MarketRegime.UNKNOWN
            
            current_price = data['close'].iloc[-1]
            current_sar = sar_result['sar'].iloc[-1]
            
            # Analyze recent trend consistency
            recent_prices = data['close'].iloc[-10:]
            recent_sars = sar_result['sar'].iloc[-10:]
            
            # Count trend consistency
            trend_consistency = sum(1 for p, s in zip(recent_prices, recent_sars) 
                                  if (p > s) == (current_price > current_sar)) / len(recent_prices)
            
            # Calculate volatility
            returns = data['close'].pct_change().iloc[-20:]
            current_vol = returns.std()
            avg_vol = data['close'].pct_change().iloc[-60:].std()
            
            # SAR distance for trend strength
            sar_distance_pct = abs(current_price - current_sar) / current_price
            
            # Determine regime
            if trend_consistency > 0.8 and sar_distance_pct > 0.02:
                if current_price > current_sar:
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            elif current_vol > avg_vol * 1.5:
                return MarketRegime.HIGH_VOLATILITY
            elif current_vol < avg_vol * 0.7:
                return MarketRegime.LOW_VOLATILITY
            elif trend_consistency < 0.4:
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
        1. SAR reversals get immediate execution
        2. Trend continuations get patient execution
        3. Strong trends get VWAP execution
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
            sar_reversal = signal.metadata.get('sar_reversal', False)
            sar_distance_pct = signal.metadata.get('sar_distance_pct', 0.01)
            
            if sar_reversal and signal.strength > 0.6:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            elif sar_distance_pct > 0.02:
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
                    'strategy': 'Parabolic_SAR',
                    'signal_confidence': signal.confidence,
                    'sar_reversal': sar_reversal,
                    'sar_value': signal.metadata.get('sar_value'),
                    'sar_distance': sar_distance_pct,
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
        1. SAR-specific performance metrics
        2. Trend following efficiency
        3. Stop loss effectiveness
        4. Risk-adjusted returns
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
                    f"Parabolic SAR Performance - Trades: {self.performance_metrics.total_trades}, "
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