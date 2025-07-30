# Asset Class Framework Documentation

## Overview

The Asset Class Framework provides a unified system for handling multiple asset classes including equities, options, futures, bonds, and cryptocurrencies. It offers asset-specific pricing models, risk calculations, and lifecycle management.

## Key Features

- **Multi-Asset Support**: Unified framework for equities, options, bonds, futures, and cryptocurrencies
- **Asset-Specific Pricing Models**: Specialized pricing algorithms for each asset class
- **Risk Metrics Calculation**: Comprehensive risk analysis including Greeks for options
- **Lifecycle Management**: Handles corporate actions, expiries, and other lifecycle events
- **Factory Functions**: Easy asset creation with sensible defaults

## Architecture

### Core Components

1. **Asset Specifications**: Data classes defining asset properties
2. **Pricing Models**: Asset-specific pricing algorithms
3. **Framework Manager**: Central orchestration and registry
4. **Factory Functions**: Convenient asset creation utilities

### Asset Classes Supported

- **Equity**: Stocks with fundamental analysis support
- **Options**: European/American options with Black-Scholes pricing
- **Bonds**: Fixed income securities with yield curve analysis
- **Futures**: Derivative contracts with cost-of-carry models
- **Cryptocurrencies**: Digital assets with network-based valuation

## Usage Examples

### Basic Setup

```python
import asyncio
from datetime import datetime
from nautilus_trader_engine.assets.asset_class_framework import (
    AssetClassFramework, OptionType,
    create_equity_asset, create_option_asset
)

# Initialize framework
framework = AssetClassFramework()
```

### Creating Assets

```python
# Create equity asset
equity = create_equity_asset(
    symbol="AAPL",
    name="Apple Inc.",
    current_price=150.0,
    pe_ratio=25.0,
    dividend_yield=0.005
)

# Create option asset
option = create_option_asset(
    symbol="AAPL240315C00150000",
    underlying_symbol="AAPL",
    option_type=OptionType.CALL,
    strike_price=150.0,
    current_price=5.0,
    implied_volatility=0.25
)
```

### Asset Registration and Pricing

```python
async def main():
    # Register assets
    await framework.register_asset(equity)
    await framework.register_asset(option)
    
    # Calculate theoretical prices
    equity_price = await framework.calculate_theoretical_price(
        "AAPL", 
        method="pe_multiple",
        target_pe=20.0
    )
    
    option_price = await framework.calculate_theoretical_price(
        "AAPL240315C00150000",
        underlying_price=155.0,
        time_to_expiry=0.25
    )
    
    print(f"Equity theoretical price: ${equity_price:.2f}")
    print(f"Option theoretical price: ${option_price:.2f}")
```

### Risk Metrics Calculation

```python
async def calculate_risk():
    # Equity risk metrics
    equity_risk = await framework.calculate_risk_metrics("AAPL")
    print(f"Equity volatility: {equity_risk['volatility']:.4f}")
    print(f"Sharpe ratio: {equity_risk['sharpe_ratio']:.4f}")
    
    # Option Greeks
    option_risk = await framework.calculate_risk_metrics(
        "AAPL240315C00150000",
        underlying_price=155.0
    )
    print(f"Delta: {option_risk['delta']:.4f}")
    print(f"Gamma: {option_risk['gamma']:.6f}")
    print(f"Vega: {option_risk['vega']:.4f}")
```

## Asset Specifications

### EquitySpecification

Properties specific to equity assets:
- `market_cap`: Market capitalization
- `pe_ratio`: Price-to-earnings ratio
- `dividend_yield`: Annual dividend yield
- `sector`: Industry sector
- `shares_outstanding`: Number of shares

### OptionSpecification

Properties specific to options:
- `underlying_symbol`: Symbol of underlying asset
- `option_type`: CALL or PUT
- `strike_price`: Exercise price
- `expiry_date`: Expiration date
- `implied_volatility`: Market implied volatility

## Pricing Models

### Equity Pricing Model

Supports multiple valuation methods:
- **P/E Multiple**: Price based on earnings multiple
- **Dividend Discount Model**: DCF based on dividends
- **DCF Model**: Discounted cash flow analysis

### Option Pricing Model

Black-Scholes implementation:
- European option pricing
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Handles expired options correctly
- Supports both calls and puts

## Risk Metrics

### Equity Risk Metrics
- Volatility (annualized)
- Sharpe ratio
- Value at Risk (VaR)
- Expected shortfall
- Maximum drawdown

### Option Risk Metrics (Greeks)
- **Delta**: Price sensitivity to underlying
- **Gamma**: Delta sensitivity to underlying
- **Theta**: Time decay
- **Vega**: Volatility sensitivity
- **Rho**: Interest rate sensitivity

## Framework Management

### Asset Registry
- Central storage for all registered assets
- Fast lookup by symbol
- Asset class filtering
- Active/inactive status tracking

### Batch Operations
- Portfolio-level calculations
- Correlation matrix generation
- Multi-asset risk analysis
- Performance attribution

## Error Handling

The framework includes comprehensive error handling:
- Graceful degradation for missing data
- Logging of calculation failures
- Fallback to current prices when models fail
- Validation of asset data integrity

## Performance Considerations

- Async/await pattern for non-blocking operations
- Efficient numpy-based calculations
- Caching of frequently accessed data
- Batch processing capabilities

## Testing

Comprehensive test suite includes:
- Unit tests for each pricing model
- Integration tests for framework operations
- Edge case handling (expired options, invalid data)
- Performance benchmarks

Run tests with:
```bash
python -m pytest tests/test_asset_class_framework_simple.py -v
```

## Future Enhancements

Planned improvements:
- Real-time market data integration
- Advanced option models (American, exotic)
- Fixed income yield curve modeling
- Cryptocurrency network metrics
- Machine learning-based pricing models

## API Reference

### AssetClassFramework

Main framework class for asset management.

#### Methods

- `register_asset(asset)`: Register new asset
- `get_asset(symbol)`: Retrieve asset by symbol
- `calculate_theoretical_price(symbol, **kwargs)`: Calculate fair value
- `calculate_risk_metrics(symbol, **kwargs)`: Calculate risk measures
- `get_assets_by_class(asset_class)`: Filter by asset class
- `get_active_assets()`: Get all active assets

### Factory Functions

- `create_equity_asset(symbol, name, **kwargs)`: Create equity
- `create_option_asset(symbol, underlying, type, strike, **kwargs)`: Create option

### Pricing Models

- `EquityPricingModel`: Equity valuation methods
- `OptionPricingModel`: Black-Scholes implementation

## Examples

See `nautilus_trader_engine/assets/asset_class_framework.py` for complete examples and the `example_usage()` function for a comprehensive demonstration.