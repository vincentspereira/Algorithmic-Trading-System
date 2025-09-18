"""
Backtesting router for running backtests
"""

import logging
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status, Depends

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models.backtest import (
    BacktestRequest, 
    BacktestResponse, 
    BacktestResult, 
    PerformanceMetrics,
    BacktestError
)
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/backtest",
    tags=["Backtesting"],
    responses={
        401: {"description": "Authentication required"},
        422: {"description": "Validation error or data processing failed"},
        500: {"description": "Internal server error"}
    }
)


def convert_backtest_result_to_model(result_dict: Dict[str, Any], engine_name: str) -> BacktestResult:
    """Convert backtest result dictionary to BacktestResult model"""
    try:
        if not result_dict:
            return BacktestResult(
                engine_name=engine_name,
                status="error",
                error="No result data returned"
            )
        
        # Create PerformanceMetrics from result
        metrics = PerformanceMetrics(
            total_return=result_dict.get("total_return", 0.0),
            annual_return=result_dict.get("annual_return", 0.0),
            sharpe_ratio=result_dict.get("sharpe_ratio", 0.0),
            max_drawdown=result_dict.get("max_drawdown", 0.0),
            volatility=result_dict.get("volatility", 0.0),
            calmar_ratio=result_dict.get("calmar_ratio", 0.0),
            sortino_ratio=result_dict.get("sortino_ratio", 0.0),
            total_trades=result_dict.get("total_trades", 0),
            winning_trades=result_dict.get("winning_trades", 0),
            losing_trades=result_dict.get("losing_trades", 0),
            win_rate=result_dict.get("win_rate", 0.0),
            avg_win=result_dict.get("avg_win", 0.0),
            avg_loss=result_dict.get("avg_loss", 0.0),
            profit_factor=result_dict.get("profit_factor", 0.0),
            initial_capital=result_dict.get("initial_capital", 0.0),
            final_capital=result_dict.get("final_capital", 0.0)
        )
        
        return BacktestResult(
            engine_name=engine_name,
            status="success",
            metrics=metrics
        )
        
    except Exception as e:
        logger.error(f"Error converting {engine_name} result: {e}")
        return BacktestResult(
            engine_name=engine_name,
            status="error",
            error=str(e)
        )


