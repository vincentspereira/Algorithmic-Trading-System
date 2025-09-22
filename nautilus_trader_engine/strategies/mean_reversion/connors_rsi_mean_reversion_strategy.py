#!/usr/bin/env python3
"""
Connors RSI Mean Reversion Strategy

Implements a sophisticated mean reversion strategy using Connors RSI (CRSI) with institutional-grade enhancements.
Connors RSI combines three components:
1. RSI(3) - Short-term RSI for momentum
2. UpDown Length - Consecutive up/down days streak
3. Rate of Change (ROC) - Magnitude of recent price changes

Key Features:
- Multi-component CRSI analysis with volume weighting
- Adaptive CRSI thresholds based on market volatility
- Streak analysis for enhanced mean reversion signals
- Volume-weighted calculations for improved accuracy
- Price action confirmation using candlestick patterns
- Dynamic position sizing based on CRSI extremes
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
from ...architecture.pillars.risk_management import RiskParameters
from ...utils.risk_management_utils import PositionSizer
from ...architecture.pillars.market_regime_detection import MarketRegimeDetector, MarketRegime
from ...indicators.technical_indicators import TechnicalIndicators
from ...indicators.candlestick_patterns import CandlestickPatterns
from ...architecture.pillars.signal_generation import Signal, SignalType, SignalStrength
from ...architecture.pillars.execution_intent import ExecutionIntent, OrderType
from ...utils.performance_tracker import PerformanceMetrics


class ConnorsRSIMeanReversionStrategy(BaseRetailStrategy):
    """
    Connors RSI Mean Reversion Strategy Implementation
    
    This strategy implements sophisticated mean reversion using Connors RSI with:
    - Multi-component CRSI analysis (RSI, UpDown Length, ROC)
    - Volume-weighted calculations for improved accuracy
    - Streak analysis for enhanced pattern recognition
    - Adaptive thresholds based on market volatility
    - Price action confirmation for enhanced signals
    """
    
    def __init__(self, 
                 symbol: str,
                 rsi_period: int = 3,
                 roc_period: int = 100,
                 crsi_oversold: float = 10,
                 crsi_overbought: float = 90,
                 volume_confirmation: bool = True,
                 trend_filter: bool = True,
                 adaptive_thresholds: bool = True,
                 min_streak_length: int = 2,
                 max_position_size: float = 0.1,
                 stop_loss_atr_multiplier: float = 2.0,
                 profit_target_ratio: float = 1.5,
                 **kwargs):
        """
        Initialize Connors RSI Mean Reversion Strategy
        
        Args:
            symbol: Trading symbol
            rsi_period: Period for RSI calculation (default: 3)
            roc_period: Period for Rate of Change calculation (default: 100)
            crsi_oversold: CRSI oversold threshold (default: 10)
            crsi_overbought: CRSI overbought threshold (default: 90)
            volume_confirmation: Use volume for signal confirmation
            trend_filter: Filter signals against longer-term trend
            adaptive_thresholds: Adapt thresholds based on volatility
            min_streak_length: Minimum streak length for enhanced signals
            max_position_size: Maximum position size as fraction of portfolio
            stop_loss_atr_multiplier: ATR multiplier for stop loss
            profit_target_ratio: Risk/reward ratio for profit targets
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.rsi_period = rsi_period
        self.roc_period = roc_period
        self.crsi_oversold = crsi_oversold
        self.crsi_overbought = crsi_overbought
        self.volume_confirmation = volume_confirmation
        self.trend_filter = trend_filter
        self.adaptive_thresholds = adaptive_thresholds
        self.min_streak_length = min_streak_length
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
        self.adaptive_oversold = crsi_oversold
        self.adaptive_overbought = crsi_overbought
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate Connors RSI mean reversion signals with volume confirmation,
        streak analysis, and price action validation.
        """
        if len(data) < max(self.roc_period, 50) + 10:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Update adaptive thresholds
            if self.adaptive_thresholds:
                self._update_adaptive_thresholds(data)
            
            # Calculate Connors RSI components
            rsi_3 = self.technical_indicators.rsi(data['close'], period=self.rsi_period)
            updown_length = self._calculate_updown_length(data)
            roc_rank = self._calculate_roc_rank(data, self.roc_period)
            
            # Calculate Connors RSI
            crsi = self._calculate_connors_rsi(rsi_3, updown_length, roc_rank)
            
            # Calculate volume-weighted CRSI if enabled
            if self.volume_confirmation:
                vw_crsi = self._calculate_volume_weighted_crsi(data, crsi)
            else:
                vw_crsi = crsi
            
            # Calculate additional indicators
            rsi_14 = self.technical_indicators.rsi(data['close'], period=14)
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            atr = self.technical_indicators.atr(data, period=14)
            sma_20 = self.technical_indicators.sma(data['close'], period=20)
            ema_50 = self.technical_indicators.ema(data['close'], period=50)
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            current_crsi = crsi.iloc[-1]
            current_vw_crsi = vw_crsi.iloc[-1]
            current_rsi_3 = rsi_3.iloc[-1]
            current_rsi_14 = rsi_14.iloc[-1]
            current_updown = updown_length.iloc[-1]
            current_roc_rank = roc_rank.iloc[-1]
            current_atr = atr.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            
            # Trend context for filtering
            trend_bullish = current_price > current_ema_50
            trend_bearish = current_price < current_ema_50
            
            # Generate primary signals
            signal_strength = SignalStrength.WEAK
            signal_type = SignalType.HOLD
            confidence = 0.5
            
            # Long signal conditions (CRSI oversold)
            if (current_crsi <= self.adaptive_oversold or 
                current_vw_crsi <= self.adaptive_oversold):
                
                # Apply trend filter if enabled
                if not self.trend_filter or trend_bullish or not trend_bearish:
                    signal_type = SignalType.BUY
                    signal_strength = SignalStrength.MEDIUM
                    confidence = 0.6
                    
                    # Enhance signal with confirmations
                    confirmations = 0
                    
                    # Extreme CRSI values (very strong mean reversion signal)
                    if current_crsi <= 5:
                        confirmations += 4  # Very strong signal
                    elif current_crsi <= 8:
                        confirmations += 3
                    elif current_crsi <= 12:
                        confirmations += 2
                    
                    # Volume-weighted CRSI confirmation
                    if current_vw_crsi <= self.adaptive_oversold:
                        confirmations += 1
                    
                    # RSI(3) component confirmation
                    if current_rsi_3 <= 15:
                        confirmations += 2
                    elif current_rsi_3 <= 25:
                        confirmations += 1
                    
                    # UpDown Length confirmation (consecutive down days)
                    if current_updown <= -self.min_streak_length:
                        confirmations += 2
                        if current_updown <= -4:  # Extended streak
                            confirmations += 2
                    
                    # ROC Rank confirmation (recent underperformance)
                    if current_roc_rank <= 20:
                        confirmations += 2
                    elif current_roc_rank <= 30:
                        confirmations += 1
                    
                    # RSI(14) confirmation (not extremely oversold to avoid falling knife)
                    if 25 < current_rsi_14 < 45:
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
                    
                    # Multiple component alignment
                    components_oversold = sum([
                        current_rsi_3 <= 20,
                        current_updown <= -2,
                        current_roc_rank <= 25
                    ])
                    if components_oversold >= 2:
                        confirmations += 2  # Multiple components aligned
                    
                    # Gap down with CRSI oversold (strong mean reversion setup)
                    if len(data) >= 2:
                        prev_close = data['close'].iloc[-2]
                        if current_price < prev_close * 0.98 and current_crsi <= 15:
                            confirmations += 3
                    
                    # Adjust signal strength based on confirmations
                    if confirmations >= 8:
                        signal_strength = SignalStrength.STRONG
                        confidence = 0.9
                    elif confirmations >= 5:
                        signal_strength = SignalStrength.MEDIUM
                        confidence = 0.75
                        
            # Short signal conditions (CRSI overbought)
            elif (current_crsi >= self.adaptive_overbought or 
                  current_vw_crsi >= self.adaptive_overbought):
                
                # Apply trend filter if enabled
                if not self.trend_filter or trend_bearish or not trend_bullish:
                    signal_type = SignalType.SELL
                    signal_strength = SignalStrength.MEDIUM
                    confidence = 0.6
                    
                    # Enhance signal with confirmations
                    confirmations = 0
                    
                    # Extreme CRSI values (very strong mean reversion signal)
                    if current_crsi >= 95:
                        confirmations += 4  # Very strong signal
                    elif current_crsi >= 92:
                        confirmations += 3
                    elif current_crsi >= 88:
                        confirmations += 2
                    
                    # Volume-weighted CRSI confirmation
                    if current_vw_crsi >= self.adaptive_overbought:
                        confirmations += 1
                    
                    # RSI(3) component confirmation
                    if current_rsi_3 >= 85:
                        confirmations += 2
                    elif current_rsi_3 >= 75:
                        confirmations += 1
                    
                    # UpDown Length confirmation (consecutive up days)
                    if current_updown >= self.min_streak_length:
                        confirmations += 2
                        if current_updown >= 4:  # Extended streak
                            confirmations += 2
                    
                    # ROC Rank confirmation (recent outperformance)
                    if current_roc_rank >= 80:
                        confirmations += 2
                    elif current_roc_rank >= 70:
                        confirmations += 1
                    
                    # RSI(14) confirmation (not extremely overbought)
                    if 55 < current_rsi_14 < 75:
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
                    
                    # Multiple component alignment
                    components_overbought = sum([
                        current_rsi_3 >= 80,
                        current_updown >= 2,
                        current_roc_rank >= 75
                    ])
                    if components_overbought >= 2:
                        confirmations += 2  # Multiple components aligned
                    
                    # Gap up with CRSI overbought (strong mean reversion setup)
                    if len(data) >= 2:
                        prev_close = data['close'].iloc[-2]
                        if current_price > prev_close * 1.02 and current_crsi >= 85:
                            confirmations += 3
                    
                    # Adjust signal strength based on confirmations
                    if confirmations >= 8:
                        signal_strength = SignalStrength.STRONG
                        confidence = 0.9
                    elif confirmations >= 5:
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
                    'connors_rsi': current_crsi,
                    'volume_weighted_crsi': current_vw_crsi,
                    'rsi_3': current_rsi_3,
                    'rsi_14': current_rsi_14,
                    'updown_length': current_updown,
                    'roc_rank': current_roc_rank,
                    'sma_20': current_sma_20,
                    'ema_50': current_ema_50,
                    'volume_ratio': current_volume / avg_volume,
                    'atr': current_atr,
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
    
    def _calculate_updown_length(self, data: pd.DataFrame) -> pd.Series:
        """
        Calculate UpDown Length - consecutive up/down days streak
        """
        try:
            # Calculate daily price changes
            price_changes = data['close'].diff()
            
            # Initialize streak series
            updown_length = pd.Series(0, index=data.index)
            
            current_streak = 0
            
            for i in range(1, len(data)):
                if price_changes.iloc[i] > 0:  # Up day
                    if current_streak >= 0:
                        current_streak += 1
                    else:
                        current_streak = 1
                elif price_changes.iloc[i] < 0:  # Down day
                    if current_streak <= 0:
                        current_streak -= 1
                    else:
                        current_streak = -1
                else:  # Unchanged
                    current_streak = 0
                
                updown_length.iloc[i] = current_streak
            
            return updown_length
            
        except Exception as e:
            self.logger.error(f"Error calculating UpDown Length: {e}")
            return pd.Series(0, index=data.index)
    
    def _calculate_roc_rank(self, data: pd.DataFrame, period: int) -> pd.Series:
        """
        Calculate Rate of Change Rank (percentile rank of ROC over period)
        """
        try:
            # Calculate Rate of Change
            roc = data['close'].pct_change(periods=1) * 100
            
            # Calculate rolling percentile rank
            roc_rank = roc.rolling(window=period).rank(pct=True) * 100
            
            return roc_rank.fillna(50)  # Neutral rank for NaN values
            
        except Exception as e:
            self.logger.error(f"Error calculating ROC Rank: {e}")
            return pd.Series(50, index=data.index)
    
    def _calculate_connors_rsi(self, rsi_3: pd.Series, updown_length: pd.Series, roc_rank: pd.Series) -> pd.Series:
        """
        Calculate Connors RSI as average of three components
        """
        try:
            # Convert UpDown Length to percentile rank
            updown_rank = updown_length.rolling(window=100).rank(pct=True) * 100
            updown_rank = updown_rank.fillna(50)
            
            # Calculate Connors RSI as average of three components
            crsi = (rsi_3 + updown_rank + roc_rank) / 3
            
            return crsi.fillna(50)  # Neutral CRSI for NaN values
            
        except Exception as e:
            self.logger.error(f"Error calculating Connors RSI: {e}")
            return pd.Series(50, index=rsi_3.index)
    
    def _calculate_volume_weighted_crsi(self, data: pd.DataFrame, crsi: pd.Series) -> pd.Series:
        """
        Calculate volume-weighted CRSI for enhanced accuracy
        """
        try:
            # Apply volume weighting using exponential moving average
            volume_weights = data['volume'] / data['volume'].rolling(window=20).mean()
            volume_weights = volume_weights.fillna(1.0).clip(0.1, 3.0)  # Reasonable bounds
            
            # Volume-weighted CRSI using EMA with volume-adjusted alpha
            vw_crsi = pd.Series(index=data.index, dtype=float)
            vw_crsi.iloc[0] = crsi.iloc[0]
            
            for i in range(1, len(data)):
                alpha = min(0.5, volume_weights.iloc[i] * 0.1)  # Volume-adjusted smoothing
                vw_crsi.iloc[i] = alpha * crsi.iloc[i] + (1 - alpha) * vw_crsi.iloc[i-1]
            
            return vw_crsi
            
        except Exception as e:
            self.logger.error(f"Error calculating volume-weighted CRSI: {e}")
            return crsi
    
    def _update_adaptive_thresholds(self, data: pd.DataFrame) -> None:
        """
        Update CRSI thresholds based on current market volatility
        """
        try:
            # Calculate recent volatility
            if len(data) >= 20:
                recent_returns = data['close'].pct_change().iloc[-20:]
                volatility = recent_returns.std() * np.sqrt(252)  # Annualized
                
                # Calculate recent CRSI distribution
                if len(data) >= 100:
                    # Calculate CRSI for recent period
                    recent_data = data.iloc[-100:]
                    rsi_3 = self.technical_indicators.rsi(recent_data['close'], period=self.rsi_period)
                    updown_length = self._calculate_updown_length(recent_data)
                    roc_rank = self._calculate_roc_rank(recent_data, min(self.roc_period, len(recent_data)))
                    recent_crsi = self._calculate_connors_rsi(rsi_3, updown_length, roc_rank)
                    
                    crsi_std = recent_crsi.std()
                    crsi_mean = recent_crsi.mean()
                    
                    if volatility > 0.3:  # High volatility
                        # Use more extreme thresholds in volatile markets
                        self.adaptive_oversold = max(5, self.crsi_oversold - 5)
                        self.adaptive_overbought = min(95, self.crsi_overbought + 5)
                        
                    elif volatility < 0.15:  # Low volatility
                        # Use less extreme thresholds in calm markets
                        self.adaptive_oversold = min(20, self.crsi_oversold + 5)
                        self.adaptive_overbought = max(80, self.crsi_overbought - 5)
                        
                    else:
                        # Adaptive thresholds based on recent CRSI distribution
                        self.adaptive_oversold = max(5, crsi_mean - 1.5 * crsi_std)
                        self.adaptive_overbought = min(95, crsi_mean + 1.5 * crsi_std)
                        
                    # Ensure reasonable bounds
                    self.adaptive_oversold = max(2, min(25, self.adaptive_oversold))
                    self.adaptive_overbought = max(75, min(98, self.adaptive_overbought))
                    
        except Exception as e:
            self.logger.error(f"Error updating adaptive thresholds: {e}")
            self.adaptive_oversold = self.crsi_oversold
            self.adaptive_overbought = self.crsi_overbought
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters based on CRSI extremes,
        volatility, and signal strength.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('price', data['close'].iloc[-1])
            current_crsi = metadata.get('connors_rsi', 50)
            current_vw_crsi = metadata.get('volume_weighted_crsi', 50)
            current_atr = metadata.get('atr', 0)
            updown_length = metadata.get('updown_length', 0)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.4,
                SignalStrength.MEDIUM: 0.7,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Adjust size based on CRSI extremes (more extreme = larger position)
            if signal.signal_type == SignalType.BUY:
                # More oversold = larger position
                crsi_multiplier = min(2.0, (20 - current_crsi) / 15) if current_crsi < 20 else 1.0
            elif signal.signal_type == SignalType.SELL:
                # More overbought = larger position
                crsi_multiplier = min(2.0, (current_crsi - 80) / 15) if current_crsi > 80 else 1.0
            else:
                crsi_multiplier = 1.0
            
            # Volume-weighted CRSI confirmation bonus
            vw_confirmation_multiplier = 1.0
            if signal.signal_type == SignalType.BUY and current_vw_crsi <= self.adaptive_oversold:
                vw_confirmation_multiplier = 1.2
            elif signal.signal_type == SignalType.SELL and current_vw_crsi >= self.adaptive_overbought:
                vw_confirmation_multiplier = 1.2
            
            # Streak length adjustment (longer streaks = more opportunity)
            streak_multiplier = 1.0
            if signal.signal_type == SignalType.BUY and updown_length <= -2:
                streak_multiplier = min(1.5, 1.0 + abs(updown_length) * 0.1)
            elif signal.signal_type == SignalType.SELL and updown_length >= 2:
                streak_multiplier = min(1.5, 1.0 + updown_length * 0.1)
            
            # Adjust size based on market regime
            regime_multiplier = {
                MarketRegime.BULL: 1.0,
                MarketRegime.BEAR: 1.0,
                MarketRegime.SIDEWAYS: 1.3,  # CRSI works best in sideways markets
                MarketRegime.HIGH_VOLATILITY: 0.8,
                MarketRegime.LOW_VOLATILITY: 1.1
            }.get(self.current_regime, 1.0)
            
            # Calculate final position size
            position_size = (base_size * strength_multiplier * crsi_multiplier * 
                           vw_confirmation_multiplier * streak_multiplier * regime_multiplier)
            position_size = min(position_size, self.max_position_size * 1.5)  # Allow slight oversize for strong signals
            
            # Calculate stop loss and take profit levels
            if signal.signal_type == SignalType.BUY:
                # Stop loss based on ATR or recent swing low
                atr_stop = current_price - (current_atr * self.stop_loss_atr_multiplier)
                
                # CRSI-based stop (below recent low with buffer)
                recent_low = data['low'].iloc[-5:].min()
                crsi_stop = recent_low * 0.98
                
                stop_loss = max(atr_stop, crsi_stop)  # Use closer stop
                
                # Take profit based on risk/reward ratio
                risk_amount = current_price - stop_loss
                take_profit = current_price + (risk_amount * self.profit_target_ratio)
                
            elif signal.signal_type == SignalType.SELL:
                # Stop loss based on ATR or recent swing high
                atr_stop = current_price + (current_atr * self.stop_loss_atr_multiplier)
                
                # CRSI-based stop (above recent high with buffer)
                recent_high = data['high'].iloc[-5:].max()
                crsi_stop = recent_high * 1.02
                
                stop_loss = min(atr_stop, crsi_stop)  # Use closer stop
                
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
                volatility_adjustment=abs(current_crsi - 50) / 50  # 0 to 1 scale
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
                current_crsi = primary_signal.metadata.get('connors_rsi', 50)
                
                # Exit conditions for long position
                if current_qty > 0:
                    # CRSI mean reversion exit - when CRSI moves to opposite extreme or neutral
                    if current_crsi >= 60 or current_crsi >= self.adaptive_overbought * 0.7:
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"CRSI mean reversion exit: CRSI={current_crsi:.1f}"
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
                    # CRSI mean reversion exit - when CRSI moves to opposite extreme or neutral
                    if current_crsi <= 40 or current_crsi <= self.adaptive_oversold * 1.3:
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"CRSI mean reversion exit: CRSI={current_crsi:.1f}"
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
                    reason=f"CRSI oversold: {primary_signal.metadata.get('connors_rsi', 0):.1f}"
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('price') * 1.001,  # Slight premium
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"CRSI overbought: {primary_signal.metadata.get('connors_rsi', 0):.1f}"
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
                
                # Track CRSI levels at entry/exit
                self.performance_metrics.add_custom_metric(
                    'crsi_at_signal', 
                    signal_metadata.get('connors_rsi', 50)
                )
                
                self.performance_metrics.add_custom_metric(
                    'volume_weighted_crsi_at_signal', 
                    signal_metadata.get('volume_weighted_crsi', 50)
                )
                
                # Track component values at signal
                self.performance_metrics.add_custom_metric(
                    'rsi_3_at_signal', 
                    signal_metadata.get('rsi_3', 50)
                )
                
                self.performance_metrics.add_custom_metric(
                    'updown_length_at_signal',
                    signal_metadata.get('updown_length', 0)
                )
                
                self.performance_metrics.add_custom_metric(
                    'roc_rank_at_signal',
                    signal_metadata.get('roc_rank', 50)
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
                    signal_metadata.get('adaptive_oversold', self.crsi_oversold)
                )
                
                self.performance_metrics.add_custom_metric(
                    'adaptive_overbought_threshold',
                    signal_metadata.get('adaptive_overbought', self.crsi_overbought)
                )
            
            # Calculate strategy-specific performance ratios
            trades = self.performance_metrics.get_trades()
            if len(trades) >= 10:
                # Extreme CRSI signal success rate
                extreme_signals = [trade for trade in trades[-20:] 
                                 if trade.get('entry_crsi', 50) <= 10 or trade.get('entry_crsi', 50) >= 90]
                if extreme_signals:
                    extreme_success = sum(1 for trade in extreme_signals 
                                        if trade.get('pnl', 0) > 0)
                    extreme_success_rate = extreme_success / len(extreme_signals)
                    
                    self.performance_metrics.add_custom_metric(
                        'extreme_crsi_success_rate',
                        extreme_success_rate
                    )
                
                # Average CRSI at entry
                entry_crsi_levels = [trade.get('entry_crsi', 50) for trade in trades[-20:]]
                avg_entry_crsi_extreme = np.mean([abs(crsi - 50) for crsi in entry_crsi_levels]) if entry_crsi_levels else 0
                
                self.performance_metrics.add_custom_metric(
                    'avg_entry_crsi_extreme',
                    avg_entry_crsi_extreme
                )
                
                # Streak trading success rate
                streak_trades = [trade for trade in trades[-20:] 
                               if abs(trade.get('entry_streak', 0)) >= 2]
                if streak_trades:
                    streak_success = sum(1 for trade in streak_trades 
                                       if trade.get('pnl', 0) > 0)
                    streak_success_rate = streak_success / len(streak_trades)
                    
                    self.performance_metrics.add_custom_metric(
                        'streak_trading_success_rate',
                        streak_success_rate
                    )
                
                # Component alignment success rate
                aligned_trades = [trade for trade in trades[-20:] 
                                if trade.get('components_aligned', False)]
                if aligned_trades:
                    aligned_success = sum(1 for trade in aligned_trades 
                                        if trade.get('pnl', 0) > 0)
                    aligned_success_rate = aligned_success / len(aligned_trades)
                    
                    self.performance_metrics.add_custom_metric(
                        'component_alignment_success_rate',
                        aligned_success_rate
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
            'name': 'Connors RSI Mean Reversion Strategy',
            'version': '1.0',
            'description': 'Mean reversion using Connors RSI with RSI(3), UpDown Length, and ROC components',
            'parameters': {
                'rsi_period': self.rsi_period,
                'roc_period': self.roc_period,
                'crsi_oversold': self.crsi_oversold,
                'crsi_overbought': self.crsi_overbought,
                'volume_confirmation': self.volume_confirmation,
                'trend_filter': self.trend_filter,
                'adaptive_thresholds': self.adaptive_thresholds,
                'min_streak_length': self.min_streak_length,
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