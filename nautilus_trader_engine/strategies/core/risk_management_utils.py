import numpy as np

def calculate_position_size(account_balance, risk_percentage, stop_loss_price, entry_price):
    """
    Calculates the position size based on account balance and risk percentage.
    """
    risk_amount = account_balance * (risk_percentage / 100)
    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share <= 0:
        return 0
    position_size = risk_amount / risk_per_share
    return position_size

def chandelier_exit(high, low, close, atr, period=22, multiplier=3.0):
    """
    Calculates the Chandelier Exit trailing stop-loss.
    """
    long_stop = np.max(high[-period:]) - atr * multiplier
    short_stop = np.min(low[-period:]) + atr * multiplier
    return long_stop, short_stop