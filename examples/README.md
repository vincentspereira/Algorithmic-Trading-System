# Nautilus Trader Engine Usage Examples

This directory contains comprehensive usage examples demonstrating how to use the Nautilus Trader Engine for algorithmic trading.

## Examples Overview

### Basic Examples
- **`basic_trading_strategy.py`** - Complete momentum-based trading strategy implementation
- **`adaptive_indicators_demo.py`** - Adaptive parameter system demonstration

### Advanced Examples (Coming Soon)
- Multi-asset portfolio strategy
- Risk-parity portfolio optimization
- Machine learning-enhanced trading
- High-frequency trading setup
- Cross-market arbitrage strategy

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure you're in the project root directory
cd /path/to/nautilus-trader-engine
```

### Running Examples

```bash
# Run basic trading strategy example
python examples/basic_trading_strategy.py

# Run adaptive indicators demo
python examples/adaptive_indicators_demo.py
```

## Example Categories

### 1. Core System Usage

#### Dependency Injection
```python
from nautilus_trader_engine.core.dependency_injection import get_container

# Get the global container
container = get_container()

# Register a service
container.register(MyService, MyServiceImpl)

# Resolve a service
service = container.get_service(MyService)
```

#### Event System
```python
from nautilus_trader_engine.core.event_system import get_event_bus, EventType

# Get event bus
event_bus = get_event_bus()

# Subscribe to events
await event_bus.subscribe(EventType.MARKET_DATA, handle_market_data)

# Publish events
await event_bus.publish_event(my_event)
```

### 2. Adaptive Parameters

#### Parameter Registration
```python
from nautilus_trader_engine.core.adaptive_parameters import (
    get_adaptive_manager, create_adaptive_parameter,
    ParameterBounds, ParameterType, AdaptationStrategy
)

# Create adaptive parameter
bounds = ParameterBounds(min_value=5, max_value=50)
param = create_adaptive_parameter(
    name="rsi_period",
    parameter_type=ParameterType.PERIOD,
    base_value=14,
    bounds=bounds,
    adaptation_strategy=AdaptationStrategy.VOLATILITY_BASED
)

# Register with manager
manager = get_adaptive_manager()
manager.register_indicator_parameters("rsi", {"period": param})
```

#### Market Condition Updates
```python
from nautilus_trader_engine.core.interfaces import MarketRegime, RiskLevel

# Update market conditions
condition = MarketCondition(
    volatility=0.3,
    trend_strength=0.7,
    volume_confirmation=0.8,
    market_regime=MarketRegime.BULL,
    risk_level=RiskLevel.MODERATE
)

manager.update_market_condition(condition)
```

### 3. Ensemble Methods

#### Signal Combination
```python
from nautilus_trader_engine.core.ensemble_methods import EnsembleManager, IndicatorSignal
from nautilus_trader_engine.core.interfaces import SignalStrength

# Create ensemble manager
ensemble = EnsembleManager(container)

# Create signals
signals = [
    IndicatorSignal("RSI", "BUY", SignalStrength.STRONG, 0.8, 14),
    IndicatorSignal("MACD", "BUY", SignalStrength.MODERATE, 0.6, 12),
    IndicatorSignal("BB", "HOLD", SignalStrength.WEAK, 0.4, 20)
]

# Combine signals
result = ensemble.combine_signals(signals, EnsembleMethod.WEIGHTED_VOTING)
```

### 4. Validation System

#### Signal Validation
```python
from nautilus_trader_engine.core.validation_system import ValidationManager

# Create validator
validator = ValidationManager(container)

# Validate signal data
signal_data = {
    'signal_type': 'BUY',
    'confidence': 0.85,
    'strength': 'strong',
    'indicator_name': 'RSI'
}

result = await validator.validate_data('signal_validation', signal_data)
```

## Architecture Patterns

### Strategy Implementation Pattern

```python
class MyTradingStrategy:
    def __init__(self):
        self.indicators = {}
        self.signals = []

    async def initialize(self):
        # Set up indicators, event subscriptions, etc.
        pass

    async def on_market_data(self, event):
        # Process market data
        # Update indicators
        # Generate signals
        # Execute trades
        pass

    async def generate_signal(self, data):
        # Implement signal generation logic
        return signal

    async def execute_trade(self, signal):
        # Implement trade execution logic
        pass
```

### Indicator with Adaptation Pattern

```python
class AdaptiveIndicator:
    def __init__(self, name, base_params):
        self.name = name
        self.params = base_params
        self.manager = get_adaptive_manager()

        # Register adaptive parameters
        self.register_adaptive_parameters()

    def register_adaptive_parameters(self):
        # Register parameters with adaptation manager
        pass

    async def update(self, price, volume, timestamp):
        # Adapt parameters based on market conditions
        adapted = await self.manager.adapt_indicator_parameters(self.name)

        # Update indicator with new parameters
        # Calculate new values
        return result
