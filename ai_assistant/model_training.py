"""
Model Training Pipeline for Stock Forecasting Models
Comprehensive training system with hyperparameter tuning, cross-validation, and experiment tracking

This module provides a complete training pipeline for all forecasting models including
hyperparameter optimization using Optuna, time series cross-validation, performance
monitoring, and model versioning.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import os
import json
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

# Optuna for hyperparameter optimization
try:
    import optuna
    from optuna.samplers import TPESampler
    from optuna.pruners import MedianPruner
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logging.warning("Optuna not available. Install with: pip install optuna")

# MLflow for experiment tracking
try:
    import mlflow
    import mlflow.sklearn
    import mlflow.pytorch
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logging.warning("MLflow not available. Install with: pip install mlflow")

from .forecasting_models import (
    BaseForecastingModel, ModelConfig, ModelType, PredictionHorizon,
    ModelPerformance, ForecastingModelFactory, FeastDataLoader,
    validate_data_quality
)

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Configuration for model training pipeline"""
    model_type: ModelType
    prediction_horizon: PredictionHorizon
    lookback_window: int = 60
    features: List[str] = field(default_factory=list)
    
    # Training parameters
    train_test_split: float = 0.8
    validation_split: float = 0.2
    cv_folds: int = 5
    
    # Hyperparameter optimization
    optimize_hyperparams: bool = True
    n_trials: int = 100
    optimization_timeout: int = 3600  # seconds
    optimization_metric: str = "rmse"
    
    # Model persistence
    save_model: bool = True
    model_dir: str = "ai_assistant/models"
    experiment_name: str = "stock_forecasting"
    
    # Performance thresholds
    min_performance_threshold: float = 0.0
    max_training_time: int = 7200  # seconds
    
    def __post_init__(self):
        if not self.features:
            self.features = [
                "closing_price", "daily_volume", "daily_high", "daily_low",
                "sma_20", "sma_50", "rsi_14", "macd_line", "volatility_20d"
            ]


