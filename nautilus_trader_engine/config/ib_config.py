"""
ib_config.py

Configuration for the Interactive Brokers adapter.

This file defines settings for connecting to the IB Gateway/TWS for both paper
and live trading environments. It includes connection parameters, account
details, and symbol mappings.
"""

from nautilus_trader.config import PaperTradingConfig, LiveTradingConfig, TradingNodeConfig
from nautilus_trader.model.identifiers import Venue

# Common settings for both paper and live trading
class IBCommonConfig:
    HOST = "127.0.0.1"
    CLIENT_ID_BASE = 100
    VENUE = Venue("IB")
    # Add symbol mappings as needed
    # Example: {"NautilusSymbol": "IBSymbol"}
    SYMBOL_MAP = {
        "EUR/USD": "EUR.CASH",
        "AAPL-STK-SMART": "AAPL",
    }

# Paper Trading Configuration
class IBPaperConfig(PaperTradingConfig, IBCommonConfig):
    """
    Configuration for paper trading with Interactive Brokers TWS.
    """
    NAME = "IB_PAPER"
    PORT = 7497  # Default TWS paper trading port
    CLIENT_ID = IBCommonConfig.CLIENT_ID_BASE + 1
    ACCOUNT_ID = "DU1234567"  # Replace with your paper trading account ID

# Live Trading Configuration
class IBLiveConfig(LiveTradingConfig, IBCommonConfig):
    """
    Configuration for live trading with Interactive Brokers TWS/Gateway.
    """
    NAME = "IB_LIVE"
    PORT = 7496  # Default TWS live trading port
    CLIENT_ID = IBCommonConfig.CLIENT_ID_BASE + 2
    ACCOUNT_ID = "U1234567"  # Replace with your live trading account ID

def get_ib_trading_node_config(mode: str) -> TradingNodeConfig:
    """
    Returns the trading node configuration for the specified mode.

    :param mode: 'paper' or 'live'
    :return: A TradingNodeConfig instance for the selected mode.
    """
    if mode.lower() == "paper":
        return TradingNodeConfig(
            name=IBPaperConfig.NAME,
            connection_config=IBPaperConfig(),
        )
    elif mode.lower() == "live":
        return TradingNodeConfig(
            name=IBLiveConfig.NAME,
            connection_config=IBLiveConfig(),
        )
    else:
        raise ValueError("Invalid mode specified. Choose 'paper' or 'live'.")