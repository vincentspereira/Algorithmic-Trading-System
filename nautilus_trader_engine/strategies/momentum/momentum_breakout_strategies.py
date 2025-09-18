"""Momentum Breakout Strategies

This module implements momentum-based breakout trading strategies that identify
and capitalize on strong directional price movements with momentum confirmation.

Features:
- Price momentum breakout strategies
- Volume momentum breakout strategies  
- Volatility momentum breakout strategies
- Multi-timeframe momentum analysis
- Momentum persistence scoring
- Risk-adjusted momentum metrics
- Volume confirmation and filtering
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import base components
from ..core.base_strategy import BaseStrategy, StrategyConfig
from ..signal_generator import SignalGenerator, TradingSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)

class MomentumDirection(Enum):
    """Momentum direction enumeration"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class MomentumStrength(Enum):
    """Momentum strength enumeration"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    VERY_WEAK = "very_weak"

@dataclass
class MomentumMetrics:
    """Momentum analysis metrics"""
    price_momentum: float
    volume_momentum: float
    volatility_momentum: float
    momentum_score: float
    persistence: float
    acceleration: float
    direction: MomentumDirection
    strength: MomentumStrength
    confidence: float
    breakout_level: float
    volume_confirmation: bool
    volume_ratio: float
    momentum_duration: int

@dataclass
class MomentumSignal:
    """Momentum signal data structure"""
    direction: MomentumDirection
    strength: MomentumStrength
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime
    momentum_metrics: MomentumMetrics
    metadata: Dict[str, Any]

class MomentumAnalyzer:
    """Core momentum analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MomentumAnalyzer")
    
    def calculate_price_momentum(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate price momentum (rate of change)"""
        try:
            if len(prices) < period + 1:
                return pd.Series([0.0] * len(prices), index=prices.index)
            
            momentum = prices.pct_change(periods=period) * 100
            return momentum.fillna(0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating price momentum: {e}")
            return pd.Series([0.0] * len(prices), index=prices.index)
    
    def calculate_volume_momentum(self, volume: pd.Series, period: int = 14) -> pd.Series:
        """Calculate volume momentum"""
        try:
            if len(volume) < period + 1:
                return pd.Series([0.0] * len(volume), index=volume.index)
            
            volume_ma = volume.rolling(window=period).mean()
            volume_momentum = (volume / volume_ma - 1) * 100
            return volume_momentum.fillna(0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating volume momentum: {e}")
            return pd.Series([0.0] * len(volume), index=volume.index)
    
    def calculate_volatility_momentum(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate volatility momentum using ATR"""
        try:
            if len(close) < period + 1:
                return pd.Series([0.0] * len(close), index=close.index)
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate ATR
            atr = tr.rolling(window=period).mean()
            
            # Calculate ATR momentum
            atr_momentum = atr.pct_change(periods=period) * 100
            return atr_momentum.fillna(0.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility momentum: {e}")
            return pd.Series([0.0] * len(close), index=close.index)
    
    def calculate_momentum_score(self, price_momentum: float, volume_momentum: float, 
                               volatility_momentum: float, weights: Tuple[float, float, float] = (0.5, 0.3, 0.2)) -> float:
        """Calculate composite momentum score"""
        try:
            # Normalize momentum values
            price_norm = np.tanh(price_momentum / 10.0)  # Normalize to [-1, 1]
            volume_norm = np.tanh(volume_momentum / 50.0)
            volatility_norm = np.tanh(volatility_momentum / 20.0)
            
            # Calculate weighted score
            momentum_score = (weights[0] * price_norm + 
                            weights[1] * volume_norm + 
                            weights[2] * volatility_norm)
            
            return momentum_score
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum score: {e}")
            return 0.0
    
    def calculate_momentum_persistence(self, momentum_series: pd.Series, threshold: float = 0.1) -> float:
        """Calculate momentum persistence (consecutive periods above threshold)"""
        try:
            if len(momentum_series) == 0:
                return 0.0
            
            # Count consecutive periods above threshold
            above_threshold = momentum_series.abs() > threshold
            
            if not above_threshold.iloc[-1]:
                return 0.0
            
            persistence_count = 0
            for i in range(len(above_threshold) - 1, -1, -1):
                if above_threshold.iloc[i]:
                    persistence_count += 1
                else:
                    break
            
            return persistence_count / len(momentum_series)
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum persistence: {e}")
            return 0.0
    
    def calculate_momentum_acceleration(self, momentum_series: pd.Series) -> float:
        """Calculate momentum acceleration (second derivative)"""
        try:
            if len(momentum_series) < 3:
                return 0.0
            
            # Calculate first derivative (velocity)
            velocity = momentum_series.diff()
            
            # Calculate second derivative (acceleration)
            acceleration = velocity.diff()
            
            return acceleration.iloc[-1] if not pd.isna(acceleration.iloc[-1]) else 0.0
            
        except Exception as e:
            self.logger.error(f"Error calculating momentum acceleration: {e}")
            return 0.0
    
    def analyze_comprehensive_momentum(self, df: pd.DataFrame) -> MomentumMetrics:
        """Analyze comprehensive momentum metrics"""
        try:
            if len(df) < 20:
                return MomentumMetrics(
                    price_momentum=0.0,
                    volume_momentum=0.0,
                    volatility_momentum=0.0,
                    momentum_score=0.0,
                    persistence=0.0,
                    acceleration=0.0,
                    direction=MomentumDirection.NEUTRAL,
                    strength=MomentumStrength.VERY_WEAK,
                    confidence=0.0,
                    breakout_level=0.0,
                    volume_confirmation=False,
                    volume_ratio=1.0,
                    momentum_duration=0
                )
            
            # Calculate individual momentum components
            price_momentum_series = self.calculate_price_momentum(df['close'])
            current_price_momentum = price_momentum_series.iloc[-1]
            
            volume_momentum_series = pd.Series([0.0] * len(df))
            current_volume_momentum = 0.0
            if 'volume' in df.columns:
                volume_momentum_series = self.calculate_volume_momentum(df['volume'])
                current_volume_momentum = volume_momentum_series.iloc[-1]
            
            volatility_momentum_series = self.calculate_volatility_momentum(
                df['high'], df['low'], df['close']
            )
            current_volatility_momentum = volatility_momentum_series.iloc[-1]
            
            # Calculate composite momentum score
            momentum_score = self.calculate_momentum_score(
                current_price_momentum, current_volume_momentum, current_volatility_momentum
            )
            
            # Calculate persistence
            persistence = self.calculate_momentum_persistence(price_momentum_series)
            
            # Calculate acceleration
            acceleration = self.calculate_momentum_acceleration(price_momentum_series)
            
            # Determine direction
            if momentum_score > 0.1:
                direction = MomentumDirection.BULLISH
            elif momentum_score < -0.1:
                direction = MomentumDirection.BEARISH
            else:
                direction = MomentumDirection.NEUTRAL
            
            # Determine strength
            abs_score = abs(momentum_score)
            if abs_score > 0.8:
                strength = MomentumStrength.VERY_STRONG
            elif abs_score > 0.6:
                strength = MomentumStrength.STRONG
            elif abs_score > 0.4:
                strength = MomentumStrength.MODERATE
            elif abs_score > 0.2:
                strength = MomentumStrength.WEAK
            else:
                strength = MomentumStrength.VERY_WEAK
            
            # Calculate confidence
            confidence = min(abs_score + persistence * 0.3, 1.0)
            
            # Calculate breakout level (recent high/low)
            lookback = min(20, len(df))
            if direction == MomentumDirection.BULLISH:
                breakout_level = df['high'].iloc[-lookback:].max()
            elif direction == MomentumDirection.BEARISH:
                breakout_level = df['low'].iloc[-lookback:].min()
            else:
                breakout_level = df['close'].iloc[-1]
            
            # Volume confirmation
            volume_confirmation = False
            volume_ratio = 1.0
            if 'volume' in df.columns and len(df) > 10:
                recent_volume = df['volume'].iloc[-5:].mean()
                avg_volume = df['volume'].iloc[-20:].mean()
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
                volume_confirmation = volume_ratio > 1.2
            
            # Calculate momentum duration
            momentum_duration = int(persistence * len(df))
            
            return MomentumMetrics(
                price_momentum=current_price_momentum,
                volume_momentum=current_volume_momentum,
                volatility_momentum=current_volatility_momentum,
                momentum_score=momentum_score,
                persistence=persistence,
                acceleration=acceleration,
                direction=direction,
                strength=strength,
                confidence=confidence,
                breakout_level=breakout_level,
                volume_confirmation=volume_confirmation,
                volume_ratio=volume_ratio,
                momentum_duration=momentum_duration
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing comprehensive momentum: {e}")
            return MomentumMetrics(
                price_momentum=0.0,
                volume_momentum=0.0,
                volatility_momentum=0.0,
                momentum_score=0.0,
                persistence=0.0,
                acceleration=0.0,
                direction=MomentumDirection.NEUTRAL,
                strength=MomentumStrength.VERY_WEAK,
                confidence=0.0,
                breakout_level=0.0,
                volume_confirmation=False,
                volume_ratio=1.0,
                momentum_duration=0
            )

class MomentumBreakoutStrategy(BaseStrategy):
    """Base class for momentum breakout strategies"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.momentum_analyzer = MomentumAnalyzer()
        self.signal_generator = SignalGenerator()
        
        # Strategy parameters
        self.momentum_threshold = config.parameters.get('momentum_threshold', 0.3)
        self.min_persistence = config.parameters.get('min_persistence', 0.2)
        self.volume_confirmation = config.parameters.get('volume_confirmation', True)
        self.min_volume_ratio = config.parameters.get('min_volume_ratio', 1.2)
        self.risk_reward_ratio = config.parameters.get('risk_reward_ratio', 2.0)
    
    def analyze_market_data(self, market_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """Analyze market data for momentum signals"""
        try:
            if len(market_data) < 20:
                return None
            
            df = pd.DataFrame(market_data)
            
            # Ensure required columns
            required_columns = ['close', 'high', 'low']
            if not all(col in df.columns for col in required_columns):
                self.logger.error("Missing required columns in market data")
                return None
            
            # Analyze momentum
            momentum_metrics = self.momentum_analyzer.analyze_comprehensive_momentum(df)
            
            return {
                'momentum_metrics': momentum_metrics,
                'current_price': df['close'].iloc[-1],
                'recent_high': df['high'].iloc[-10:].max(),
                'recent_low': df['low'].iloc[-10:].min()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market data: {e}")
            return None

class PriceMomentumBreakoutStrategy(MomentumBreakoutStrategy):
    """Price momentum breakout strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Price momentum parameters
        self.momentum_period = config.parameters.get('momentum_period', 14)
        self.breakout_threshold = config.parameters.get('breakout_threshold', 2.0)
        self.confirmation_periods = config.parameters.get('confirmation_periods', 2)
    
    def generate_signals(self, market_data: List[Dict]) -> List[TradingSignal]:
        """Generate price momentum breakout signals"""
        try:
            if len(market_data) < self.momentum_period + self.confirmation_periods:
                return []
            
            df = pd.DataFrame(market_data)
            
            # Analyze momentum
            analysis = self.analyze_market_data(market_data)
            if not analysis:
                return []
            
            momentum_metrics = analysis['momentum_metrics']
            current_price = analysis['current_price']
            
            signals = []
            
            # Check for strong bullish momentum breakout
            if (momentum_metrics.direction == MomentumDirection.BULLISH and
                momentum_metrics.strength in [MomentumStrength.STRONG, MomentumStrength.VERY_STRONG] and
                momentum_metrics.persistence >= self.min_persistence and
                momentum_metrics.price_momentum > self.breakout_threshold):
                
                # Volume confirmation check
                if not self.volume_confirmation or momentum_metrics.volume_confirmation:
                    
                    # Calculate stop loss and take profit
                    atr = self._calculate_atr(df['high'], df['low'], df['close'])
                    stop_loss = current_price - (2 * atr)
                    take_profit = current_price + (self.risk_reward_ratio * 2 * atr)
                    
                    signal = TradingSignal(
                        symbol=self.config.symbols[0],
                        signal_type=SignalType.BUY,
                        strength=self._determine_signal_strength(momentum_metrics),
                        confidence=momentum_metrics.confidence,
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'price_momentum_breakout',
                            'price_momentum': momentum_metrics.price_momentum,
                            'momentum_score': momentum_metrics.momentum_score,
                            'persistence': momentum_metrics.persistence,
                            'volume_ratio': momentum_metrics.volume_ratio,
                            'breakout_level': momentum_metrics.breakout_level,
                            'momentum_duration': momentum_metrics.momentum_duration
                        }
                    )
                    signals.append(signal)
            
            # Check for strong bearish momentum breakout
            elif (momentum_metrics.direction == MomentumDirection.BEARISH and
                  momentum_metrics.strength in [MomentumStrength.STRONG, MomentumStrength.VERY_STRONG] and
                  momentum_metrics.persistence >= self.min_persistence and
                  momentum_metrics.price_momentum < -self.breakout_threshold):
                
                # Volume confirmation check
                if not self.volume_confirmation or momentum_metrics.volume_confirmation:
                    
                    atr = self._calculate_atr(df['high'], df['low'], df['close'])
                    stop_loss = current_price + (2 * atr)
                    take_profit = current_price - (self.risk_reward_ratio * 2 * atr)
                    
                    signal = TradingSignal(
                        symbol=self.config.symbols[0],
                        signal_type=SignalType.SELL,
                        strength=self._determine_signal_strength(momentum_metrics),
                        confidence=momentum_metrics.confidence,
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'price_momentum_breakout',
                            'price_momentum': momentum_metrics.price_momentum,
                            'momentum_score': momentum_metrics.momentum_score,
                            'persistence': momentum_metrics.persistence,
                            'volume_ratio': momentum_metrics.volume_ratio,
                            'breakout_level': momentum_metrics.breakout_level,
                            'momentum_duration': momentum_metrics.momentum_duration
                        }
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating price momentum signals: {e}")
            return []
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            if len(close) < period + 1:
                return (high - low).mean()
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            return tr.rolling(window=period).mean().iloc[-1]
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.01
    
    def _determine_signal_strength(self, momentum_metrics: MomentumMetrics) -> SignalStrength:
        """Determine signal strength based on momentum metrics"""
        if momentum_metrics.strength == MomentumStrength.VERY_STRONG:
            return SignalStrength.STRONG
        elif momentum_metrics.strength == MomentumStrength.STRONG:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

class VolumeMomentumBreakoutStrategy(MomentumBreakoutStrategy):
    """Volume momentum breakout strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Volume momentum parameters
        self.volume_momentum_threshold = config.parameters.get('volume_momentum_threshold', 50.0)
        self.min_volume_spike = config.parameters.get('min_volume_spike', 2.0)
        self.price_confirmation = config.parameters.get('price_confirmation', True)
    
    def generate_signals(self, market_data: List[Dict]) -> List[TradingSignal]:
        """Generate volume momentum breakout signals"""
        try:
            if len(market_data) < 20:
                return []
            
            df = pd.DataFrame(market_data)
            
            # Check if volume data is available
            if 'volume' not in df.columns:
                self.logger.warning("Volume data not available for volume momentum strategy")
                return []
            
            # Analyze momentum
            analysis = self.analyze_market_data(market_data)
            if not analysis:
                return []
            
            momentum_metrics = analysis['momentum_metrics']
            current_price = analysis['current_price']
            
            signals = []
            
            # Check for volume momentum breakout
            if (momentum_metrics.volume_momentum > self.volume_momentum_threshold and
                momentum_metrics.volume_ratio >= self.min_volume_spike):
                
                # Price confirmation check
                price_direction_confirmed = True
                if self.price_confirmation:
                    price_direction_confirmed = (
                        (momentum_metrics.direction == MomentumDirection.BULLISH and momentum_metrics.price_momentum > 0) or
                        (momentum_metrics.direction == MomentumDirection.BEARISH and momentum_metrics.price_momentum < 0)
                    )
                
                if price_direction_confirmed:
                    # Determine signal direction based on price momentum
                    if momentum_metrics.price_momentum > 0:
                        signal_type = SignalType.BUY
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price - (2 * atr)
                        take_profit = current_price + (self.risk_reward_ratio * 2 * atr)
                    else:
                        signal_type = SignalType.SELL
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price + (2 * atr)
                        take_profit = current_price - (self.risk_reward_ratio * 2 * atr)
                    
                    signal = TradingSignal(
                        symbol=self.config.symbols[0],
                        signal_type=signal_type,
                        strength=self._determine_signal_strength(momentum_metrics),
                        confidence=min(momentum_metrics.volume_ratio / 3.0, 1.0),
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'volume_momentum_breakout',
                            'volume_momentum': momentum_metrics.volume_momentum,
                            'volume_ratio': momentum_metrics.volume_ratio,
                            'price_momentum': momentum_metrics.price_momentum,
                            'momentum_score': momentum_metrics.momentum_score,
                            'volume_spike': momentum_metrics.volume_ratio >= self.min_volume_spike
                        }
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating volume momentum signals: {e}")
            return []
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            if len(close) < period + 1:
                return (high - low).mean()
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            return tr.rolling(window=period).mean().iloc[-1]
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.01
    
    def _determine_signal_strength(self, momentum_metrics: MomentumMetrics) -> SignalStrength:
        """Determine signal strength based on volume momentum"""
        volume_strength = momentum_metrics.volume_ratio
        
        if volume_strength > 3.0:
            return SignalStrength.STRONG
        elif volume_strength > 2.0:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

class VolatilityMomentumBreakoutStrategy(MomentumBreakoutStrategy):
    """Volatility momentum breakout strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Volatility momentum parameters
        self.volatility_threshold = config.parameters.get('volatility_threshold', 10.0)
        self.volatility_expansion_ratio = config.parameters.get('volatility_expansion_ratio', 1.5)
        self.trend_confirmation = config.parameters.get('trend_confirmation', True)
    
    def generate_signals(self, market_data: List[Dict]) -> List[TradingSignal]:
        """Generate volatility momentum breakout signals"""
        try:
            if len(market_data) < 30:
                return []
            
            df = pd.DataFrame(market_data)
            
            # Analyze momentum
            analysis = self.analyze_market_data(market_data)
            if not analysis:
                return []
            
            momentum_metrics = analysis['momentum_metrics']
            current_price = analysis['current_price']
            
            signals = []
            
            # Check for volatility expansion
            if momentum_metrics.volatility_momentum > self.volatility_threshold:
                
                # Trend confirmation check
                trend_confirmed = True
                if self.trend_confirmation:
                    trend_confirmed = momentum_metrics.direction != MomentumDirection.NEUTRAL
                
                if trend_confirmed:
                    # Determine signal direction
                    if momentum_metrics.direction == MomentumDirection.BULLISH:
                        signal_type = SignalType.BUY
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price - (2.5 * atr)  # Wider stop for volatility
                        take_profit = current_price + (self.risk_reward_ratio * 2.5 * atr)
                    elif momentum_metrics.direction == MomentumDirection.BEARISH:
                        signal_type = SignalType.SELL
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price + (2.5 * atr)
                        take_profit = current_price - (self.risk_reward_ratio * 2.5 * atr)
                    else:
                        return signals  # No clear direction
                    
                    signal = TradingSignal(
                        symbol=self.config.symbols[0],
                        signal_type=signal_type,
                        strength=self._determine_signal_strength(momentum_metrics),
                        confidence=min(momentum_metrics.volatility_momentum / 50.0, 1.0),
                        entry_price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=datetime.now(),
                        metadata={
                            'strategy': 'volatility_momentum_breakout',
                            'volatility_momentum': momentum_metrics.volatility_momentum,
                            'momentum_score': momentum_metrics.momentum_score,
                            'direction': momentum_metrics.direction.value,
                            'acceleration': momentum_metrics.acceleration,
                            'volatility_expansion': True
                        }
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating volatility momentum signals: {e}")
            return []
    
    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            if len(close) < period + 1:
                return (high - low).mean()
            
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            return tr.rolling(window=period).mean().iloc[-1]
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return 0.01
    
    def _determine_signal_strength(self, momentum_metrics: MomentumMetrics) -> SignalStrength:
        """Determine signal strength based on volatility momentum"""
        volatility_strength = momentum_metrics.volatility_momentum
        
        if volatility_strength > 30.0:
            return SignalStrength.STRONG
        elif volatility_strength > 20.0:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

# Utility functions
def calculate_momentum_score(price_momentum: float, volume_momentum: float, volatility_momentum: float) -> float:
    """Calculate composite momentum score"""
    analyzer = MomentumAnalyzer()
    return analyzer.calculate_momentum_score(price_momentum, volume_momentum, volatility_momentum)

def detect_momentum_breakout(df: pd.DataFrame, threshold: float = 0.3) -> bool:
    """Detect momentum breakout"""
    analyzer = MomentumAnalyzer()
    metrics = analyzer.analyze_comprehensive_momentum(df)
    return abs(metrics.momentum_score) > threshold

def calculate_momentum_persistence(momentum_series: pd.Series, threshold: float = 0.1) -> float:
    """Calculate momentum persistence"""
    analyzer = MomentumAnalyzer()
    return analyzer.calculate_momentum_persistence(momentum_series, threshold)