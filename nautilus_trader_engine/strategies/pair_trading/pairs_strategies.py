#!/usr/bin/env python3
"""
Pairs Trading Strategies

Implements comprehensive pairs trading strategies including convergence (mean reversion)
and divergence (momentum) approaches with advanced statistical analysis and risk management.

Key Features:
- Convergence Strategy: Mean reversion on spread/ratio with statistical validation
- Divergence Strategy: Momentum breakout on spread/ratio with trend confirmation
- Multi-timeframe analysis and confirmation
- Dynamic position sizing and risk management
- Regime-aware strategy adaptation
- Advanced entry/exit logic with multiple confirmation signals
- Performance tracking and optimization
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Union, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta
import logging
from abc import ABC, abstractmethod

# Import our custom modules
from .pair_selection import PairSelector, PairMetrics
from .correlation_analysis import (
    CorrelationAnalyzer, CointegrationTester, SpreadAnalyzer,
    CorrelationResult, CointegrationResult, SpreadAnalysis
)
from .spread_indicators import (
    SpreadIndicatorSuite, SpreadSignal, RegimeType,
    ZScoreResult, BollingerBandsResult
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Types of pairs trading strategies."""
    CONVERGENCE = "convergence"
    DIVERGENCE = "divergence"
    HYBRID = "hybrid"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"


class PositionType(Enum):
    """Position types for pairs trading."""
    LONG_SPREAD = "long_spread"  # Long asset1, short asset2
    SHORT_SPREAD = "short_spread"  # Short asset1, long asset2
    FLAT = "flat"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    EXTREME = "extreme"


@dataclass
class TradingSignal:
    """Trading signal for pairs trading."""
    signal_type: StrategyType
    position_type: PositionType
    strength: SignalStrength
    confidence: float  # 0 to 1
    entry_price_1: float
    entry_price_2: float
    hedge_ratio: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: float = 1.0
    regime: RegimeType = RegimeType.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Position:
    """Active pairs trading position."""
    pair_id: str
    symbol1: str
    symbol2: str
    position_type: PositionType
    entry_time: datetime
    entry_price_1: float
    entry_price_2: float
    hedge_ratio: float
    quantity_1: float
    quantity_2: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    current_pnl: float = 0.0
    max_favorable: float = 0.0
    max_adverse: float = 0.0
    metadata: Dict = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """Configuration for pairs trading strategies."""
    # General parameters
    lookback_period: int = 60
    min_correlation: float = 0.7
    max_correlation: float = 0.95
    cointegration_pvalue: float = 0.05
    
    # Z-Score parameters
    zscore_entry_threshold: float = 2.0
    zscore_exit_threshold: float = 0.5
    zscore_stop_loss: float = 3.0
    
    # Bollinger Bands parameters
    bollinger_period: int = 20
    bollinger_std_dev: float = 2.0
    
    # Risk management
    max_position_size: float = 1.0
    max_portfolio_exposure: float = 0.2
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.03
    
    # Strategy-specific
    convergence_enabled: bool = True
    divergence_enabled: bool = False
    multi_timeframe: bool = True
    regime_filter: bool = True
    volume_confirmation: bool = True
    
    # Performance
    min_half_life: float = 5.0
    max_half_life: float = 30.0
    min_trades_per_year: int = 12
    target_sharpe_ratio: float = 1.5


