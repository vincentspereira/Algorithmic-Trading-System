from fastapi import APIRouter, HTTPException
from nautilus_trader_engine.services.strategy_executor import StrategyExecutor
from nautilus_trader_engine.services.trading_gateway import TradingGateway
from nautilus_trader_engine.services.risk_management_service import RiskManagementService
from nautilus_trader_engine.services.market_data_service import MarketDataService
from nautilus_trader_engine.services.strategy_validation_service import StrategyValidationService

router = APIRouter()

# Initialize services
risk_management_service = RiskManagementService()
trading_gateway = TradingGateway(risk_management_service=risk_management_service)
market_data_service = MarketDataService()
strategy_validation_service = StrategyValidationService()
strategy_executor = StrategyExecutor(
    trading_gateway=trading_gateway,
    risk_management_service=risk_management_service,
    market_data_service=market_data_service,
)

@router.post("/strategy/execute")
async def execute_strategy(strategy_id: str, code: str):
    """
    Executes a trading strategy.
    """
    try:
        await strategy_executor.execute_strategy(strategy_id, code)
        return {"status": "success", "message": f"Strategy {strategy_id} executed successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/strategy/stop")
async def stop_strategy(strategy_id: str):
    """
    Stops a running trading strategy.
    """
    try:
        strategy_executor.stop_strategy(strategy_id)
        return {"status": "success", "message": f"Strategy {strategy_id} stopped successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/strategy/running")
async def list_running_strategies():
    """
    Lists the running strategies.
    """
    return {"running_strategies": list(strategy_executor.active_strategies.keys())}

@router.post("/strategy/validate")
async def validate_strategy(strategy_id: str, code: str):
    """
    Validates and tests a trading strategy.
    """
    try:
        is_valid = strategy_validation_service.validate_strategy(code)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Strategy failed validation.")
        
        backtest_results = strategy_validation_service.run_backtest(code, strategy_id)
        performance_metrics = strategy_validation_service.get_performance_metrics(backtest_results)
        
        return {
            "status": "success",
            "message": f"Strategy {strategy_id} validated successfully.",
            "performance_metrics": performance_metrics,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/strategy/performance/{strategy_id}")
async def get_strategy_performance(strategy_id: str):
    """
    Retrieves the performance of a specific strategy.
    """
    try:
        performance = strategy_executor.get_strategy_performance(strategy_id)
        return {"status": "success", "performance": performance}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/strategy/test")
async def test_strategy(strategy_id: str, code: str):
    """
    Runs a full suite of tests for a given strategy.
    """
    try:
        test_results = strategy_validation_service.test_strategy(code, strategy_id)
        return {"status": "success", "test_results": test_results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/strategy/report")
async def get_strategy_report(strategy_id: str, code: str):
    """
    Generates a performance report for a given strategy.
    """
    try:
        backtest_results = strategy_validation_service.run_backtest(code, strategy_id)
        report = strategy_validation_service.generate_report(backtest_results)
        return {"status": "success", "report": report}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/strategy/deploy")
async def deploy_strategy(strategy_id: str, code: str):
    """
    Deploys a new trading strategy.
    """
    try:
        strategy_executor.deploy_strategy(strategy_id, code)
        return {"status": "success", "message": f"Strategy {strategy_id} deployed successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/strategy/lifecycle/{strategy_id}")
async def get_strategy_lifecycle(strategy_id: str):
    """
    Retrieves the lifecycle of a specific strategy.
    """
    try:
        lifecycle = strategy_executor.get_strategy_lifecycle(strategy_id)
        return {"status": "success", "lifecycle": lifecycle}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/strategy/deployed")
async def list_deployed_strategies():
    """
    Lists the deployed strategies.
    """
    try:
        deployed_strategies = strategy_executor.get_deployed_strategies()
        return {"status": "success", "deployed_strategies": deployed_strategies}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))