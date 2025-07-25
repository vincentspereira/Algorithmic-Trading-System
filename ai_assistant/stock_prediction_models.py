"""
Stock Prediction Models Collection
Multiple forecasting algorithms for stock price prediction

This module implements various machine learning and statistical models for stock price
forecasting including ARIMA, Random Forest, XGBoost, Prophet, and ensemble methods.

Author: Kilo Code
Version: 1.0.0
"""

import logging
import warnings
from typing import Dict, Any, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Statistical models
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# Machine learning models
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error
import xgboost as xgb
import lightgbm as lgb

# Prophet for time series forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not available. Install with: pip install prophet")

from .forecasting_models import (
    BaseForecastingModel, ModelConfig, ModelType, PredictionResult, 
    ModelPerformance, PredictionHorizon
)

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure logging
logger = logging.getLogger(__name__)


class ARIMAModel(BaseForecastingModel):
    """
    ARIMA (AutoRegressive Integrated Moving Average) model for time series forecasting
    Suitable for univariate time series with trend and seasonality
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        
        # ARIMA-specific hyperparameters
        self.hyperparams = {
            'p': 5,  # AR order
            'd': 1,  # Differencing order
            'q': 0,  # MA order
            'seasonal': False,
            'seasonal_order': (0, 0, 0, 0),
            'auto_arima': True,  # Use auto ARIMA for parameter selection
            'max_p': 5,
            'max_d': 2,
            'max_q': 5,
            'information_criterion': 'aic'
        }
        
        # Update with config hyperparameters
        self.hyperparams.update(config.hyperparameters)
        
        self.fitted_model = None
        self.differencing_applied = False
        self.original_series = None
    
    def _build_model(self) -> None:
        """ARIMA model is built during training"""
        return None
    
    def _check_stationarity(self, series: pd.Series) -> Tuple[bool, float]:
        """Check if time series is stationary using Augmented Dickey-Fuller test"""
        try:
            result = adfuller(series.dropna())
            adf_statistic = result[0]
            p_value = result[1]
            
            # Series is stationary if p-value < 0.05
            is_stationary = p_value < 0.05
            
            logger.info(f"ADF Statistic: {adf_statistic:.6f}, p-value: {p_value:.6f}")
            logger.info(f"Series is {'stationary' if is_stationary else 'non-stationary'}")
            
            return is_stationary, p_value
            
        except Exception as e:
            logger.warning(f"Stationarity test failed: {e}")
            return False, 1.0
    
    def _auto_arima_selection(self, series: pd.Series) -> Tuple[int, int, int]:
        """Automatically select ARIMA parameters using grid search"""
        try:
            from pmdarima import auto_arima
            
            logger.info("Running auto ARIMA parameter selection...")
            
            auto_model = auto_arima(
                series,
                start_p=0, start_q=0,
                max_p=self.hyperparams['max_p'],
                max_d=self.hyperparams['max_d'],
                max_q=self.hyperparams['max_q'],
                seasonal=self.hyperparams['seasonal'],
                stepwise=True,
                suppress_warnings=True,
                error_action='ignore',
                information_criterion=self.hyperparams['information_criterion']
            )
            
            p, d, q = auto_model.order
            logger.info(f"Auto ARIMA selected parameters: p={p}, d={d}, q={q}")
            
            return p, d, q
            
        except ImportError:
            logger.warning("pmdarima not available. Using default parameters.")
            return self.hyperparams['p'], self.hyperparams['d'], self.hyperparams['q']
        except Exception as e:
            logger.warning(f"Auto ARIMA failed: {e}. Using default parameters.")
            return self.hyperparams['p'], self.hyperparams['d'], self.hyperparams['q']
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train ARIMA model"""
        # ARIMA works with univariate time series, use target column
        if len(y.shape) > 1:
            y = y.flatten()
        
        # Convert to pandas Series for ARIMA
        series = pd.Series(y)
        self.original_series = series.copy()
        
        # Check stationarity
        is_stationary, p_value = self._check_stationarity(series)
        
        # Select ARIMA parameters
        if self.hyperparams['auto_arima']:
            p, d, q = self._auto_arima_selection(series)
        else:
            p = self.hyperparams['p']
            d = self.hyperparams['d']
            q = self.hyperparams['q']
        
        # Fit ARIMA model
        try:
            logger.info(f"Fitting ARIMA({p}, {d}, {q}) model...")
            
            if self.hyperparams['seasonal']:
                seasonal_order = self.hyperparams['seasonal_order']
                self.fitted_model = ARIMA(
                    series, 
                    order=(p, d, q),
                    seasonal_order=seasonal_order
                ).fit()
            else:
                self.fitted_model = ARIMA(series, order=(p, d, q)).fit()
            
            logger.info("ARIMA model fitted successfully")
            logger.info(f"AIC: {self.fitted_model.aic:.2f}")
            logger.info(f"BIC: {self.fitted_model.bic:.2f}")
            
        except Exception as e:
            logger.error(f"ARIMA model fitting failed: {e}")
            raise
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with ARIMA model"""
        if self.fitted_model is None:
            raise ValueError("Model must be trained before making predictions")
        
        try:
            # Forecast future values
            forecast_steps = self.config.prediction_horizon.value
            forecast = self.fitted_model.forecast(steps=forecast_steps)
            
            if isinstance(forecast, pd.Series):
                predictions = forecast.values
            else:
                predictions = np.array(forecast)
            
            return predictions
            
        except Exception as e:
            logger.error(f"ARIMA prediction failed: {e}")
            raise
    
    def _calculate_confidence_intervals(
        self,
        X: np.ndarray,
        predictions: np.ndarray
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Calculate confidence intervals from ARIMA forecast"""
        if self.fitted_model is None:
            return super()._calculate_confidence_intervals(X, predictions)
        
        try:
            forecast_steps = self.config.prediction_horizon.value
            forecast_result = self.fitted_model.get_forecast(steps=forecast_steps)
            
            # Get confidence intervals
            conf_int = forecast_result.conf_int()
            
            if hasattr(conf_int, 'values'):
                lower = conf_int.values[:, 0]
                upper = conf_int.values[:, 1]
            else:
                lower = conf_int.iloc[:, 0].values
                upper = conf_int.iloc[:, 1].values
            
            return (lower, upper)
            
        except Exception as e:
            logger.warning(f"Failed to calculate ARIMA confidence intervals: {e}")
            return super()._calculate_confidence_intervals(X, predictions)
    
    def _calculate_model_confidence(self) -> float:
        """Calculate model confidence based on AIC/BIC"""
        if self.fitted_model is None:
            return 0.5
        
        # Use AIC to estimate confidence (lower AIC = higher confidence)
        aic = self.fitted_model.aic
        
        # Normalize AIC to confidence score (heuristic)
        confidence = 1.0 / (1.0 + abs(aic) / 1000.0)
        return min(max(confidence, 0.0), 1.0)


