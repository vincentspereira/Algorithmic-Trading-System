"""Backtesting Engine

Core backtesting engine with event-driven simulation, transaction cost modeling,
and comprehensive performance tracking.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

from .config import BacktestConfig, BacktestMode, TransactionCosts
from .results import BacktestResults, Trade, Position, PortfolioSnapshot, TradeType, TradeStatus
from .metrics import MetricsCalculator
from nautilus_trader_engine.indicators.consolidated_indicators import ConsolidatedIndicators


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """Market data container"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # Additional data
    bid: Optional[float] = None
    ask: Optional[float] = None
    vwap: Optional[float] = None
    
    @property
    def typical_price(self) -> float:
        """Typical price (HLC/3)"""
        return (self.high + self.low + self.close) / 3
    
    @property
    def bid_ask_spread(self) -> float:
        """Bid-ask spread"""
        if self.bid and self.ask:
            return (self.ask - self.bid) / self.close
        return 0.001  # Default spread


@dataclass
class Order:
    """Order representation"""
    timestamp: datetime
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    order_type: str = 'market'
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Order metadata
    order_id: str = ""
    strategy_id: str = ""
    signal_strength: Optional[float] = None
    confidence: Optional[float] = None
    
    # Execution tracking
    status: TradeStatus = TradeStatus.PENDING
    fill_price: Optional[float] = None
    fill_quantity: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    market_impact: float = 0.0


