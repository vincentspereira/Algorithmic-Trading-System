
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from api.app.models import APIResponse, IndicatorRequest
from api.app.utils import get_cache_key, get_cached_data, set_cached_data
from nautilus_trader_engine.core.data_feed_manager import DataFeedManager
from nautilus_trader_engine.indicators.comprehensive_indicators import ComprehensiveIndicators
from app.core.security import verify_token

router = APIRouter()
data_feed_manager = DataFeedManager()
indicators_engine = ComprehensiveIndicators()

@router.post("/indicators", response_model=APIResponse)
async def calculate_indicators(
    request: IndicatorRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(verify_token)
):
    """Calculate technical indicators for a symbol"""
    try:
        # Check cache first
        cache_key = get_cache_key("indicators",
                                symbol=request.symbol.symbol,
                                indicators=sorted(request.indicator_types),
                                volume_weighted=request.include_volume_weighted,
                                patterns=request.include_patterns)

        cached_data = await get_cached_data(cache_key)
        if cached_data:
            return APIResponse(success=True, data=cached_data, message="Indicators retrieved from cache")

        # Get market data first
        market_data = await data_feed_manager.get_historical_data(
            symbol=request.symbol.symbol,
            period="1y",  # Use more data for better indicator calculations
            interval="1d"
        )

        if market_data is None or (hasattr(market_data, 'empty') and market_data.empty):
            raise HTTPException(status_code=404, detail=f"No market data found for {request.symbol.symbol}")

        # Prepare data for indicators
        data_dict = {
            'open': market_data['Open'],
            'high': market_data['High'],
            'low': market_data['Low'],
            'close': market_data['Close'],
            'volume': market_data['Volume']
        }

        # Calculate all indicators
        all_indicators = indicators_engine.calculate_all_indicators(
            data_dict,
            include_patterns=request.include_patterns,
            include_volume_weighted=request.include_volume_weighted
        )

        # Filter requested indicators if specified
        if request.indicator_types and request.indicator_types != ["all"]:
            filtered_indicators = {}
            for indicator_name, result in all_indicators.items():
                for requested_type in request.indicator_types:
                    if requested_type.lower() in indicator_name.lower():
                        filtered_indicators[indicator_name] = {
                            "name": result.indicator_name,
                            "category": result.category.value,
                            "signal": result.signal,
                            "strength": result.strength,
                            "confidence": result.confidence,
                            "volume_weighted": result.volume_weighted,
                            "metadata": result.metadata
                        }
            all_indicators = filtered_indicators
        else:
            # Convert to serializable format
            serializable_indicators = {}
            for name, result in all_indicators.items():
                serializable_indicators[name] = {
                    "name": result.indicator_name,
                    "category": result.category.value,
                    "signal": result.signal,
                    "strength": result.strength,
                    "confidence": result.confidence,
                    "volume_weighted": result.volume_weighted,
                    "metadata": result.metadata
                }
            all_indicators = serializable_indicators

        # Get summary
        summary = indicators_engine.get_indicator_summary(
            {k: type('MockResult', (), {
                'indicator_name': v['name'],
                'category': type('MockCategory', (), {'value': v['category']})(),
                'signal': v['signal'],
                'strength': v['strength'],
                'confidence': v['confidence'],
                'volume_weighted': v['volume_weighted']
            })() for k, v in all_indicators.items()}
        )

        result_data = {
            "symbol": request.symbol.symbol,
            "indicators": all_indicators,
            "summary": summary,
            "calculation_time": datetime.now(),
            "data_points": len(market_data)
        }

        # Cache results
        background_tasks.add_task(set_cached_data, cache_key, result_data, 600)

        return APIResponse(success=True, data=result_data,
                         message=f"Calculated {len(all_indicators)} indicators")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indicator calculation failed: {str(e)}")

@router.get("/indicators/available")
async def get_available_indicators(user: dict = Depends(verify_token)):
    """Get list of available indicators"""
    indicators_info = {
        "trend_indicators": [
            "sma", "ema", "vwma", "vw_ema", "hull_ma", "kama", "dema", "tema",
            "mcginley_dynamic", "zero_lag_ema", "linear_regression"
        ],
        "momentum_indicators": [
            "rsi", "vw_rsi", "macd", "vw_macd", "stochastic", "williams_r",
            "cci", "awesome_oscillator", "fisher_transform"
        ],
        "volatility_indicators": [
            "bollinger_bands", "atr", "vw_atr", "vw_atrp", "keltner_channels",
            "donchian_channels", "historical_volatility", "adx"
        ],
        "volume_indicators": [
            "vwap", "obv", "enhanced_vwap", "enhanced_obv", "ad_line",
            "mfi", "cmf", "volume_roc", "pvt", "emv"
        ],
        "candlestick_patterns": [
            "doji", "hammer", "hanging_man", "shooting_star", "marubozu",
            "spinning_top", "engulfing", "harami", "morning_star", "evening_star"
        ]
    }

    return APIResponse(success=True, data=indicators_info,
                     message="Available indicators by category")
