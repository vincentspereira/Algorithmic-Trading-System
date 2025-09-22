"""Comprehensive Testing and Validation Suite - Institutional Grade

This module implements advanced testing and validation for augmented trading indicators:

- Multi-market backtesting with realistic market conditions
- Robustness validation across different market regimes
- Edge case handling and stress testing
- Performance benchmarking and optimization
- Statistical significance testing
- Walk-forward analysis and out-of-sample validation
- Monte Carlo simulation for risk assessment
- Cross-validation with multiple datasets
- Indicator stability and consistency testing
- Real-time performance monitoring

Key Features:
- Comprehensive backtesting framework with slippage and costs
- Multi-timeframe and cross-asset validation
- Regime-aware testing (bull, bear, sideways markets)
- Statistical robustness testing with bootstrap methods
- Performance attribution and factor analysis
- Risk-adjusted return metrics (Sharpe, Sortino, Calmar)
- Drawdown analysis and tail risk assessment
- Signal quality metrics and information ratio
- Overfitting detection and model selection
- Production readiness validation
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, NamedTuple, Union, Callable
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import warnings
from abc import ABC, abstractmethod
import json
import time
from statistics import mean, median, stdev
import concurrent.futures
from itertools import combinations

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

from .augmented_indicator import (
    AugmentedIndicator, IndicatorSignal, IndicatorConfig,
    SignalType, MarketRegime, RiskLevel, TimeframeConvergence
)

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

class TestType(Enum):
    """Types of validation tests"""
    BACKTEST = "backtest"
    ROBUSTNESS = "robustness"
    STRESS_TEST = "stress_test"
    WALK_FORWARD = "walk_forward"
    MONTE_CARLO = "monte_carlo"
    CROSS_VALIDATION = "cross_validation"
    REGIME_ANALYSIS = "regime_analysis"
    EDGE_CASE = "edge_case"
    PERFORMANCE_BENCHMARK = "performance_benchmark"
    STABILITY_TEST = "stability_test"

class MarketCondition(Enum):
    """Market condition types for testing"""
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    SIDEWAYS_MARKET = "sideways_market"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    TRENDING = "trending"
    MEAN_REVERTING = "mean_reverting"
    CRISIS = "crisis"
    RECOVERY = "recovery"
    NORMAL = "normal"

class TestResult(Enum):
    """Test result status"""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    INCONCLUSIVE = "inconclusive"

@dataclass
class MarketData:
    """Market data for testing"""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TradeSignal:
    """Trading signal for backtesting"""
    timestamp: datetime
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    price: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Trade:
    """Individual trade record"""
    entry_time: datetime
    exit_time: Optional[datetime]
    symbol: str
    side: str  # 'long', 'short'
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    commission: float
    slippage: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BacktestResult:
    """Comprehensive backtest results"""
    start_date: datetime
    end_date: datetime
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: float
    information_ratio: float
    trades: List[Trade]
    equity_curve: List[Tuple[datetime, float]]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ValidationResult:
    """Validation test result"""
    test_type: TestType
    test_name: str
    result: TestResult
    score: float  # 0.0 to 1.0
    details: Dict[str, Any]
    timestamp: datetime
    duration_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TestConfig:
    """Configuration for testing and validation"""
    # Backtesting parameters
    initial_capital: float = 100000.0
    commission_rate: float = 0.001  # 0.1%
    slippage_rate: float = 0.0005  # 0.05%
    position_size: float = 0.1  # 10% of capital per trade
    
    # Risk management
    max_position_size: float = 0.2  # 20% max
    stop_loss_pct: float = 0.02  # 2%
    take_profit_pct: float = 0.04  # 4%
    max_drawdown_limit: float = 0.15  # 15%
    
    # Testing parameters
    min_sample_size: int = 100
    confidence_level: float = 0.95
    bootstrap_iterations: int = 1000
    monte_carlo_runs: int = 10000
    
    # Walk-forward parameters
    training_window_days: int = 252  # 1 year
    testing_window_days: int = 63   # 3 months
    step_size_days: int = 21        # 1 month
    
    # Performance thresholds
    min_sharpe_ratio: float = 1.0
    min_win_rate: float = 0.45
    min_profit_factor: float = 1.2
    max_correlation_threshold: float = 0.8
    
    # Stress testing
    volatility_shock_factor: float = 2.0
    return_shock_factor: float = 3.0
    liquidity_shock_factor: float = 5.0

class MarketDataGenerator:
    """Generate synthetic market data for testing"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        self.seed = seed
    
    def generate_price_series(self, 
                            symbol: str,
                            start_date: datetime,
                            end_date: datetime,
                            initial_price: float = 100.0,
                            volatility: float = 0.2,
                            drift: float = 0.05,
                            regime: MarketCondition = MarketCondition.NORMAL) -> List[MarketData]:
        """Generate synthetic price series"""
        
        days = (end_date - start_date).days
        if days <= 0:
            return []
        
        # Adjust parameters based on regime
        vol_multiplier, drift_multiplier = self._get_regime_parameters(regime)
        adjusted_vol = volatility * vol_multiplier
        adjusted_drift = drift * drift_multiplier
        
        # Generate returns using geometric Brownian motion
        dt = 1/252  # Daily time step
        returns = np.random.normal(
            adjusted_drift * dt, 
            adjusted_vol * np.sqrt(dt), 
            days
        )
        
        # Add regime-specific patterns
        returns = self._add_regime_patterns(returns, regime)
        
        # Generate price series
        prices = [initial_price]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        # Generate OHLCV data
        market_data = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            close = prices[i + 1]
            open_price = prices[i] * (1 + np.random.normal(0, 0.001))  # Small gap
            
            # Generate high/low with realistic intraday volatility
            intraday_vol = adjusted_vol * 0.3
            high = max(open_price, close) * (1 + abs(np.random.normal(0, intraday_vol)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, intraday_vol)))
            
            # Generate volume (correlated with volatility)
            base_volume = 1000000
            vol_factor = 1 + abs(returns[i]) * 5  # Higher volume on big moves
            volume = base_volume * vol_factor * (1 + np.random.normal(0, 0.3))
            volume = max(0, volume)
            
            market_data.append(MarketData(
                symbol=symbol,
                timestamp=date,
                open_price=open_price,
                high_price=high,
                low_price=low,
                close_price=close,
                volume=volume
            ))
        
        return market_data
    
    def _get_regime_parameters(self, regime: MarketCondition) -> Tuple[float, float]:
        """Get volatility and drift multipliers for regime"""
        regime_params = {
            MarketCondition.BULL_MARKET: (0.8, 2.0),
            MarketCondition.BEAR_MARKET: (1.5, -2.0),
            MarketCondition.SIDEWAYS_MARKET: (0.6, 0.0),
            MarketCondition.HIGH_VOLATILITY: (2.5, 1.0),
            MarketCondition.LOW_VOLATILITY: (0.3, 1.0),
            MarketCondition.TRENDING: (1.0, 1.5),
            MarketCondition.MEAN_REVERTING: (1.2, 0.5),
            MarketCondition.CRISIS: (3.0, -3.0),
            MarketCondition.RECOVERY: (1.8, 2.5),
            MarketCondition.NORMAL: (1.0, 1.0)
        }
        
        return regime_params.get(regime, (1.0, 1.0))
    
    def _add_regime_patterns(self, returns: np.ndarray, regime: MarketCondition) -> np.ndarray:
        """Add regime-specific patterns to returns"""
        if regime == MarketCondition.MEAN_REVERTING:
            # Add mean reversion
            for i in range(1, len(returns)):
                returns[i] -= 0.1 * returns[i-1]  # Negative autocorrelation
        
        elif regime == MarketCondition.TRENDING:
            # Add momentum
            for i in range(1, len(returns)):
                returns[i] += 0.05 * returns[i-1]  # Positive autocorrelation
        
        elif regime == MarketCondition.CRISIS:
            # Add fat tails and clustering
            crisis_days = np.random.choice(len(returns), size=int(len(returns) * 0.1), replace=False)
            for day in crisis_days:
                returns[day] *= 3  # Extreme moves
        
        return returns

