# Strategy Framework Documentation

## Overview

The NautilusTrader Strategy Framework provides a comprehensive, enterprise-grade foundation for developing, testing, and deploying algorithmic trading strategies. Built with performance, scalability, and maintainability in mind, the framework supports multiple asset classes and trading styles while providing robust risk management and performance monitoring capabilities.

## Architecture

### Core Components

```
nautilus_trader_engine/strategies/
├── core/
│   └── base_strategy.py          # Abstract base strategy class
├── utils/
│   ├── strategy_utilities.py     # Common utility functions
│   ├── performance_tracker.py    # Performance monitoring
│   ├── signal_processing.py      # Signal generation and processing
│   └── logging_config.py         # Centralized logging configuration
└── implementations/
    ├── momentum_strategy.py       # Example momentum strategy
    ├── mean_reversion_strategy.py # Example mean reversion strategy
    └── arbitrage_strategy.py      # Example arbitrage strategy
```

### Key Features

- **Abstract Base Strategy**: Provides a consistent interface for all trading strategies
- **Comprehensive Utilities**: Position sizing, risk management, and data validation
- **Performance Tracking**: Real-time performance monitoring and reporting
- **Signal Processing**: Advanced signal generation and aggregation
- **Centralized Logging**: Structured logging with performance monitoring
- **Type Safety**: Full type hints and validation throughout
- **Async Support**: Asynchronous operations for high-performance execution

## Quick Start

### 1. Creating a Basic Strategy

```python
from decimal import Decimal
from datetime import datetime
import pandas as pd

from nautilus_trader_engine.strategies.core.base_strategy import (
    BaseStrategy, StrategyConfig, RiskParameters, Signal,
    StrategyType, SignalType, SignalStrength, PositionSizing
)

class MyMomentumStrategy(BaseStrategy):
    """Simple momentum strategy implementation."""
    
    def generate_signals(self, market_data: pd.DataFrame) -> list[Signal]:
        """Generate trading signals based on momentum indicators."""
        if len(market_data) < 20:
            return []
        
        # Calculate simple moving averages
        short_ma = market_data['close'].rolling(5).mean()
        long_ma = market_data['close'].rolling(20).mean()
        
        signals = []
        current_price = market_data['close'].iloc[-1]
        
        # Generate buy signal on golden cross
        if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
            signals.append(Signal(
                signal_type=SignalType.BUY,
                strength=SignalStrength.STRONG,
                price=Decimal(str(current_price)),
                confidence=0.8,
                timestamp=datetime.now()
            ))
        
        # Generate sell signal on death cross
        elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
            signals.append(Signal(
                signal_type=SignalType.SELL,
                strength=SignalStrength.STRONG,
                price=Decimal(str(current_price)),
                confidence=0.8,
                timestamp=datetime.now()
            ))
        
        return signals
    
    def calculate_position_size(self, signal: Signal, account_balance: Decimal) -> Decimal:
        """Calculate position size based on risk parameters."""
        from nautilus_trader_engine.strategies.utils.strategy_utilities import StrategyUtilities
        
        stop_loss_price = signal.price * Decimal('0.98')  # 2% stop loss
        
        return StrategyUtilities.calculate_position_size(
            account_balance=account_balance,
            risk_per_trade=self.config.risk_parameters.stop_loss_pct,
            entry_price=signal.price,
            stop_loss_price=stop_loss_price
        )

# Create strategy configuration
config = StrategyConfig(
    name="my_momentum_strategy",
    strategy_type=StrategyType.MOMENTUM,
    risk_parameters=RiskParameters(
        max_position_size=Decimal('50000'),
        stop_loss_pct=Decimal('0.02'),
        take_profit_pct=Decimal('0.05'),
        max_daily_loss=Decimal('2000'),
        position_sizing=PositionSizing.RISK_BASED
    ),
    parameters={
        'short_period': 5,
        'long_period': 20,
        'min_confidence': 0.7
    }
)

# Initialize strategy
strategy = MyMomentumStrategy(config)
```

