"""Institutional-Grade Mean Reversion Trading Strategies

This module implements comprehensive mean reversion strategies with
institutional-grade risk controls, statistical validation, and performance optimization.

Strategies Included:
- Statistical Arbitrage
- Bollinger Band Reversion
- RSI Mean Reversion
- Z-Score Reversion
- Ornstein-Uhlenbeck Process
- Cointegration-Based Reversion
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod
from scipy import stats
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

# Import technical indicators
try:
    from ...indicators.consolidated_indicators import ConsolidatedIndicators, IndicatorResult
    from ...indicators.core.core_indicator_base import AugmentedIndicator, IndicatorConfig
except ImportError:
    # Fallback for development
    class ConsolidatedIndicators:
        @staticmethod
        def rsi(*args, **kwargs):
            return None
        
        @staticmethod
        def bollinger_bands(*args, **kwargs):
            return None
    
    class AugmentedIndicator:
        pass
    
    class IndicatorConfig:
        pass


class ReversionSignal(Enum):
    """Mean reversion signal types"""
    STRONG_BUY = 2
    BUY = 1
    NEUTRAL = 0
    SELL = -1
    STRONG_SELL = -2


class ReversionRegime(Enum):
    """Market regime for mean reversion"""
    MEAN_REVERTING = "mean_reverting"
    TRENDING = "trending"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RANGE_BOUND = "range_bound"


@dataclass
class ReversionConfig:
    """Configuration for mean reversion strategies"""
    # Statistical parameters
    lookback_period: int = 50
    z_score_threshold: float = 2.0
    half_life_threshold: int = 20  # Maximum half-life for mean reversion
    
    # Bollinger Band parameters
    bb_period: int = 20
    bb_std_dev: float = 2.0
    bb_reversion_threshold: float = 0.8  # How close to bands for signal
    
    # RSI parameters
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    
    # Risk management
    max_position_size: float = 0.05  # 5% max position
    stop_loss: float = 0.03  # 3% stop loss
    take_profit: float = 0.02  # 2% take profit (smaller for mean reversion)
    
    # Statistical validation
    min_observations: int = 100
    confidence_level: float = 0.95
    stationarity_test: bool = True
    
    # Performance optimization
    use_cuda: bool = False
    batch_processing: bool = True


@dataclass
class ReversionResult:
    """Result from mean reversion strategy calculation"""
    signal: ReversionSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    z_score: float
    mean_level: float
    current_deviation: float
    regime: ReversionRegime
    half_life: Optional[float]  # Expected time to revert
    statistical_significance: float
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseMeanReversionStrategy(ABC):
    """Abstract base class for mean reversion strategies"""
    
    def __init__(self, config: ReversionConfig = None):
        self.config = config or ReversionConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_indicators()
    
    def _setup_indicators(self):
        """Initialize technical indicators"""
        self.indicators = ConsolidatedIndicators()
        
        # Configure indicator parameters
        self.rsi_config = IndicatorConfig(
            period=self.config.rsi_period,
            use_volume_weighting=True,
            smoothing_factor=0.1
        )
        
        self.bb_config = IndicatorConfig(
            period=self.config.bb_period,
            std_dev=self.config.bb_std_dev,
            use_volume_weighting=True
        )
    
    @abstractmethod
    def calculate_reversion(self, data: pd.DataFrame) -> ReversionResult:
        """Calculate mean reversion signal for given data"""
        pass
    
    def _calculate_z_score(self, data: pd.Series, window: int = None) -> Tuple[float, float, float]:
        """Calculate z-score for mean reversion analysis"""
        window = window or self.config.lookback_period
        
        if len(data) < window:
            return 0.0, data.mean(), 0.0
        
        rolling_mean = data.rolling(window).mean()
        rolling_std = data.rolling(window).std()
        
        current_value = data.iloc[-1]
        mean_level = rolling_mean.iloc[-1]
        std_level = rolling_std.iloc[-1]
        
        if std_level > 0:
            z_score = (current_value - mean_level) / std_level
        else:
            z_score = 0.0
        
        return z_score, mean_level, current_value - mean_level
    
    def _calculate_half_life(self, data: pd.Series) -> Optional[float]:
        """Calculate half-life of mean reversion using Ornstein-Uhlenbeck process"""
        if len(data) < self.config.min_observations:
            return None
        
        try:
            # Calculate price differences
            y = data.diff().dropna()
            x = data.shift(1).dropna()
            
            # Align series
            min_len = min(len(x), len(y))
            x = x.iloc[-min_len:]
            y = y.iloc[-min_len:]
            
            # Fit AR(1) model: dy = alpha + beta * y_{t-1} + epsilon
            X = np.column_stack([np.ones(len(x)), x.values])
            coeffs = np.linalg.lstsq(X, y.values, rcond=None)[0]
            
            beta = coeffs[1]
            
            # Half-life calculation
            if beta < 0:
                half_life = -np.log(2) / beta
                return half_life if half_life > 0 else None
            else:
                return None  # No mean reversion
                
        except Exception as e:
            self.logger.warning(f"Error calculating half-life: {e}")
            return None
    
    def _test_stationarity(self, data: pd.Series) -> Tuple[bool, float]:
        """Test for stationarity using Augmented Dickey-Fuller test"""
        try:
            from statsmodels.tsa.stattools import adfuller
            
            result = adfuller(data.dropna())
            p_value = result[1]
            is_stationary = p_value < (1 - self.config.confidence_level)
            
            return is_stationary, p_value
            
        except ImportError:
            # Fallback: simple variance test
            rolling_var = data.rolling(self.config.lookback_period).var()
            var_stability = rolling_var.std() / rolling_var.mean() if rolling_var.mean() > 0 else float('inf')
            is_stationary = var_stability < 0.5  # Heuristic threshold
            
            return is_stationary, var_stability
        except Exception as e:
            self.logger.warning(f"Error in stationarity test: {e}")
            return False, 1.0
    
    def _detect_reversion_regime(self, data: pd.DataFrame) -> ReversionRegime:
        """Detect market regime for mean reversion"""
        if len(data) < self.config.lookback_period:
            return ReversionRegime.RANGE_BOUND
        
        # Calculate returns and volatility
        returns = data['close'].pct_change().dropna()
        volatility = returns.rolling(self.config.lookback_period).std()
        
        # Test for mean reversion vs trending
        half_life = self._calculate_half_life(data['close'])
        is_stationary, _ = self._test_stationarity(data['close'])
        
        # Calculate trend strength
        sma_short = data['close'].rolling(10).mean()
        sma_long = data['close'].rolling(self.config.lookback_period).mean()
        trend_strength = abs((sma_short.iloc[-1] - sma_long.iloc[-1]) / sma_long.iloc[-1])
        
        current_vol = volatility.iloc[-1]
        vol_percentile = (current_vol > volatility.quantile(0.8))
        
        # Regime classification
        if vol_percentile:
            return ReversionRegime.HIGH_VOLATILITY
        elif current_vol < volatility.quantile(0.2):
            return ReversionRegime.LOW_VOLATILITY
        elif trend_strength > 0.05:  # Strong trend
            return ReversionRegime.TRENDING
        elif is_stationary and half_life and half_life < self.config.half_life_threshold:
            return ReversionRegime.MEAN_REVERTING
        else:
            return ReversionRegime.RANGE_BOUND
    
    def _calculate_statistical_significance(self, z_score: float, n_observations: int) -> float:
        """Calculate statistical significance of mean reversion signal"""
        if n_observations < self.config.min_observations:
            return 0.0
        
        # Two-tailed t-test for significance
        t_stat = abs(z_score) * np.sqrt(n_observations - 1)
        p_value = 2 * (1 - stats.t.cdf(t_stat, n_observations - 2))
        
        return 1 - p_value  # Convert to confidence score


class StatisticalArbitrageStrategy(BaseMeanReversionStrategy):
    """Statistical arbitrage strategy using z-score analysis"""
    
    def calculate_reversion(self, data: pd.DataFrame) -> ReversionResult:
        """Calculate statistical arbitrage signal"""
        if len(data) < self.config.lookback_period:
            return self._create_neutral_result(data)
        
        # Calculate z-score for price series
        z_score, mean_level, deviation = self._calculate_z_score(
            data['close'], self.config.lookback_period
        )
        
        # Calculate half-life and statistical tests
        half_life = self._calculate_half_life(data['close'])
        is_stationary, stationarity_p = self._test_stationarity(data['close'])
        
        # Detect regime
        regime = self._detect_reversion_regime(data)
        
        # Calculate statistical significance
        significance = self._calculate_statistical_significance(
            z_score, len(data)
        )
        
        # Generate signal based on z-score and regime
        signal = self._generate_statistical_signal(z_score, regime, is_stationary)
        
        # Calculate strength and confidence
        strength = min(1.0, abs(z_score) / self.config.z_score_threshold)
        confidence = significance * (0.8 if is_stationary else 0.4)
        
        # Adjust confidence based on half-life
        if half_life and half_life < self.config.half_life_threshold:
            confidence *= 1.2  # Boost confidence for fast mean reversion
        elif half_life and half_life > self.config.half_life_threshold * 2:
            confidence *= 0.6  # Reduce confidence for slow mean reversion
        
        confidence = min(1.0, confidence)
        
        return ReversionResult(
            signal=signal,
            strength=strength,
            confidence=confidence,
            z_score=z_score,
            mean_level=mean_level,
            current_deviation=deviation,
            regime=regime,
            half_life=half_life,
            statistical_significance=significance,
            metadata={
                'is_stationary': is_stationary,
                'stationarity_p_value': stationarity_p,
                'lookback_period': self.config.lookback_period,
                'threshold_used': self.config.z_score_threshold
            },
            timestamp=datetime.now()
        )
    
    def _generate_statistical_signal(self, z_score: float, regime: ReversionRegime, 
                                   is_stationary: bool) -> ReversionSignal:
        """Generate signal based on statistical analysis"""
        threshold = self.config.z_score_threshold
        
        # Only trade in mean-reverting regimes
        if regime == ReversionRegime.TRENDING:
            return ReversionSignal.NEUTRAL
        
        # Require stationarity for strong signals
        if not is_stationary:
            threshold *= 1.5  # Higher threshold for non-stationary series
        
        # Adjust threshold based on regime
        if regime == ReversionRegime.HIGH_VOLATILITY:
            threshold *= 1.3  # Higher threshold in volatile markets
        elif regime == ReversionRegime.LOW_VOLATILITY:
            threshold *= 0.8  # Lower threshold in calm markets
        
        # Generate signals (reversed logic for mean reversion)
        if z_score > threshold * 1.5:  # Extremely overbought
            return ReversionSignal.STRONG_SELL
        elif z_score > threshold:  # Overbought
            return ReversionSignal.SELL
        elif z_score < -threshold * 1.5:  # Extremely oversold
            return ReversionSignal.STRONG_BUY
        elif z_score < -threshold:  # Oversold
            return ReversionSignal.BUY
        else:
            return ReversionSignal.NEUTRAL
    
    def _create_neutral_result(self, data: pd.DataFrame) -> ReversionResult:
        """Create neutral result for insufficient data"""
        return ReversionResult(
            signal=ReversionSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            z_score=0.0,
            mean_level=0.0,
            current_deviation=0.0,
            regime=ReversionRegime.RANGE_BOUND,
            half_life=None,
            statistical_significance=0.0,
            metadata={'insufficient_data': True},
            timestamp=datetime.now()
        )


class BollingerBandReversionStrategy(BaseMeanReversionStrategy):
    """Bollinger Band mean reversion strategy"""
    
    def calculate_reversion(self, data: pd.DataFrame) -> ReversionResult:
        """Calculate Bollinger Band reversion signal"""
        if len(data) < self.config.bb_period:
            return self._create_neutral_result(data)
        
        # Calculate Bollinger Bands
        close_prices = data['close']
        sma = close_prices.rolling(self.config.bb_period).mean()
        std = close_prices.rolling(self.config.bb_period).std()
        
        upper_band = sma + (self.config.bb_std_dev * std)
        lower_band = sma - (self.config.bb_std_dev * std)
        
        current_price = close_prices.iloc[-1]
        current_sma = sma.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        
        # Calculate position within bands
        band_width = current_upper - current_lower
        if band_width > 0:
            band_position = (current_price - current_lower) / band_width
        else:
            band_position = 0.5  # Middle of bands
        
        # Calculate z-score equivalent
        if std.iloc[-1] > 0:
            z_score = (current_price - current_sma) / std.iloc[-1]
        else:
            z_score = 0.0
        
        # Calculate deviation from mean
        deviation = current_price - current_sma
        
        # Detect regime and calculate half-life
        regime = self._detect_reversion_regime(data)
        half_life = self._calculate_half_life(close_prices)
        
        # Calculate statistical significance
        significance = self._calculate_statistical_significance(z_score, len(data))
        
        # Generate signal
        signal = self._generate_bb_signal(band_position, z_score, regime)
        
        # Calculate strength based on distance from bands
        if band_position > 0.5:
            strength = min(1.0, (band_position - 0.5) * 2 / self.config.bb_reversion_threshold)
        else:
            strength = min(1.0, (0.5 - band_position) * 2 / self.config.bb_reversion_threshold)
        
        # Calculate confidence
        confidence = significance * min(1.0, strength * 1.5)
        
        return ReversionResult(
            signal=signal,
            strength=strength,
            confidence=confidence,
            z_score=z_score,
            mean_level=current_sma,
            current_deviation=deviation,
            regime=regime,
            half_life=half_life,
            statistical_significance=significance,
            metadata={
                'band_position': band_position,
                'upper_band': current_upper,
                'lower_band': current_lower,
                'band_width': band_width,
                'bb_period': self.config.bb_period,
                'std_dev_multiplier': self.config.bb_std_dev
            },
            timestamp=datetime.now()
        )
    
    def _generate_bb_signal(self, band_position: float, z_score: float, 
                           regime: ReversionRegime) -> ReversionSignal:
        """Generate signal based on Bollinger Band position"""
        threshold = self.config.bb_reversion_threshold
        
        # Don't trade against strong trends
        if regime == ReversionRegime.TRENDING:
            return ReversionSignal.NEUTRAL
        
        # Adjust threshold based on regime
        if regime == ReversionRegime.HIGH_VOLATILITY:
            threshold *= 0.9  # Easier to trigger in volatile markets
        elif regime == ReversionRegime.LOW_VOLATILITY:
            threshold *= 1.1  # Harder to trigger in calm markets
        
        # Generate signals based on band position (reversed for mean reversion)
        if band_position > (1 - threshold):  # Near upper band
            if abs(z_score) > 2.5:
                return ReversionSignal.STRONG_SELL
            else:
                return ReversionSignal.SELL
        elif band_position < threshold:  # Near lower band
            if abs(z_score) > 2.5:
                return ReversionSignal.STRONG_BUY
            else:
                return ReversionSignal.BUY
        else:
            return ReversionSignal.NEUTRAL
    
    def _create_neutral_result(self, data: pd.DataFrame) -> ReversionResult:
        """Create neutral result for insufficient data"""
        return ReversionResult(
            signal=ReversionSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            z_score=0.0,
            mean_level=0.0,
            current_deviation=0.0,
            regime=ReversionRegime.RANGE_BOUND,
            half_life=None,
            statistical_significance=0.0,
            metadata={'insufficient_data': True},
            timestamp=datetime.now()
        )


class RSIMeanReversionStrategy(BaseMeanReversionStrategy):
    """RSI-based mean reversion strategy"""
    
    def calculate_reversion(self, data: pd.DataFrame) -> ReversionResult:
        """Calculate RSI mean reversion signal"""
        if len(data) < self.config.rsi_period + 1:
            return self._create_neutral_result(data)
        
        # Calculate RSI
        close_prices = data['close']
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Calculate z-score for price
        z_score, mean_level, deviation = self._calculate_z_score(
            close_prices, self.config.lookback_period
        )
        
        # Detect regime and calculate half-life
        regime = self._detect_reversion_regime(data)
        half_life = self._calculate_half_life(close_prices)
        
        # Calculate RSI-based z-score (normalized RSI)
        rsi_z_score = (current_rsi - 50) / 15  # Normalize RSI around 50
        
        # Calculate statistical significance
        significance = self._calculate_statistical_significance(rsi_z_score, len(data))
        
        # Generate signal
        signal = self._generate_rsi_signal(current_rsi, regime)
        
        # Calculate strength based on RSI extremes
        if current_rsi > 50:
            strength = min(1.0, (current_rsi - 50) / 30)  # 0 to 1 for RSI 50-80
        else:
            strength = min(1.0, (50 - current_rsi) / 30)  # 0 to 1 for RSI 20-50
        
        # Calculate confidence
        confidence = significance * strength
        
        return ReversionResult(
            signal=signal,
            strength=strength,
            confidence=confidence,
            z_score=rsi_z_score,
            mean_level=mean_level,
            current_deviation=deviation,
            regime=regime,
            half_life=half_life,
            statistical_significance=significance,
            metadata={
                'rsi_value': current_rsi,
                'rsi_period': self.config.rsi_period,
                'rsi_overbought': self.config.rsi_overbought,
                'rsi_oversold': self.config.rsi_oversold,
                'price_z_score': z_score
            },
            timestamp=datetime.now()
        )
    
    def _generate_rsi_signal(self, rsi: float, regime: ReversionRegime) -> ReversionSignal:
        """Generate signal based on RSI levels"""
        overbought = self.config.rsi_overbought
        oversold = self.config.rsi_oversold
        
        # Don't trade against strong trends
        if regime == ReversionRegime.TRENDING:
            return ReversionSignal.NEUTRAL
        
        # Adjust thresholds based on regime
        if regime == ReversionRegime.HIGH_VOLATILITY:
            overbought += 5  # 75 instead of 70
            oversold -= 5    # 25 instead of 30
        elif regime == ReversionRegime.LOW_VOLATILITY:
            overbought -= 5  # 65 instead of 70
            oversold += 5    # 35 instead of 30
        
        # Generate signals (reversed for mean reversion)
        if rsi > overbought + 10:  # Extremely overbought
            return ReversionSignal.STRONG_SELL
        elif rsi > overbought:  # Overbought
            return ReversionSignal.SELL
        elif rsi < oversold - 10:  # Extremely oversold
            return ReversionSignal.STRONG_BUY
        elif rsi < oversold:  # Oversold
            return ReversionSignal.BUY
        else:
            return ReversionSignal.NEUTRAL
    
    def _create_neutral_result(self, data: pd.DataFrame) -> ReversionResult:
        """Create neutral result for insufficient data"""
        return ReversionResult(
            signal=ReversionSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            z_score=0.0,
            mean_level=0.0,
            current_deviation=0.0,
            regime=ReversionRegime.RANGE_BOUND,
            half_life=None,
            statistical_significance=0.0,
            metadata={'insufficient_data': True},
            timestamp=datetime.now()
        )


class MeanReversionStrategyManager:
    """Manager class for coordinating multiple mean reversion strategies"""
    
    def __init__(self, config: ReversionConfig = None):
        self.config = config or ReversionConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.strategies = {
            'statistical_arbitrage': StatisticalArbitrageStrategy(self.config),
            'bollinger_reversion': BollingerBandReversionStrategy(self.config),
            'rsi_reversion': RSIMeanReversionStrategy(self.config)
        }
    
    def calculate_ensemble_signal(self, data: pd.DataFrame) -> Dict[str, ReversionResult]:
        """Calculate signals from all mean reversion strategies"""
        results = {}
        
        # Calculate signals from all strategies
        for name, strategy in self.strategies.items():
            try:
                results[name] = strategy.calculate_reversion(data)
                self.logger.info(f"Calculated {name} reversion: {results[name].signal.value}")
            except Exception as e:
                self.logger.error(f"Error calculating {name} reversion: {e}")
                results[name] = strategy._create_neutral_result(data)
        
        return results
    
    def get_consensus_signal(self, results: Dict[str, ReversionResult]) -> ReversionResult:
        """Generate consensus signal from multiple strategies"""
        if not results:
            return ReversionResult(
                signal=ReversionSignal.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                z_score=0.0,
                mean_level=0.0,
                current_deviation=0.0,
                regime=ReversionRegime.RANGE_BOUND,
                half_life=None,
                statistical_significance=0.0,
                metadata={'consensus': True, 'no_results': True},
                timestamp=datetime.now()
            )
        
        # Weight strategies by confidence and statistical significance
        total_weight = 0.0
        weighted_signal = 0.0
        weighted_strength = 0.0
        weighted_z_score = 0.0
        
        strategy_weights = {
            'statistical_arbitrage': 0.5,  # Highest weight for statistical approach
            'bollinger_reversion': 0.3,
            'rsi_reversion': 0.2
        }
        
        for name, result in results.items():
            base_weight = strategy_weights.get(name, 0.33)
            weight = base_weight * result.confidence * result.statistical_significance
            total_weight += weight
            weighted_signal += result.signal.value * weight
            weighted_strength += result.strength * weight
            weighted_z_score += result.z_score * weight
        
        if total_weight > 0:
            avg_signal = weighted_signal / total_weight
            avg_strength = weighted_strength / total_weight
            avg_z_score = weighted_z_score / total_weight
        else:
            avg_signal = 0.0
            avg_strength = 0.0
            avg_z_score = 0.0
        
        # Convert average signal to enum
        if avg_signal >= 1.5:
            consensus_signal = ReversionSignal.STRONG_BUY
        elif avg_signal >= 0.5:
            consensus_signal = ReversionSignal.BUY
        elif avg_signal <= -1.5:
            consensus_signal = ReversionSignal.STRONG_SELL
        elif avg_signal <= -0.5:
            consensus_signal = ReversionSignal.SELL
        else:
            consensus_signal = ReversionSignal.NEUTRAL
        
        # Calculate consensus confidence
        consensus_confidence = min(1.0, total_weight / len(results))
        
        # Use first strategy's regime and other metadata
        first_result = list(results.values())[0]
        
        return ReversionResult(
            signal=consensus_signal,
            strength=avg_strength,
            confidence=consensus_confidence,
            z_score=avg_z_score,
            mean_level=first_result.mean_level,
            current_deviation=first_result.current_deviation,
            regime=first_result.regime,
            half_life=first_result.half_life,
            statistical_significance=sum(r.statistical_significance for r in results.values()) / len(results),
            metadata={
                'consensus': True,
                'strategy_results': {name: result.signal.value for name, result in results.items()},
                'total_weight': total_weight,
                'num_strategies': len(results)
            },
            timestamp=datetime.now()
        )


# Example usage and testing functions
def create_mean_reverting_data(days: int = 252) -> pd.DataFrame:
    """Create sample mean-reverting data for testing"""
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # Generate mean-reverting price series using Ornstein-Uhlenbeck process
    np.random.seed(42)
    dt = 1.0  # Daily time step
    theta = 0.1  # Mean reversion speed
    mu = 100.0  # Long-term mean
    sigma = 2.0  # Volatility
    
    prices = [mu]
    for _ in range(days - 1):
        dx = theta * (mu - prices[-1]) * dt + sigma * np.sqrt(dt) * np.random.normal()
        prices.append(prices[-1] + dx)
    
    # Add some noise and ensure positive prices
    prices = np.array(prices)
    prices = np.maximum(prices, 50.0)  # Floor at 50
    
    # Generate volume data
    base_volume = 1000000
    volume = np.random.lognormal(np.log(base_volume), 0.2, days)
    
    # Create OHLC data
    data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
        'close': prices,
        'volume': volume
    })
    
    return data


def test_mean_reversion_strategies():
    """Test mean reversion strategies with sample data"""
    # Create sample mean-reverting data
    data = create_mean_reverting_data(300)
    
    # Initialize strategy manager
    config = ReversionConfig(
        lookback_period=50,
        z_score_threshold=2.0,
        bb_period=20,
        rsi_period=14,
        confidence_level=0.95
    )
    
    manager = MeanReversionStrategyManager(config)
    
    # Calculate signals
    results = manager.calculate_ensemble_signal(data)
    consensus = manager.get_consensus_signal(results)
    
    print("\n=== Mean Reversion Strategy Results ===")
    for name, result in results.items():
        print(f"\n{name.upper()}:")
        print(f"  Signal: {result.signal.name}")
        print(f"  Strength: {result.strength:.3f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Z-Score: {result.z_score:.3f}")
        print(f"  Regime: {result.regime.value}")
        print(f"  Half-Life: {result.half_life:.1f} days" if result.half_life else "  Half-Life: N/A")
        print(f"  Statistical Significance: {result.statistical_significance:.3f}")
    
    print(f"\nCONSENSUS:")
    print(f"  Signal: {consensus.signal.name}")
    print(f"  Strength: {consensus.strength:.3f}")
    print(f"  Confidence: {consensus.confidence:.3f}")
    print(f"  Z-Score: {consensus.z_score:.3f}")
    print(f"  Statistical Significance: {consensus.statistical_significance:.3f}")


if __name__ == "__main__":
    # Run tests
    test_mean_reversion_strategies()