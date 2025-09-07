# Mock risk module for nautilus_trader_engine

class MockRiskManager:
    def __init__(self, *args, **kwargs):
        pass

# Make it available at module level
RiskManager = MockRiskManager
RiskEngine = MockRiskManager