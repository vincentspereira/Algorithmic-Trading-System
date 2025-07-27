"""
Real-Time Risk Management Service
This service monitors and controls trading risk in real-time.

Features:
- Position limits and stop-loss mechanisms
- Real-time risk monitoring with alerts
- Risk metrics calculation (VaR, drawdown, exposure)
- Integration with portfolio and trading services

Author: Kilo Code
Version: 2.0.0
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class RiskMetrics:
    """Dataclass for holding risk metrics."""
    value_at_risk_95: float = 0.0
    max_drawdown: float = 0.0
    exposure: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value_at_risk_95": self.value_at_risk_95,
            "max_drawdown": self.max_drawdown,
            "exposure": self.exposure,
            "risk_level": self.risk_level.value,
        }

class RiskManagementService:
    """
    Monitors portfolio risk and enforces trading limits.
    """

    def __init__(
        self,
        max_portfolio_risk: float = 0.1,
        max_trade_risk: float = 0.01,
        stop_loss_pct: float = 0.05,
        position_limit: int = 10,
    ):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_trade_risk = max_trade_risk
        self.stop_loss_pct = stop_loss_pct
        self.position_limit = position_limit
        self.positions: Dict[str, Any] = {}
        self.portfolio_value: float = 100000.0  # Starting portfolio value
        self.historical_values = pd.Series([self.portfolio_value])
        logger.info("RiskManagementService initialized with version 2.0 features.")

    def update_position(self, symbol: str, quantity: int, price: float):
        """
        Updates the quantity and average price of a position.
        """
        if symbol in self.positions:
            current_qty = self.positions[symbol]['quantity']
            new_qty = current_qty + quantity
            if new_qty != 0:
                current_value = self.positions[symbol]['avg_price'] * current_qty
                trade_value = price * quantity
                self.positions[symbol]['avg_price'] = (current_value + trade_value) / new_qty
                self.positions[symbol]['quantity'] = new_qty
            else:
                del self.positions[symbol]
        elif len(self.positions) < self.position_limit:
            self.positions[symbol] = {'quantity': quantity, 'avg_price': price, 'stop_loss': price * (1 - self.stop_loss_pct)}
        else:
            logger.warning(f"Position limit ({self.position_limit}) reached. Cannot open new position for {symbol}.")
            return

        self.update_portfolio_value()
        logger.info(f"Updated position for {symbol}: {self.positions.get(symbol)}")

    def update_portfolio_value(self):
        """Recalculates the total portfolio value based on current positions and prices."""
        # In a real scenario, you would fetch current prices for all positions
        # For simplicity, we'll use the average price here.
        total_position_value = sum(pos['quantity'] * pos['avg_price'] for pos in self.positions.values())
        # Assuming cash balance is tracked elsewhere and updated.
        # Here, we will just track changes based on position values.
        self.portfolio_value += total_position_value - self.portfolio_value
        self.historical_values = self.historical_values.append(pd.Series([self.portfolio_value]))
        if len(self.historical_values) > 1000:  # Keep a rolling window of historical values
            self.historical_values = self.historical_values.iloc[-1000:]

    def check_trade_risk(self, symbol: str, quantity: int, price: float) -> bool:
        """
        Checks if a proposed trade violates risk limits.
        """
        if len(self.positions) >= self.position_limit and symbol not in self.positions:
            logger.warning(f"Position limit reached. Cannot execute trade for {symbol}.")
            return False

        trade_value = quantity * price
        trade_risk = trade_value / self.portfolio_value

        if trade_risk > self.max_trade_risk:
            logger.warning(f"Trade risk for {symbol} ({trade_risk:.2%}) exceeds the limit of {self.max_trade_risk:.2%}.")
            return False

        logger.info(f"Trade risk for {symbol} ({trade_risk:.2%}) is within limits.")
        return True

    def _calculate_risk_metrics(self) -> RiskMetrics:
        """Calculates advanced risk metrics for the portfolio."""
        returns = self.historical_values.pct_change().dropna()
        if returns.empty:
            return RiskMetrics()

        # Value at Risk (VaR) at 95% confidence
        var_95 = returns.quantile(0.05)
        value_at_risk_95 = abs(self.portfolio_value * var_95)

        # Max Drawdown
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = abs(drawdown.min())

        # Exposure
        exposure = sum(abs(pos['quantity'] * pos['avg_price']) for pos in self.positions.values())

        # Determine Risk Level
        risk_level = RiskLevel.LOW
        if max_drawdown > 0.15 or value_at_risk_95 > self.portfolio_value * 0.05:
            risk_level = RiskLevel.CRITICAL
        elif max_drawdown > 0.1 or value_at_risk_95 > self.portfolio_value * 0.03:
            risk_level = RiskLevel.HIGH
        elif max_drawdown > 0.05 or value_at_risk_95 > self.portfolio_value * 0.015:
            risk_level = RiskLevel.MEDIUM

        return RiskMetrics(
            value_at_risk_95=value_at_risk_95,
            max_drawdown=max_drawdown,
            exposure=exposure,
            risk_level=risk_level
        )

    def monitor_risk(self) -> Optional[RiskMetrics]:
        """Monitors all positions for risk violations and emits alerts."""
        for symbol, position in list(self.positions.items()):
            # Mock current price - in production, this would come from a live data feed
            current_price = position['avg_price'] * (1 + np.random.uniform(-0.02, 0.02))
            if current_price <= position['stop_loss']:
                logger.critical(
                    f"STOP-LOSS TRIGGERED for {symbol} at {current_price:.2f}. "
                    f"Stop-loss was at {position['stop_loss']:.2f}. "
                    f"Original quantity: {position['quantity']}."
                )
                # Here you would trigger a sell order
                # For now, we'll just log and remove the position
                del self.positions[symbol]

        metrics = self._calculate_risk_metrics()
        self.log_risk_summary(metrics)
        return metrics

    def log_risk_summary(self, metrics: RiskMetrics):
        """Logs a summary of the current risk metrics."""
        log_level = logging.INFO
        if metrics.risk_level == RiskLevel.HIGH:
            log_level = logging.WARNING
        elif metrics.risk_level == RiskLevel.CRITICAL:
            log_level = logging.CRITICAL

        logger.log(
            log_level,
            f"Risk Summary: Level={metrics.risk_level.value}, "
            f"VaR(95%): ${metrics.value_at_risk_95:,.2f}, "
            f"Max Drawdown: {metrics.max_drawdown:.2%}, "
            f"Exposure: ${metrics.exposure:,.2f}"
        )

    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        Returns the current status of the portfolio, including risk metrics.
        """
        risk_metrics = self.monitor_risk()
        return {
            "portfolio_value": self.portfolio_value,
            "positions": self.positions,
            "risk_metrics": risk_metrics.to_dict() if risk_metrics else {},
        }