@router.post(
    "/",
    response_model=BacktestResponse,
    summary="Run Strategy Backtest",
    description="Execute a comprehensive backtest of a trading strategy using historical market data",
    responses={
        200: {
            "description": "Backtest completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "completed",
                        "timestamp": "2024-01-15T14:30:00Z",
                        "parameters": {
                            "ticker": "AAPL",
                            "start_date": "2023-01-01",
                            "end_date": "2023-12-31",
                            "strategy_name": "moving_average_crossover",
                            "initial_capital": 100000.0
                        },
                        "data_points": 252,
                        "results": {
                            "backtrader": {
                                "engine_name": "Backtrader",
                                "status": "success",
                                "metrics": {
                                    "total_return": 0.1547,
                                    "sharpe_ratio": 1.25,
                                    "max_drawdown": -0.0823
                                }
                            }
                        },
                        "summary": {
                            "total_return": 0.1547,
                            "sharpe_ratio": 1.25,
                            "max_drawdown": -0.0823
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        },
        422: {
            "description": "Invalid parameters or data processing failed",
            "content": {
                "application/json": {
                    "example": {
                        "status": "error",
                        "timestamp": "2024-01-15T14:30:00Z",
                        "error": "Failed to fetch market data for INVALID",
                        "details": "The ticker symbol 'INVALID' is not available",
                        "parameters": {
                            "ticker": "INVALID",
                            "start_date": "2023-01-01",
                            "end_date": "2023-12-31"
                        }
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Backtesting engine not available"
                    }
                }
            }
        }
    }
)
async def run_backtest(
    request: BacktestRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    **Execute Strategy Backtest**
    
    Runs a comprehensive backtest of a trading strategy using historical market data
    across multiple backtesting engines for comparison and validation.
    
    ### Authentication Required
    This endpoint requires a valid access token in the Authorization header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    
    ### Backtesting Process
    1. **Data Retrieval**: Fetches historical market data for the specified ticker and date range
    2. **Strategy Execution**: Applies the selected trading strategy with given parameters
    3. **Multi-Engine Analysis**: Runs the backtest on multiple engines (Backtrader, TradingGym)
    4. **Performance Calculation**: Computes comprehensive performance metrics
    5. **Results Comparison**: Provides results from all engines for validation
    
    ### Supported Strategies
    - **Moving Average Crossover**: Uses fast and slow moving averages to generate signals
    - Additional strategies can be added through the strategy framework
    
    ### Performance Metrics
    The backtest returns comprehensive performance metrics including:
    - **Return Metrics**: Total return, annual return, profit factor
    - **Risk Metrics**: Sharpe ratio, Sortino ratio, Calmar ratio, maximum drawdown
    - **Trade Statistics**: Total trades, win rate, average win/loss
    - **Capital Metrics**: Initial and final capital values
    
    ### Multiple Engine Validation
    - **Backtrader**: Professional backtesting framework with extensive features
    - **TradingGym**: Reinforcement learning focused backtesting environment
    - Results from both engines help validate strategy performance
    
    ### Data Requirements
    - Historical market data must be available for the specified ticker
    - Date range should provide sufficient data points for meaningful analysis
    - Minimum recommended period: 6 months of daily data
    
    ### Performance Considerations
    - Backtests may take 10-60 seconds depending on data range and complexity
    - Larger date ranges require more processing time
    - Multiple engines run in sequence for comprehensive analysis
    
    ### Error Handling
    - Invalid ticker symbols return 422 with descriptive error
    - Data retrieval failures are handled gracefully
    - Engine-specific errors are isolated and reported separately
    """
    try:
        logger.info(f"Starting backtest for user {current_user_id}: {request.ticker} ({request.start_date} to {request.end_date})")
        
        # Import BacktestRunner from the existing implementation
        try:
            from run_initial_backtest import BacktestRunner
        except ImportError as e:
            logger.error(f"Failed to import BacktestRunner: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Backtesting engine not available"
            )
        
        # Convert dates to year format for BacktestRunner compatibility
        # Note: The existing BacktestRunner uses year-based data fetching
        # In a production system, this would be enhanced to support date ranges
        year = request.start_date.year
        
        # Create BacktestRunner instance
        runner = BacktestRunner(
            symbol=request.ticker,
            year=year,
            initial_capital=request.initial_capital
        )
        
        # Set strategy parameters
        runner.fast_period = request.fast_period
        runner.slow_period = request.slow_period
        
        # Fetch market data
        if not runner.fetch_data():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to fetch market data for {request.ticker}"
            )
        
        # Run backtests with both engines
        results = {}
        
        # Run Backtrader backtest
        try:
            backtrader_result = runner.run_backtrader_backtest()
            results["backtrader"] = convert_backtest_result_to_model(
                backtrader_result, "Backtrader"
            )
        except Exception as e:
            logger.error(f"Backtrader backtest failed: {e}")
            results["backtrader"] = BacktestResult(
                engine_name="Backtrader",
                status="error",
                error=str(e)
            )
        
        # Run TradingGym backtest
        try:
            trading_gym_result = runner.run_trading_gym_backtest()
            results["trading_gym"] = convert_backtest_result_to_model(
                trading_gym_result, "TradingGym"
            )
        except Exception as e:
            logger.error(f"TradingGym backtest failed: {e}")
            results["trading_gym"] = BacktestResult(
                engine_name="TradingGym",
                status="error",
                error=str(e)
            )
        
        # Determine best performing engine for summary
        summary_metrics = None
        best_return = float('-inf')
        
        for engine_result in results.values():
            if engine_result.status == "success" and engine_result.metrics:
                if engine_result.metrics.total_return > best_return:
                    best_return = engine_result.metrics.total_return
                    summary_metrics = engine_result.metrics
        
        # Prepare response
        response = BacktestResponse(
            status="completed",
            timestamp=datetime.now(timezone.utc),
            parameters={
                "ticker": request.ticker,
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat(),
                "strategy_name": request.strategy_name,
                "initial_capital": request.initial_capital,
                "fast_period": request.fast_period,
                "slow_period": request.slow_period,
                "user_id": current_user_id
            },
            data_points=len(runner.data) if runner.data is not None else 0,
            results=results,
            summary=summary_metrics
        )
        
        logger.info(f"Backtest completed successfully for {request.ticker}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/status",
    summary="Backtesting Engine Status",
    description="Check the availability and status of backtesting engines and supported features",
    responses={
        200: {
            "description": "Backtesting engine status retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "ready": {
                            "summary": "All engines available",
                            "value": {
                                "status": "ready",
                                "engines": {
                                    "backtrader": "available",
                                    "trading_gym": "available"
                                },
                                "supported_strategies": ["moving_average_crossover"],
                                "default_parameters": {
                                    "initial_capital": 100000.0,
                                    "fast_period": 10,
                                    "slow_period": 30
                                },
                                "timestamp": "2024-01-15T14:30:00Z",
                                "user_id": "demo_user_001"
                            }
                        },
                        "error": {
                            "summary": "Engine unavailable",
                            "value": {
                                "status": "error",
                                "error": "Backtest modules not available: No module named 'backtrader'",
                                "timestamp": "2024-01-15T14:30:00Z",
                                "user_id": "demo_user_001"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Authentication required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authenticated"
                    }
                }
            }
        }
    }
)
async def get_backtest_status(current_user_id: str = Depends(get_current_user)):
    """
    **Backtesting Engine Status Check**
    
    Provides comprehensive status information about the backtesting system,
    including engine availability, supported strategies, and default parameters.
    
    ### Authentication Required
    This endpoint requires a valid access token in the Authorization header:
    ```
    Authorization: Bearer <your_access_token>
    ```
    
    ### Status Information
    - **Engine Availability**: Status of each backtesting engine (Backtrader, TradingGym)
    - **Supported Strategies**: List of available trading strategies
    - **Default Parameters**: Default values for strategy parameters
    - **System Health**: Overall system readiness for backtesting operations
    
    ### Engine Status Values
    - **available**: Engine is loaded and ready for use
    - **unavailable**: Engine module is not installed or accessible
    - **error**: Engine encountered an initialization error
    
    ### Use Cases
    - **System Health Checks**: Verify backtesting system is operational
    - **Client Initialization**: Determine available features before making requests
    - **Debugging**: Diagnose issues with backtesting engine availability
    - **Monitoring**: Track system status for operational dashboards
    
    ### Troubleshooting
    If engines show as unavailable:
    1. Check that required Python packages are installed
    2. Verify system dependencies are met
    3. Review server logs for detailed error information
    4. Contact system administrator if issues persist
    """
    try:
        # Test if backtest modules are available
        from run_initial_backtest import BacktestRunner
        from backtesting.backtrader_engine import BacktraderEngine
        from backtesting.trading_gym_engine import TradingGymEngine
        
        return {
            "status": "ready",
            "engines": {
                "backtrader": "available",
                "trading_gym": "available"
            },
            "supported_strategies": ["moving_average_crossover"],
            "default_parameters": {
                "initial_capital": 100000.0,
                "fast_period": 10,
                "slow_period": 30
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": current_user_id
        }
        
    except ImportError as e:
        return {
            "status": "error",
            "error": f"Backtest modules not available: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": current_user_id
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": current_user_id
        }