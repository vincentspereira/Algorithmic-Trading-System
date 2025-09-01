
from fastapi import APIRouter, Depends

from app.models import APIResponse
from nautilus_trader_engine.core.order_management import OrderManager
from app.core.security import verify_token

router = APIRouter()
order_manager = OrderManager()

@router.get("/portfolio/positions")
async def get_portfolio_positions(user: dict = Depends(verify_token)):
    """Get user's portfolio positions"""
    try:
        positions = await order_manager.get_positions(user["user_id"])

        portfolio_summary = {
            "total_value": sum(pos.get("market_value", 0) for pos in positions),
            "total_pnl": sum(pos.get("unrealized_pnl", 0) for pos in positions),
            "position_count": len(positions),
            "last_updated": datetime.now()
        }

        return APIResponse(
            success=True,
            data={"positions": positions, "summary": portfolio_summary},
            message=f"Retrieved {len(positions)} positions"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve positions: {str(e)}")

@router.get("/portfolio/performance")
async def get_portfolio_performance(
    period: str = "1d",
    user: dict = Depends(verify_token)
):
    """Get portfolio performance metrics"""
    try:
        performance = await order_manager.get_portfolio_performance(
            user_id=user["user_id"],
            period=period
        )

        return APIResponse(
            success=True,
            data=performance,
            message=f"Portfolio performance for {period}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance: {str(e)}")
