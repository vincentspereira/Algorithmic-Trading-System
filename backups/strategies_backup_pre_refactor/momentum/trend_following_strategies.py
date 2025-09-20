"""Trend Following Strategies

This module implements comprehensive trend-following trading strategies that identify
and capitalize on sustained directional price movements.

Features:
- Multiple moving average crossover strategies
- MACD-based trend identification
- ADX trend strength analysis
- Multi-timeframe trend confirmation
- Adaptive trend detection
- Volume-weighted trend analysis
- Trend persistence scoring
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

# Import base components
from ...core.base_strategy import BaseStrategy, StrategyConfig
from ..architecture.pillars.signal_generation import SignalGenerator, MultiTimeframeSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)

class TrendDirection(Enum):
    """Trend direction enumeration"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    UNKNOWN = "unknown"

class TrendStrength(Enum):
    """Trend strength enumeration"""
    VERY_STRONG = "very_strong"
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    VERY_WEAK = "very_weak"

@dataclass
class TrendSignal:
    """Trend signal data structure"""
    direction: TrendDirection
    strength: TrendStrength
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    timestamp: datetime
    indicators: Dict[str, float]
    metadata: Dict[str, Any]

@dataclass
class TrendMetrics:
    """Trend analysis metrics"""
    direction: TrendDirection
    strength: TrendStrength
    strength_score: float
    persistence: float
    volatility_adjusted_strength: float
    trend_duration: int
    slope: float
    r_squared: float
    support_resistance_levels: List[float]
    volume_confirmation: bool
    volume_trend: TrendDirection

