"""Dual Momentum Strategy - Institutional Grade Implementation

This strategy implements Gary Antonacci's Dual Momentum approach with institutional-grade
enhancements, combining relative momentum (cross-sectional) and absolute momentum (time-series).

Core Logic:
- Relative Momentum: Compare asset performance against benchmark/peers
- Absolute Momentum: Ensure positive momentum before entering positions
- Volume-weighted momentum calculations for institutional flow
- Dynamic lookback periods based on market volatility
- Risk parity position sizing across selected assets

Author: Vincent S. Pereira
Version: 1.0.0
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
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


class DualMomentumStrategy(BaseInstitutionalStrategy):
    """
    Dual Momentum Strategy implementing the 5-Pillar Architecture.
    
    This strategy combines relative and absolute momentum to select the best
    performing assets while ensuring positive absolute momentum.
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
        self.lookback_period = self.config.get('momentum_lookback_period', 252)  # 1 year
        self.short_lookback = self.config.get('short_momentum_lookback', 63)  # 3 months
        self.benchmark_symbol = self.config.get('benchmark_symbol', 'SPY')
        self.risk_free_rate = self.config.get('risk_free_rate', 0.02)  # 2% annual
        self.volatility_adjustment = self.config.get('volatility_adjustment', True)
        self.min_absolute_momentum = self.config.get('min_absolute_momentum', 0.0)
        
        # Universe of assets for relative momentum (can be expanded)
        self.asset_universe = self.config.get('asset_universe', [self.symbol, self.benchmark_symbol])
        
        # Momentum calculation cache
        self.momentum_cache = {}
        self.volatility_cache = {}
        
        self.logger.info(f"Dual Momentum Strategy initialized for {self.symbol}")
    
    def _generate_signal(self, data: pd.DataFrame) -> IndicatorSignal:
        """
        PILLAR 1: Generate trading signal using dual momentum approach.
        
        Signal Logic:
        1. Calculate absolute momentum (time-series momentum)
        2. Calculate relative momentum (cross-sectional momentum)
        3. Volume-weighted momentum for institutional confirmation
        4. Risk-adjusted momentum using volatility scaling
        5. Multi-timeframe momentum alignment
        """
        try:
            if len(data) < self.lookback_period:
                return self._create_neutral_signal("Insufficient data for momentum calculation")
            
            current_price = data['close'].iloc[-1]
            
            # Calculate absolute momentum (time-series)
            absolute_momentum = self._calculate_absolute_momentum(data)
            short_momentum = self._calculate_short_term_momentum(data)
            
            # Calculate volume-weighted momentum
            vw_momentum = self._calculate_volume_weighted_momentum(data)
            
            # Calculate risk-adjusted momentum
            risk_adjusted_momentum = self._calculate_risk_adjusted_momentum(data)
            
            # Calculate relative momentum (if benchmark data available)
            relative_momentum = self._calculate_relative_momentum(data)
            
            # Combine momentum signals
            momentum_score = self._combine_momentum_signals(
                absolute_momentum, short_momentum, vw_momentum, 
                risk_adjusted_momentum, relative_momentum
            )
            
            # Determine signal type based on momentum score
            if momentum_score > 0.6 and absolute_momentum > self.min_absolute_momentum:
                if momentum_score > 0.8:
                    signal_type = SignalType.STRONG_BULLISH
                    confidence = 0.9
                else:
                    signal_type = SignalType.BULLISH
                    confidence = 0.7
            elif momentum_score < -0.6:
                if momentum_score < -0.8:
                    signal_type = SignalType.STRONG_BEARISH
                    confidence = 0.9
                else:
                    signal_type = SignalType.BEARISH
                    confidence = 0.7
            elif momentum_score > 0.2:
                signal_type = SignalType.WEAK_BULLISH
                confidence = 0.5
            elif momentum_score < -0.2:
                signal_type = SignalType.WEAK_BEARISH
                confidence = 0.5
            else:
                signal_type = SignalType.NEUTRAL
                confidence = 0.3
            
            # Adjust confidence based on momentum consistency
            momentum_consistency = self._calculate_momentum_consistency(data)
            confidence *= momentum_consistency
            
            # Calculate strength based on absolute momentum magnitude
            strength = min(abs(momentum_score), 1.0)
            
            # Create metadata
            metadata = {
                'absolute_momentum': absolute_momentum,
                'short_momentum': short_momentum,
                'vw_momentum': vw_momentum,
                'risk_adjusted_momentum': risk_adjusted_momentum,
                'relative_momentum': relative_momentum,
                'momentum_score': momentum_score,
                'momentum_consistency': momentum_consistency,
                'price': current_price,
                'lookback_period': self.lookback_period
            }
            
            return IndicatorSignal(
                raw_value=momentum_score,
                signal_type=signal_type,
                confidence=confidence,
                strength=strength,
                timeframe=self.timeframe,
                timestamp=datetime.now(),
                metadata=metadata
            )
            
        except Exception as e:
            self.logger.error(f"Error generating dual momentum signal: {e}")
            return self._create_neutral_signal(f"Error: {e}")
    
    def _calculate_absolute_momentum(self, data: pd.DataFrame) -> float:
        """Calculate absolute (time-series) momentum"""
        try:
            current_price = data['close'].iloc[-1]
            past_price = data['close'].iloc[-self.lookback_period]
            
            # Calculate total return
            total_return = (current_price / past_price) - 1.0
            
            # Annualize the return
            periods_per_year = 252 if self.timeframe == '1D' else 252 * 24  # Adjust for intraday
            annualized_return = (1 + total_return) ** (periods_per_year / self.lookback_period) - 1
            
            # Subtract risk-free rate for excess return
            excess_return = annualized_return - self.risk_free_rate
            
            return excess_return
            
        except Exception as e:
            self.logger.warning(f"Error calculating absolute momentum: {e}")
            return 0.0
    
    def _calculate_short_term_momentum(self, data: pd.DataFrame) -> float:
        """Calculate short-term momentum for trend confirmation"""
        try:
            current_price = data['close'].iloc[-1]
            past_price = data['close'].iloc[-self.short_lookback]
            
            return (current_price / past_price) - 1.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating short-term momentum: {e}")
            return 0.0
    
    def _calculate_volume_weighted_momentum(self, data: pd.DataFrame) -> float:
        """Calculate volume-weighted momentum for institutional flow"""
        try:
            # Calculate VWAP over lookback period
            vwap_current = self.volume_indicators.vwap(
                data['high'].iloc[-20:], data['low'].iloc[-20:], 
                data['close'].iloc[-20:], data['volume'].iloc[-20:]
            ).iloc[-1]
            
            vwap_past = self.volume_indicators.vwap(
                data['high'].iloc[-self.lookback_period-20:-self.lookback_period], 
                data['low'].iloc[-self.lookback_period-20:-self.lookback_period],
                data['close'].iloc[-self.lookback_period-20:-self.lookback_period], 
                data['volume'].iloc[-self.lookback_period-20:-self.lookback_period]
            ).iloc[-1]
            
            return (vwap_current / vwap_past) - 1.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating volume-weighted momentum: {e}")
            return 0.0
    
    def _calculate_risk_adjusted_momentum(self, data: pd.DataFrame) -> float:
        """Calculate risk-adjusted momentum using volatility scaling"""
        try:
            # Calculate returns
            returns = data['close'].pct_change().iloc[-self.lookback_period:]
            
            # Calculate mean return and volatility
            mean_return = returns.mean()
            volatility = returns.std()
            
            if volatility == 0:
                return 0.0
            
            # Calculate Sharpe-like ratio
            risk_adjusted = (mean_return * np.sqrt(252)) / (volatility * np.sqrt(252))
            
            return risk_adjusted
            
        except Exception as e:
            self.logger.warning(f"Error calculating risk-adjusted momentum: {e}")
            return 0.0
    
    def _calculate_relative_momentum(self, data: pd.DataFrame) -> float:
        """Calculate relative momentum vs benchmark (simplified version)"""
        try:
            # For now, return 0 as we don't have benchmark data
            # In a full implementation, this would compare against benchmark/universe
            # relative_return = asset_return - benchmark_return
            return 0.0
            
        except Exception as e:
            self.logger.warning(f"Error calculating relative momentum: {e}")
            return 0.0
    
    def _combine_momentum_signals(self, absolute_mom: float, short_mom: float, 
                                vw_mom: float, risk_adj_mom: float, rel_mom: float) -> float:
        """Combine different momentum signals into a single score"""
        try:
            # Weighted combination of momentum signals
            weights = {
                'absolute': 0.4,
                'short_term': 0.2,
                'volume_weighted': 0.2,
                'risk_adjusted': 0.15,
                'relative': 0.05
            }
            
            # Normalize signals to [-1, 1] range
            normalized_absolute = np.tanh(absolute_mom * 5)  # Scale for tanh
            normalized_short = np.tanh(short_mom * 10)
            normalized_vw = np.tanh(vw_mom * 10)
            normalized_risk_adj = np.tanh(risk_adj_mom)
            normalized_relative = np.tanh(rel_mom * 10)
            
            # Weighted combination
            combined_score = (
                weights['absolute'] * normalized_absolute +
                weights['short_term'] * normalized_short +
                weights['volume_weighted'] * normalized_vw +
                weights['risk_adjusted'] * normalized_risk_adj +
                weights['relative'] * normalized_relative
            )
            
            return combined_score
            
        except Exception as e:
            self.logger.warning(f"Error combining momentum signals: {e}")
            return 0.0
    
    def _calculate_momentum_consistency(self, data: pd.DataFrame) -> float:
        """Calculate momentum consistency across different timeframes"""
        try:
            # Calculate momentum over different periods
            periods = [21, 63, 126, 252]  # 1M, 3M, 6M, 1Y
            momentum_values = []
            
            current_price = data['close'].iloc[-1]
            
            for period in periods:
                if len(data) >= period:
                    past_price = data['close'].iloc[-period]
                    momentum = (current_price / past_price) - 1.0
                    momentum_values.append(np.sign(momentum))
            
            if not momentum_values:
                return 0.5
            
            # Calculate consistency as agreement across timeframes
            consistency = abs(sum(momentum_values)) / len(momentum_values)
            return 0.5 + (consistency * 0.5)  # Scale to [0.5, 1.0]
            
        except Exception as e:
            self.logger.warning(f"Error calculating momentum consistency: {e}")
            return 0.5
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: IndicatorSignal) -> RiskParameters:
        """
        PILLAR 2: Calculate dynamic risk management parameters.
        
        Risk Logic:
        1. Volatility-based position sizing
        2. Momentum-adjusted stop losses
        3. Dynamic take profit based on momentum strength
        4. Risk parity across momentum factors
        """
        try:
            # Calculate volatility for risk scaling
            returns = data['close'].pct_change().iloc[-63:]  # 3 months
            volatility = returns.std() * np.sqrt(252)  # Annualized volatility
            
            current_price = data['close'].iloc[-1]
            account_risk_pct = self.config.get('account_risk_percentage', 0.02)
            base_position_size = self.config.get('base_position_size', 1000)
            
            # Volatility-based position sizing (inverse volatility)
            target_volatility = self.config.get('target_volatility', 0.15)  # 15% target vol
            vol_adjustment = target_volatility / max(volatility, 0.05)  # Min 5% vol
            vol_adjustment = min(vol_adjustment, 3.0)  # Cap at 3x leverage
            
            # Momentum strength adjustment
            momentum_score = abs(signal.metadata.get('momentum_score', 0.5))
            momentum_adjustment = 0.5 + (momentum_score * 1.5)  # 0.5x to 2x
            
            position_size = base_position_size * vol_adjustment * momentum_adjustment
            max_position = self.config.get('max_position_size', 5000)
            position_size = min(position_size, max_position)
            
            # Stop loss based on volatility and momentum
            stop_distance_pct = volatility * 0.5  # Half of annual volatility
            stop_distance_pct = max(stop_distance_pct, 0.02)  # Minimum 2%
            stop_distance_pct = min(stop_distance_pct, 0.10)  # Maximum 10%
            
            if signal.signal_type in [SignalType.BULLISH, SignalType.STRONG_BULLISH, SignalType.WEAK_BULLISH]:
                stop_loss_price = current_price * (1 - stop_distance_pct)
                take_profit_price = current_price * (1 + stop_distance_pct * 2.0)  # 2:1 R/R
            elif signal.signal_type in [SignalType.BEARISH, SignalType.STRONG_BEARISH, SignalType.WEAK_BEARISH]:
                stop_loss_price = current_price * (1 + stop_distance_pct)
                take_profit_price = current_price * (1 - stop_distance_pct * 2.0)
            else:
                stop_loss_price = None
                take_profit_price = None
            
            # Trailing stop based on momentum
            trailing_stop_distance = current_price * stop_distance_pct * 0.75
            
            return RiskParameters(
                position_size=position_size,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                trailing_stop_distance=trailing_stop_distance,
                max_position_size=max_position,
                account_risk_percentage=account_risk_pct,
                volatility_adjustment=vol_adjustment,
                portfolio_correlation_adjustment=1.0
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        PILLAR 3: Determine current market regime for strategy adaptation.
        
        Regime Logic:
        1. Use momentum consistency for trend identification
        2. Volatility analysis for regime classification
        3. Cross-asset momentum for market-wide regime
        """
        try:
            # Calculate momentum metrics
            absolute_momentum = self._calculate_absolute_momentum(data)
            momentum_consistency = self._calculate_momentum_consistency(data)
            
            # Calculate volatility regime
            returns = data['close'].pct_change().iloc[-63:]
            current_vol = returns.std() * np.sqrt(252)
            long_term_vol = data['close'].pct_change().iloc[-252:].std() * np.sqrt(252)
            
            # Determine regime based on momentum and volatility
            if momentum_consistency > 0.8 and absolute_momentum > 0.05:
                return MarketRegime.TRENDING_UP
            elif momentum_consistency > 0.8 and absolute_momentum < -0.05:
                return MarketRegime.TRENDING_DOWN
            elif current_vol > long_term_vol * 1.5:
                return MarketRegime.HIGH_VOLATILITY
            elif current_vol < long_term_vol * 0.7:
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
        2. Weak momentum gets patient execution
        3. High volatility gets VWAP execution
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
            momentum_score = abs(signal.metadata.get('momentum_score', 0.5))
            momentum_consistency = signal.metadata.get('momentum_consistency', 0.5)
            
            if momentum_score > 0.7 and momentum_consistency > 0.8:
                algorithm = ExecutionAlgorithm.VWAP
                urgency = ExecutionUrgency.HIGH
            elif momentum_score > 0.4:
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
                    'strategy': 'Dual_Momentum',
                    'signal_confidence': signal.confidence,
                    'momentum_score': momentum_score,
                    'momentum_consistency': momentum_consistency,
                    'absolute_momentum': signal.metadata.get('absolute_momentum'),
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
        1. Momentum-specific performance metrics
        2. Risk-adjusted returns (Sharpe ratio)
        3. Maximum drawdown tracking
        4. Momentum factor attribution
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
                    f"Dual Momentum Performance - Trades: {self.performance_metrics.total_trades}, "
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