class RandomForestModel(BaseForecastingModel):
    """
    Random Forest model for stock price prediction
    Suitable for feature-based predictions with non-linear relationships
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        
        # Random Forest hyperparameters
        self.hyperparams = {
            'n_estimators': 100,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'sqrt',
            'random_state': 42,
            'n_jobs': -1,
            'bootstrap': True,
            'oob_score': True
        }
        
        # Update with config hyperparameters
        self.hyperparams.update(config.hyperparameters)
    
    def _build_model(self) -> RandomForestRegressor:
        """Build Random Forest model"""
        return RandomForestRegressor(**self.hyperparams)
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train Random Forest model"""
        # Reshape data for sklearn
        if len(X.shape) == 3:
            X = X.reshape(X.shape[0], -1)
        
        if len(y.shape) > 1:
            y = y.flatten()
        
        logger.info(f"Training Random Forest with {X.shape[0]} samples and {X.shape[1]} features")
        
        # Fit the model
        self.model.fit(X, y)
        
        # Log training metrics
        if self.hyperparams.get('oob_score', False):
            logger.info(f"Out-of-bag score: {self.model.oob_score_:.4f}")
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Random Forest"""
        # Reshape data for sklearn
        if len(X.shape) == 3:
            X = X.reshape(X.shape[0], -1)
        
        predictions = self.model.predict(X)
        
        # Handle multi-step predictions
        if self.config.prediction_horizon.value > 1:
            # For multi-step, repeat the last prediction
            # More sophisticated approaches could use recursive prediction
            last_pred = predictions[-1] if len(predictions) > 0 else 0
            predictions = np.full(self.config.prediction_horizon.value, last_pred)
        
        return predictions
    
    def _get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from Random Forest"""
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            return None
        
        if not self.feature_columns:
            return None
        
        importances = self.model.feature_importances_
        
        # Handle flattened features for time series
        if len(importances) > len(self.feature_columns):
            # Average importance across time steps
            n_features = len(self.feature_columns)
            n_timesteps = len(importances) // n_features
            
            avg_importances = []
            for i in range(n_features):
                feature_importance = np.mean([
                    importances[j * n_features + i] 
                    for j in range(n_timesteps)
                ])
                avg_importances.append(feature_importance)
            
            importances = np.array(avg_importances)
        
        # Normalize to sum to 1
        importances = importances / importances.sum()
        
        importance_dict = {
            feature: float(importance)
            for feature, importance in zip(self.feature_columns, importances)
        }
        
        return importance_dict
    
    def _calculate_model_confidence(self) -> float:
        """Calculate model confidence based on OOB score"""
        if self.model is None:
            return 0.5
        
        if hasattr(self.model, 'oob_score_'):
            # OOB score is R² score, convert to confidence
            oob_score = self.model.oob_score_
            confidence = max(0.0, min(1.0, (oob_score + 1.0) / 2.0))
            return confidence
        
        return 0.5


