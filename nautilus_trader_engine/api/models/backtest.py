"""
Pydantic models for backtesting

This module contains all backtesting-related data models used throughout the API.
These models define the structure for backtest requests, results, performance metrics,
and error handling for the backtesting system.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class StrategyName(str, Enum):
    """
    Available trading strategy names
    
    Enumeration of all supported trading strategies that can be used
    for backtesting operations.
    """
    MOVING_AVERAGE_CROSSOVER = "moving_average_crossover"
    # Add more strategies as they become available


class BacktestRequest(BaseModel):
    """
    Backtest request model
    
    Defines the parameters required to run a backtest, including the asset,
    time period, strategy, and strategy-specific parameters.
    """
    ticker: str = Field(
        ...,
        description="Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)",
        min_length=1,
        max_length=10,
        example="AAPL"
    )
    start_date: date = Field(
        ...,
        description="Start date for backtesting in YYYY-MM-DD format",
        example="2023-01-01"
    )
    end_date: date = Field(
        ...,
        description="End date for backtesting in YYYY-MM-DD format",
        example="2023-12-31"
    )
    strategy_name: StrategyName = Field(
        ...,
        description="Name of the trading strategy to use for backtesting",
        example="moving_average_crossover"
    )
    initial_capital: Optional[float] = Field(
        default=100000.0,
        description="Initial capital amount for backtesting in USD",
        gt=0,
        example=100000.0
    )
    
    # Strategy-specific parameters (optional)
    fast_period: Optional[int] = Field(
        default=10,
        description="Fast moving average period (number of days)",
        gt=0,
        le=100,
        example=10
    )
    slow_period: Optional[int] = Field(
        default=30,
        description="Slow moving average period (number of days)",
        gt=0,
        le=200,
        example=30
    )
    
    @field_validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values.data and v <= values.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @field_validator('slow_period')
    def slow_period_must_be_greater_than_fast_period(cls, v, values):
        if 'fast_period' in values.data and v <= values.data['fast_period']:
            raise ValueError('slow_period must be greater than fast_period')
        return v
    
    @field_validator('ticker')
    def ticker_must_be_uppercase(cls, v):
        return v.upper().strip()

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000.0,
            "fast_period": 10,
            "slow_period": 30
        }
    })


class PerformanceMetrics(BaseModel):
    """
    Performance metrics model
    
    Comprehensive performance metrics calculated from backtest results,
    including returns, risk metrics, and trade statistics.
    """
    total_return: float = Field(
        ...,
        description="Total return as decimal (e.g., 0.15 for 15%)",
        example=0.1547
    )
    annual_return: float = Field(
        ...,
        description="Annualized return as decimal",
        example=0.1234
    )
    sharpe_ratio: float = Field(
        ...,
        description="Sharpe ratio (risk-adjusted return metric)",
        example=1.25
    )
    max_drawdown: float = Field(
        ...,
        description="Maximum drawdown as decimal (e.g., -0.08 for -8%)",
        example=-0.0823
    )
    volatility: float = Field(
        ...,
        description="Volatility (standard deviation of returns) as decimal",
        example=0.1456
    )
    calmar_ratio: float = Field(
        ...,
        description="Calmar ratio (annual return / max drawdown)",
        example=1.50
    )
    sortino_ratio: float = Field(
        ...,
        description="Sortino ratio (downside deviation adjusted return)",
        example=1.78
    )
    
    # Trade statistics
    total_trades: int = Field(
        ...,
        description="Total number of trades executed",
        example=45
    )
    winning_trades: int = Field(
        ...,
        description="Number of profitable trades",
        example=28
    )
    losing_trades: int = Field(
        ...,
        description="Number of losing trades",
        example=17
    )
    win_rate: float = Field(
        ...,
        description="Win rate as decimal (winning trades / total trades)",
        example=0.6222
    )
    avg_win: float = Field(
        ...,
        description="Average winning trade amount in USD",
        example=1250.75
    )
    avg_loss: float = Field(
        ...,
        description="Average losing trade amount in USD (negative value)",
        example=-850.25
    )
    profit_factor: float = Field(
        ...,
        description="Profit factor (gross profit / gross loss)",
        example=1.85
    )
    
    # Capital metrics
    initial_capital: float = Field(
        ...,
        description="Initial capital amount in USD",
        example=100000.0
    )
    final_capital: float = Field(
        ...,
        description="Final capital amount in USD",
        example=115470.0
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_return": 0.1547,
            "annual_return": 0.1234,
            "sharpe_ratio": 1.25,
            "max_drawdown": -0.0823,
            "volatility": 0.1456,
            "calmar_ratio": 1.50,
            "sortino_ratio": 1.78,
            "total_trades": 45,
            "winning_trades": 28,
            "losing_trades": 17,
            "win_rate": 0.6222,
            "avg_win": 1250.75,
            "avg_loss": -850.25,
            "profit_factor": 1.85,
            "initial_capital": 100000.0,
            "final_capital": 115470.0
        }
    })


class BacktestResult(BaseModel):
    """
    Individual backtest engine result
    
    Contains the results from a single backtesting engine, including
    performance metrics or error information if the backtest failed.
    """
    engine_name: str = Field(
        ...,
        description="Name of the backtesting engine used (e.g., 'Backtrader', 'TradingGym')",
        example="Backtrader"
    )
    status: str = Field(
        ...,
        description="Status of the backtest execution ('success' or 'error')",
        example="success"
    )
    metrics: Optional[PerformanceMetrics] = Field(
        None,
        description="Performance metrics if backtest was successful"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if backtest failed",
        example=None
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "engine_name": "Backtrader",
            "status": "success",
            "metrics": {
                "total_return": 0.1547,
                "sharpe_ratio": 1.25,
                "max_drawdown": -0.0823,
                "total_trades": 45,
                "win_rate": 0.6222
            },
            "error": None
        }
    })


class BacktestResponse(BaseModel):
    """
    Complete backtest response model
    
    Contains the complete results from a backtesting operation,
    including results from multiple engines and summary metrics.
    """
    status: str = Field(
        ...,
        description="Overall status of the backtest operation",
        example="success"
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when backtest was completed",
        example="2024-01-15T14:30:00Z"
    )
    
    # Request parameters
    parameters: Dict[str, Any] = Field(
        ...,
        description="Parameters used for the backtest execution",
        example={
            "ticker": "AAPL",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "strategy_name": "moving_average_crossover",
            "initial_capital": 100000.0
        }
    )
    data_points: int = Field(
        ...,
        description="Number of historical data points processed",
        example=252
    )
    
    # Results from different engines
    results: Dict[str, BacktestResult] = Field(
        ...,
        description="Results from different backtesting engines"
    )
    
    # Summary metrics (from the best performing engine)
    summary: Optional[PerformanceMetrics] = Field(
        None,
        description="Summary metrics from the best performing engine"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "success",
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
                "Backtrader": {
                    "engine_name": "Backtrader",
                    "status": "success",
                    "metrics": {
                        "total_return": 0.1547,
                        "sharpe_ratio": 1.25
                    }
                }
            },
            "summary": {
                "total_return": 0.1547,
                "sharpe_ratio": 1.25,
                "max_drawdown": -0.0823
            }
        }
    })


class BacktestError(BaseModel):
    """
    Backtest error response model
    
    Contains error information when a backtest operation fails,
    including the error message and relevant context.
    """
    status: str = Field(
        default="error",
        description="Status indicating error occurred",
        example="error"
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when error occurred",
        example="2024-01-15T14:30:00Z"
    )
    error: str = Field(
        ...,
        description="Primary error message describing what went wrong",
        example="Invalid ticker symbol: XYZ not found"
    )
    details: Optional[str] = Field(
        None,
        description="Additional error details and context",
        example="The ticker symbol 'XYZ' is not available in the data provider"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters that caused the error",
        example={
            "ticker": "XYZ",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31"
        }
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "error",
            "timestamp": "2024-01-15T14:30:00Z",
            "error": "Invalid ticker symbol: XYZ not found",
            "details": "The ticker symbol 'XYZ' is not available in the data provider",
            "parameters": {
                "ticker": "XYZ",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            }
        }
    })