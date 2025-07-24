"""
Optimization router for hyperparameter tuning using Optuna
"""

import logging
import sys
import os
import time
from datetime import datetime
from typing import Dict, Any, Union
from fastapi import APIRouter, HTTPException, status, Depends
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..models.optimization import (
    OptimizationRequest,
    OptimizationResponse,
    OptimizationResult,
    OptimizationError
)
from ..auth.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/optimise", tags=["Optimization"])


class OptimizationEngine:
    """Engine for running Optuna-based hyperparameter optimization"""
    
    def __init__(self, request: OptimizationRequest, user_id: str):
        self.request = request
        self.user_id = user_id
        self.study = None
        self.backtest_runner = None
        self.start_time = None
        
    def _create_objective_function(self):
        """Create the objective function for Optuna optimization"""
        def objective(trial):
            try:
                # Sample parameters from the defined ranges
                params = {}
                for param_name, param_range in self.request.params.items():
                    if param_range.step is not None:
                        # Discrete parameter
                        if isinstance(param_range.min, int) and isinstance(param_range.max, int):
                            params[param_name] = trial.suggest_int(
                                param_name, 
                                param_range.min, 
                                param_range.max, 
                                step=int(param_range.step)
                            )
                        else:
                            params[param_name] = trial.suggest_float(
                                param_name,
                                param_range.min,
                                param_range.max,
                                step=param_range.step
                            )
                    else:
                        # Continuous parameter
                        if isinstance(param_range.min, int) and isinstance(param_range.max, int):
                            params[param_name] = trial.suggest_int(
                                param_name,
                                param_range.min,
                                param_range.max
                            )
                        else:
                            params[param_name] = trial.suggest_float(
                                param_name,
                                param_range.min,
                                param_range.max
                            )
                
                # Run backtest with these parameters
                result = self._run_backtest_with_params(params)
                
                if result is None:
                    # Failed backtest
                    raise optuna.TrialPruned()
                
                # Return the objective value (Sharpe ratio by default)
                objective_value = result.get(self.request.objective, 0.0)
                
                # Store additional metrics in trial user attributes
                trial.set_user_attr("total_return", result.get("total_return", 0.0))
                trial.set_user_attr("max_drawdown", result.get("max_drawdown", 0.0))
                trial.set_user_attr("total_trades", result.get("total_trades", 0))
                trial.set_user_attr("win_rate", result.get("win_rate", 0.0))
                
                return objective_value
                
            except Exception as e:
                logger.error(f"Trial {trial.number} failed: {e}")
                raise optuna.TrialPruned()
        
        return objective
    
    def _run_backtest_with_params(self, params: Dict[str, Union[int, float]]) -> Dict[str, Any]:
        """Run backtest with specific parameters"""
        try:
            # Import BacktestRunner
            from run_initial_backtest import BacktestRunner
            
            # Create BacktestRunner instance
            year = self.request.start_date.year
            runner = BacktestRunner(
                symbol=self.request.ticker,
                year=year,
                initial_capital=self.request.initial_capital
            )
            
            # Set strategy parameters
            for param_name, param_value in params.items():
                if param_name == "fast_period":
                    runner.fast_period = int(param_value)
                elif param_name == "slow_period":
                    runner.slow_period = int(param_value)
                # Add more parameter mappings as needed
            
            # Fetch data
            if not runner.fetch_data():
                logger.error(f"Failed to fetch data for {self.request.ticker}")
                return None
            
            # Run backtest (using Backtrader by default for optimization)
            result = runner.run_backtrader_backtest()
            
            return result
            
        except Exception as e:
            logger.error(f"Backtest failed with params {params}: {e}")
            return None
    
    def optimize(self) -> OptimizationResponse:
        """Run the optimization process"""
        self.start_time = time.time()
        
        try:
            # Create Optuna study
            study_name = f"optimization_{self.request.ticker}_{self.user_id}_{int(self.start_time)}"
            
            self.study = optuna.create_study(
                study_name=study_name,
                direction="maximize",  # Maximize Sharpe ratio
                sampler=TPESampler(seed=42),
                pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=10)
            )
            
            # Create objective function
            objective = self._create_objective_function()
            
            # Run optimization
            logger.info(f"Starting optimization with {self.request.n_trials} trials")
            self.study.optimize(
                objective,
                n_trials=self.request.n_trials,
                timeout=self.request.timeout,
                catch=(Exception,)
            )
            
            # Calculate optimization time
            optimization_time = time.time() - self.start_time
            
            # Get best parameters and value
            best_params = self.study.best_params
            best_value = self.study.best_value
            
            # Collect trial results
            trials = []
            for trial in self.study.trials:
                if trial.state == optuna.trial.TrialState.COMPLETE:
                    trial_result = OptimizationResult(
                        trial_number=trial.number,
                        parameters=trial.params,
                        objective_value=trial.value,
                        metrics={
                            "total_return": trial.user_attrs.get("total_return", 0.0),
                            "max_drawdown": trial.user_attrs.get("max_drawdown", 0.0),
                            "total_trades": trial.user_attrs.get("total_trades", 0),
                            "win_rate": trial.user_attrs.get("win_rate", 0.0)
                        },
                        status="success"
                    )
                else:
                    trial_result = OptimizationResult(
                        trial_number=trial.number,
                        parameters=trial.params,
                        objective_value=0.0,
                        status="failed",
                        error=str(trial.state)
                    )
                trials.append(trial_result)
            
            # Create response
            response = OptimizationResponse(
                status="completed",
                timestamp=datetime.utcnow(),
                parameters={
                    "ticker": self.request.ticker,
                    "start_date": self.request.start_date.isoformat(),
                    "end_date": self.request.end_date.isoformat(),
                    "strategy": self.request.strategy,
                    "initial_capital": self.request.initial_capital,
                    "n_trials": self.request.n_trials,
                    "timeout": self.request.timeout,
                    "objective": self.request.objective,
                    "user_id": self.user_id
                },
                best_parameters=best_params,
                best_value=best_value,
                n_trials=len(self.study.trials),
                n_complete_trials=len([t for t in self.study.trials if t.state == optuna.trial.TrialState.COMPLETE]),
                n_failed_trials=len([t for t in self.study.trials if t.state != optuna.trial.TrialState.COMPLETE]),
                study_name=study_name,
                optimization_time=optimization_time,
                trials=trials
            )
            
            logger.info(f"Optimization completed: best {self.request.objective} = {best_value:.4f}")
            return response
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Optimization failed: {str(e)}"
            )