### 2. Running a Backtest

```python
import pandas as pd
from datetime import datetime, timedelta

# Load historical data
market_data = pd.read_csv('historical_data.csv')

# Generate signals
signals = strategy.generate_signals(market_data)

# Process signals and track performance
account_balance = Decimal('100000')
for signal in signals:
    position_size = strategy.calculate_position_size(signal, account_balance)
    
    # Simulate trade execution
    position = Position(
        symbol="AAPL",
        side=PositionSide.LONG if signal.signal_type == SignalType.BUY else PositionSide.SHORT,
        size=position_size,
        entry_price=signal.price,
        timestamp=signal.timestamp
    )
    
    strategy.add_position("AAPL", position)

# Get performance summary
performance = strategy.performance_tracker.get_performance_summary()
print(f"Total PnL: ${performance.total_pnl:.2f}")
print(f"Win Rate: {performance.win_rate:.2%}")
print(f"Sharpe Ratio: {performance.sharpe_ratio:.2f}")
```

## Core Classes

### BaseStrategy

The abstract base class that all strategies must inherit from.

#### Key Methods

- `generate_signals(market_data: pd.DataFrame) -> list[Signal]`: Generate trading signals
- `calculate_position_size(signal: Signal, account_balance: Decimal) -> Decimal`: Calculate position size
- `update_position(symbol: str, new_price: Decimal)`: Update position with new market price
- `add_position(symbol: str, position: Position)`: Add new position to portfolio
- `update_performance_metrics()`: Update strategy performance metrics

#### Properties

- `state: StrategyState`: Current strategy state (INITIALIZED, RUNNING, STOPPED, ERROR)
- `positions: dict[str, Position]`: Current positions by symbol
- `total_pnl: Decimal`: Total profit/loss across all positions
- `performance_tracker: PerformanceTracker`: Performance monitoring instance

### StrategyConfig

Configuration class for strategy parameters.

```python
@dataclass
class StrategyConfig:
    name: str
    strategy_type: StrategyType
    risk_parameters: RiskParameters
    parameters: dict[str, Any]
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not self.name or not self.name.strip():
            raise ValueError("Strategy name cannot be empty")
        
        if not isinstance(self.risk_parameters, RiskParameters):
            raise TypeError("risk_parameters must be RiskParameters instance")
```

### RiskParameters

Risk management configuration.

```python
@dataclass
class RiskParameters:
    max_position_size: Decimal
    stop_loss_pct: Decimal
    take_profit_pct: Decimal
    max_daily_loss: Decimal
    position_sizing: PositionSizing
    
    def __post_init__(self):
        """Validate risk parameters."""
        if self.max_position_size <= 0:
            raise ValueError("max_position_size must be positive")
        
        if not (0 < self.stop_loss_pct < 1):
            raise ValueError("stop_loss_pct must be between 0 and 1")
```

### Position

Represents a trading position.

```python
@dataclass
class Position:
    symbol: str
    side: PositionSide
    size: Decimal
    entry_price: Decimal
    timestamp: datetime
    current_price: Optional[Decimal] = None
    
    @property
    def market_value(self) -> Decimal:
        """Calculate current market value of position."""
        price = self.current_price or self.entry_price
        return self.size * price
    
    @property
    def pnl(self) -> Decimal:
        """Calculate unrealized profit/loss."""
        if not self.current_price:
            return Decimal('0')
        
        price_diff = self.current_price - self.entry_price
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff
        
        return self.size * price_diff
```

### Signal

Represents a trading signal.

```python
@dataclass
class Signal:
    signal_type: SignalType
    strength: SignalStrength
    price: Decimal
    confidence: float
    timestamp: datetime
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """Validate signal parameters."""
        if not (0 <= self.confidence <= 1):
            raise ValueError("Confidence must be between 0 and 1")
        
        if self.price <= 0:
            raise ValueError("Price must be positive")
```

