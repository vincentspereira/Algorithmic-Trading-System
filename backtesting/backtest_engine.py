"""Core Backtesting Engine

This module provides the main backtesting engine for algorithmic trading strategies
with event-driven simulation, performance tracking, and risk management.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Import core components
from core.events import Event, EventType
from core.data_types import MarketData, Trade, Position, Order
from core.risk_management import RiskManager
from core.portfolio import Portfolio

logger = logging.getLogger(__name__)

class BacktestMode(Enum):
    """Backtesting modes"""
    VECTORIZED = "vectorized"
    EVENT_DRIVEN = "event_driven"
    HYBRID = "hybrid"

class BacktestState(Enum):
    """Backtesting states"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    name: str = "Default Backtest"
    start_date: datetime = field(default_factory=lambda: datetime.now() - timedelta(days=365))
    end_date: datetime = field(default_factory=datetime.now)
    initial_capital: float = 1000000.0
    
    # Trading parameters
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    market_impact_rate: float = 0.0001
    
    # Risk parameters
    max_positions: int = 50
    max_position_size: float = 0.1  # 10% of portfolio
    max_sector_exposure: float = 0.3  # 30% per sector
    max_leverage: float = 1.0
    
    # Execution parameters
    execution_delay: int = 0  # bars
    fill_probability: float = 1.0
    partial_fill_probability: float = 0.1
    
    # Benchmark and risk-free rate
    benchmark_symbol: str = "SPY"
    risk_free_rate: float = 0.02
    
    # Frequency settings
    data_frequency: str = "1D"  # 1D, 1H, 15T, etc.
    rebalance_frequency: int = 21  # trading days
    
    # Mode and options
    mode: BacktestMode = BacktestMode.EVENT_DRIVEN
    enable_shorting: bool = True
    enable_options: bool = False
    enable_futures: bool = False
    
    # Performance tracking
    track_trades: bool = True
    track_positions: bool = True
    track_orders: bool = True
    
    # Optimization settings
    warm_up_period: int = 252  # trading days
    cool_down_period: int = 21  # trading days
    
    def __post_init__(self):
        """Validate configuration"""
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        
        if not 0 <= self.commission_rate <= 1:
            raise ValueError("Commission rate must be between 0 and 1")
        
        if not 0 <= self.slippage_rate <= 1:
            raise ValueError("Slippage rate must be between 0 and 1")

