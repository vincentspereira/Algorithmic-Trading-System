"""Trading-Specific Utility Functions

This module provides utility functions specifically for trading operations:
- Order management utilities
- Position calculations
- Risk management helpers
- Portfolio analysis functions
- Market data processing utilities
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum
import numpy as np
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP

from .shared_utilities import validate_price, validate_quantity, validate_symbol


class OrderSide(Enum):
    """Order side enumeration"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


# =============================================================================
# ORDER MANAGEMENT UTILITIES
# =============================================================================

def calculate_order_value(price: float, quantity: float, 
                         include_fees: bool = True, fee_rate: float = 0.001) -> float:
    """Calculate total order value including fees
    
    Args:
        price: Order price per unit
        quantity: Order quantity
        include_fees: Whether to include trading fees
        fee_rate: Fee rate as decimal (0.001 = 0.1%)
        
    Returns:
        float: Total order value
    """
    price = validate_price(price)
    quantity = validate_quantity(quantity)
    
    base_value = price * quantity
    
    if include_fees:
        fees = base_value * fee_rate
        return base_value + fees
    
    return base_value


def calculate_lot_size(account_balance: float, risk_percentage: float, 
                      entry_price: float, stop_loss_price: float) -> float:
    """Calculate position size based on risk management
    
    Args:
        account_balance: Total account balance
        risk_percentage: Risk percentage as decimal (0.02 = 2%)
        entry_price: Entry price per unit
        stop_loss_price: Stop loss price per unit
        
    Returns:
        float: Calculated lot size
    """
    entry_price = validate_price(entry_price)
    stop_loss_price = validate_price(stop_loss_price)
    
    if entry_price == stop_loss_price:
        raise ValueError("Entry price and stop loss price cannot be equal")
    
    risk_amount = account_balance * risk_percentage
    price_difference = abs(entry_price - stop_loss_price)
    
    lot_size = risk_amount / price_difference
    return max(lot_size, 0.01)  # Minimum lot size


def round_to_tick_size(price: float, tick_size: float = 0.01) -> float:
    """Round price to nearest tick size
    
    Args:
        price: Price to round
        tick_size: Minimum price increment
        
    Returns:
        float: Rounded price
    """
    price = validate_price(price)
    
    if tick_size <= 0:
        raise ValueError("Tick size must be positive")
    
    # Use Decimal for precise rounding
    decimal_price = Decimal(str(price))
    decimal_tick = Decimal(str(tick_size))
    
    rounded = (decimal_price / decimal_tick).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * decimal_tick
    return float(rounded)


# =============================================================================
# POSITION CALCULATIONS
# =============================================================================

def calculate_position_pnl(entry_price: float, current_price: float, 
                          quantity: float, side: PositionSide) -> float:
    """Calculate unrealized P&L for a position
    
    Args:
        entry_price: Entry price per unit
        current_price: Current market price per unit
        quantity: Position quantity
        side: Position side (LONG/SHORT)
        
    Returns:
        float: Unrealized P&L
    """
    entry_price = validate_price(entry_price)
    current_price = validate_price(current_price)
    quantity = validate_quantity(quantity)
    
    price_diff = current_price - entry_price
    
    if side == PositionSide.LONG:
        return price_diff * quantity
    elif side == PositionSide.SHORT:
        return -price_diff * quantity
    else:
        return 0.0


def calculate_position_return(entry_price: float, current_price: float, 
                            side: PositionSide) -> float:
    """Calculate position return percentage
    
    Args:
        entry_price: Entry price per unit
        current_price: Current market price per unit
        side: Position side (LONG/SHORT)
        
    Returns:
        float: Return percentage
    """
    entry_price = validate_price(entry_price)
    current_price = validate_price(current_price)
    
    if entry_price == 0:
        return 0.0
    
    price_change = (current_price - entry_price) / entry_price
    
    if side == PositionSide.LONG:
        return price_change * 100
    elif side == PositionSide.SHORT:
        return -price_change * 100
    else:
        return 0.0


def calculate_average_price(trades: List[Dict]) -> float:
    """Calculate volume-weighted average price from trades
    
    Args:
        trades: List of trade dictionaries with 'price' and 'quantity' keys
        
    Returns:
        float: Volume-weighted average price
    """
    if not trades:
        return 0.0
    
    total_value = 0.0
    total_quantity = 0.0
    
    for trade in trades:
        price = validate_price(trade['price'])
        quantity = validate_quantity(trade['quantity'])
        
        total_value += price * quantity
        total_quantity += quantity
    
    if total_quantity == 0:
        return 0.0
    
    return total_value / total_quantity


