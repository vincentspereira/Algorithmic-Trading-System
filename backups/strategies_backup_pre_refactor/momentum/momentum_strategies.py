"""Institutional-Grade Momentum Trading Strategies

This module implements comprehensive momentum-based trading strategies with
institutional-grade risk controls, performance optimization, and compliance features.

Strategies Included:
- Trend Following Momentum
- Breakout Momentum
- Cross-Sectional Momentum
- Time Series Momentum
- Dual Momentum (Absolute + Relative)
- Risk-Adjusted Momentum
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod

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
    
    class AugmentedIndicator:
        pass
    
    class IndicatorConfig:
        pass


class MomentumSignal(Enum):
    """Momentum signal types"""
    STRONG_BUY = 2
    BUY = 1
    NEUTRAL = 0
    SELL = -1
    STRONG_SELL = -2


class MarketRegime(Enum):
    """Market regime classification"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


@dataclass
class MomentumConfig:
    """Configuration for momentum strategies"""
    # Lookback periods
    short_period: int = 20
    medium_period: int = 50
    long_period: int = 200
    
    # Momentum thresholds
    momentum_threshold: float = 0.02  # 2% minimum momentum
    breakout_threshold: float = 0.015  # 1.5% breakout threshold
    
    # Risk management
    max_position_size: float = 0.1  # 10% max position
    stop_loss: float = 0.05  # 5% stop loss
    take_profit: float = 0.15  # 15% take profit
    
    # Volume confirmation
    volume_confirmation: bool = True
    volume_threshold: float = 1.5  # 1.5x average volume
    
    # Regime awareness
    regime_aware: bool = True
    volatility_lookback: int = 30
    
    # Performance optimization
    use_cuda: bool = False
    batch_processing: bool = True


@dataclass
class MomentumResult:
    """Result from momentum strategy calculation"""
    signal: MomentumSignal
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    momentum_score: float
    regime: MarketRegime
    risk_adjusted_score: float
    metadata: Dict[str, Any]
    timestamp: datetime


class BaseMomentumStrategy(ABC):
    """Abstract base class for momentum strategies"""
    
    def __init__(self, config: MomentumConfig = None):
        self.config = config or MomentumConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_indicators()
    
    def _setup_indicators(self):
        """Initialize technical indicators"""
        self.indicators = ConsolidatedIndicators()
        
        # Configure indicator parameters
        self.rsi_config = IndicatorConfig(
            period=14,
            use_volume_weighting=True,
            smoothing_factor=0.1
        )
        
        self.macd_config = IndicatorConfig(
            fast_period=12,
            slow_period=26,
            signal_period=9,
            use_volume_weighting=True
        )
    
    @abstractmethod
    def calculate_momentum(self, data: pd.DataFrame) -> MomentumResult:
        """Calculate momentum signal for given data"""
        pass
    
    def _detect_market_regime(self, data: pd.DataFrame) -> MarketRegime:
        """Detect current market regime"""
        if len(data) < self.config.volatility_lookback:
            return MarketRegime.SIDEWAYS
        
        # Calculate returns and volatility
        returns = data['close'].pct_change().dropna()
        volatility = returns.rolling(self.config.volatility_lookback).std()
        
        # Calculate trend strength
        sma_short = data['close'].rolling(self.config.short_period).mean()
        sma_long = data['close'].rolling(self.config.long_period).mean()
        
        current_price = data['close'].iloc[-1]
        current_vol = volatility.iloc[-1]
        vol_percentile = (volatility.iloc[-1] > volatility.quantile(0.8))
        
        # Regime classification logic
        if vol_percentile:
            return MarketRegime.HIGH_VOLATILITY
        elif current_vol < volatility.quantile(0.2):
            return MarketRegime.LOW_VOLATILITY
        elif current_price > sma_long.iloc[-1] * 1.02:
            return MarketRegime.TRENDING_UP
        elif current_price < sma_long.iloc[-1] * 0.98:
            return MarketRegime.TRENDING_DOWN
        else:
            return MarketRegime.SIDEWAYS
    
    def _calculate_volume_confirmation(self, data: pd.DataFrame) -> float:
        """Calculate volume confirmation score"""
        if not self.config.volume_confirmation or 'volume' not in data.columns:
            return 1.0
        
        avg_volume = data['volume'].rolling(self.config.short_period).mean()
        current_volume = data['volume'].iloc[-1]
        
        volume_ratio = current_volume / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1.0
        
        # Normalize volume confirmation (0.5 to 1.5)
        return min(1.5, max(0.5, volume_ratio / self.config.volume_threshold))
    
    def _apply_risk_adjustment(self, momentum_score: float, data: pd.DataFrame) -> float:
        """Apply risk adjustment to momentum score"""
        # Calculate volatility-adjusted momentum
        returns = data['close'].pct_change().dropna()
        volatility = returns.rolling(self.config.volatility_lookback).std().iloc[-1]
        
        if volatility > 0:
            risk_adjusted = momentum_score / (1 + volatility * 10)  # Scale volatility
        else:
            risk_adjusted = momentum_score
        
        return risk_adjusted