## Utility Functions

### StrategyUtilities

Common utility functions for strategy development.

#### Position Sizing

```python
from nautilus_trader_engine.strategies.utils.strategy_utilities import StrategyUtilities

# Calculate position size based on risk
position_size = StrategyUtilities.calculate_position_size(
    account_balance=Decimal('100000'),
    risk_per_trade=Decimal('0.02'),  # 2% risk
    entry_price=Decimal('150.00'),
    stop_loss_price=Decimal('147.00')
)
```

#### Risk Metrics

```python
# Calculate comprehensive risk metrics
returns = pd.Series([0.01, -0.005, 0.02, -0.01, 0.015])
risk_metrics = StrategyUtilities.calculate_risk_metrics(
    returns=returns,
    risk_free_rate=0.02
)

print(f"Sharpe Ratio: {risk_metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {risk_metrics['max_drawdown']:.2%}")
print(f"VaR (95%): {risk_metrics['var_95']:.2%}")
```

#### Data Processing

```python
# Normalize price data
normalized_data = StrategyUtilities.normalize_data(
    data=market_data['close'],
    method='z_score'
)

# Detect outliers
outliers = StrategyUtilities.detect_outliers(
    data=market_data['volume'],
    method='iqr',
    threshold=1.5
)
```

### DataValidation

Data validation utilities.

```python
from nautilus_trader_engine.strategies.utils.strategy_utilities import DataValidation

# Validate price data
is_valid = DataValidation.validate_price_data(market_data)
if not is_valid:
    print("Invalid price data detected")

# Validate strategy configuration
config_dict = {
    'name': 'test_strategy',
    'lookback_period': 20,
    'threshold': 0.02
}
is_valid_config = DataValidation.validate_strategy_config(config_dict)
```

## Performance Tracking

### PerformanceTracker

Comprehensive performance monitoring and analysis.

```python
from nautilus_trader_engine.strategies.utils.performance_tracker import PerformanceTracker

# Initialize tracker
tracker = PerformanceTracker()

# Record trades
tracker.record_trade(
    symbol="AAPL",
    entry_price=150.00,
    exit_price=155.00,
    quantity=100.0,
    side="long",
    entry_time=datetime.now() - timedelta(hours=2),
    exit_time=datetime.now(),
    pnl=500.0
)

# Get performance summary
summary = tracker.get_performance_summary()
print(f"Total Trades: {summary.total_trades}")
print(f"Win Rate: {summary.win_rate:.2%}")
print(f"Average Trade: ${summary.avg_trade_pnl:.2f}")
print(f"Sharpe Ratio: {summary.sharpe_ratio:.2f}")

# Generate detailed report
report = tracker.generate_performance_report()
print(report)
```

### Performance Metrics

The framework tracks comprehensive performance metrics:

- **Return Metrics**: Total return, annualized return, excess return
- **Risk Metrics**: Volatility, Sharpe ratio, Sortino ratio, maximum drawdown
- **Trade Metrics**: Win rate, average trade, profit factor, expectancy
- **Time-based Analysis**: Monthly/yearly performance, rolling metrics
- **Risk Analysis**: Value at Risk (VaR), Expected Shortfall (ES)

## Signal Processing

### SignalProcessor

Advanced signal generation and processing capabilities.

```python
from nautilus_trader_engine.strategies.utils.signal_processing import (
    SignalProcessor, TradingSignal, SignalType
)

# Initialize processor
processor = SignalProcessor()

# Create trading signals
signals = [
    TradingSignal(
        signal_type=SignalType.BUY,
        strength=SignalStrength.STRONG,
        price=150.0,
        confidence=0.8,
        timestamp=datetime.now(),
        metadata={'indicator': 'RSI'}
    ),
    TradingSignal(
        signal_type=SignalType.BUY,
        strength=SignalStrength.MEDIUM,
        price=150.5,
        confidence=0.6,
        timestamp=datetime.now(),
        metadata={'indicator': 'MACD'}
    )
]

# Aggregate signals
result = processor.aggregate_signals(signals)
print(f"Consensus: {result.consensus_signal}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Signal Count: {result.signal_count}")
```

