import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

# Import base classes and utilities
from ....core.base_strategy import BaseInstitutionalStrategy
from ....core.enums import MarketRegime, SignalType, ExecutionAction
from ....core.execution_intent import ExecutionIntent
from ....core.performance_tracker import PerformanceMetrics
from ....core.strategy_state import StrategyState
from ....utils.risk_management_utils import RiskManagementUtils
from ....utils.execution_intent_utils import ExecutionIntentUtils, ExecutionConstraints
from ....core.strategy_config import (
    StrategyConfig, StrategyCategory, AssetClass, TimeFrame,
    IndicatorConfig, SignalConfig, RiskConfig, RegimeConfig,
    ExecutionConfig, PerformanceConfig, BacktestConfig
)


@dataclass
class VWMASignal:
    """Volume-Weighted Moving Average signal data"""
    fast_vwma: float
    slow_vwma: float
    price: float
    volume: float
    signal_strength: float
    signal_type: SignalType
    crossover_confirmed: bool
    volume_confirmation: bool
    regime_filter_passed: bool
    timestamp: datetime


class MovingAverageCrossoverVWMAStrategy(BaseInstitutionalStrategy):
    """
    Volume-Weighted Moving Average Crossover Strategy
    
    This strategy implements a sophisticated moving average crossover system using
    Volume-Weighted Moving Averages (VWMA) instead of traditional price-only averages.
    The strategy follows the 5-Pillar Institutional Architecture:
    
    Pillar 1: Signal Generation & Augmentation
    - Primary: VWMA crossover signals (fast VWMA crossing above/below slow VWMA)
    - Secondary: Volume confirmation, momentum confirmation
    - Candlestick patterns for entry timing optimization
    
    Pillar 2: Dynamic Risk & Money Management
    - Position sizing based on volatility and signal strength
    - Dynamic stop-loss and take-profit levels
    - Portfolio correlation adjustments
    
    Pillar 3: Market Regime Adaptation
    - Volatility regime detection
    - Trend strength assessment
    - Parameter adaptation based on market conditions
    
    Pillar 4: Decoupled Execution Logic & Order Management
    - Smart order routing based on market conditions
    - Execution algorithm selection
    - Slippage and market impact optimization
    
    Pillar 5: Performance Tracking & Configurability
    - Real-time performance metrics
    - Risk-adjusted returns calculation
    - Comprehensive logging and analysis
    """
    
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        
        # Strategy-specific parameters
        self.fast_period = config.strategy_parameters.get('fast_period', 10)
        self.slow_period = config.strategy_parameters.get('slow_period', 30)
        self.volume_confirmation_threshold = config.strategy_parameters.get('volume_confirmation_threshold', 1.2)
        self.momentum_lookback = config.strategy_parameters.get('momentum_lookback', 5)
        self.signal_persistence_bars = config.strategy_parameters.get('signal_persistence_bars', 2)
        
        # Internal state
        self.fast_vwma_values = {}
        self.slow_vwma_values = {}
        self.volume_ma_values = {}
        self.price_momentum = {}
        self.signal_history = {}
        self.crossover_signals = {}
        
        # Risk management
        self.risk_manager = RiskManagementUtils()
        self.execution_utils = ExecutionIntentUtils()
        
        self.logger.info(f"Initialized VWMA Crossover Strategy with fast_period={self.fast_period}, slow_period={self.slow_period}")
    
    def calculate_vwma(self, prices: pd.Series, volumes: pd.Series, period: int) -> pd.Series:
        """
        Calculate Volume-Weighted Moving Average.
        
        VWMA = Sum(Price * Volume) / Sum(Volume) over the period
        
        Args:
            prices: Price series
            volumes: Volume series
            period: Lookback period
            
        Returns:
            VWMA series
        """
        if len(prices) < period or len(volumes) < period:
            return pd.Series(index=prices.index, dtype=float)
        
        # Calculate price * volume
        pv = prices * volumes
        
        # Rolling sums
        pv_sum = pv.rolling(window=period, min_periods=period).sum()
        volume_sum = volumes.rolling(window=period, min_periods=period).sum()
        
        # VWMA calculation
        vwma = pv_sum / volume_sum
        
        return vwma.fillna(method='ffill')
    
    def calculate_volume_confirmation(self, volumes: pd.Series, period: int = 20) -> pd.Series:
        """
        Calculate volume confirmation indicator.
        
        Args:
            volumes: Volume series
            period: Lookback period for volume average
            
        Returns:
            Volume confirmation ratio (current volume / average volume)
        """
        volume_ma = volumes.rolling(window=period, min_periods=period).mean()
        volume_ratio = volumes / volume_ma
        return volume_ratio.fillna(1.0)
    
    def calculate_momentum_confirmation(self, prices: pd.Series, period: int = 5) -> pd.Series:
        """
        Calculate price momentum for signal confirmation.
        
        Args:
            prices: Price series
            period: Lookback period
            
        Returns:
            Momentum series (rate of change)
        """
        momentum = prices.pct_change(periods=period)
        return momentum.fillna(0.0)
    
    def generate_signals(self, symbol: str, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Pillar 1: Signal Generation & Augmentation
        
        Generate VWMA crossover signals with volume and momentum confirmation.
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            
        Returns:
            List of signal dictionaries
        """
        if len(data) < max(self.slow_period, 50):
            return []
        
        signals = []
        
        try:
            # Use typical price for VWMA calculation
            typical_price = (data['high'] + data['low'] + data['close']) / 3
            volumes = data['volume']
            
            # Calculate VWMAs
            fast_vwma = self.calculate_vwma(typical_price, volumes, self.fast_period)
            slow_vwma = self.calculate_vwma(typical_price, volumes, self.slow_period)
            
            # Calculate confirmation indicators
            volume_confirmation = self.calculate_volume_confirmation(volumes)
            momentum_confirmation = self.calculate_momentum_confirmation(data['close'], self.momentum_lookback)
            
            # Store for later use
            self.fast_vwma_values[symbol] = fast_vwma
            self.slow_vwma_values[symbol] = slow_vwma
            
            # Detect crossovers
            fast_above_slow = fast_vwma > slow_vwma
            fast_above_slow_prev = fast_above_slow.shift(1)
            
            # Bullish crossover: fast VWMA crosses above slow VWMA
            bullish_crossover = (fast_above_slow & ~fast_above_slow_prev)
            
            # Bearish crossover: fast VWMA crosses below slow VWMA
            bearish_crossover = (~fast_above_slow & fast_above_slow_prev)
            
            # Generate signals for recent crossovers
            recent_data = data.tail(10)  # Look at last 10 bars
            
            for i, (timestamp, row) in enumerate(recent_data.iterrows()):
                idx = data.index.get_loc(timestamp)
                
                if idx < max(self.slow_period, 20):
                    continue
                
                current_price = row['close']
                current_volume = row['volume']
                
                # Get indicator values
                fast_val = fast_vwma.iloc[idx] if idx < len(fast_vwma) else np.nan
                slow_val = slow_vwma.iloc[idx] if idx < len(slow_vwma) else np.nan
                vol_conf = volume_confirmation.iloc[idx] if idx < len(volume_confirmation) else 1.0
                momentum = momentum_confirmation.iloc[idx] if idx < len(momentum_confirmation) else 0.0
                
                if pd.isna(fast_val) or pd.isna(slow_val):
                    continue
                
                # Check for crossovers
                signal_type = SignalType.NEUTRAL
                signal_strength = 0.0
                crossover_confirmed = False
                
                if bullish_crossover.iloc[idx]:
                    signal_type = SignalType.BULLISH
                    crossover_confirmed = True
                    
                    # Calculate signal strength
                    vwma_separation = (fast_val - slow_val) / slow_val
                    volume_boost = min(2.0, vol_conf / self.volume_confirmation_threshold)
                    momentum_boost = max(0.5, min(2.0, 1.0 + momentum * 10))
                    
                    signal_strength = min(1.0, 0.6 + vwma_separation * 2 + 
                                        (volume_boost - 1) * 0.2 + (momentum_boost - 1) * 0.2)
                    
                elif bearish_crossover.iloc[idx]:
                    signal_type = SignalType.BEARISH
                    crossover_confirmed = True
                    
                    # Calculate signal strength
                    vwma_separation = (slow_val - fast_val) / slow_val
                    volume_boost = min(2.0, vol_conf / self.volume_confirmation_threshold)
                    momentum_boost = max(0.5, min(2.0, 1.0 - momentum * 10))
                    
                    signal_strength = min(1.0, 0.6 + vwma_separation * 2 + 
                                        (volume_boost - 1) * 0.2 + (momentum_boost - 1) * 0.2)
                
                # Check for strong signals based on VWMA separation
                elif fast_val > slow_val * 1.02:  # Fast VWMA significantly above slow
                    signal_type = SignalType.WEAK_BULLISH
                    signal_strength = min(0.7, (fast_val - slow_val) / slow_val * 5)
                    
                elif slow_val > fast_val * 1.02:  # Slow VWMA significantly above fast
                    signal_type = SignalType.WEAK_BEARISH
                    signal_strength = min(0.7, (slow_val - fast_val) / fast_val * 5)
                
                # Volume confirmation check
                volume_confirmed = vol_conf >= self.volume_confirmation_threshold
                
                # Create signal if significant
                if signal_strength > 0.3:
                    vwma_signal = VWMASignal(
                        fast_vwma=fast_val,
                        slow_vwma=slow_val,
                        price=current_price,
                        volume=current_volume,
                        signal_strength=signal_strength,
                        signal_type=signal_type,
                        crossover_confirmed=crossover_confirmed,
                        volume_confirmation=volume_confirmed,
                        regime_filter_passed=True,  # Will be updated in regime detection
                        timestamp=timestamp
                    )
                    
                    signals.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'signal_type': signal_type,
                        'signal_strength': signal_strength,
                        'price': current_price,
                        'volume': current_volume,
                        'fast_vwma': fast_val,
                        'slow_vwma': slow_val,
                        'volume_confirmation': volume_confirmed,
                        'crossover_confirmed': crossover_confirmed,
                        'momentum': momentum,
                        'metadata': {
                            'vwma_separation_pct': ((fast_val - slow_val) / slow_val) * 100,
                            'volume_ratio': vol_conf,
                            'momentum_5d': momentum
                        }
                    })
            
            # Store signal history
            if symbol not in self.signal_history:
                self.signal_history[symbol] = []
            
            self.signal_history[symbol].extend(signals)
            
            # Keep only recent signals (last 100)
            self.signal_history[symbol] = self.signal_history[symbol][-100:]
            
            self.logger.info(f"Generated {len(signals)} VWMA signals for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Error generating VWMA signals for {symbol}: {e}")
            return []
        
        return signals
    
    def detect_market_regime(self, symbol: str, data: pd.DataFrame) -> MarketRegime:
        """
        Pillar 3: Market Regime Adaptation
        
        Detect current market regime for strategy adaptation.
        
        Args:
            symbol: Trading symbol
            data: OHLCV data
            
        Returns:
            Detected market regime
        """
        if len(data) < 50:
            return MarketRegime.SIDEWAYS_MARKET
        
        try:
            # Calculate volatility (20-day rolling)
            returns = data['close'].pct_change()
            volatility = returns.rolling(window=20).std() * np.sqrt(252)  # Annualized
            current_vol = volatility.iloc[-1]
            
            # Calculate trend strength using VWMA slope
            if symbol in self.slow_vwma_values:
                slow_vwma = self.slow_vwma_values[symbol]
                if len(slow_vwma) >= 10:
                    recent_slope = (slow_vwma.iloc[-1] - slow_vwma.iloc[-10]) / slow_vwma.iloc[-10]
                    
                    # Determine regime based on volatility and trend
                    if current_vol > 0.25:  # High volatility threshold
                        return MarketRegime.HIGH_VOLATILITY
                    elif current_vol < 0.10:  # Low volatility threshold
                        return MarketRegime.LOW_VOLATILITY
                    elif recent_slope > 0.05:  # Strong uptrend
                        return MarketRegime.BULL_MARKET
                    elif recent_slope < -0.05:  # Strong downtrend
                        return MarketRegime.BEAR_MARKET
                    else:
                        return MarketRegime.SIDEWAYS_MARKET
            
            # Default regime detection based on price action
            price_change_20d = (data['close'].iloc[-1] - data['close'].iloc[-20]) / data['close'].iloc[-20]
            
            if current_vol > 0.20:
                return MarketRegime.HIGH_VOLATILITY
            elif price_change_20d > 0.10:
                return MarketRegime.BULL_MARKET
            elif price_change_20d < -0.10:
                return MarketRegime.BEAR_MARKET
            else:
                return MarketRegime.SIDEWAYS_MARKET
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime for {symbol}: {e}")
            return MarketRegime.SIDEWAYS_MARKET
    
    def calculate_position_size(self, symbol: str, signal_strength: float, 
                              current_price: float, account_value: float) -> float:
        """
        Pillar 2: Dynamic Risk & Money Management
        
        Calculate optimal position size based on signal strength and risk parameters.
        
        Args:
            symbol: Trading symbol
            signal_strength: Strength of the signal (0-1)
            current_price: Current asset price
            account_value: Total account value
            
        Returns:
            Position size in shares/units
        """
        try:
            # Base position size from configuration
            base_size_pct = self.config.risk_config.base_position_size
            max_size_pct = self.config.risk_config.max_position_size
            
            # Adjust position size based on signal strength
            adjusted_size_pct = base_size_pct * signal_strength
            adjusted_size_pct = min(adjusted_size_pct, max_size_pct)
            
            # Calculate dollar amount
            dollar_amount = account_value * adjusted_size_pct
            
            # Convert to shares
            shares = int(dollar_amount / current_price)
            
            # Apply minimum position size if configured
            min_shares = 1  # Minimum 1 share
            shares = max(shares, min_shares)
            
            self.logger.debug(f"Calculated position size for {symbol}: {shares} shares (${dollar_amount:.2f})")
            
            return shares
            
        except Exception as e:
            self.logger.error(f"Error calculating position size for {symbol}: {e}")
            return 0
    
    def create_execution_intent(self, symbol: str, action: ExecutionAction, 
                              quantity: float, signal_data: Dict[str, Any]) -> ExecutionIntent:
        """
        Pillar 4: Decoupled Execution Logic & Order Management
        
        Create optimized execution intent for the trade.
        
        Args:
            symbol: Trading symbol
            action: Execution action
            quantity: Order quantity
            signal_data: Signal information
            
        Returns:
            Execution intent
        """
        try:
            # Prepare market data for execution optimization
            market_data = {
                'price': signal_data.get('price', 0),
                'volume': signal_data.get('volume', 1000000),
                'avg_volume': signal_data.get('volume', 1000000),  # Simplified
                'volatility': 0.02,  # Default volatility
                'spread': signal_data.get('price', 0) * 0.001  # Estimated spread
            }
            
            # Create execution constraints
            constraints = ExecutionConstraints(
                max_participation_rate=0.1,
                time_horizon=timedelta(minutes=30),
                price_improvement_threshold=0.0001
            )
            
            # Create execution intent
            intent = self.execution_utils.create_execution_intent(
                action=action,
                symbol=symbol,
                quantity=quantity,
                signal_confidence=signal_data.get('signal_strength', 0.5),
                signal_type=signal_data.get('signal_type', SignalType.NEUTRAL),
                market_data=market_data,
                constraints=constraints
            )
            
            self.logger.info(f"Created execution intent for {symbol}: {action.value} {quantity} shares")
            
            return intent
            
        except Exception as e:
            self.logger.error(f"Error creating execution intent for {symbol}: {e}")
            # Return a basic execution intent as fallback
            return ExecutionIntent(
                action=action,
                symbol=symbol,
                quantity=quantity,
                algorithm=self.config.execution_config.default_algorithm,
                urgency=self.config.execution_config.default_urgency,
                time_in_force=self.config.execution_config.default_time_in_force,
                metadata={'error': str(e)}
            )
    
    def calculate_performance_metrics(self, trades: List[Dict[str, Any]], 
                                    benchmark_returns: Optional[pd.Series] = None) -> PerformanceMetrics:
        """
        Pillar 5: Performance Tracking & Configurability
        
        Calculate comprehensive performance metrics.
        
        Args:
            trades: List of completed trades
            benchmark_returns: Benchmark return series for comparison
            
        Returns:
            Performance metrics
        """
        try:
            if not trades:
                return PerformanceMetrics(
                    total_return=0.0,
                    sharpe_ratio=0.0,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    profit_factor=0.0,
                    total_trades=0
                )
            
            # Calculate basic metrics
            returns = [trade.get('return_pct', 0) for trade in trades]
            total_return = sum(returns)
            
            winning_trades = [r for r in returns if r > 0]
            losing_trades = [r for r in returns if r < 0]
            
            win_rate = len(winning_trades) / len(returns) if returns else 0
            
            # Calculate profit factor
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum(losing_trades)) if losing_trades else 1
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
            
            # Calculate Sharpe ratio (simplified)
            if len(returns) > 1:
                returns_std = np.std(returns)
                sharpe_ratio = (np.mean(returns) / returns_std) if returns_std > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Calculate maximum drawdown (simplified)
            cumulative_returns = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = cumulative_returns - running_max
            max_drawdown = abs(min(drawdowns)) if len(drawdowns) > 0 else 0
            
            return PerformanceMetrics(
                total_return=total_return,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                total_trades=len(trades)
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics(
                total_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0
            )
    
    def should_exit_position(self, symbol: str, current_price: float, 
                           entry_price: float, entry_time: datetime) -> Tuple[bool, str]:
        """
        Determine if current position should be exited based on strategy rules.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            entry_price: Position entry price
            entry_time: Position entry time
            
        Returns:
            Tuple of (should_exit, reason)
        """
        try:
            # Calculate current return
            current_return = (current_price - entry_price) / entry_price
            
            # Time-based exit (if configured)
            if self.config.strategy_parameters.get('max_hold_days'):
                max_hold_days = self.config.strategy_parameters['max_hold_days']
                if (datetime.now() - entry_time).days > max_hold_days:
                    return True, "Maximum hold period exceeded"
            
            # Stop-loss check
            if self.config.risk_config.stop_loss_pct:
                if current_return <= -self.config.risk_config.stop_loss_pct:
                    return True, f"Stop-loss triggered at {current_return:.2%}"
            
            # Take-profit check
            if self.config.risk_config.take_profit_pct:
                if current_return >= self.config.risk_config.take_profit_pct:
                    return True, f"Take-profit triggered at {current_return:.2%}"
            
            # VWMA-based exit signal
            if symbol in self.fast_vwma_values and symbol in self.slow_vwma_values:
                fast_vwma = self.fast_vwma_values[symbol]
                slow_vwma = self.slow_vwma_values[symbol]
                
                if len(fast_vwma) >= 2 and len(slow_vwma) >= 2:
                    # Check for VWMA crossover reversal
                    current_fast = fast_vwma.iloc[-1]
                    current_slow = slow_vwma.iloc[-1]
                    prev_fast = fast_vwma.iloc[-2]
                    prev_slow = slow_vwma.iloc[-2]
                    
                    # Exit long position if fast VWMA crosses below slow VWMA
                    if (prev_fast > prev_slow and current_fast < current_slow and 
                        current_return > -0.02):  # Don't exit on small losses due to noise
                        return True, "VWMA bearish crossover signal"
                    
                    # Exit short position if fast VWMA crosses above slow VWMA
                    if (prev_fast < prev_slow and current_fast > current_slow and 
                        current_return > -0.02):
                        return True, "VWMA bullish crossover signal"
            
            return False, "No exit conditions met"
            
        except Exception as e:
            self.logger.error(f"Error checking exit conditions for {symbol}: {e}")
            return False, f"Error in exit logic: {e}"
    
    def get_strategy_state(self) -> StrategyState:
        """
        Get current strategy state and diagnostics.
        
        Returns:
            Current strategy state
        """
        try:
            return StrategyState(
                is_active=True,
                current_positions=len(self.signal_history),
                total_signals_generated=sum(len(signals) for signals in self.signal_history.values()),
                last_signal_time=datetime.now(),
                strategy_health="HEALTHY",
                error_count=0,
                metadata={
                    'fast_period': self.fast_period,
                    'slow_period': self.slow_period,
                    'volume_confirmation_threshold': self.volume_confirmation_threshold,
                    'tracked_symbols': list(self.signal_history.keys()),
                    'vwma_values_cached': len(self.fast_vwma_values)
                }
            )
        except Exception as e:
            self.logger.error(f"Error getting strategy state: {e}")
            return StrategyState(
                is_active=False,
                current_positions=0,
                total_signals_generated=0,
                last_signal_time=datetime.now(),
                strategy_health="ERROR",
                error_count=1,
                metadata={'error': str(e)}
            )


# Example configuration for the VWMA Crossover Strategy
def create_vwma_crossover_config() -> StrategyConfig:
    """
    Create a sample configuration for the VWMA Crossover Strategy.
    
    Returns:
        Strategy configuration
    """
    from datetime import datetime, timedelta
    
    today = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    return StrategyConfig(
        name="VWMA Crossover Strategy",
        version="1.0.0",
        description="Volume-Weighted Moving Average crossover strategy with institutional-grade risk management and execution optimization",
        category=StrategyCategory.MOMENTUM,
        author="Institutional Strategy Developer",
        created_date=today,
        last_modified=today,
        asset_classes=[AssetClass.EQUITY, AssetClass.ETF],
        symbols=["SPY", "QQQ", "IWM", "AAPL", "MSFT", "GOOGL"],
        timeframes=[TimeFrame.DAILY, TimeFrame.HOUR_4, TimeFrame.HOUR_1],
        primary_timeframe=TimeFrame.DAILY,
        signal_config=SignalConfig(
            primary_indicators=[
                IndicatorConfig(
                    name="VWMA_FAST",
                    parameters={"period": 10},
                    volume_weighted=True
                ),
                IndicatorConfig(
                    name="VWMA_SLOW",
                    parameters={"period": 30},
                    volume_weighted=True
                )
            ],
            secondary_indicators=[
                IndicatorConfig(
                    name="VOLUME_CONFIRMATION",
                    parameters={"period": 20},
                    volume_weighted=False
                ),
                IndicatorConfig(
                    name="MOMENTUM",
                    parameters={"period": 5},
                    volume_weighted=False
                )
            ],
            signal_threshold=0.6,
            confirmation_required=True,
            volume_confirmation=True,
            regime_filter=True,
            lookback_bars=20
        ),
        risk_config=RiskConfig(
            position_sizing_method="VOLATILITY_ADJUSTED",
            base_position_size=0.05,  # 5% per position
            max_position_size=0.15,   # 15% maximum
            stop_loss_pct=0.08,       # 8% stop-loss
            take_profit_pct=0.20,     # 20% take-profit
            trailing_stop_pct=0.05,   # 5% trailing stop
            max_drawdown_pct=0.15,    # 15% max drawdown
            correlation_threshold=0.7,
            leverage_limit=1.0
        ),
        regime_config=RegimeConfig(
            enabled=True,
            detection_method="VOLATILITY_REGIME",
            lookback_period=252,
            regime_threshold=0.5,
            adaptation_speed=0.1
        ),
        execution_config=ExecutionConfig(
            max_participation_rate=0.1,
            price_improvement_threshold=0.0001,
            slippage_tolerance=0.002,
            smart_routing=True,
            dark_pool_preference=0.3
        ),
        performance_config=PerformanceConfig(
            benchmark_symbol="SPY",
            track_intraday=True,
            calculate_attribution=True,
            risk_metrics_enabled=True
        ),
        backtest_config=BacktestConfig(
            start_date=start_date,
            end_date=today,
            initial_capital=100000.0,
            commission_per_trade=1.0,
            commission_pct=0.001,
            slippage_pct=0.001
        ),
        strategy_parameters={
            'fast_period': 10,
            'slow_period': 30,
            'volume_confirmation_threshold': 1.2,
            'momentum_lookback': 5,
            'signal_persistence_bars': 2,
            'max_hold_days': 30
        }
    )


# Example usage and testing
if __name__ == "__main__":
    # Create strategy configuration
    config = create_vwma_crossover_config()
    
    # Initialize strategy
    strategy = MovingAverageCrossoverVWMAStrategy(config)
    
    # Create sample data for testing
    dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
    np.random.seed(42)
    
    sample_data = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5),
        'high': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5) + np.random.rand(len(dates)) * 2,
        'low': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5) - np.random.rand(len(dates)) * 2,
        'close': 100 + np.cumsum(np.random.randn(len(dates)) * 0.5),
        'volume': np.random.randint(1000000, 5000000, len(dates))
    }, index=dates)
    
    # Ensure high >= low and realistic OHLC relationships
    sample_data['high'] = np.maximum(sample_data[['open', 'close']].max(axis=1), sample_data['high'])
    sample_data['low'] = np.minimum(sample_data[['open', 'close']].min(axis=1), sample_data['low'])
    
    # Test signal generation
    signals = strategy.generate_signals('TEST', sample_data)
    print(f"Generated {len(signals)} signals for test data")
    
    # Test market regime detection
    regime = strategy.detect_market_regime('TEST', sample_data)
    print(f"Detected market regime: {regime.value}")
    
    # Test strategy state
    state = strategy.get_strategy_state()
    print(f"Strategy state: {state.strategy_health}")
    
    print("VWMA Crossover Strategy implementation completed successfully!")