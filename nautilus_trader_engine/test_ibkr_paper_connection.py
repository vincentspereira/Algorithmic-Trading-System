import asyncio
import sys

from nautilus_trader.adapters.interactive_brokers.config import InteractiveBrokersDataClientConfig, InteractiveBrokersExecClientConfig
from nautilus_trader.adapters.interactive_brokers.factories import InteractiveBrokersLiveDataClientFactory, InteractiveBrokersLiveExecClientFactory
from nautilus_trader.config import TradingNodeConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.live.node import TradingNode


async def main(mode: str = "paper"):
    if mode not in ["paper", "live"]:
        print("Invalid mode. Use 'paper' or 'live'")
        sys.exit(1)

    port = 7497 if mode == "paper" else 7496
    account_id = "YOUR_PAPER_ACCOUNT_ID" if mode == "paper" else "YOUR_LIVE_ACCOUNT_ID"  # Replace with actual IDs

    config = TradingNodeConfig(
        logging=LoggingConfig(log_level="INFO"),
        data_clients={
            "IB": InteractiveBrokersDataClientConfig(
                ibg_host="127.0.0.1",
                ibg_port=port,
                ibg_client_id=1,
            ),
        },
        exec_clients={
            "IB": InteractiveBrokersExecClientConfig(
                ibg_host="127.0.0.1",
                ibg_port=port,
                ibg_client_id=1,
                account_id=account_id,
            ),
        },
    )

    node = TradingNode(config=config)
    node.add_data_client_factory("IB", InteractiveBrokersLiveDataClientFactory)
    node.add_exec_client_factory("IB", InteractiveBrokersLiveExecClientFactory)
    node.build()
    await node.run_async()

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "paper"
    asyncio.run(main(mode))