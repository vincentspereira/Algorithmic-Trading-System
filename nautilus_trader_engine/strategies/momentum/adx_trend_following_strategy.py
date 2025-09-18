"""ADX Trend Following Strategy - Institutional Grade Implementation

This strategy implements a sophisticated trend-following approach using the Average Directional Index (ADX)
with volume-weighted enhancements and institutional-grade risk management.

Core Logic:
- Uses ADX to identify strong trending markets
- Combines with +DI/-DI for directional bias
- Volume-weighted confirmation for institutional flow
- Dynamic position sizing based on trend strength
- Market regime adaptation to avoid choppy conditions

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


class ADXTrendFollowingStrategy(BaseInstitutionalStrategy):
    """
    ADX Trend Following Strategy implementing the 5-Pillar Architecture.
    
    This strategy capitalizes on strong trending markets identified by ADX,
    with volume-weighted confirmation and institutional-grade risk management.
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
        self.adx_period = self.config.get('adx_period', 14)
        self.adx_threshold = self.config.get('adx_threshold', 25)
        self.strong_trend_threshold = self.config.get('strong_trend_threshold', 40)
        self.di_separation_threshold = self.config.get('di_separation_threshold', 5)
        self.volume_confirmation_period = self.config.get('volume_confirmation_period', 20)
        
        self.logger.info(f"ADX Trend Following Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using ADX and directional indicators.
        
        Signal Logic:
        1. ADX > threshold indicates trending market
        2. +DI > -DI suggests uptrend, -DI > +DI suggests downtrend
        3. Volume-weighted confirmation for institutional flow
        4. Multi-timeframe alignment for higher confidence
        """
        try:
            # Calculate ADX and directional indicators
            adx_result = self.trend_indicators.adx(
                data['high'], data['low'], data['close'], period=self.adx_period
            )
            
            if adx_result is None or len(adx_result) == 0:
                return self._create_neutral_signal("Insufficient ADX data")
            
            current_adx = adx_result['adx'].iloc[-1]
            current_plus_di = adx_result['plus_di'].iloc[-1]
            current_minus_di = adx_result['minus_di'].iloc[-1]
            
            # Volume-weighted price for confirmation
            vw_price = self.volume_indicators.vw_ema(
                data['close'], data['volume'], period=self.volume_confirmation_period
            )
            current_price = data['close'].iloc[-1]
            vw_price_current = vw_price.iloc[-1]
            
            # Calculate signal components
            trend_strength = min(current_adx / 100.0, 1.0)  # Normalize to 0-1
            di_separation = abs(current_plus_di - current_minus_di)
            
            # Determine signal type and direction
            if current_adx < self.adx_threshold:
                signal_type = SignalType.NEUTRAL
                confidence = 0.3
                strength = 0.2
                raw_value = 0.0
            elif current_plus_di > current_minus_di + self.di_separation_threshold:
                # Bullish trend signal
                signal_type = SignalType.STRONG_BULLISH if current_adx > self.strong_trend_threshold else SignalType.BULLISH
                confidence = min(0.6 + (trend_strength * 0.4), 1.0)
                strength = trend_strength
                raw_value = (current_plus_di - current_minus_di) / 100.0
            elif current_minus_di > current_plus_di + self.di_separation_threshold:
                # Bearish trend signal
                signal_type = SignalType.STRONG_BEARISH if current_adx > self.strong_trend_threshold else SignalType.BEARISH
                confidence = min(0.6 + (trend_strength * 0.4), 1.0)
                strength = trend_strength
                raw_value = -(current_minus_di - current_plus_di) / 100.0
            else:
                signal_type = SignalType.NEUTRAL
                confidence = 0.4
                strength = 0.3
                raw_value = 0.0
            
            # Volume confirmation adjustment
            volume_confirmation = 1.0 if current_price > vw_price_current else 0.8
            confidence *= volume_confirmation
            
            # Create metadata
            metadata = {
                'adx': current_adx,
                'plus_di': current_plus_di,
                'minus_di': current_minus_di,
                'di_separation': di_separation,
                'volume_confirmation': volume_confirmation,
                'trend_strength': trend_strength,
                'price': current_price,
                'vw_price': vw_price_current
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
            self.logger.error(f"Error generating ADX signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters.
        
        Risk Logic:
        1. Position size based on ADX strength and account risk
        2. ATR-based stop loss with trend strength adjustment
        3. Dynamic take profit based on trend momentum
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
            
            # Adjust position size based on trend strength
            trend_strength = signal.metadata.get('trend_strength', 0.5)
            adx_value = signal.metadata.get('adx', 25)
            
            # Position sizing with trend strength multiplier
            trend_multiplier = 0.5 + (trend_strength * 1.5)  # Range: 0.5 to 2.0
            volatility_adjustment = min(2.0, max(0.5, 20.0 / current_atr))  # Inverse volatility scaling
            
            position_size = base_position_size * trend_multiplier * volatility_adjustment
            max_position = self.config.get('max_position_size', 5000)
            position_size = min(position_size, max_position)
            
            # Stop loss calculation - tighter stops for stronger trends
            stop_multiplier = 2.0 if adx_value > self.strong_trend_threshold else 2.5
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                stop_loss_price = current_price - (current_atr * stop_multiplier)
                take_profit_price = current_price + (current_atr * stop_multiplier * 2.0)  # 2:1 R/R
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                stop_loss_price = current_price + (current_atr * stop_multiplier)
                take_profit_price = current_price - (current_atr * stop_multiplier * 2.0)  # 2:1 R/R
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop distance based on ATR
            trailing_stop_distance = current_atr * 1.5
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=max_position,
                account_risk_percentage=account_risk_pct,
                volatility_adjustment=volatility_adjustment,
                portfolio_correlation_adjustment=1.0  # Can be enhanced with portfolio context
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime for strategy adaptation.
        
        Regime Logic:
        1. Use ADX to identify trending vs ranging markets
        2. Volatility analysis for high/low vol regimes
        3. Volume analysis for institutional participation
        """
        try:
            # Calculate ADX for trend identification
            adx_result = self.trend_indicators.adx(
                data['high'], data['low'], data['close'], period=self.adx_period
            )
            
            if adx_result is None:
                return MarketRegime.UNKNOWN
            
            current_adx = adx_result['adx'].iloc[-1]
            current_plus_di = adx_result['plus_di'].iloc[-1]
            current_minus_di = adx_result['minus_di'].iloc[-1]
            
            # Calculate volatility regime
            atr_result = self.volatility_indicators.atr(
                data['high'], data['low'], data['close'], period=20
            )
            current_atr = atr_result.iloc[-1] if atr_result is not None else 0.02
            avg_atr = atr_result.rolling(50).mean().iloc[-1] if atr_result is not None else 0.02
            
            # Determine regime
            if current_adx > self.strong_trend_threshold:
                if current_plus_di > current_minus_di:
                    return MarketRegime.TRENDING_UP
                else:
                    return MarketRegime.TRENDING_DOWN
            elif current_adx > self.adx_threshold:
                if current_atr > avg_atr * 1.2:
                    return MarketRegime.HIGH_VOLATILITY
                else:
                    return MarketRegime.LOW_VOLATILITY
            else:
                if current_atr > avg_atr * 1.5:
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
        1. Strong signals get higher urgency and VWAP execution
        2. Weak signals get lower urgency and TWAP execution
        3. Position sizing based on signal strength
        """
        try:
            # Determine action based on signal
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH]:
                action = ExecutionAction.ENTER_LONG
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH]:
                action = ExecutionAction.ENTER_SHORT
            else:
                return None  # No action for neutral signals
            
            # Determine execution algorithm and urgency based on signal strength
            if signal.strength > 0.8:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            elif signal.strength > 0.6:
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
                limit_price=None,  # Let OMS determine optimal price
                stop_price=risk_params.stop_loss_price,
                metadata={
                    'strategy': 'ADX_Trend_Following',
                    'signal_confidence': signal.confidence,
                    'signal_strength': signal.strength,
                    'adx_value': signal.metadata.get('adx'),
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
        2. ADX-specific metrics (trend capture efficiency)
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
                
                self.logger.info(
                    f"Performance updated - Total trades: {self.performance_metrics.total_trades}, "
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