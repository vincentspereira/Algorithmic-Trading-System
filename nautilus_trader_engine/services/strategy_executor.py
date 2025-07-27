# nautilus_trader_engine/services/strategy_executor.py

"""
This service is responsible for executing trading strategies generated from Blockly.
It connects to the trading gateway to place orders and manages the strategy's lifecycle.
"""

import logging
import asyncio
from nautilus_trader_engine.services.trading_gateway import TradingGateway
from nautilus_trader_engine.services.risk_management_service import RiskManagementService
from nautilus_trader_engine.services.market_data_service import MarketDataService

class StrategyExecutor:
    """
    Executes and manages trading strategies.
    """
    def __init__(
        self,
        trading_gateway: TradingGateway,
        risk_management_service: RiskManagementService,
        market_data_service: MarketDataService,
    ):
        self.trading_gateway = trading_gateway
        self.risk_management_service = risk_management_service
        self.market_data_service = market_data_service
        self.logger = logging.getLogger(self.__class__.__name__)
        self.active_strategies = {}
        self.strategy_contexts = {}
        self.strategy_performance = {}
        self.deployed_strategies = {}
        self.strategy_lifecycle = {}

    async def execute_strategy(self, strategy_id: str, strategy_code: str):
        """
        Executes a strategy based on the provided Python code.

        Args:
            strategy_id (str): A unique identifier for the strategy.
            strategy_code (str): The Python code for the strategy, generated from Blockly.
        """
        if not self.validate_strategy(strategy_code):
            self.logger.error(f"Strategy {strategy_id} failed validation.")
            return

        # In a real-world scenario, this would involve a more complex execution engine
        self.active_strategies[strategy_id] = strategy_code
        self.strategy_contexts[strategy_id] = self._create_strategy_context()
        self.logger.info(f"Strategy {strategy_id} has been loaded and is active.")
        # Periodically run the strategy
        asyncio.create_task(self._run_strategy_loop(strategy_id))

    def validate_strategy(self, strategy_code: str) -> bool:
        """
        Validates the strategy code for safety and correctness.
        For now, this is a placeholder. A real implementation would involve static analysis,
        backtesting, and other checks.

        Args:
            strategy_code (str): The Python code of the strategy.

        Returns:
            bool: True if the strategy is valid, False otherwise.
        """
        # Placeholder for strategy validation logic
        # For example, check for forbidden functions or modules
        if "os." in strategy_code or "subprocess." in strategy_code:
            self.logger.warning("Strategy contains potentially unsafe code.")
            return False
        return True

    def _create_strategy_context(self):
        """
        Creates a new execution context for a strategy.
        """
        return {
            "place_order": self.trading_gateway.place_order,
            "get_market_data": self.market_data_service.get_market_data,
            "get_positions": self.trading_gateway.get_positions,
            "logger": self.logger,
        }

    async def _run_strategy_loop(self, strategy_id: str):
        """
        A simplified function to 'run' the strategy in a loop.
        In a real application, this would be triggered by market data events.
        """
        while strategy_id in self.active_strategies:
            if self._is_safe_to_execute(strategy_id):
                strategy_code = self.active_strategies.get(strategy_id)
                if strategy_code:
                    execution_context = self.strategy_contexts[strategy_id]
                    try:
                        exec(strategy_code, execution_context)
                        self.strategy_performance[strategy_id] = {
                            "status": "running",
                            "last_execution": "success",
                        }
                    except Exception as e:
                        self.logger.error(f"Error executing strategy {strategy_id}: {e}")
                        self.strategy_performance[strategy_id] = {
                            "status": "error",
                            "last_execution": "failed",
                        }
            else:
                self.logger.warning(f"Strategy {strategy_id} is not safe to execute due to risk limits.")
            
            await asyncio.sleep(5)  # Run every 5 seconds

    def stop_strategy(self, strategy_id: str):
        """
        Stops an active strategy.

        Args:
            strategy_id (str): The identifier of the strategy to stop.
        """
        if strategy_id in self.active_strategies:
            del self.active_strategies[strategy_id]
            del self.strategy_contexts[strategy_id]
            self.strategy_performance[strategy_id] = {
                "status": "stopped",
                "last_execution": "n/a",
            }
            self.logger.info(f"Strategy {strategy_id} has been stopped.")

    def get_strategy_performance(self, strategy_id: str) -> dict:
        """
        Retrieves the performance of a specific strategy.

        Args:
            strategy_id (str): The ID of the strategy to check.

        Returns:
            A dictionary containing the strategy's performance.
        """
        return self.strategy_performance.get(strategy_id, {"status": "unknown"})

    def _is_safe_to_execute(self, strategy_id: str) -> bool:
        """
        Checks if the strategy is safe to execute based on risk management rules.
        """
        # In a real application, you would check various risk metrics here
        return self.risk_management_service.get_portfolio_status()["risk_level"] != "CRITICAL"

    def deploy_strategy(self, strategy_id: str, strategy_code: str):
        """
        Deploys a new strategy.

        Args:
            strategy_id (str): A unique identifier for the strategy.
            strategy_code (str): The Python code for the strategy.
        """
        self.deployed_strategies[strategy_id] = strategy_code
        self.strategy_lifecycle[strategy_id] = ["deployed"]
        self.logger.info(f"Strategy {strategy_id} has been deployed.")

    def get_strategy_lifecycle(self, strategy_id: str) -> list:
        """
        Retrieves the lifecycle of a specific strategy.

        Args:
            strategy_id (str): The ID of the strategy to check.

        Returns:
            A list containing the strategy's lifecycle.
        """
        return self.strategy_lifecycle.get(strategy_id, [])

    def get_deployed_strategies(self) -> list:
        """
        Retrieves a list of all deployed strategies.

        Returns:
            A list of deployed strategy IDs.
        """
        return list(self.deployed_strategies.keys())

# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize services
        risk_service = RiskManagementService()
        market_data_service = MarketDataService()
        gateway = TradingGateway(risk_management_service=risk_service)
        strategy_executor = StrategyExecutor(
            trading_gateway=gateway,
            risk_management_service=risk_service,
            market_data_service=market_data_service,
        )

        # Start market data feed
        asyncio.create_task(market_data_service.start_market_data_feed())

        # Connect to the gateway
        await gateway.connect()

        # Example strategy code (usually from Blockly)
        strategy_code_example = """
market_data = get_market_data("EUR/USD")
if market_data.get("bid", 0) > 1.1:
    print("Executing example strategy: Placing a BUY order for EUR/USD")
    # asyncio.run(place_order(
    #     instrument_id="EUR/USD.FX.IDEALPRO",
    #     side="BUY",
    #     quantity=100,
    #     price=1.12,
    #     order_type="LIMIT"
    # ))
"""
        strategy_id_example = "strategy-001"
        await strategy_executor.execute_strategy(strategy_id_example, strategy_code_example)

        # Stop the strategy after some time (for demonstration)
        await asyncio.sleep(10)
        strategy_executor.stop_strategy(strategy_id_example)

        # Disconnect from the gateway
        await gateway.disconnect()
        await market_data_service.stop_market_data_feed()

    asyncio.run(main())