@router.post("/", response_model=OptimizationResponse, responses={422: {"model": OptimizationError}})
async def run_optimization(
    request: OptimizationRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Run hyperparameter optimization using Optuna
    
    This endpoint uses Optuna to find the best parameters for a trading strategy
    by maximizing the Sharpe ratio (or other specified objective).
    
    **Authentication Required:** Bearer token must be provided in Authorization header.
    
    **Parameters:**
    - **ticker**: Stock symbol (e.g., AAPL, MSFT)
    - **start_date**: Start date for backtesting (YYYY-MM-DD)
    - **end_date**: End date for backtesting (YYYY-MM-DD)
    - **strategy**: Strategy name to optimize
    - **initial_capital**: Starting capital (default: 100000.0)
    - **params**: Parameter search space (e.g., {"sma_short": {"min": 5, "max": 20}, "sma_long": {"min": 50, "max": 200}})
    - **n_trials**: Number of optimization trials (default: 100, max: 1000)
    - **timeout**: Timeout in seconds (default: 300, max: 3600)
    - **objective**: Optimization objective (default: "sharpe_ratio")
    
    **Returns:**
    - Best parameters found and their objective value
    - Detailed trial results and optimization statistics
    - Study information for further analysis
    """
    try:
        logger.info(f"Starting optimization for user {current_user_id}: {request.ticker} ({request.strategy})")
        
        # Validate strategy
        if request.strategy != "sma_crossover":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Strategy '{request.strategy}' not supported. Available: sma_crossover"
            )
        
        # Validate parameter names for SMA crossover strategy
        valid_params = {"fast_period", "slow_period"}
        invalid_params = set(request.params.keys()) - valid_params
        if invalid_params:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid parameters for sma_crossover strategy: {invalid_params}. Valid: {valid_params}"
            )
        
        # Create optimization engine
        engine = OptimizationEngine(request, current_user_id)
        
        # Run optimization
        result = engine.optimize()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during optimization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/status")
async def get_optimization_status(current_user_id: str = Depends(get_current_user)):
    """
    Get the status of the optimization engine
    """
    try:
        # Test if optimization modules are available
        import optuna
        from run_initial_backtest import BacktestRunner
        
        return {
            "status": "ready",
            "optuna_version": optuna.__version__,
            "supported_strategies": ["sma_crossover"],
            "supported_objectives": ["sharpe_ratio", "total_return", "calmar_ratio"],
            "max_trials": 1000,
            "max_timeout": 3600,
            "default_parameters": {
                "n_trials": 100,
                "timeout": 300,
                "objective": "sharpe_ratio"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user_id
        }
        
    except ImportError as e:
        return {
            "status": "error",
            "error": f"Optimization modules not available: {str(e)}",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user_id
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": current_user_id
        }