class BasePairsStrategy(ABC):
    """Base class for pairs trading strategies."""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.pair_selector = PairSelector()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.cointegration_tester = CointegrationTester()
        self.spread_analyzer = SpreadAnalyzer()
        self.indicator_suite = SpreadIndicatorSuite(
            zscore_period=config.lookback_period,
            bollinger_period=config.bollinger_period
        )
        
        # Strategy state
        self.active_positions: Dict[str, Position] = {}
        self.performance_metrics: Dict = {}
        self.last_update: Optional[datetime] = None
    
    @abstractmethod
    def generate_signals(self, 
                        data1: pd.Series, 
                        data2: pd.Series,
                        volume1: Optional[pd.Series] = None,
                        volume2: Optional[pd.Series] = None) -> List[TradingSignal]:
        """Generate trading signals for the pair."""
        pass
    
    @abstractmethod
    def calculate_position_size(self, 
                              signal: TradingSignal,
                              portfolio_value: float,
                              current_exposure: float) -> Tuple[float, float]:
        """Calculate position sizes for both assets."""
        pass
    
    def validate_pair(self, 
                     data1: pd.Series, 
                     data2: pd.Series) -> Tuple[bool, Dict[str, float]]:
        """Validate if pair is suitable for trading.
        
        Args:
            data1: First asset price series
            data2: Second asset price series
            
        Returns:
            Tuple of (is_valid, validation_metrics)
        """
        try:
            # Align data
            aligned_data = pd.concat([data1, data2], axis=1).dropna()
            if len(aligned_data) < self.config.lookback_period:
                return False, {'error': 'insufficient_data'}
            
            series1 = aligned_data.iloc[:, 0]
            series2 = aligned_data.iloc[:, 1]
            
            # Correlation analysis
            corr_result = self.correlation_analyzer.calculate_correlation(series1, series2)
            
            # Cointegration test
            coint_result = self.cointegration_tester.engle_granger_test(series1, series2)
            
            # Spread analysis
            spread_result = self.spread_analyzer.analyze_spread(series1, series2)
            
            # Validation criteria
            validation_metrics = {
                'correlation': corr_result.correlation,
                'correlation_pvalue': corr_result.pvalue,
                'cointegration_pvalue': coint_result.pvalue,
                'is_cointegrated': coint_result.is_cointegrated,
                'spread_half_life': spread_result.half_life,
                'spread_stationarity': spread_result.stationarity_result.is_stationary,
                'hedge_ratio': coint_result.hedge_ratio or 1.0
            }
            
            # Check validation criteria
            is_valid = (
                abs(corr_result.correlation) >= self.config.min_correlation and
                abs(corr_result.correlation) <= self.config.max_correlation and
                corr_result.pvalue <= 0.05 and
                coint_result.is_cointegrated and
                coint_result.pvalue <= self.config.cointegration_pvalue and
                spread_result.stationarity_result.is_stationary and
                self.config.min_half_life <= spread_result.half_life <= self.config.max_half_life
            )
            
            return is_valid, validation_metrics
        
        except Exception as e:
            logger.warning(f"Error validating pair: {e}")
            return False, {'error': str(e)}
    
    def update_positions(self, 
                        current_prices: Dict[str, float],
                        timestamp: datetime) -> None:
        """Update active positions with current market data.
        
        Args:
            current_prices: Dictionary of current prices {symbol: price}
            timestamp: Current timestamp
        """
        try:
            for pair_id, position in self.active_positions.items():
                if position.symbol1 in current_prices and position.symbol2 in current_prices:
                    price1 = current_prices[position.symbol1]
                    price2 = current_prices[position.symbol2]
                    
                    # Calculate current P&L
                    if position.position_type == PositionType.LONG_SPREAD:
                        # Long asset1, short asset2
                        pnl1 = position.quantity_1 * (price1 - position.entry_price_1)
                        pnl2 = position.quantity_2 * (position.entry_price_2 - price2)
                    else:
                        # Short asset1, long asset2
                        pnl1 = position.quantity_1 * (position.entry_price_1 - price1)
                        pnl2 = position.quantity_2 * (price2 - position.entry_price_2)
                    
                    position.current_pnl = pnl1 + pnl2
                    
                    # Update max favorable/adverse
                    if position.current_pnl > position.max_favorable:
                        position.max_favorable = position.current_pnl
                    if position.current_pnl < position.max_adverse:
                        position.max_adverse = position.current_pnl
            
            self.last_update = timestamp
        
        except Exception as e:
            logger.warning(f"Error updating positions: {e}")
    
    def check_exit_conditions(self, 
                            data1: pd.Series, 
                            data2: pd.Series,
                            volume1: Optional[pd.Series] = None,
                            volume2: Optional[pd.Series] = None) -> List[str]:
        """Check exit conditions for active positions.
        
        Args:
            data1: First asset price series
            data2: Second asset price series
            volume1: Optional volume series for first asset
            volume2: Optional volume series for second asset
            
        Returns:
            List of pair IDs that should be closed
        """
        try:
            positions_to_close = []
            
            if not self.active_positions:
                return positions_to_close
            
            # Calculate current spread and indicators
            aligned_data = pd.concat([data1, data2], axis=1).dropna()
            if len(aligned_data) < 10:
                return positions_to_close
            
            series1 = aligned_data.iloc[:, 0]
            series2 = aligned_data.iloc[:, 1]
            
            # Get latest hedge ratio from active positions
            hedge_ratio = list(self.active_positions.values())[0].hedge_ratio
            spread = series1 - hedge_ratio * series2
            
            # Calculate indicators
            indicators = self.indicator_suite.calculate_all_indicators(spread)
            
            if not indicators:
                return positions_to_close
            
            current_zscore = indicators['zscore'].iloc[-1] if len(indicators['zscore']) > 0 else 0
            current_regime = indicators['regime'].iloc[-1] if len(indicators['regime']) > 0 else RegimeType.UNKNOWN.value
            
            # Check exit conditions for each position
            for pair_id, position in self.active_positions.items():
                should_exit = False
                
                # Z-Score exit condition
                if position.position_type == PositionType.LONG_SPREAD:
                    # Exit long spread when Z-Score crosses above exit threshold
                    if current_zscore >= -self.config.zscore_exit_threshold:
                        should_exit = True
                elif position.position_type == PositionType.SHORT_SPREAD:
                    # Exit short spread when Z-Score crosses below exit threshold
                    if current_zscore <= self.config.zscore_exit_threshold:
                        should_exit = True
                
                # Stop loss condition
                if position.stop_loss and position.current_pnl <= -abs(position.stop_loss):
                    should_exit = True
                
                # Take profit condition
                if position.take_profit and position.current_pnl >= position.take_profit:
                    should_exit = True
                
                # Regime change condition
                if (self.config.regime_filter and 
                    current_regime not in [RegimeType.MEAN_REVERTING.value, RegimeType.STABLE.value]):
                    should_exit = True
                
                # Time-based exit (optional)
                time_in_position = (datetime.now() - position.entry_time).days
                if time_in_position > 30:  # Max 30 days in position
                    should_exit = True
                
                if should_exit:
                    positions_to_close.append(pair_id)
            
            return positions_to_close
        
        except Exception as e:
            logger.warning(f"Error checking exit conditions: {e}")
            return []
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate strategy performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        try:
            if not self.active_positions:
                return {}
            
            total_pnl = sum(pos.current_pnl for pos in self.active_positions.values())
            total_positions = len(self.active_positions)
            winning_positions = sum(1 for pos in self.active_positions.values() if pos.current_pnl > 0)
            
            metrics = {
                'total_pnl': total_pnl,
                'total_positions': total_positions,
                'winning_positions': winning_positions,
                'win_rate': winning_positions / total_positions if total_positions > 0 else 0,
                'avg_pnl_per_position': total_pnl / total_positions if total_positions > 0 else 0,
                'max_favorable_excursion': max((pos.max_favorable for pos in self.active_positions.values()), default=0),
                'max_adverse_excursion': min((pos.max_adverse for pos in self.active_positions.values()), default=0)
            }
            
            self.performance_metrics = metrics
            return metrics
        
        except Exception as e:
            logger.warning(f"Error calculating performance metrics: {e}")
            return {}