```

## Testing Examples

### Unit Test Pattern

```python
import pytest
from nautilus_trader_engine.core.dependency_injection import DependencyInjectionContainer

class TestMyComponent:
    def setup_method(self):
        self.container = DependencyInjectionContainer()

    def test_my_functionality(self):
        # Arrange
        component = MyComponent(self.container)

        # Act
        result = component.do_something()

        # Assert
        assert result == expected_value
```

### Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_component_integration():
    # Set up full system
    container = get_container()
    event_bus = get_event_bus()

    # Initialize components
    component1 = await Component1.create(container)
    component2 = await Component2.create(container)

    # Execute integration scenario
    await component1.send_data()
    result = await component2.receive_data()

    # Verify integration
    assert result.is_valid()
```

## Performance Optimization Examples

### Memory-Efficient Processing

```python
# Use generators for large datasets
def process_market_data(data_stream):
    for data_point in data_stream:
        # Process one point at a time
        yield process_single_point(data_point)

# Batch processing for efficiency
async def batch_process_signals(signals, batch_size=100):
    for i in range(0, len(signals), batch_size):
        batch = signals[i:i + batch_size]
        await process_batch(batch)
```

### Async/Await Patterns

```python
# Concurrent indicator updates
async def update_all_indicators(data):
    tasks = [
        rsi.update(data),
        macd.update(data),
        bollinger.update(data)
    ]
    results = await asyncio.gather(*tasks)
    return results

# Event-driven processing
async def handle_market_events():
    event_bus = get_event_bus()
    queue = asyncio.Queue()

    # Subscribe to events
    await event_bus.subscribe(EventType.MARKET_DATA, queue.put)

    # Process events
    while True:
        event = await queue.get()
        await process_event(event)
```

## Configuration Examples

### Environment-Based Configuration

```python
import os

class TradingConfig:
    def __init__(self):
        self.environment = os.getenv('TRADING_ENV', 'development')
        self.database_url = os.getenv('DATABASE_URL')
        self.api_key = os.getenv('API_KEY')

    @property
    def is_production(self):
        return self.environment == 'production'

    @property
    def risk_limits(self):
        if self.is_production:
            return {'max_position': 0.1, 'max_loss': 0.02}
        else:
            return {'max_position': 0.5, 'max_loss': 0.10}
```

### Strategy Configuration

```python
@dataclass
class StrategyConfig:
    symbol: str = "AAPL"
    timeframe: str = "1h"
    initial_balance: float = 100000.0
    max_position_size: float = 0.1
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.05

    indicators: Dict[str, Dict] = field(default_factory=lambda: {
        'rsi': {'period': 14, 'overbought': 70, 'oversold': 30},
        'macd': {'fast': 12, 'slow': 26, 'signal': 9},
        'bollinger': {'period': 20, 'std_dev': 2.0}
    })

# Load from YAML/JSON
import yaml
with open('config/strategy.yaml') as f:
    config_dict = yaml.safe_load(f)
    config = StrategyConfig(**config_dict)
```

## Error Handling Patterns

### Graceful Degradation

```python
async def execute_trade_with_fallback(self, signal):
    try:
        # Primary execution method
        return await self.primary_broker.execute_trade(signal)
    except BrokerError:
        try:
            # Fallback broker
            return await self.fallback_broker.execute_trade(signal)
        except BrokerError:
            # Log and handle failure
            await self.log_trade_failure(signal)
            return None
```

### Circuit Breaker Pattern

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = 0
        self.state = 'CLOSED'

    async def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
```

## Contributing

When adding new examples:

1. **Follow naming conventions**: Use descriptive, snake_case names
2. **Include comprehensive docstrings**: Explain what the example demonstrates
3. **Add error handling**: Show proper error handling patterns
4. **Provide configuration**: Include example configuration files
5. **Document dependencies**: List any special requirements
6. **Test examples**: Ensure examples run without errors
7. **Update this README**: Add new examples to the overview

## Running All Examples

```bash
# Run all examples (requires automation script)
python scripts/run_examples.py

# Run examples with specific configuration
python scripts/run_examples.py --config examples/config/demo.yaml

# Run examples in CI environment
python scripts/run_examples.py --ci --verbose
```

## Troubleshooting

### Common Issues

**Import Errors**
- Ensure you're running from the project root
- Check that all dependencies are installed
- Verify Python path includes the project directory

**Asyncio Errors**
- Use `asyncio.run()` for main functions
- Ensure all async functions are properly awaited
- Check for event loop conflicts

**Configuration Issues**
- Verify environment variables are set
- Check configuration file paths
- Ensure required services are running

**Performance Issues**
- Monitor memory usage in long-running examples
- Use profiling tools to identify bottlenecks
- Consider using batch processing for large datasets

For additional help, check the main documentation or create an issue on GitHub.