### Signal Generation

Built-in signal generation methods:

```python
# Generate crossover signals
crossover_signals = processor.generate_crossover_signals(
    fast_series=short_ma,
    slow_series=long_ma,
    prices=market_data['close']
)

# Generate threshold signals
threshold_signals = processor.generate_threshold_signals(
    indicator_series=rsi,
    buy_threshold=30,
    sell_threshold=70,
    prices=market_data['close']
)

# Generate divergence signals
divergence_signals = processor.generate_divergence_signals(
    price_series=market_data['close'],
    indicator_series=rsi,
    lookback_period=20
)
```

## Logging and Monitoring

### Centralized Logging

```python
from nautilus_trader_engine.strategies.utils.logging_config import (
    setup_trading_logger, performance_monitor, trade_event
)

# Setup logger
logger = setup_trading_logger(
    name="my_strategy",
    log_file="strategy.log",
    level=logging.INFO
)

# Use performance monitoring decorator
@performance_monitor(logger)
def expensive_calculation():
    # Your code here
    return result

# Use trade event logging decorator
@trade_event(logger)
def execute_trade(symbol: str, action: str, quantity: float):
    # Your trade execution code
    return f"Executed {action} {quantity} shares of {symbol}"
```

### Performance Monitoring

```python
from nautilus_trader_engine.strategies.utils.logging_config import PerformanceMonitor

# Initialize monitor
monitor = PerformanceMonitor()

# Log system metrics
monitor.log_system_metrics()

# Log strategy metrics
monitor.log_strategy_metrics(
    strategy_name="momentum_strategy",
    total_pnl=1500.0,
    open_positions=5,
    daily_pnl=250.0
)
```

## Testing

### Unit Tests

The framework includes comprehensive unit tests:

```bash
# Run all strategy tests
pytest tests/nautilus_trader_engine/strategies/ -v

# Run specific test modules
pytest tests/nautilus_trader_engine/strategies/test_base_strategy.py -v
pytest tests/nautilus_trader_engine/strategies/test_strategy_utilities.py -v
```

### Integration Tests

Test strategy component interactions:

```bash
# Run integration tests
pytest tests/nautilus_trader_engine/strategies/test_strategy_integration.py -v
```

### Performance Benchmarks

Validate performance requirements:

```bash
# Run performance benchmarks
pytest tests/nautilus_trader_engine/strategies/test_performance_benchmarks.py -v -s
```

## Best Practices

### 1. Strategy Development

- **Inherit from BaseStrategy**: Always extend the abstract base class
- **Implement Required Methods**: Provide implementations for `generate_signals` and `calculate_position_size`
- **Use Type Hints**: Maintain type safety throughout your code
- **Validate Inputs**: Check data quality and parameter validity
- **Handle Errors Gracefully**: Implement proper error handling and logging

### 2. Risk Management

- **Set Appropriate Limits**: Configure reasonable position sizes and stop losses
- **Monitor Drawdowns**: Track maximum drawdown and implement circuit breakers
- **Diversify Positions**: Avoid concentration in single assets or strategies
- **Regular Review**: Periodically review and adjust risk parameters

### 3. Performance Optimization

- **Vectorized Operations**: Use pandas/numpy for efficient data processing
- **Minimize Loops**: Avoid explicit loops where possible
- **Cache Calculations**: Store expensive computations for reuse
- **Profile Code**: Use performance benchmarks to identify bottlenecks

### 4. Testing and Validation

- **Unit Test Everything**: Test individual components thoroughly
- **Integration Testing**: Validate component interactions
- **Backtesting**: Test strategies on historical data
- **Paper Trading**: Validate in simulated environment before live trading

### 5. Monitoring and Logging

