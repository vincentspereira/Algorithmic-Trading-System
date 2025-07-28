from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from nautilus_trader_engine.strategy_execution.runtime_engine import StrategyRuntimeEngine
from nautilus_trader_engine.strategy_execution.validation import StrategyValidator
from nautilus_trader_engine.strategy_execution.backtesting import Backtester
from nautilus_trader_engine.strategy_execution.performance_monitor import PerformanceMonitor
from nautilus_trader_engine.storage.strategy_store import StrategyStore # Assuming this exists

router = APIRouter()

# Dependency injection for the components
# In a real application, these would be initialized once and passed around
# For simplicity, we'll instantiate them here.
# You would likely use FastAPI's Depends for proper dependency injection.
strategy_runtime_engine = StrategyRuntimeEngine(trading_engine_connection=None, data_pipeline=None) # Replace None with actual connections
strategy_validator = StrategyValidator()
backtester = Backtester(data_pipeline=None) # Replace None with actual data pipeline
performance_monitor = PerformanceMonitor()
strategy_store = StrategyStore() # Assuming StrategyStore can be instantiated without args or takes config

class StrategyCreateRequest(BaseModel):
    strategy_id: str
    strategy_code: str

class BacktestRequest(BaseModel):
    strategy_code: str
    historical_data_config: Dict[str, Any]

@router.post("/strategies/deploy", summary="Deploy a new trading strategy")
async def deploy_strategy(request: StrategyCreateRequest):
    """
    Deploys a new trading strategy.
    Validates the strategy code and loads it into the runtime engine.
    """
    if not strategy_validator.validate_strategy(request.strategy_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy code failed validation (syntax or basic logic)."
        )

    if not strategy_runtime_engine.load_strategy(request.strategy_id, request.strategy_code):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load strategy into runtime engine."
        )
    
    # Persist the strategy
    strategy_store.save_strategy(request.strategy_id, request.strategy_code)

    return {"message": f"Strategy {request.strategy_id} deployed successfully."}

@router.post("/strategies/{strategy_id}/execute", summary="Execute a deployed trading strategy")
async def execute_strategy(strategy_id: str):
    """
    Starts the execution of a deployed trading strategy.
    """
    if not strategy_runtime_engine.execute_strategy(strategy_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to execute strategy {strategy_id}. It might not be loaded or already running."
        )
    performance_monitor.initialize_strategy_metrics(strategy_id)
    return {"message": f"Strategy {strategy_id} execution started."}

@router.post("/strategies/{strategy_id}/stop", summary="Stop a running trading strategy")
async def stop_strategy(strategy_id: str):
    """
    Stops a running trading strategy.
    """
    if not strategy_runtime_engine.stop_strategy(strategy_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to stop strategy {strategy_id}. It might not be running."
        )
    return {"message": f"Strategy {strategy_id} stopped."}

@router.get("/strategies/{strategy_id}/status", summary="Get the status of a trading strategy")
async def get_strategy_status(strategy_id: str):
    """
    Retrieves the current status of a trading strategy.
    """
    status = strategy_runtime_engine.get_strategy_status(strategy_id)
    if status == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {strategy_id} not found."
        )
    return {"strategy_id": strategy_id, "status": status}

@router.get("/strategies", summary="Get status of all deployed strategies")
async def get_all_strategies_status():
    """
    Retrieves the status of all deployed trading strategies.
    """
    return strategy_runtime_engine.get_all_strategies_status()

@router.post("/strategies/backtest", summary="Run a backtest for a strategy")
async def run_strategy_backtest(request: BacktestRequest):
    """
    Runs a backtest for the provided strategy code against historical data.
    """
    if not strategy_validator.validate_syntax(request.strategy_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Strategy code has syntax errors, cannot run backtest."
        )
    
    results = backtester.run_backtest(request.strategy_code, request.historical_data_config)
    if "error" in results:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=results["error"]
        )
    return {"message": "Backtest completed", "results": results}

@router.get("/strategies/{strategy_id}/performance", summary="Get performance metrics for a live strategy")
async def get_strategy_performance(strategy_id: str):
    """
    Retrieves performance metrics for a live trading strategy.
    """
    performance = performance_monitor.get_strategy_performance(strategy_id)
    if performance.get("status") == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Performance metrics for strategy {strategy_id} not found. Is it running?"
        )
    return {"strategy_id": strategy_id, "performance": performance}

@router.delete("/strategies/{strategy_id}", summary="Delete a deployed strategy")
async def delete_strategy(strategy_id: str):
    """
    Deletes a deployed strategy.
    Note: This only removes it from the runtime engine and storage.
    Ensure the strategy is stopped before deletion if it's running.
    """
    # In a real system, you'd want to ensure the strategy is stopped first
    # and handle any cleanup of resources.
    if strategy_runtime_engine.get_strategy_status(strategy_id) == "running":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Strategy {strategy_id} is currently running. Please stop it before deleting."
        )

    # Remove from runtime engine
    if strategy_id in strategy_runtime_engine.active_strategies:
        del strategy_runtime_engine.active_strategies[strategy_id]
    
    # Remove from performance monitor
    if strategy_id in performance_monitor.strategy_metrics:
        del performance_monitor.strategy_metrics[strategy_id]

    # Remove from persistent storage
    strategy_store.delete_strategy(strategy_id) # Assuming delete_strategy method exists

    return {"message": f"Strategy {strategy_id} deleted successfully."}