# =============================================================================
# RISK MANAGEMENT UTILITIES
# =============================================================================

def calculate_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """Calculate Value at Risk (VaR)
    
    Args:
        returns: Series of returns
        confidence_level: Confidence level (0.95 = 95%)
        
    Returns:
        float: VaR value
    """
    if returns.empty:
        return 0.0
    
    return np.percentile(returns, (1 - confidence_level) * 100)


def calculate_max_drawdown(equity_curve: pd.Series) -> Tuple[float, datetime, datetime]:
    """Calculate maximum drawdown from equity curve
    
    Args:
        equity_curve: Series of equity values with datetime index
        
    Returns:
        Tuple: (max_drawdown_pct, peak_date, trough_date)
    """
    if equity_curve.empty:
        return 0.0, None, None
    
    # Calculate running maximum (peak)
    peak = equity_curve.expanding().max()
    
    # Calculate drawdown
    drawdown = (equity_curve - peak) / peak
    
    # Find maximum drawdown
    max_dd_idx = drawdown.idxmin()
    max_drawdown = drawdown.min()
    
    # Find peak before maximum drawdown
    peak_idx = peak[:max_dd_idx].idxmax()
    
    return abs(max_drawdown) * 100, peak_idx, max_dd_idx


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio
    
    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annual)
        
    Returns:
        float: Sharpe ratio
    """
    if returns.empty or returns.std() == 0:
        return 0.0
    
    # Convert annual risk-free rate to period rate
    periods_per_year = 252  # Assuming daily returns
    period_rf_rate = risk_free_rate / periods_per_year
    
    excess_returns = returns - period_rf_rate
    
    return excess_returns.mean() / returns.std() * np.sqrt(periods_per_year)


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Calculate Sortino ratio
    
    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annual)
        
    Returns:
        float: Sortino ratio
    """
    if returns.empty:
        return 0.0
    
    # Convert annual risk-free rate to period rate
    periods_per_year = 252  # Assuming daily returns
    period_rf_rate = risk_free_rate / periods_per_year
    
    excess_returns = returns - period_rf_rate
    downside_returns = excess_returns[excess_returns < 0]
    
    if downside_returns.empty or downside_returns.std() == 0:
        return float('inf') if excess_returns.mean() > 0 else 0.0
    
    downside_deviation = downside_returns.std()
    
    return excess_returns.mean() / downside_deviation * np.sqrt(periods_per_year)


# =============================================================================
# PORTFOLIO ANALYSIS UTILITIES
# =============================================================================

def calculate_portfolio_value(positions: List[Dict], current_prices: Dict[str, float]) -> float:
    """Calculate total portfolio value
    
    Args:
        positions: List of position dictionaries with 'symbol', 'quantity', 'side'
        current_prices: Dictionary mapping symbols to current prices
        
    Returns:
        float: Total portfolio value
    """
    total_value = 0.0
    
    for position in positions:
        symbol = validate_symbol(position['symbol'])
        quantity = validate_quantity(abs(position['quantity']))
        side = position.get('side', PositionSide.LONG)
        
        if symbol not in current_prices:
            logging.warning(f"No price available for symbol: {symbol}")
            continue
        
        current_price = validate_price(current_prices[symbol])
        
        if side == PositionSide.LONG:
            position_value = current_price * quantity
        elif side == PositionSide.SHORT:
            # For short positions, value is negative
            position_value = -current_price * quantity
        else:
            position_value = 0.0
        
        total_value += position_value
    
    return total_value


def calculate_portfolio_weights(positions: List[Dict], current_prices: Dict[str, float]) -> Dict[str, float]:
    """Calculate portfolio weights by symbol
    
    Args:
        positions: List of position dictionaries
        current_prices: Dictionary mapping symbols to current prices
        
    Returns:
        Dict: Symbol to weight mapping
    """
    total_value = calculate_portfolio_value(positions, current_prices)
    
    if total_value == 0:
        return {}
    
    weights = {}
    
    for position in positions:
        symbol = validate_symbol(position['symbol'])
        quantity = validate_quantity(abs(position['quantity']))
        side = position.get('side', PositionSide.LONG)
        
        if symbol not in current_prices:
            continue
        
        current_price = validate_price(current_prices[symbol])
        
        if side == PositionSide.LONG:
            position_value = current_price * quantity
        elif side == PositionSide.SHORT:
            position_value = -current_price * quantity
        else:
            position_value = 0.0
        
        weights[symbol] = position_value / total_value
    
    return weights