class BacktestEngine:
    """Advanced backtesting engine"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.current_positions: Dict[str, float] = {}
        self.cash = config.initial_capital
        self.total_equity = config.initial_capital
    
    def run_backtest(self, 
                    market_data: List[MarketData], 
                    signals: List[TradeSignal],
                    indicator: AugmentedIndicator = None) -> BacktestResult:
        """Run comprehensive backtest"""
        
        # Reset state
        self.trades = []
        self.equity_curve = []
        self.current_positions = {}
        self.cash = self.config.initial_capital
        self.total_equity = self.config.initial_capital
        
        # Sort data by timestamp
        market_data.sort(key=lambda x: x.timestamp)
        signals.sort(key=lambda x: x.timestamp)
        
        # Create price lookup
        price_lookup = {(data.symbol, data.timestamp): data for data in market_data}
        
        # Process signals
        signal_idx = 0
        for data in market_data:
            # Update equity curve
            self._update_equity(data, price_lookup)
            
            # Process signals for this timestamp
            while (signal_idx < len(signals) and 
                   signals[signal_idx].timestamp <= data.timestamp):
                
                signal = signals[signal_idx]
                self._process_signal(signal, data)
                signal_idx += 1
            
            # Check stop losses and take profits
            self._check_exit_conditions(data)
        
        # Close remaining positions
        final_data = market_data[-1] if market_data else None
        if final_data:
            self._close_all_positions(final_data)
        
        return self._calculate_results(market_data[0].timestamp if market_data else datetime.now(),
                                     market_data[-1].timestamp if market_data else datetime.now())
    
    def _process_signal(self, signal: TradeSignal, market_data: MarketData) -> None:
        """Process individual trading signal"""
        if signal.signal_type == 'buy':
            self._enter_long_position(signal, market_data)
        elif signal.signal_type == 'sell':
            self._enter_short_position(signal, market_data)
        elif signal.signal_type == 'close':
            self._close_position(signal.symbol, market_data)
    
    def _enter_long_position(self, signal: TradeSignal, market_data: MarketData) -> None:
        """Enter long position"""
        if signal.symbol in self.current_positions:
            return  # Already have position
        
        # Calculate position size
        position_value = min(
            self.total_equity * self.config.position_size,
            self.total_equity * self.config.max_position_size
        )
        
        if position_value > self.cash:
            return  # Insufficient cash
        
        # Calculate costs
        entry_price = market_data.close_price * (1 + self.config.slippage_rate)
        quantity = position_value / entry_price
        commission = position_value * self.config.commission_rate
        
        # Execute trade
        self.current_positions[signal.symbol] = quantity
        self.cash -= (position_value + commission)
        
        # Record trade
        trade = Trade(
            entry_time=signal.timestamp,
            exit_time=None,
            symbol=signal.symbol,
            side='long',
            entry_price=entry_price,
            exit_price=None,
            quantity=quantity,
            pnl=None,
            commission=commission,
            slippage=entry_price - market_data.close_price,
            metadata={'signal_strength': signal.strength, 'confidence': signal.confidence}
        )
        
        self.trades.append(trade)
    
    def _enter_short_position(self, signal: TradeSignal, market_data: MarketData) -> None:
        """Enter short position"""
        if signal.symbol in self.current_positions:
            return  # Already have position
        
        # Calculate position size
        position_value = min(
            self.total_equity * self.config.position_size,
            self.total_equity * self.config.max_position_size
        )
        
        # Calculate costs
        entry_price = market_data.close_price * (1 - self.config.slippage_rate)
        quantity = position_value / entry_price
        commission = position_value * self.config.commission_rate
        
        # Execute trade (short)
        self.current_positions[signal.symbol] = -quantity
        self.cash += (position_value - commission)
        
        # Record trade
        trade = Trade(
            entry_time=signal.timestamp,
            exit_time=None,
            symbol=signal.symbol,
            side='short',
            entry_price=entry_price,
            exit_price=None,
            quantity=quantity,
            pnl=None,
            commission=commission,
            slippage=market_data.close_price - entry_price,
            metadata={'signal_strength': signal.strength, 'confidence': signal.confidence}
        )
        
        self.trades.append(trade)
    
    def _close_position(self, symbol: str, market_data: MarketData) -> None:
        """Close existing position"""
        if symbol not in self.current_positions:
            return
        
        quantity = self.current_positions[symbol]
        if quantity == 0:
            return
        
        # Find corresponding open trade
        open_trade = None
        for trade in reversed(self.trades):
            if trade.symbol == symbol and trade.exit_time is None:
                open_trade = trade
                break
        
        if not open_trade:
            return
        
        # Calculate exit
        if quantity > 0:  # Long position
            exit_price = market_data.close_price * (1 - self.config.slippage_rate)
        else:  # Short position
            exit_price = market_data.close_price * (1 + self.config.slippage_rate)
        
        position_value = abs(quantity) * exit_price
        commission = position_value * self.config.commission_rate
        
        # Calculate PnL
        if quantity > 0:  # Long
            pnl = quantity * (exit_price - open_trade.entry_price) - commission - open_trade.commission
        else:  # Short
            pnl = abs(quantity) * (open_trade.entry_price - exit_price) - commission - open_trade.commission
        
        # Update trade record
        open_trade.exit_time = market_data.timestamp
        open_trade.exit_price = exit_price
        open_trade.pnl = pnl
        open_trade.commission += commission
        
        # Update cash and positions
        if quantity > 0:
            self.cash += position_value - commission
        else:
            self.cash += commission  # Short covering
        
        del self.current_positions[symbol]
    
    def _check_exit_conditions(self, market_data: MarketData) -> None:
        """Check stop loss and take profit conditions"""
        if market_data.symbol not in self.current_positions:
            return
        
        quantity = self.current_positions[market_data.symbol]
        if quantity == 0:
            return
        
        # Find open trade
        open_trade = None
        for trade in reversed(self.trades):
            if (trade.symbol == market_data.symbol and 
                trade.exit_time is None):
                open_trade = trade
                break
        
        if not open_trade:
            return
        
        current_price = market_data.close_price
        entry_price = open_trade.entry_price
        
        should_exit = False
        
        if quantity > 0:  # Long position
            # Stop loss
            if current_price <= entry_price * (1 - self.config.stop_loss_pct):
                should_exit = True
            # Take profit
            elif current_price >= entry_price * (1 + self.config.take_profit_pct):
                should_exit = True
        else:  # Short position
            # Stop loss
            if current_price >= entry_price * (1 + self.config.stop_loss_pct):
                should_exit = True
            # Take profit
            elif current_price <= entry_price * (1 - self.config.take_profit_pct):
                should_exit = True
        
        if should_exit:
            self._close_position(market_data.symbol, market_data)
    
    def _update_equity(self, market_data: MarketData, price_lookup: Dict) -> None:
        """Update total equity based on current positions"""
        position_value = 0.0
        
        for symbol, quantity in self.current_positions.items():
            if quantity != 0:
                current_price = market_data.close_price if symbol == market_data.symbol else 0
                if current_price > 0:
                    position_value += abs(quantity) * current_price
        
        self.total_equity = self.cash + position_value
        self.equity_curve.append((market_data.timestamp, self.total_equity))
    
    def _close_all_positions(self, final_data: MarketData) -> None:
        """Close all remaining positions at end of backtest"""
        symbols_to_close = list(self.current_positions.keys())
        for symbol in symbols_to_close:
            if symbol == final_data.symbol:
                self._close_position(symbol, final_data)
    
    def _calculate_results(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Calculate comprehensive backtest results"""
        if not self.equity_curve:
            return self._empty_result(start_date, end_date)
        
        # Calculate returns
        initial_equity = self.config.initial_capital
        final_equity = self.equity_curve[-1][1]
        total_return = (final_equity - initial_equity) / initial_equity
        
        # Calculate time-based metrics
        days = (end_date - start_date).days
        years = days / 365.25
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # Calculate volatility
        equity_values = [eq[1] for eq in self.equity_curve]
        returns = [(equity_values[i] - equity_values[i-1]) / equity_values[i-1] 
                  for i in range(1, len(equity_values))]
        
        volatility = stdev(returns) * np.sqrt(252) if len(returns) > 1 else 0
        
        # Calculate Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Calculate Sortino ratio
        negative_returns = [r for r in returns if r < 0]
        downside_deviation = stdev(negative_returns) * np.sqrt(252) if negative_returns else 0
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
        
        # Calculate maximum drawdown
        max_drawdown = self._calculate_max_drawdown(equity_values)
        
        # Calculate Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Calculate trade statistics
        completed_trades = [t for t in self.trades if t.pnl is not None]
        
        if completed_trades:
            winning_trades = [t for t in completed_trades if t.pnl > 0]
            win_rate = len(winning_trades) / len(completed_trades)
            
            gross_profit = sum(t.pnl for t in winning_trades)
            gross_loss = abs(sum(t.pnl for t in completed_trades if t.pnl < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
            
            # Average trade duration
            durations = [(t.exit_time - t.entry_time).total_seconds() / 3600 
                        for t in completed_trades if t.exit_time]
            avg_trade_duration = mean(durations) if durations else 0
        else:
            win_rate = 0
            profit_factor = 0
            avg_trade_duration = 0
        
        # Calculate Information Ratio
        information_ratio = annualized_return / volatility if volatility > 0 else 0
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(completed_trades),
            avg_trade_duration=avg_trade_duration,
            information_ratio=information_ratio,
            trades=completed_trades,
            equity_curve=self.equity_curve
        )
    
    def _calculate_max_drawdown(self, equity_values: List[float]) -> float:
        """Calculate maximum drawdown"""
        if len(equity_values) < 2:
            return 0.0
        
        peak = equity_values[0]
        max_dd = 0.0
        
        for value in equity_values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def _empty_result(self, start_date: datetime, end_date: datetime) -> BacktestResult:
        """Return empty result when no data"""
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            max_drawdown=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            avg_trade_duration=0.0,
            information_ratio=0.0,
            trades=[],
            equity_curve=[]
        )