class ConvergenceStrategy(BasePairsStrategy):
    """Mean reversion pairs trading strategy."""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.strategy_type = StrategyType.CONVERGENCE
    
    def generate_signals(self, 
                        data1: pd.Series, 
                        data2: pd.Series,
                        volume1: Optional[pd.Series] = None,
                        volume2: Optional[pd.Series] = None) -> List[TradingSignal]:
        """Generate convergence (mean reversion) signals.
        
        Args:
            data1: First asset price series
            data2: Second asset price series
            volume1: Optional volume series for first asset
            volume2: Optional volume series for second asset
            
        Returns:
            List of trading signals
        """
        try:
            signals = []
            
            # Validate pair first
            is_valid, validation_metrics = self.validate_pair(data1, data2)
            if not is_valid:
                return signals
            
            # Align data
            aligned_data = pd.concat([data1, data2], axis=1).dropna()
            if len(aligned_data) < self.config.lookback_period:
                return signals
            
            series1 = aligned_data.iloc[:, 0]
            series2 = aligned_data.iloc[:, 1]
            hedge_ratio = validation_metrics.get('hedge_ratio', 1.0)
            
            # Calculate spread
            spread = series1 - hedge_ratio * series2
            
            # Align volume data if provided
            volume_combined = None
            if volume1 is not None and volume2 is not None:
                volume_aligned = pd.concat([volume1, volume2], axis=1).dropna()
                if len(volume_aligned) == len(spread):
                    volume_combined = volume_aligned.iloc[:, 0] + volume_aligned.iloc[:, 1]
            
            # Calculate indicators
            indicators = self.indicator_suite.calculate_all_indicators(spread, volume_combined)
            
            if not indicators:
                return signals
            
            # Get latest values
            latest_zscore = indicators['zscore'].iloc[-1] if len(indicators['zscore']) > 0 else 0
            latest_regime = indicators['regime'].iloc[-1] if len(indicators['regime']) > 0 else RegimeType.UNKNOWN.value
            latest_bb_percent_b = indicators.get('bollinger_percent_b', pd.Series([0.5])).iloc[-1]
            latest_squeeze = indicators.get('bollinger_squeeze', pd.Series([0])).iloc[-1]
            
            # Only trade in mean-reverting or stable regimes
            if (self.config.regime_filter and 
                latest_regime not in [RegimeType.MEAN_REVERTING.value, RegimeType.STABLE.value]):
                return signals
            
            # Generate signals based on Z-Score
            current_price_1 = series1.iloc[-1]
            current_price_2 = series2.iloc[-1]
            
            # Long spread signal (Z-Score < -threshold)
            if latest_zscore <= -self.config.zscore_entry_threshold:
                # Confirm with Bollinger Bands
                bb_confirmation = latest_bb_percent_b <= 0.2
                
                # Volume confirmation
                volume_confirmation = True
                if self.config.volume_confirmation and volume_combined is not None:
                    recent_volume = volume_combined.iloc[-5:].mean()
                    avg_volume = volume_combined.iloc[-20:].mean()
                    volume_confirmation = recent_volume > avg_volume * 1.1
                
                if bb_confirmation and volume_confirmation:
                    strength = self._calculate_signal_strength(abs(latest_zscore))
                    confidence = self._calculate_confidence(latest_zscore, latest_regime, latest_squeeze)
                    
                    signal = TradingSignal(
                        signal_type=StrategyType.CONVERGENCE,
                        position_type=PositionType.LONG_SPREAD,
                        strength=strength,
                        confidence=confidence,
                        entry_price_1=current_price_1,
                        entry_price_2=current_price_2,
                        hedge_ratio=hedge_ratio,
                        stop_loss=abs(latest_zscore) * self.config.stop_loss_pct,
                        take_profit=abs(latest_zscore) * self.config.take_profit_pct,
                        regime=RegimeType(latest_regime),
                        metadata={
                            'zscore': latest_zscore,
                            'bb_percent_b': latest_bb_percent_b,
                            'squeeze': latest_squeeze,
                            'validation_metrics': validation_metrics
                        }
                    )
                    signals.append(signal)
            
            # Short spread signal (Z-Score > threshold)
            elif latest_zscore >= self.config.zscore_entry_threshold:
                # Confirm with Bollinger Bands
                bb_confirmation = latest_bb_percent_b >= 0.8
                
                # Volume confirmation
                volume_confirmation = True
                if self.config.volume_confirmation and volume_combined is not None:
                    recent_volume = volume_combined.iloc[-5:].mean()
                    avg_volume = volume_combined.iloc[-20:].mean()
                    volume_confirmation = recent_volume > avg_volume * 1.1
                
                if bb_confirmation and volume_confirmation:
                    strength = self._calculate_signal_strength(abs(latest_zscore))
                    confidence = self._calculate_confidence(latest_zscore, latest_regime, latest_squeeze)
                    
                    signal = TradingSignal(
                        signal_type=StrategyType.CONVERGENCE,
                        position_type=PositionType.SHORT_SPREAD,
                        strength=strength,
                        confidence=confidence,
                        entry_price_1=current_price_1,
                        entry_price_2=current_price_2,
                        hedge_ratio=hedge_ratio,
                        stop_loss=abs(latest_zscore) * self.config.stop_loss_pct,
                        take_profit=abs(latest_zscore) * self.config.take_profit_pct,
                        regime=RegimeType(latest_regime),
                        metadata={
                            'zscore': latest_zscore,
                            'bb_percent_b': latest_bb_percent_b,
                            'squeeze': latest_squeeze,
                            'validation_metrics': validation_metrics
                        }
                    )
                    signals.append(signal)
            
            return signals
        
        except Exception as e:
            logger.warning(f"Error generating convergence signals: {e}")
            return []
    
    def calculate_position_size(self, 
                              signal: TradingSignal,
                              portfolio_value: float,
                              current_exposure: float) -> Tuple[float, float]:
        """Calculate position sizes for convergence strategy.
        
        Args:
            signal: Trading signal
            portfolio_value: Total portfolio value
            current_exposure: Current portfolio exposure
            
        Returns:
            Tuple of (quantity_asset1, quantity_asset2)
        """
        try:
            # Base position size as percentage of portfolio
            base_position_pct = 0.1  # 10% of portfolio per trade
            
            # Adjust based on signal strength and confidence
            strength_multiplier = {
                SignalStrength.WEAK: 0.5,
                SignalStrength.MODERATE: 0.75,
                SignalStrength.STRONG: 1.0,
                SignalStrength.EXTREME: 1.25
            }.get(signal.strength, 1.0)
            
            confidence_multiplier = signal.confidence
            
            # Check exposure limits
            if current_exposure + base_position_pct > self.config.max_portfolio_exposure:
                base_position_pct = max(0, self.config.max_portfolio_exposure - current_exposure)
            
            # Calculate position value
            position_value = portfolio_value * base_position_pct * strength_multiplier * confidence_multiplier
            
            # Calculate quantities
            if signal.position_type == PositionType.LONG_SPREAD:
                # Long asset1, short asset2
                quantity_1 = position_value / signal.entry_price_1
                quantity_2 = -quantity_1 * signal.hedge_ratio * signal.entry_price_1 / signal.entry_price_2
            else:
                # Short asset1, long asset2
                quantity_1 = -position_value / signal.entry_price_1
                quantity_2 = -quantity_1 * signal.hedge_ratio * signal.entry_price_1 / signal.entry_price_2
            
            return quantity_1, quantity_2
        
        except Exception as e:
            logger.warning(f"Error calculating position size: {e}")
            return 0.0, 0.0
    
    def _calculate_signal_strength(self, zscore_abs: float) -> SignalStrength:
        """Calculate signal strength based on Z-Score magnitude."""
        if zscore_abs >= 3.0:
            return SignalStrength.EXTREME
        elif zscore_abs >= 2.5:
            return SignalStrength.STRONG
        elif zscore_abs >= 2.0:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _calculate_confidence(self, zscore: float, regime: str, squeeze: float) -> float:
        """Calculate signal confidence based on multiple factors."""
        try:
            base_confidence = min(abs(zscore) / 3.0, 1.0)  # Z-Score contribution
            
            # Regime contribution
            regime_bonus = 0.2 if regime == RegimeType.MEAN_REVERTING.value else 0.0
            
            # Squeeze contribution (higher confidence during squeeze)
            squeeze_bonus = 0.1 if squeeze > 0.5 else 0.0
            
            total_confidence = min(base_confidence + regime_bonus + squeeze_bonus, 1.0)
            return max(total_confidence, 0.1)  # Minimum 10% confidence
        
        except:
            return 0.5


