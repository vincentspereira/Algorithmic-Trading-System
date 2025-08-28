# Risk Manager Service

This microservice handles real-time risk assessment, portfolio risk monitoring, and risk control mechanisms.

## Core Responsibilities

- Pre-trade risk checks and validation
- Portfolio-level risk monitoring
- Position limit enforcement
- Value-at-Risk (VaR) calculations
- Stress testing and scenario analysis
- Dynamic risk parameter adjustments

## Architecture

The service follows microservices principles:
- Single responsibility for risk management
- Real-time risk calculations
- Event-driven risk monitoring
- Integration with portfolio and market data services
- Configurable risk parameters and limits

## API Endpoints

- `POST /risk/check` - Pre-trade risk check
- `GET /risk/portfolio/{portfolio_id}` - Portfolio risk metrics
- `PUT /risk/limits/{user_id}` - Update risk limits
- `GET /risk/var/{portfolio_id}` - Calculate VaR
- `POST /risk/stress-test` - Run stress test scenarios
- `GET /risk/metrics` - Service health metrics

## Event Integration

### Consumed Events
- `order.pre_trade_check` - Pre-trade risk validation
- `portfolio.position.update` - Position changes
- `market.data.*` - Market data for risk calculations

### Produced Events
- `risk.check.result` - Risk assessment results
- `risk.limit.breach` - Risk limit violations
- `risk.alert.critical` - Critical risk alerts
- `risk.metrics.update` - Updated risk metrics

## Risk Models

The service implements multiple risk models:
- Parametric VaR
- Historical VaR
- Monte Carlo VaR
- Correlation-based risk
- Sector concentration risk
- Liquidity risk assessment

## Configuration

Risk parameters are configurable per user/portfolio:
- Maximum position sizes
- Portfolio concentration limits
- VaR thresholds
- Correlation limits
- Leverage restrictions

## Monitoring

The service provides comprehensive risk monitoring:
- Real-time risk dashboards
- Risk limit breach alerts
- Risk-adjusted performance metrics
- Regulatory reporting capabilities