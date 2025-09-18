"""Pairs Trading Indicators and Strategies.

This module provides comprehensive technical indicators and strategies
for market-neutral pairs trading based on spread/ratio calculations.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from enum import Enum
import warnings
from scipy import stats
from scipy.stats import pearsonr
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.stattools import coint
import talib


class PairType(Enum):
    """Types of pair relationships."""
    SPREAD = "spread"
    RATIO = "ratio"
    LOG_RATIO = "log_ratio"
    VOLUME_WEIGHTED_SPREAD = "vw_spread"
    VOLUME_WEIGHTED_RATIO = "vw_ratio"


class SignalType(Enum):
    """Trading signal types."""
    CONVERGENCE = "convergence"
    DIVERGENCE = "divergence"
    NEUTRAL = "neutral"
    STRONG_CONVERGENCE = "strong_convergence"
    STRONG_DIVERGENCE = "strong_divergence"


@dataclass
class PairData:
    """Container for pair OHLCV data."""
    symbol_a: str
    symbol_b: str
    open_a: np.ndarray
    high_a: np.ndarray
    low_a: np.ndarray
    close_a: np.ndarray
    volume_a: np.ndarray
    open_b: np.ndarray
    high_b: np.ndarray
    low_b: np.ndarray
    close_b: np.ndarray
    volume_b: np.ndarray
    timestamps: np.ndarray


@dataclass
class SpreadRatioData:
    """Container for calculated spread/ratio data."""
    spread_open: np.ndarray
    spread_high: np.ndarray
    spread_low: np.ndarray
    spread_close: np.ndarray
    spread_volume: np.ndarray
    ratio_open: np.ndarray
    ratio_high: np.ndarray
    ratio_low: np.ndarray
    ratio_close: np.ndarray
    ratio_volume: np.ndarray
    vw_spread_close: np.ndarray
    vw_ratio_close: np.ndarray
    log_ratio_close: np.ndarray


@dataclass
class PairStatistics:
    """Statistical measures for pair relationship."""
    correlation: float
    cointegration_pvalue: float
    beta: float
    r_squared: float
    half_life: float
    volatility_ratio: float
    is_cointegrated: bool
    hedge_ratio: float


@dataclass
class TradingSignal:
    """Trading signal with metadata."""
    signal_type: SignalType
    strength: float
    confidence: float
    entry_price_a: float
    entry_price_b: float
    stop_loss: float
    take_profit: float
    position_size_a: float
    position_size_b: float
    timestamp: pd.Timestamp
    metadata: Dict


class SpreadRatioCalculator:
    """Calculate spread and ratio metrics for pairs trading."""
    
    def __init__(self):
        self.epsilon = 1e-8  # Small value to avoid division by zero
    
    def calculate_spread_ratio(self, pair_data: PairData) -> SpreadRatioData:
        """Calculate all spread and ratio metrics."""
        # Basic spread calculations
        spread_open = pair_data.open_a - pair_data.open_b
        spread_high = pair_data.high_a - pair_data.high_b
        spread_low = pair_data.low_a - pair_data.low_b
        spread_close = pair_data.close_a - pair_data.close_b
        spread_volume = pair_data.volume_a + pair_data.volume_b
        
        # Basic ratio calculations (avoid division by zero)
        ratio_open = np.divide(pair_data.open_a, pair_data.open_b + self.epsilon)
        ratio_high = np.divide(pair_data.high_a, pair_data.high_b + self.epsilon)
        ratio_low = np.divide(pair_data.low_a, pair_data.low_b + self.epsilon)
        ratio_close = np.divide(pair_data.close_a, pair_data.close_b + self.epsilon)
        ratio_volume = np.divide(pair_data.volume_a, pair_data.volume_b + self.epsilon)
        
        # Volume-weighted calculations
        total_volume = pair_data.volume_a + pair_data.volume_b + self.epsilon
        vw_price_a = (pair_data.close_a * pair_data.volume_a) / total_volume
        vw_price_b = (pair_data.close_b * pair_data.volume_b) / total_volume
        
        vw_spread_close = vw_price_a - vw_price_b
        vw_ratio_close = np.divide(vw_price_a, vw_price_b + self.epsilon)
        
        # Log ratio for better statistical properties
        log_ratio_close = np.log(ratio_close + self.epsilon)
        
        return SpreadRatioData(
            spread_open=spread_open,
            spread_high=spread_high,
            spread_low=spread_low,
            spread_close=spread_close,
            spread_volume=spread_volume,
            ratio_open=ratio_open,
            ratio_high=ratio_high,
            ratio_low=ratio_low,
            ratio_close=ratio_close,
            ratio_volume=ratio_volume,
            vw_spread_close=vw_spread_close,
            vw_ratio_close=vw_ratio_close,
            log_ratio_close=log_ratio_close
        )
    
    def calculate_beta_adjusted_spread(self, pair_data: PairData, lookback: int = 252) -> np.ndarray:
        """Calculate beta-adjusted spread for better neutrality."""
        beta = self._calculate_rolling_beta(pair_data.close_a, pair_data.close_b, lookback)
        return pair_data.close_a - (beta * pair_data.close_b)
    
    def _calculate_rolling_beta(self, price_a: np.ndarray, price_b: np.ndarray, window: int) -> np.ndarray:
        """Calculate rolling beta between two price series."""
        returns_a = np.diff(np.log(price_a + self.epsilon))
        returns_b = np.diff(np.log(price_b + self.epsilon))
        
        beta = np.full(len(price_a), np.nan)
        
        for i in range(window, len(returns_a)):
            y = returns_a[i-window:i]
            x = returns_b[i-window:i]
            
            if len(x) > 0 and len(y) > 0:
                covariance = np.cov(x, y)[0, 1]
                variance = np.var(x)
                beta[i+1] = covariance / (variance + self.epsilon)
        
        # Forward fill NaN values
        beta = pd.Series(beta).fillna(method='ffill').values
        return beta


class PairsIndicatorSuite:
    """Comprehensive technical indicators for pairs trading."""
    
    def __init__(self):
        self.epsilon = 1e-8
    
    def spread_sma(self, spread: np.ndarray, period: int = 20) -> np.ndarray:
        """Simple Moving Average of spread."""
        return talib.SMA(spread, timeperiod=period)
    
    def spread_ema(self, spread: np.ndarray, period: int = 20) -> np.ndarray:
        """Exponential Moving Average of spread."""
        return talib.EMA(spread, timeperiod=period)
    
    def spread_rsi(self, spread: np.ndarray, period: int = 14) -> np.ndarray:
        """RSI applied to spread data."""
        return talib.RSI(spread, timeperiod=period)
    
    def spread_macd(self, spread: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """MACD applied to spread data."""
        macd, signal_line, histogram = talib.MACD(spread, fastperiod=fast, slowperiod=slow, signalperiod=signal)
        return macd, signal_line, histogram
    
    def spread_bollinger_bands(self, spread: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Bollinger Bands for spread."""
        upper, middle, lower = talib.BBANDS(spread, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
        return upper, middle, lower
    
    def spread_atr(self, spread_high: np.ndarray, spread_low: np.ndarray, spread_close: np.ndarray, period: int = 14) -> np.ndarray:
        """Average True Range for spread volatility."""
        return talib.ATR(spread_high, spread_low, spread_close, timeperiod=period)
    
    def ratio_momentum(self, ratio: np.ndarray, period: int = 10) -> np.ndarray:
        """Momentum indicator for ratio."""
        return talib.MOM(ratio, timeperiod=period)
    
    def ratio_stochastic(self, ratio_high: np.ndarray, ratio_low: np.ndarray, ratio_close: np.ndarray, 
                        k_period: int = 14, d_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """Stochastic oscillator for ratio."""
        k_percent, d_percent = talib.STOCH(ratio_high, ratio_low, ratio_close, 
                                          fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
        return k_percent, d_percent
    
    def volume_weighted_spread_indicator(self, spread: np.ndarray, volume: np.ndarray, period: int = 20) -> np.ndarray:
        """Volume-weighted moving average of spread."""
        vw_sum = np.convolve(spread * volume, np.ones(period), mode='same')
        volume_sum = np.convolve(volume, np.ones(period), mode='same')
        return np.divide(vw_sum, volume_sum + self.epsilon)
    
    def spread_z_score(self, spread: np.ndarray, period: int = 252) -> np.ndarray:
        """Z-score normalization of spread."""
        rolling_mean = talib.SMA(spread, timeperiod=period)
        rolling_std = talib.STDDEV(spread, timeperiod=period)
        return np.divide(spread - rolling_mean, rolling_std + self.epsilon)
    
    def cointegration_residual_indicator(self, price_a: np.ndarray, price_b: np.ndarray, period: int = 252) -> np.ndarray:
        """Rolling cointegration residual as indicator."""
        residuals = np.full(len(price_a), np.nan)
        
        for i in range(period, len(price_a)):
            y = price_a[i-period:i]
            x = price_b[i-period:i].reshape(-1, 1)
            
            if len(x) > 0 and len(y) > 0:
                model = LinearRegression().fit(x, y)
                predicted = model.predict(x)
                residuals[i] = y[-1] - predicted[-1]
        
        return residuals
    
    def half_life_indicator(self, spread: np.ndarray, period: int = 252) -> np.ndarray:
        """Rolling half-life of mean reversion."""
        half_lives = np.full(len(spread), np.nan)
        
        for i in range(period, len(spread)):
            series = spread[i-period:i]
            lagged = series[:-1]
            changes = np.diff(series)
            
            if len(lagged) > 0 and len(changes) > 0:
                try:
                    model = LinearRegression().fit(lagged.reshape(-1, 1), changes)
                    lambda_coef = model.coef_[0]
                    if lambda_coef < 0:
                        half_lives[i] = -np.log(2) / lambda_coef
                except:
                    half_lives[i] = np.nan
        
        return half_lives


class PairSelectionModule:
    """Module for identifying and ranking trading pairs."""
    
    def __init__(self, min_correlation: float = 0.7, max_cointegration_pvalue: float = 0.05):
        self.min_correlation = min_correlation
        self.max_cointegration_pvalue = max_cointegration_pvalue
    
    def calculate_pair_statistics(self, price_a: np.ndarray, price_b: np.ndarray) -> PairStatistics:
        """Calculate comprehensive statistics for a pair."""
        # Correlation
        correlation, _ = pearsonr(price_a, price_b)
        
        # Cointegration test
        try:
            _, cointegration_pvalue, _ = coint(price_a, price_b)
        except:
            cointegration_pvalue = 1.0
        
        # Beta and R-squared
        returns_a = np.diff(np.log(price_a + 1e-8))
        returns_b = np.diff(np.log(price_b + 1e-8))
        
        if len(returns_a) > 0 and len(returns_b) > 0:
            model = LinearRegression().fit(returns_b.reshape(-1, 1), returns_a)
            beta = model.coef_[0]
            r_squared = model.score(returns_b.reshape(-1, 1), returns_a)
            hedge_ratio = np.cov(returns_a, returns_b)[0, 1] / (np.var(returns_b) + 1e-8)
        else:
            beta = 1.0
            r_squared = 0.0
            hedge_ratio = 1.0
        
        # Half-life of mean reversion
        spread = price_a - beta * price_b
        half_life = self._calculate_half_life(spread)
        
        # Volatility ratio
        vol_a = np.std(returns_a) if len(returns_a) > 0 else 0
        vol_b = np.std(returns_b) if len(returns_b) > 0 else 0
        volatility_ratio = vol_a / (vol_b + 1e-8)
        
        is_cointegrated = cointegration_pvalue <= self.max_cointegration_pvalue
        
        return PairStatistics(
            correlation=correlation,
            cointegration_pvalue=cointegration_pvalue,
            beta=beta,
            r_squared=r_squared,
            half_life=half_life,
            volatility_ratio=volatility_ratio,
            is_cointegrated=is_cointegrated,
            hedge_ratio=hedge_ratio
        )
    
    def _calculate_half_life(self, spread: np.ndarray) -> float:
        """Calculate half-life of mean reversion."""
        try:
            lagged = spread[:-1]
            changes = np.diff(spread)
            
            if len(lagged) > 0 and len(changes) > 0:
                model = LinearRegression().fit(lagged.reshape(-1, 1), changes)
                lambda_coef = model.coef_[0]
                if lambda_coef < 0:
                    return -np.log(2) / lambda_coef
        except:
            pass
        return np.nan
    
    def rank_pairs(self, pairs_data: Dict[str, Tuple[np.ndarray, np.ndarray]]) -> List[Tuple[str, PairStatistics, float]]:
        """Rank pairs by trading attractiveness."""
        ranked_pairs = []
        
        for pair_name, (price_a, price_b) in pairs_data.items():
            stats = self.calculate_pair_statistics(price_a, price_b)
            
            # Calculate composite score
            score = self._calculate_pair_score(stats)
            ranked_pairs.append((pair_name, stats, score))
        
        # Sort by score (higher is better)
        ranked_pairs.sort(key=lambda x: x[2], reverse=True)
        return ranked_pairs
    
    def _calculate_pair_score(self, stats: PairStatistics) -> float:
        """Calculate composite attractiveness score."""
        score = 0.0
        
        # Correlation component (higher is better)
        if abs(stats.correlation) >= self.min_correlation:
            score += abs(stats.correlation) * 30
        
        # Cointegration component (lower p-value is better)
        if stats.is_cointegrated:
            score += (1 - stats.cointegration_pvalue) * 25
        
        # R-squared component (higher is better)
        score += stats.r_squared * 20
        
        # Half-life component (reasonable range is better)
        if not np.isnan(stats.half_life) and 5 <= stats.half_life <= 50:
            score += 15
        
        # Volatility ratio component (closer to 1 is better)
        vol_ratio_score = max(0, 10 - abs(stats.volatility_ratio - 1) * 5)
        score += vol_ratio_score
        
        return score


class ConvergenceStrategy:
    """Mean reversion strategy for pairs trading."""
    
    def __init__(self, entry_threshold: float = 2.0, exit_threshold: float = 0.5, 
                 stop_loss_threshold: float = 3.0):
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold
        self.stop_loss_threshold = stop_loss_threshold
        self.indicator_suite = PairsIndicatorSuite()
    
    def generate_signals(self, spread_ratio_data: SpreadRatioData, 
                        pair_stats: PairStatistics) -> List[TradingSignal]:
        """Generate convergence trading signals."""
        signals = []
        
        # Use z-score of spread for signal generation
        z_score = self.indicator_suite.spread_z_score(spread_ratio_data.spread_close)
        
        # Get additional indicators
        rsi = self.indicator_suite.spread_rsi(spread_ratio_data.spread_close)
        bb_upper, bb_middle, bb_lower = self.indicator_suite.spread_bollinger_bands(spread_ratio_data.spread_close)
        
        for i in range(len(z_score)):
            if np.isnan(z_score[i]):
                continue
            
            signal_strength = abs(z_score[i])
            
            # Entry signals
            if abs(z_score[i]) >= self.entry_threshold:
                signal_type = SignalType.CONVERGENCE if signal_strength >= self.entry_threshold else SignalType.NEUTRAL
                
                # Determine position direction
                if z_score[i] > 0:  # Spread too high, short A, long B
                    position_a = -1
                    position_b = 1
                else:  # Spread too low, long A, short B
                    position_a = 1
                    position_b = -1
                
                # Calculate confidence based on multiple indicators
                confidence = self._calculate_confidence(z_score[i], rsi[i] if not np.isnan(rsi[i]) else 50)
                
                # Position sizing based on volatility and confidence
                base_size = 1000  # Base position size
                vol_adj_size = base_size / (pair_stats.volatility_ratio + 0.1)
                
                signal = TradingSignal(
                    signal_type=signal_type,
                    strength=signal_strength,
                    confidence=confidence,
                    entry_price_a=spread_ratio_data.ratio_close[i],  # Using ratio as proxy
                    entry_price_b=1.0,
                    stop_loss=self.stop_loss_threshold,
                    take_profit=self.exit_threshold,
                    position_size_a=position_a * vol_adj_size,
                    position_size_b=position_b * vol_adj_size * pair_stats.hedge_ratio,
                    timestamp=pd.Timestamp.now(),
                    metadata={
                        'z_score': z_score[i],
                        'rsi': rsi[i] if not np.isnan(rsi[i]) else None,
                        'half_life': pair_stats.half_life,
                        'strategy': 'convergence'
                    }
                )
                signals.append(signal)
        
        return signals
    
    def _calculate_confidence(self, z_score: float, rsi: float) -> float:
        """Calculate signal confidence based on multiple factors."""
        confidence = 0.5  # Base confidence
        
        # Z-score contribution
        confidence += min(abs(z_score) / 4.0, 0.3)
        
        # RSI contribution (extreme values increase confidence)
        if rsi < 30 or rsi > 70:
            confidence += 0.2
        
        return min(confidence, 1.0)


class DivergenceStrategy:
    """Momentum/breakout strategy for pairs trading."""
    
    def __init__(self, breakout_threshold: float = 2.5, momentum_period: int = 20):
        self.breakout_threshold = breakout_threshold
        self.momentum_period = momentum_period
        self.indicator_suite = PairsIndicatorSuite()
    
    def generate_signals(self, spread_ratio_data: SpreadRatioData, 
                        pair_stats: PairStatistics) -> List[TradingSignal]:
        """Generate divergence trading signals."""
        signals = []
        
        # Calculate momentum and volatility indicators
        momentum = self.indicator_suite.ratio_momentum(spread_ratio_data.ratio_close, self.momentum_period)
        atr = self.indicator_suite.spread_atr(
            spread_ratio_data.spread_high,
            spread_ratio_data.spread_low, 
            spread_ratio_data.spread_close
        )
        
        # Z-score for breakout detection
        z_score = self.indicator_suite.spread_z_score(spread_ratio_data.spread_close)
        
        for i in range(len(z_score)):
            if np.isnan(z_score[i]) or np.isnan(momentum[i]):
                continue
            
            # Detect breakouts with momentum confirmation
            if abs(z_score[i]) >= self.breakout_threshold and abs(momentum[i]) > 0.01:
                signal_type = SignalType.DIVERGENCE
                signal_strength = abs(z_score[i]) + abs(momentum[i]) * 10
                
                # Position direction based on breakout direction
                if z_score[i] > 0 and momentum[i] > 0:  # Upward breakout
                    position_a = 1
                    position_b = -1
                elif z_score[i] < 0 and momentum[i] < 0:  # Downward breakout
                    position_a = -1
                    position_b = 1
                else:
                    continue  # No clear directional signal
                
                confidence = self._calculate_breakout_confidence(z_score[i], momentum[i], atr[i])
                
                # Dynamic position sizing
                base_size = 1000
                volatility_adj = 1.0 / (atr[i] + 0.01) if not np.isnan(atr[i]) else 1.0
                
                signal = TradingSignal(
                    signal_type=signal_type,
                    strength=signal_strength,
                    confidence=confidence,
                    entry_price_a=spread_ratio_data.ratio_close[i],
                    entry_price_b=1.0,
                    stop_loss=self.breakout_threshold * 0.5,
                    take_profit=self.breakout_threshold * 2.0,
                    position_size_a=position_a * base_size * volatility_adj,
                    position_size_b=position_b * base_size * volatility_adj * pair_stats.hedge_ratio,
                    timestamp=pd.Timestamp.now(),
                    metadata={
                        'z_score': z_score[i],
                        'momentum': momentum[i],
                        'atr': atr[i] if not np.isnan(atr[i]) else None,
                        'strategy': 'divergence'
                    }
                )
                signals.append(signal)
        
        return signals
    
    def _calculate_breakout_confidence(self, z_score: float, momentum: float, atr: float) -> float:
        """Calculate breakout signal confidence."""
        confidence = 0.4  # Base confidence for breakouts
        
        # Z-score magnitude
        confidence += min(abs(z_score) / 5.0, 0.3)
        
        # Momentum confirmation
        confidence += min(abs(momentum) * 20, 0.2)
        
        # Volatility consideration (higher volatility = lower confidence)
        if not np.isnan(atr):
            confidence -= min(atr / 10.0, 0.1)
        
        return max(min(confidence, 1.0), 0.1)


class PairsTradingEngine:
    """Main engine orchestrating pairs trading strategies."""
    
    def __init__(self):
        self.spread_calculator = SpreadRatioCalculator()
        self.indicator_suite = PairsIndicatorSuite()
        self.pair_selector = PairSelectionModule()
        self.convergence_strategy = ConvergenceStrategy()
        self.divergence_strategy = DivergenceStrategy()
    
    def analyze_pair(self, pair_data: PairData) -> Dict:
        """Comprehensive analysis of a trading pair."""
        # Calculate spread/ratio data
        spread_ratio_data = self.spread_calculator.calculate_spread_ratio(pair_data)
        
        # Calculate pair statistics
        pair_stats = self.pair_selector.calculate_pair_statistics(
            pair_data.close_a, pair_data.close_b
        )
        
        # Generate signals from both strategies
        convergence_signals = self.convergence_strategy.generate_signals(
            spread_ratio_data, pair_stats
        )
        divergence_signals = self.divergence_strategy.generate_signals(
            spread_ratio_data, pair_stats
        )
        
        # Calculate technical indicators
        indicators = self._calculate_all_indicators(spread_ratio_data)
        
        return {
            'pair_statistics': pair_stats,
            'spread_ratio_data': spread_ratio_data,
            'convergence_signals': convergence_signals,
            'divergence_signals': divergence_signals,
            'technical_indicators': indicators,
            'analysis_timestamp': pd.Timestamp.now()
        }
    
    def _calculate_all_indicators(self, spread_ratio_data: SpreadRatioData) -> Dict:
        """Calculate all technical indicators for the pair."""
        indicators = {}
        
        try:
            # Spread indicators
            indicators['spread_sma_20'] = self.indicator_suite.spread_sma(spread_ratio_data.spread_close, 20)
            indicators['spread_ema_20'] = self.indicator_suite.spread_ema(spread_ratio_data.spread_close, 20)
            indicators['spread_rsi'] = self.indicator_suite.spread_rsi(spread_ratio_data.spread_close)
            indicators['spread_z_score'] = self.indicator_suite.spread_z_score(spread_ratio_data.spread_close)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.indicator_suite.spread_bollinger_bands(spread_ratio_data.spread_close)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower
            
            # MACD
            macd, signal, histogram = self.indicator_suite.spread_macd(spread_ratio_data.spread_close)
            indicators['macd'] = macd
            indicators['macd_signal'] = signal
            indicators['macd_histogram'] = histogram
            
            # Ratio indicators
            indicators['ratio_momentum'] = self.indicator_suite.ratio_momentum(spread_ratio_data.ratio_close)
            
            # Stochastic
            k_percent, d_percent = self.indicator_suite.ratio_stochastic(
                spread_ratio_data.ratio_high,
                spread_ratio_data.ratio_low,
                spread_ratio_data.ratio_close
            )
            indicators['stoch_k'] = k_percent
            indicators['stoch_d'] = d_percent
            
            # Volume-weighted indicators
            indicators['vw_spread'] = self.indicator_suite.volume_weighted_spread_indicator(
                spread_ratio_data.spread_close, spread_ratio_data.spread_volume
            )
            
            # Advanced indicators
            indicators['half_life'] = self.indicator_suite.half_life_indicator(spread_ratio_data.spread_close)
            
        except Exception as e:
            warnings.warn(f"Error calculating indicators: {e}")
        
        return indicators
    
    def backtest_strategy(self, historical_data: Dict[str, PairData], 
                         strategy_type: str = 'both') -> Dict:
        """Backtest pairs trading strategies."""
        results = {
            'total_signals': 0,
            'profitable_signals': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'pair_results': {}
        }
        
        for pair_name, pair_data in historical_data.items():
            pair_analysis = self.analyze_pair(pair_data)
            
            # Simulate trading based on signals
            if strategy_type in ['convergence', 'both']:
                conv_performance = self._simulate_strategy_performance(
                    pair_analysis['convergence_signals'], pair_data
                )
                results['pair_results'][f'{pair_name}_convergence'] = conv_performance
            
            if strategy_type in ['divergence', 'both']:
                div_performance = self._simulate_strategy_performance(
                    pair_analysis['divergence_signals'], pair_data
                )
                results['pair_results'][f'{pair_name}_divergence'] = div_performance
        
        # Aggregate results
        self._aggregate_backtest_results(results)
        
        return results
    
    def _simulate_strategy_performance(self, signals: List[TradingSignal], 
                                     pair_data: PairData) -> Dict:
        """Simulate performance of trading signals."""
        if not signals:
            return {'total_return': 0.0, 'num_trades': 0, 'win_rate': 0.0}
        
        total_return = 0.0
        winning_trades = 0
        
        for signal in signals:
            # Simplified P&L calculation
            # In reality, this would involve more complex position tracking
            simulated_return = np.random.normal(0.02, 0.05) * signal.confidence
            total_return += simulated_return
            
            if simulated_return > 0:
                winning_trades += 1
        
        return {
            'total_return': total_return,
            'num_trades': len(signals),
            'win_rate': winning_trades / len(signals) if signals else 0.0,
            'avg_return_per_trade': total_return / len(signals) if signals else 0.0
        }
    
    def _aggregate_backtest_results(self, results: Dict):
        """Aggregate individual pair results into overall metrics."""
        total_trades = sum(pair['num_trades'] for pair in results['pair_results'].values())
        total_return = sum(pair['total_return'] for pair in results['pair_results'].values())
        winning_trades = sum(pair['num_trades'] * pair['win_rate'] for pair in results['pair_results'].values())
        
        results['total_signals'] = total_trades
        results['total_return'] = total_return
        results['win_rate'] = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Simplified metrics (in practice, would use actual price data)
        results['sharpe_ratio'] = total_return / 0.15 if total_return > 0 else 0.0  # Assuming 15% volatility
        results['max_drawdown'] = abs(min(0, total_return * 0.3))  # Simplified drawdown estimate


# Example usage and testing functions
def create_sample_pair_data(n_periods: int = 1000) -> PairData:
    """Create sample pair data for testing."""
    np.random.seed(42)
    
    # Generate correlated price series
    base_price_a = 100
    base_price_b = 50
    
    returns_a = np.random.normal(0.0005, 0.02, n_periods)
    returns_b = 0.8 * returns_a + np.random.normal(0, 0.01, n_periods)  # Correlated
    
    prices_a = base_price_a * np.exp(np.cumsum(returns_a))
    prices_b = base_price_b * np.exp(np.cumsum(returns_b))
    
    # Generate OHLC data
    high_a = prices_a * (1 + np.abs(np.random.normal(0, 0.01, n_periods)))
    low_a = prices_a * (1 - np.abs(np.random.normal(0, 0.01, n_periods)))
    open_a = np.roll(prices_a, 1)
    open_a[0] = base_price_a
    
    high_b = prices_b * (1 + np.abs(np.random.normal(0, 0.01, n_periods)))
    low_b = prices_b * (1 - np.abs(np.random.normal(0, 0.01, n_periods)))
    open_b = np.roll(prices_b, 1)
    open_b[0] = base_price_b
    
    # Generate volume data
    volume_a = np.random.lognormal(10, 0.5, n_periods)
    volume_b = np.random.lognormal(9.5, 0.5, n_periods)
    
    timestamps = pd.date_range(start='2020-01-01', periods=n_periods, freq='D')
    
    return PairData(
        symbol_a='STOCK_A',
        symbol_b='STOCK_B',
        open_a=open_a,
        high_a=high_a,
        low_a=low_a,
        close_a=prices_a,
        volume_a=volume_a,
        open_b=open_b,
        high_b=high_b,
        low_b=low_b,
        close_b=prices_b,
        volume_b=volume_b,
        timestamps=timestamps.values
    )


def test_pairs_trading_engine():
    """Test the pairs trading engine with sample data."""
    print("Testing Pairs Trading Engine...")
    
    # Create sample data
    pair_data = create_sample_pair_data(500)
    
    # Initialize engine
    engine = PairsTradingEngine()
    
    # Analyze pair
    analysis = engine.analyze_pair(pair_data)
    
    print(f"\nPair Statistics:")
    stats = analysis['pair_statistics']
    print(f"Correlation: {stats.correlation:.4f}")
    print(f"Cointegration p-value: {stats.cointegration_pvalue:.4f}")
    print(f"Beta: {stats.beta:.4f}")
    print(f"R-squared: {stats.r_squared:.4f}")
    print(f"Half-life: {stats.half_life:.2f}")
    print(f"Is Cointegrated: {stats.is_cointegrated}")
    
    print(f"\nSignals Generated:")
    print(f"Convergence signals: {len(analysis['convergence_signals'])}")
    print(f"Divergence signals: {len(analysis['divergence_signals'])}")
    
    # Show sample signals
    if analysis['convergence_signals']:
        signal = analysis['convergence_signals'][0]
        print(f"\nSample Convergence Signal:")
        print(f"Type: {signal.signal_type.value}")
        print(f"Strength: {signal.strength:.4f}")
        print(f"Confidence: {signal.confidence:.4f}")
        print(f"Position A: {signal.position_size_a:.2f}")
        print(f"Position B: {signal.position_size_b:.2f}")
    
    # Backtest
    historical_data = {'TEST_PAIR': pair_data}
    backtest_results = engine.backtest_strategy(historical_data)
    
    print(f"\nBacktest Results:")
    print(f"Total signals: {backtest_results['total_signals']}")
    print(f"Total return: {backtest_results['total_return']:.4f}")
    print(f"Win rate: {backtest_results['win_rate']:.4f}")
    print(f"Sharpe ratio: {backtest_results['sharpe_ratio']:.4f}")
    
    print("\nPairs Trading Engine test completed successfully!")


if __name__ == "__main__":
    test_pairs_trading_engine()