class DivergenceStrategy(BasePairsStrategy):
    """Momentum/breakout pairs trading strategy."""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.strategy_type = StrategyType.DIVERGENCE
    
    def generate_signals(self, 
                        data1: pd.Series, 
                        data2: pd.Series,
                        volume1: Optional[pd.Series] = None,
                        volume2: Optional[pd.Series] = None) -> List[TradingSignal]:
        """Generate divergence (momentum) signals.
        
        Args:
            data1: First asset price series
            data2: Second asset price series
            volume1: Optional volume series for first asset
            volume2: Optional volume series for second asset
            
        Returns:
            List of trading signals
        """
        try:
            signals = []
            
            # Validate pair first
            is_valid, validation_metrics = self.validate_pair(data1, data2)
            if not is_valid:
                return signals
            
            # Align data
            aligned_data = pd.concat([data1, data2], axis=1).dropna()
            if len(aligned_data) < self.config.lookback_period:
                return signals
            
            series1 = aligned_data.iloc[:, 0]
            series2 = aligned_data.iloc[:, 1]
            hedge_ratio = validation_metrics.get('hedge_ratio', 1.0)
            
            # Calculate spread
            spread = series1 - hedge_ratio * series2
            
            # Calculate indicators
            indicators = self.indicator_suite.calculate_all_indicators(spread)
            
            if not indicators:
                return signals
            
            # Get momentum indicators
            momentum = indicators.get('momentum', pd.Series([0]))
            velocity = indicators.get('velocity', pd.Series([0]))
            latest_regime = indicators['regime'].iloc[-1] if len(indicators['regime']) > 0 else RegimeType.UNKNOWN.value
            
            # Only trade in trending regimes for divergence
            if (self.config.regime_filter and 
                latest_regime != RegimeType.TRENDING.value):
                return signals
            
            # Get latest values
            latest_momentum = momentum.iloc[-1] if len(momentum) > 0 else 0
            latest_velocity = velocity.iloc[-1] if len(velocity) > 0 else 0
            current_price_1 = series1.iloc[-1]
            current_price_2 = series2.iloc[-1]
            
            # Momentum breakout signals
            momentum_threshold = spread.std() * 0.5  # Dynamic threshold
            
            if latest_momentum > momentum_threshold and latest_velocity > 0:
                # Bullish momentum - long spread
                strength = self._calculate_momentum_strength(latest_momentum, momentum_threshold)
                confidence = self._calculate_momentum_confidence(latest_momentum, latest_velocity)
                
                signal = TradingSignal(
                    signal_type=StrategyType.DIVERGENCE,
                    position_type=PositionType.LONG_SPREAD,
                    strength=strength,
                    confidence=confidence,
                    entry_price_1=current_price_1,
                    entry_price_2=current_price_2,
                    hedge_ratio=hedge_ratio,
                    stop_loss=momentum_threshold * 0.5,
                    take_profit=momentum_threshold * 2.0,
                    regime=RegimeType(latest_regime),
                    metadata={
                        'momentum': latest_momentum,
                        'velocity': latest_velocity,
                        'momentum_threshold': momentum_threshold,
                        'validation_metrics': validation_metrics
                    }
                )
                signals.append(signal)
            
            elif latest_momentum < -momentum_threshold and latest_velocity < 0:
                # Bearish momentum - short spread
                strength = self._calculate_momentum_strength(abs(latest_momentum), momentum_threshold)
                confidence = self._calculate_momentum_confidence(abs(latest_momentum), abs(latest_velocity))
                
                signal = TradingSignal(
                    signal_type=StrategyType.DIVERGENCE,
                    position_type=PositionType.SHORT_SPREAD,
                    strength=strength,
                    confidence=confidence,
                    entry_price_1=current_price_1,
                    entry_price_2=current_price_2,
                    hedge_ratio=hedge_ratio,
                    stop_loss=momentum_threshold * 0.5,
                    take_profit=momentum_threshold * 2.0,
                    regime=RegimeType(latest_regime),
                    metadata={
                        'momentum': latest_momentum,
                        'velocity': latest_velocity,
                        'momentum_threshold': momentum_threshold,
                        'validation_metrics': validation_metrics
                    }
                )
                signals.append(signal)
            
            return signals
        
        except Exception as e:
            logger.warning(f"Error generating divergence signals: {e}")
            return []
    
    def calculate_position_size(self, 
                              signal: TradingSignal,
                              portfolio_value: float,
                              current_exposure: float) -> Tuple[float, float]:
        """Calculate position sizes for divergence strategy.
        
        Args:
            signal: Trading signal
            portfolio_value: Total portfolio value
            current_exposure: Current portfolio exposure
            
        Returns:
            Tuple of (quantity_asset1, quantity_asset2)
        """
        try:
            # Smaller base position for momentum strategy (higher risk)
            base_position_pct = 0.05  # 5% of portfolio per trade
            
            # Adjust based on signal strength and confidence
            strength_multiplier = {
                SignalStrength.WEAK: 0.5,
                SignalStrength.MODERATE: 0.75,
                SignalStrength.STRONG: 1.0,
                SignalStrength.EXTREME: 1.5
            }.get(signal.strength, 1.0)
            
            confidence_multiplier = signal.confidence
            
            # Check exposure limits
            if current_exposure + base_position_pct > self.config.max_portfolio_exposure:
                base_position_pct = max(0, self.config.max_portfolio_exposure - current_exposure)
            
            # Calculate position value
            position_value = portfolio_value * base_position_pct * strength_multiplier * confidence_multiplier
            
            # Calculate quantities
            if signal.position_type == PositionType.LONG_SPREAD:
                quantity_1 = position_value / signal.entry_price_1
                quantity_2 = -quantity_1 * signal.hedge_ratio * signal.entry_price_1 / signal.entry_price_2
            else:
                quantity_1 = -position_value / signal.entry_price_1
                quantity_2 = -quantity_1 * signal.hedge_ratio * signal.entry_price_1 / signal.entry_price_2
            
            return quantity_1, quantity_2
        
        except Exception as e:
            logger.warning(f"Error calculating position size: {e}")
            return 0.0, 0.0
    
    def _calculate_momentum_strength(self, momentum_abs: float, threshold: float) -> SignalStrength:
        """Calculate signal strength based on momentum magnitude."""
        ratio = momentum_abs / threshold
        if ratio >= 3.0:
            return SignalStrength.EXTREME
        elif ratio >= 2.0:
            return SignalStrength.STRONG
        elif ratio >= 1.5:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _calculate_momentum_confidence(self, momentum: float, velocity: float) -> float:
        """Calculate signal confidence based on momentum and velocity alignment."""
        try:
            # Base confidence from momentum magnitude
            base_confidence = min(momentum / (momentum + 1.0), 0.8)
            
            # Velocity confirmation bonus
            velocity_bonus = 0.2 if velocity > 0 else 0.0
            
            total_confidence = min(base_confidence + velocity_bonus, 1.0)
            return max(total_confidence, 0.1)
        
        except:
            return 0.5