class Portfolio:
    """Portfolio management class"""
    
    def __init__(self, initial_capital: float, currency: str = "USD"):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.currency = currency
        self.positions: Dict[str, Position] = {}
        self.history: List[PortfolioSnapshot] = []
        
        # Performance tracking
        self.total_pnl = 0.0
        self.realized_pnl = 0.0
        self.unrealized_pnl = 0.0
        
        # Risk tracking
        self.max_leverage = 1.0
        self.current_leverage = 0.0
    
    @property
    def total_value(self) -> float:
        """Total portfolio value"""
        positions_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + positions_value
    
    @property
    def positions_value(self) -> float:
        """Total value of positions"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def update_position(self, symbol: str, quantity: float, price: float, timestamp: datetime):
        """Update position after trade execution"""
        if symbol not in self.positions:
            if quantity != 0:
                self.positions[symbol] = Position(
                    timestamp=timestamp,
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price,
                    market_price=price,
                    market_value=quantity * price,
                    unrealized_pnl=0.0,
                    realized_pnl=0.0,
                    total_pnl=0.0,
                    weight=0.0
                )
        else:
            position = self.positions[symbol]
            old_quantity = position.quantity
            
            if old_quantity * quantity < 0:  # Position reversal
                # Close existing position first
                close_quantity = min(abs(old_quantity), abs(quantity))
                realized_pnl = close_quantity * (price - position.avg_price) * (1 if old_quantity > 0 else -1)
                position.realized_pnl += realized_pnl
                self.realized_pnl += realized_pnl
                
                # Update quantity
                remaining_old = old_quantity - close_quantity * (1 if old_quantity > 0 else -1)
                remaining_new = quantity - close_quantity * (-1 if old_quantity > 0 else 1)
                
                if abs(remaining_new) > 0.001:  # New position
                    position.quantity = remaining_new
                    position.avg_price = price
                elif abs(remaining_old) > 0.001:  # Partial close
                    position.quantity = remaining_old
                else:  # Complete close
                    position.quantity = 0
            
            elif quantity != 0:  # Same direction trade
                # Update average price
                total_cost = position.quantity * position.avg_price + quantity * price
                position.quantity += quantity
                if position.quantity != 0:
                    position.avg_price = total_cost / position.quantity
            
            # Remove zero positions
            if abs(position.quantity) < 0.001:
                del self.positions[symbol]
    
    def update_market_prices(self, market_data: Dict[str, MarketData]):
        """Update market prices for all positions"""
        self.unrealized_pnl = 0.0
        total_value = self.cash
        
        for symbol, position in self.positions.items():
            if symbol in market_data:
                position.market_price = market_data[symbol].close
                position.market_value = position.quantity * position.market_price
                position.unrealized_pnl = (position.market_price - position.avg_price) * position.quantity
                position.total_pnl = position.realized_pnl + position.unrealized_pnl
                
                self.unrealized_pnl += position.unrealized_pnl
                total_value += position.market_value
        
        # Update position weights
        if total_value > 0:
            for position in self.positions.values():
                position.weight = position.market_value / total_value
        
        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        
        # Update leverage
        gross_exposure = sum(abs(pos.market_value) for pos in self.positions.values())
        self.current_leverage = gross_exposure / total_value if total_value > 0 else 0.0
    
    def create_snapshot(self, timestamp: datetime, market_data: Dict[str, MarketData]) -> PortfolioSnapshot:
        """Create portfolio snapshot"""
        self.update_market_prices(market_data)
        
        # Calculate daily return
        daily_return = 0.0
        if len(self.history) > 0:
            prev_value = self.history[-1].total_value
            daily_return = (self.total_value - prev_value) / prev_value if prev_value > 0 else 0.0
        
        # Calculate cumulative return
        cumulative_return = (self.total_value - self.initial_capital) / self.initial_capital
        
        # Create snapshot
        snapshot = PortfolioSnapshot(
            timestamp=timestamp,
            total_value=self.total_value,
            cash=self.cash,
            positions_value=self.positions_value,
            daily_return=daily_return,
            cumulative_return=cumulative_return,
            volatility=0.0,  # Will be calculated later
            sharpe_ratio=0.0,  # Will be calculated later
            beta=0.0,  # Will be calculated later
            var_95=0.0,  # Will be calculated later
            var_99=0.0,  # Will be calculated later
            max_drawdown=0.0,  # Will be calculated later
            positions=list(self.positions.values()),
            leverage=self.current_leverage
        )
        
        self.history.append(snapshot)
        return snapshot


class ExecutionEngine:
    """Order execution engine with transaction cost modeling"""
    
    def __init__(self, transaction_costs: TransactionCosts):
        self.transaction_costs = transaction_costs
        self.executed_trades: List[Trade] = []
    
    def execute_order(self, order: Order, market_data: MarketData, portfolio_value: float) -> Optional[Trade]:
        """Execute order with realistic transaction costs"""
        
        # Determine execution price
        if order.order_type == 'market':
            if order.side == 'buy':
                execution_price = market_data.ask or market_data.close
            else:
                execution_price = market_data.bid or market_data.close
        elif order.order_type == 'limit':
            if order.limit_price is None:
                return None
            
            # Check if limit order can be filled
            if order.side == 'buy' and order.limit_price >= market_data.low:
                execution_price = min(order.limit_price, market_data.close)
            elif order.side == 'sell' and order.limit_price <= market_data.high:
                execution_price = max(order.limit_price, market_data.close)
            else:
                return None  # Order not filled
        else:
            execution_price = market_data.close
        
        # Calculate transaction costs
        trade_value = abs(order.quantity * execution_price)
        
        # Commission
        commission = max(
            self.transaction_costs.commission_min,
            min(
                order.quantity * self.transaction_costs.commission_per_share,
                trade_value * self.transaction_costs.commission_max
            )
        )
        
        # Bid-ask spread cost
        spread_cost = trade_value * market_data.bid_ask_spread / 2
        
        # Market impact (based on trade size relative to volume)
        volume_ratio = abs(order.quantity) / max(market_data.volume, 1)
        market_impact = trade_value * self.transaction_costs.market_impact * np.sqrt(volume_ratio)
        
        # Slippage (random component)
        slippage_amount = trade_value * self.transaction_costs.slippage * np.random.normal(0, 1)
        
        # Adjust execution price for slippage
        if order.side == 'buy':
            execution_price += abs(slippage_amount) / abs(order.quantity)
        else:
            execution_price -= abs(slippage_amount) / abs(order.quantity)
        
        # Create trade record
        trade = Trade(
            timestamp=order.timestamp,
            symbol=order.symbol,
            trade_type=TradeType.BUY if order.side == 'buy' else TradeType.SELL,
            quantity=order.quantity,
            price=execution_price,
            commission=commission,
            slippage=abs(slippage_amount),
            market_impact=market_impact,
            trade_id=f"{order.symbol}_{order.timestamp.strftime('%Y%m%d_%H%M%S')}",
            strategy_id=order.strategy_id,
            signal_strength=order.signal_strength,
            confidence=order.confidence,
            status=TradeStatus.FILLED,
            fill_time=order.timestamp,
            order_type=order.order_type,
            portfolio_value=portfolio_value,
            volume=market_data.volume
        )
        
        self.executed_trades.append(trade)
        return trade


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.portfolio = Portfolio(config.initial_capital, config.currency)
        self.execution_engine = ExecutionEngine(config.transaction_costs)
        
        # Data storage
        self.market_data: Dict[str, pd.DataFrame] = {}
        self.benchmark_data: Optional[pd.DataFrame] = None
        
        # Strategy interface
        self.strategy_function: Optional[Callable] = None
        
        # Results tracking
        self.results: Optional[BacktestResults] = None
        
        # Performance tracking
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def add_data(self, symbol: str, data: pd.DataFrame):
        """Add market data for a symbol"""
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in data.columns for col in required_columns):
            raise ValueError(f"Data must contain columns: {required_columns}")
        
        # Ensure datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        # Filter data to backtest period
        mask = (data.index >= self.config.start_date) & (data.index <= self.config.end_date)
        self.market_data[symbol] = data[mask].copy()
        
        logger.info(f"Added {len(self.market_data[symbol])} bars for {symbol}")
    
    def add_benchmark_data(self, data: pd.DataFrame):
        """Add benchmark data"""
        if 'close' not in data.columns:
            raise ValueError("Benchmark data must contain 'close' column")
        
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)
        
        mask = (data.index >= self.config.start_date) & (data.index <= self.config.end_date)
        self.benchmark_data = data[mask].copy()
        
        logger.info(f"Added {len(self.benchmark_data)} benchmark bars")
    
    def set_strategy(self, strategy_function: Callable):
        """Set strategy function"""
        self.strategy_function = strategy_function
    
    def run_backtest(self) -> BacktestResults:
        """Run the backtest"""
        if not self.market_data:
            raise ValueError("No market data provided")
        
        if self.strategy_function is None:
            raise ValueError("No strategy function provided")
        
        logger.info(f"Starting backtest from {self.config.start_date} to {self.config.end_date}")
        self.start_time = datetime.now()
        
        try:
            if self.config.mode == BacktestMode.EVENT_DRIVEN:
                self._run_event_driven_backtest()
            elif self.config.mode == BacktestMode.VECTORIZED:
                self._run_vectorized_backtest()
            elif self.config.mode == BacktestMode.MONTE_CARLO:
                self._run_monte_carlo_backtest()
            elif self.config.mode == BacktestMode.WALK_FORWARD:
                self._run_walk_forward_backtest()
            else:
                raise ValueError(f"Unsupported backtest mode: {self.config.mode}")
            
            self.end_time = datetime.now()
            
            # Generate results
            self.results = self._generate_results()
            
            logger.info(f"Backtest completed in {self.end_time - self.start_time}")
            return self.results
        
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            raise
    
    def _run_event_driven_backtest(self):
        """Run event-driven backtest"""
        # Get all unique timestamps
        all_timestamps = set()
        for symbol_data in self.market_data.values():
            all_timestamps.update(symbol_data.index)
        
        timestamps = sorted(all_timestamps)
        
        # Warmup period
        warmup_end = min(len(timestamps), self.config.warmup_period)
        
        logger.info(f"Processing {len(timestamps)} time periods with {warmup_end} warmup periods")
        
        for i, timestamp in enumerate(timestamps):
            # Prepare market data for this timestamp
            current_market_data = {}
            for symbol, data in self.market_data.items():
                if timestamp in data.index:
                    row = data.loc[timestamp]
                    current_market_data[symbol] = MarketData(
                        timestamp=timestamp,
                        symbol=symbol,
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=row['volume']
                    )
            
            if not current_market_data:
                continue
            
            # Update portfolio with current market prices
            self.portfolio.update_market_prices(current_market_data)
            
            # Generate signals (skip warmup period)
            if i >= warmup_end:
                # Prepare historical data for strategy
                historical_data = {}
                for symbol, data in self.market_data.items():
                    symbol_history = data[data.index <= timestamp].tail(252)  # Last year of data
                    if len(symbol_history) > 0:
                        historical_data[symbol] = symbol_history
                
                # Call strategy function
                try:
                    orders = self.strategy_function(
                        timestamp=timestamp,
                        market_data=current_market_data,
                        historical_data=historical_data,
                        portfolio=self.portfolio,
                        config=self.config
                    )
                    
                    # Execute orders
                    if orders:
                        for order in orders:
                            if order.symbol in current_market_data:
                                trade = self.execution_engine.execute_order(
                                    order, 
                                    current_market_data[order.symbol],
                                    self.portfolio.total_value
                                )
                                
                                if trade:
                                    # Update portfolio
                                    self.portfolio.update_position(
                                        trade.symbol,
                                        trade.quantity if trade.trade_type == TradeType.BUY else -trade.quantity,
                                        trade.price,
                                        trade.timestamp
                                    )
                                    
                                    # Update cash
                                    cash_flow = -trade.net_proceeds
                                    self.portfolio.cash += cash_flow
                
                except Exception as e:
                    logger.warning(f"Strategy error at {timestamp}: {str(e)}")
            
            # Create portfolio snapshot
            self.portfolio.create_snapshot(timestamp, current_market_data)
            
            # Progress logging
            if i % 100 == 0:
                progress = (i / len(timestamps)) * 100
                logger.info(f"Progress: {progress:.1f}% - Portfolio Value: ${self.portfolio.total_value:,.2f}")
    
    def _run_vectorized_backtest(self):
        """Run vectorized backtest (simplified implementation)"""
        logger.info("Running vectorized backtest")
        
        # For now, fall back to event-driven
        # TODO: Implement true vectorized backtesting
        self._run_event_driven_backtest()
    
    def _run_monte_carlo_backtest(self):
        """Run Monte Carlo simulation"""
        logger.info(f"Running Monte Carlo simulation with {self.config.monte_carlo_runs} runs")
        
        # For now, run single backtest
        # TODO: Implement Monte Carlo simulation
        self._run_event_driven_backtest()
    
    def _run_walk_forward_backtest(self):
        """Run walk-forward analysis"""
        logger.info("Running walk-forward analysis")
        
        # For now, run single backtest
        # TODO: Implement walk-forward analysis
        self._run_event_driven_backtest()
    
    def _generate_results(self) -> BacktestResults:
        """Generate comprehensive backtest results"""
        if not self.portfolio.history:
            raise ValueError("No portfolio history available")
        
        # Create portfolio history DataFrame
        portfolio_data = []
        for snapshot in self.portfolio.history:
            portfolio_data.append({
                'timestamp': snapshot.timestamp,
                'portfolio_value': snapshot.total_value,
                'cash': snapshot.cash,
                'positions_value': snapshot.positions_value,
                'daily_return': snapshot.daily_return,
                'cumulative_return': snapshot.cumulative_return
            })
        
        portfolio_df = pd.DataFrame(portfolio_data).set_index('timestamp')
        returns_series = portfolio_df['daily_return'].dropna()
        
        # Benchmark returns
        benchmark_returns = pd.Series(dtype=float)
        if self.benchmark_data is not None:
            benchmark_prices = self.benchmark_data['close'].reindex(portfolio_df.index, method='ffill')
            benchmark_returns = benchmark_prices.pct_change().dropna()
        
        # Calculate all metrics
        metrics = MetricsCalculator.calculate_all_metrics(
            returns=returns_series,
            benchmark_returns=benchmark_returns if not benchmark_returns.empty else None,
            trades=self.execution_engine.executed_trades
        )
        
        # Create results object
        results = BacktestResults(
            strategy_name="Custom Strategy",
            start_date=self.config.start_date,
            end_date=self.config.end_date,
            initial_capital=self.config.initial_capital,
            final_capital=self.portfolio.total_value,
            portfolio_history=portfolio_df,
            returns_series=returns_series,
            benchmark_returns=benchmark_returns,
            trades=self.execution_engine.executed_trades,
            positions_history=self.portfolio.history
        )
        
        # Update results with calculated metrics
        perf = metrics['performance']
        risk = metrics['risk']
        trade_metrics = metrics['trades']
        benchmark_metrics = metrics['benchmark']
        
        # Performance metrics
        results.total_return = perf.total_return
        results.annualized_return = perf.annualized_return
        results.volatility = perf.volatility
        results.sharpe_ratio = perf.sharpe_ratio
        results.sortino_ratio = perf.sortino_ratio
        results.calmar_ratio = perf.calmar_ratio
        
        # Risk metrics
        results.max_drawdown = risk.max_drawdown
        results.var_95 = risk.var_95
        results.var_99 = risk.var_99
        results.cvar_95 = risk.cvar_95
        results.cvar_99 = risk.cvar_99
        
        # Benchmark metrics
        results.alpha = benchmark_metrics.alpha
        results.beta = benchmark_metrics.beta
        results.information_ratio = benchmark_metrics.information_ratio
        results.tracking_error = benchmark_metrics.tracking_error
        
        # Trade metrics
        results.total_trades = trade_metrics.total_trades
        results.winning_trades = trade_metrics.winning_trades
        results.losing_trades = trade_metrics.losing_trades
        results.win_rate = trade_metrics.win_rate
        results.avg_win = trade_metrics.avg_win
        results.avg_loss = trade_metrics.avg_loss
        results.profit_factor = trade_metrics.profit_factor
        
        # Execution quality
        results.avg_slippage = trade_metrics.avg_slippage
        results.avg_commission = trade_metrics.avg_commission
        results.total_costs = trade_metrics.total_costs
        
        return results
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if self.results is None:
            raise ValueError("No backtest results available. Run backtest first.")
        
        return self.results.get_summary_stats()


# Example strategy function signature
def example_strategy(timestamp: datetime, market_data: Dict[str, MarketData], 
                   historical_data: Dict[str, pd.DataFrame], portfolio: Portfolio,
                   config: BacktestConfig) -> List[Order]:
    """Example strategy function
    
    Args:
        timestamp: Current timestamp
        market_data: Current market data for all symbols
        historical_data: Historical data for all symbols
        portfolio: Current portfolio state
        config: Backtest configuration
    
    Returns:
        List of orders to execute
    """
    orders = []
    
    # Example: Simple buy and hold
    for symbol in market_data.keys():
        if symbol not in portfolio.positions:
            # Buy $1000 worth of each symbol
            price = market_data[symbol].close
            quantity = 1000 / price
            
            order = Order(
                timestamp=timestamp,
                symbol=symbol,
                side='buy',
                quantity=quantity,
                order_type='market',
                strategy_id='buy_and_hold'
            )
            orders.append(order)
    
    return orders