class BacktestEngine:
    """Main backtesting engine
    
    Provides event-driven backtesting with comprehensive performance tracking,
    risk management, and transaction cost modeling.
    """
    
    def __init__(self, config: BacktestConfig):
        """Initialize backtest engine
        
        Args:
            config: Backtesting configuration
        """
        self.config = config
        self.state = BacktestState.INITIALIZED
        
        # Core components
        self.portfolio = Portfolio(initial_capital=config.initial_capital)
        self.risk_manager = RiskManager()
        
        # Event system
        self.events = []
        self.event_handlers = defaultdict(list)
        
        # Strategy management
        self.strategies = []
        self.strategy_weights = {}
        
        # Data management
        self.market_data = {}
        self.current_time = None
        self.data_iterator = None
        
        # Performance tracking
        self.trades = []
        self.positions_history = []
        self.portfolio_history = []
        self.orders = []
        
        # Execution tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        # Transaction costs
        self.total_commission = 0.0
        self.total_slippage = 0.0
        self.total_market_impact = 0.0
        
        # Benchmark data
        self.benchmark_data = None
        
        logger.info(f"Initialized backtest engine: {config.name}")
    
    def add_strategy(self, strategy, weight: float = 1.0):
        """Add trading strategy to backtest
        
        Args:
            strategy: Trading strategy instance
            weight: Strategy weight in portfolio (default: 1.0)
        """
        try:
            self.strategies.append(strategy)
            self.strategy_weights[strategy] = weight
            
            # Register strategy event handlers
            if hasattr(strategy, 'on_market_data'):
                self.register_handler(EventType.MARKET_DATA, strategy.on_market_data)
            
            if hasattr(strategy, 'on_trade'):
                self.register_handler(EventType.TRADE, strategy.on_trade)
            
            if hasattr(strategy, 'on_order_fill'):
                self.register_handler(EventType.ORDER_FILL, strategy.on_order_fill)
            
            logger.info(f"Added strategy: {strategy.__class__.__name__} (weight: {weight})")
            
        except Exception as e:
            logger.error(f"Error adding strategy: {e}")
            raise
    
    def register_handler(self, event_type: EventType, handler):
        """Register event handler
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        self.event_handlers[event_type].append(handler)
    
    def emit_event(self, event: Event):
        """Emit event to registered handlers
        
        Args:
            event: Event to emit
        """
        try:
            handlers = self.event_handlers.get(event.type, [])
            for handler in handlers:
                handler(event)
        
        except Exception as e:
            logger.error(f"Error handling event {event.type}: {e}")
    
    def load_market_data(self, data: Dict[str, pd.DataFrame]):
        """Load market data for backtesting
        
        Args:
            data: Dictionary of symbol -> DataFrame mappings
        """
        try:
            self.market_data = data
            
            # Validate data
            for symbol, df in data.items():
                required_columns = ['open', 'high', 'low', 'close', 'volume']
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    raise ValueError(f"Missing columns for {symbol}: {missing_columns}")
                
                # Ensure datetime index
                if not isinstance(df.index, pd.DatetimeIndex):
                    df.index = pd.to_datetime(df.index)
            
            # Create unified time index
            all_dates = set()
            for df in data.values():
                all_dates.update(df.index)
            
            self.time_index = sorted(all_dates)
            self.time_index = [dt for dt in self.time_index 
                             if self.config.start_date <= dt <= self.config.end_date]
            
            logger.info(f"Loaded market data for {len(data)} symbols")
            logger.info(f"Backtest period: {self.time_index[0]} to {self.time_index[-1]}")
            
        except Exception as e:
            logger.error(f"Error loading market data: {e}")
            raise
    
    def load_benchmark_data(self, benchmark_data: pd.DataFrame):
        """Load benchmark data
        
        Args:
            benchmark_data: Benchmark price data
        """
        try:
            self.benchmark_data = benchmark_data
            
            # Ensure datetime index
            if not isinstance(benchmark_data.index, pd.DatetimeIndex):
                self.benchmark_data.index = pd.to_datetime(benchmark_data.index)
            
            logger.info(f"Loaded benchmark data: {self.config.benchmark_symbol}")
            
        except Exception as e:
            logger.error(f"Error loading benchmark data: {e}")
            raise
    
    def calculate_transaction_costs(self, order: Order, fill_price: float) -> Tuple[float, float, float]:
        """Calculate transaction costs for order
        
        Args:
            order: Order being filled
            fill_price: Actual fill price
            
        Returns:
            Tuple of (commission, slippage, market_impact)
        """
        try:
            # Calculate commission
            commission = abs(order.quantity * fill_price * self.config.commission_rate)
            
            # Calculate slippage (difference from expected price)
            expected_price = order.limit_price if order.limit_price else fill_price
            slippage = abs(order.quantity * (fill_price - expected_price))
            
            # Calculate market impact (proportional to order size)
            market_value = abs(order.quantity * fill_price)
            portfolio_value = self.portfolio.total_value
            impact_factor = min(market_value / portfolio_value, 0.1)  # Cap at 10%
            market_impact = market_value * self.config.market_impact_rate * impact_factor
            
            return commission, slippage, market_impact
            
        except Exception as e:
            logger.error(f"Error calculating transaction costs: {e}")
            return 0.0, 0.0, 0.0
    
    def execute_order(self, order: Order, market_data: MarketData) -> Optional[Trade]:
        """Execute order with transaction costs
        
        Args:
            order: Order to execute
            market_data: Current market data
            
        Returns:
            Trade if order was filled, None otherwise
        """
        try:
            # Check if order can be filled
            if np.random.random() > self.config.fill_probability:
                return None
            
            # Determine fill price
            if order.order_type == 'market':
                fill_price = market_data.close
            elif order.order_type == 'limit':
                if order.side == 'buy' and market_data.low <= order.limit_price:
                    fill_price = min(order.limit_price, market_data.open)
                elif order.side == 'sell' and market_data.high >= order.limit_price:
                    fill_price = max(order.limit_price, market_data.open)
                else:
                    return None
            else:
                fill_price = market_data.close
            
            # Apply slippage
            slippage_factor = np.random.normal(0, self.config.slippage_rate)
            if order.side == 'buy':
                fill_price *= (1 + abs(slippage_factor))
            else:
                fill_price *= (1 - abs(slippage_factor))
            
            # Calculate transaction costs
            commission, slippage, market_impact = self.calculate_transaction_costs(order, fill_price)
            
            # Create trade
            trade = Trade(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=fill_price,
                timestamp=self.current_time,
                commission=commission,
                slippage=slippage,
                market_impact=market_impact
            )
            
            # Update portfolio
            self.portfolio.execute_trade(trade)
            
            # Track costs
            self.total_commission += commission
            self.total_slippage += slippage
            self.total_market_impact += market_impact
            
            # Track trade statistics
            self.total_trades += 1
            if trade.pnl > 0:
                self.winning_trades += 1
            elif trade.pnl < 0:
                self.losing_trades += 1
            
            # Store trade
            if self.config.track_trades:
                self.trades.append(trade)
            
            # Emit trade event
            self.emit_event(Event(EventType.TRADE, trade))
            
            logger.debug(f"Executed trade: {trade.symbol} {trade.side} {trade.quantity} @ {trade.price:.2f}")
            return trade
            
        except Exception as e:
            logger.error(f"Error executing order: {e}")
            return None
    
    def run_backtest(self) -> 'BacktestResults':
        """Run the backtest
        
        Returns:
            BacktestResults containing performance metrics and analysis
        """
        try:
            self.state = BacktestState.RUNNING
            logger.info(f"Starting backtest: {self.config.name}")
            
            # Initialize strategies
            for strategy in self.strategies:
                if hasattr(strategy, 'initialize'):
                    strategy.initialize(self.config)
            
            # Main backtest loop
            for i, timestamp in enumerate(self.time_index):
                self.current_time = timestamp
                
                # Get market data for current timestamp
                current_market_data = {}
                for symbol, df in self.market_data.items():
                    if timestamp in df.index:
                        row = df.loc[timestamp]
                        current_market_data[symbol] = MarketData(
                            symbol=symbol,
                            timestamp=timestamp,
                            open=row['open'],
                            high=row['high'],
                            low=row['low'],
                            close=row['close'],
                            volume=row['volume']
                        )
                
                # Emit market data events
                for market_data in current_market_data.values():
                    self.emit_event(Event(EventType.MARKET_DATA, market_data))
                
                # Update portfolio with current prices
                self.portfolio.update_market_prices(current_market_data)
                
                # Track portfolio history
                if self.config.track_positions:
                    self.portfolio_history.append({
                        'timestamp': timestamp,
                        'total_value': self.portfolio.total_value,
                        'cash': self.portfolio.cash,
                        'positions_value': self.portfolio.positions_value,
                        'unrealized_pnl': self.portfolio.unrealized_pnl,
                        'realized_pnl': self.portfolio.realized_pnl
                    })
                
                # Progress logging
                if i % 252 == 0:  # Log progress yearly
                    progress = (i / len(self.time_index)) * 100
                    logger.info(f"Backtest progress: {progress:.1f}% - Portfolio value: ${self.portfolio.total_value:,.2f}")
            
            self.state = BacktestState.COMPLETED
            logger.info(f"Backtest completed: {self.config.name}")
            
            # Create and return results
            from .backtest_results import BacktestResults
            results = BacktestResults(self)
            
            return results
            
        except Exception as e:
            self.state = BacktestState.ERROR
            logger.error(f"Error running backtest: {e}")
            raise
    
    async def run_backtest_async(self) -> 'BacktestResults':
        """Run backtest asynchronously
        
        Returns:
            BacktestResults containing performance metrics and analysis
        """
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            return await loop.run_in_executor(executor, self.run_backtest)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get basic performance summary
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            if not self.portfolio_history:
                return {}
            
            # Calculate basic metrics
            initial_value = self.config.initial_capital
            final_value = self.portfolio.total_value
            total_return = (final_value - initial_value) / initial_value
            
            # Calculate returns series
            portfolio_df = pd.DataFrame(self.portfolio_history)
            portfolio_df.set_index('timestamp', inplace=True)
            returns = portfolio_df['total_value'].pct_change().dropna()
            
            # Basic statistics
            win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
            
            return {
                'total_return': total_return,
                'annualized_return': (1 + total_return) ** (252 / len(self.time_index)) - 1,
                'volatility': returns.std() * np.sqrt(252),
                'sharpe_ratio': (returns.mean() * 252 - self.config.risk_free_rate) / (returns.std() * np.sqrt(252)),
                'max_drawdown': (portfolio_df['total_value'] / portfolio_df['total_value'].cummax() - 1).min(),
                'total_trades': self.total_trades,
                'win_rate': win_rate,
                'total_commission': self.total_commission,
                'total_slippage': self.total_slippage,
                'final_portfolio_value': final_value
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance summary: {e}")
            return {}
    
    def save_results(self, filepath: str):
        """Save backtest results to file
        
        Args:
            filepath: Path to save results
        """
        try:
            results_data = {
                'config': self.config.__dict__,
                'performance': self.get_performance_summary(),
                'portfolio_history': self.portfolio_history,
                'trades': [trade.__dict__ for trade in self.trades] if self.trades else [],
                'final_positions': self.portfolio.get_positions_summary()
            }
            
            import json
            with open(filepath, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
            
            logger.info(f"Saved backtest results to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise


@dataclass
class BacktestResults:
    """Container for backtest results"""
    
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    trades: List[Dict]
    portfolio_history: List[Dict]
    performance_metrics: Dict
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.initial_capital > 0:
            self.total_return_pct = (self.final_capital - self.initial_capital) / self.initial_capital
        else:
            self.total_return_pct = 0.0