@dataclass
class TrainingResult:
    """Result of model training"""
    model: BaseForecastingModel
    performance: ModelPerformance
    best_hyperparams: Dict[str, Any]
    training_time: float
    cv_scores: List[float]
    model_path: Optional[str] = None
    experiment_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert training result to dictionary"""
        return {
            "model_type": self.model.config.model_type.value,
            "prediction_horizon": self.model.config.prediction_horizon.value,
            "performance": self.performance.to_dict(),
            "best_hyperparams": self.best_hyperparams,
            "training_time": self.training_time,
            "cv_scores": self.cv_scores,
            "model_path": self.model_path,
            "experiment_id": self.experiment_id,
            "metadata": self.metadata
        }


class ModelTrainer:
    """
    Comprehensive model training pipeline with hyperparameter optimization
    """
    
    def __init__(self, config: TrainingConfig):
        self.config = config
        self.data_loader = FeastDataLoader()
        
        # Initialize MLflow if available
        if MLFLOW_AVAILABLE:
            mlflow.set_experiment(config.experiment_name)
        
        # Create model directory
        os.makedirs(config.model_dir, exist_ok=True)
    
    def train_model(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        custom_data: Optional[pd.DataFrame] = None
    ) -> TrainingResult:
        """
        Train a forecasting model with full pipeline
        
        Args:
            ticker: Stock ticker symbol
            start_date: Training data start date
            end_date: Training data end date
            custom_data: Optional custom training data
            
        Returns:
            Training result with model and metrics
        """
        start_time = datetime.now()
        
        logger.info(f"Starting training for {self.config.model_type.value} model")
        logger.info(f"Ticker: {ticker}, Period: {start_date} to {end_date}")
        
        # Load or use custom data
        if custom_data is not None:
            data = custom_data.copy()
        else:
            data = self.data_loader.load_historical_data(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                features=self.config.features
            )
        
        # Validate data quality
        quality_report = validate_data_quality(data, self.config.features)
        if not quality_report["is_valid"]:
            logger.warning(f"Data quality issues: {quality_report['issues']}")
        
        # Start MLflow run
        if MLFLOW_AVAILABLE:
            mlflow.start_run()
            mlflow.log_params({
                "model_type": self.config.model_type.value,
                "prediction_horizon": self.config.prediction_horizon.value,
                "lookback_window": self.config.lookback_window,
                "ticker": ticker,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            })
        
        try:
            # Optimize hyperparameters if enabled
            if self.config.optimize_hyperparams and OPTUNA_AVAILABLE:
                best_hyperparams = self._optimize_hyperparameters(data, ticker)
            else:
                best_hyperparams = {}
            
            # Create model with best hyperparameters
            model_config = ModelConfig(
                model_type=self.config.model_type,
                prediction_horizon=self.config.prediction_horizon,
                lookback_window=self.config.lookback_window,
                features=self.config.features,
                hyperparameters=best_hyperparams
            )
            
            model = ForecastingModelFactory.create_model(
                self.config.model_type,
                model_config
            )
            
            # Perform cross-validation
            cv_scores = self._cross_validate_model(model, data)
            
            # Train final model on full dataset
            logger.info("Training final model on full dataset...")
            performance = model.train(data)
            
            # Calculate training time
            training_time = (datetime.now() - start_time).total_seconds()
            
            # Save model if enabled
            model_path = None
            if self.config.save_model:
                model_path = self._save_model(model, ticker, best_hyperparams)
            
            # Log metrics to MLflow
            if MLFLOW_AVAILABLE:
                mlflow.log_metrics({
                    "rmse": performance.rmse,
                    "mae": performance.mae,
                    "mape": performance.mape,
                    "directional_accuracy": performance.directional_accuracy,
                    "r2_score": performance.r2_score,
                    "training_time": training_time,
                    "cv_mean": np.mean(cv_scores),
                    "cv_std": np.std(cv_scores)
                })
                
                if model_path:
                    mlflow.log_artifact(model_path)
            
            # Create training result
            result = TrainingResult(
                model=model,
                performance=performance,
                best_hyperparams=best_hyperparams,
                training_time=training_time,
                cv_scores=cv_scores,
                model_path=model_path,
                experiment_id=mlflow.active_run().info.run_id if MLFLOW_AVAILABLE else None,
                metadata={
                    "ticker": ticker,
                    "data_quality": quality_report,
                    "training_samples": len(data),
                    "features_used": len(self.config.features)
                }
            )
            
            logger.info(f"Training completed successfully in {training_time:.2f} seconds")
            logger.info(f"Final RMSE: {performance.rmse:.4f}, MAE: {performance.mae:.4f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Training failed: {e}")
            raise
        finally:
            if MLFLOW_AVAILABLE and mlflow.active_run():
                mlflow.end_run()
    
    def _optimize_hyperparameters(
        self,
        data: pd.DataFrame,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Optimize hyperparameters using Optuna
        
        Args:
            data: Training data
            ticker: Stock ticker symbol
            
        Returns:
            Best hyperparameters
        """
        logger.info("Starting hyperparameter optimization...")
        
        def objective(trial):
            try:
                # Suggest hyperparameters based on model type
                hyperparams = self._suggest_hyperparameters(trial)
                
                # Create model with suggested hyperparameters
                model_config = ModelConfig(
                    model_type=self.config.model_type,
                    prediction_horizon=self.config.prediction_horizon,
                    lookback_window=self.config.lookback_window,
                    features=self.config.features,
                    hyperparameters=hyperparams
                )
                
                model = ForecastingModelFactory.create_model(
                    self.config.model_type,
                    model_config
                )
                
                # Perform cross-validation
                cv_scores = self._cross_validate_model(model, data, n_folds=3)  # Reduced for optimization
                
                # Return mean CV score
                mean_score = np.mean(cv_scores)
                
                # Log intermediate result
                trial.report(mean_score, step=0)
                
                return mean_score
                
            except Exception as e:
                logger.warning(f"Trial failed: {e}")
                return float('inf')
        
        # Create study
        study = optuna.create_study(
            direction='minimize',
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        )
        
        # Optimize
        study.optimize(
            objective,
            n_trials=self.config.n_trials,
            timeout=self.config.optimization_timeout,
            show_progress_bar=True
        )
        
        logger.info(f"Optimization completed. Best {self.config.optimization_metric}: {study.best_value:.4f}")
        logger.info(f"Best hyperparameters: {study.best_params}")
        
        return study.best_params
    
    def _suggest_hyperparameters(self, trial) -> Dict[str, Any]:
        """Suggest hyperparameters based on model type"""
        if self.config.model_type == ModelType.LSTM:
            return {
                'hidden_size': trial.suggest_categorical('hidden_size', [64, 128, 256]),
                'num_layers': trial.suggest_int('num_layers', 1, 3),
                'dropout': trial.suggest_float('dropout', 0.1, 0.5),
                'learning_rate': trial.suggest_loguniform('learning_rate', 1e-4, 1e-2),
                'batch_size': trial.suggest_categorical('batch_size', [16, 32, 64]),
                'epochs': 50,  # Fixed for optimization speed
                'patience': 10
            }
        
        elif self.config.model_type == ModelType.RANDOM_FOREST:
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 200),
                'max_depth': trial.suggest_int('max_depth', 5, 20),
                'min_samples_split': trial.suggest_int('min_samples_split', 2, 10),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 5),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None])
            }
        
        elif self.config.model_type == ModelType.XGBOOST:
            return {
                'n_estimators': trial.suggest_int('n_estimators', 50, 200),
                'max_depth': trial.suggest_int('max_depth', 3, 10),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
                'reg_alpha': trial.suggest_loguniform('reg_alpha', 1e-3, 10.0),
                'reg_lambda': trial.suggest_loguniform('reg_lambda', 1e-3, 10.0)
            }
        
        elif self.config.model_type == ModelType.ARIMA:
            return {
                'p': trial.suggest_int('p', 0, 5),
                'd': trial.suggest_int('d', 0, 2),
                'q': trial.suggest_int('q', 0, 5),
                'auto_arima': False  # Use manual parameters for optimization
            }
        
        elif self.config.model_type == ModelType.PROPHET:
            return {
                'changepoint_prior_scale': trial.suggest_loguniform('changepoint_prior_scale', 0.001, 0.5),
                'seasonality_prior_scale': trial.suggest_loguniform('seasonality_prior_scale', 0.01, 10),
                'holidays_prior_scale': trial.suggest_loguniform('holidays_prior_scale', 0.01, 10),
                'seasonality_mode': trial.suggest_categorical('seasonality_mode', ['additive', 'multiplicative'])
            }
        
        else:
            return {}
    
    def _cross_validate_model(
        self,
        model: BaseForecastingModel,
        data: pd.DataFrame,
        n_folds: Optional[int] = None
    ) -> List[float]:
        """
        Perform time series cross-validation
        
        Args:
            model: Model to validate
            data: Training data
            n_folds: Number of CV folds (uses config if None)
            
        Returns:
            List of CV scores
        """
        n_folds = n_folds or self.config.cv_folds
        
        logger.info(f"Performing {n_folds}-fold time series cross-validation...")
        
        # Time series split
        tscv = TimeSeriesSplit(n_splits=n_folds)
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(data)):
            try:
                # Split data
                train_data = data.iloc[train_idx]
                val_data = data.iloc[val_idx]
                
                # Create a copy of the model for this fold
                fold_config = ModelConfig(
                    model_type=model.config.model_type,
                    prediction_horizon=model.config.prediction_horizon,
                    lookback_window=model.config.lookback_window,
                    features=model.config.features,
                    hyperparameters=model.config.hyperparameters,
                    scaling_method=model.config.scaling_method
                )
                
                fold_model = ForecastingModelFactory.create_model(
                    model.config.model_type,
                    fold_config
                )
                
                # Train on fold training data
                fold_model.train(train_data)
                
                # Predict on validation data
                prediction_result = fold_model.predict(val_data, ticker="CV")
                predictions = prediction_result.predictions
                
                # Get actual values for validation
                target_col = fold_model.config.target_column
                if target_col in val_data.columns:
                    actual_values = val_data[target_col].values[-len(predictions):]
                else:
                    # Use closing price as fallback
                    actual_values = val_data['closing_price'].values[-len(predictions):]
                
                # Calculate score
                if self.config.optimization_metric == "rmse":
                    score = np.sqrt(mean_squared_error(actual_values, predictions))
                elif self.config.optimization_metric == "mae":
                    score = mean_absolute_error(actual_values, predictions)
                elif self.config.optimization_metric == "mape":
                    score = mean_absolute_percentage_error(actual_values, predictions) * 100
                else:
                    score = np.sqrt(mean_squared_error(actual_values, predictions))
                
                cv_scores.append(score)
                logger.info(f"Fold {fold + 1}/{n_folds}: {self.config.optimization_metric.upper()} = {score:.4f}")
                
            except Exception as e:
                logger.warning(f"Fold {fold + 1} failed: {e}")
                cv_scores.append(float('inf'))
        
        logger.info(f"CV {self.config.optimization_metric.upper()}: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
        return cv_scores
    
    def _save_model(
        self,
        model: BaseForecastingModel,
        ticker: str,
        hyperparams: Dict[str, Any]
    ) -> str:
        """
        Save trained model to disk
        
        Args:
            model: Trained model
            ticker: Stock ticker
            hyperparams: Best hyperparameters
            
        Returns:
            Path to saved model
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_filename = f"{self.config.model_type.value}_{ticker}_{self.config.prediction_horizon.value}d_{timestamp}.pkl"
        model_path = os.path.join(self.config.model_dir, model_filename)
        
        # Save model
        model.save_model(model_path)
        
        # Save metadata
        metadata = {
            "model_type": self.config.model_type.value,
            "prediction_horizon": self.config.prediction_horizon.value,
            "ticker": ticker,
            "hyperparameters": hyperparams,
            "training_config": {
                "lookback_window": self.config.lookback_window,
                "features": self.config.features,
                "optimization_metric": self.config.optimization_metric
            },
            "created_at": timestamp,
            "model_file": model_filename
        }
        
        metadata_path = model_path.replace('.pkl', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_path}")
        return model_path


class BatchTrainer:
    """
    Batch training for multiple models and tickers
    """
    
    def __init__(self, base_config: TrainingConfig):
        self.base_config = base_config
        self.results = {}
    
    def train_multiple_models(
        self,
        tickers: List[str],
        model_types: List[ModelType],
        start_date: datetime,
        end_date: datetime,
        prediction_horizons: List[PredictionHorizon] = None
    ) -> Dict[str, Dict[str, TrainingResult]]:
        """
        Train multiple models for multiple tickers
        
        Args:
            tickers: List of stock tickers
            model_types: List of model types to train
            start_date: Training data start date
            end_date: Training data end date
            prediction_horizons: List of prediction horizons
            
        Returns:
            Dictionary of training results
        """
        if prediction_horizons is None:
            prediction_horizons = [PredictionHorizon.SEVEN_DAYS]
        
        total_combinations = len(tickers) * len(model_types) * len(prediction_horizons)
        logger.info(f"Starting batch training for {total_combinations} model combinations")
        
        results = {}
        completed = 0
        
        for ticker in tickers:
            results[ticker] = {}
            
            for model_type in model_types:
                for horizon in prediction_horizons:
                    try:
                        # Create training config for this combination
                        config = TrainingConfig(
                            model_type=model_type,
                            prediction_horizon=horizon,
                            lookback_window=self.base_config.lookback_window,
                            features=self.base_config.features,
                            optimize_hyperparams=self.base_config.optimize_hyperparams,
                            n_trials=self.base_config.n_trials // 2,  # Reduce trials for batch training
                            model_dir=self.base_config.model_dir,
                            experiment_name=f"{self.base_config.experiment_name}_batch"
                        )
                        
                        # Train model
                        trainer = ModelTrainer(config)
                        result = trainer.train_model(ticker, start_date, end_date)
                        
                        # Store result
                        key = f"{model_type.value}_{horizon.value}d"
                        results[ticker][key] = result
                        
                        completed += 1
                        logger.info(f"Completed {completed}/{total_combinations}: {ticker} - {key}")
                        
                    except Exception as e:
                        logger.error(f"Failed to train {ticker} - {model_type.value} - {horizon.value}d: {e}")
                        key = f"{model_type.value}_{horizon.value}d"
                        if ticker not in results:
                            results[ticker] = {}
                        results[ticker][key] = {"error": str(e)}
        
        self.results = results
        logger.info(f"Batch training completed. {completed}/{total_combinations} successful")
        
        return results
    
    def get_best_models_per_ticker(self, metric: str = "rmse") -> Dict[str, Tuple[str, TrainingResult]]:
        """Get the best performing model for each ticker"""
        best_models = {}
        
        for ticker, ticker_results in self.results.items():
            best_score = float('inf') if metric in ['rmse', 'mae', 'mape'] else float('-inf')
            best_model_key = None
            best_result = None
            
            for model_key, result in ticker_results.items():
                if isinstance(result, dict) and "error" in result:
                    continue
                
                if hasattr(result, 'performance'):
                    score = getattr(result.performance, metric, None)
                    if score is None:
                        continue
                    
                    if metric in ['rmse', 'mae', 'mape']:
                        if score < best_score:
                            best_score = score
                            best_model_key = model_key
                            best_result = result
                    else:
                        if score > best_score:
                            best_score = score
                            best_model_key = model_key
                            best_result = result
            
            if best_model_key and best_result:
                best_models[ticker] = (best_model_key, best_result)
        
        return best_models
    
    def save_batch_results(self, filepath: str) -> None:
        """Save batch training results to file"""
        # Convert results to serializable format
        serializable_results = {}
        
        for ticker, ticker_results in self.results.items():
            serializable_results[ticker] = {}
            
            for model_key, result in ticker_results.items():
                if isinstance(result, dict):
                    serializable_results[ticker][model_key] = result
                else:
                    serializable_results[ticker][model_key] = result.to_dict()
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        logger.info(f"Batch results saved to {filepath}")


# Utility functions
def load_trained_model(model_path: str) -> BaseForecastingModel:
    """
    Load a trained model from disk
    
    Args:
        model_path: Path to saved model
        
    Returns:
        Loaded model
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    # Load metadata to determine model type
    metadata_path = model_path.replace('.pkl', '_metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        model_type = ModelType(metadata['model_type'])
        prediction_horizon = PredictionHorizon(metadata['prediction_horizon'])
        
        # Create model config
        config = ModelConfig(
            model_type=model_type,
            prediction_horizon=prediction_horizon,
            lookback_window=metadata['training_config']['lookback_window'],
            features=metadata['training_config']['features'],
            hyperparameters=metadata['hyperparameters']
        )
        
        # Create and load model
        model = ForecastingModelFactory.create_model(model_type, config)
        model.load_model(model_path)
        
        return model
    else:
        # Fallback: try to load model directly
        import joblib
        model_data = joblib.load(model_path)
        
        if isinstance(model_data, dict) and 'model' in model_data:
            # Extract model from saved data
            config = model_data.get('config')
            model = ForecastingModelFactory.create_model(config.model_type, config)
            model.load_model(model_path)
            return model
        else:
            raise ValueError("Invalid model file format")


def create_training_config(
    model_type: str,
    prediction_horizon: int = 7,
    optimize_hyperparams: bool = True,
    **kwargs
) -> TrainingConfig:
    """
    Create a training configuration
    
    Args:
        model_type: Type of model ('lstm', 'arima', 'random_forest', 'xgboost', 'prophet')
        prediction_horizon: Prediction horizon in days
        optimize_hyperparams: Whether to optimize hyperparameters
        **kwargs: Additional configuration parameters
        
    Returns:
        Training configuration
    """
    # Map string to enum
    model_type_map = {
        'lstm': ModelType.LSTM,
        'arima': ModelType.ARIMA,
        'random_forest': ModelType.RANDOM_FOREST,
        'xgboost': ModelType.XGBOOST,
        'prophet': ModelType.PROPHET,
        'ensemble': ModelType.ENSEMBLE
    }
    
    horizon_map = {
        1: PredictionHorizon.ONE_DAY,
        7: PredictionHorizon.SEVEN_DAYS,
        30: PredictionHorizon.THIRTY_DAYS
    }
    
    return TrainingConfig(
        model_type=model_type_map[model_type.lower()],
        prediction_horizon=horizon_map.get(prediction_horizon, PredictionHorizon.SEVEN_DAYS),
        optimize_hyperparams=optimize_hyperparams,
        **kwargs
    )


# Export main classes and functions
__all__ = [
    "TrainingConfig",
    "TrainingResult",
    "ModelTrainer",
    "BatchTrainer",
    "load_trained_model",
    "create_training_config"
]