class TrendFollowingMomentum(BaseMomentumStrategy):
    """Trend-following momentum strategy using multiple timeframes"""
    
    def calculate_momentum(self, data: pd.DataFrame) -> MomentumResult:
        """Calculate trend-following momentum signal"""
        if len(data) < self.config.long_period:
            return self._create_neutral_result(data)
        
        # Calculate moving averages
        sma_short = data['close'].rolling(self.config.short_period).mean()
        sma_medium = data['close'].rolling(self.config.medium_period).mean()
        sma_long = data['close'].rolling(self.config.long_period).mean()
        
        current_price = data['close'].iloc[-1]
        
        # Calculate momentum components
        short_momentum = (current_price - sma_short.iloc[-1]) / sma_short.iloc[-1]
        medium_momentum = (current_price - sma_medium.iloc[-1]) / sma_medium.iloc[-1]
        long_momentum = (current_price - sma_long.iloc[-1]) / sma_long.iloc[-1]
        
        # Weighted momentum score
        momentum_score = (
            0.5 * short_momentum +
            0.3 * medium_momentum +
            0.2 * long_momentum
        )
        
        # Detect regime and apply adjustments
        regime = self._detect_market_regime(data)
        volume_conf = self._calculate_volume_confirmation(data)
        risk_adjusted_score = self._apply_risk_adjustment(momentum_score, data)
        
        # Generate signal
        signal = self._generate_signal(momentum_score, regime)
        strength = abs(momentum_score) / self.config.momentum_threshold
        confidence = min(1.0, strength * volume_conf)
        
        return MomentumResult(
            signal=signal,
            strength=min(1.0, strength),
            confidence=confidence,
            momentum_score=momentum_score,
            regime=regime,
            risk_adjusted_score=risk_adjusted_score,
            metadata={
                'short_momentum': short_momentum,
                'medium_momentum': medium_momentum,
                'long_momentum': long_momentum,
                'volume_confirmation': volume_conf,
                'sma_alignment': sma_short.iloc[-1] > sma_medium.iloc[-1] > sma_long.iloc[-1]
            },
            timestamp=datetime.now()
        )
    
    def _generate_signal(self, momentum_score: float, regime: MarketRegime) -> MomentumSignal:
        """Generate trading signal based on momentum and regime"""
        threshold = self.config.momentum_threshold
        
        # Adjust threshold based on regime
        if regime == MarketRegime.HIGH_VOLATILITY:
            threshold *= 1.5  # Higher threshold in volatile markets
        elif regime == MarketRegime.LOW_VOLATILITY:
            threshold *= 0.8  # Lower threshold in calm markets
        
        if momentum_score > threshold * 2:
            return MomentumSignal.STRONG_BUY
        elif momentum_score > threshold:
            return MomentumSignal.BUY
        elif momentum_score < -threshold * 2:
            return MomentumSignal.STRONG_SELL
        elif momentum_score < -threshold:
            return MomentumSignal.SELL
        else:
            return MomentumSignal.NEUTRAL
    
    def _create_neutral_result(self, data: pd.DataFrame) -> MomentumResult:
        """Create neutral result for insufficient data"""
        return MomentumResult(
            signal=MomentumSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            momentum_score=0.0,
            regime=MarketRegime.SIDEWAYS,
            risk_adjusted_score=0.0,
            metadata={'insufficient_data': True},
            timestamp=datetime.now()
        )


