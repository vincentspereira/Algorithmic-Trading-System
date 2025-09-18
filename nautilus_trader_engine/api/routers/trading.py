
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_trading_status():
    return {"status": "Trading router placeholder"}


# Minimal dummy trading gateway used by api.main during tests/startup
class DummyTradingGateway:
    async def connect(self):
        # No-op connection for tests
        return None

    async def disconnect(self):
        # No-op disconnect for tests
        return None

    async def get_positions(self):
        # Return empty positions by default
        return {}

    async def place_order(self, instrument_id: str, side: str, quantity: float, price: float | None = None, order_type: str = "MARKET"):
        # Return a minimal order dict compatible with OrderResponse model usage in api.main
        return {
            "order_id": "test-order-1",
            "symbol": instrument_id,
            "quantity": quantity,
            "order_type": order_type,
            "price": price,
            "side": side,
            "status": "PENDING",
        }

    async def cancel_order(self, order_id: str) -> bool:
        # Always report success in tests
        return True


# Expose the dummy gateway so api.main can import and use it
trading_gateway = DummyTradingGateway()
