import unittest
from nautilus_trader_engine.strategies.core.strategy_factory import create_strategy
from nautilus_trader_engine.strategies.momentum.augmented_momentum_strategy import AugmentedMomentumStrategy

class TestStrategyFactory(unittest.TestCase):
    def test_create_augmented_momentum_strategy(self):
        """
        Tests that the strategy factory can create an AugmentedMomentumStrategy.
        """
        strategy = create_strategy(
            category="augmented_strategies",
            blueprint_name="augmented_momentum"
        )
        self.assertIsInstance(strategy, AugmentedMomentumStrategy)

if __name__ == "__main__":
    unittest.main()