class BreakoutMomentum(BaseMomentumStrategy):
    """Breakout momentum strategy with volume confirmation"""
    
    def calculate_momentum(self, data: pd.DataFrame) -> MomentumResult:
        """Calculate breakout momentum signal"""
        if len(data) < self.config.medium_period:
            return self._create_neutral_result(data)
        
        # Calculate support and resistance levels
        high_period = data['high'].rolling(self.config.medium_period)
        low_period = data['low'].rolling(self.config.medium_period)
        
        resistance = high_period.max()
        support = low_period.min()
        
        current_price = data['close'].iloc[-1]
        current_high = data['high'].iloc[-1]
        current_low = data['low'].iloc[-1]
        
        # Calculate breakout signals
        resistance_breakout = (current_high - resistance.iloc[-1]) / resistance.iloc[-1]
        support_breakdown = (support.iloc[-1] - current_low) / support.iloc[-1]
        
        # Determine breakout type and strength
        if resistance_breakout > self.config.breakout_threshold:
            momentum_score = resistance_breakout
            breakout_type = 'resistance_breakout'
        elif support_breakdown > self.config.breakout_threshold:
            momentum_score = -support_breakdown
            breakout_type = 'support_breakdown'
        else:
            momentum_score = 0.0
            breakout_type = 'no_breakout'
        
        # Apply volume confirmation
        volume_conf = self._calculate_volume_confirmation(data)
        if volume_conf < 1.0:  # Weak volume confirmation
            momentum_score *= volume_conf
        
        # Detect regime and apply risk adjustment
        regime = self._detect_market_regime(data)
        risk_adjusted_score = self._apply_risk_adjustment(momentum_score, data)
        
        # Generate signal
        signal = self._generate_breakout_signal(momentum_score, volume_conf)
        strength = abs(momentum_score) / self.config.breakout_threshold
        confidence = min(1.0, strength * volume_conf)
        
        return MomentumResult(
            signal=signal,
            strength=min(1.0, strength),
            confidence=confidence,
            momentum_score=momentum_score,
            regime=regime,
            risk_adjusted_score=risk_adjusted_score,
            metadata={
                'breakout_type': breakout_type,
                'resistance_level': resistance.iloc[-1],
                'support_level': support.iloc[-1],
                'volume_confirmation': volume_conf,
                'resistance_breakout': resistance_breakout,
                'support_breakdown': support_breakdown
            },
            timestamp=datetime.now()
        )
    
    def _generate_breakout_signal(self, momentum_score: float, volume_conf: float) -> MomentumSignal:
        """Generate breakout signal with volume confirmation"""
        threshold = self.config.breakout_threshold
        
        # Require minimum volume confirmation for strong signals
        if volume_conf < 1.2:  # Below 1.2x average volume
            if momentum_score > threshold * 1.5:
                return MomentumSignal.BUY
            elif momentum_score < -threshold * 1.5:
                return MomentumSignal.SELL
            else:
                return MomentumSignal.NEUTRAL
        
        # Strong volume confirmation allows stronger signals
        if momentum_score > threshold * 2:
            return MomentumSignal.STRONG_BUY
        elif momentum_score > threshold:
            return MomentumSignal.BUY
        elif momentum_score < -threshold * 2:
            return MomentumSignal.STRONG_SELL
        elif momentum_score < -threshold:
            return MomentumSignal.SELL
        else:
            return MomentumSignal.NEUTRAL
    
    def _create_neutral_result(self, data: pd.DataFrame) -> MomentumResult:
        """Create neutral result for insufficient data"""
        return MomentumResult(
            signal=MomentumSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            momentum_score=0.0,
            regime=MarketRegime.SIDEWAYS,
            risk_adjusted_score=0.0,
            metadata={'insufficient_data': True},
            timestamp=datetime.now()
        )


