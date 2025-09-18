#!/usr/bin/env python3
"""
Internal Bar Strength (IBS) Mean Reversion Strategy

Implements a sophisticated mean reversion strategy using Internal Bar Strength (IBS) with institutional-grade enhancements.
IBS measures where the close is relative to the day's range: IBS = (Close - Low) / (High - Low)
Values near 0 indicate closes near the low (potential oversold), values near 1 indicate closes near the high (potential overbought).

Key Features:
- Multi-period IBS analysis with volume weighting
- Adaptive IBS thresholds based on market volatility
- Cumulative IBS for multi-day patterns
- Volume-weighted IBS calculations for enhanced accuracy
- Price action confirmation using candlestick patterns
- Dynamic position sizing based on IBS extremes
- False signal filtering using trend context
- Risk management with volatility-adjusted stops

Author: Algorithmic Trading System
Date: 2024
Version: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime, timedelta

# Import base strategy class and required modules
from ...core.base_strategy import BaseRetailStrategy
from ....core.risk_management import RiskParameters, PositionSizer
from ....core.market_regime import MarketRegimeDetector, MarketRegime
from ....indicators.technical_indicators import TechnicalIndicators
from ....indicators.candlestick_patterns import CandlestickPatterns
from ....core.signal_generator import Signal, SignalType, SignalStrength
from ....core.execution_engine import ExecutionIntent, OrderType
from ....core.performance_tracker import PerformanceMetrics


class IBSMeanReversionStrategy(BaseRetailStrategy):
    """
    Internal Bar Strength (IBS) Mean Reversion Strategy Implementation
    
    This strategy implements sophisticated mean reversion using IBS with:
    - Multi-period IBS analysis for pattern recognition
    - Volume-weighted IBS calculations for improved accuracy
    - Cumulative IBS for multi-day mean reversion patterns
    - Adaptive thresholds based on market volatility
    - Price action confirmation for enhanced signals
    """
    
    def __init__(self, 
                 symbol: str,
                 ibs_period: int = 1,
                 cumulative_ibs_period: int = 3,
                 ibs_oversold: float = 0.2,
                 ibs_overbought: float = 0.8,
                 volume_confirmation: bool = True,
                 trend_filter: bool = True,
                 adaptive_thresholds: bool = True,
                 min_range_filter: float = 0.005,
                 max_position_size: float = 0.1,
                 stop_loss_atr_multiplier: float = 2.0,
                 profit_target_ratio: float = 1.5,
                 **kwargs):
        """
        Initialize IBS Mean Reversion Strategy
        
        Args:
            symbol: Trading symbol
            ibs_period: Period for IBS calculation (default: 1 for single bar)
            cumulative_ibs_period: Period for cumulative IBS (default: 3)
            ibs_oversold: IBS oversold threshold (default: 0.2)
            ibs_overbought: IBS overbought threshold (default: 0.8)
            volume_confirmation: Use volume for signal confirmation
            trend_filter: Filter signals against longer-term trend
            adaptive_thresholds: Adapt thresholds based on volatility
            min_range_filter: Minimum daily range filter (as % of price)
            max_position_size: Maximum position size as fraction of portfolio
            stop_loss_atr_multiplier: ATR multiplier for stop loss
            profit_target_ratio: Risk/reward ratio for profit targets
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.ibs_period = ibs_period
        self.cumulative_ibs_period = cumulative_ibs_period
        self.ibs_oversold = ibs_oversold
        self.ibs_overbought = ibs_overbought
        self.volume_confirmation = volume_confirmation
        self.trend_filter = trend_filter
        self.adaptive_thresholds = adaptive_thresholds
        self.min_range_filter = min_range_filter
        self.max_position_size = max_position_size
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.profit_target_ratio = profit_target_ratio
        
        # Initialize components
        self.technical_indicators = TechnicalIndicators()
        self.candlestick_patterns = CandlestickPatterns()
        self.market_regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.adaptive_oversold = ibs_oversold
        self.adaptive_overbought = ibs_overbought
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate IBS mean reversion signals with volume confirmation,
        cumulative patterns, and price action validation.
        """
        if len(data) < max(self.cumulative_ibs_period, 20) + 10:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Update adaptive thresholds
            if self.adaptive_thresholds:
                self._update_adaptive_thresholds(data)
            
            # Calculate IBS (Internal Bar Strength)
            ibs = self._calculate_ibs(data)
            
            # Calculate volume-weighted IBS if enabled
            if self.volume_confirmation:
                vw_ibs = self._calculate_volume_weighted_ibs(data)
            else:
                vw_ibs = ibs
            
            # Calculate cumulative IBS for multi-day patterns
            cumulative_ibs = self._calculate_cumulative_ibs(ibs, self.cumulative_ibs_period)
            
            # Calculate additional indicators
            rsi = self.technical_indicators.rsi(data['close'], period=14)
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            atr = self.technical_indicators.atr(data, period=14)
            sma_20 = self.technical_indicators.sma(data['close'], period=20)
            ema_50 = self.technical_indicators.ema(data['close'], period=50)
            
            # Calculate daily range as percentage of price
            daily_range_pct = (data['high'] - data['low']) / data['close']
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            current_ibs = ibs.iloc[-1]
            current_vw_ibs = vw_ibs.iloc[-1]
            current_cumulative_ibs = cumulative_ibs.iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_atr = atr.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            current_range_pct = daily_range_pct.iloc[-1]
            
            # Apply minimum range filter
            if current_range_pct < self.min_range_filter:
                return [self._create_neutral_signal()]
            
            # Trend context for filtering
            trend_bullish = current_price > current_ema_50
            trend_bearish = current_price < current_ema_50
            
            # Generate primary signals
            signal_strength = SignalStrength.WEAK
            signal_type = SignalType.HOLD
            confidence = 0.5
            
            # Long signal conditions (IBS oversold)
            if (current_ibs <= self.adaptive_oversold or 
                current_vw_ibs <= self.adaptive_oversold or
                current_cumulative_ibs <= self.adaptive_oversold * self.cumulative_ibs_period):
                
                # Apply trend filter if enabled
                if not self.trend_filter or trend_bullish or not trend_bearish:
                    signal_type = SignalType.BUY
                    signal_strength = SignalStrength.MEDIUM
                    confidence = 0.6
                    
                    # Enhance signal with confirmations
                    confirmations = 0
                    
                    # Extreme IBS values (very strong mean reversion signal)
                    if current_ibs <= 0.1:
                        confirmations += 3  # Very strong signal
                    elif current_ibs <= 0.15:
                        confirmations += 2
                    
                    # Volume-weighted IBS confirmation
                    if current_vw_ibs <= self.adaptive_oversold:
                        confirmations += 1
                    
                    # Cumulative IBS pattern (multiple days of low closes)
                    if current_cumulative_ibs <= self.adaptive_oversold * self.cumulative_ibs_period * 0.8:
                        confirmations += 2  # Strong multi-day pattern
                    
                    # RSI confirmation (not extremely oversold to avoid falling knife)
                    if 25 < current_rsi < 45:
                        confirmations += 1
                    
                    # Volume confirmation (above average volume)
                    if self.volume_confirmation and current_volume > avg_volume * 1.2:
                        confirmations += 1
                    
                    # Price action confirmation - hammer or bullish patterns
                    if len(data) >= 3:
                        recent_candles = data.iloc[-3:]
                        patterns = self.candlestick_patterns.detect_patterns(recent_candles)
                        if any(pattern in ['hammer', 'bullish_engulfing', 'morning_star', 'dragonfly_doji'] 
                               for pattern in patterns):
                            confirmations += 2  # Strong price action confirmation
                    
                    # Gap down with low IBS (strong mean reversion setup)
                    if len(data) >= 2:
                        prev_close = data['close'].iloc[-2]
                        if current_price < prev_close * 0.98 and current_ibs <= 0.3:
                            confirmations += 2
                    
                    # Multiple consecutive low IBS days
                    if len(ibs) >= 3:
                        recent_ibs = ibs.iloc[-3:]
                        if all(val <= 0.3 for val in recent_ibs):
                            confirmations += 2
                    
                    # Large daily range with low close (strong mean reversion)
                    if current_range_pct > 0.02 and current_ibs <= 0.25:
                        confirmations += 1
                    
                    # Adjust signal strength based on confirmations
                    if confirmations >= 6:
                        signal_strength = SignalStrength.STRONG
                        confidence = 0.9
                    elif confirmations >= 4:
                        signal_strength = SignalStrength.MEDIUM
                        confidence = 0.75
                        
            # Short signal conditions (IBS overbought)
            elif (current_ibs >= self.adaptive_overbought or 
                  current_vw_ibs >= self.adaptive_overbought or
                  current_cumulative_ibs >= self.adaptive_overbought * self.cumulative_ibs_period):
                
                # Apply trend filter if enabled
                if not self.trend_filter or trend_bearish or not trend_bullish:
                    signal_type = SignalType.SELL
                    signal_strength = SignalStrength.MEDIUM
                    confidence = 0.6
                    
                    # Enhance signal with confirmations
                    confirmations = 0
                    
                    # Extreme IBS values (very strong mean reversion signal)
                    if current_ibs >= 0.9:
                        confirmations += 3  # Very strong signal
                    elif current_ibs >= 0.85:
                        confirmations += 2
                    
                    # Volume-weighted IBS confirmation
                    if current_vw_ibs >= self.adaptive_overbought:
                        confirmations += 1
                    
                    # Cumulative IBS pattern (multiple days of high closes)
                    if current_cumulative_ibs >= self.adaptive_overbought * self.cumulative_ibs_period * 1.2:
                        confirmations += 2  # Strong multi-day pattern
                    
                    # RSI confirmation (not extremely overbought)
                    if 55 < current_rsi < 75:
                        confirmations += 1
                    
                    # Volume confirmation (above average volume)
                    if self.volume_confirmation and current_volume > avg_volume * 1.2:
                        confirmations += 1
                    
                    # Price action confirmation - shooting star or bearish patterns
                    if len(data) >= 3:
                        recent_candles = data.iloc[-3:]
                        patterns = self.candlestick_patterns.detect_patterns(recent_candles)
                        if any(pattern in ['shooting_star', 'bearish_engulfing', 'evening_star', 'gravestone_doji'] 
                               for pattern in patterns):
                            confirmations += 2  # Strong price action confirmation
                    
                    # Gap up with high IBS (strong mean reversion setup)
                    if len(data) >= 2:
                        prev_close = data['close'].iloc[-2]
                        if current_price > prev_close * 1.02 and current_ibs >= 0.7:
                            confirmations += 2
                    
                    # Multiple consecutive high IBS days
                    if len(ibs) >= 3:
                        recent_ibs = ibs.iloc[-3:]
                        if all(val >= 0.7 for val in recent_ibs):
                            confirmations += 2
                    
                    # Large daily range with high close (strong mean reversion)
                    if current_range_pct > 0.02 and current_ibs >= 0.75:
                        confirmations += 1
                    
                    # Adjust signal strength based on confirmations
                    if confirmations >= 6:
                        signal_strength = SignalStrength.STRONG
                        confidence = 0.9
                    elif confirmations >= 4:
                        signal_strength = SignalStrength.MEDIUM
                        confidence = 0.75
            
            # Create signal with metadata
            signal = Signal(
                symbol=self.symbol,
                signal_type=signal_type,
                strength=signal_strength,
                confidence=confidence,
                timestamp=data.index[-1],
                metadata={
                    'price': current_price,
                    'ibs': current_ibs,
                    'volume_weighted_ibs': current_vw_ibs,
                    'cumulative_ibs': current_cumulative_ibs,
                    'rsi': current_rsi,
                    'sma_20': current_sma_20,
                    'ema_50': current_ema_50,
                    'volume_ratio': current_volume / avg_volume,
                    'atr': current_atr,
                    'daily_range_pct': current_range_pct,
                    'trend_bullish': trend_bullish,
                    'trend_bearish': trend_bearish,
                    'adaptive_oversold': self.adaptive_oversold,
                    'adaptive_overbought': self.adaptive_overbought,
                    'market_regime': self.current_regime.value
                }
            )
            
            signals.append(signal)
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            signals.append(self._create_neutral_signal())
            
        return signals
    
    def _calculate_ibs(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate Internal Bar Strength (IBS)
        IBS = (Close - Low) / (High - Low)
        """
        try:
            high_low_range = data['high'] - data['low']
            # Avoid division by zero
            high_low_range = high_low_range.replace(0, np.nan)
            
            ibs = (data['close'] - data['low']) / high_low_range
            
            # Handle edge cases
            ibs = ibs.fillna(0.5)  # Neutral IBS for zero range bars
            ibs = ibs.clip(0, 1)   # Ensure IBS is between 0 and 1
            
            return ibs
            
        except Exception as e:
            self.logger.error(f"Error calculating IBS: {e}")
            return pd.Series(0.5, index=data.index)
    
    def _calculate_volume_weighted_ibs(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate volume-weighted IBS for enhanced accuracy
        """
        try:
            # Calculate regular IBS
            ibs = self._calculate_ibs(data)
            
            # Apply volume weighting using exponential moving average
            volume_weights = data['volume'] / data['volume'].rolling(window=20).mean()
            volume_weights = volume_weights.fillna(1.0).clip(0.1, 3.0)  # Reasonable bounds
            
            # Volume-weighted IBS using EMA with volume-adjusted alpha
            vw_ibs = pd.Series(index=data.index, dtype=float)
            vw_ibs.iloc[0] = ibs.iloc[0]
            
            for i in range(1, len(data)):
                alpha = min(0.5, volume_weights.iloc[i] * 0.1)  # Volume-adjusted smoothing
                vw_ibs.iloc[i] = alpha * ibs.iloc[i] + (1 - alpha) * vw_ibs.iloc[i-1]
            
            return vw_ibs
            
        except Exception as e:
            self.logger.error(f"Error calculating volume-weighted IBS: {e}")
            return self._calculate_ibs(data)
    
    def _calculate_cumulative_ibs(self, ibs: pd.Series, period: int) -> pd.Series:
        """
        Calculate cumulative IBS over specified period
        """
        try:
            # Sum IBS over rolling window
            cumulative_ibs = ibs.rolling(window=period).sum()
            
            return cumulative_ibs.fillna(period * 0.5)  # Neutral cumulative IBS
            
        except Exception as e:
            self.logger.error(f"Error calculating cumulative IBS: {e}")
            return pd.Series(period * 0.5, index=ibs.index)
    
    def _update_adaptive_thresholds(self, data: pd.DataFrame) -> None:
        """
        Update IBS thresholds based on current market volatility
        """
        try:
            # Calculate recent volatility
            if len(data) >= 20:
                recent_returns = data['close'].pct_change().iloc[-20:]
                volatility = recent_returns.std() * np.sqrt(252)  # Annualized
                
                # Calculate recent IBS distribution
                recent_ibs = self._calculate_ibs(data.iloc[-50:]) if len(data) >= 50 else self._calculate_ibs(data)
                ibs_std = recent_ibs.std()
                ibs_mean = recent_ibs.mean()
                
                if volatility > 0.3:  # High volatility
                    # Use more extreme thresholds in volatile markets
                    self.adaptive_oversold = max(0.05, self.ibs_oversold - 0.1)
                    self.adaptive_overbought = min(0.95, self.ibs_overbought + 0.1)
                    
                elif volatility < 0.15:  # Low volatility
                    # Use less extreme thresholds in calm markets
                    self.adaptive_oversold = min(0.35, self.ibs_oversold + 0.1)
                    self.adaptive_overbought = max(0.65, self.ibs_overbought - 0.1)
                    
                else:
                    # Adaptive thresholds based on recent IBS distribution
                    self.adaptive_oversold = max(0.1, ibs_mean - 1.5 * ibs_std)
                    self.adaptive_overbought = min(0.9, ibs_mean + 1.5 * ibs_std)
                    
                # Ensure reasonable bounds
                self.adaptive_oversold = max(0.05, min(0.4, self.adaptive_oversold))
                self.adaptive_overbought = max(0.6, min(0.95, self.adaptive_overbought))
                    
        except Exception as e:
            self.logger.error(f"Error updating adaptive thresholds: {e}")
            self.adaptive_oversold = self.ibs_oversold
            self.adaptive_overbought = self.ibs_overbought
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters based on IBS extremes,
        volatility, and signal strength.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('price', data['close'].iloc[-1])
            current_ibs = metadata.get('ibs', 0.5)
            current_vw_ibs = metadata.get('volume_weighted_ibs', 0.5)
            current_atr = metadata.get('atr', 0)
            daily_range_pct = metadata.get('daily_range_pct', 0.01)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.4,
                SignalStrength.MEDIUM: 0.7,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Adjust size based on IBS extremes (more extreme = larger position)
            if signal.signal_type == SignalType.BUY:
                # More oversold = larger position
                ibs_multiplier = min(2.0, (0.3 - current_ibs) / 0.2) if current_ibs < 0.3 else 1.0
            elif signal.signal_type == SignalType.SELL:
                # More overbought = larger position
                ibs_multiplier = min(2.0, (current_ibs - 0.7) / 0.2) if current_ibs > 0.7 else 1.0
            else:
                ibs_multiplier = 1.0
            
            # Volume-weighted IBS confirmation bonus
            vw_confirmation_multiplier = 1.0
            if signal.signal_type == SignalType.BUY and current_vw_ibs <= self.adaptive_oversold:
                vw_confirmation_multiplier = 1.2
            elif signal.signal_type == SignalType.SELL and current_vw_ibs >= self.adaptive_overbought:
                vw_confirmation_multiplier = 1.2
            
            # Daily range adjustment (larger ranges = more opportunity)
            range_multiplier = min(1.5, max(0.7, daily_range_pct / 0.015))
            
            # Adjust size based on market regime
            regime_multiplier = {
                MarketRegime.BULL: 1.0,
                MarketRegime.BEAR: 1.0,
                MarketRegime.SIDEWAYS: 1.3,  # IBS works best in sideways markets
                MarketRegime.HIGH_VOLATILITY: 0.8,
                MarketRegime.LOW_VOLATILITY: 1.1
            }.get(self.current_regime, 1.0)
            
            # Calculate final position size
            position_size = (base_size * strength_multiplier * ibs_multiplier * 
                           vw_confirmation_multiplier * range_multiplier * regime_multiplier)
            position_size = min(position_size, self.max_position_size * 1.5)  # Allow slight oversize for strong signals
            
            # Calculate stop loss and take profit levels
            if signal.signal_type == SignalType.BUY:
                # Stop loss based on ATR or recent swing low
                atr_stop = current_price - (current_atr * self.stop_loss_atr_multiplier)
                
                # IBS-based stop (below the low of the current bar)
                ibs_stop = current_price - (daily_range_pct * current_price * 1.2)
                
                stop_loss = max(atr_stop, ibs_stop)  # Use closer stop
                
                # Take profit based on risk/reward ratio
                risk_amount = current_price - stop_loss
                take_profit = current_price + (risk_amount * self.profit_target_ratio)
                
            elif signal.signal_type == SignalType.SELL:
                # Stop loss based on ATR or recent swing high
                atr_stop = current_price + (current_atr * self.stop_loss_atr_multiplier)
                
                # IBS-based stop (above the high of the current bar)
                ibs_stop = current_price + (daily_range_pct * current_price * 1.2)
                
                stop_loss = min(atr_stop, ibs_stop)  # Use closer stop
                
                # Take profit based on risk/reward ratio
                risk_amount = stop_loss - current_price
                take_profit = current_price - (risk_amount * self.profit_target_ratio)
                
            else:
                stop_loss = None
                take_profit = None
            
            return RiskParameters(
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_risk_per_trade=0.02,  # Conservative for mean reversion
                risk_reward_ratio=self.profit_target_ratio,
                volatility_adjustment=abs(current_ibs - 0.5) * 2  # 0 to 1 scale
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating risk parameters: {e}")
            return self._create_default_risk_parameters()
    
    def _check_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect current market regime and adapt strategy parameters accordingly.
        """
        try:
            # Use market regime detector
            regime = self.market_regime_detector.detect_regime(data)
            self.current_regime = regime
            
            # Log regime changes
            if hasattr(self, '_previous_regime') and self._previous_regime != regime:
                self.logger.info(f"Market regime changed from {self._previous_regime.value} to {regime.value}")
            
            self._previous_regime = regime
            return regime
            
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return MarketRegime.NEUTRAL
    
    def _determine_execution_intent(self, 
                                  signals: List[Signal], 
                                  risk_params: RiskParameters,
                                  current_position: Optional[Dict]) -> ExecutionIntent:
        """
        Pillar 4: Decoupled Execution Logic & Order Management
        
        Determine execution intent based on signals, risk parameters,
        and current position.
        """
        if not signals:
            return ExecutionIntent(action="HOLD", quantity=0)
            
        primary_signal = signals[0]
        
        try:
            # Check if we should exit current position
            if current_position and current_position.get('quantity', 0) != 0:
                current_qty = current_position['quantity']
                entry_price = current_position.get('entry_price', 0)
                current_price = primary_signal.metadata.get('price', 0)
                current_ibs = primary_signal.metadata.get('ibs', 0.5)
                
                # Exit conditions for long position
                if current_qty > 0:
                    # IBS mean reversion exit - when IBS moves to opposite extreme or neutral
                    if current_ibs >= 0.6 or current_ibs >= self.adaptive_overbought * 0.8:
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"IBS mean reversion exit: IBS={current_ibs:.3f}"
                        )
                    
                    # Stop loss or take profit
                    if (risk_params.stop_loss and current_price <= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price >= risk_params.take_profit):
                        pnl_pct = (current_price - entry_price) / entry_price
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
                
                # Exit conditions for short position
                elif current_qty < 0:
                    # IBS mean reversion exit - when IBS moves to opposite extreme or neutral
                    if current_ibs <= 0.4 or current_ibs <= self.adaptive_oversold * 1.2:
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"IBS mean reversion exit: IBS={current_ibs:.3f}"
                        )
                    
                    # Stop loss or take profit
                    if (risk_params.stop_loss and current_price >= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price <= risk_params.take_profit):
                        pnl_pct = (entry_price - current_price) / entry_price
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
            
            # Entry logic
            if primary_signal.signal_type == SignalType.BUY and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="BUY",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('price') * 0.999,  # Slight discount
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"IBS oversold: {primary_signal.metadata.get('ibs', 0):.3f}"
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('price') * 1.001,  # Slight premium
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"IBS overbought: {primary_signal.metadata.get('ibs', 0):.3f}"
                )
            
            return ExecutionIntent(action="HOLD", quantity=0)
            
        except Exception as e:
            self.logger.error(f"Error determining execution intent: {e}")
            return ExecutionIntent(action="HOLD", quantity=0)
    
    def _update_performance_metrics(self, 
                                  execution_result: Dict,
                                  market_data: pd.DataFrame) -> None:
        """
        Pillar 5: Performance Tracking & Configurability
        
        Update strategy performance metrics and statistics.
        """
        try:
            # Update basic performance metrics
            self.performance_metrics.update(
                timestamp=market_data.index[-1],
                price=market_data['close'].iloc[-1],
                position=execution_result.get('position', 0),
                pnl=execution_result.get('pnl', 0),
                execution_result=execution_result
            )
            
            # Strategy-specific metrics
            if hasattr(self, '_last_signal'):
                signal_metadata = self._last_signal.metadata
                
                # Track IBS levels at entry/exit
                self.performance_metrics.add_custom_metric(
                    'ibs_at_signal', 
                    signal_metadata.get('ibs', 0.5)
                )
                
                self.performance_metrics.add_custom_metric(
                    'volume_weighted_ibs_at_signal', 
                    signal_metadata.get('volume_weighted_ibs', 0.5)
                )
                
                self.performance_metrics.add_custom_metric(
                    'cumulative_ibs_at_signal', 
                    signal_metadata.get('cumulative_ibs', 1.5)
                )
                
                # Track daily range at signal
                self.performance_metrics.add_custom_metric(
                    'daily_range_pct_at_signal',
                    signal_metadata.get('daily_range_pct', 0.01)
                )
                
                # Track volume confirmation rate
                volume_ratio = signal_metadata.get('volume_ratio', 1.0)
                self.performance_metrics.add_custom_metric(
                    'volume_confirmation_rate',
                    1.0 if volume_ratio > 1.2 else 0.0
                )
                
                # Track adaptive threshold effectiveness
                self.performance_metrics.add_custom_metric(
                    'adaptive_oversold_threshold',
                    signal_metadata.get('adaptive_oversold', self.ibs_oversold)
                )
                
                self.performance_metrics.add_custom_metric(
                    'adaptive_overbought_threshold',
                    signal_metadata.get('adaptive_overbought', self.ibs_overbought)
                )
            
            # Calculate strategy-specific performance ratios
            trades = self.performance_metrics.get_trades()
            if len(trades) >= 10:
                # IBS extreme signal success rate
                extreme_signals = [trade for trade in trades[-20:] 
                                 if trade.get('entry_ibs', 0.5) <= 0.2 or trade.get('entry_ibs', 0.5) >= 0.8]
                if extreme_signals:
                    extreme_success = sum(1 for trade in extreme_signals 
                                        if trade.get('pnl', 0) > 0)
                    extreme_success_rate = extreme_success / len(extreme_signals)
                    
                    self.performance_metrics.add_custom_metric(
                        'extreme_ibs_success_rate',
                        extreme_success_rate
                    )
                
                # Average IBS at entry
                entry_ibs_levels = [trade.get('entry_ibs', 0.5) for trade in trades[-20:]]
                avg_entry_ibs_extreme = np.mean([abs(ibs - 0.5) for ibs in entry_ibs_levels]) if entry_ibs_levels else 0
                
                self.performance_metrics.add_custom_metric(
                    'avg_entry_ibs_extreme',
                    avg_entry_ibs_extreme
                )
                
                # Cumulative IBS pattern success rate
                cumulative_trades = [trade for trade in trades[-20:] 
                                   if trade.get('had_cumulative_pattern', False)]
                if cumulative_trades:
                    cumulative_success = sum(1 for trade in cumulative_trades 
                                           if trade.get('pnl', 0) > 0)
                    cumulative_success_rate = cumulative_success / len(cumulative_trades)
                    
                    self.performance_metrics.add_custom_metric(
                        'cumulative_ibs_success_rate',
                        cumulative_success_rate
                    )
                
                # Gap trading success rate
                gap_trades = [trade for trade in trades[-20:] 
                            if trade.get('had_gap', False)]
                if gap_trades:
                    gap_success = sum(1 for trade in gap_trades 
                                    if trade.get('pnl', 0) > 0)
                    gap_success_rate = gap_success / len(gap_trades)
                    
                    self.performance_metrics.add_custom_metric(
                        'gap_trading_success_rate',
                        gap_success_rate
                    )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _create_neutral_signal(self) -> Signal:
        """Create a neutral signal when no clear signal is present"""
        return Signal(
            symbol=self.symbol,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.5,
            timestamp=datetime.now(),
            metadata={'reason': 'Insufficient data or unclear signal'}
        )
    
    def _create_default_risk_parameters(self) -> RiskParameters:
        """Create default risk parameters when calculation fails"""
        return RiskParameters(
            position_size=self.max_position_size * 0.5,
            stop_loss=None,
            take_profit=None,
            max_risk_per_trade=0.02,
            risk_reward_ratio=self.profit_target_ratio,
            volatility_adjustment=0.5
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information and current parameters"""
        return {
            'name': 'Internal Bar Strength (IBS) Mean Reversion Strategy',
            'version': '1.0',
            'description': 'Mean reversion using Internal Bar Strength with volume weighting and cumulative patterns',
            'parameters': {
                'ibs_period': self.ibs_period,
                'cumulative_ibs_period': self.cumulative_ibs_period,
                'ibs_oversold': self.ibs_oversold,
                'ibs_overbought': self.ibs_overbought,
                'volume_confirmation': self.volume_confirmation,
                'trend_filter': self.trend_filter,
                'adaptive_thresholds': self.adaptive_thresholds,
                'min_range_filter': self.min_range_filter,
                'max_position_size': self.max_position_size,
                'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
                'profit_target_ratio': self.profit_target_ratio
            },
            'current_state': {
                'market_regime': self.current_regime.value,
                'adaptive_oversold': self.adaptive_oversold,
                'adaptive_overbought': self.adaptive_overbought
            },
            'asset_classes': ['stocks', 'etfs', 'futures', 'forex'],
            'timeframes': ['1d', '4h', '1h'],  # Works best on daily and intraday
            'market_conditions': ['sideways', 'volatile', 'mean_reverting']
        }