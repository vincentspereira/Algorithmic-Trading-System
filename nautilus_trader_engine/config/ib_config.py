import os

# Optional nautilus_trader imports
try:
    from nautilus_trader.adapters.interactive_brokers.common import IB
    from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersDataClientConfig
    from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersExecClientConfig
    from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveDataClientFactory
    from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveExecClientFactory
    from nautilus_trader.config import TradingNodeConfig, CacheConfig, MessageBusConfig, LiveDataEngineConfig, LiveRiskEngineConfig, LiveExecEngineConfig, PortfolioConfig
    from nautilus_trader.model.identifiers import TraderId, Venue
    NAUTILUS_AVAILABLE = True
except ImportError:
    # Mock classes when nautilus_trader is not available
    class IB:
        pass
    
    class InteractiveBrokersDataClientConfig:
        def __init__(self, **kwargs):
            pass
    
    class InteractiveBrokersExecClientConfig:
        def __init__(self, **kwargs):
            pass
    
    class TradingNodeConfig:
        def __init__(self, **kwargs):
            pass
    
    class CacheConfig:
        def __init__(self, **kwargs):
            pass
    
    class MessageBusConfig:
        def __init__(self, **kwargs):
            pass
    
    class LiveDataEngineConfig:
        def __init__(self, **kwargs):
            pass
    
    class LiveRiskEngineConfig:
        def __init__(self, **kwargs):
            pass
    
    class LiveExecEngineConfig:
        def __init__(self, **kwargs):
            pass
    
    class PortfolioConfig:
        def __init__(self, **kwargs):
            pass
    
    class TraderId:
        def __init__(self, trader_id):
            self.trader_id = trader_id
    
    class Venue:
        def __init__(self, name):
            self.name = name
    
    NAUTILUS_AVAILABLE = False

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
            "IB": InteractiveBrokersDataClientConfig(
                ibg_host=IB_HOST,
                ibg_port=settings.IB_PAPER_PORT,
                ibg_client_id=settings.IB_PAPER_CLIENT_ID,
            ),
        },
        exec_clients={
            "IB": InteractiveBrokersExecClientConfig(
                ibg_host=IB_HOST,
                ibg_port=settings.IB_PAPER_PORT,
                ibg_client_id=settings.IB_PAPER_CLIENT_ID,
                account_id=settings.IB_PAPER_ACCOUNT,
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
            "IB": InteractiveBrokersDataClientConfig(
                ibg_host=IB_HOST,
                ibg_port=settings.IB_LIVE_PORT,
                ibg_client_id=settings.IB_LIVE_CLIENT_ID,
            ),
        },
        exec_clients={
            "IB": InteractiveBrokersExecClientConfig(
                ibg_host=IB_HOST,
                ibg_port=settings.IB_LIVE_PORT,
                ibg_client_id=settings.IB_LIVE_CLIENT_ID,
                account_id=settings.IB_LIVE_ACCOUNT,
            ),
        },
    )

def get_ib_trading_node_config(mode: str) -> TradingNodeConfig:
    """
    Returns the trading node configuration based on the mode.
    """
    if mode == "paper":
        return get_ib_paper_trading_config()
    elif mode == "live":
        return get_ib_live_trading_config()
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'paper' or 'live'.")

class IBPaperConfig:
    pass

class IBLiveConfig:
    pass

class IBCommonConfig:
    """Common configuration for Interactive Brokers adapter."""
    def __init__(self, host="127.0.0.1", port=7497, client_id=1, account=None):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account
        self.symbol_map = SYMBOL_MAP