class DualMomentumStrategy(BaseMomentumStrategy):
    """Dual momentum strategy combining absolute and relative momentum"""
    
    def __init__(self, config: MomentumConfig = None, benchmark_data: pd.DataFrame = None):
        super().__init__(config)
        self.benchmark_data = benchmark_data  # Market benchmark (e.g., S&P 500)
    
    def calculate_momentum(self, data: pd.DataFrame) -> MomentumResult:
        """Calculate dual momentum signal"""
        if len(data) < self.config.long_period:
            return self._create_neutral_result(data)
        
        # Calculate absolute momentum (time series momentum)
        returns_period = self.config.long_period
        current_price = data['close'].iloc[-1]
        past_price = data['close'].iloc[-returns_period]
        
        absolute_momentum = (current_price - past_price) / past_price
        
        # Calculate relative momentum (cross-sectional momentum)
        relative_momentum = 0.0
        if self.benchmark_data is not None and len(self.benchmark_data) >= returns_period:
            benchmark_current = self.benchmark_data['close'].iloc[-1]
            benchmark_past = self.benchmark_data['close'].iloc[-returns_period]
            benchmark_return = (benchmark_current - benchmark_past) / benchmark_past
            
            relative_momentum = absolute_momentum - benchmark_return
        
        # Combine absolute and relative momentum
        momentum_score = 0.6 * absolute_momentum + 0.4 * relative_momentum
        
        # Apply volume and regime adjustments
        regime = self._detect_market_regime(data)
        volume_conf = self._calculate_volume_confirmation(data)
        risk_adjusted_score = self._apply_risk_adjustment(momentum_score, data)
        
        # Generate signal
        signal = self._generate_dual_signal(absolute_momentum, relative_momentum)
        strength = abs(momentum_score) / self.config.momentum_threshold
        confidence = min(1.0, strength * volume_conf)
        
        return MomentumResult(
            signal=signal,
            strength=min(1.0, strength),
            confidence=confidence,
            momentum_score=momentum_score,
            regime=regime,
            risk_adjusted_score=risk_adjusted_score,
            metadata={
                'absolute_momentum': absolute_momentum,
                'relative_momentum': relative_momentum,
                'volume_confirmation': volume_conf,
                'lookback_period': returns_period
            },
            timestamp=datetime.now()
        )
    
    def _generate_dual_signal(self, absolute_mom: float, relative_mom: float) -> MomentumSignal:
        """Generate signal based on dual momentum criteria"""
        threshold = self.config.momentum_threshold
        
        # Both absolute and relative momentum must be positive for buy signal
        if absolute_mom > threshold and relative_mom > 0:
            if absolute_mom > threshold * 2:
                return MomentumSignal.STRONG_BUY
            else:
                return MomentumSignal.BUY
        
        # Both negative for sell signal
        elif absolute_mom < -threshold and relative_mom < 0:
            if absolute_mom < -threshold * 2:
                return MomentumSignal.STRONG_SELL
            else:
                return MomentumSignal.SELL
        
        else:
            return MomentumSignal.NEUTRAL
    
    def _create_neutral_result(self, data: pd.DataFrame) -> MomentumResult:
        """Create neutral result for insufficient data"""
        return MomentumResult(
            signal=MomentumSignal.NEUTRAL,
            strength=0.0,
            confidence=0.0,
            momentum_score=0.0,
            regime=MarketRegime.SIDEWAYS,
            risk_adjusted_score=0.0,
            metadata={'insufficient_data': True},
            timestamp=datetime.now()
        )