- **Structured Logging**: Use consistent log formats and levels
- **Performance Metrics**: Track key performance indicators
- **Error Monitoring**: Log and alert on errors and exceptions
- **Regular Reviews**: Analyze logs and metrics regularly

## Advanced Features

### Custom Indicators

Create custom technical indicators:

```python
class CustomIndicator:
    def __init__(self, period: int = 14):
        self.period = period
    
    def calculate(self, data: pd.Series) -> pd.Series:
        """Calculate custom indicator."""
        # Your indicator logic here
        return result

# Use in strategy
class MyStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig):
        super().__init__(config)
        self.custom_indicator = CustomIndicator(period=20)
    
    def generate_signals(self, market_data: pd.DataFrame) -> list[Signal]:
        indicator_values = self.custom_indicator.calculate(market_data['close'])
        # Generate signals based on indicator
        return signals
```

### Multi-Asset Strategies

Handle multiple assets:

```python
class MultiAssetStrategy(BaseStrategy):
    def __init__(self, config: StrategyConfig, symbols: list[str]):
        super().__init__(config)
        self.symbols = symbols
        self.positions_by_symbol = {symbol: {} for symbol in symbols}
    
    def generate_signals(self, market_data: dict[str, pd.DataFrame]) -> list[Signal]:
        """Generate signals for multiple assets."""
        signals = []
        
        for symbol, data in market_data.items():
            # Generate signals for each symbol
            symbol_signals = self._generate_symbol_signals(symbol, data)
            signals.extend(symbol_signals)
        
        return signals
```

### Portfolio Optimization

Integrate portfolio optimization:

```python
from scipy.optimize import minimize
import numpy as np

class OptimizedStrategy(BaseStrategy):
    def optimize_portfolio(self, expected_returns: np.ndarray, 
                          covariance_matrix: np.ndarray) -> np.ndarray:
        """Optimize portfolio weights using mean-variance optimization."""
        n_assets = len(expected_returns)
        
        # Objective function (negative Sharpe ratio)
        def objective(weights):
            portfolio_return = np.sum(weights * expected_returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            return -portfolio_return / portfolio_vol
        
        # Constraints
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Initial guess
        x0 = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(objective, x0, method='SLSQP', 
                         bounds=bounds, constraints=constraints)
        
        return result.x
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python path configuration
   - Verify module structure

2. **Performance Issues**
   - Profile code to identify bottlenecks
   - Use vectorized operations
   - Consider caching expensive calculations

3. **Memory Issues**
   - Monitor memory usage during backtests
   - Clear unnecessary data structures
   - Use data streaming for large datasets

4. **Precision Issues**
   - Use Decimal for financial calculations
   - Be aware of floating-point precision limits
   - Validate calculation results

### Debugging Tips

- Enable detailed logging
- Use performance profiling tools
- Test with small datasets first
- Validate intermediate calculations
- Check data quality and completeness

## API Reference

For detailed API documentation, see the individual module docstrings:

- [BaseStrategy API](../api/base_strategy.md)
- [StrategyUtilities API](../api/strategy_utilities.md)
- [PerformanceTracker API](../api/performance_tracker.md)
- [SignalProcessor API](../api/signal_processing.md)
- [Logging Configuration API](../api/logging_config.md)

## Examples

See the `examples/` directory for complete strategy implementations:

- [Momentum Strategy](../examples/momentum_strategy.py)
- [Mean Reversion Strategy](../examples/mean_reversion_strategy.py)
- [Pairs Trading Strategy](../examples/pairs_trading_strategy.py)
- [Multi-Asset Strategy](../examples/multi_asset_strategy.py)

## Contributing

To contribute to the strategy framework:

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Update documentation
5. Submit a pull request

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd algorithmic-trading-system

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/nautilus_trader_engine/strategies/ -v
```

## License

This strategy framework is part of the Algorithmic Trading System and is licensed under [LICENSE](../../LICENSE).

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review existing examples
- Join the community discussions

---

*Last updated: January 2024*