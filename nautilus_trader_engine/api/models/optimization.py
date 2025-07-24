"""
Pydantic models for optimization endpoints

This module contains all optimization-related data models used throughout the API.
These models define the structure for optimization requests, parameter ranges,
results, and error handling for the hyperparameter optimization system.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, Union
from datetime import date, datetime
from enum import Enum


class ParameterRange(BaseModel):
    """
    Parameter range for optimization
    
    Defines the search space for a single parameter during optimization,
    including minimum and maximum values and optional step size.
    """
    min: Union[int, float] = Field(
        ...,
        description="Minimum value for the parameter",
        example=5
    )
    max: Union[int, float] = Field(
        ...,
        description="Maximum value for the parameter",
        example=50
    )
    step: Optional[Union[int, float]] = Field(
        None,
        description="Step size for discrete parameters (optional)",
        example=1
    )
    
    @field_validator('max')
    def max_must_be_greater_than_min(cls, v, values):
        if 'min' in values.data and v <= values.data['min']:
            raise ValueError('max must be greater than min')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "min": 5,
                "max": 50,
                "step": 1
            }
        }


class OptimizationRequest(BaseModel):
    """
    Optimization request model
    
    Defines the parameters required to run a hyperparameter optimization,
    including the asset, time period, strategy, and optimization settings.
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
    strategy: str = Field(
        ...,
        description="Strategy name to optimize (e.g., 'sma_crossover')",
        example="sma_crossover"
    )
    initial_capital: Optional[float] = Field(
        default=100000.0,
        description="Initial capital amount for backtesting in USD",
        gt=0,
        example=100000.0
    )
    
    # Optimization parameters
    params: Dict[str, ParameterRange] = Field(
        ...,
        description="Parameter search space defining ranges for each parameter to optimize",
        example={
            "sma_short": {"min": 5, "max": 20, "step": 1},
            "sma_long": {"min": 50, "max": 200, "step": 5}
        }
    )
    
    # Optimization settings
    n_trials: Optional[int] = Field(
        default=100,
        description="Number of optimization trials to run",
        gt=0,
        le=1000,
        example=100
    )
    timeout: Optional[int] = Field(
        default=300,
        description="Maximum optimization time in seconds",
        gt=0,
        le=3600,
        example=300
    )
    objective: Optional[str] = Field(
        default="sharpe_ratio",
        description="Optimization objective ('sharpe_ratio', 'total_return', 'calmar_ratio')",
        example="sharpe_ratio"
    )
    
    @field_validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values.data and v <= values.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @field_validator('ticker')
    def ticker_must_be_uppercase(cls, v):
        return v.upper().strip()
    
    @field_validator('params')
    def params_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('params cannot be empty')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy": "sma_crossover",
                "initial_capital": 100000.0,
                "params": {
                    "sma_short": {"min": 5, "max": 20, "step": 1},
                    "sma_long": {"min": 50, "max": 200, "step": 5}
                },
                "n_trials": 100,
                "timeout": 300,
                "objective": "sharpe_ratio"
            }
        }


class OptimizationResult(BaseModel):
    """
    Individual optimization trial result
    
    Contains the results from a single optimization trial,
    including the parameters tested and the resulting performance.
    """
    trial_number: int = Field(
        ...,
        description="Sequential trial number",
        example=42
    )
    parameters: Dict[str, Union[int, float]] = Field(
        ...,
        description="Parameters used in this trial",
        example={"sma_short": 12, "sma_long": 85}
    )
    objective_value: float = Field(
        ...,
        description="Objective function value achieved",
        example=1.25
    )
    metrics: Optional[Dict[str, float]] = Field(
        None,
        description="Additional performance metrics",
        example={"total_return": 0.15, "max_drawdown": -0.08}
    )
    status: str = Field(
        ...,
        description="Trial status ('success' or 'failed')",
        example="success"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if trial failed",
        example=None
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trial_number": 42,
                "parameters": {"sma_short": 12, "sma_long": 85},
                "objective_value": 1.25,
                "metrics": {"total_return": 0.15, "max_drawdown": -0.08},
                "status": "success",
                "error": None
            }
        }


class OptimizationResponse(BaseModel):
    """
    Complete optimization response model
    
    Contains the complete results from a hyperparameter optimization,
    including the best parameters found and detailed statistics.
    """
    status: str = Field(
        ...,
        description="Overall optimization status",
        example="success"
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when optimization was completed",
        example="2024-01-15T16:45:00Z"
    )
    
    # Request parameters
    parameters: Dict[str, Any] = Field(
        ...,
        description="Parameters used for the optimization",
        example={
            "ticker": "AAPL",
            "strategy": "sma_crossover",
            "n_trials": 100,
            "objective": "sharpe_ratio"
        }
    )
    
    # Optimization results
    best_parameters: Dict[str, Union[int, float]] = Field(
        ...,
        description="Best parameters found during optimization",
        example={"sma_short": 12, "sma_long": 85}
    )
    best_value: float = Field(
        ...,
        description="Best objective value achieved",
        example=1.45
    )
    
    # Study statistics
    n_trials: int = Field(
        ...,
        description="Total number of trials completed",
        example=100
    )
    n_complete_trials: int = Field(
        ...,
        description="Number of successfully completed trials",
        example=95
    )
    n_failed_trials: int = Field(
        ...,
        description="Number of failed trials",
        example=5
    )
    
    # Additional information
    study_name: str = Field(
        ...,
        description="Optuna study name used for this optimization",
        example="sma_crossover_AAPL_20240115"
    )
    optimization_time: float = Field(
        ...,
        description="Total optimization time in seconds",
        example=287.5
    )
    
    # Optional detailed results
    trials: Optional[list[OptimizationResult]] = Field(
        None,
        description="Detailed results from all trials (optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "timestamp": "2024-01-15T16:45:00Z",
                "parameters": {
                    "ticker": "AAPL",
                    "strategy": "sma_crossover",
                    "n_trials": 100,
                    "objective": "sharpe_ratio"
                },
                "best_parameters": {"sma_short": 12, "sma_long": 85},
                "best_value": 1.45,
                "n_trials": 100,
                "n_complete_trials": 95,
                "n_failed_trials": 5,
                "study_name": "sma_crossover_AAPL_20240115",
                "optimization_time": 287.5,
                "trials": None
            }
        }


class OptimizationError(BaseModel):
    """
    Optimization error response model
    
    Contains error information when an optimization operation fails,
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
        example="2024-01-15T16:45:00Z"
    )
    error: str = Field(
        ...,
        description="Primary error message describing what went wrong",
        example="Invalid strategy name: unknown_strategy not supported"
    )
    details: Optional[str] = Field(
        None,
        description="Additional error details and context",
        example="Supported strategies: sma_crossover, rsi_strategy"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters that caused the error",
        example={
            "strategy": "unknown_strategy",
            "ticker": "AAPL"
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "timestamp": "2024-01-15T16:45:00Z",
                "error": "Invalid strategy name: unknown_strategy not supported",
                "details": "Supported strategies: sma_crossover, rsi_strategy",
                "parameters": {
                    "strategy": "unknown_strategy",
                    "ticker": "AAPL"
                }
            }
        }