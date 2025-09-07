# Mock portfolio module for nautilus_trader_engine

class MockPortfolioManager:
    def __init__(self, *args, **kwargs):
        pass

# Make it available at module level
MultiAssetPortfolioManager = MockPortfolioManager
PortfolioManager = MockPortfolioManager