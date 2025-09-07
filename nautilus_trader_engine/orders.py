# Mock orders module for nautilus_trader_engine

class MockOrderManager:
    def __init__(self, *args, **kwargs):
        pass

# Make it available at module level
OrderManager = MockOrderManager
OrderExecutionEngine = MockOrderManager