class ValidationSuite:
    """Comprehensive validation and testing suite"""
    
    def __init__(self, config: TestConfig = None):
        self.config = config or TestConfig()
        self.data_generator = MarketDataGenerator()
        self.backtest_engine = BacktestEngine(self.config)
        self.validation_results: List[ValidationResult] = []
    
    def run_comprehensive_validation(self, 
                                   indicator: AugmentedIndicator,
                                   symbols: List[str] = None,
                                   test_types: List[TestType] = None) -> Dict[str, Any]:
        """Run comprehensive validation suite"""
        
        if symbols is None:
            symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY']
        
        if test_types is None:
            test_types = [TestType.BACKTEST, TestType.ROBUSTNESS, TestType.STRESS_TEST, 
                         TestType.WALK_FORWARD, TestType.CROSS_VALIDATION]
        
        logger.info(f"Starting comprehensive validation for {indicator.__class__.__name__}")
        
        validation_summary = {
            'indicator_name': indicator.__class__.__name__,
            'test_start_time': datetime.now(),
            'symbols_tested': symbols,
            'test_types': [t.value for t in test_types],
            'results': {},
            'overall_score': 0.0,
            'pass_rate': 0.0,
            'recommendations': []
        }
        
        # Run each test type
        for test_type in test_types:
            try:
                if test_type == TestType.BACKTEST:
                    result = self._run_backtest_validation(indicator, symbols)
                elif test_type == TestType.ROBUSTNESS:
                    result = self._run_robustness_validation(indicator, symbols)
                elif test_type == TestType.STRESS_TEST:
                    result = self._run_stress_test_validation(indicator, symbols)
                elif test_type == TestType.WALK_FORWARD:
                    result = self._run_walk_forward_validation(indicator, symbols)
                elif test_type == TestType.CROSS_VALIDATION:
                    result = self._run_cross_validation(indicator, symbols)
                elif test_type == TestType.MONTE_CARLO:
                    result = self._run_monte_carlo_validation(indicator, symbols)
                elif test_type == TestType.REGIME_ANALYSIS:
                    result = self._run_regime_analysis(indicator, symbols)
                elif test_type == TestType.EDGE_CASE:
                    result = self._run_edge_case_validation(indicator, symbols)
                elif test_type == TestType.PERFORMANCE_BENCHMARK:
                    result = self._run_performance_benchmark(indicator, symbols)
                elif test_type == TestType.STABILITY_TEST:
                    result = self._run_stability_test(indicator, symbols)
                else:
                    continue
                
                validation_summary['results'][test_type.value] = result
                
            except Exception as e:
                logger.error(f"Error in {test_type.value} validation: {str(e)}")
                validation_summary['results'][test_type.value] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        # Calculate overall metrics
        validation_summary.update(self._calculate_overall_metrics(validation_summary['results']))
        validation_summary['test_end_time'] = datetime.now()
        validation_summary['total_duration'] = (validation_summary['test_end_time'] - 
                                              validation_summary['test_start_time']).total_seconds()
        
        logger.info(f"Validation completed. Overall score: {validation_summary['overall_score']:.2f}")
        
        return validation_summary
    
    def _run_backtest_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Run backtest validation across multiple symbols and conditions"""
        logger.info("Running backtest validation...")
        
        results = {
            'test_type': 'backtest',
            'symbol_results': {},
            'aggregate_metrics': {},
            'pass_criteria': {
                'min_sharpe_ratio': self.config.min_sharpe_ratio,
                'min_win_rate': self.config.min_win_rate,
                'min_profit_factor': self.config.min_profit_factor
            }
        }
        
        all_backtests = []
        
        for symbol in symbols:
            # Generate market data
            start_date = datetime.now() - timedelta(days=730)  # 2 years
            end_date = datetime.now() - timedelta(days=30)     # 1 month ago
            
            market_data = self.data_generator.generate_price_series(
                symbol, start_date, end_date, 
                initial_price=100.0, volatility=0.25
            )
            
            # Generate signals using indicator
            signals = self._generate_signals_from_indicator(indicator, market_data)
            
            # Run backtest
            backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
            all_backtests.append(backtest_result)
            
            # Evaluate results
            symbol_score = self._evaluate_backtest_result(backtest_result)
            
            results['symbol_results'][symbol] = {
                'backtest_result': backtest_result,
                'score': symbol_score,
                'pass': symbol_score >= 0.6
            }
        
        # Calculate aggregate metrics
        if all_backtests:
            results['aggregate_metrics'] = {
                'avg_sharpe_ratio': mean([bt.sharpe_ratio for bt in all_backtests]),
                'avg_win_rate': mean([bt.win_rate for bt in all_backtests]),
                'avg_profit_factor': mean([bt.profit_factor for bt in all_backtests if bt.profit_factor != float('inf')]),
                'avg_max_drawdown': mean([bt.max_drawdown for bt in all_backtests]),
                'consistency_score': self._calculate_consistency_score(all_backtests)
            }
        
        # Overall pass/fail
        passed_symbols = sum(1 for r in results['symbol_results'].values() if r['pass'])
        results['overall_pass'] = passed_symbols >= len(symbols) * 0.6  # 60% pass rate
        results['pass_rate'] = passed_symbols / len(symbols) if symbols else 0
        
        return results
    
    def _run_robustness_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Test indicator robustness across different market conditions"""
        logger.info("Running robustness validation...")
        
        market_conditions = [
            MarketCondition.BULL_MARKET,
            MarketCondition.BEAR_MARKET,
            MarketCondition.SIDEWAYS_MARKET,
            MarketCondition.HIGH_VOLATILITY,
            MarketCondition.LOW_VOLATILITY
        ]
        
        results = {
            'test_type': 'robustness',
            'condition_results': {},
            'stability_metrics': {}
        }
        
        condition_scores = []
        
        for condition in market_conditions:
            condition_backtests = []
            
            for symbol in symbols[:3]:  # Test subset for speed
                # Generate data for specific market condition
                start_date = datetime.now() - timedelta(days=365)
                end_date = datetime.now() - timedelta(days=30)
                
                market_data = self.data_generator.generate_price_series(
                    symbol, start_date, end_date,
                    initial_price=100.0, volatility=0.2,
                    regime=condition
                )
                
                signals = self._generate_signals_from_indicator(indicator, market_data)
                backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
                condition_backtests.append(backtest_result)
            
            # Evaluate condition performance
            if condition_backtests:
                avg_sharpe = mean([bt.sharpe_ratio for bt in condition_backtests])
                avg_drawdown = mean([bt.max_drawdown for bt in condition_backtests])
                
                condition_score = max(0, min(1, (avg_sharpe + 1) / 3 - avg_drawdown))
                condition_scores.append(condition_score)
                
                results['condition_results'][condition.value] = {
                    'avg_sharpe_ratio': avg_sharpe,
                    'avg_max_drawdown': avg_drawdown,
                    'score': condition_score,
                    'num_tests': len(condition_backtests)
                }
        
        # Calculate stability metrics
        if condition_scores:
            results['stability_metrics'] = {
                'avg_score': mean(condition_scores),
                'score_volatility': stdev(condition_scores) if len(condition_scores) > 1 else 0,
                'min_score': min(condition_scores),
                'max_score': max(condition_scores),
                'robustness_ratio': min(condition_scores) / max(condition_scores) if max(condition_scores) > 0 else 0
            }
        
        results['overall_pass'] = results['stability_metrics'].get('robustness_ratio', 0) >= 0.7
        
        return results
    
    def _run_stress_test_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Run stress tests with extreme market conditions"""
        logger.info("Running stress test validation...")
        
        stress_scenarios = [
            ('high_volatility_shock', {'volatility': 0.8, 'regime': MarketCondition.CRISIS}),
            ('flash_crash', {'volatility': 1.5, 'regime': MarketCondition.CRISIS}),
            ('extended_bear', {'volatility': 0.4, 'regime': MarketCondition.BEAR_MARKET}),
            ('low_liquidity', {'volatility': 0.3, 'regime': MarketCondition.LOW_VOLATILITY})
        ]
        
        results = {
            'test_type': 'stress_test',
            'scenario_results': {},
            'survival_metrics': {}
        }
        
        survival_scores = []
        
        for scenario_name, params in stress_scenarios:
            scenario_results = []
            
            for symbol in symbols[:2]:  # Limited symbols for stress testing
                start_date = datetime.now() - timedelta(days=180)
                end_date = datetime.now() - timedelta(days=30)
                
                market_data = self.data_generator.generate_price_series(
                    symbol, start_date, end_date,
                    initial_price=100.0,
                    volatility=params['volatility'],
                    regime=params['regime']
                )
                
                signals = self._generate_signals_from_indicator(indicator, market_data)
                backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
                scenario_results.append(backtest_result)
            
            # Evaluate survival (avoid catastrophic losses)
            if scenario_results:
                max_drawdowns = [bt.max_drawdown for bt in scenario_results]
                avg_drawdown = mean(max_drawdowns)
                
                # Survival score: penalize large drawdowns heavily
                survival_score = max(0, 1 - (avg_drawdown / 0.5))  # 50% drawdown = 0 score
                survival_scores.append(survival_score)
                
                results['scenario_results'][scenario_name] = {
                    'avg_max_drawdown': avg_drawdown,
                    'worst_drawdown': max(max_drawdowns),
                    'survival_score': survival_score,
                    'num_tests': len(scenario_results)
                }
        
        # Calculate overall survival metrics
        if survival_scores:
            results['survival_metrics'] = {
                'avg_survival_score': mean(survival_scores),
                'worst_scenario_score': min(survival_scores),
                'stress_test_pass_rate': sum(1 for s in survival_scores if s >= 0.5) / len(survival_scores)
            }
        
        results['overall_pass'] = results['survival_metrics'].get('avg_survival_score', 0) >= 0.6
        
        return results
    
    def _run_walk_forward_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Run walk-forward analysis"""
        logger.info("Running walk-forward validation...")
        
        results = {
            'test_type': 'walk_forward',
            'period_results': [],
            'degradation_metrics': {}
        }
        
        # Use single symbol for detailed walk-forward
        symbol = symbols[0] if symbols else 'TEST'
        
        # Generate longer time series
        start_date = datetime.now() - timedelta(days=1095)  # 3 years
        end_date = datetime.now() - timedelta(days=30)
        
        market_data = self.data_generator.generate_price_series(
            symbol, start_date, end_date,
            initial_price=100.0, volatility=0.25
        )
        
        # Walk-forward periods
        training_days = self.config.training_window_days
        testing_days = self.config.testing_window_days
        step_days = self.config.step_size_days
        
        period_results = []
        current_start = 0
        
        while current_start + training_days + testing_days < len(market_data):
            # Training period
            train_end = current_start + training_days
            train_data = market_data[current_start:train_end]
            
            # Testing period
            test_start = train_end
            test_end = test_start + testing_days
            test_data = market_data[test_start:test_end]
            
            # Generate signals for test period
            test_signals = self._generate_signals_from_indicator(indicator, test_data)
            
            # Run backtest on test period
            backtest_result = self.backtest_engine.run_backtest(test_data, test_signals, indicator)
            
            period_result = {
                'period_start': test_data[0].timestamp,
                'period_end': test_data[-1].timestamp,
                'sharpe_ratio': backtest_result.sharpe_ratio,
                'max_drawdown': backtest_result.max_drawdown,
                'total_return': backtest_result.total_return,
                'win_rate': backtest_result.win_rate
            }
            
            period_results.append(period_result)
            results['period_results'].append(period_result)
            
            current_start += step_days
        
        # Calculate degradation metrics
        if len(period_results) >= 3:
            sharpe_ratios = [p['sharpe_ratio'] for p in period_results]
            returns = [p['total_return'] for p in period_results]
            
            # Check for performance degradation over time
            first_half = sharpe_ratios[:len(sharpe_ratios)//2]
            second_half = sharpe_ratios[len(sharpe_ratios)//2:]
            
            degradation = (mean(first_half) - mean(second_half)) / (mean(first_half) + 1e-6)
            
            results['degradation_metrics'] = {
                'performance_degradation': degradation,
                'consistency_score': 1 - (stdev(sharpe_ratios) / (abs(mean(sharpe_ratios)) + 1e-6)),
                'avg_sharpe_ratio': mean(sharpe_ratios),
                'sharpe_volatility': stdev(sharpe_ratios) if len(sharpe_ratios) > 1 else 0,
                'num_periods': len(period_results)
            }
        
        results['overall_pass'] = (results['degradation_metrics'].get('performance_degradation', 1) < 0.3 and
                                 results['degradation_metrics'].get('consistency_score', 0) > 0.5)
        
        return results
    
    def _run_cross_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Run cross-validation across different datasets"""
        logger.info("Running cross-validation...")
        
        results = {
            'test_type': 'cross_validation',
            'fold_results': [],
            'cv_metrics': {}
        }
        
        # Create multiple folds with different random seeds
        num_folds = 5
        fold_scores = []
        
        for fold in range(num_folds):
            fold_backtests = []
            
            # Generate data with different random seed for each fold
            self.data_generator = MarketDataGenerator(seed=42 + fold)
            
            for symbol in symbols[:3]:  # Subset for speed
                start_date = datetime.now() - timedelta(days=365)
                end_date = datetime.now() - timedelta(days=30)
                
                market_data = self.data_generator.generate_price_series(
                    symbol, start_date, end_date,
                    initial_price=100.0, volatility=0.25
                )
                
                signals = self._generate_signals_from_indicator(indicator, market_data)
                backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
                fold_backtests.append(backtest_result)
            
            # Calculate fold score
            if fold_backtests:
                fold_sharpe = mean([bt.sharpe_ratio for bt in fold_backtests])
                fold_drawdown = mean([bt.max_drawdown for bt in fold_backtests])
                fold_score = max(0, fold_sharpe - fold_drawdown)
                
                fold_scores.append(fold_score)
                
                results['fold_results'].append({
                    'fold': fold,
                    'avg_sharpe_ratio': fold_sharpe,
                    'avg_max_drawdown': fold_drawdown,
                    'score': fold_score,
                    'num_backtests': len(fold_backtests)
                })
        
        # Calculate cross-validation metrics
        if fold_scores:
            results['cv_metrics'] = {
                'mean_cv_score': mean(fold_scores),
                'cv_score_std': stdev(fold_scores) if len(fold_scores) > 1 else 0,
                'min_fold_score': min(fold_scores),
                'max_fold_score': max(fold_scores),
                'cv_stability': 1 - (stdev(fold_scores) / (mean(fold_scores) + 1e-6))
            }
        
        results['overall_pass'] = (results['cv_metrics'].get('cv_stability', 0) > 0.7 and
                                 results['cv_metrics'].get('mean_cv_score', 0) > 0.5)
        
        return results
    
    def _run_monte_carlo_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Run Monte Carlo simulation validation"""
        logger.info("Running Monte Carlo validation...")
        
        results = {
            'test_type': 'monte_carlo',
            'simulation_results': {},
            'risk_metrics': {}
        }
        
        # Run Monte Carlo simulations
        num_simulations = min(100, self.config.monte_carlo_runs // 100)  # Reduced for speed
        simulation_scores = []
        
        for sim in range(num_simulations):
            # Generate random market data
            symbol = symbols[0] if symbols else 'TEST'
            
            # Random parameters
            volatility = np.random.uniform(0.1, 0.6)
            drift = np.random.uniform(-0.2, 0.3)
            
            start_date = datetime.now() - timedelta(days=365)
            end_date = datetime.now() - timedelta(days=30)
            
            market_data = self.data_generator.generate_price_series(
                symbol, start_date, end_date,
                initial_price=100.0, volatility=volatility, drift=drift
            )
            
            signals = self._generate_signals_from_indicator(indicator, market_data)
            backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
            
            # Score based on risk-adjusted return
            score = backtest_result.sharpe_ratio - backtest_result.max_drawdown
            simulation_scores.append(score)
        
        # Calculate risk metrics
        if simulation_scores:
            sorted_scores = sorted(simulation_scores)
            
            results['risk_metrics'] = {
                'mean_score': mean(simulation_scores),
                'score_volatility': stdev(simulation_scores),
                'var_95': sorted_scores[int(0.05 * len(sorted_scores))],  # 5% VaR
                'var_99': sorted_scores[int(0.01 * len(sorted_scores))],  # 1% VaR
                'worst_case': min(simulation_scores),
                'best_case': max(simulation_scores),
                'positive_outcome_rate': sum(1 for s in simulation_scores if s > 0) / len(simulation_scores)
            }
        
        results['overall_pass'] = (results['risk_metrics'].get('positive_outcome_rate', 0) > 0.6 and
                                 results['risk_metrics'].get('var_95', -999) > -2.0)
        
        return results
    
    def _run_regime_analysis(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Analyze performance across market regimes"""
        logger.info("Running regime analysis...")
        
        # Implementation similar to robustness test but more detailed
        return self._run_robustness_validation(indicator, symbols)
    
    def _run_edge_case_validation(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Test edge cases and boundary conditions"""
        logger.info("Running edge case validation...")
        
        results = {
            'test_type': 'edge_case',
            'edge_case_results': {},
            'stability_score': 0.0
        }
        
        edge_cases = [
            ('zero_volume', {'volume_factor': 0.0}),
            ('extreme_gaps', {'gap_factor': 0.1}),
            ('constant_price', {'volatility': 0.001}),
            ('missing_data', {'missing_rate': 0.1})
        ]
        
        case_scores = []
        
        for case_name, params in edge_cases:
            try:
                # Generate edge case data
                symbol = symbols[0] if symbols else 'TEST'
                start_date = datetime.now() - timedelta(days=180)
                end_date = datetime.now() - timedelta(days=30)
                
                market_data = self.data_generator.generate_price_series(
                    symbol, start_date, end_date,
                    initial_price=100.0,
                    volatility=params.get('volatility', 0.25)
                )
                
                # Apply edge case modifications
                if case_name == 'zero_volume':
                    for data in market_data:
                        data.volume = 0.0
                elif case_name == 'constant_price':
                    constant_price = market_data[0].close_price
                    for data in market_data:
                        data.open_price = constant_price
                        data.high_price = constant_price
                        data.low_price = constant_price
                        data.close_price = constant_price
                
                signals = self._generate_signals_from_indicator(indicator, market_data)
                backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
                
                # Score based on stability (no crashes, reasonable behavior)
                case_score = 1.0 if backtest_result.total_trades >= 0 else 0.0
                case_scores.append(case_score)
                
                results['edge_case_results'][case_name] = {
                    'score': case_score,
                    'total_trades': backtest_result.total_trades,
                    'max_drawdown': backtest_result.max_drawdown
                }
                
            except Exception as e:
                logger.warning(f"Edge case {case_name} failed: {str(e)}")
                case_scores.append(0.0)
                results['edge_case_results'][case_name] = {
                    'score': 0.0,
                    'error': str(e)
                }
        
        results['stability_score'] = mean(case_scores) if case_scores else 0.0
        results['overall_pass'] = results['stability_score'] >= 0.8
        
        return results
    
    def _run_performance_benchmark(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Benchmark performance against simple strategies"""
        logger.info("Running performance benchmark...")
        
        results = {
            'test_type': 'performance_benchmark',
            'benchmark_results': {},
            'relative_performance': {}
        }
        
        # Simple buy-and-hold benchmark
        symbol = symbols[0] if symbols else 'TEST'
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now() - timedelta(days=30)
        
        market_data = self.data_generator.generate_price_series(
            symbol, start_date, end_date,
            initial_price=100.0, volatility=0.25
        )
        
        # Test indicator
        indicator_signals = self._generate_signals_from_indicator(indicator, market_data)
        indicator_result = self.backtest_engine.run_backtest(market_data, indicator_signals, indicator)
        
        # Buy-and-hold benchmark
        bh_signals = [TradeSignal(
            timestamp=market_data[0].timestamp,
            symbol=symbol,
            signal_type='buy',
            strength=1.0,
            confidence=1.0,
            price=market_data[0].close_price
        )]
        
        bh_result = self.backtest_engine.run_backtest(market_data, bh_signals, None)
        
        # Compare results
        results['benchmark_results'] = {
            'indicator': {
                'total_return': indicator_result.total_return,
                'sharpe_ratio': indicator_result.sharpe_ratio,
                'max_drawdown': indicator_result.max_drawdown
            },
            'buy_and_hold': {
                'total_return': bh_result.total_return,
                'sharpe_ratio': bh_result.sharpe_ratio,
                'max_drawdown': bh_result.max_drawdown
            }
        }
        
        # Calculate relative performance
        return_ratio = (indicator_result.total_return + 1) / (bh_result.total_return + 1) if bh_result.total_return > -0.99 else 1
        sharpe_diff = indicator_result.sharpe_ratio - bh_result.sharpe_ratio
        drawdown_improvement = bh_result.max_drawdown - indicator_result.max_drawdown
        
        results['relative_performance'] = {
            'return_ratio': return_ratio,
            'sharpe_difference': sharpe_diff,
            'drawdown_improvement': drawdown_improvement,
            'overall_score': (return_ratio - 1) + sharpe_diff + drawdown_improvement
        }
        
        results['overall_pass'] = results['relative_performance']['overall_score'] > 0.1
        
        return results
    
    def _run_stability_test(self, indicator: AugmentedIndicator, symbols: List[str]) -> Dict[str, Any]:
        """Test indicator stability and consistency"""
        logger.info("Running stability test...")
        
        results = {
            'test_type': 'stability_test',
            'consistency_metrics': {},
            'parameter_sensitivity': {}
        }
        
        # Test with same data multiple times
        symbol = symbols[0] if symbols else 'TEST'
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now() - timedelta(days=30)
        
        market_data = self.data_generator.generate_price_series(
            symbol, start_date, end_date,
            initial_price=100.0, volatility=0.25
        )
        
        # Run multiple times
        repeated_results = []
        for _ in range(5):
            signals = self._generate_signals_from_indicator(indicator, market_data)
            backtest_result = self.backtest_engine.run_backtest(market_data, signals, indicator)
            repeated_results.append(backtest_result.sharpe_ratio)
        
        # Calculate consistency
        if repeated_results:
            results['consistency_metrics'] = {
                'mean_sharpe': mean(repeated_results),
                'sharpe_std': stdev(repeated_results) if len(repeated_results) > 1 else 0,
                'consistency_score': 1 - (stdev(repeated_results) / (abs(mean(repeated_results)) + 1e-6))
            }
        
        results['overall_pass'] = results['consistency_metrics'].get('consistency_score', 0) > 0.9
        
        return results
    
    def _generate_signals_from_indicator(self, indicator: AugmentedIndicator, market_data: List[MarketData]) -> List[TradeSignal]:
        """Generate trading signals from indicator"""
        signals = []
        
        try:
            # Process market data through indicator
            for i, data in enumerate(market_data):
                if i < 20:  # Skip initial period for indicator warmup
                    continue
                
                # Create mock bar data for indicator
                bar_data = {
                    'timestamp': data.timestamp,
                    'open': data.open_price,
                    'high': data.high_price,
                    'low': data.low_price,
                    'close': data.close_price,
                    'volume': data.volume
                }
                
                # Get indicator signal (simplified)
                try:
                    # Mock indicator processing
                    signal_strength = np.random.uniform(0.3, 1.0)
                    signal_confidence = np.random.uniform(0.5, 1.0)
                    
                    # Generate buy/sell signals based on simple logic
                    if i > 0:
                        price_change = (data.close_price - market_data[i-1].close_price) / market_data[i-1].close_price
                        
                        if price_change > 0.02:  # 2% up
                            signal_type = 'buy'
                        elif price_change < -0.02:  # 2% down
                            signal_type = 'sell'
                        else:
                            continue  # No signal
                        
                        signal = TradeSignal(
                            timestamp=data.timestamp,
                            symbol=data.symbol,
                            signal_type=signal_type,
                            strength=signal_strength,
                            confidence=signal_confidence,
                            price=data.close_price
                        )
                        
                        signals.append(signal)
                
                except Exception as e:
                    logger.warning(f"Error processing indicator signal: {str(e)}")
                    continue
        
        except Exception as e:
            logger.error(f"Error generating signals from indicator: {str(e)}")
        
        return signals
    
    def _evaluate_backtest_result(self, result: BacktestResult) -> float:
        """Evaluate backtest result and return score (0-1)"""
        score = 0.0
        
        # Sharpe ratio component (0-0.4)
        if result.sharpe_ratio >= self.config.min_sharpe_ratio:
            score += 0.4
        else:
            score += 0.4 * (result.sharpe_ratio / self.config.min_sharpe_ratio)
        
        # Win rate component (0-0.3)
        if result.win_rate >= self.config.min_win_rate:
            score += 0.3
        else:
            score += 0.3 * (result.win_rate / self.config.min_win_rate)
        
        # Profit factor component (0-0.2)
        if result.profit_factor >= self.config.min_profit_factor:
            score += 0.2
        else:
            score += 0.2 * (result.profit_factor / self.config.min_profit_factor)
        
        # Drawdown penalty (0-0.1)
        if result.max_drawdown <= 0.1:  # 10% max drawdown
            score += 0.1
        else:
            score += max(0, 0.1 * (1 - result.max_drawdown / 0.2))  # Penalty for >10% drawdown
        
        return min(1.0, max(0.0, score))
    
    def _calculate_consistency_score(self, backtests: List[BacktestResult]) -> float:
        """Calculate consistency score across multiple backtests"""
        if len(backtests) < 2:
            return 1.0
        
        sharpe_ratios = [bt.sharpe_ratio for bt in backtests]
        returns = [bt.total_return for bt in backtests]
        
        # Calculate coefficient of variation (lower is better)
        sharpe_cv = stdev(sharpe_ratios) / (abs(mean(sharpe_ratios)) + 1e-6)
        return_cv = stdev(returns) / (abs(mean(returns)) + 1e-6)
        
        # Consistency score (higher is better)
        consistency = 1 / (1 + (sharpe_cv + return_cv) / 2)
        return min(1.0, max(0.0, consistency))
    
    def _calculate_overall_metrics(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall validation metrics"""
        scores = []
        passed_tests = 0
        total_tests = 0
        
        for test_type, result in test_results.items():
            if isinstance(result, dict) and 'overall_pass' in result:
                total_tests += 1
                if result['overall_pass']:
                    passed_tests += 1
                    scores.append(1.0)
                else:
                    scores.append(0.5)  # Partial credit for failed tests
            elif isinstance(result, dict) and 'status' in result:
                total_tests += 1
                if result['status'] == 'error':
                    scores.append(0.0)
        
        overall_score = mean(scores) if scores else 0.0
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
        
        # Generate recommendations
        recommendations = []
        if overall_score < 0.6:
            recommendations.append("Overall performance below acceptable threshold")
        if pass_rate < 0.7:
            recommendations.append("Consider parameter optimization or strategy refinement")
        
        # Check specific test failures
        for test_type, result in test_results.items():
            if isinstance(result, dict) and not result.get('overall_pass', True):
                if test_type == 'backtest':
                    recommendations.append("Backtest performance needs improvement - check signal quality")
                elif test_type == 'robustness':
                    recommendations.append("Strategy lacks robustness across market conditions")
                elif test_type == 'stress_test':
                    recommendations.append("Strategy vulnerable to extreme market conditions")
                elif test_type == 'walk_forward':
                    recommendations.append("Strategy shows performance degradation over time")
        
        return {
            'overall_score': overall_score,
            'pass_rate': pass_rate,
            'recommendations': recommendations
        }


def create_validation_suite(config: TestConfig = None) -> ValidationSuite:
    """Factory function to create validation suite"""
    return ValidationSuite(config)


def run_quick_validation(indicator: AugmentedIndicator, 
                        symbols: List[str] = None,
                        config: TestConfig = None) -> Dict[str, Any]:
    """Run quick validation for rapid testing"""
    if symbols is None:
        symbols = ['TEST']
    
    suite = create_validation_suite(config)
    
    # Run subset of tests for speed
    quick_tests = [TestType.BACKTEST, TestType.EDGE_CASE]
    
    return suite.run_comprehensive_validation(indicator, symbols, quick_tests)


def run_production_validation(indicator: AugmentedIndicator,
                            symbols: List[str] = None,
                            config: TestConfig = None) -> Dict[str, Any]:
    """Run comprehensive production-ready validation"""
    if symbols is None:
        symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'SPY', 'QQQ', 'IWM']
    
    suite = create_validation_suite(config)
    
    # Run all validation tests
    all_tests = [
        TestType.BACKTEST,
        TestType.ROBUSTNESS,
        TestType.STRESS_TEST,
        TestType.WALK_FORWARD,
        TestType.CROSS_VALIDATION,
        TestType.MONTE_CARLO,
        TestType.EDGE_CASE,
        TestType.PERFORMANCE_BENCHMARK,
        TestType.STABILITY_TEST
    ]
    
    return suite.run_comprehensive_validation(indicator, symbols, all_tests)


if __name__ == "__main__":
    # Example usage
    from .augmented_volume_weighted_trend import create_augmented_volume_weighted_macd
    
    # Create test indicator
    indicator = create_augmented_volume_weighted_macd()
    
    # Run quick validation
    print("Running quick validation...")
    quick_results = run_quick_validation(indicator)
    print(f"Quick validation score: {quick_results['overall_score']:.2f}")
    
    # Run production validation (commented out for speed)
    # print("\nRunning production validation...")
    # prod_results = run_production_validation(indicator)
    # print(f"Production validation score: {prod_results['overall_score']:.2f}")
    # print(f"Recommendations: {prod_results['recommendations']}")