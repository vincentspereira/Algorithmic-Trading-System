#!/usr/bin/env python3
"""
Stochastic Mean Reversion Strategy

Implements a sophisticated mean reversion strategy using Stochastic oscillator with institutional-grade enhancements.
The Stochastic oscillator compares a security's closing price to its price range over a given time period,
identifying overbought and oversold conditions for mean reversion opportunities.

Key Features:
- Dual Stochastic (%K and %D) with adaptive periods
- Volume-weighted Stochastic calculations for enhanced accuracy
- Multi-timeframe confirmation using different Stochastic periods
- Divergence detection between price and Stochastic
- Dynamic position sizing based on Stochastic extremes
- False signal filtering using price action confirmation
- Adaptive thresholds based on market volatility
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
from ..base_strategy import BaseRetailStrategy
from ..core.risk_management import RiskParameters, PositionSizer
from ..core.market_regime import MarketRegimeDetector, MarketRegime
from ..indicators.technical_indicators import TechnicalIndicators
from ..indicators.candlestick_patterns import CandlestickPatterns
from ..core.signal_generator import Signal, SignalType, SignalStrength
from ..core.execution_engine import ExecutionIntent, OrderType
from ..core.performance_tracker import PerformanceMetrics


class StochasticMeanReversionStrategy(BaseRetailStrategy):
    """
    Stochastic Mean Reversion Strategy Implementation
    
    This strategy implements sophisticated mean reversion using Stochastic oscillator with:
    - Dual Stochastic (%K and %D) analysis
    - Volume-weighted calculations for improved accuracy
    - Multi-timeframe confirmation
    - Divergence detection for enhanced signals
    - Dynamic position sizing based on Stochastic extremes
    """
    
    def __init__(self, 
                 symbol: str,
                 k_period: int = 14,
                 d_period: int = 3,
                 smooth_k: int = 3,
                 stoch_oversold: float = 20.0,
                 stoch_overbought: float = 80.0,
                 confirmation_period: int = 21,
                 volume_confirmation: bool = True,
                 divergence_detection: bool = True,
                 adaptive_periods: bool = True,
                 max_position_size: float = 0.1,
                 stop_loss_atr_multiplier: float = 2.0,
                 profit_target_stoch_level: float = 50.0,
                 **kwargs):
        """
        Initialize Stochastic Mean Reversion Strategy
        
        Args:
            symbol: Trading symbol
            k_period: Period for %K calculation (default: 14)
            d_period: Period for %D smoothing (default: 3)
            smooth_k: Period for %K smoothing (default: 3)
            stoch_oversold: Stochastic oversold threshold (default: 20)
            stoch_overbought: Stochastic overbought threshold (default: 80)
            confirmation_period: Period for confirmation Stochastic (default: 21)
            volume_confirmation: Use volume for signal confirmation
            divergence_detection: Detect price/Stochastic divergences
            adaptive_periods: Adapt periods based on market volatility
            max_position_size: Maximum position size as fraction of portfolio
            stop_loss_atr_multiplier: ATR multiplier for stop loss
            profit_target_stoch_level: Stochastic level for profit taking (default: 50)
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.k_period = k_period
        self.d_period = d_period
        self.smooth_k = smooth_k
        self.stoch_oversold = stoch_oversold
        self.stoch_overbought = stoch_overbought
        self.confirmation_period = confirmation_period
        self.volume_confirmation = volume_confirmation
        self.divergence_detection = divergence_detection
        self.adaptive_periods = adaptive_periods
        self.max_position_size = max_position_size
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.profit_target_stoch_level = profit_target_stoch_level
        
        # Initialize components
        self.technical_indicators = TechnicalIndicators()
        self.candlestick_patterns = CandlestickPatterns()
        self.market_regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.adaptive_k_period = k_period
        self.adaptive_oversold = stoch_oversold
        self.adaptive_overbought = stoch_overbought
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate Stochastic mean reversion signals with volume confirmation,
        divergence detection, and multi-timeframe analysis.
        """
        if len(data) < max(self.k_period, self.confirmation_period) + 20:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Update adaptive parameters
            if self.adaptive_periods:
                self._update_adaptive_parameters(data)
            
            # Calculate Stochastic oscillator
            stoch_k, stoch_d = self.technical_indicators.stochastic(
                data['high'], 
                data['low'], 
                data['close'],
                k_period=self.adaptive_k_period,
                d_period=self.d_period,
                smooth_k=self.smooth_k,
                volume_weighted=True,
                volume=data['volume'] if self.volume_confirmation else None
            )
            
            # Calculate confirmation Stochastic (longer period)
            stoch_k_long, stoch_d_long = self.technical_indicators.stochastic(
                data['high'], 
                data['low'], 
                data['close'],
                k_period=self.confirmation_period,
                d_period=self.d_period,
                smooth_k=self.smooth_k
            )
            
            # Calculate additional indicators
            rsi = self.technical_indicators.rsi(data['close'], period=14)
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            atr = self.technical_indicators.atr(data, period=14)
            sma_20 = self.technical_indicators.sma(data['close'], period=20)
            ema_50 = self.technical_indicators.ema(data['close'], period=50)
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            current_stoch_k = stoch_k.iloc[-1]
            current_stoch_d = stoch_d.iloc[-1]
            current_stoch_k_long = stoch_k_long.iloc[-1]
            current_stoch_d_long = stoch_d_long.iloc[-1]
            current_rsi = rsi.iloc[-1]
            current_atr = atr.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_ema_50 = ema_50.iloc[-1]
            
            # Detect divergences if enabled
            bullish_divergence = False
            bearish_divergence = False
            
            if self.divergence_detection and len(data) >= 40:
                bullish_divergence = self._detect_bullish_divergence(data, stoch_k)
                bearish_divergence = self._detect_bearish_divergence(data, stoch_k)
            
            # Generate primary signals
            signal_strength = SignalStrength.WEAK
            signal_type = SignalType.HOLD
            confidence = 0.5
            
            # Long signal conditions (Stochastic oversold)
            if (current_stoch_k <= self.adaptive_oversold and 
                current_stoch_d <= self.adaptive_oversold):
                signal_type = SignalType.BUY
                signal_strength = SignalStrength.MEDIUM
                confidence = 0.6
                
                # Enhance signal with confirmations
                confirmations = 0
                
                # %K and %D crossover (bullish)
                if len(stoch_k) >= 2 and len(stoch_d) >= 2:
                    if (stoch_k.iloc[-1] > stoch_d.iloc[-1] and 
                        stoch_k.iloc[-2] <= stoch_d.iloc[-2]):
                        confirmations += 2  # Strong bullish signal
                
                # Confirmation Stochastic also oversold
                if current_stoch_k_long <= self.adaptive_oversold + 10:
                    confirmations += 1
                    
                # RSI confirmation (not extremely oversold to avoid falling knife)
                if 25 < current_rsi < 45:
                    confirmations += 1
                    
                # Volume confirmation
                if self.volume_confirmation and current_volume > avg_volume * 0.8:
                    confirmations += 1
                    
                # Price above longer-term average (uptrend context)
                if current_price > current_ema_50:
                    confirmations += 1
                    
                # Bullish divergence confirmation
                if bullish_divergence:
                    confirmations += 2  # Strong confirmation
                    
                # Price action confirmation - hammer or bullish patterns
                if len(data) >= 3:
                    recent_candles = data.iloc[-3:]
                    patterns = self.candlestick_patterns.detect_patterns(recent_candles)
                    if any(pattern in ['hammer', 'bullish_engulfing', 'morning_star'] 
                           for pattern in patterns):
                        confirmations += 1
                
                # Double bottom in Stochastic (very strong mean reversion signal)
                if self._detect_stochastic_double_bottom(stoch_k):
                    confirmations += 2
                
                # Adjust signal strength based on confirmations
                if confirmations >= 5:
                    signal_strength = SignalStrength.STRONG
                    confidence = 0.85
                elif confirmations >= 3:
                    signal_strength = SignalStrength.MEDIUM
                    confidence = 0.75
                    
            # Short signal conditions (Stochastic overbought)
            elif (current_stoch_k >= self.adaptive_overbought and 
                  current_stoch_d >= self.adaptive_overbought):
                signal_type = SignalType.SELL
                signal_strength = SignalStrength.MEDIUM
                confidence = 0.6
                
                # Enhance signal with confirmations
                confirmations = 0
                
                # %K and %D crossover (bearish)
                if len(stoch_k) >= 2 and len(stoch_d) >= 2:
                    if (stoch_k.iloc[-1] < stoch_d.iloc[-1] and 
                        stoch_k.iloc[-2] >= stoch_d.iloc[-2]):
                        confirmations += 2  # Strong bearish signal
                
                # Confirmation Stochastic also overbought
                if current_stoch_k_long >= self.adaptive_overbought - 10:
                    confirmations += 1
                    
                # RSI confirmation (not extremely overbought)
                if 55 < current_rsi < 75:
                    confirmations += 1
                    
                # Volume confirmation
                if self.volume_confirmation and current_volume > avg_volume * 0.8:
                    confirmations += 1
                    
                # Price below longer-term average (downtrend context)
                if current_price < current_ema_50:
                    confirmations += 1
                    
                # Bearish divergence confirmation
                if bearish_divergence:
                    confirmations += 2  # Strong confirmation
                    
                # Price action confirmation - shooting star or bearish patterns
                if len(data) >= 3:
                    recent_candles = data.iloc[-3:]
                    patterns = self.candlestick_patterns.detect_patterns(recent_candles)
                    if any(pattern in ['shooting_star', 'bearish_engulfing', 'evening_star'] 
                           for pattern in patterns):
                        confirmations += 1
                
                # Double top in Stochastic (very strong mean reversion signal)
                if self._detect_stochastic_double_top(stoch_k):
                    confirmations += 2
                
                # Adjust signal strength based on confirmations
                if confirmations >= 5:
                    signal_strength = SignalStrength.STRONG
                    confidence = 0.85
                elif confirmations >= 3:
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
                    'stoch_k': current_stoch_k,
                    'stoch_d': current_stoch_d,
                    'stoch_k_long': current_stoch_k_long,
                    'stoch_d_long': current_stoch_d_long,
                    'rsi': current_rsi,
                    'sma_20': current_sma_20,
                    'ema_50': current_ema_50,
                    'volume_ratio': current_volume / avg_volume,
                    'atr': current_atr,
                    'bullish_divergence': bullish_divergence,
                    'bearish_divergence': bearish_divergence,
                    'adaptive_k_period': self.adaptive_k_period,
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
    
    def _detect_stochastic_double_bottom(self, stoch_k: pd.Series) -> bool:
        """
        Detect double bottom pattern in Stochastic %K
        """
        try:
            if len(stoch_k) < 20:
                return False
                
            recent_stoch = stoch_k.iloc[-20:]
            
            # Find local minima
            minima_indices = []
            for i in range(2, len(recent_stoch) - 2):
                if (recent_stoch.iloc[i] < recent_stoch.iloc[i-1] and 
                    recent_stoch.iloc[i] < recent_stoch.iloc[i-2] and
                    recent_stoch.iloc[i] < recent_stoch.iloc[i+1] and 
                    recent_stoch.iloc[i] < recent_stoch.iloc[i+2]):
                    minima_indices.append(i)
            
            # Check for double bottom pattern
            if len(minima_indices) >= 2:
                # Get the two most recent minima
                first_min_idx = minima_indices[-2]
                second_min_idx = minima_indices[-1]
                
                first_min_val = recent_stoch.iloc[first_min_idx]
                second_min_val = recent_stoch.iloc[second_min_idx]
                
                # Double bottom criteria:
                # 1. Both minima should be in oversold territory
                # 2. Second minimum should be similar to first (within 5 points)
                # 3. There should be a peak between them
                if (first_min_val <= 25 and second_min_val <= 25 and
                    abs(first_min_val - second_min_val) <= 5):
                    
                    # Check for peak between minima
                    between_max = recent_stoch.iloc[first_min_idx:second_min_idx].max()
                    if between_max > max(first_min_val, second_min_val) + 10:
                        return True
                        
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting Stochastic double bottom: {e}")
            return False
    
    def _detect_stochastic_double_top(self, stoch_k: pd.Series) -> bool:
        """
        Detect double top pattern in Stochastic %K
        """
        try:
            if len(stoch_k) < 20:
                return False
                
            recent_stoch = stoch_k.iloc[-20:]
            
            # Find local maxima
            maxima_indices = []
            for i in range(2, len(recent_stoch) - 2):
                if (recent_stoch.iloc[i] > recent_stoch.iloc[i-1] and 
                    recent_stoch.iloc[i] > recent_stoch.iloc[i-2] and
                    recent_stoch.iloc[i] > recent_stoch.iloc[i+1] and 
                    recent_stoch.iloc[i] > recent_stoch.iloc[i+2]):
                    maxima_indices.append(i)
            
            # Check for double top pattern
            if len(maxima_indices) >= 2:
                # Get the two most recent maxima
                first_max_idx = maxima_indices[-2]
                second_max_idx = maxima_indices[-1]
                
                first_max_val = recent_stoch.iloc[first_max_idx]
                second_max_val = recent_stoch.iloc[second_max_idx]
                
                # Double top criteria:
                # 1. Both maxima should be in overbought territory
                # 2. Second maximum should be similar to first (within 5 points)
                # 3. There should be a trough between them
                if (first_max_val >= 75 and second_max_val >= 75 and
                    abs(first_max_val - second_max_val) <= 5):
                    
                    # Check for trough between maxima
                    between_min = recent_stoch.iloc[first_max_idx:second_max_idx].min()
                    if between_min < min(first_max_val, second_max_val) - 10:
                        return True
                        
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting Stochastic double top: {e}")
            return False
    
    def _detect_bullish_divergence(self, data: pd.DataFrame, stoch_k: pd.Series) -> bool:
        """
        Detect bullish divergence between price and Stochastic %K
        """
        try:
            if len(data) < 20:
                return False
                
            # Look for recent lows in price and Stochastic
            recent_data = data.iloc[-20:]
            recent_stoch = stoch_k.iloc[-20:]
            
            # Check if we have a more recent low in price but higher low in Stochastic
            if len(recent_data) >= 10:
                # Get the last 10 periods
                very_recent_data = recent_data.iloc[-10:]
                very_recent_stoch = recent_stoch.iloc[-10:]
                
                recent_price_low = very_recent_data['low'].min()
                recent_stoch_low = very_recent_stoch.min()
                
                # Earlier period (10-20 periods ago)
                earlier_data = recent_data.iloc[-20:-10]
                earlier_stoch = recent_stoch.iloc[-20:-10]
                
                earlier_price_low = earlier_data['low'].min()
                earlier_stoch_low = earlier_stoch.min()
                
                # Bullish divergence: lower price low but higher Stochastic low
                if (recent_price_low < earlier_price_low and 
                    recent_stoch_low > earlier_stoch_low and
                    recent_stoch_low <= 30):  # Must be in oversold territory
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting bullish divergence: {e}")
            return False
    
    def _detect_bearish_divergence(self, data: pd.DataFrame, stoch_k: pd.Series) -> bool:
        """
        Detect bearish divergence between price and Stochastic %K
        """
        try:
            if len(data) < 20:
                return False
                
            # Look for recent highs in price and Stochastic
            recent_data = data.iloc[-20:]
            recent_stoch = stoch_k.iloc[-20:]
            
            # Check if we have a more recent high in price but lower high in Stochastic
            if len(recent_data) >= 10:
                # Get the last 10 periods
                very_recent_data = recent_data.iloc[-10:]
                very_recent_stoch = recent_stoch.iloc[-10:]
                
                recent_price_high = very_recent_data['high'].max()
                recent_stoch_high = very_recent_stoch.max()
                
                # Earlier period (10-20 periods ago)
                earlier_data = recent_data.iloc[-20:-10]
                earlier_stoch = recent_stoch.iloc[-20:-10]
                
                earlier_price_high = earlier_data['high'].max()
                earlier_stoch_high = earlier_stoch.max()
                
                # Bearish divergence: higher price high but lower Stochastic high
                if (recent_price_high > earlier_price_high and 
                    recent_stoch_high < earlier_stoch_high and
                    recent_stoch_high >= 70):  # Must be in overbought territory
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting bearish divergence: {e}")
            return False
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters based on Stochastic extremes,
        volatility, and signal strength.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('price', data['close'].iloc[-1])
            current_stoch_k = metadata.get('stoch_k', 50)
            current_stoch_d = metadata.get('stoch_d', 50)
            current_atr = metadata.get('atr', 0)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.4,
                SignalStrength.MEDIUM: 0.7,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Adjust size based on Stochastic extremes (more extreme = larger position)
            if signal.signal_type == SignalType.BUY:
                # More oversold = larger position
                stoch_multiplier = min(1.5, (30 - current_stoch_k) / 20) if current_stoch_k < 30 else 1.0
            elif signal.signal_type == SignalType.SELL:
                # More overbought = larger position
                stoch_multiplier = min(1.5, (current_stoch_k - 70) / 20) if current_stoch_k > 70 else 1.0
            else:
                stoch_multiplier = 1.0
            
            # %K and %D alignment bonus
            alignment_multiplier = 1.0
            if signal.signal_type == SignalType.BUY and current_stoch_k > current_stoch_d:
                alignment_multiplier = 1.2  # Bullish crossover
            elif signal.signal_type == SignalType.SELL and current_stoch_k < current_stoch_d:
                alignment_multiplier = 1.2  # Bearish crossover
            
            # Adjust size based on market regime
            regime_multiplier = {
                MarketRegime.BULL: 1.1,
                MarketRegime.BEAR: 0.9,
                MarketRegime.SIDEWAYS: 1.2,  # Mean reversion works best in sideways markets
                MarketRegime.HIGH_VOLATILITY: 0.7,
                MarketRegime.LOW_VOLATILITY: 1.1
            }.get(self.current_regime, 1.0)
            
            # Divergence bonus
            divergence_multiplier = 1.0
            if metadata.get('bullish_divergence') or metadata.get('bearish_divergence'):
                divergence_multiplier = 1.3
            
            # Calculate final position size
            position_size = (base_size * strength_multiplier * stoch_multiplier * 
                           alignment_multiplier * regime_multiplier * divergence_multiplier)
            position_size = min(position_size, self.max_position_size * 1.5)  # Allow slight oversize for strong signals
            
            # Calculate stop loss and take profit levels
            if signal.signal_type == SignalType.BUY:
                # Stop loss based on ATR or recent swing low
                atr_stop = current_price - (current_atr * self.stop_loss_atr_multiplier)
                
                # Find recent swing low for stop
                if len(data) >= 10:
                    recent_low = data['low'].iloc[-10:].min()
                    swing_stop = recent_low * 0.995
                    stop_loss = max(atr_stop, swing_stop)  # Use closer stop
                else:
                    stop_loss = atr_stop
                
                # Take profit when Stochastic reaches target level
                target_multiplier = (30 - current_stoch_k) / 100 if current_stoch_k < 30 else 0.02
                take_profit = current_price * (1 + target_multiplier)
                
            elif signal.signal_type == SignalType.SELL:
                # Stop loss based on ATR or recent swing high
                atr_stop = current_price + (current_atr * self.stop_loss_atr_multiplier)
                
                # Find recent swing high for stop
                if len(data) >= 10:
                    recent_high = data['high'].iloc[-10:].max()
                    swing_stop = recent_high * 1.005
                    stop_loss = min(atr_stop, swing_stop)  # Use closer stop
                else:
                    stop_loss = atr_stop
                
                # Take profit when Stochastic reaches target level
                target_multiplier = (current_stoch_k - 70) / 100 if current_stoch_k > 70 else 0.02
                take_profit = current_price * (1 - target_multiplier)
                
            else:
                stop_loss = None
                take_profit = None
            
            return RiskParameters(
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_risk_per_trade=0.025,  # Slightly higher for mean reversion
                risk_reward_ratio=1.8,
                volatility_adjustment=abs(current_stoch_k - 50) / 50
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
                current_stoch_k = primary_signal.metadata.get('stoch_k', 50)
                current_stoch_d = primary_signal.metadata.get('stoch_d', 50)
                
                # Exit conditions for long position
                if current_qty > 0:
                    # Stochastic exit - when %K reaches target level or becomes overbought
                    if (current_stoch_k >= self.profit_target_stoch_level or 
                        current_stoch_k >= 75 or
                        (current_stoch_k < current_stoch_d and current_stoch_k > 70)):  # Bearish crossover in overbought
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stochastic mean reversion exit: %K={current_stoch_k:.1f}, %D={current_stoch_d:.1f}"
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
                    # Stochastic exit - when %K reaches target level or becomes oversold
                    if (current_stoch_k <= self.profit_target_stoch_level or 
                        current_stoch_k <= 25 or
                        (current_stoch_k > current_stoch_d and current_stoch_k < 30)):  # Bullish crossover in oversold
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stochastic mean reversion exit: %K={current_stoch_k:.1f}, %D={current_stoch_d:.1f}"
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
                    reason=f"Stochastic oversold: %K={primary_signal.metadata.get('stoch_k', 0):.1f}, %D={primary_signal.metadata.get('stoch_d', 0):.1f}"
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('price') * 1.001,  # Slight premium
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"Stochastic overbought: %K={primary_signal.metadata.get('stoch_k', 0):.1f}, %D={primary_signal.metadata.get('stoch_d', 0):.1f}"
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
                
                # Track Stochastic levels at entry/exit
                self.performance_metrics.add_custom_metric(
                    'stoch_k_at_signal', 
                    signal_metadata.get('stoch_k', 50)
                )
                
                self.performance_metrics.add_custom_metric(
                    'stoch_d_at_signal', 
                    signal_metadata.get('stoch_d', 50)
                )
                
                # Track divergence detection rate
                has_divergence = (signal_metadata.get('bullish_divergence', False) or 
                                signal_metadata.get('bearish_divergence', False))
                self.performance_metrics.add_custom_metric(
                    'divergence_detection_rate',
                    1.0 if has_divergence else 0.0
                )
                
                # Track volume confirmation rate
                volume_ratio = signal_metadata.get('volume_ratio', 1.0)
                self.performance_metrics.add_custom_metric(
                    'volume_confirmation_rate',
                    1.0 if volume_ratio > 0.8 else 0.0
                )
                
                # Track adaptive parameter effectiveness
                self.performance_metrics.add_custom_metric(
                    'adaptive_k_period',
                    signal_metadata.get('adaptive_k_period', self.k_period)
                )
            
            # Calculate strategy-specific performance ratios
            trades = self.performance_metrics.get_trades()
            if len(trades) >= 10:
                # Mean reversion success rate
                successful_reversions = sum(1 for trade in trades[-20:] 
                                          if trade.get('pnl', 0) > 0)
                reversion_success_rate = successful_reversions / min(20, len(trades))
                
                self.performance_metrics.add_custom_metric(
                    'mean_reversion_success_rate',
                    reversion_success_rate
                )
                
                # Average Stochastic %K at entry
                entry_stoch_levels = [trade.get('entry_stoch_k', 50) for trade in trades[-20:]]
                avg_entry_stoch_extreme = np.mean([abs(stoch - 50) for stoch in entry_stoch_levels]) if entry_stoch_levels else 0
                
                self.performance_metrics.add_custom_metric(
                    'avg_entry_stoch_extreme',
                    avg_entry_stoch_extreme
                )
                
                # Crossover signal success rate
                crossover_trades = [trade for trade in trades[-20:] 
                                  if trade.get('had_crossover', False)]
                if crossover_trades:
                    crossover_success = sum(1 for trade in crossover_trades 
                                          if trade.get('pnl', 0) > 0)
                    crossover_success_rate = crossover_success / len(crossover_trades)
                    
                    self.performance_metrics.add_custom_metric(
                        'crossover_signal_success_rate',
                        crossover_success_rate
                    )
                
                # Double bottom/top pattern success rate
                pattern_trades = [trade for trade in trades[-20:] 
                                if trade.get('had_double_pattern', False)]
                if pattern_trades:
                    pattern_success = sum(1 for trade in pattern_trades 
                                        if trade.get('pnl', 0) > 0)
                    pattern_success_rate = pattern_success / len(pattern_trades)
                    
                    self.performance_metrics.add_custom_metric(
                        'double_pattern_success_rate',
                        pattern_success_rate
                    )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _update_adaptive_parameters(self, data: pd.DataFrame) -> None:
        """
        Update Stochastic parameters based on current market volatility
        """
        try:
            # Calculate recent volatility
            if len(data) >= 20:
                recent_returns = data['close'].pct_change().iloc[-20:]
                volatility = recent_returns.std() * np.sqrt(252)  # Annualized
                
                if volatility > 0.3:  # High volatility
                    # Use shorter periods for faster signals
                    self.adaptive_k_period = max(7, self.k_period - 3)
                    # Use more extreme thresholds
                    self.adaptive_oversold = max(10, self.stoch_oversold - 5)
                    self.adaptive_overbought = min(95, self.stoch_overbought + 5)
                    
                elif volatility < 0.15:  # Low volatility
                    # Use longer periods for more stable signals
                    self.adaptive_k_period = min(21, self.k_period + 3)
                    # Use less extreme thresholds
                    self.adaptive_oversold = min(30, self.stoch_oversold + 5)
                    self.adaptive_overbought = max(70, self.stoch_overbought - 5)
                    
                else:
                    # Default parameters
                    self.adaptive_k_period = self.k_period
                    self.adaptive_oversold = self.stoch_oversold
                    self.adaptive_overbought = self.stoch_overbought
                    
        except Exception as e:
            self.logger.error(f"Error updating adaptive parameters: {e}")
    
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
            max_risk_per_trade=0.025,
            risk_reward_ratio=1.8,
            volatility_adjustment=0.5
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information and current parameters"""
        return {
            'name': 'Stochastic Mean Reversion Strategy',
            'version': '1.0',
            'description': 'Mean reversion using Stochastic oscillator with crossover and divergence detection',
            'parameters': {
                'k_period': self.k_period,
                'd_period': self.d_period,
                'smooth_k': self.smooth_k,
                'stoch_oversold': self.stoch_oversold,
                'stoch_overbought': self.stoch_overbought,
                'confirmation_period': self.confirmation_period,
                'volume_confirmation': self.volume_confirmation,
                'divergence_detection': self.divergence_detection,
                'adaptive_periods': self.adaptive_periods,
                'max_position_size': self.max_position_size,
                'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
                'profit_target_stoch_level': self.profit_target_stoch_level
            },
            'current_state': {
                'market_regime': self.current_regime.value,
                'adaptive_k_period': self.adaptive_k_period,
                'adaptive_oversold': self.adaptive_oversold,
                'adaptive_overbought': self.adaptive_overbought
            },
            'asset_classes': ['stocks', 'etfs', 'futures', 'forex'],
            'timeframes': ['5min', '15min', '1h', '4h', '1d'],
            'market_conditions': ['sideways', 'volatile', 'mean_reverting']
        }