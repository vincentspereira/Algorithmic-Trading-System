# Portfolio Manager Service

This microservice manages portfolio state, position tracking, and performance attribution.

## Core Responsibilities

- Real-time portfolio state management
- Position tracking and reconciliation
- Performance attribution analysis
- Portfolio rebalancing recommendations
- Asset allocation monitoring
- P&L calculations and reporting

## Architecture

The service follows microservices principles:
- Authoritative source for portfolio data
- Real-time position updates
- Event-driven portfolio updates
- Integration with order and market data services
- Cached portfolio state for low-latency access

## API Endpoints

- `GET /portfolios/{portfolio_id}` - Get portfolio details
- `GET /portfolios/{portfolio_id}/positions` - Get portfolio positions
- `GET /portfolios/{portfolio_id}/performance` - Performance metrics
- `POST /portfolios/{portfolio_id}/rebalance` - Generate rebalancing plan
- `GET /portfolios/{portfolio_id}/pnl` - P&L analysis
- `PUT /portfolios/{portfolio_id}/allocation` - Update target allocation

## Event Integration

### Consumed Events
- `order.filled` - Trade execution updates
- `market.data.price` - Price updates for P&L
- `dividend.payment` - Corporate actions

### Produced Events
- `portfolio.state.update` - Portfolio state changes
- `portfolio.rebalance.required` - Rebalancing alerts
- `portfolio.performance.update` - Performance updates
- `position.reconciliation.mismatch` - Position discrepancies

## Data Management

The service maintains:
- Real-time portfolio positions
- Historical performance data
- Asset allocation targets
- Benchmark comparisons
- Risk-adjusted returns

## Performance Analytics

Advanced portfolio analytics:
- Sharpe ratio calculations
- Alpha and beta analysis
- Maximum drawdown tracking
- Sector attribution analysis
- Factor exposure analysis

## Integration Points

- Order Management Service (trade updates)
- Market Data Service (pricing data)
- Risk Manager Service (risk metrics)
- Accounting Service (settlement data)