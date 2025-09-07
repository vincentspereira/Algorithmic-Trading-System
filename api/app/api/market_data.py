
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from api.app.models import APIResponse, MarketDataRequest
from api.app.utils import get_cache_key, get_cached_data, set_cached_data
from nautilus_trader_engine.core.data_feed_manager import DataFeedManager
from app.core.security import verify_token

router = APIRouter()
data_feed_manager = DataFeedManager()

@router.post("/market-data", response_model=APIResponse)
async def get_market_data(
    request: MarketDataRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_token)
):
    """Get historical market data for symbols"""
    try:
        # Check cache first
        cache_key = get_cache_key("market_data",
                                symbols=[s.symbol for s in request.symbols],
                                period=request.period,
                                interval=request.interval)

        cached_data = await get_cached_data(cache_key)
        if cached_data:
            return APIResponse(success=True, data=cached_data, message="Data retrieved from cache")

        # Fetch fresh data
        results = {}
        for symbol in request.symbols:
            try:
                data = await data_feed_manager.get_historical_data(
                    symbol=symbol.symbol,
                    period=request.period,
                    interval=request.interval,
                    start_date=request.start_date,
                    end_date=request.end_date
                )
                # Convert DataFrame to JSON-serializable format
                if hasattr(data, 'to_dict'):
                    data_dict = data.to_dict('records')
                    results[symbol.symbol] = {
                        "data": data_dict,
                        "symbol": symbol.symbol,
                        "period": request.period,
                        "interval": request.interval,
                        "rows": len(data_dict)
                    }
                else:
                    results[symbol.symbol] = data
            except Exception as e:
                results[symbol.symbol] = {"error": str(e)}

        # Cache successful results
        background_tasks.add_task(set_cached_data, cache_key, results, 300)

        return APIResponse(success=True, data=results, message=f"Retrieved data for {len(results)} symbols")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve market data: {str(e)}")

@router.get("/market-data/quote/{symbol}")
async def get_real_time_quote(symbol: str, user: dict = Depends(verify_token)):
    """Get real-time quote for a symbol"""
    try:
        quote = await data_feed_manager.get_real_time_quote(symbol.upper())
        return APIResponse(success=True, data=quote, message=f"Real-time quote for {symbol}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quote: {str(e)}")
