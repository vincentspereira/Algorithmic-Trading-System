#!/usr/bin/env python3
"""
Bollinger Bands Mean Reversion Strategy

Implements a sophisticated mean reversion strategy using Bollinger Bands with institutional-grade enhancements.
This strategy capitalizes on price extremes relative to the moving average, using band touches as reversal signals.

Key Features:
- Dynamic Bollinger Bands with adaptive periods
- Volume-weighted band calculations for enhanced accuracy
- Multi-timeframe confirmation using different band periods
- Squeeze detection for volatility breakout filtering
- Dynamic position sizing based on band width
- False breakout filtering using price action confirmation
- Adaptive parameters based on market regime
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


class BollingerBandsMeanReversionStrategy(BaseRetailStrategy):
    """
    Bollinger Bands Mean Reversion Strategy Implementation
    
    This strategy implements sophisticated mean reversion using Bollinger Bands with:
    - Dynamic band calculations with volume weighting
    - Multi-timeframe confirmation
    - Squeeze detection for volatility filtering
    - Adaptive position sizing based on band width
    - Advanced risk management
    """
    
    def __init__(self, 
                 symbol: str,
                 bb_period: int = 20,
                 bb_std_dev: float = 2.0,
                 confirmation_period: int = 50,
                 volume_confirmation: bool = True,
                 squeeze_detection: bool = True,
                 adaptive_bands: bool = True,
                 max_position_size: float = 0.1,
                 stop_loss_atr_multiplier: float = 2.0,
                 profit_target_band_pct: float = 0.5,
                 **kwargs):
        """
        Initialize Bollinger Bands Mean Reversion Strategy
        
        Args:
            symbol: Trading symbol
            bb_period: Period for Bollinger Bands calculation (default: 20)
            bb_std_dev: Standard deviation multiplier for bands (default: 2.0)
            confirmation_period: Period for longer-term trend confirmation (default: 50)
            volume_confirmation: Use volume for signal confirmation
            squeeze_detection: Filter signals during low volatility squeezes
            adaptive_bands: Adapt band parameters based on market regime
            max_position_size: Maximum position size as fraction of portfolio
            stop_loss_atr_multiplier: ATR multiplier for stop loss
            profit_target_band_pct: Percentage of band width for profit target
        """
        super().__init__(symbol, **kwargs)
        
        # Strategy parameters
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.confirmation_period = confirmation_period
        self.volume_confirmation = volume_confirmation
        self.squeeze_detection = squeeze_detection
        self.adaptive_bands = adaptive_bands
        self.max_position_size = max_position_size
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.profit_target_band_pct = profit_target_band_pct
        
        # Initialize components
        self.technical_indicators = TechnicalIndicators()
        self.candlestick_patterns = CandlestickPatterns()
        self.market_regime_detector = MarketRegimeDetector()
        self.position_sizer = PositionSizer()
        
        # Strategy state
        self.current_regime = MarketRegime.NEUTRAL
        self.adaptive_period = bb_period
        self.adaptive_std_dev = bb_std_dev
        self.is_squeeze = False
        
        # Performance tracking
        self.performance_metrics = PerformanceMetrics()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def _generate_signals(self, data: pd.DataFrame) -> List[Signal]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate Bollinger Bands mean reversion signals with volume confirmation
        and multi-timeframe analysis.
        """
        if len(data) < max(self.bb_period, self.confirmation_period) + 10:
            return [self._create_neutral_signal()]
            
        signals = []
        
        try:
            # Update adaptive parameters
            if self.adaptive_bands:
                self._update_adaptive_parameters(data)
            
            # Calculate Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.technical_indicators.bollinger_bands(
                data['close'], 
                period=self.adaptive_period,
                std_dev=self.adaptive_std_dev,
                volume_weighted=True,
                volume=data['volume'] if self.volume_confirmation else None
            )
            
            # Calculate confirmation Bollinger Bands (longer period)
            bb_upper_long, bb_middle_long, bb_lower_long = self.technical_indicators.bollinger_bands(
                data['close'], 
                period=self.confirmation_period,
                std_dev=self.adaptive_std_dev
            )
            
            # Calculate additional indicators
            rsi = self.technical_indicators.rsi(data['close'], period=14)
            volume_sma = self.technical_indicators.sma(data['volume'], period=20)
            atr = self.technical_indicators.atr(data, period=14)
            
            # Calculate band width for squeeze detection
            band_width = (bb_upper - bb_lower) / bb_middle
            band_width_sma = self.technical_indicators.sma(band_width, period=20)
            
            # Detect squeeze conditions
            if self.squeeze_detection:
                self.is_squeeze = band_width.iloc[-1] < band_width_sma.iloc[-1] * 0.8
            
            # Get current values
            current_price = data['close'].iloc[-1]
            current_high = data['high'].iloc[-1]
            current_low = data['low'].iloc[-1]
            current_volume = data['volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            
            current_bb_upper = bb_upper.iloc[-1]
            current_bb_middle = bb_middle.iloc[-1]
            current_bb_lower = bb_lower.iloc[-1]
            current_bb_upper_long = bb_upper_long.iloc[-1]
            current_bb_lower_long = bb_lower_long.iloc[-1]
            
            current_rsi = rsi.iloc[-1]
            current_atr = atr.iloc[-1]
            current_band_width = band_width.iloc[-1]
            
            # Calculate band position (0 = lower band, 1 = upper band)
            band_position = (current_price - current_bb_lower) / (current_bb_upper - current_bb_lower)
            
            # Generate primary signals
            signal_strength = SignalStrength.WEAK
            signal_type = SignalType.HOLD
            confidence = 0.5
            
            # Long signal conditions (price near lower band)
            if (current_low <= current_bb_lower * 1.002 and  # Touch or penetrate lower band
                current_price > current_bb_lower and  # Close above lower band
                not self.is_squeeze):  # Not in squeeze
                
                signal_type = SignalType.BUY
                signal_strength = SignalStrength.MEDIUM
                confidence = 0.6
                
                # Enhance signal with confirmations
                confirmations = 0
                
                # RSI oversold confirmation
                if current_rsi < 35:
                    confirmations += 1
                    
                # Volume confirmation
                if self.volume_confirmation and current_volume > avg_volume * 0.8:
                    confirmations += 1
                    
                # Long-term trend confirmation (price above long-term middle band)
                if current_price > current_bb_middle_long:
                    confirmations += 1
                    
                # Price action confirmation - hammer or doji patterns
                if len(data) >= 3:
                    recent_candles = data.iloc[-3:]
                    patterns = self.candlestick_patterns.detect_patterns(recent_candles)
                    if any(pattern in ['hammer', 'doji', 'bullish_engulfing'] 
                           for pattern in patterns):
                        confirmations += 1
                
                # Band position confirmation (very oversold)
                if band_position < 0.1:
                    confirmations += 1
                
                # Adjust signal strength based on confirmations
                if confirmations >= 3:
                    signal_strength = SignalStrength.STRONG
                    confidence = 0.85
                elif confirmations >= 2:
                    signal_strength = SignalStrength.MEDIUM
                    confidence = 0.75
                    
            # Short signal conditions (price near upper band)
            elif (current_high >= current_bb_upper * 0.998 and  # Touch or penetrate upper band
                  current_price < current_bb_upper and  # Close below upper band
                  not self.is_squeeze):  # Not in squeeze
                
                signal_type = SignalType.SELL
                signal_strength = SignalStrength.MEDIUM
                confidence = 0.6
                
                # Enhance signal with confirmations
                confirmations = 0
                
                # RSI overbought confirmation
                if current_rsi > 65:
                    confirmations += 1
                    
                # Volume confirmation
                if self.volume_confirmation and current_volume > avg_volume * 0.8:
                    confirmations += 1
                    
                # Long-term trend confirmation (price below long-term middle band)
                if current_price < current_bb_middle_long:
                    confirmations += 1
                    
                # Price action confirmation - shooting star or doji patterns
                if len(data) >= 3:
                    recent_candles = data.iloc[-3:]
                    patterns = self.candlestick_patterns.detect_patterns(recent_candles)
                    if any(pattern in ['shooting_star', 'doji', 'bearish_engulfing'] 
                           for pattern in patterns):
                        confirmations += 1
                
                # Band position confirmation (very overbought)
                if band_position > 0.9:
                    confirmations += 1
                
                # Adjust signal strength based on confirmations
                if confirmations >= 3:
                    signal_strength = SignalStrength.STRONG
                    confidence = 0.85
                elif confirmations >= 2:
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
                    'bb_upper': current_bb_upper,
                    'bb_middle': current_bb_middle,
                    'bb_lower': current_bb_lower,
                    'bb_upper_long': current_bb_upper_long,
                    'bb_lower_long': current_bb_lower_long,
                    'band_position': band_position,
                    'band_width': current_band_width,
                    'is_squeeze': self.is_squeeze,
                    'rsi': current_rsi,
                    'volume_ratio': current_volume / avg_volume,
                    'atr': current_atr,
                    'adaptive_period': self.adaptive_period,
                    'adaptive_std_dev': self.adaptive_std_dev,
                    'market_regime': self.current_regime.value
                }
            )
            
            signals.append(signal)
            
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            signals.append(self._create_neutral_signal())
            
        return signals
    
    def _calculate_risk_parameters(self, data: pd.DataFrame, signal: Signal) -> RiskParameters:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate position size and risk parameters based on band width,
        volatility, and signal strength.
        """
        try:
            # Get signal metadata
            metadata = signal.metadata
            current_price = metadata.get('price', data['close'].iloc[-1])
            band_width = metadata.get('band_width', 0.04)
            current_atr = metadata.get('atr', 0)
            
            # Base position size
            base_size = self.max_position_size
            
            # Adjust size based on signal strength
            strength_multiplier = {
                SignalStrength.WEAK: 0.4,
                SignalStrength.MEDIUM: 0.7,
                SignalStrength.STRONG: 1.0
            }.get(signal.strength, 0.5)
            
            # Adjust size based on band width (wider bands = higher volatility = smaller size)
            band_width_multiplier = min(1.0, 0.04 / max(band_width, 0.01))
            
            # Adjust size based on market regime
            regime_multiplier = {
                MarketRegime.BULL: 1.1,
                MarketRegime.BEAR: 0.9,
                MarketRegime.SIDEWAYS: 1.2,  # Mean reversion works best in sideways markets
                MarketRegime.HIGH_VOLATILITY: 0.7,
                MarketRegime.LOW_VOLATILITY: 1.1
            }.get(self.current_regime, 1.0)
            
            # Calculate final position size
            position_size = base_size * strength_multiplier * band_width_multiplier * regime_multiplier
            position_size = min(position_size, self.max_position_size)
            
            # Calculate stop loss and take profit levels
            if signal.signal_type == SignalType.BUY:
                # Stop loss below lower band or ATR-based
                bb_lower = metadata.get('bb_lower', current_price * 0.98)
                atr_stop = current_price - (current_atr * self.stop_loss_atr_multiplier)
                stop_loss = min(bb_lower * 0.995, atr_stop)  # Use tighter of the two
                
                # Take profit at middle band or percentage of band width
                bb_middle = metadata.get('bb_middle', current_price * 1.02)
                band_target = current_price + (metadata.get('bb_upper', current_price * 1.04) - 
                                             current_price) * self.profit_target_band_pct
                take_profit = min(bb_middle, band_target)
                
            elif signal.signal_type == SignalType.SELL:
                # Stop loss above upper band or ATR-based
                bb_upper = metadata.get('bb_upper', current_price * 1.02)
                atr_stop = current_price + (current_atr * self.stop_loss_atr_multiplier)
                stop_loss = max(bb_upper * 1.005, atr_stop)  # Use tighter of the two
                
                # Take profit at middle band or percentage of band width
                bb_middle = metadata.get('bb_middle', current_price * 0.98)
                band_target = current_price - (current_price - 
                                             metadata.get('bb_lower', current_price * 0.96)) * self.profit_target_band_pct
                take_profit = max(bb_middle, band_target)
                
            else:
                stop_loss = None
                take_profit = None
            
            return RiskParameters(
                position_size=position_size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                max_risk_per_trade=0.02,
                risk_reward_ratio=1.5,
                volatility_adjustment=band_width
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
                
                # Exit conditions for long position
                if current_qty > 0:
                    # Mean reversion exit - price reaches middle band
                    bb_middle = primary_signal.metadata.get('bb_middle', 0)
                    if current_price >= bb_middle * 0.999:
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Mean reversion to middle band"
                        )
                    
                    # Stop loss or take profit
                    pnl_pct = (current_price - entry_price) / entry_price
                    if (risk_params.stop_loss and current_price <= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price >= risk_params.take_profit):
                        return ExecutionIntent(
                            action="SELL",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason=f"Stop/Target hit: {pnl_pct:.2%}"
                        )
                
                # Exit conditions for short position
                elif current_qty < 0:
                    # Mean reversion exit - price reaches middle band
                    bb_middle = primary_signal.metadata.get('bb_middle', 0)
                    if current_price <= bb_middle * 1.001:
                        return ExecutionIntent(
                            action="BUY",
                            quantity=abs(current_qty),
                            order_type=OrderType.MARKET,
                            reason="Mean reversion to middle band"
                        )
                    
                    # Stop loss or take profit
                    pnl_pct = (entry_price - current_price) / entry_price
                    if (risk_params.stop_loss and current_price >= risk_params.stop_loss) or \
                       (risk_params.take_profit and current_price <= risk_params.take_profit):
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
                    reason=f"BB lower band touch, position: {primary_signal.metadata.get('band_position', 0):.2f}"
                )
                
            elif primary_signal.signal_type == SignalType.SELL and primary_signal.strength != SignalStrength.WEAK:
                return ExecutionIntent(
                    action="SELL",
                    quantity=risk_params.position_size,
                    order_type=OrderType.LIMIT,
                    limit_price=primary_signal.metadata.get('price') * 1.001,  # Slight premium
                    stop_loss=risk_params.stop_loss,
                    take_profit=risk_params.take_profit,
                    reason=f"BB upper band touch, position: {primary_signal.metadata.get('band_position', 0):.2f}"
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
                
                # Track band position at entry/exit
                self.performance_metrics.add_custom_metric(
                    'band_position_at_signal', 
                    signal_metadata.get('band_position', 0.5)
                )
                
                # Track band width at signal
                self.performance_metrics.add_custom_metric(
                    'band_width_at_signal', 
                    signal_metadata.get('band_width', 0.04)
                )
                
                # Track squeeze conditions
                self.performance_metrics.add_custom_metric(
                    'squeeze_filter_rate',
                    1.0 if signal_metadata.get('is_squeeze', False) else 0.0
                )
                
                # Track volume confirmation rate
                volume_ratio = signal_metadata.get('volume_ratio', 1.0)
                self.performance_metrics.add_custom_metric(
                    'volume_confirmation_rate',
                    1.0 if volume_ratio > 0.8 else 0.0
                )
                
                # Track adaptive parameter effectiveness
                self.performance_metrics.add_custom_metric(
                    'adaptive_period',
                    signal_metadata.get('adaptive_period', self.bb_period)
                )
                
                self.performance_metrics.add_custom_metric(
                    'adaptive_std_dev',
                    signal_metadata.get('adaptive_std_dev', self.bb_std_dev)
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
                
                # Average band position at entry
                entry_positions = [trade.get('entry_band_position', 0.5) for trade in trades[-20:]]
                avg_entry_position = np.mean(entry_positions) if entry_positions else 0.5
                
                self.performance_metrics.add_custom_metric(
                    'avg_entry_band_position',
                    avg_entry_position
                )
                
                # Band width correlation with performance
                band_widths = [trade.get('entry_band_width', 0.04) for trade in trades[-20:]]
                pnls = [trade.get('pnl', 0) for trade in trades[-20:]]
                
                if len(band_widths) == len(pnls) and len(band_widths) > 5:
                    correlation = np.corrcoef(band_widths, pnls)[0, 1]
                    self.performance_metrics.add_custom_metric(
                        'band_width_pnl_correlation',
                        correlation if not np.isnan(correlation) else 0.0
                    )
            
        except Exception as e:
            self.logger.error(f"Error updating performance metrics: {e}")
    
    def _update_adaptive_parameters(self, data: pd.DataFrame) -> None:
        """
        Update Bollinger Band parameters based on current market regime
        """
        try:
            if self.current_regime == MarketRegime.HIGH_VOLATILITY:
                # In high volatility, use wider bands and shorter periods
                self.adaptive_period = max(10, self.bb_period - 5)
                self.adaptive_std_dev = min(3.0, self.bb_std_dev + 0.5)
                
            elif self.current_regime == MarketRegime.LOW_VOLATILITY:
                # In low volatility, use tighter bands and longer periods
                self.adaptive_period = min(30, self.bb_period + 5)
                self.adaptive_std_dev = max(1.5, self.bb_std_dev - 0.3)
                
            elif self.current_regime == MarketRegime.TRENDING:
                # In trending markets, use longer periods to avoid false signals
                self.adaptive_period = min(30, self.bb_period + 10)
                self.adaptive_std_dev = self.bb_std_dev
                
            elif self.current_regime == MarketRegime.SIDEWAYS:
                # In sideways markets, use standard parameters (optimal for mean reversion)
                self.adaptive_period = self.bb_period
                self.adaptive_std_dev = self.bb_std_dev
                
            else:
                # Default parameters
                self.adaptive_period = self.bb_period
                self.adaptive_std_dev = self.bb_std_dev
                
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
            max_risk_per_trade=0.02,
            risk_reward_ratio=1.5,
            volatility_adjustment=0.04
        )
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Return strategy information and current parameters"""
        return {
            'name': 'Bollinger Bands Mean Reversion Strategy',
            'version': '1.0',
            'description': 'Mean reversion using Bollinger Band extremes with institutional enhancements',
            'parameters': {
                'bb_period': self.bb_period,
                'bb_std_dev': self.bb_std_dev,
                'confirmation_period': self.confirmation_period,
                'volume_confirmation': self.volume_confirmation,
                'squeeze_detection': self.squeeze_detection,
                'adaptive_bands': self.adaptive_bands,
                'max_position_size': self.max_position_size,
                'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
                'profit_target_band_pct': self.profit_target_band_pct
            },
            'current_state': {
                'market_regime': self.current_regime.value,
                'adaptive_period': self.adaptive_period,
                'adaptive_std_dev': self.adaptive_std_dev,
                'is_squeeze': self.is_squeeze
            },
            'asset_classes': ['stocks', 'etfs', 'futures', 'forex'],
            'timeframes': ['5min', '15min', '1h', '4h', '1d'],
            'market_conditions': ['sideways', 'low_volatility', 'mean_reverting']
        }