class XGBoostModel(BaseForecastingModel):
    """
    XGBoost model for stock price prediction
    Gradient boosting with advanced regularization and feature selection
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        
        # XGBoost hyperparameters
        self.hyperparams = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'reg_alpha': 0.1,
            'reg_lambda': 1.0,
            'random_state': 42,
            'n_jobs': -1,
            'early_stopping_rounds': 10,
            'eval_metric': 'rmse'
        }
        
        # Update with config hyperparameters
        self.hyperparams.update(config.hyperparameters)
    
    def _build_model(self) -> xgb.XGBRegressor:
        """Build XGBoost model"""
        # Remove early_stopping_rounds from model params
        model_params = self.hyperparams.copy()
        model_params.pop('early_stopping_rounds', None)
        model_params.pop('eval_metric', None)
        
        return xgb.XGBRegressor(**model_params)
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train XGBoost model"""
        # Reshape data for sklearn
        if len(X.shape) == 3:
            X = X.reshape(X.shape[0], -1)
        
        if len(y.shape) > 1:
            y = y.flatten()
        
        # Split for early stopping
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        logger.info(f"Training XGBoost with {X_train.shape[0]} samples and {X_train.shape[1]} features")
        
        # Fit with early stopping
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=self.hyperparams.get('early_stopping_rounds', 10),
            verbose=False
        )
        
        # Log training metrics
        if hasattr(self.model, 'best_score'):
            logger.info(f"Best validation score: {self.model.best_score:.4f}")
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with XGBoost"""
        # Reshape data for sklearn
        if len(X.shape) == 3:
            X = X.reshape(X.shape[0], -1)
        
        predictions = self.model.predict(X)
        
        # Handle multi-step predictions
        if self.config.prediction_horizon.value > 1:
            # For multi-step, repeat the last prediction
            last_pred = predictions[-1] if len(predictions) > 0 else 0
            predictions = np.full(self.config.prediction_horizon.value, last_pred)
        
        return predictions
    
    def _get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from XGBoost"""
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            return None
        
        if not self.feature_columns:
            return None
        
        importances = self.model.feature_importances_
        
        # Handle flattened features for time series
        if len(importances) > len(self.feature_columns):
            # Average importance across time steps
            n_features = len(self.feature_columns)
            n_timesteps = len(importances) // n_features
            
            avg_importances = []
            for i in range(n_features):
                feature_importance = np.mean([
                    importances[j * n_features + i] 
                    for j in range(n_timesteps)
                ])
                avg_importances.append(feature_importance)
            
            importances = np.array(avg_importances)
        
        # Normalize to sum to 1
        importances = importances / importances.sum()
        
        importance_dict = {
            feature: float(importance)
            for feature, importance in zip(self.feature_columns, importances)
        }
        
        return importance_dict
    
    def _calculate_model_confidence(self) -> float:
        """Calculate model confidence based on validation score"""
        if self.model is None:
            return 0.5
        
        if hasattr(self.model, 'best_score'):
            # Convert RMSE to confidence (lower RMSE = higher confidence)
            rmse = self.model.best_score
            confidence = 1.0 / (1.0 + rmse)
            return min(max(confidence, 0.0), 1.0)
        
        return 0.5


