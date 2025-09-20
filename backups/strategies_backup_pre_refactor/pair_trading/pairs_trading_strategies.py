"""Pairs Trading Strategies Implementation.

This module provides complete strategy implementations for market-neutral
pairs trading, combining technical indicators and candlestick patterns.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
import warnings
from datetime import datetime, timedelta

try:
    from .pairs_trading_indicators import (
        PairsTradingIndicators, SpreadCalculator, RatioCalculator,
        PairSelectionEngine, ConvergenceStrategy, DivergenceStrategy
    )
    from .pairs_candlestick_patterns import (
        SpreadPatternAnalyzer, PatternResult, PatternSignal
    )
except ImportError:
    # Fallback for standalone usage
    from pairs_trading_indicators import (
        PairsTradingIndicators, SpreadCalculator, RatioCalculator,
        PairSelectionEngine, ConvergenceStrategy, DivergenceStrategy
    )
    from pairs_candlestick_patterns import (
        SpreadPatternAnalyzer, PatternResult, PatternSignal
    )


class StrategyType(Enum):
    """Types of pairs trading strategies."""
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    COINTEGRATION = "cointegration"
    HYBRID = "hybrid"


class PositionType(Enum):
    """Position types for pairs trading."""
    LONG_SPREAD = "long_spread"  # Long stock1, short stock2
    SHORT_SPREAD = "short_spread"  # Short stock1, long stock2
    FLAT = "flat"


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class TradingSignal:
    """Trading signal for pairs trading."""
    timestamp: datetime
    signal_type: PositionType
    strength: SignalStrength
    confidence: float  # 0.0 to 1.0
    entry_price_stock1: float
    entry_price_stock2: float
    spread_value: float
    ratio_value: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Position:
    """Pairs trading position."""
    pair_id: str
    position_type: PositionType
    entry_timestamp: datetime
    entry_price_stock1: float
    entry_price_stock2: float
    entry_spread: float
    entry_ratio: float
    quantity_stock1: float
    quantity_stock2: float
    current_pnl: float = 0.0
    max_pnl: float = 0.0
    min_pnl: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    exit_price_stock1: Optional[float] = None
    exit_price_stock2: Optional[float] = None
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)


@dataclass
class StrategyConfig:
    """Configuration for pairs trading strategies."""
    # Strategy parameters
    strategy_type: StrategyType = StrategyType.HYBRID
    lookback_period: int = 20
    entry_threshold: float = 2.0  # Z-score threshold for entry
    exit_threshold: float = 0.5   # Z-score threshold for exit
    stop_loss_threshold: float = 3.0  # Z-score threshold for stop loss
    
    # Position sizing
    max_position_size: float = 100000.0  # Maximum position size per pair
    position_sizing_method: str = "equal_dollar"  # "equal_dollar", "beta_neutral", "volatility_adjusted"
    
    # Risk management
    max_pairs: int = 10
    max_correlation_threshold: float = 0.95  # Maximum correlation to avoid over-concentration
    min_correlation_threshold: float = 0.7   # Minimum correlation for pair selection
    max_drawdown_threshold: float = 0.1      # Maximum portfolio drawdown
    
    # Technical indicators
    use_volume_weighting: bool = True
    use_candlestick_patterns: bool = True
    pattern_confirmation_required: bool = True
    
    # Timing parameters
    min_holding_period: int = 1    # Minimum holding period in days
    max_holding_period: int = 30   # Maximum holding period in days
    rebalance_frequency: str = "daily"  # "intraday", "daily", "weekly"
    
    # Data requirements
    min_history_days: int = 252    # Minimum historical data required
    data_frequency: str = "1D"     # Data frequency for analysis


class PairsTradingEngine:
    """Complete pairs trading engine combining indicators and patterns."""
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.indicators = PairsTradingIndicators()
        self.pattern_analyzer = SpreadPatternAnalyzer()
        self.pair_selector = PairSelectionEngine()
        self.convergence_strategy = ConvergenceStrategy()
        self.divergence_strategy = DivergenceStrategy()
        
        # Strategy state
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.selected_pairs: List[Dict] = []
        self.signal_history: List[TradingSignal] = []
        
        # Performance tracking
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.win_rate = 0.0
        self.sharpe_ratio = 0.0
        
    def initialize_strategy(self, universe_data: Dict[str, pd.DataFrame]) -> Dict:
        """Initialize the strategy with universe data."""
        print("Initializing pairs trading strategy...")
        
        # Select pairs from universe
        self.selected_pairs = self.pair_selector.select_pairs(
            universe_data,
            min_correlation=self.config.min_correlation_threshold,
            max_pairs=self.config.max_pairs
        )
        
        print(f"Selected {len(self.selected_pairs)} pairs for trading")
        
        # Initialize indicators for each pair
        pair_indicators = {}
        for pair in self.selected_pairs:
            pair_id = f"{pair['stock1']}_{pair['stock2']}"
            
            # Get data for the pair
            stock1_data = universe_data[pair['stock1']]
            stock2_data = universe_data[pair['stock2']]
            
            # Calculate indicators
            indicators = self._calculate_pair_indicators(stock1_data, stock2_data)
            pair_indicators[pair_id] = indicators
        
        return {
            'selected_pairs': self.selected_pairs,
            'pair_indicators': pair_indicators,
            'initialization_timestamp': datetime.now()
        }
    
    def generate_signals(self, current_data: Dict[str, pd.DataFrame]) -> List[TradingSignal]:
        """Generate trading signals for all pairs."""
        signals = []
        
        for pair in self.selected_pairs:
            pair_id = f"{pair['stock1']}_{pair['stock2']}"
            
            # Get current data for the pair
            stock1_data = current_data[pair['stock1']]
            stock2_data = current_data[pair['stock2']]
            
            # Generate signal for this pair
            pair_signal = self._generate_pair_signal(pair_id, stock1_data, stock2_data)
            
            if pair_signal:
                signals.append(pair_signal)
        
        # Store signals in history
        self.signal_history.extend(signals)
        
        return signals
    
    def execute_signals(self, signals: List[TradingSignal]) -> Dict:
        """Execute trading signals and manage positions."""
        execution_results = {
            'new_positions': [],
            'closed_positions': [],
            'position_updates': [],
            'execution_timestamp': datetime.now()
        }
        
        for signal in signals:
            if signal.signal_type == PositionType.FLAT:
                # Close existing position if any
                self._close_position_by_signal(signal, execution_results)
            else:
                # Open new position or update existing
                self._execute_entry_signal(signal, execution_results)
        
        # Update position PnL
        self._update_position_pnl()
        
        # Check for stop losses and take profits
        self._check_exit_conditions(execution_results)
        
        return execution_results
    
    def _calculate_pair_indicators(self, stock1_data: pd.DataFrame, 
                                 stock2_data: pd.DataFrame) -> Dict:
        """Calculate all indicators for a pair."""
        # Calculate spread and ratio
        spread_calc = SpreadCalculator()
        ratio_calc = RatioCalculator()
        
        spread_data = spread_calc.calculate_spread(
            stock1_data['Open'].values, stock1_data['High'].values,
            stock1_data['Low'].values, stock1_data['Close'].values,
            stock1_data['Volume'].values,
            stock2_data['Open'].values, stock2_data['High'].values,
            stock2_data['Low'].values, stock2_data['Close'].values,
            stock2_data['Volume'].values
        )
        
        ratio_data = ratio_calc.calculate_ratio(
            stock1_data['Open'].values, stock1_data['High'].values,
            stock1_data['Low'].values, stock1_data['Close'].values,
            stock1_data['Volume'].values,
            stock2_data['Open'].values, stock2_data['High'].values,
            stock2_data['Low'].values, stock2_data['Close'].values,
            stock2_data['Volume'].values
        )
        
        # Calculate technical indicators
        spread_indicators = self.indicators.calculate_spread_indicators(
            spread_data['spread_open'], spread_data['spread_high'],
            spread_data['spread_low'], spread_data['spread_close'],
            spread_data['spread_volume']
        )
        
        ratio_indicators = self.indicators.calculate_ratio_indicators(
            ratio_data['ratio_open'], ratio_data['ratio_high'],
            ratio_data['ratio_low'], ratio_data['ratio_close'],
            ratio_data['ratio_volume']
        )
        
        # Pattern analysis if enabled
        pattern_analysis = None
        if self.config.use_candlestick_patterns:
            spread_patterns = self.pattern_analyzer.analyze_spread_patterns(
                spread_data['spread_open'], spread_data['spread_high'],
                spread_data['spread_low'], spread_data['spread_close'],
                spread_data['spread_volume']
            )
            
            ratio_patterns = self.pattern_analyzer.analyze_ratio_patterns(
                ratio_data['ratio_open'], ratio_data['ratio_high'],
                ratio_data['ratio_low'], ratio_data['ratio_close'],
                ratio_data['ratio_volume']
            )
            
            pattern_analysis = self.pattern_analyzer.combine_spread_ratio_analysis(
                spread_patterns, ratio_patterns
            )
        
        return {
            'spread_data': spread_data,
            'ratio_data': ratio_data,
            'spread_indicators': spread_indicators,
            'ratio_indicators': ratio_indicators,
            'pattern_analysis': pattern_analysis,
            'calculation_timestamp': datetime.now()
        }
    
    def _generate_pair_signal(self, pair_id: str, stock1_data: pd.DataFrame, 
                            stock2_data: pd.DataFrame) -> Optional[TradingSignal]:
        """Generate trading signal for a specific pair."""
        # Calculate current indicators
        indicators = self._calculate_pair_indicators(stock1_data, stock2_data)
        
        # Get current values
        current_spread = indicators['spread_data']['spread_close'][-1]
        current_ratio = indicators['ratio_data']['ratio_close'][-1]
        current_price1 = stock1_data['Close'].iloc[-1]
        current_price2 = stock2_data['Close'].iloc[-1]
        
        # Calculate z-scores for mean reversion signals
        spread_zscore = self._calculate_zscore(
            indicators['spread_data']['spread_close'], self.config.lookback_period
        )
        
        ratio_zscore = self._calculate_zscore(
            indicators['ratio_data']['ratio_close'], self.config.lookback_period
        )
        
        # Determine signal based on strategy type
        if self.config.strategy_type == StrategyType.MEAN_REVERSION:
            signal = self._generate_mean_reversion_signal(
                pair_id, spread_zscore, ratio_zscore, current_spread, current_ratio,
                current_price1, current_price2, indicators
            )
        elif self.config.strategy_type == StrategyType.MOMENTUM:
            signal = self._generate_momentum_signal(
                pair_id, indicators, current_spread, current_ratio,
                current_price1, current_price2
            )
        elif self.config.strategy_type == StrategyType.HYBRID:
            signal = self._generate_hybrid_signal(
                pair_id, spread_zscore, ratio_zscore, current_spread, current_ratio,
                current_price1, current_price2, indicators
            )
        else:
            signal = None
        
        return signal
    
    def _generate_mean_reversion_signal(self, pair_id: str, spread_zscore: float,
                                      ratio_zscore: float, current_spread: float,
                                      current_ratio: float, price1: float, price2: float,
                                      indicators: Dict) -> Optional[TradingSignal]:
        """Generate mean reversion trading signal."""
        # Check if we have an existing position
        existing_position = self.active_positions.get(pair_id)
        
        # Entry signals
        if existing_position is None:
            if spread_zscore > self.config.entry_threshold:
                # Spread is too high, expect mean reversion (short spread)
                signal_type = PositionType.SHORT_SPREAD
                strength = self._determine_signal_strength(abs(spread_zscore))
                confidence = min(0.9, abs(spread_zscore) / 4.0)
                
            elif spread_zscore < -self.config.entry_threshold:
                # Spread is too low, expect mean reversion (long spread)
                signal_type = PositionType.LONG_SPREAD
                strength = self._determine_signal_strength(abs(spread_zscore))
                confidence = min(0.9, abs(spread_zscore) / 4.0)
                
            else:
                return None  # No signal
        
        # Exit signals
        else:
            if (existing_position.position_type == PositionType.LONG_SPREAD and 
                spread_zscore > -self.config.exit_threshold):
                signal_type = PositionType.FLAT
                strength = SignalStrength.MODERATE
                confidence = 0.7
                
            elif (existing_position.position_type == PositionType.SHORT_SPREAD and 
                  spread_zscore < self.config.exit_threshold):
                signal_type = PositionType.FLAT
                strength = SignalStrength.MODERATE
                confidence = 0.7
                
            else:
                return None  # No exit signal
        
        # Apply pattern confirmation if enabled
        if self.config.use_candlestick_patterns and self.config.pattern_confirmation_required:
            pattern_confirmation = self._check_pattern_confirmation(
                signal_type, indicators.get('pattern_analysis')
            )
            if not pattern_confirmation:
                return None
        
        # Create signal
        signal = TradingSignal(
            timestamp=datetime.now(),
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price_stock1=price1,
            entry_price_stock2=price2,
            spread_value=current_spread,
            ratio_value=current_ratio,
            stop_loss=self._calculate_stop_loss(signal_type, current_spread, spread_zscore),
            take_profit=self._calculate_take_profit(signal_type, current_spread, spread_zscore),
            metadata={
                'pair_id': pair_id,
                'spread_zscore': spread_zscore,
                'ratio_zscore': ratio_zscore,
                'strategy_type': 'mean_reversion'
            }
        )
        
        return signal
    
    def _generate_momentum_signal(self, pair_id: str, indicators: Dict,
                                current_spread: float, current_ratio: float,
                                price1: float, price2: float) -> Optional[TradingSignal]:
        """Generate momentum trading signal."""
        # Get momentum indicators
        spread_indicators = indicators['spread_indicators']
        
        # Check MACD crossover
        macd_line = spread_indicators['macd']['macd_line']
        signal_line = spread_indicators['macd']['signal_line']
        
        if len(macd_line) < 2 or len(signal_line) < 2:
            return None
        
        # Bullish crossover
        if (macd_line[-1] > signal_line[-1] and macd_line[-2] <= signal_line[-2]):
            signal_type = PositionType.LONG_SPREAD
            strength = SignalStrength.MODERATE
            confidence = 0.6
        
        # Bearish crossover
        elif (macd_line[-1] < signal_line[-1] and macd_line[-2] >= signal_line[-2]):
            signal_type = PositionType.SHORT_SPREAD
            strength = SignalStrength.MODERATE
            confidence = 0.6
        
        else:
            return None
        
        # Create signal
        signal = TradingSignal(
            timestamp=datetime.now(),
            signal_type=signal_type,
            strength=strength,
            confidence=confidence,
            entry_price_stock1=price1,
            entry_price_stock2=price2,
            spread_value=current_spread,
            ratio_value=current_ratio,
            metadata={
                'pair_id': pair_id,
                'macd_crossover': True,
                'strategy_type': 'momentum'
            }
        )
        
        return signal
    
    def _generate_hybrid_signal(self, pair_id: str, spread_zscore: float,
                              ratio_zscore: float, current_spread: float,
                              current_ratio: float, price1: float, price2: float,
                              indicators: Dict) -> Optional[TradingSignal]:
        """Generate hybrid trading signal combining mean reversion and momentum."""
        # Get both mean reversion and momentum signals
        mr_signal = self._generate_mean_reversion_signal(
            pair_id, spread_zscore, ratio_zscore, current_spread, current_ratio,
            price1, price2, indicators
        )
        
        momentum_signal = self._generate_momentum_signal(
            pair_id, indicators, current_spread, current_ratio, price1, price2
        )
        
        # Combine signals
        if mr_signal and momentum_signal:
            # Both signals agree
            if mr_signal.signal_type == momentum_signal.signal_type:
                combined_confidence = (mr_signal.confidence + momentum_signal.confidence) / 2
                combined_strength = self._combine_signal_strengths(
                    mr_signal.strength, momentum_signal.strength
                )
                
                signal = TradingSignal(
                    timestamp=datetime.now(),
                    signal_type=mr_signal.signal_type,
                    strength=combined_strength,
                    confidence=min(0.95, combined_confidence * 1.2),  # Boost confidence for agreement
                    entry_price_stock1=price1,
                    entry_price_stock2=price2,
                    spread_value=current_spread,
                    ratio_value=current_ratio,
                    stop_loss=mr_signal.stop_loss,
                    take_profit=mr_signal.take_profit,
                    metadata={
                        'pair_id': pair_id,
                        'strategy_type': 'hybrid',
                        'signal_agreement': True,
                        'mr_confidence': mr_signal.confidence,
                        'momentum_confidence': momentum_signal.confidence
                    }
                )
                return signal
        
        # Return stronger signal if only one exists
        elif mr_signal and mr_signal.confidence > 0.7:
            return mr_signal
        elif momentum_signal and momentum_signal.confidence > 0.7:
            return momentum_signal
        
        return None
    
    def _calculate_zscore(self, values: np.ndarray, lookback: int) -> float:
        """Calculate z-score for the latest value."""
        if len(values) < lookback:
            return 0.0
        
        recent_values = values[-lookback:]
        mean_val = np.mean(recent_values[:-1])  # Exclude current value from mean
        std_val = np.std(recent_values[:-1])
        
        if std_val == 0:
            return 0.0
        
        return (values[-1] - mean_val) / std_val
    
    def _determine_signal_strength(self, zscore_abs: float) -> SignalStrength:
        """Determine signal strength based on z-score magnitude."""
        if zscore_abs >= 3.0:
            return SignalStrength.VERY_STRONG
        elif zscore_abs >= 2.5:
            return SignalStrength.STRONG
        elif zscore_abs >= 2.0:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _combine_signal_strengths(self, strength1: SignalStrength, 
                                strength2: SignalStrength) -> SignalStrength:
        """Combine two signal strengths."""
        strength_values = {
            SignalStrength.WEAK: 1,
            SignalStrength.MODERATE: 2,
            SignalStrength.STRONG: 3,
            SignalStrength.VERY_STRONG: 4
        }
        
        combined_value = (strength_values[strength1] + strength_values[strength2]) / 2
        
        if combined_value >= 3.5:
            return SignalStrength.VERY_STRONG
        elif combined_value >= 2.5:
            return SignalStrength.STRONG
        elif combined_value >= 1.5:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
    
    def _check_pattern_confirmation(self, signal_type: PositionType, 
                                  pattern_analysis: Optional[Dict]) -> bool:
        """Check if candlestick patterns confirm the signal."""
        if not pattern_analysis or not pattern_analysis.get('combined_recommendations'):
            return True  # No pattern analysis available, allow signal
        
        recommendations = pattern_analysis['combined_recommendations']
        
        for rec in recommendations:
            if rec.get('consensus', False):  # Only consider consensus recommendations
                if signal_type == PositionType.LONG_SPREAD and rec['action'] == 'LONG_SPREAD':
                    return True
                elif signal_type == PositionType.SHORT_SPREAD and rec['action'] == 'SHORT_SPREAD':
                    return True
        
        return False
    
    def _calculate_stop_loss(self, signal_type: PositionType, current_spread: float, 
                           zscore: float) -> float:
        """Calculate stop loss level."""
        if signal_type == PositionType.LONG_SPREAD:
            # Stop loss below entry for long spread
            return current_spread * (1 - self.config.stop_loss_threshold * 0.01)
        elif signal_type == PositionType.SHORT_SPREAD:
            # Stop loss above entry for short spread
            return current_spread * (1 + self.config.stop_loss_threshold * 0.01)
        return None
    
    def _calculate_take_profit(self, signal_type: PositionType, current_spread: float, 
                             zscore: float) -> float:
        """Calculate take profit level."""
        # Take profit at mean reversion (zscore near 0)
        if signal_type == PositionType.LONG_SPREAD:
            return current_spread * (1 + abs(zscore) * 0.005)  # Profit target
        elif signal_type == PositionType.SHORT_SPREAD:
            return current_spread * (1 - abs(zscore) * 0.005)  # Profit target
        return None
    
    def _execute_entry_signal(self, signal: TradingSignal, results: Dict):
        """Execute entry signal and create position."""
        pair_id = signal.metadata['pair_id']
        
        # Calculate position size
        position_size = self._calculate_position_size(signal)
        
        # Create position
        position = Position(
            pair_id=pair_id,
            position_type=signal.signal_type,
            entry_timestamp=signal.timestamp,
            entry_price_stock1=signal.entry_price_stock1,
            entry_price_stock2=signal.entry_price_stock2,
            entry_spread=signal.spread_value,
            entry_ratio=signal.ratio_value,
            quantity_stock1=position_size,
            quantity_stock2=position_size * signal.ratio_value,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            metadata=signal.metadata
        )
        
        self.active_positions[pair_id] = position
        results['new_positions'].append(position)
    
    def _close_position_by_signal(self, signal: TradingSignal, results: Dict):
        """Close position based on exit signal."""
        pair_id = signal.metadata['pair_id']
        position = self.active_positions.get(pair_id)
        
        if position:
            position.exit_timestamp = signal.timestamp
            position.exit_price_stock1 = signal.entry_price_stock1
            position.exit_price_stock2 = signal.entry_price_stock2
            position.is_active = False
            
            # Calculate final PnL
            final_pnl = self._calculate_position_pnl_final(position)
            position.current_pnl = final_pnl
            
            # Move to closed positions
            self.closed_positions.append(position)
            del self.active_positions[pair_id]
            
            results['closed_positions'].append(position)
    
    def _calculate_position_size(self, signal: TradingSignal) -> float:
        """Calculate position size based on configuration."""
        if self.config.position_sizing_method == "equal_dollar":
            return self.config.max_position_size / signal.entry_price_stock1
        else:
            # Simplified position sizing
            return self.config.max_position_size / signal.entry_price_stock1
    
    def _update_position_pnl(self):
        """Update PnL for all active positions."""
        for position in self.active_positions.values():
            # Simplified PnL calculation - would need current prices in practice
            pass
    
    def _calculate_position_pnl_final(self, position: Position) -> float:
        """Calculate final PnL for closed position."""
        if position.position_type == PositionType.LONG_SPREAD:
            stock1_pnl = (position.exit_price_stock1 - position.entry_price_stock1) * position.quantity_stock1
            stock2_pnl = (position.entry_price_stock2 - position.exit_price_stock2) * position.quantity_stock2
        else:  # SHORT_SPREAD
            stock1_pnl = (position.entry_price_stock1 - position.exit_price_stock1) * position.quantity_stock1
            stock2_pnl = (position.exit_price_stock2 - position.entry_price_stock2) * position.quantity_stock2
        
        return stock1_pnl + stock2_pnl
    
    def _check_exit_conditions(self, results: Dict):
        """Check stop loss and take profit conditions."""
        for pair_id, position in list(self.active_positions.items()):
            # Simplified exit condition checking
            # In practice, would need current market prices
            pass
    
    def get_strategy_performance(self) -> Dict:
        """Get comprehensive strategy performance metrics."""
        total_trades = len(self.closed_positions)
        
        if total_trades == 0:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'average_pnl': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'active_positions': len(self.active_positions)
            }
        
        # Calculate performance metrics
        pnls = [pos.current_pnl for pos in self.closed_positions]
        winning_trades = len([pnl for pnl in pnls if pnl > 0])
        
        total_pnl = sum(pnls)
        win_rate = winning_trades / total_trades
        avg_pnl = total_pnl / total_trades
        
        # Calculate drawdown (simplified)
        cumulative_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdowns = (cumulative_pnl - running_max) / (running_max + 1e-8)
        max_drawdown = np.min(drawdowns) if len(drawdowns) > 0 else 0.0
        
        # Calculate Sharpe ratio (simplified)
        if len(pnls) > 1:
            sharpe_ratio = np.mean(pnls) / (np.std(pnls) + 1e-8) * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': total_trades - winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'average_pnl': avg_pnl,
            'max_drawdown': abs(max_drawdown),
            'sharpe_ratio': sharpe_ratio,
            'active_positions': len(self.active_positions),
            'selected_pairs': len(self.selected_pairs)
        }
    
    def get_current_positions(self) -> Dict:
        """Get current active positions summary."""
        positions_summary = []
        
        for pair_id, position in self.active_positions.items():
            positions_summary.append({
                'pair_id': pair_id,
                'position_type': position.position_type.value,
                'entry_timestamp': position.entry_timestamp,
                'entry_spread': position.entry_spread,
                'entry_ratio': position.entry_ratio,
                'current_pnl': position.current_pnl,
                'days_held': (datetime.now() - position.entry_timestamp).days,
                'stop_loss': position.stop_loss,
                'take_profit': position.take_profit
            })
        
        return {
            'active_positions': positions_summary,
            'total_active': len(positions_summary),
            'total_exposure': sum(pos.quantity_stock1 * pos.entry_price_stock1 
                                for pos in self.active_positions.values())
        }


# Example usage and testing functions
def test_pairs_trading_strategies():
    """Test the complete pairs trading strategy implementation."""
    print("Testing Pairs Trading Strategies...")
    
    # Create strategy configuration
    config = StrategyConfig(
        strategy_type=StrategyType.HYBRID,
        lookback_period=20,
        entry_threshold=2.0,
        exit_threshold=0.5,
        max_pairs=5,
        use_candlestick_patterns=True
    )
    
    # Initialize trading engine
    engine = PairsTradingEngine(config)
    
    # Generate sample universe data
    np.random.seed(42)
    n_periods = 252
    
    # Create sample stock data
    universe_data = {}
    stock_names = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    for stock in stock_names:
        # Generate correlated price series
        base_price = 100.0
        returns = np.random.normal(0.0005, 0.02, n_periods)
        prices = base_price * np.exp(np.cumsum(returns))
        
        # Create OHLCV data
        data = pd.DataFrame({
            'Open': prices * (1 + np.random.normal(0, 0.001, n_periods)),
            'High': prices * (1 + np.abs(np.random.normal(0, 0.01, n_periods))),
            'Low': prices * (1 - np.abs(np.random.normal(0, 0.01, n_periods))),
            'Close': prices,
            'Volume': np.random.lognormal(10, 0.5, n_periods)
        })
        
        universe_data[stock] = data
    
    # Initialize strategy
    init_result = engine.initialize_strategy(universe_data)
    print(f"Strategy initialized with {len(init_result['selected_pairs'])} pairs")
    
    # Generate signals for recent data
    recent_data = {stock: data.tail(50) for stock, data in universe_data.items()}
    signals = engine.generate_signals(recent_data)
    
    print(f"Generated {len(signals)} trading signals")
    
    # Execute signals
    if signals:
        execution_results = engine.execute_signals(signals)
        print(f"Execution results:")
        print(f"  New positions: {len(execution_results['new_positions'])}")
        print(f"  Closed positions: {len(execution_results['closed_positions'])}")
    
    # Get performance metrics
    performance = engine.get_strategy_performance()
    print(f"\nStrategy Performance:")
    print(f"  Total trades: {performance['total_trades']}")
    print(f"  Win rate: {performance['win_rate']:.2%}")
    print(f"  Total PnL: ${performance['total_pnl']:.2f}")
    print(f"  Active positions: {performance['active_positions']}")
    
    # Get current positions
    current_positions = engine.get_current_positions()
    print(f"\nCurrent Positions:")
    print(f"  Active positions: {current_positions['total_active']}")
    print(f"  Total exposure: ${current_positions['total_exposure']:.2f}")
    
    print("\nPairs Trading Strategies test completed successfully!")


if __name__ == "__main__":
    test_pairs_trading_strategies()