class TrendAnalyzer:
    """Core trend analysis engine"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TrendAnalyzer")
    
    def calculate_moving_averages(self, prices: pd.Series, periods: List[int]) -> Dict[int, pd.Series]:
        """Calculate multiple moving averages"""
        try:
            mas = {}
            for period in periods:
                if len(prices) >= period:
                    mas[period] = prices.rolling(window=period).mean()
                else:
                    mas[period] = pd.Series([np.nan] * len(prices), index=prices.index)
            return mas
        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {e}")
            return {}
    
    def calculate_ema(self, prices: pd.Series, period: int, alpha: Optional[float] = None) -> pd.Series:
        """Calculate exponential moving average"""
        try:
            if alpha is None:
                alpha = 2.0 / (period + 1)
            
            if len(prices) == 0:
                return pd.Series(dtype=float)
            
            ema = prices.ewm(alpha=alpha, adjust=False).mean()
            return ema
        except Exception as e:
            self.logger.error(f"Error calculating EMA: {e}")
            return pd.Series(dtype=float)
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD indicator"""
        try:
            if len(prices) < slow:
                return {
                    'macd': pd.Series(dtype=float),
                    'signal': pd.Series(dtype=float),
                    'histogram': pd.Series(dtype=float)
                }
            
            ema_fast = self.calculate_ema(prices, fast)
            ema_slow = self.calculate_ema(prices, slow)
            
            macd_line = ema_fast - ema_slow
            signal_line = self.calculate_ema(macd_line, signal)
            histogram = macd_line - signal_line
            
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            }
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            return {'macd': pd.Series(dtype=float), 'signal': pd.Series(dtype=float), 'histogram': pd.Series(dtype=float)}
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
        """Calculate ADX (Average Directional Index)"""
        try:
            if len(close) < period + 1:
                return {
                    'adx': pd.Series(dtype=float),
                    'di_plus': pd.Series(dtype=float),
                    'di_minus': pd.Series(dtype=float)
                }
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate Directional Movement
            dm_plus = np.where((high - high.shift(1)) > (low.shift(1) - low), 
                              np.maximum(high - high.shift(1), 0), 0)
            dm_minus = np.where((low.shift(1) - low) > (high - high.shift(1)), 
                               np.maximum(low.shift(1) - low, 0), 0)
            
            dm_plus = pd.Series(dm_plus, index=high.index)
            dm_minus = pd.Series(dm_minus, index=high.index)
            
            # Calculate smoothed values
            tr_smooth = tr.rolling(window=period).mean()
            dm_plus_smooth = dm_plus.rolling(window=period).mean()
            dm_minus_smooth = dm_minus.rolling(window=period).mean()
            
            # Calculate Directional Indicators
            di_plus = 100 * (dm_plus_smooth / tr_smooth)
            di_minus = 100 * (dm_minus_smooth / tr_smooth)
            
            # Calculate ADX
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            adx = dx.rolling(window=period).mean()
            
            return {
                'adx': adx,
                'di_plus': di_plus,
                'di_minus': di_minus
            }
        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return {'adx': pd.Series(dtype=float), 'di_plus': pd.Series(dtype=float), 'di_minus': pd.Series(dtype=float)}
    
    def analyze_trend_strength(self, prices: pd.Series, volume: Optional[pd.Series] = None) -> TrendMetrics:
        """Analyze comprehensive trend strength"""
        try:
            if len(prices) < 20:
                return TrendMetrics(
                    direction=TrendDirection.UNKNOWN,
                    strength=TrendStrength.VERY_WEAK,
                    strength_score=0.0,
                    persistence=0.0,
                    volatility_adjusted_strength=0.0,
                    trend_duration=0,
                    slope=0.0,
                    r_squared=0.0,
                    support_resistance_levels=[],
                    volume_confirmation=False,
                    volume_trend=TrendDirection.UNKNOWN
                )
            
            # Calculate trend slope using linear regression
            x = np.arange(len(prices))
            coeffs = np.polyfit(x, prices, 1)
            slope = coeffs[0]
            
            # Calculate R-squared
            y_pred = np.polyval(coeffs, x)
            ss_res = np.sum((prices - y_pred) ** 2)
            ss_tot = np.sum((prices - np.mean(prices)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
            
            # Determine trend direction
            if slope > 0 and r_squared > 0.5:
                direction = TrendDirection.BULLISH
            elif slope < 0 and r_squared > 0.5:
                direction = TrendDirection.BEARISH
            else:
                direction = TrendDirection.SIDEWAYS
            
            # Calculate strength score
            strength_score = abs(slope) * r_squared
            
            # Determine strength category
            if strength_score > 2.0:
                strength = TrendStrength.VERY_STRONG
            elif strength_score > 1.0:
                strength = TrendStrength.STRONG
            elif strength_score > 0.5:
                strength = TrendStrength.MODERATE
            elif strength_score > 0.1:
                strength = TrendStrength.WEAK
            else:
                strength = TrendStrength.VERY_WEAK
            
            # Calculate persistence (consecutive periods in same direction)
            returns = prices.pct_change().dropna()
            if len(returns) > 0:
                current_direction = 1 if returns.iloc[-1] > 0 else -1
                persistence_count = 0
                for i in range(len(returns) - 1, -1, -1):
                    if (returns.iloc[i] > 0 and current_direction > 0) or (returns.iloc[i] < 0 and current_direction < 0):
                        persistence_count += 1
                    else:
                        break
                persistence = persistence_count / len(returns)
            else:
                persistence = 0.0
            
            # Calculate volatility-adjusted strength
            volatility = returns.std() if len(returns) > 1 else 1.0
            volatility_adjusted_strength = strength_score / max(volatility, 0.01)
            
            # Calculate support/resistance levels
            support_resistance_levels = self._calculate_support_resistance(prices)
            
            # Volume analysis
            volume_confirmation = False
            volume_trend = TrendDirection.UNKNOWN
            if volume is not None and len(volume) > 10:
                volume_ma = volume.rolling(window=10).mean()
                recent_volume = volume.iloc[-5:].mean()
                volume_confirmation = recent_volume > volume_ma.iloc[-1]
                
                # Volume trend
                volume_slope = np.polyfit(np.arange(len(volume)), volume, 1)[0]
                volume_trend = TrendDirection.BULLISH if volume_slope > 0 else TrendDirection.BEARISH
            
            return TrendMetrics(
                direction=direction,
                strength=strength,
                strength_score=strength_score,
                persistence=persistence,
                volatility_adjusted_strength=volatility_adjusted_strength,
                trend_duration=persistence_count if 'persistence_count' in locals() else 0,
                slope=slope,
                r_squared=r_squared,
                support_resistance_levels=support_resistance_levels,
                volume_confirmation=volume_confirmation,
                volume_trend=volume_trend
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend strength: {e}")
            return TrendMetrics(
                direction=TrendDirection.UNKNOWN,
                strength=TrendStrength.VERY_WEAK,
                strength_score=0.0,
                persistence=0.0,
                volatility_adjusted_strength=0.0,
                trend_duration=0,
                slope=0.0,
                r_squared=0.0,
                support_resistance_levels=[],
                volume_confirmation=False,
                volume_trend=TrendDirection.UNKNOWN
            )
    
    def _calculate_support_resistance(self, prices: pd.Series, window: int = 20) -> List[float]:
        """Calculate support and resistance levels"""
        try:
            if len(prices) < window:
                return []
            
            levels = []
            
            # Find local minima and maxima
            for i in range(window, len(prices) - window):
                # Local minimum (support)
                if prices.iloc[i] == prices.iloc[i-window:i+window+1].min():
                    levels.append(prices.iloc[i])
                
                # Local maximum (resistance)
                if prices.iloc[i] == prices.iloc[i-window:i+window+1].max():
                    levels.append(prices.iloc[i])
            
            # Remove duplicates and sort
            levels = sorted(list(set(levels)))
            
            return levels
            
        except Exception as e:
            self.logger.error(f"Error calculating support/resistance: {e}")
            return []

class TrendFollowingStrategy(BaseStrategy):
    """Base class for trend following strategies"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.trend_analyzer = TrendAnalyzer()
        self.signal_generator = SignalGenerator()
        
        # Strategy parameters
        self.min_trend_strength = config.parameters.get('min_trend_strength', 0.5)
        self.min_persistence = config.parameters.get('min_persistence', 0.3)
        self.volume_confirmation = config.parameters.get('volume_confirmation', True)
        self.risk_reward_ratio = config.parameters.get('risk_reward_ratio', 2.0)
    
    def analyze_market_data(self, market_data: List[Dict]) -> Optional[Dict[str, Any]]:
        """Analyze market data for trend signals"""
        try:
            if len(market_data) < 20:
                return None
            
            df = pd.DataFrame(market_data)
            
            # Ensure required columns
            required_columns = ['close', 'high', 'low']
            if not all(col in df.columns for col in required_columns):
                self.logger.error("Missing required columns in market data")
                return None
            
            # Analyze trend
            volume = df['volume'] if 'volume' in df.columns else None
            trend_metrics = self.trend_analyzer.analyze_trend_strength(df['close'], volume)
            
            return {
                'trend_metrics': trend_metrics,
                'current_price': df['close'].iloc[-1],
                'volume_data': volume.iloc[-10:].tolist() if volume is not None else []
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing market data: {e}")
            return None

class MovingAverageTrendStrategy(TrendFollowingStrategy):
    """Moving average crossover trend following strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # MA parameters
        self.short_period = config.parameters.get('short_ma_period', 10)
        self.long_period = config.parameters.get('long_ma_period', 20)
        self.ma_type = config.parameters.get('ma_type', 'sma')  # sma, ema
        self.confirmation_periods = config.parameters.get('confirmation_periods', 2)
    
    def generate_signals(self, market_data: List[Dict]) -> List[MultiTimeframeSignal]:
        """Generate moving average crossover signals"""
        try:
            if len(market_data) < max(self.short_period, self.long_period) + self.confirmation_periods:
                return []
            
            df = pd.DataFrame(market_data)
            prices = df['close']
            
            # Calculate moving averages
            if self.ma_type == 'ema':
                short_ma = self.trend_analyzer.calculate_ema(prices, self.short_period)
                long_ma = self.trend_analyzer.calculate_ema(prices, self.long_period)
            else:
                mas = self.trend_analyzer.calculate_moving_averages(prices, [self.short_period, self.long_period])
                short_ma = mas[self.short_period]
                long_ma = mas[self.long_period]
            
            signals = []
            
            # Check for crossover
            if len(short_ma) >= 2 and len(long_ma) >= 2:
                current_short = short_ma.iloc[-1]
                current_long = long_ma.iloc[-1]
                prev_short = short_ma.iloc[-2]
                prev_long = long_ma.iloc[-2]
                
                current_price = prices.iloc[-1]
                
                # Bullish crossover
                if prev_short <= prev_long and current_short > current_long:
                    # Confirm trend strength
                    analysis = self.analyze_market_data(market_data)
                    if analysis and analysis['trend_metrics'].strength_score >= self.min_trend_strength:
                        
                        # Calculate stop loss and take profit
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price - (2 * atr)
                        take_profit = current_price + (self.risk_reward_ratio * 2 * atr)
                        
                        signal = MultiTimeframeSignal(
                            symbol=self.config.symbols[0],
                            signal_type=SignalType.BUY,
                            strength=self._determine_signal_strength(analysis['trend_metrics']),
                            confidence=min(analysis['trend_metrics'].strength_score, 1.0),
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'ma_crossover',
                                'short_ma': current_short,
                                'long_ma': current_long,
                                'trend_strength': analysis['trend_metrics'].strength_score,
                                'ma_type': self.ma_type,
                                'short_period': self.short_period,
                                'long_period': self.long_period
                            }
                        )
                        signals.append(signal)
                
                # Bearish crossover
                elif prev_short >= prev_long and current_short < current_long:
                    analysis = self.analyze_market_data(market_data)
                    if analysis and analysis['trend_metrics'].strength_score >= self.min_trend_strength:
                        
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price + (2 * atr)
                        take_profit = current_price - (self.risk_reward_ratio * 2 * atr)
                        
                        signal = MultiTimeframeSignal(
                            symbol=self.config.symbols[0],
                            signal_type=SignalType.SELL,
                            strength=self._determine_signal_strength(analysis['trend_metrics']),
                            confidence=min(analysis['trend_metrics'].strength_score, 1.0),
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'ma_crossover',
                                'short_ma': current_short,
                                'long_ma': current_long,
                                'trend_strength': analysis['trend_metrics'].strength_score,
                                'ma_type': self.ma_type,
                                'short_period': self.short_period,
                                'long_period': self.long_period
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating MA signals: {e}")
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
    
    def _determine_signal_strength(self, trend_metrics: TrendMetrics) -> SignalStrength:
        """Determine signal strength based on trend metrics"""
        if trend_metrics.strength == TrendStrength.VERY_STRONG:
            return SignalStrength.STRONG
        elif trend_metrics.strength == TrendStrength.STRONG:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

class MACDTrendStrategy(TrendFollowingStrategy):
    """MACD-based trend following strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # MACD parameters
        self.fast_period = config.parameters.get('macd_fast', 12)
        self.slow_period = config.parameters.get('macd_slow', 26)
        self.signal_period = config.parameters.get('macd_signal', 9)
        self.histogram_threshold = config.parameters.get('histogram_threshold', 0.0)
    
    def generate_signals(self, market_data: List[Dict]) -> List[MultiTimeframeSignal]:
        """Generate MACD-based trend signals"""
        try:
            if len(market_data) < self.slow_period + self.signal_period:
                return []
            
            df = pd.DataFrame(market_data)
            prices = df['close']
            
            # Calculate MACD
            macd_data = self.trend_analyzer.calculate_macd(
                prices, self.fast_period, self.slow_period, self.signal_period
            )
            
            signals = []
            
            if len(macd_data['macd']) >= 2:
                current_macd = macd_data['macd'].iloc[-1]
                current_signal = macd_data['signal'].iloc[-1]
                current_histogram = macd_data['histogram'].iloc[-1]
                
                prev_macd = macd_data['macd'].iloc[-2]
                prev_signal = macd_data['signal'].iloc[-2]
                prev_histogram = macd_data['histogram'].iloc[-2]
                
                current_price = prices.iloc[-1]
                
                # Bullish MACD crossover
                if (prev_macd <= prev_signal and current_macd > current_signal and 
                    current_histogram > self.histogram_threshold):
                    
                    analysis = self.analyze_market_data(market_data)
                    if analysis and analysis['trend_metrics'].direction == TrendDirection.BULLISH:
                        
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price - (2 * atr)
                        take_profit = current_price + (self.risk_reward_ratio * 2 * atr)
                        
                        signal = MultiTimeframeSignal(
                            symbol=self.config.symbols[0],
                            signal_type=SignalType.BUY,
                            strength=self._determine_signal_strength(analysis['trend_metrics']),
                            confidence=min(abs(current_histogram) * 10, 1.0),
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'macd_trend',
                                'macd': current_macd,
                                'signal_line': current_signal,
                                'histogram': current_histogram,
                                'trend_direction': analysis['trend_metrics'].direction.value
                            }
                        )
                        signals.append(signal)
                
                # Bearish MACD crossover
                elif (prev_macd >= prev_signal and current_macd < current_signal and 
                      current_histogram < -self.histogram_threshold):
                    
                    analysis = self.analyze_market_data(market_data)
                    if analysis and analysis['trend_metrics'].direction == TrendDirection.BEARISH:
                        
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price + (2 * atr)
                        take_profit = current_price - (self.risk_reward_ratio * 2 * atr)
                        
                        signal = MultiTimeframeSignal(
                            symbol=self.config.symbols[0],
                            signal_type=SignalType.SELL,
                            strength=self._determine_signal_strength(analysis['trend_metrics']),
                            confidence=min(abs(current_histogram) * 10, 1.0),
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'macd_trend',
                                'macd': current_macd,
                                'signal_line': current_signal,
                                'histogram': current_histogram,
                                'trend_direction': analysis['trend_metrics'].direction.value
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating MACD signals: {e}")
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
    
    def _determine_signal_strength(self, trend_metrics: TrendMetrics) -> SignalStrength:
        """Determine signal strength based on trend metrics"""
        if trend_metrics.strength == TrendStrength.VERY_STRONG:
            return SignalStrength.STRONG
        elif trend_metrics.strength == TrendStrength.STRONG:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

class ADXTrendStrategy(TrendFollowingStrategy):
    """ADX-based trend strength strategy"""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # ADX parameters
        self.adx_period = config.parameters.get('adx_period', 14)
        self.adx_threshold = config.parameters.get('adx_threshold', 25)
        self.di_threshold = config.parameters.get('di_threshold', 5)
    
    def generate_signals(self, market_data: List[Dict]) -> List[MultiTimeframeSignal]:
        """Generate ADX-based trend signals"""
        try:
            if len(market_data) < self.adx_period * 2:
                return []
            
            df = pd.DataFrame(market_data)
            
            # Calculate ADX
            adx_data = self.trend_analyzer.calculate_adx(
                df['high'], df['low'], df['close'], self.adx_period
            )
            
            signals = []
            
            if len(adx_data['adx']) >= 2:
                current_adx = adx_data['adx'].iloc[-1]
                current_di_plus = adx_data['di_plus'].iloc[-1]
                current_di_minus = adx_data['di_minus'].iloc[-1]
                
                current_price = df['close'].iloc[-1]
                
                # Strong trend with bullish direction
                if (current_adx > self.adx_threshold and 
                    current_di_plus > current_di_minus + self.di_threshold):
                    
                    analysis = self.analyze_market_data(market_data)
                    if analysis:
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price - (2 * atr)
                        take_profit = current_price + (self.risk_reward_ratio * 2 * atr)
                        
                        signal = MultiTimeframeSignal(
                            symbol=self.config.symbols[0],
                            signal_type=SignalType.BUY,
                            strength=self._determine_signal_strength_adx(current_adx),
                            confidence=min(current_adx / 50.0, 1.0),
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'adx_trend',
                                'adx': current_adx,
                                'di_plus': current_di_plus,
                                'di_minus': current_di_minus,
                                'trend_strength': 'strong' if current_adx > 40 else 'moderate'
                            }
                        )
                        signals.append(signal)
                
                # Strong trend with bearish direction
                elif (current_adx > self.adx_threshold and 
                      current_di_minus > current_di_plus + self.di_threshold):
                    
                    analysis = self.analyze_market_data(market_data)
                    if analysis:
                        atr = self._calculate_atr(df['high'], df['low'], df['close'])
                        stop_loss = current_price + (2 * atr)
                        take_profit = current_price - (self.risk_reward_ratio * 2 * atr)
                        
                        signal = MultiTimeframeSignal(
                            symbol=self.config.symbols[0],
                            signal_type=SignalType.SELL,
                            strength=self._determine_signal_strength_adx(current_adx),
                            confidence=min(current_adx / 50.0, 1.0),
                            entry_price=current_price,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            timestamp=datetime.now(),
                            metadata={
                                'strategy': 'adx_trend',
                                'adx': current_adx,
                                'di_plus': current_di_plus,
                                'di_minus': current_di_minus,
                                'trend_strength': 'strong' if current_adx > 40 else 'moderate'
                            }
                        )
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Error generating ADX signals: {e}")
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
    
    def _determine_signal_strength_adx(self, adx_value: float) -> SignalStrength:
        """Determine signal strength based on ADX value"""
        if adx_value > 50:
            return SignalStrength.STRONG
        elif adx_value > 35:
            return SignalStrength.MEDIUM
        else:
            return SignalStrength.WEAK

# Utility functions
def calculate_trend_strength(prices: pd.Series, volume: Optional[pd.Series] = None) -> float:
    """Calculate trend strength score"""
    analyzer = TrendAnalyzer()
    metrics = analyzer.analyze_trend_strength(prices, volume)
    return metrics.strength_score

def detect_trend_change(prices: pd.Series, window: int = 10) -> bool:
    """Detect trend change"""
    if len(prices) < window * 2:
        return False
    
    recent_trend = np.polyfit(range(window), prices.iloc[-window:], 1)[0]
    previous_trend = np.polyfit(range(window), prices.iloc[-window*2:-window], 1)[0]
    
    return (recent_trend > 0) != (previous_trend > 0)

def calculate_ma_crossover(short_ma: pd.Series, long_ma: pd.Series) -> Optional[str]:
    """Calculate moving average crossover"""
    if len(short_ma) < 2 or len(long_ma) < 2:
        return None
    
    current_short = short_ma.iloc[-1]
    current_long = long_ma.iloc[-1]
    prev_short = short_ma.iloc[-2]
    prev_long = long_ma.iloc[-2]
    
    if prev_short <= prev_long and current_short > current_long:
        return "bullish_crossover"
    elif prev_short >= prev_long and current_short < current_long:
        return "bearish_crossover"
    
    return None