class HybridPairsStrategy(BasePairsStrategy):
    """Hybrid strategy combining convergence and divergence approaches."""
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.strategy_type = StrategyType.HYBRID
        self.convergence_strategy = ConvergenceStrategy(config)
        self.divergence_strategy = DivergenceStrategy(config)
    
    def generate_signals(self, 
                        data1: pd.Series, 
                        data2: pd.Series,
                        volume1: Optional[pd.Series] = None,
                        volume2: Optional[pd.Series] = None) -> List[TradingSignal]:
        """Generate hybrid signals combining both strategies.
        
        Args:
            data1: First asset price series
            data2: Second asset price series
            volume1: Optional volume series for first asset
            volume2: Optional volume series for second asset
            
        Returns:
            List of trading signals
        """
        try:
            signals = []
            
            # Generate signals from both strategies
            if self.config.convergence_enabled:
                convergence_signals = self.convergence_strategy.generate_signals(
                    data1, data2, volume1, volume2
                )
                signals.extend(convergence_signals)
            
            if self.config.divergence_enabled:
                divergence_signals = self.divergence_strategy.generate_signals(
                    data1, data2, volume1, volume2
                )
                signals.extend(divergence_signals)
            
            # Filter and prioritize signals
            if len(signals) > 1:
                # Prioritize based on confidence and regime appropriateness
                signals.sort(key=lambda s: s.confidence, reverse=True)
                # Take only the best signal to avoid conflicts
                signals = signals[:1]
            
            return signals
        
        except Exception as e:
            logger.warning(f"Error generating hybrid signals: {e}")
            return []
    
    def calculate_position_size(self, 
                              signal: TradingSignal,
                              portfolio_value: float,
                              current_exposure: float) -> Tuple[float, float]:
        """Calculate position sizes for hybrid strategy."""
        if signal.signal_type == StrategyType.CONVERGENCE:
            return self.convergence_strategy.calculate_position_size(
                signal, portfolio_value, current_exposure
            )
        else:
            return self.divergence_strategy.calculate_position_size(
                signal, portfolio_value, current_exposure
            )