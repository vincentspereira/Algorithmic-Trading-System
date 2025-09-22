#!/usr/bin/env python3
"""
Spread Technical Indicators for Pairs Trading

Specialized technical indicators designed for spread and ratio analysis in pairs trading.
These indicators are optimized for mean-reverting spread behavior and provide enhanced
signal generation for pairs trading strategies.

Key Features:
- Spread-specific moving averages and oscillators
- Bollinger Bands for spread analysis
- Z-score calculations with dynamic parameters
- Spread momentum and velocity indicators
- Volume-weighted spread indicators
- Adaptive threshold calculations
- Regime-aware indicator adjustments
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime
import logging
from scipy import stats
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.cluster import KMeans

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SpreadIndicatorType(Enum):
    """Types of spread indicators."""
    ZSCORE = "zscore"
    BOLLINGER = "bollinger"
    MOMENTUM = "momentum"
    VELOCITY = "velocity"
    ACCELERATION = "acceleration"
    VOLATILITY = "volatility"
    REGIME = "regime"
    THRESHOLD = "threshold"


class RegimeType(Enum):
    """Market regime types for spread analysis."""
    MEAN_REVERTING = "mean_reverting"
    TRENDING = "trending"
    VOLATILE = "volatile"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class SpreadSignal:
    """Spread trading signal."""
    signal_type: str
    strength: float  # -1 to 1
    confidence: float  # 0 to 1
    entry_threshold: float
    exit_threshold: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    regime: RegimeType = RegimeType.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BollingerBandsResult:
    """Bollinger Bands calculation result."""
    upper_band: pd.Series
    middle_band: pd.Series
    lower_band: pd.Series
    bandwidth: pd.Series
    percent_b: pd.Series
    squeeze: pd.Series


@dataclass
class ZScoreResult:
    """Z-Score calculation result."""
    zscore: pd.Series
    rolling_mean: pd.Series
    rolling_std: pd.Series
    normalized_zscore: pd.Series
    extreme_levels: Dict[str, float]


class SpreadZScore:
    """Advanced Z-Score calculations for spread analysis."""
    
    def __init__(self, 
                 lookback_period: int = 60,
                 min_periods: int = 20,
                 adaptive: bool = True):
        self.lookback_period = lookback_period
        self.min_periods = min_periods
        self.adaptive = adaptive
    
    def calculate(self, spread: pd.Series, volume: Optional[pd.Series] = None) -> ZScoreResult:
        """Calculate Z-Score for spread with optional volume weighting.
        
        Args:
            spread: Spread time series
            volume: Optional volume series for weighting
            
        Returns:
            ZScoreResult object
        """
        try:
            if len(spread) < self.min_periods:
                return self._empty_zscore_result(spread.index)
            
            # Calculate rolling statistics
            if volume is not None and len(volume) == len(spread):
                # Volume-weighted statistics
                rolling_mean = self._volume_weighted_mean(spread, volume, self.lookback_period)
                rolling_std = self._volume_weighted_std(spread, volume, self.lookback_period)
            else:
                # Simple rolling statistics
                rolling_mean = spread.rolling(window=self.lookback_period, min_periods=self.min_periods).mean()
                rolling_std = spread.rolling(window=self.lookback_period, min_periods=self.min_periods).std()
            
            # Calculate Z-Score
            zscore = (spread - rolling_mean) / rolling_std
            zscore = zscore.fillna(0.0)
            
            # Adaptive lookback adjustment
            if self.adaptive:
                zscore = self._adaptive_zscore_adjustment(zscore, spread)
            
            # Normalized Z-Score (0 to 1 scale)
            normalized_zscore = self._normalize_zscore(zscore)
            
            # Calculate extreme levels
            extreme_levels = self._calculate_extreme_levels(zscore)
            
            return ZScoreResult(
                zscore=zscore,
                rolling_mean=rolling_mean,
                rolling_std=rolling_std,
                normalized_zscore=normalized_zscore,
                extreme_levels=extreme_levels
            )
        
        except Exception as e:
            logger.warning(f"Error calculating Z-Score: {e}")
            return self._empty_zscore_result(spread.index)
    
    def _volume_weighted_mean(self, spread: pd.Series, volume: pd.Series, window: int) -> pd.Series:
        """Calculate volume-weighted rolling mean."""
        try:
            vw_sum = (spread * volume).rolling(window=window, min_periods=self.min_periods).sum()
            vol_sum = volume.rolling(window=window, min_periods=self.min_periods).sum()
            return vw_sum / vol_sum
        except:
            return spread.rolling(window=window, min_periods=self.min_periods).mean()
    
    def _volume_weighted_std(self, spread: pd.Series, volume: pd.Series, window: int) -> pd.Series:
        """Calculate volume-weighted rolling standard deviation."""
        try:
            vw_mean = self._volume_weighted_mean(spread, volume, window)
            vw_var_sum = ((spread - vw_mean) ** 2 * volume).rolling(window=window, min_periods=self.min_periods).sum()
            vol_sum = volume.rolling(window=window, min_periods=self.min_periods).sum()
            vw_var = vw_var_sum / vol_sum
            return np.sqrt(vw_var)
        except:
            return spread.rolling(window=window, min_periods=self.min_periods).std()
    
    def _adaptive_zscore_adjustment(self, zscore: pd.Series, spread: pd.Series) -> pd.Series:
        """Apply adaptive adjustments to Z-Score based on market conditions."""
        try:
            # Calculate volatility regime
            volatility = spread.rolling(window=20).std()
            vol_percentile = volatility.rolling(window=100).rank(pct=True)
            
            # Adjust Z-Score based on volatility regime
            adjustment_factor = pd.Series(1.0, index=zscore.index)
            
            # High volatility periods - reduce sensitivity
            high_vol_mask = vol_percentile > 0.8
            adjustment_factor[high_vol_mask] = 0.7
            
            # Low volatility periods - increase sensitivity
            low_vol_mask = vol_percentile < 0.2
            adjustment_factor[low_vol_mask] = 1.3
            
            return zscore * adjustment_factor
        except:
            return zscore
    
    def _normalize_zscore(self, zscore: pd.Series) -> pd.Series:
        """Normalize Z-Score to 0-1 scale using tanh function."""
        try:
            # Use tanh to map to (-1, 1) then shift to (0, 1)
            normalized = np.tanh(zscore / 2.0)
            return (normalized + 1.0) / 2.0
        except:
            return pd.Series(0.5, index=zscore.index)
    
    def _calculate_extreme_levels(self, zscore: pd.Series) -> Dict[str, float]:
        """Calculate extreme Z-Score levels for signal generation."""
        try:
            if len(zscore.dropna()) < 50:
                return {'extreme_high': 2.0, 'high': 1.5, 'low': -1.5, 'extreme_low': -2.0}
            
            # Calculate percentile-based levels
            clean_zscore = zscore.dropna()
            
            return {
                'extreme_high': float(clean_zscore.quantile(0.95)),
                'high': float(clean_zscore.quantile(0.8)),
                'low': float(clean_zscore.quantile(0.2)),
                'extreme_low': float(clean_zscore.quantile(0.05))
            }
        except:
            return {'extreme_high': 2.0, 'high': 1.5, 'low': -1.5, 'extreme_low': -2.0}
    
    def _empty_zscore_result(self, index: pd.Index) -> ZScoreResult:
        """Return empty Z-Score result for error cases."""
        empty_series = pd.Series(0.0, index=index)
        return ZScoreResult(
            zscore=empty_series,
            rolling_mean=empty_series,
            rolling_std=empty_series,
            normalized_zscore=empty_series,
            extreme_levels={'extreme_high': 2.0, 'high': 1.5, 'low': -1.5, 'extreme_low': -2.0}
        )


class SpreadBollingerBands:
    """Bollinger Bands optimized for spread analysis."""
    
    def __init__(self, 
                 period: int = 20,
                 std_dev: float = 2.0,
                 adaptive: bool = True):
        self.period = period
        self.std_dev = std_dev
        self.adaptive = adaptive
    
    def calculate(self, spread: pd.Series, volume: Optional[pd.Series] = None) -> BollingerBandsResult:
        """Calculate Bollinger Bands for spread.
        
        Args:
            spread: Spread time series
            volume: Optional volume series for weighting
            
        Returns:
            BollingerBandsResult object
        """
        try:
            if len(spread) < self.period:
                return self._empty_bollinger_result(spread.index)
            
            # Calculate middle band (moving average)
            if volume is not None and len(volume) == len(spread):
                # Volume-weighted moving average
                vw_sum = (spread * volume).rolling(window=self.period).sum()
                vol_sum = volume.rolling(window=self.period).sum()
                middle_band = vw_sum / vol_sum
            else:
                middle_band = spread.rolling(window=self.period).mean()
            
            # Calculate standard deviation
            rolling_std = spread.rolling(window=self.period).std()
            
            # Adaptive standard deviation multiplier
            if self.adaptive:
                std_multiplier = self._adaptive_std_multiplier(spread, rolling_std)
            else:
                std_multiplier = pd.Series(self.std_dev, index=spread.index)
            
            # Calculate bands
            upper_band = middle_band + (std_multiplier * rolling_std)
            lower_band = middle_band - (std_multiplier * rolling_std)
            
            # Calculate additional metrics
            bandwidth = (upper_band - lower_band) / middle_band
            percent_b = (spread - lower_band) / (upper_band - lower_band)
            
            # Bollinger Band squeeze detection
            squeeze = self._detect_squeeze(bandwidth)
            
            return BollingerBandsResult(
                upper_band=upper_band,
                middle_band=middle_band,
                lower_band=lower_band,
                bandwidth=bandwidth,
                percent_b=percent_b,
                squeeze=squeeze
            )
        
        except Exception as e:
            logger.warning(f"Error calculating Bollinger Bands: {e}")
            return self._empty_bollinger_result(spread.index)
    
    def _adaptive_std_multiplier(self, spread: pd.Series, rolling_std: pd.Series) -> pd.Series:
        """Calculate adaptive standard deviation multiplier."""
        try:
            # Base multiplier
            multiplier = pd.Series(self.std_dev, index=spread.index)
            
            # Volatility adjustment
            volatility_percentile = rolling_std.rolling(window=50).rank(pct=True)
            
            # Increase multiplier in high volatility periods
            high_vol_mask = volatility_percentile > 0.8
            multiplier[high_vol_mask] = self.std_dev * 1.2
            
            # Decrease multiplier in low volatility periods
            low_vol_mask = volatility_percentile < 0.2
            multiplier[low_vol_mask] = self.std_dev * 0.8
            
            return multiplier
        except:
            return pd.Series(self.std_dev, index=spread.index)
    
    def _detect_squeeze(self, bandwidth: pd.Series, lookback: int = 20) -> pd.Series:
        """Detect Bollinger Band squeeze conditions."""
        try:
            # Calculate rolling minimum of bandwidth
            rolling_min = bandwidth.rolling(window=lookback).min()
            
            # Squeeze occurs when current bandwidth is at or near minimum
            squeeze_threshold = rolling_min * 1.1
            squeeze = bandwidth <= squeeze_threshold
            
            return squeeze.astype(float)
        except:
            return pd.Series(0.0, index=bandwidth.index)
    
    def _empty_bollinger_result(self, index: pd.Index) -> BollingerBandsResult:
        """Return empty Bollinger Bands result for error cases."""
        empty_series = pd.Series(0.0, index=index)
        return BollingerBandsResult(
            upper_band=empty_series,
            middle_band=empty_series,
            lower_band=empty_series,
            bandwidth=empty_series,
            percent_b=empty_series,
            squeeze=empty_series
        )


class SpreadMomentum:
    """Momentum indicators for spread analysis."""
    
    def __init__(self, 
                 short_period: int = 5,
                 long_period: int = 20,
                 signal_period: int = 9):
        self.short_period = short_period
        self.long_period = long_period
        self.signal_period = signal_period
    
    def calculate_momentum(self, spread: pd.Series) -> Dict[str, pd.Series]:
        """Calculate various momentum indicators for spread.
        
        Args:
            spread: Spread time series
            
        Returns:
            Dictionary of momentum indicators
        """
        try:
            results = {}
            
            # Rate of Change (ROC)
            results['roc_short'] = self._rate_of_change(spread, self.short_period)
            results['roc_long'] = self._rate_of_change(spread, self.long_period)
            
            # Momentum oscillator
            results['momentum'] = spread - spread.shift(self.long_period)
            
            # Velocity (first derivative)
            results['velocity'] = spread.diff()
            
            # Acceleration (second derivative)
            results['acceleration'] = results['velocity'].diff()
            
            # Momentum MACD
            results['macd'] = self._momentum_macd(spread)
            
            # Momentum RSI
            results['momentum_rsi'] = self._momentum_rsi(results['momentum'])
            
            return results
        
        except Exception as e:
            logger.warning(f"Error calculating momentum indicators: {e}")
            return {}
    
    def _rate_of_change(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate Rate of Change."""
        try:
            return ((series - series.shift(period)) / series.shift(period)) * 100
        except:
            return pd.Series(0.0, index=series.index)
    
    def _momentum_macd(self, spread: pd.Series) -> Dict[str, pd.Series]:
        """Calculate MACD for momentum."""
        try:
            # Calculate EMAs
            ema_short = spread.ewm(span=self.short_period).mean()
            ema_long = spread.ewm(span=self.long_period).mean()
            
            # MACD line
            macd_line = ema_short - ema_long
            
            # Signal line
            signal_line = macd_line.ewm(span=self.signal_period).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            return {
                'macd_line': macd_line,
                'signal_line': signal_line,
                'histogram': histogram
            }
        except:
            empty_series = pd.Series(0.0, index=spread.index)
            return {
                'macd_line': empty_series,
                'signal_line': empty_series,
                'histogram': empty_series
            }
    
    def _momentum_rsi(self, momentum: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI for momentum series."""
        try:
            delta = momentum.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.fillna(50.0)
        except:
            return pd.Series(50.0, index=momentum.index)


class SpreadRegimeDetector:
    """Detect market regimes for spread behavior."""
    
    def __init__(self, 
                 lookback_period: int = 50,
                 volatility_threshold: float = 1.5,
                 trend_threshold: float = 0.1):
        self.lookback_period = lookback_period
        self.volatility_threshold = volatility_threshold
        self.trend_threshold = trend_threshold
    
    def detect_regime(self, spread: pd.Series) -> pd.Series:
        """Detect market regime for spread.
        
        Args:
            spread: Spread time series
            
        Returns:
            Series of regime classifications
        """
        try:
            if len(spread) < self.lookback_period:
                return pd.Series(RegimeType.UNKNOWN.value, index=spread.index)
            
            regimes = pd.Series(RegimeType.UNKNOWN.value, index=spread.index)
            
            # Calculate rolling statistics
            rolling_mean = spread.rolling(window=self.lookback_period).mean()
            rolling_std = spread.rolling(window=self.lookback_period).std()
            rolling_trend = self._calculate_trend(spread, self.lookback_period)
            
            # Normalize volatility
            volatility_percentile = rolling_std.rolling(window=100).rank(pct=True)
            
            for i in range(self.lookback_period, len(spread)):
                current_vol = volatility_percentile.iloc[i]
                current_trend = abs(rolling_trend.iloc[i])
                
                # Classify regime
                if current_vol > 0.8:  # High volatility
                    regimes.iloc[i] = RegimeType.VOLATILE.value
                elif current_vol < 0.2:  # Low volatility
                    regimes.iloc[i] = RegimeType.STABLE.value
                elif current_trend > self.trend_threshold:  # Trending
                    regimes.iloc[i] = RegimeType.TRENDING.value
                else:  # Mean reverting
                    regimes.iloc[i] = RegimeType.MEAN_REVERTING.value
            
            return regimes
        
        except Exception as e:
            logger.warning(f"Error detecting regime: {e}")
            return pd.Series(RegimeType.UNKNOWN.value, index=spread.index)
    
    def _calculate_trend(self, spread: pd.Series, period: int) -> pd.Series:
        """Calculate trend strength using linear regression slope."""
        try:
            trends = pd.Series(0.0, index=spread.index)
            
            for i in range(period, len(spread)):
                window_data = spread.iloc[i-period:i]
                x = np.arange(len(window_data))
                y = window_data.values
                
                # Calculate slope using least squares
                slope = np.polyfit(x, y, 1)[0]
                trends.iloc[i] = slope / window_data.mean()  # Normalize by mean
            
            return trends
        except:
            return pd.Series(0.0, index=spread.index)


class AdaptiveThresholds:
    """Adaptive threshold calculation for spread trading signals."""
    
    def __init__(self, 
                 base_threshold: float = 2.0,
                 adaptation_period: int = 100,
                 min_threshold: float = 1.0,
                 max_threshold: float = 4.0):
        self.base_threshold = base_threshold
        self.adaptation_period = adaptation_period
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
    
    def calculate_thresholds(self, 
                           zscore: pd.Series,
                           regime: pd.Series) -> Dict[str, pd.Series]:
        """Calculate adaptive thresholds based on market regime and historical performance.
        
        Args:
            zscore: Z-Score series
            regime: Market regime series
            
        Returns:
            Dictionary of threshold series
        """
        try:
            thresholds = {
                'entry_long': pd.Series(self.base_threshold, index=zscore.index),
                'entry_short': pd.Series(-self.base_threshold, index=zscore.index),
                'exit_long': pd.Series(0.0, index=zscore.index),
                'exit_short': pd.Series(0.0, index=zscore.index)
            }
            
            # Adapt thresholds based on regime
            for i in range(len(zscore)):
                current_regime = regime.iloc[i] if i < len(regime) else RegimeType.UNKNOWN.value
                
                if current_regime == RegimeType.MEAN_REVERTING.value:
                    # Lower thresholds for mean-reverting regime
                    multiplier = 0.8
                elif current_regime == RegimeType.VOLATILE.value:
                    # Higher thresholds for volatile regime
                    multiplier = 1.3
                elif current_regime == RegimeType.TRENDING.value:
                    # Much higher thresholds for trending regime
                    multiplier = 1.5
                else:
                    multiplier = 1.0
                
                # Apply multiplier with bounds
                entry_threshold = np.clip(
                    self.base_threshold * multiplier,
                    self.min_threshold,
                    self.max_threshold
                )
                
                thresholds['entry_long'].iloc[i] = -entry_threshold
                thresholds['entry_short'].iloc[i] = entry_threshold
                thresholds['exit_long'].iloc[i] = -entry_threshold * 0.3
                thresholds['exit_short'].iloc[i] = entry_threshold * 0.3
            
            return thresholds
        
        except Exception as e:
            logger.warning(f"Error calculating adaptive thresholds: {e}")
            return {
                'entry_long': pd.Series(-self.base_threshold, index=zscore.index),
                'entry_short': pd.Series(self.base_threshold, index=zscore.index),
                'exit_long': pd.Series(0.0, index=zscore.index),
                'exit_short': pd.Series(0.0, index=zscore.index)
            }


class SpreadIndicatorSuite:
    """Comprehensive suite of spread indicators for pairs trading."""
    
    def __init__(self, 
                 zscore_period: int = 60,
                 bollinger_period: int = 20,
                 momentum_short: int = 5,
                 momentum_long: int = 20):
        self.zscore_calculator = SpreadZScore(lookback_period=zscore_period)
        self.bollinger_calculator = SpreadBollingerBands(period=bollinger_period)
        self.momentum_calculator = SpreadMomentum(short_period=momentum_short, long_period=momentum_long)
        self.regime_detector = SpreadRegimeDetector()
        self.threshold_calculator = AdaptiveThresholds()
    
    def calculate_all_indicators(self, 
                               spread: pd.Series,
                               volume: Optional[pd.Series] = None) -> Dict[str, Union[pd.Series, Dict]]:
        """Calculate all spread indicators.
        
        Args:
            spread: Spread time series
            volume: Optional volume series
            
        Returns:
            Dictionary containing all indicator results
        """
        try:
            results = {}
            
            # Z-Score indicators
            zscore_result = self.zscore_calculator.calculate(spread, volume)
            results['zscore'] = zscore_result.zscore
            results['zscore_normalized'] = zscore_result.normalized_zscore
            results['zscore_levels'] = zscore_result.extreme_levels
            
            # Bollinger Bands
            bollinger_result = self.bollinger_calculator.calculate(spread, volume)
            results['bollinger_upper'] = bollinger_result.upper_band
            results['bollinger_middle'] = bollinger_result.middle_band
            results['bollinger_lower'] = bollinger_result.lower_band
            results['bollinger_bandwidth'] = bollinger_result.bandwidth
            results['bollinger_percent_b'] = bollinger_result.percent_b
            results['bollinger_squeeze'] = bollinger_result.squeeze
            
            # Momentum indicators
            momentum_results = self.momentum_calculator.calculate_momentum(spread)
            results.update(momentum_results)
            
            # Regime detection
            results['regime'] = self.regime_detector.detect_regime(spread)
            
            # Adaptive thresholds
            threshold_results = self.threshold_calculator.calculate_thresholds(
                zscore_result.zscore, results['regime']
            )
            results.update(threshold_results)
            
            return results
        
        except Exception as e:
            logger.error(f"Error calculating spread indicators: {e}")
            return {}
    
    def generate_signals(self, 
                        spread: pd.Series,
                        volume: Optional[pd.Series] = None) -> pd.DataFrame:
        """Generate trading signals based on spread indicators.
        
        Args:
            spread: Spread time series
            volume: Optional volume series
            
        Returns:
            DataFrame containing trading signals
        """
        try:
            # Calculate all indicators
            indicators = self.calculate_all_indicators(spread, volume)
            
            if not indicators:
                return pd.DataFrame()
            
            # Initialize signals DataFrame
            signals = pd.DataFrame(index=spread.index)
            signals['spread'] = spread
            
            # Z-Score signals
            zscore = indicators.get('zscore', pd.Series(0.0, index=spread.index))
            entry_long_threshold = indicators.get('entry_long', pd.Series(-2.0, index=spread.index))
            entry_short_threshold = indicators.get('entry_short', pd.Series(2.0, index=spread.index))
            
            signals['zscore_long_signal'] = (zscore <= entry_long_threshold).astype(int)
            signals['zscore_short_signal'] = (zscore >= entry_short_threshold).astype(int)
            
            # Bollinger Bands signals
            percent_b = indicators.get('bollinger_percent_b', pd.Series(0.5, index=spread.index))
            signals['bb_long_signal'] = (percent_b <= 0.1).astype(int)
            signals['bb_short_signal'] = (percent_b >= 0.9).astype(int)
            
            # Momentum confirmation
            momentum = indicators.get('momentum', pd.Series(0.0, index=spread.index))
            signals['momentum_confirmation'] = np.where(
                momentum > 0, 1, np.where(momentum < 0, -1, 0)
            )
            
            # Regime filter
            regime = indicators.get('regime', pd.Series(RegimeType.UNKNOWN.value, index=spread.index))
            signals['regime_filter'] = (regime == RegimeType.MEAN_REVERTING.value).astype(int)
            
            # Combined signals
            signals['long_signal'] = (
                (signals['zscore_long_signal'] | signals['bb_long_signal']) &
                signals['regime_filter']
            ).astype(int)
            
            signals['short_signal'] = (
                (signals['zscore_short_signal'] | signals['bb_short_signal']) &
                signals['regime_filter']
            ).astype(int)
            
            # Signal strength
            signals['signal_strength'] = np.where(
                signals['long_signal'] == 1, -abs(zscore),
                np.where(signals['short_signal'] == 1, abs(zscore), 0)
            )
            
            return signals
        
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return pd.DataFrame()
    
    def backtest_signals(self, 
                        signals: pd.DataFrame,
                        transaction_cost: float = 0.001) -> Dict[str, float]:
        """Backtest trading signals and calculate performance metrics.
        
        Args:
            signals: DataFrame containing trading signals
            transaction_cost: Transaction cost per trade
            
        Returns:
            Dictionary of performance metrics
        """
        try:
            if signals.empty or 'spread' not in signals.columns:
                return {}
            
            # Calculate returns
            spread_returns = signals['spread'].pct_change().fillna(0)
            
            # Generate positions
            positions = pd.Series(0, index=signals.index)
            current_position = 0
            
            for i in range(1, len(signals)):
                if signals['long_signal'].iloc[i] == 1 and current_position <= 0:
                    current_position = 1
                elif signals['short_signal'].iloc[i] == 1 and current_position >= 0:
                    current_position = -1
                elif (signals['long_signal'].iloc[i] == 0 and signals['short_signal'].iloc[i] == 0 and
                      current_position != 0):
                    current_position = 0
                
                positions.iloc[i] = current_position
            
            # Calculate strategy returns
            strategy_returns = positions.shift(1) * spread_returns
            
            # Apply transaction costs
            position_changes = positions.diff().abs()
            transaction_costs = position_changes * transaction_cost
            strategy_returns -= transaction_costs
            
            # Calculate performance metrics
            total_return = (1 + strategy_returns).prod() - 1
            annualized_return = (1 + total_return) ** (252 / len(strategy_returns)) - 1
            volatility = strategy_returns.std() * np.sqrt(252)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            max_drawdown = self._calculate_max_drawdown(strategy_returns)
            win_rate = (strategy_returns > 0).sum() / len(strategy_returns[strategy_returns != 0])
            
            return {
                'total_return': float(total_return),
                'annualized_return': float(annualized_return),
                'volatility': float(volatility),
                'sharpe_ratio': float(sharpe_ratio),
                'max_drawdown': float(max_drawdown),
                'win_rate': float(win_rate),
                'total_trades': int(position_changes.sum() / 2)
            }
        
        except Exception as e:
            logger.error(f"Error backtesting signals: {e}")
            return {}
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown."""
        try:
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return float(drawdown.min())
        except:
            return 0.0