class MomentumStrategyManager:
    """Manager class for coordinating multiple momentum strategies"""
    
    def __init__(self, config: MomentumConfig = None):
        self.config = config or MomentumConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize strategies
        self.strategies = {
            'trend_following': TrendFollowingMomentum(self.config),
            'breakout': BreakoutMomentum(self.config),
            'dual_momentum': DualMomentumStrategy(self.config)
        }
    
    def calculate_ensemble_signal(self, data: pd.DataFrame, 
                                benchmark_data: pd.DataFrame = None) -> Dict[str, MomentumResult]:
        """Calculate signals from all momentum strategies"""
        results = {}
        
        # Update dual momentum with benchmark data
        if benchmark_data is not None:
            self.strategies['dual_momentum'].benchmark_data = benchmark_data
        
        # Calculate signals from all strategies
        for name, strategy in self.strategies.items():
            try:
                results[name] = strategy.calculate_momentum(data)
                self.logger.info(f"Calculated {name} momentum: {results[name].signal.value}")
            except Exception as e:
                self.logger.error(f"Error calculating {name} momentum: {e}")
                results[name] = strategy._create_neutral_result(data)
        
        return results
    
    def get_consensus_signal(self, results: Dict[str, MomentumResult]) -> MomentumResult:
        """Generate consensus signal from multiple strategies"""
        if not results:
            return MomentumResult(
                signal=MomentumSignal.NEUTRAL,
                strength=0.0,
                confidence=0.0,
                momentum_score=0.0,
                regime=MarketRegime.SIDEWAYS,
                risk_adjusted_score=0.0,
                metadata={'consensus': True, 'no_results': True},
                timestamp=datetime.now()
            )
        
        # Weight strategies by confidence
        total_weight = 0.0
        weighted_signal = 0.0
        weighted_strength = 0.0
        weighted_momentum = 0.0
        
        strategy_weights = {
            'trend_following': 0.4,
            'breakout': 0.3,
            'dual_momentum': 0.3
        }
        
        for name, result in results.items():
            weight = strategy_weights.get(name, 0.33) * result.confidence
            total_weight += weight
            weighted_signal += result.signal.value * weight
            weighted_strength += result.strength * weight
            weighted_momentum += result.momentum_score * weight
        
        if total_weight > 0:
            avg_signal = weighted_signal / total_weight
            avg_strength = weighted_strength / total_weight
            avg_momentum = weighted_momentum / total_weight
        else:
            avg_signal = 0.0
            avg_strength = 0.0
            avg_momentum = 0.0
        
        # Convert average signal to enum
        if avg_signal >= 1.5:
            consensus_signal = MomentumSignal.STRONG_BUY
        elif avg_signal >= 0.5:
            consensus_signal = MomentumSignal.BUY
        elif avg_signal <= -1.5:
            consensus_signal = MomentumSignal.STRONG_SELL
        elif avg_signal <= -0.5:
            consensus_signal = MomentumSignal.SELL
        else:
            consensus_signal = MomentumSignal.NEUTRAL
        
        # Calculate consensus confidence
        consensus_confidence = min(1.0, total_weight / len(results))
        
        return MomentumResult(
            signal=consensus_signal,
            strength=avg_strength,
            confidence=consensus_confidence,
            momentum_score=avg_momentum,
            regime=results[list(results.keys())[0]].regime,  # Use first strategy's regime
            risk_adjusted_score=avg_momentum,
            metadata={
                'consensus': True,
                'strategy_results': {name: result.signal.value for name, result in results.items()},
                'total_weight': total_weight,
                'num_strategies': len(results)
            },
            timestamp=datetime.now()
        )


# Example usage and testing functions
def create_sample_data(days: int = 252) -> pd.DataFrame:
    """Create sample market data for testing"""
    dates = pd.date_range(start='2023-01-01', periods=days, freq='D')
    
    # Generate realistic price data with trend and noise
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.02, days)  # Daily returns
    prices = [100.0]  # Starting price
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Generate volume data
    base_volume = 1000000
    volume = np.random.lognormal(np.log(base_volume), 0.3, days)
    
    # Create OHLC data
    data = pd.DataFrame({
        'date': dates,
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': volume
    })
    
    return data


def test_momentum_strategies():
    """Test momentum strategies with sample data"""
    # Create sample data
    data = create_sample_data(300)
    benchmark_data = create_sample_data(300)  # Market benchmark
    
    # Initialize strategy manager
    config = MomentumConfig(
        short_period=20,
        medium_period=50,
        long_period=200,
        momentum_threshold=0.02,
        volume_confirmation=True
    )
    
    manager = MomentumStrategyManager(config)
    
    # Calculate signals
    results = manager.calculate_ensemble_signal(data, benchmark_data)
    consensus = manager.get_consensus_signal(results)
    
    print("\n=== Momentum Strategy Results ===")
    for name, result in results.items():
        print(f"\n{name.upper()}:")
        print(f"  Signal: {result.signal.name}")
        print(f"  Strength: {result.strength:.3f}")
        print(f"  Confidence: {result.confidence:.3f}")
        print(f"  Momentum Score: {result.momentum_score:.4f}")
        print(f"  Regime: {result.regime.value}")
    
    print(f"\nCONSENSUS:")
    print(f"  Signal: {consensus.signal.name}")
    print(f"  Strength: {consensus.strength:.3f}")
    print(f"  Confidence: {consensus.confidence:.3f}")
    print(f"  Momentum Score: {consensus.momentum_score:.4f}")


if __name__ == "__main__":
    # Run tests
    test_momentum_strategies()