# Mock strategies module for nautilus_trader_engine

class MockStrategyManager:
    def __init__(self, *args, **kwargs):
        pass

# Make it available at module level
StrategyManager = MockStrategyManager
StrategyEngine = MockStrategyManager