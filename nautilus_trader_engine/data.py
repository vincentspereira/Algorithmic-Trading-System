# Mock data module for nautilus_trader_engine

class MockDataManager:
    def __init__(self, *args, **kwargs):
        pass

# Make it available at module level
DataManager = MockDataManager
MarketDataManager = MockDataManager
DataFeedManager = MockDataManager