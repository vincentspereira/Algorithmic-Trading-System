import random
from datetime import datetime
from nautilus_trader_engine.api.models.trading import (
    PortfolioResponse,
    PortfolioPosition,
    OrderResponse,
    RiskSnapshot,
    PositionGreeks,
)

def generate_mock_portfolio() -> PortfolioResponse:
    """Generates a mock portfolio with realistic data."""
    positions = [
        PortfolioPosition(symbol="AAPL", quantity=100, average_price=175.25, market_value=175.25 * 100 * random.uniform(0.98, 1.02)),
        PortfolioPosition(symbol="GOOGL", quantity=50, average_price=2800.50, market_value=2800.50 * 50 * random.uniform(0.98, 1.02)),
        PortfolioPosition(symbol="TSLA", quantity=25, average_price=700.00, market_value=700.00 * 25 * random.uniform(0.98, 1.02)),
    ]
    cash = 100000.0
    total_value = cash + sum(p.market_value for p in positions)
    return PortfolioResponse(cash=cash, positions=positions, total_value=total_value)

order_history = []

def generate_mock_orders(limit: int = 50) -> list[OrderResponse]:
    """Generates a list of historical mock orders."""
    if not order_history:
        for _ in range(20):
            order = OrderResponse(
                symbol=random.choice(["AAPL", "GOOGL", "TSLA", "MSFT"]),
                quantity=random.randint(1, 100),
                order_type=random.choice(["MARKET", "LIMIT"]),
                price=round(random.uniform(100, 3000), 2) if random.choice([True, False]) else None,
                side=random.choice(["BUY", "SELL"]),
                status=random.choice(["FILLED", "CANCELLED", "PENDING"]),
            )
            order_history.append(order)
    return order_history[:limit]

def generate_mock_risk_metrics() -> RiskSnapshot:
    """Generates mock risk metrics including Greeks and VaR."""
    greeks = [
        PositionGreeks(symbol="AAPL", delta=0.5, gamma=0.05, theta=-0.1, vega=0.2),
        PositionGreeks(symbol="GOOGL", delta=0.7, gamma=0.02, theta=-0.05, vega=0.15),
        PositionGreeks(symbol="TSLA", delta=0.9, gamma=0.01, theta=-0.2, vega=0.3),
    ]
    concentration = {
        "by_sector": {"Technology": 0.8, "Consumer Discretionary": 0.2},
        "by_asset_class": {"Equity": 1.0},
    }
    return RiskSnapshot(
        portfolio_var=random.uniform(5000, 15000),
        position_greeks=greeks,
        concentration_metrics=concentration,
    )