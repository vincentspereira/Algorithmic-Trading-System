import os
from nautilus_trader.adapters.interactive_brokers.common import IB
from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersDataClientConfig
from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersExecClientConfig
from nautilus_trader.config import TradingNodeConfig, CacheConfig, MessageBusConfig, LiveDataEngineConfig, LiveRiskEngineConfig, LiveExecEngineConfig, PortfolioConfig
from nautilus_trader.model.identifiers import TraderId, Venue

from shared.config import settings

# Common settings for both paper and live trading
IB_HOST = settings.IB_HOST
VENUE = Venue("IB")
# Add symbol mappings as needed
# Example: {"NautilusSymbol": "IBSymbol"}
SYMBOL_MAP = {
    "EUR/USD": "EUR.CASH",
    "AAPL-STK-SMART": "AAPL",
}

def get_ib_paper_trading_config() -> TradingNodeConfig:
    """
    Returns the trading node configuration for paper trading.
    """
    return TradingNodeConfig(
        trader_id=TraderId("PaperTrader-001"),
        cache=CacheConfig(),
        message_bus=MessageBusConfig(),
        data_engine=LiveDataEngineConfig(),
        risk_engine=LiveRiskEngineConfig(),
        exec_engine=LiveExecEngineConfig(),
        portfolio=PortfolioConfig(),
        data_clients={
            IB: InteractiveBrokersDataClientConfig(
                host=IB_HOST,
                port=settings.IB_PAPER_PORT,
                client_id=settings.IB_PAPER_CLIENT_ID,
                account=settings.IB_PAPER_ACCOUNT,
            ),
        },
        exec_clients={
            IB: InteractiveBrokersExecClientConfig(
                host=IB_HOST,
                port=settings.IB_PAPER_PORT,
                client_id=settings.IB_PAPER_CLIENT_ID,
                account=settings.IB_PAPER_ACCOUNT,
            ),
        },
    )

def get_ib_live_trading_config() -> TradingNodeConfig:
    """
    Returns the trading node configuration for live trading.
    """
    return TradingNodeConfig(
        trader_id=TraderId("LiveTrader-001"),
        cache=CacheConfig(),
        message_bus=MessageBusConfig(),
        data_engine=LiveDataEngineConfig(),
        risk_engine=LiveRiskEngineConfig(),
        exec_engine=LiveExecEngineConfig(),
        portfolio=PortfolioConfig(),
        data_clients={
            IB: InteractiveBrokersDataClientConfig(
                host=IB_HOST,
                port=settings.IB_LIVE_PORT,
                client_id=settings.IB_LIVE_CLIENT_ID,
                account=settings.IB_LIVE_ACCOUNT,
            ),
        },
        exec_clients={
            IB: InteractiveBrokersExecClientConfig(
                host=IB_HOST,
                port=settings.IB_LIVE_PORT,
                client_id=settings.IB_LIVE_CLIENT_ID,
                account=settings.IB_LIVE_ACCOUNT,
            ),
        },
    )

def get_ib_trading_node_config(mode: str) -> TradingNodeConfig:
    """
    Returns the trading node configuration for the specified mode.

    :param mode: 'paper' or 'live'
    :return: A TradingNodeConfig instance for the selected mode.
    """
    if mode.lower() == "paper":
        return get_ib_paper_trading_config()
    elif mode.lower() == "live":
        return get_ib_live_trading_config()
    else:
        raise ValueError("Invalid mode specified. Choose 'paper' or 'live'.")

class IBPaperConfig:
    pass

class IBLiveConfig:
    pass