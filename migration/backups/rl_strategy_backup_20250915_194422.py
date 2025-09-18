# nautilus_trader_engine/strategies/rl_strategy.py

"""
Base strategy class for reinforcement learning models.

This module provides a strategy that integrates a trained RL agent with the
NautilusTrader's event-driven backtesting engine.
"""

from nautilus_trader.model.data import Bar
from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.strategy import Strategy
from stable_baselines3.common.base_class import BaseAlgorithm

from nautilus_trader_engine.rl.environment import NautilusTradingEnv


class RLStrategy(Strategy):
    """
    A strategy that uses a pre-trained RL agent to make trading decisions.
    """

    def __init__(
        self,
        instrument_id: InstrumentId,
        model: BaseAlgorithm,
        capital_base: float,
        window_size: int = 30,
    ):
        super().__init__()
        self.instrument_id = instrument_id
        self.model = model
        self.capital_base = capital_base
        self.window_size = window_size
        self.bars = []
        self.portfolio_history = []

    def on_start(self):
        """Initializes the strategy at the start of the backtest."""
        self.subscribe_bars(self.instrument_id)
        self.portfolio_history.append((self.clock.timestamp, self.portfolio.equity()))

    def on_bar(self, bar: Bar):
        """
        Called on each new bar of data.
        """
        self.bars.append(bar)
        if len(self.bars) < self.window_size:
            return

        # Prepare observation from the latest bars
        observation = self._prepare_observation()

        # Get action from the RL model
        action, _ = self.model.predict(observation, deterministic=True)
        self._execute_trade(action)
        
        # Update portfolio history
        self.portfolio_history.append((self.clock.timestamp, self.portfolio.equity()))

    def on_order_filled(self, order_filled: OrderFilled):
        """
        Called when an order is filled.
        """
        self.log.info(f"FILLED: {order_filled.order}")

    def on_stop(self):
        """
        Called at the end of the backtest.
        """
        self.log.info("Backtest finished.")
        self.log.info(f"Final portfolio value: {self.portfolio.equity()}")

    def _prepare_observation(self) -> dict:
        """
        Prepares the observation dictionary for the RL model.
        """
        # This needs to be consistent with the environment's observation space
        # This is a simplified example; a real implementation would process
        # the bars into features (e.g., technical indicators).
        
        # Creating a dummy observation for now
        # In a real scenario, you'd use a feature extractor here
        dummy_features = [bar.close for bar in self.bars[-self.window_size:]]
        
        # The observation needs to match the structure expected by the model's policy
        # For a simple MlpPolicy, a flat array works.
        # If using a MultiInputPolicy, it would be a dictionary.
        return {"features": dummy_features}

    def _execute_trade(self, action: int):
        """
        Executes a trade based on the RL agent's action.
        """
        # Example for a discrete action space (0: Hold, 1: Buy, 2: Sell)
        if action == 1:  # Buy
            position = self.portfolio.get_position(self.instrument_id)
            if not position or position.is_short:
                # Close short position before going long
                if position:
                    self.close_position(position)
                # Simple logic: invest a fixed portion of equity
                self.buy(self.instrument_id, self.capital_base * 0.1 / self.bars[-1].close)
        elif action == 2:  # Sell
            position = self.portfolio.get_position(self.instrument_id)
            if not position or position.is_long:
                if position:
                    self.close_position(position)
                self.sell(self.instrument_id, self.capital_base * 0.1 / self.bars[-1].close)
        # Action 0 is "Hold", so no action is taken