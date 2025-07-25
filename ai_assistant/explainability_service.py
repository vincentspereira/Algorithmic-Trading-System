"""
Explainability Service for AI Assistant - Phase 3
Model-agnostic explanations using SHAP (SHapley Additive exPlanations)

This module provides comprehensive explainability capabilities including:
1. SHAP explanations for forecasting models and backtesting decisions
2. Feature importance analysis with visualization
3. Decision path analysis and counterfactual explanations
4. Model-agnostic explanations for any prediction model
5. Integration with forecasting models and NLP processors

The service provides transparency in AI decision-making and helps users
understand why specific predictions or recommendations were made.
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import pickle
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio

# SHAP imports
import shap
from shap import Explainer, TreeExplainer, LinearExplainer, KernelExplainer
from shap import Explanation, waterfall_plot, summary_plot, force_plot

# ML model imports for compatibility
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LinearRegression, LogisticRegression
import xgboost as xgb
import lightgbm as lgb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress SHAP warnings
warnings.filterwarnings('ignore', category=UserWarning, module='shap')


class ExplanationType(Enum):
    """Types of explanations supported"""
    FEATURE_IMPORTANCE = "feature_importance"
    DECISION_PATH = "decision_path"
    COUNTERFACTUAL = "counterfactual"
    WATERFALL = "waterfall"
    FORCE_PLOT = "force_plot"
    SUMMARY_PLOT = "summary_plot"
    PARTIAL_DEPENDENCE = "partial_dependence"


class ModelType(Enum):
    """Supported model types for explanation"""
    TREE_BASED = "tree_based"
    LINEAR = "linear"
    NEURAL_NETWORK = "neural_network"
    ENSEMBLE = "ensemble"
    BLACK_BOX = "black_box"


@dataclass
class ExplanationResult:
    """Base class for explanation results"""
    model_name: str
    explanation_type: ExplanationType
    feature_names: List[str]
    shap_values: np.ndarray
    base_value: Union[float, np.ndarray]
    prediction: Union[float, np.ndarray]
    confidence: float
    processing_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FeatureImportanceResult(ExplanationResult):
    """Feature importance explanation result"""
    importance_scores: Dict[str, float] = field(default_factory=dict)
    top_features: List[Tuple[str, float]] = field(default_factory=list)
    importance_ranking: List[str] = field(default_factory=list)


@dataclass
class CounterfactualResult(ExplanationResult):
    """Counterfactual explanation result"""
    original_prediction: float
    counterfactual_prediction: float
    feature_changes: Dict[str, Dict[str, float]] = field(default_factory=dict)
    change_impact: Dict[str, float] = field(default_factory=dict)
    scenario_description: str = ""


@dataclass
class DecisionPathResult(ExplanationResult):
    """Decision path explanation result"""
    decision_nodes: List[Dict[str, Any]] = field(default_factory=list)
    path_contribution: Dict[str, float] = field(default_factory=dict)
    decision_rules: List[str] = field(default_factory=list)


class ExplainabilityService:
    """
    Comprehensive explainability service using SHAP
    
    Features:
    - Model-agnostic explanations for any ML model
    - Multiple explanation types (feature importance, counterfactuals, etc.)
    - Integration with forecasting models and backtesting decisions
    - Visualization generation and export capabilities
    - Caching for improved performance
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the explainability service
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = self._load_config(config_path)
        self.explainers = {}
        self.cache = {}
        self.model_registry = {}
        
        # Set up plotting backend
        pio.renderers.default = "browser"
        plt.style.use('seaborn-v0_8')
        
        logger.info("Explainability Service initialized")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults"""
        default_config = {
            "explainers": {
                "kernel_explainer": {
                    "n_samples": 100,
                    "l1_reg": "auto"
                },
                "tree_explainer": {
                    "feature_perturbation": "tree_path_dependent",
                    "check_additivity": False
                },
                "linear_explainer": {
                    "feature_perturbation": "correlation_dependent"
                }
            },
            "visualization": {
                "max_display": 20,
                "plot_size": (12, 8),
                "color_scheme": "RdYlBu",
                "export_format": "html"
            },
            "cache": {
                "enabled": True,
                "max_size": 500,
                "ttl_hours": 12
            },
            "counterfactuals": {
                "max_iterations": 100,
                "tolerance": 0.01,
                "feature_ranges": {}
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config
    
    def register_model(
        self,
        model_name: str,
        model: Any,
        model_type: ModelType,
        feature_names: List[str],
        predict_function: Optional[Callable] = None
    ):
        """
        Register a model for explanation
        
        Args:
            model_name: Unique name for the model
            model: The trained model object
            model_type: Type of model for explainer selection
            feature_names: Names of input features
            predict_function: Custom prediction function (optional)
        """
        try:
            # Store model information
            self.model_registry[model_name] = {
                "model": model,
                "model_type": model_type,
                "feature_names": feature_names,
                "predict_function": predict_function or (lambda x: model.predict(x)),
                "registered_at": datetime.now()
            }
            
            # Create appropriate explainer
            explainer = self._create_explainer(model, model_type, feature_names)
            if explainer:
                self.explainers[model_name] = explainer
                logger.info(f"Model '{model_name}' registered successfully with {model_type.value} explainer")
            else:
                logger.warning(f"Failed to create explainer for model '{model_name}'")
                
        except Exception as e:
            logger.error(f"Error registering model '{model_name}': {e}")
            raise
    
    def _create_explainer(
        self,
        model: Any,
        model_type: ModelType,
        feature_names: List[str]
    ) -> Optional[Explainer]:
        """Create appropriate SHAP explainer based on model type"""
        try:
            if model_type == ModelType.TREE_BASED:
                # For tree-based models (RandomForest, XGBoost, LightGBM)
                if hasattr(model, 'estimators_') or isinstance(model, (xgb.XGBRegressor, xgb.XGBClassifier)):
                    return TreeExplainer(model, **self.config["explainers"]["tree_explainer"])
                
            elif model_type == ModelType.LINEAR:
                # For linear models
                if hasattr(model, 'coef_'):
                    return LinearExplainer(model, **self.config["explainers"]["linear_explainer"])
            
            elif model_type == ModelType.ENSEMBLE:
                # Try tree explainer first for ensemble models
                try:
                    return TreeExplainer(model, **self.config["explainers"]["tree_explainer"])
                except:
                    pass
            
            # Fallback to KernelExplainer for any model
            logger.info(f"Using KernelExplainer as fallback for {model_type.value}")
            
            # Create a simple background dataset (zeros)
            background = np.zeros((1, len(feature_names)))
            
            return KernelExplainer(
                model.predict if hasattr(model, 'predict') else model,
                background,
                **self.config["explainers"]["kernel_explainer"]
            )
            
        except Exception as e:
            logger.error(f"Error creating explainer: {e}")
            return None
    
    def explain_prediction(
        self,
        model_name: str,
        input_data: Union[np.ndarray, pd.DataFrame, Dict[str, Any]],
        explanation_types: List[ExplanationType] = None,
        include_visualization: bool = True
    ) -> Dict[ExplanationType, ExplanationResult]:
        """
        Generate explanations for a model prediction
        
        Args:
            model_name: Name of registered model
            input_data: Input data for prediction
            explanation_types: Types of explanations to generate
            include_visualization: Whether to generate visualizations
            
        Returns:
            Dictionary mapping explanation types to results
        """
        start_time = datetime.now()
        
        if explanation_types is None:
            explanation_types = [
                ExplanationType.FEATURE_IMPORTANCE,
                ExplanationType.WATERFALL,
                ExplanationType.DECISION_PATH
            ]
        
        try:
            # Validate model registration
            if model_name not in self.model_registry:
                raise ValueError(f"Model '{model_name}' not registered")
            
            if model_name not in self.explainers:
                raise ValueError(f"No explainer available for model '{model_name}'")
            
            model_info = self.model_registry[model_name]
            explainer = self.explainers[model_name]
            
            # Prepare input data
            X = self._prepare_input_data(input_data, model_info["feature_names"])
            
            # Make prediction
            prediction = model_info["predict_function"](X)
            if hasattr(prediction, 'shape') and len(prediction.shape) > 0:
                prediction = prediction[0] if len(prediction) == 1 else prediction
            
            # Generate SHAP values
            shap_values = explainer.shap_values(X)
            if isinstance(shap_values, list):
                shap_values = shap_values[0]  # For multi-class, take first class
            
            # Get base value
            base_value = explainer.expected_value
            if isinstance(base_value, np.ndarray):
                base_value = base_value[0]
            
            # Generate explanations
            results = {}
            
            for exp_type in explanation_types:
                try:
                    if exp_type == ExplanationType.FEATURE_IMPORTANCE:
                        results[exp_type] = self._generate_feature_importance(
                            model_name, model_info["feature_names"], shap_values, 
                            base_value, prediction, X
                        )
                    
                    elif exp_type == ExplanationType.WATERFALL:
                        results[exp_type] = self._generate_waterfall_explanation(
                            model_name, model_info["feature_names"], shap_values,
                            base_value, prediction, X
                        )
                    
                    elif exp_type == ExplanationType.DECISION_PATH:
                        results[exp_type] = self._generate_decision_path(
                            model_name, model_info, shap_values, base_value, prediction, X
                        )
                    
                    elif exp_type == ExplanationType.COUNTERFACTUAL:
                        results[exp_type] = self._generate_counterfactual(
                            model_name, model_info, X, prediction
                        )
                    
                except Exception as e:
                    logger.error(f"Error generating {exp_type.value} explanation: {e}")
                    continue
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Add processing metadata to all results
            for result in results.values():
                result.processing_time = processing_time
                result.metadata.update({
                    "input_shape": X.shape,
                    "model_type": model_info["model_type"].value,
                    "explanation_count": len(results)
                })
            
            logger.info(f"Generated {len(results)} explanations for model '{model_name}' in {processing_time:.2f}s")
            return results
            
        except Exception as e:
            logger.error(f"Error explaining prediction for model '{model_name}': {e}")
            raise
    
    def _prepare_input_data(
        self,
        input_data: Union[np.ndarray, pd.DataFrame, Dict[str, Any]],
        feature_names: List[str]
    ) -> np.ndarray:
        """Prepare input data for explanation"""
        if isinstance(input_data, dict):
            # Convert dictionary to array using feature names order
            X = np.array([[input_data.get(name, 0.0) for name in feature_names]])
        elif isinstance(input_data, pd.DataFrame):
            # Ensure correct column order
            X = input_data[feature_names].values
        elif isinstance(input_data, np.ndarray):
            X = input_data.reshape(1, -1) if input_data.ndim == 1 else input_data
        else:
            raise ValueError(f"Unsupported input data type: {type(input_data)}")
        
        return X
    
    def _generate_feature_importance(
        self,
        model_name: str,
        feature_names: List[str],
        shap_values: np.ndarray,
        base_value: float,
        prediction: float,
        input_data: np.ndarray
    ) -> FeatureImportanceResult:
        """Generate feature importance explanation"""
        
        # Calculate importance scores (absolute SHAP values)
        if shap_values.ndim > 1:
            importance_values = np.abs(shap_values[0])
        else:
            importance_values = np.abs(shap_values)
        
        # Create importance dictionary
        importance_scores = {
            name: float(score) for name, score in zip(feature_names, importance_values)
        }
        
        # Sort features by importance
        top_features = sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)
        importance_ranking = [name for name, _ in top_features]
        
        return FeatureImportanceResult(
            model_name=model_name,
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            feature_names=feature_names,
            shap_values=shap_values,
            base_value=base_value,
            prediction=prediction,
            confidence=0.9,  # High confidence for feature importance
            processing_time=0.0,  # Will be set by caller
            importance_scores=importance_scores,
            top_features=top_features,
            importance_ranking=importance_ranking,
            metadata={
                "total_features": len(feature_names),
                "max_importance": max(importance_values),
                "mean_importance": np.mean(importance_values)
            }
        )
    
    def _generate_waterfall_explanation(
        self,
        model_name: str,
        feature_names: List[str],
        shap_values: np.ndarray,
        base_value: float,
        prediction: float,
        input_data: np.ndarray
    ) -> ExplanationResult:
        """Generate waterfall explanation"""
        
        if shap_values.ndim > 1:
            shap_vals = shap_values[0]
        else:
            shap_vals = shap_values
        
        return ExplanationResult(
            model_name=model_name,
            explanation_type=ExplanationType.WATERFALL,
            feature_names=feature_names,
            shap_values=shap_values,
            base_value=base_value,
            prediction=prediction,
            confidence=0.85,
            processing_time=0.0,
            metadata={
                "waterfall_data": {
                    "base_value": float(base_value),
                    "contributions": {
                        name: float(val) for name, val in zip(feature_names, shap_vals)
                    },
                    "final_prediction": float(prediction)
                }
            }
        )
    
    def _generate_decision_path(
        self,
        model_name: str,
        model_info: Dict[str, Any],
        shap_values: np.ndarray,
        base_value: float,
        prediction: float,
        input_data: np.ndarray
    ) -> DecisionPathResult:
        """Generate decision path explanation"""
        
        feature_names = model_info["feature_names"]
        
        if shap_values.ndim > 1:
            shap_vals = shap_values[0]
        else:
            shap_vals = shap_values
        
        # Create decision nodes based on SHAP contributions
        decision_nodes = []
        path_contribution = {}
        decision_rules = []
        
        # Sort features by absolute contribution
        feature_contributions = list(zip(feature_names, shap_vals, input_data[0]))
        feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        
        cumulative_value = base_value
        
        for i, (feature, contribution, value) in enumerate(feature_contributions[:10]):  # Top 10
            cumulative_value += contribution
            
            decision_nodes.append({
                "step": i + 1,
                "feature": feature,
                "value": float(value),
                "contribution": float(contribution),
                "cumulative_prediction": float(cumulative_value),
                "importance_rank": i + 1
            })
            
            path_contribution[feature] = float(contribution)
            
            # Create human-readable decision rule
            direction = "increases" if contribution > 0 else "decreases"
            decision_rules.append(
                f"Step {i+1}: {feature} = {value:.3f} {direction} prediction by {abs(contribution):.3f}"
            )
        
        return DecisionPathResult(
            model_name=model_name,
            explanation_type=ExplanationType.DECISION_PATH,
            feature_names=feature_names,
            shap_values=shap_values,
            base_value=base_value,
            prediction=prediction,
            confidence=0.8,
            processing_time=0.0,
            decision_nodes=decision_nodes,
            path_contribution=path_contribution,
            decision_rules=decision_rules,
            metadata={
                "total_steps": len(decision_nodes),
                "base_prediction": float(base_value),
                "final_prediction": float(prediction)
            }
        )
    
    def _generate_counterfactual(
        self,
        model_name: str,
        model_info: Dict[str, Any],
        input_data: np.ndarray,
        original_prediction: float
    ) -> CounterfactualResult:
        """Generate counterfactual explanation"""
        
        feature_names = model_info["feature_names"]
        predict_function = model_info["predict_function"]
        
        # Simple counterfactual generation by perturbing features
        feature_changes = {}
        change_impact = {}
        
        original_input = input_data[0].copy()
        
        for i, feature_name in enumerate(feature_names):
            # Try small perturbations
            for perturbation in [0.1, -0.1, 0.5, -0.5]:
                modified_input = original_input.copy()
                modified_input[i] += perturbation
                
                try:
                    new_prediction = predict_function(modified_input.reshape(1, -1))
                    if hasattr(new_prediction, 'shape') and len(new_prediction.shape) > 0:
                        new_prediction = new_prediction[0]
                    
                    impact = abs(new_prediction - original_prediction)
                    
                    if feature_name not in change_impact or impact > change_impact[feature_name]:
                        feature_changes[feature_name] = {
                            "original_value": float(original_input[i]),
                            "modified_value": float(modified_input[i]),
                            "perturbation": float(perturbation)
                        }
                        change_impact[feature_name] = float(impact)
                        
                except Exception as e:
                    logger.warning(f"Error generating counterfactual for {feature_name}: {e}")
                    continue
        
        # Find the most impactful change
        if change_impact:
            most_impactful = max(change_impact.items(), key=lambda x: x[1])
            scenario_description = f"Changing {most_impactful[0]} would have the highest impact ({most_impactful[1]:.3f})"
        else:
            scenario_description = "No significant counterfactual scenarios found"
        
        # Create a hypothetical counterfactual prediction
        counterfactual_prediction = original_prediction
        if change_impact:
            # Use the most impactful change
            most_impactful_feature = most_impactful[0]
            feature_idx = feature_names.index(most_impactful_feature)
            modified_input = original_input.copy()
            modified_input[feature_idx] = feature_changes[most_impactful_feature]["modified_value"]
            
            try:
                counterfactual_prediction = predict_function(modified_input.reshape(1, -1))
                if hasattr(counterfactual_prediction, 'shape') and len(counterfactual_prediction.shape) > 0:
                    counterfactual_prediction = counterfactual_prediction[0]
            except:
                counterfactual_prediction = original_prediction
        
        return CounterfactualResult(
            model_name=model_name,
            explanation_type=ExplanationType.COUNTERFACTUAL,
            feature_names=feature_names,
            shap_values=np.zeros_like(original_input),  # Placeholder
            base_value=0.0,  # Not applicable for counterfactuals
            prediction=original_prediction,
            confidence=0.7,  # Lower confidence for counterfactuals
            processing_time=0.0,
            original_prediction=float(original_prediction),
            counterfactual_prediction=float(counterfactual_prediction),
            feature_changes=feature_changes,
            change_impact=change_impact,
            scenario_description=scenario_description,
            metadata={
                "features_analyzed": len(feature_names),
                "significant_changes": len([v for v in change_impact.values() if v > 0.01])
            }
        )
    
    def explain_forecasting_decision(
        self,
        model_name: str,
        historical_data: pd.DataFrame,
        prediction_result: Dict[str, Any],
        feature_columns: List[str]
    ) -> Dict[str, Any]:
        """
        Explain a forecasting model decision
        
        Args:
            model_name: Name of the forecasting model
            historical_data: Historical data used for prediction
            prediction_result: Result from forecasting model
            feature_columns: Names of feature columns
            
        Returns:
            Comprehensive explanation of the forecasting decision
        """
        try:
            # Extract recent data for explanation
            recent_data = historical_data.tail(1)[feature_columns]
            
            # Generate explanations
            explanations = self.explain_prediction(
                model_name=model_name,
                input_data=recent_data,
                explanation_types=[
                    ExplanationType.FEATURE_IMPORTANCE,
                    ExplanationType.DECISION_PATH,
                    ExplanationType.COUNTERFACTUAL
                ]
            )
            
            # Format for forecasting context
            forecasting_explanation = {
                "model_name": model_name,
                "prediction": prediction_result,
                "explanations": {},
                "summary": self._create_forecasting_summary(explanations, prediction_result),
                "recommendations": self._generate_forecasting_recommendations(explanations)
            }
            
            # Convert explanations to serializable format
            for exp_type, result in explanations.items():
                forecasting_explanation["explanations"][exp_type.value] = {
                    "confidence": result.confidence,
                    "processing_time": result.processing_time,
                    "metadata": result.metadata
                }
                
                if exp_type == ExplanationType.FEATURE_IMPORTANCE:
                    forecasting_explanation["explanations"][exp_type.value].update({
                        "top_features": result.top_features[:10],
                        "importance_scores": result.importance_scores
                    })
                elif exp_type == ExplanationType.DECISION_PATH:
                    forecasting_explanation["explanations"][exp_type.value].update({
                        "decision_rules": result.decision_rules[:5],
                        "path_contribution": result.path_contribution
                    })
                elif exp_type == ExplanationType.COUNTERFACTUAL:
                    forecasting_explanation["explanations"][exp_type.value].update({
                        "scenario_description": result.scenario_description,
                        "change_impact": result.change_impact
                    })
            
            return forecasting_explanation
            
        except Exception as e:
            logger.error(f"Error explaining forecasting decision: {e}")
            return {
                "model_name": model_name,
                "error": str(e),
                "explanations": {},
                "summary": "Error occurred during explanation generation"
            }
    
    def _create_forecasting_summary(
        self,
        explanations: Dict[ExplanationType, ExplanationResult],
        prediction_result: Dict[str, Any]
    ) -> str:
        """Create a human-readable summary of forecasting explanations"""
        
        summary_parts = []
        
        # Add prediction summary
        if "predictions" in prediction_result:
            pred_value = prediction_result["predictions"]
            if isinstance(pred_value, (list, np.ndarray)):
                pred_value = pred_value[0] if len(pred_value) > 0 else "N/A"
            summary_parts.append(f"Predicted value: {pred_value:.3f}")
        
        # Add feature importance summary
        if ExplanationType.FEATURE_IMPORTANCE in explanations:
            importance_result = explanations[ExplanationType.FEATURE_IMPORTANCE]
            top_feature = importance_result.top_features[0] if importance_result.top_features else None
            if top_feature:
                summary_parts.append(f"Most important factor: {top_feature[0]} (impact: {top_feature[1]:.3f})")
        
        # Add decision path summary
        if ExplanationType.DECISION_PATH in explanations:
            decision_result = explanations[ExplanationType.DECISION_PATH]
            if decision_result.decision_rules:
                summary_parts.append(f"Key decision: {decision_result.decision_rules[0]}")
        
        return ". ".join(summary_parts) if summary_parts else "No explanation summary available"
    
    def _generate_forecasting_recommendations(
        self,
        explanations: Dict[ExplanationType, ExplanationResult]
    ) -> List[str]:
        """Generate actionable recommendations based on explanations"""
        
        recommendations = []
        
        # Feature importance recommendations
        if ExplanationType.FEATURE_IMPORTANCE in explanations:
            importance_result = explanations[ExplanationType.FEATURE_IMPORTANCE]
            if importance_result.top_features:
                top_feature = importance_result.top_features[0]
                recommendations.append(
                    f"Monitor {top_feature[0]} closely as it has the highest impact on predictions"
                )
        
        # Counterfactual recommendations
        if ExplanationType.COUNTERFACTUAL in explanations:
            counterfactual_result = explanations[ExplanationType.COUNTERFACTUAL]
            if counterfactual_result.change_impact:
                most_sensitive = max(counterfactual_result.change_impact.items(), key=lambda x: x[1])
                recommendations.append(
                    f"Small changes in {most_sensitive[0]} could significantly affect predictions"
                )
        
        # General recommendations
        recommendations.extend([
            "Consider multiple time horizons for robust forecasting",
            "Validate predictions with domain expertise",
            "Monitor model performance over time"
        ])
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def get_model_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get information about registered models"""
        registry_info = {}
        
        for model_name, info in self.model_registry.items():
            registry_info[model_name] = {
                "model_type": info["model_type"].value,
                "feature_count": len(info["feature_names"]),
                "feature_names": info["feature_names"],
                "registered_at": info["registered_at"].isoformat(),
                "has_explainer": model_name in self.explainers
            }
        
        return registry_info
    
    def clear_cache(self):
        """Clear the explanation cache"""
        self.cache.clear()
        logger.info("Explainability service cache cleared")
    
    def export_explanation(
        self,
        explanation_result: ExplanationResult,
        output_path: str,
        format: str = "json"
    ):
        """
        Export explanation result to file
        
        Args:
            explanation_result: Explanation result to export
            output_path: Path to save the explanation
            format: Export format ('json', 'pickle')
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if format.lower() == "json":
                # Convert to JSON-serializable format
                export_data = {
                    "model_name": explanation_result.model_name,
                    "explanation_type": explanation_result.explanation_type.value,
                    "feature_names": explanation_result.feature_names,
                    "shap_values": explanation_result.shap_values.tolist(),
                    "base_value": float(explanation_result.base_value) if isinstance(explanation_result.base_value, np.ndarray) else explanation_result.base_value,
                    "prediction": float(explanation_result.prediction) if isinstance(explanation_result.prediction, np.ndarray) else explanation_result.prediction,
                    "confidence": explanation_result.confidence,
                    "processing_time": explanation_result.processing_time,
                    "timestamp": explanation_result.timestamp.isoformat(),
                    "metadata": explanation_result.metadata
                }
                
                # Add type-specific data
                if isinstance(explanation_result, FeatureImportanceResult):
                    export_data.update({
                        "importance_scores": explanation_result.importance_scores,
                        "top_features": explanation_result.top_features,
                        "importance_ranking": explanation_result.importance_ranking
                    })
                elif isinstance(explanation_result, CounterfactualResult):
                    export_data.update({
                        "original_prediction": explanation_result.original_prediction,
                        "counterfactual_prediction": explanation_result.counterfactual_prediction,
                        "feature_changes": explanation_result.feature_changes,
                        "change_impact": explanation_result.change_impact,
                        "scenario_description": explanation_result.scenario_description
                    })
                elif isinstance(explanation_result, DecisionPathResult):
                    export_data.update({
                        "decision_nodes": explanation_result.decision_nodes,
                        "path_contribution": explanation_result.path_contribution,
                        "decision_rules": explanation_result.decision_rules
                    })
                
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                    
            elif format.lower() == "pickle":
                with open(output_path, 'wb') as f:
                    pickle.dump(explanation_result, f)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Explanation exported to {output_path} in {format} format")
            
        except Exception as e:
            logger.error(f"Error exporting explanation: {e}")
            raise


# Factory function for easy initialization
def create_explainability_service(config_path: Optional[str] = None) -> ExplainabilityService:
    """
    Factory function to create and initialize explainability service
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Initialized ExplainabilityService instance
    """
    return ExplainabilityService(config_path)


# Utility functions for common explanation tasks
def explain_model_prediction(
    model: Any,
    model_type: ModelType,
    feature_names: List[str],
    input_data: Union[np.ndarray, pd.DataFrame, Dict[str, Any]],
    model_name: str = "temp_model"
) -> Dict[ExplanationType, ExplanationResult]:
    """
    Quick explanation for a model without registration
    
    Args:
        model: The trained model
        model_type: Type of model
        feature_names: Names of input features
        input_data: Input data for prediction
        model_name: Temporary name for the model
        
    Returns:
        Dictionary of explanations
    """
    service = ExplainabilityService()
    service.register_model(model_name, model, model_type, feature_names)
    return service.explain_prediction(model_name, input_data)


def compare_model_explanations(
    models: Dict[str, Dict[str, Any]],
    input_data: Union[np.ndarray, pd.DataFrame, Dict[str, Any]]
) -> Dict[str, Dict[ExplanationType, ExplanationResult]]:
    """
    Compare explanations across multiple models
    
    Args:
        models: Dictionary with model info {name: {model, model_type, feature_names}}
        input_data: Input data for prediction
        
    Returns:
        Dictionary mapping model names to their explanations
    """
    service = ExplainabilityService()
    results = {}
    
    # Register all models
    for model_name, model_info in models.items():
        service.register_model(
            model_name,
            model_info["model"],
            model_info["model_type"],
            model_info["feature_names"]
        )
    
    # Generate explanations for each model
    for model_name in models.keys():
        try:
            results[model_name] = service.explain_prediction(model_name, input_data)
        except Exception as e:
            logger.error(f"Error explaining model {model_name}: {e}")
            results[model_name] = {}
    
    return results


# Export main classes and functions
__all__ = [
    "ExplainabilityService",
    "ExplanationResult",
    "FeatureImportanceResult",
    "CounterfactualResult",
    "DecisionPathResult",
    "ExplanationType",
    "ModelType",
    "create_explainability_service",
    "explain_model_prediction",
    "compare_model_explanations"
]