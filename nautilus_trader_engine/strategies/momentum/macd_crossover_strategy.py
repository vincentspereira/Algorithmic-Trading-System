"""MACD Crossover Strategy - Institutional Grade Implementation

This strategy implements a sophisticated MACD-based momentum approach with volume-weighted
enhancements and institutional-grade risk management.

Core Logic:
- Uses MACD line and signal line crossovers for entry/exit signals
- Volume-weighted MACD for institutional flow confirmation
- Histogram analysis for momentum strength assessment
- Dynamic position sizing based on momentum strength
- Market regime adaptation to avoid false signals

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
import json

from ...core.base_institutional_strategy import (
    BaseInstitutionalStrategy, IndicatorSignal, RiskParameters, ExecutionIntent,
    SignalType, MarketRegime, ExecutionAction, ExecutionAlgorithm, ExecutionUrgency, TimeInForce
)
from ...indicators.traditional.momentum_indicators import MomentumIndicators
from ...indicators.volume_weighted.volume_weighted_indicators import VolumeWeightedIndicators
from ...indicators.traditional.volatility_indicators import VolatilityIndicators
from ...utils.risk_management_utils import RiskManagementUtils
from ...utils.execution_intent_utils import ExecutionIntentUtils


class MACDCrossoverStrategy(BaseInstitutionalStrategy):
    """
    MACD Crossover Strategy implementing the 5-Pillar Architecture.
    
    This strategy capitalizes on momentum shifts identified by MACD crossovers,
    with volume-weighted confirmation and institutional-grade risk management.
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
        self.fast_period = self.config.get('macd_fast_period', 12)
        self.slow_period = self.config.get('macd_slow_period', 26)
        self.signal_period = self.config.get('macd_signal_period', 9)
        self.histogram_threshold = self.config.get('histogram_threshold', 0.001)
        self.volume_confirmation_period = self.config.get('volume_confirmation_period', 20)
        self.divergence_lookback = self.config.get('divergence_lookback', 10)
        
        # Track previous values for crossover detection
        self.prev_macd = None
        self.prev_signal = None
        self.prev_histogram = None
        
        self.logger.info(f"MACD Crossover Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using MACD crossovers and volume confirmation.
        
        Signal Logic:
        1. MACD line crossing above signal line = bullish signal
        2. MACD line crossing below signal line = bearish signal
        3. Histogram analysis for momentum strength
        4. Volume-weighted MACD for institutional confirmation
        5. Divergence analysis for signal quality
        """
        try:
            # Calculate traditional MACD
            macd_result = self.momentum_indicators.macd(
                data['close'], 
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                signal_period=self.signal_period
            )
            
            if macd_result is None or len(macd_result) < 2:
                return self._create_neutral_signal("Insufficient MACD data")
            
            current_macd = macd_result['macd'].iloc[-1]
            current_signal = macd_result['signal'].iloc[-1]
            current_histogram = macd_result['histogram'].iloc[-1]
            
            prev_macd = macd_result['macd'].iloc[-2]
            prev_signal = macd_result['signal'].iloc[-2]
            prev_histogram = macd_result['histogram'].iloc[-2]
            
            # Calculate volume-weighted MACD for confirmation
            vw_macd_result = self.volume_indicators.vw_macd(
                data['close'], data['volume'],
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                signal_period=self.signal_period
            )
            
            vw_confirmation = 1.0
            if vw_macd_result is not None:
                vw_macd = vw_macd_result['macd'].iloc[-1]
                vw_signal = vw_macd_result['signal'].iloc[-1]
                # Volume confirmation: both traditional and VW MACD should agree
                vw_confirmation = 1.0 if np.sign(current_macd - current_signal) == np.sign(vw_macd - vw_signal) else 0.7
            
            # Detect crossovers
            bullish_crossover = (prev_macd <= prev_signal) and (current_macd > current_signal)
            bearish_crossover = (prev_macd >= prev_signal) and (current_macd < current_signal)
            
            # Calculate momentum strength from histogram
            histogram_strength = abs(current_histogram) / (data['close'].iloc[-1] * 0.01)  # Normalize by 1% of price
            histogram_strength = min(histogram_strength, 1.0)  # Cap at 1.0
            
            # Analyze histogram trend for momentum confirmation
            histogram_trend = 1.0 if current_histogram > prev_histogram else -1.0
            histogram_acceleration = abs(current_histogram - prev_histogram) / max(abs(prev_histogram), 0.0001)
            
            # Check for divergences (price vs MACD)
            divergence_factor = self._check_divergence(data, macd_result)
            
            # Determine signal type and strength
            if bullish_crossover:
                if current_histogram > self.histogram_threshold:
                    signal_type = SignalType.STRONG_BULLISH
                    base_confidence = 0.8
                else:
                    signal_type = SignalType.BULLISH
                    base_confidence = 0.6
                
                strength = histogram_strength * (1.0 + histogram_acceleration * 0.5)
                raw_value = (current_macd - current_signal) / data['close'].iloc[-1]
                
            elif bearish_crossover:
                if current_histogram < -self.histogram_threshold:
                    signal_type = SignalType.STRONG_BEARISH
                    base_confidence = 0.8
                else:
                    signal_type = SignalType.BEARISH
                    base_confidence = 0.6
                
                strength = histogram_strength * (1.0 + histogram_acceleration * 0.5)
                raw_value = (current_macd - current_signal) / data['close'].iloc[-1]
                
            else:
                # No crossover - check for continuation signals
                if abs(current_histogram) > self.histogram_threshold:
                    if current_histogram > 0 and histogram_trend > 0:
                        signal_type = SignalType.WEAK_BULLISH
                        base_confidence = 0.4
                    elif current_histogram < 0 and histogram_trend < 0:
                        signal_type = SignalType.WEAK_BEARISH
                        base_confidence = 0.4
                    else:
                        signal_type = SignalType.NEUTRAL
                        base_confidence = 0.2
                else:
                    signal_type = SignalType.NEUTRAL
                    base_confidence = 0.2
                
                strength = histogram_strength * 0.5  # Lower strength for continuation
                raw_value = current_histogram / data['close'].iloc[-1]
            
            # Apply adjustments
            confidence = base_confidence * vw_confirmation * divergence_factor
            confidence = max(0.1, min(1.0, confidence))  # Clamp between 0.1 and 1.0
            
            # Create metadata
            metadata = {
                'macd': current_macd,
                'signal': current_signal,
                'histogram': current_histogram,
                'histogram_strength': histogram_strength,
                'histogram_trend': histogram_trend,
                'volume_confirmation': vw_confirmation,
                'divergence_factor': divergence_factor,
                'bullish_crossover': bullish_crossover,
                'bearish_crossover': bearish_crossover,
                'price': data['close'].iloc[-1]
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
            self.logger.error(f"Error generating MACD signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _check_divergence(self, data: pd.DataFrame, macd_result: pd.DataFrame) -> float:
        """
        Check for bullish/bearish divergences between price and MACD.
        Returns a factor between 0.5 (negative divergence) and 1.5 (positive divergence)
        """
        try:
            if len(data) < self.divergence_lookback or len(macd_result) < self.divergence_lookback:
                return 1.0
            
            # Get recent price and MACD data
            recent_prices = data['close'].iloc[-self.divergence_lookback:]
            recent_macd = macd_result['macd'].iloc[-self.divergence_lookback:]
            
            # Calculate price trend (linear regression slope)
            price_x = np.arange(len(recent_prices))
            price_slope = np.polyfit(price_x, recent_prices, 1)[0]
            
            # Calculate MACD trend
            macd_slope = np.polyfit(price_x, recent_macd, 1)[0]
            
            # Normalize slopes
            price_trend = np.sign(price_slope)
            macd_trend = np.sign(macd_slope)
            
            # Check for divergence
            if price_trend != macd_trend and abs(price_slope) > 0.001 and abs(macd_slope) > 0.001:
                # Divergence detected
                if price_trend > 0 and macd_trend < 0:
                    return 0.7  # Bearish divergence (price up, MACD down)
                elif price_trend < 0 and macd_trend > 0:
                    return 1.3  # Bullish divergence (price down, MACD up)
            
            # No significant divergence
            return 1.0
            
        except Exception as e:
            self.logger.warning(f"Error checking divergence: {e}")
            return 1.0
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters.
        
        Risk Logic:
        1. Position size based on MACD histogram strength
        2. ATR-based stop loss with momentum adjustment
        3. Dynamic take profit based on histogram momentum
        4. Volatility-adjusted position sizing
        """
        try:
            # Calculate ATR for volatility-based risk management
            atr_result = self.volatility_indicators.atr(
                data['high'], data['low'], data['close'], period=14
            )
            current_atr = atr_result.iloc[-1] if atr_result is not None else data['close'].iloc[-1] * 0.02
            
            current_price = data['close'].iloc[-1]
            account_risk_pct = self.config.get('account_risk_percentage', 0.02)
            base_position_size = self.config.get('base_position_size', 1000)
            
            # Adjust position size based on signal strength and histogram
            histogram_strength = signal.metadata.get('histogram_strength', 0.5)
            volume_confirmation = signal.metadata.get('volume_confirmation', 1.0)
            
            # Position sizing with momentum strength multiplier
            momentum_multiplier = 0.5 + (histogram_strength * 1.0) + (signal.strength * 0.5)
            momentum_multiplier = min(momentum_multiplier, 2.0)  # Cap at 2x
            
            volatility_adjustment = min(2.0, max(0.5, 20.0 / current_atr))  # Inverse volatility scaling
            
            position_size = base_position_size * momentum_multiplier * volume_confirmation * volatility_adjustment
            max_position = self.config.get('max_position_size', 5000)
            position_size = min(position_size, max_position)
            
            # Stop loss calculation - tighter stops for stronger momentum
            stop_multiplier = 1.5 if histogram_strength > 0.7 else 2.0
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH, SignalType.WEAK_BULLISH]:
                stop_loss_price = current_price - (current_atr * stop_multiplier)
                # Dynamic take profit based on momentum strength
                tp_multiplier = 2.0 + (histogram_strength * 2.0)  # 2x to 4x R/R ratio
                take_profit_price = current_price + (current_atr * stop_multiplier * tp_multiplier)
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH, SignalType.WEAK_BEARISH]:
                stop_loss_price = current_price + (current_atr * stop_multiplier)
                tp_multiplier = 2.0 + (histogram_strength * 2.0)
                take_profit_price = current_price - (current_atr * stop_multiplier * tp_multiplier)
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop distance based on ATR and momentum
            trailing_stop_distance = current_atr * (1.0 + histogram_strength)
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=max_position,
                account_risk_percentage=account_risk_pct,
                volatility_adjustment=volatility_adjustment,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime for strategy adaptation.
        
        Regime Logic:
        1. Use MACD histogram for momentum regime identification
        2. Volatility analysis for high/low vol regimes
        3. Trend strength analysis
        """
        try:
            # Calculate MACD for regime identification
            macd_result = self.momentum_indicators.macd(
                data['close'],
                fast_period=self.fast_period,
                slow_period=self.slow_period,
                signal_period=self.signal_period
            )
            
            if macd_result is None:
                return MarketRegime.UNKNOWN
            
            current_histogram = macd_result['histogram'].iloc[-1]
            recent_histograms = macd_result['histogram'].iloc[-10:]
            
            # Calculate volatility regime
            atr_result = self.volatility_indicators.atr(
                data['high'], data['low'], data['close'], period=20
            )
            current_atr = atr_result.iloc[-1] if atr_result is not None else 0.02
            avg_atr = atr_result.rolling(50).mean().iloc[-1] if atr_result is not None else 0.02
            
            # Analyze momentum regime
            histogram_trend = recent_histograms.diff().mean()
            histogram_volatility = recent_histograms.std()
            
            # Determine regime
            if abs(current_histogram) > self.histogram_threshold * 2:
                if current_histogram > 0 and histogram_trend > 0:
                    return MarketRegime.TRENDING_UP
                elif current_histogram < 0 and histogram_trend < 0:
                    return MarketRegime.TRENDING_DOWN
                else:
                    return MarketRegime.HIGH_VOLATILITY
            elif histogram_volatility > self.histogram_threshold:
                if current_atr > avg_atr * 1.2:
                    return MarketRegime.CHOPPY
                else:
                    return MarketRegime.HIGH_VOLATILITY
            else:
                if current_atr < avg_atr * 0.8:
                    return MarketRegime.LOW_VOLATILITY
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
        1. Crossover signals get higher urgency
        2. Strong momentum gets VWAP execution
        3. Weak signals get TWAP execution
        """
        try:
            # Determine action based on signal
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH, SignalType.WEAK_BULLISH]:
                action = ExecutionAction.ENTER_LONG
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH, SignalType.WEAK_BEARISH]:
                action = ExecutionAction.ENTER_SHORT
            else:
                return None  # No action for neutral signals
            
            # Determine execution algorithm and urgency
            is_crossover = signal.metadata.get('bullish_crossover', False) or signal.metadata.get('bearish_crossover', False)
            histogram_strength = signal.metadata.get('histogram_strength', 0.5)
            
            if is_crossover and signal.strength > 0.7:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            elif signal.strength > 0.5:
                algorithm = ExecutionAlgorithm.TWAP
                urgency = ExecutionUrgency.MEDIUM
            else:
                algorithm = ExecutionAlgorithm.LIMIT
                urgency = ExecutionUrgency.LOW
            
            # Create execution intent
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
                    'strategy': 'MACD_Crossover',
                    'signal_confidence': signal.confidence,
                    'signal_strength': signal.strength,
                    'histogram': signal.metadata.get('histogram'),
                    'crossover': is_crossover,
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
        1. Win rate and profit factor
        2. MACD-specific metrics (crossover success rate)
        3. Risk-adjusted returns
        4. Execution quality metrics
        """
        try:
            # Update basic performance metrics
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
                
                # Calculate win rate
                if self.performance_metrics.total_trades > 0:
                    self.performance_metrics.win_rate = (
                        self.performance_metrics.winning_trades / self.performance_metrics.total_trades
                    )
                
                # Calculate profit factor
                if self.performance_metrics.losing_trades > 0 and self.performance_metrics.average_loss > 0:
                    total_wins = self.performance_metrics.winning_trades * self.performance_metrics.average_win
                    total_losses = self.performance_metrics.losing_trades * self.performance_metrics.average_loss
                    self.performance_metrics.profit_factor = total_wins / total_losses
                
                # Track MACD-specific metrics
                is_crossover = execution_result.get('metadata', {}).get('crossover', False)
                if is_crossover:
                    # Track crossover-specific performance
                    pass  # Can be extended with crossover-specific tracking
                
                self.logger.info(
                    f"MACD Performance updated - Total trades: {self.performance_metrics.total_trades}, "
                    f"Win rate: {self.performance_metrics.win_rate:.2%}, "
                    f"Total return: {self.performance_metrics.total_return:.2f}"
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