# =============================================================================
# MARKET DATA PROCESSING UTILITIES
# =============================================================================

def calculate_vwap(prices: pd.Series, volumes: pd.Series) -> pd.Series:
    """Calculate Volume Weighted Average Price
    
    Args:
        prices: Price series
        volumes: Volume series
        
    Returns:
        pd.Series: VWAP series
    """
    if len(prices) != len(volumes):
        raise ValueError("Prices and volumes must have same length")
    
    cumulative_pv = (prices * volumes).cumsum()
    cumulative_volume = volumes.cumsum()
    
    # Avoid division by zero
    vwap = cumulative_pv / cumulative_volume.replace(0, np.nan)
    
    return vwap.fillna(method='ffill')


def calculate_typical_price(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calculate typical price (HLC/3)
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        
    Returns:
        pd.Series: Typical price series
    """
    return (high + low + close) / 3


def calculate_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Calculate True Range
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        
    Returns:
        pd.Series: True Range series
    """
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def detect_gaps(open_prices: pd.Series, prev_close: pd.Series, 
               threshold: float = 0.02) -> pd.Series:
    """Detect price gaps
    
    Args:
        open_prices: Opening price series
        prev_close: Previous close price series
        threshold: Gap threshold as percentage (0.02 = 2%)
        
    Returns:
        pd.Series: Boolean series indicating gaps
    """
    gap_percentage = abs(open_prices - prev_close) / prev_close
    return gap_percentage > threshold


# =============================================================================
# UTILITY FUNCTIONS FOR BACKTESTING
# =============================================================================

def calculate_trade_statistics(trades: List[Dict]) -> Dict[str, float]:
    """Calculate comprehensive trade statistics
    
    Args:
        trades: List of completed trade dictionaries
        
    Returns:
        Dict: Trade statistics
    """
    if not trades:
        return {}
    
    pnls = [trade.get('pnl', 0) for trade in trades]
    winning_trades = [pnl for pnl in pnls if pnl > 0]
    losing_trades = [pnl for pnl in pnls if pnl < 0]
    
    stats = {
        'total_trades': len(trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': len(winning_trades) / len(trades) * 100 if trades else 0,
        'total_pnl': sum(pnls),
        'average_win': np.mean(winning_trades) if winning_trades else 0,
        'average_loss': np.mean(losing_trades) if losing_trades else 0,
        'largest_win': max(winning_trades) if winning_trades else 0,
        'largest_loss': min(losing_trades) if losing_trades else 0,
        'profit_factor': abs(sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf')
    }
    
    return stats


def calculate_equity_curve(trades: List[Dict], initial_balance: float = 100000) -> pd.Series:
    """Calculate equity curve from trades
    
    Args:
        trades: List of completed trade dictionaries with 'timestamp' and 'pnl'
        initial_balance: Starting account balance
        
    Returns:
        pd.Series: Equity curve with datetime index
    """
    if not trades:
        return pd.Series([initial_balance], index=[datetime.now(timezone.utc)])
    
    # Sort trades by timestamp
    sorted_trades = sorted(trades, key=lambda x: x.get('timestamp', datetime.now(timezone.utc)))
    
    timestamps = []
    equity_values = []
    
    current_equity = initial_balance
    
    for trade in sorted_trades:
        timestamp = trade.get('timestamp', datetime.now(timezone.utc))
        pnl = trade.get('pnl', 0)
        
        current_equity += pnl
        
        timestamps.append(timestamp)
        equity_values.append(current_equity)
    
    return pd.Series(equity_values, index=timestamps)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test order calculations
    order_value = calculate_order_value(100.0, 10, include_fees=True)
    print(f"Order value with fees: ${order_value:.2f}")
    
    # Test position calculations
    pnl = calculate_position_pnl(100.0, 105.0, 10, PositionSide.LONG)
    print(f"Position P&L: ${pnl:.2f}")
    
    # Test risk calculations
    returns = pd.Series([0.01, -0.02, 0.015, -0.01, 0.005])
    sharpe = calculate_sharpe_ratio(returns)
    print(f"Sharpe ratio: {sharpe:.4f}")