"""
LSTM Neural Network Predictor for Stock Price Forecasting
Advanced deep learning implementation using PyTorch for time series prediction

This module implements LSTM (Long Short-Term Memory) neural networks for stock price
prediction with support for univariate and multivariate time series, configurable
architectures, and advanced features like attention mechanisms and dropout.

Author: Vincent S. Pereira
Version: 1.0.0
"""

import logging
import warnings
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler

from .forecasting_models import BaseForecastingModel, ModelConfig, ModelType, PredictionResult

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure logging
logger = logging.getLogger(__name__)

# Set device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
logger.info(f"Using device: {device}")


class LSTMNetwork(nn.Module):
    """
    LSTM Neural Network Architecture
    Supports multiple LSTM layers, dropout, and attention mechanisms
    """
    
    def __init__(
        self,
        input_size: int,
        hidden_size: int = 128,
        num_layers: int = 2,
        output_size: int = 1,
        dropout: float = 0.2,
        bidirectional: bool = False,
        use_attention: bool = False
    ):
        super(LSTMNetwork, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.output_size = output_size
        self.bidirectional = bidirectional
        self.use_attention = use_attention
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional,
            batch_first=True
        )
        
        # Attention mechanism (optional)
        if use_attention:
            lstm_output_size = hidden_size * 2 if bidirectional else hidden_size
            self.attention = nn.MultiheadAttention(
                embed_dim=lstm_output_size,
                num_heads=8,
                dropout=dropout,
                batch_first=True
            )
            self.attention_norm = nn.LayerNorm(lstm_output_size)
        
        # Output layers
        lstm_output_size = hidden_size * 2 if bidirectional else hidden_size
        self.dropout = nn.Dropout(dropout)
        self.fc1 = nn.Linear(lstm_output_size, hidden_size // 2)
        self.fc2 = nn.Linear(hidden_size // 2, output_size)
        self.relu = nn.ReLU()
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize network weights"""
        for name, param in self.named_parameters():
            if 'weight_ih' in name:
                nn.init.xavier_uniform_(param.data)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param.data)
            elif 'bias' in name:
                param.data.fill_(0)
    
    def forward(self, x):
        """Forward pass through the network"""
        batch_size = x.size(0)
        
        # LSTM forward pass
        lstm_out, (hidden, cell) = self.lstm(x)
        
        # Apply attention if enabled
        if self.use_attention:
            attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
            lstm_out = self.attention_norm(lstm_out + attn_out)
        
        # Use the last output for prediction
        last_output = lstm_out[:, -1, :]
        
        # Fully connected layers
        out = self.dropout(last_output)
        out = self.relu(self.fc1(out))
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out
    
    def init_hidden(self, batch_size):
        """Initialize hidden states"""
        num_directions = 2 if self.bidirectional else 1
        hidden = torch.zeros(self.num_layers * num_directions, batch_size, self.hidden_size).to(device)
        cell = torch.zeros(self.num_layers * num_directions, batch_size, self.hidden_size).to(device)
        return hidden, cell


class LSTMPredictor(BaseForecastingModel):
    """
    LSTM-based stock price predictor
    Implements the BaseForecastingModel interface for LSTM neural networks
    """
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        
        # LSTM-specific hyperparameters
        self.hyperparams = {
            'hidden_size': 128,
            'num_layers': 2,
            'dropout': 0.2,
            'learning_rate': 0.001,
            'batch_size': 32,
            'epochs': 100,
            'patience': 10,
            'bidirectional': False,
            'use_attention': False,
            'weight_decay': 1e-5,
            'gradient_clip': 1.0
        }
        
        # Update with config hyperparameters
        self.hyperparams.update(config.hyperparameters)
        
        # Model components
        self.model = None
        self.optimizer = None
        self.criterion = None
        self.scheduler = None
        
        # Training history
        self.training_history = {
            'train_loss': [],
            'val_loss': [],
            'epochs': 0
        }
    
    def _build_model(self) -> LSTMNetwork:
        """Build LSTM neural network"""
        input_size = len(self.config.features)
        output_size = self.config.prediction_horizon.value
        
        model = LSTMNetwork(
            input_size=input_size,
            hidden_size=self.hyperparams['hidden_size'],
            num_layers=self.hyperparams['num_layers'],
            output_size=output_size,
            dropout=self.hyperparams['dropout'],
            bidirectional=self.hyperparams['bidirectional'],
            use_attention=self.hyperparams['use_attention']
        ).to(device)
        
        # Initialize optimizer and loss function
        self.optimizer = optim.Adam(
            model.parameters(),
            lr=self.hyperparams['learning_rate'],
            weight_decay=self.hyperparams['weight_decay']
        )
        
        self.criterion = nn.MSELoss()
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=self.hyperparams['patience'] // 2,
            verbose=True
        )
        
        logger.info(f"Built LSTM model with {sum(p.numel() for p in model.parameters())} parameters")
        return model
    
    def _train_model(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train the LSTM model"""
        # Split data into train/validation
        split_idx = int(0.8 * len(X))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Convert to PyTorch tensors
        X_train_tensor = torch.FloatTensor(X_train).to(device)
        y_train_tensor = torch.FloatTensor(y_train).to(device)
        X_val_tensor = torch.FloatTensor(X_val).to(device)
        y_val_tensor = torch.FloatTensor(y_val).to(device)
        
        # Reshape y if needed
        if len(y_train_tensor.shape) == 1:
            y_train_tensor = y_train_tensor.unsqueeze(1)
        if len(y_val_tensor.shape) == 1:
            y_val_tensor = y_val_tensor.unsqueeze(1)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.hyperparams['batch_size'],
            shuffle=True,
            drop_last=True
        )
        
        val_dataset = TensorDataset(X_val_tensor, y_val_tensor)
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.hyperparams['batch_size'],
            shuffle=False,
            drop_last=False
        )
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        
        self.model.train()
        
        for epoch in range(self.hyperparams['epochs']):
            # Training phase
            train_loss = self._train_epoch(train_loader)
            
            # Validation phase
            val_loss = self._validate_epoch(val_loader)
            
            # Update learning rate
            self.scheduler.step(val_loss)
            
            # Store history
            self.training_history['train_loss'].append(train_loss)
            self.training_history['val_loss'].append(val_loss)
            self.training_history['epochs'] = epoch + 1
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model state
                self.best_model_state = self.model.state_dict().copy()
            else:
                patience_counter += 1
            
            if patience_counter >= self.hyperparams['patience']:
                logger.info(f"Early stopping at epoch {epoch + 1}")
                break
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch + 1}/{self.hyperparams['epochs']}, "
                          f"Train Loss: {train_loss:.6f}, Val Loss: {val_loss:.6f}")
        
        # Load best model state
        if hasattr(self, 'best_model_state'):
            self.model.load_state_dict(self.best_model_state)
        
        logger.info(f"Training completed. Best validation loss: {best_val_loss:.6f}")
    
    def _train_epoch(self, train_loader: DataLoader) -> float:
        """Train for one epoch"""
        self.model.train()
        total_loss = 0.0
        
        for batch_X, batch_y in train_loader:
            self.optimizer.zero_grad()
            
            # Forward pass
            outputs = self.model(batch_X)
            loss = self.criterion(outputs, batch_y)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(
                self.model.parameters(),
                self.hyperparams['gradient_clip']
            )
            
            self.optimizer.step()
            total_loss += loss.item()
        
        return total_loss / len(train_loader)
    
    def _validate_epoch(self, val_loader: DataLoader) -> float:
        """Validate for one epoch"""
        self.model.eval()
        total_loss = 0.0
        
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = self.model(batch_X)
                loss = self.criterion(outputs, batch_y)
                total_loss += loss.item()
        
        return total_loss / len(val_loader)
    
    def _predict_model(self, X: np.ndarray) -> np.ndarray:
        """Make predictions with the LSTM model"""
        self.model.eval()
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(device)
            predictions = self.model(X_tensor)
            predictions = predictions.cpu().numpy()
        
        return predictions
    
    def _calculate_confidence_intervals(
        self,
        X: np.ndarray,
        predictions: np.ndarray
    ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Calculate confidence intervals using Monte Carlo dropout"""
        if not hasattr(self.model, 'dropout'):
            return super()._calculate_confidence_intervals(X, predictions)
        
        # Enable dropout for uncertainty estimation
        self.model.train()
        
        mc_predictions = []
        n_samples = 100
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X).to(device)
            
            for _ in range(n_samples):
                pred = self.model(X_tensor).cpu().numpy()
                mc_predictions.append(pred)
        
        # Reset to eval mode
        self.model.eval()
        
        mc_predictions = np.array(mc_predictions)
        
        # Calculate confidence intervals
        lower = np.percentile(mc_predictions, 2.5, axis=0)
        upper = np.percentile(mc_predictions, 97.5, axis=0)
        
        return (lower.flatten(), upper.flatten())
    
    def _get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance using gradient-based attribution"""
        if not self.feature_columns:
            return None
        
        # Simple gradient-based feature importance
        self.model.eval()
        
        # Create a sample input
        sample_input = torch.randn(1, self.config.lookback_window, len(self.feature_columns)).to(device)
        sample_input.requires_grad_(True)
        
        # Forward pass
        output = self.model(sample_input)
        
        # Backward pass to get gradients
        output.backward(torch.ones_like(output))
        
        # Calculate feature importance as mean absolute gradient
        gradients = sample_input.grad.abs().mean(dim=(0, 1)).cpu().numpy()
        
        # Normalize to sum to 1
        gradients = gradients / gradients.sum()
        
        importance_dict = {
            feature: float(importance)
            for feature, importance in zip(self.feature_columns, gradients)
        }
        
        return importance_dict
    
    def _calculate_model_confidence(self) -> float:
        """Calculate model confidence based on training history"""
        if not self.training_history['val_loss']:
            return 0.5
        
        # Use validation loss trend and final loss to estimate confidence
        val_losses = self.training_history['val_loss']
        
        # Calculate confidence based on:
        # 1. Final validation loss (lower is better)
        # 2. Loss stability (less variation is better)
        # 3. Training convergence
        
        final_loss = val_losses[-1]
        loss_std = np.std(val_losses[-10:]) if len(val_losses) >= 10 else np.std(val_losses)
        
        # Normalize confidence score (0-1)
        # This is a heuristic - can be improved with domain knowledge
        base_confidence = 1.0 / (1.0 + final_loss)
        stability_factor = 1.0 / (1.0 + loss_std)
        
        confidence = (base_confidence + stability_factor) / 2.0
        return min(max(confidence, 0.0), 1.0)
    
    def predict_with_uncertainty(
        self,
        data: pd.DataFrame,
        ticker: str,
        n_samples: int = 100
    ) -> PredictionResult:
        """
        Make predictions with uncertainty quantification using Monte Carlo dropout
        
        Args:
            data: Input data for prediction
            ticker: Stock ticker symbol
            n_samples: Number of Monte Carlo samples for uncertainty estimation
            
        Returns:
            Prediction result with uncertainty estimates
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Preprocess data
        X, _ = self.preprocess_data(data)
        
        if len(X) == 0:
            raise ValueError("No prediction sequences created from input data")
        
        # Use the last sequence for prediction
        X_pred = X[-1:]
        
        # Enable dropout for uncertainty estimation
        self.model.train()
        
        predictions_list = []
        
        with torch.no_grad():
            X_tensor = torch.FloatTensor(X_pred).to(device)
            
            for _ in range(n_samples):
                pred = self.model(X_tensor).cpu().numpy()
                predictions_list.append(pred.flatten())
        
        # Reset to eval mode
        self.model.eval()
        
        predictions_array = np.array(predictions_list)
        
        # Calculate statistics
        mean_predictions = np.mean(predictions_array, axis=0)
        std_predictions = np.std(predictions_array, axis=0)
        
        # Confidence intervals
        lower_ci = np.percentile(predictions_array, 2.5, axis=0)
        upper_ci = np.percentile(predictions_array, 97.5, axis=0)
        
        # Generate prediction dates
        last_date = data.index[-1] if hasattr(data.index, 'date') else pd.Timestamp.now()
        prediction_dates = [
            last_date + pd.Timedelta(days=i+1)
            for i in range(self.config.prediction_horizon.value)
        ]
        
        # Calculate model confidence based on prediction uncertainty
        uncertainty_confidence = 1.0 / (1.0 + np.mean(std_predictions))
        training_confidence = self._calculate_model_confidence()
        combined_confidence = (uncertainty_confidence + training_confidence) / 2.0
        
        return PredictionResult(
            ticker=ticker,
            model_type=self.config.model_type,
            prediction_horizon=self.config.prediction_horizon,
            predictions=mean_predictions,
            confidence_intervals=(lower_ci, upper_ci),
            prediction_dates=prediction_dates,
            model_confidence=combined_confidence,
            feature_importance=self._get_feature_importance(),
            metadata={
                "lookback_window": self.config.lookback_window,
                "features_used": self.feature_columns,
                "scaling_method": self.config.scaling_method,
                "prediction_std": std_predictions.tolist(),
                "n_mc_samples": n_samples,
                "training_epochs": self.training_history['epochs'],
                "final_train_loss": self.training_history['train_loss'][-1] if self.training_history['train_loss'] else None,
                "final_val_loss": self.training_history['val_loss'][-1] if self.training_history['val_loss'] else None
            }
        )
    
    def get_training_history(self) -> Dict[str, Any]:
        """Get training history and metrics"""
        return {
            "training_history": self.training_history,
            "hyperparameters": self.hyperparams,
            "model_architecture": {
                "input_size": len(self.config.features),
                "hidden_size": self.hyperparams['hidden_size'],
                "num_layers": self.hyperparams['num_layers'],
                "output_size": self.config.prediction_horizon.value,
                "bidirectional": self.hyperparams['bidirectional'],
                "use_attention": self.hyperparams['use_attention']
            }
        }
    
    def plot_training_history(self) -> Optional[Any]:
        """Plot training history (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt
            
            if not self.training_history['train_loss']:
                logger.warning("No training history available")
                return None
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            epochs = range(1, len(self.training_history['train_loss']) + 1)
            ax.plot(epochs, self.training_history['train_loss'], 'b-', label='Training Loss')
            ax.plot(epochs, self.training_history['val_loss'], 'r-', label='Validation Loss')
            
            ax.set_xlabel('Epoch')
            ax.set_ylabel('Loss')
            ax.set_title('LSTM Training History')
            ax.legend()
            ax.grid(True)
            
            return fig
            
        except ImportError:
            logger.warning("Matplotlib not available for plotting")
            return None


# Utility functions for LSTM-specific operations
def create_lstm_config(
    prediction_horizon: int = 7,
    lookback_window: int = 60,
    features: Optional[List[str]] = None,
    **hyperparams
) -> ModelConfig:
    """
    Create LSTM model configuration
    
    Args:
        prediction_horizon: Number of days to predict
        lookback_window: Number of historical days to use
        features: List of features to use
        **hyperparams: Additional hyperparameters
        
    Returns:
        ModelConfig for LSTM
    """
    from .forecasting_models import PredictionHorizon
    
    # Map prediction horizon to enum
    horizon_map = {1: PredictionHorizon.ONE_DAY, 7: PredictionHorizon.SEVEN_DAYS, 30: PredictionHorizon.THIRTY_DAYS}
    horizon = horizon_map.get(prediction_horizon, PredictionHorizon.SEVEN_DAYS)
    
    return ModelConfig(
        model_type=ModelType.LSTM,
        prediction_horizon=horizon,
        lookback_window=lookback_window,
        features=features or [],
        hyperparameters=hyperparams,
        scaling_method="standard"
    )


def optimize_lstm_hyperparameters(
    data: pd.DataFrame,
    n_trials: int = 50,
    prediction_horizon: int = 7
) -> Dict[str, Any]:
    """
    Optimize LSTM hyperparameters using Optuna
    
    Args:
        data: Training data
        n_trials: Number of optimization trials
        prediction_horizon: Prediction horizon in days
        
    Returns:
        Best hyperparameters
    """
    try:
        import optuna
        
        def objective(trial):
            # Suggest hyperparameters
            hyperparams = {
                'hidden_size': trial.suggest_categorical('hidden_size', [64, 128, 256]),
                'num_layers': trial.suggest_int('num_layers', 1, 3),
                'dropout': trial.suggest_float('dropout', 0.1, 0.5),
                'learning_rate': trial.suggest_loguniform('learning_rate', 1e-4, 1e-2),
                'batch_size': trial.suggest_categorical('batch_size', [16, 32, 64]),
                'epochs': 50,  # Reduced for optimization
                'patience': 10
            }
            
            # Create model config
            config = create_lstm_config(
                prediction_horizon=prediction_horizon,
                **hyperparams
            )
            
            # Train model
            model = LSTMPredictor(config)
            
            try:
                performance = model.train(data)
                return performance.rmse
            except Exception as e:
                logger.warning(f"Trial failed: {e}")
                return float('inf')
        
        # Run optimization
        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"Best hyperparameters: {study.best_params}")
        return study.best_params
        
    except ImportError:
        logger.warning("Optuna not available for hyperparameter optimization")
        return {}


# Export main classes and functions
__all__ = [
    "LSTMNetwork",
    "LSTMPredictor", 
    "create_lstm_config",
    "optimize_lstm_hyperparameters"
]