class ProphetModel(BaseForecastingModel):
    """
    Prophet model for time series forecasting
    Handles trend, seasonality, and holidays automatically
    """
    
    def __init__(self, config: ModelConfig):
        if not PROPHET_AVAILABLE:
            raise ImportError("Prophet is required for ProphetModel. Install with: pip install prophet")
        
        super().__init__(config)
        
        # Prophet hyperparameters
        self.hyperparams = {
            'growth': 'linear',
            'changepoints': None,
            'n_changepoints': 25,
            'changepoint_range': 0.8,
            'yearly_seasonality': 'auto',
            'weekly_seasonality': 'auto',
            'daily_seasonality': 'auto',
            'seasonality_mode': 'additive',
            'seasonality_prior_scale': 10.0,
            'holidays_prior_scale': 10.0,
            'changepoint_prior_scale': 0.05,
            'mcmc_samples': 0,
            'interval_width': 0.95,
            'uncertainty_samples': 1000
        }
        
        # Update with config hyperparameters
        self.hyperparams.update(config.hyperparameters)
        
        self.prophet_model = None
        self.last_date = None
    
    def _build_model(self) -> Prophet:
        """Build Prophet model"""
        return Prophet(**self.hyperparams)
    
    def _prepare_prophet_data(self, X: np.ndarray, y: np.ndarray) -> pd.DataFrame:
        """Prepare data in Prophet format (ds, y columns)"""
        if len(y.shape) > 1:
            y = y.flatten()
        
        # Create date range (assuming daily data)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=len(y) - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Store last date for future predictions
        self.last_date = dates[-1]
        
        # Create Prophet DataFrame
        df = pd.DataFrame({
            'ds': dates[:len(y)],
            'y': y
        })
        
        return df
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train Prophet model"""
        logger.info("Training Prophet model...")
        
        # Prepare data
        df = self._prepare_prophet_data(X, y)
        
        # Fit Prophet model
        self.prophet_model = self.model
        self.prophet_model.fit(df)
        
        logger.info("Prophet model fitted successfully")
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with Prophet"""
        if self.prophet_model is None:
            raise ValueError("Model must be trained before making predictions")
        
        # Create future dataframe
        future_periods = self.config.prediction_horizon.value
        future = self.prophet_model.make_future_dataframe(periods=future_periods)
        
        # Make forecast
        forecast = self.prophet_model.predict(future)
        
        # Extract predictions for future periods
        predictions = forecast['yhat'].tail(future_periods).values
        
        return predictions
    
    def _calculate_confidence_intervals(
        self,
        X: np.ndarray,
        predictions: np.ndarray
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Calculate confidence intervals from Prophet forecast"""
        if self.prophet_model is None:
            return super()._calculate_confidence_intervals(X, predictions)
        
        try:
            # Create future dataframe
            future_periods = self.config.prediction_horizon.value
            future = self.prophet_model.make_future_dataframe(periods=future_periods)
            
            # Make forecast with uncertainty
            forecast = self.prophet_model.predict(future)
            
            # Extract confidence intervals for future periods
            lower = forecast['yhat_lower'].tail(future_periods).values
            upper = forecast['yhat_upper'].tail(future_periods).values
            
            return (lower, upper)
            
        except Exception as e:
            logger.warning(f"Failed to calculate Prophet confidence intervals: {e}")
            return super()._calculate_confidence_intervals(X, predictions)
    
    def _calculate_model_confidence(self) -> float:
        """Calculate model confidence based on forecast uncertainty"""
        if self.prophet_model is None:
            return 0.5
        
        # Use the width of confidence intervals as uncertainty measure
        try:
            future = self.prophet_model.make_future_dataframe(periods=1)
            forecast = self.prophet_model.predict(future)
            
            last_forecast = forecast.iloc[-1]
            uncertainty = last_forecast['yhat_upper'] - last_forecast['yhat_lower']
            prediction = last_forecast['yhat']
            
            # Calculate confidence as inverse of relative uncertainty
            if prediction != 0:
                relative_uncertainty = abs(uncertainty / prediction)
                confidence = 1.0 / (1.0 + relative_uncertainty)
            else:
                confidence = 0.5
            
            return min(max(confidence, 0.0), 1.0)
            
        except Exception:
            return 0.5


class EnsembleModel(BaseForecastingModel):
    """
    Ensemble model combining multiple forecasting algorithms
    Uses weighted averaging based on individual model performance
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        
        # Ensemble hyperparameters
        self.hyperparams = {
            'models': ['random_forest', 'xgboost', 'arima'],
            'weighting_method': 'performance',  # 'equal', 'performance', 'dynamic'
            'performance_metric': 'rmse',
            'min_weight': 0.1,  # Minimum weight for any model
            'validation_split': 0.2
        }
        
        # Update with config hyperparameters
        self.hyperparams.update(config.hyperparameters)
        
        self.base_models = {}
        self.model_weights = {}
        self.model_performances = {}
    
    def _build_model(self) -> Dict[str, BaseForecastingModel]:
        """Build ensemble of base models"""
        models = {}
        
        for model_name in self.hyperparams['models']:
            if model_name == 'random_forest':
                model_config = ModelConfig(
                    model_type=ModelType.RANDOM_FOREST,
                    prediction_horizon=self.config.prediction_horizon,
                    lookback_window=self.config.lookback_window,
                    features=self.config.features,
                    scaling_method=self.config.scaling_method
                )
                models[model_name] = RandomForestModel(model_config)
                
            elif model_name == 'xgboost':
                model_config = ModelConfig(
                    model_type=ModelType.XGBOOST,
                    prediction_horizon=self.config.prediction_horizon,
                    lookback_window=self.config.lookback_window,
                    features=self.config.features,
                    scaling_method=self.config.scaling_method
                )
                models[model_name] = XGBoostModel(model_config)
                
            elif model_name == 'arima':
                model_config = ModelConfig(
                    model_type=ModelType.ARIMA,
                    prediction_horizon=self.config.prediction_horizon,
                    lookback_window=self.config.lookback_window,
                    features=self.config.features,
                    scaling_method=self.config.scaling_method
                )
                models[model_name] = ARIMAModel(model_config)
                
            elif model_name == 'prophet' and PROPHET_AVAILABLE:
                model_config = ModelConfig(
                    model_type=ModelType.PROPHET,
                    prediction_horizon=self.config.prediction_horizon,
                    lookback_window=self.config.lookback_window,
                    features=self.config.features,
                    scaling_method=self.config.scaling_method
                )
                models[model_name] = ProphetModel(model_config)
        
        return models
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train all base models and calculate weights"""
        logger.info(f"Training ensemble with {len(self.base_models)} base models")
        
        # Split data for validation
        val_split = self.hyperparams['validation_split']
        split_idx = int((1 - val_split) * len(X))
        
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Train each base model
        for name, model in self.base_models.items():
            try:
                logger.info(f"Training {name} model...")
                performance = model.train(pd.DataFrame(X_train))  # Simplified for ensemble
                
                # Evaluate on validation set
                val_predictions = model._predict_model(X_val)
                
                # Calculate validation performance
                if len(y_val.shape) > 1:
                    y_val_flat = y_val.flatten()
                else:
                    y_val_flat = y_val
                
                if len(val_predictions.shape) > 1:
                    val_predictions_flat = val_predictions.flatten()
                else:
                    val_predictions_flat = val_predictions
                
                # Ensure same length
                min_len = min(len(y_val_flat), len(val_predictions_flat))
                y_val_flat = y_val_flat[:min_len]
                val_predictions_flat = val_predictions_flat[:min_len]
                
                val_rmse = np.sqrt(mean_squared_error(y_val_flat, val_predictions_flat))
                val_mae = mean_absolute_error(y_val_flat, val_predictions_flat)
                
                self.model_performances[name] = {
                    'rmse': val_rmse,
                    'mae': val_mae,
                    'training_performance': performance
                }
                
                logger.info(f"{name} validation RMSE: {val_rmse:.4f}")
                
            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")
                # Remove failed model
                if name in self.base_models:
                    del self.base_models[name]
        
        # Calculate model weights
        self._calculate_weights()
    
    def _calculate_weights(self) -> None:
        """Calculate weights for ensemble models"""
        if not self.model_performances:
            # Equal weights if no performance data
            n_models = len(self.base_models)
            self.model_weights = {name: 1.0 / n_models for name in self.base_models.keys()}
            return
        
        weighting_method = self.hyperparams['weighting_method']
        metric = self.hyperparams['performance_metric']
        min_weight = self.hyperparams['min_weight']
        
        if weighting_method == 'equal':
            # Equal weights
            n_models = len(self.base_models)
            self.model_weights = {name: 1.0 / n_models for name in self.base_models.keys()}
            
        elif weighting_method == 'performance':
            # Inverse performance weighting (lower error = higher weight)
            performances = [self.model_performances[name][metric] for name in self.base_models.keys()]
            
            # Convert to weights (inverse of performance)
            inverse_perfs = [1.0 / (perf + 1e-8) for perf in performances]
            total_inverse = sum(inverse_perfs)
            
            weights = [inv_perf / total_inverse for inv_perf in inverse_perfs]
            
            # Apply minimum weight constraint
            weights = [max(w, min_weight) for w in weights]
            
            # Renormalize
            total_weight = sum(weights)
            weights = [w / total_weight for w in weights]
            
            self.model_weights = {
                name: weight 
                for name, weight in zip(self.base_models.keys(), weights)
            }
        
        logger.info(f"Model weights: {self.model_weights}")
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make ensemble predictions"""
        if not self.base_models:
            raise ValueError("No trained models available for ensemble prediction")
        
        predictions = []
        weights = []
        
        for name, model in self.base_models.items():
            try:
                pred = model._predict_model(X)
                predictions.append(pred)
                weights.append(self.model_weights.get(name, 0.0))
            except Exception as e:
                logger.warning(f"Prediction failed for {name}: {e}")
        
        if not predictions:
            raise ValueError("All ensemble models failed to make predictions")
        
        # Convert predictions to numpy arrays and ensure same shape
        predictions = [np.array(pred).flatten() for pred in predictions]
        max_len = max(len(pred) for pred in predictions)
        
        # Pad predictions to same length if needed
        padded_predictions = []
        for pred in predictions:
            if len(pred) < max_len:
                # Repeat last value to match length
                padded = np.concatenate([pred, np.full(max_len - len(pred), pred[-1])])
            else:
                padded = pred[:max_len]
            padded_predictions.append(padded)
        
        # Weighted average
        ensemble_prediction = np.zeros(max_len)
        total_weight = sum(weights)
        
        for pred, weight in zip(padded_predictions, weights):
            ensemble_prediction += pred * (weight / total_weight)
        
        return ensemble_prediction
    
    def _get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get aggregated feature importance from ensemble models"""
        if not self.base_models:
            return None
        
        all_importances = {}
        total_weight = 0.0
        
        for name, model in self.base_models.items():
            importance = model._get_feature_importance()
            if importance is not None:
                weight = self.model_weights.get(name, 0.0)
                
                for feature, imp in importance.items():
                    if feature not in all_importances:
                        all_importances[feature] = 0.0
                    all_importances[feature] += imp * weight
                
                total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            for feature in all_importances:
                all_importances[feature] /= total_weight
        
        return all_importances if all_importances else None
    
    def _calculate_model_confidence(self) -> float:
        """Calculate ensemble confidence as weighted average of base model confidences"""
        if not self.base_models:
            return 0.5
        
        total_confidence = 0.0
        total_weight = 0.0
        
        for name, model in self.base_models.items():
            confidence = model._calculate_model_confidence()
            weight = self.model_weights.get(name, 0.0)
            
            total_confidence += confidence * weight
            total_weight += weight
        
        return total_confidence / total_weight if total_weight > 0 else 0.5
    
    def get_model_performances(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all base models"""
        return self.model_performances.copy()
    
    def get_model_weights(self) -> Dict[str, float]:
        """Get current model weights"""
        return self.model_weights.copy()


# Utility functions for model selection and comparison
def compare_models(
    data: pd.DataFrame,
    models: List[str] = None,
    prediction_horizon: int = 7,
    test_size: float = 0.2
) -> Dict[str, Dict[str, float]]:
    """
    Compare multiple forecasting models on the same dataset
    
    Args:
        data: Historical market data
        models: List of model names to compare
        prediction_horizon: Prediction horizon in days
        test_size: Fraction of data to use for testing
        
    Returns:
        Dictionary with model performance comparisons
    """
    if models is None:
        models = ['arima', 'random_forest', 'xgboost']
        if PROPHET_AVAILABLE:
            models.append('prophet')
    
    # Split data
    split_idx = int((1 - test_size) * len(data))
    train_data = data[:split_idx]
    test_data = data[split_idx:]
    
    results = {}
    
    for model_name in models:
        try:
            logger.info(f"Evaluating {model_name} model...")
            
            # Create model config
            from .forecasting_models import PredictionHorizon
            horizon_map = {1: PredictionHorizon.ONE_DAY, 7: PredictionHorizon.SEVEN_DAYS, 30: PredictionHorizon.THIRTY_DAYS}
            horizon = horizon_map.get(prediction_horizon, PredictionHorizon.SEVEN_DAYS)
            
            config = ModelConfig(
                model_type=ModelType[model_name.upper()],
                prediction_horizon=horizon,
                lookback_window=60,
                features=data.columns.tolist()
            )
            
            # Create and train model
            if model_name == 'arima':
                model = ARIMAModel(config)
            elif model_name == 'random_forest':
                model = RandomForestModel(config)
            elif model_name == 'xgboost':
                model = XGBoostModel(config)
            elif model_name == 'prophet':
                model = ProphetModel(config)
            else:
                continue
            
            # Train model
            performance = model.train(train_data)
            
            # Make predictions on test data
            prediction_result = model.predict(test_data, ticker="TEST")
            
            results[model_name] = {
                'training_performance': performance.to_dict(),
                'model_confidence': prediction_result.model_confidence,
                'prediction_length': len(prediction_result.predictions)
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate {model_name}: {e}")
            results[model_name] = {'error': str(e)}
    
    return results


def select_best_model(
    data: pd.DataFrame,
    models: List[str] = None,
    metric: str = 'rmse',
    prediction_horizon: int = 7
) -> Tuple[str, BaseForecastingModel]:
    """
    Select the best performing model for the given data
    
    Args:
        data: Historical market data
        models: List of model names to evaluate
        metric: Performance metric to use for selection
        prediction_horizon: Prediction horizon in days
        
    Returns:
        Tuple of (best_model_name, trained_model)
    """
    comparison_results = compare_models(data, models, prediction_horizon)
    
    best_model_name = None
    best_score = float('inf') if metric in ['rmse', 'mae', 'mape'] else float('-inf')
    
    for model_name, results in comparison_results.items():
        if 'error' in results:
            continue
        
        training_perf = results.get('training_performance', {})
        score = training_perf.get(metric)
        
        if score is None:
            continue
        
        if metric in ['rmse', 'mae', 'mape']:
            # Lower is better
            if score < best_score:
                best_score = score
                best_model_name = model_name
        else:
            # Higher is better
            if score > best_score:
                best_score = score
                best_model_name = model_name
    
    if best_model_name is None:
        raise ValueError("No suitable model found")
    
    # Train the best model on full data
    logger.info(f"Selected {best_model_name} as best model with {metric}: {best_score:.4f}")
    
    # Create and train the best model
    from .forecasting_models import PredictionHorizon
    horizon_map = {1: PredictionHorizon.ONE_DAY, 7: PredictionHorizon.SEVEN_DAYS, 30: PredictionHorizon.THIRTY_DAYS}
    horizon = horizon_map.get(prediction_horizon, PredictionHorizon.SEVEN_DAYS)
    
    config = ModelConfig(
        model_type=ModelType[best_model_name.upper()],
        prediction_horizon=horizon,
        lookback_window=60,
        features=data.columns.tolist()
    )
    
    if best_model_name == 'arima':
        best_model = ARIMAModel(config)
    elif best_model_name == 'random_forest':
        best_model = RandomForestModel(config)
    elif best_model_name == 'xgboost':
        best_model = XGBoostModel(config)
    elif best_model_name == 'prophet':
        best_model = ProphetModel(config)
    else:
        raise ValueError(f"Unknown model: {best_model_name}")
    
    best_model.train(data)
    
    return best_model_name, best_model


def create_ensemble_from_best_models(
    data: pd.DataFrame,
    n_models: int = 3,
    prediction_horizon: int = 7
) -> EnsembleModel:
    """
    Create an ensemble from the best performing individual models
    
    Args:
        data: Historical market data
        n_models: Number of top models to include in ensemble
        prediction_horizon: Prediction horizon in days
        
    Returns:
        Trained ensemble model
    """
    # Compare all available models
    all_models = ['arima', 'random_forest', 'xgboost']
    if PROPHET_AVAILABLE:
        all_models.append('prophet')
    
    comparison_results = compare_models(data, all_models, prediction_horizon)
    
    # Sort models by RMSE (ascending)
    valid_models = [
        (name, results) for name, results in comparison_results.items()
        if 'error' not in results and 'training_performance' in results
    ]
    
    valid_models.sort(
        key=lambda x: x[1]['training_performance'].get('rmse', float('inf'))
    )
    
    # Select top n_models
    best_models = [name for name, _ in valid_models[:n_models]]
    
    logger.info(f"Creating ensemble with models: {best_models}")
    
    # Create ensemble config
    from .forecasting_models import PredictionHorizon
    horizon_map = {1: PredictionHorizon.ONE_DAY, 7: PredictionHorizon.SEVEN_DAYS, 30: PredictionHorizon.THIRTY_DAYS}
    horizon = horizon_map.get(prediction_horizon, PredictionHorizon.SEVEN_DAYS)
    
    config = ModelConfig(
        model_type=ModelType.ENSEMBLE,
        prediction_horizon=horizon,
        lookback_window=60,
        features=data.columns.tolist(),
        hyperparameters={'models': best_models}
    )
    
    # Create and train ensemble
    ensemble = EnsembleModel(config)
    ensemble.train(data)
    
    return ensemble


# Export main classes and functions
__all__ = [
    "ARIMAModel",
    "RandomForestModel",
    "XGBoostModel",
    "ProphetModel",
    "EnsembleModel",
    "compare_models",
    "select_best_model",
    "create_ensemble_from_best_models"
]
        