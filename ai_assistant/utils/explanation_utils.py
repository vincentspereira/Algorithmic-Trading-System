"""
Explanation Utilities for AI Assistant
Provides shared utility functions for generating insights, recommendations, and summaries
from model explanations.
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field
import numpy as np

# Assuming ExplanationResult and ExplanationType are defined elsewhere and imported
# For now, we'll define minimal versions or assume they are passed as dicts.

@dataclass
class ExplanationResult:
    # Minimal definition for type hinting purposes
    confidence: float = 0.0
    processing_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class ExplanationType:
    # Minimal definition for type hinting purposes
    FEATURE_IMPORTANCE = "feature_importance"
    DECISION_PATH = "decision_path"
    COUNTERFACTUAL = "counterfactual"


def generate_insights(
    explanation_results: Dict[str, Any],
    prediction: float,
    confidence: float
) -> List[str]:
    """Generate key insights from explanation results"""
    insights = []
    
    # Confidence insights
    if confidence > 0.8:
        insights.append("High confidence prediction - model is very certain about this result")
    elif confidence > 0.6:
        insights.append("Moderate confidence prediction - consider additional validation")
    else:
        insights.append("Low confidence prediction - use with caution and seek additional information")
    
    # Feature importance insights
    if 'feature_importance' in explanation_results:
        importance_data = explanation_results['feature_importance']
        top_features = importance_data.get('top_features', [])
        if top_features:
            top_feature = top_features[0]
            insights.append(f"Most influential factor: {top_feature[0]} (impact: {top_feature[1]:.3f})")
    
    # Decision path insights
    if 'decision_path' in explanation_results:
        decision_data = explanation_results['decision_path']
        decision_rules = decision_data.get('decision_rules', [])
        if decision_rules:
            insights.append(f"Key decision factor: {decision_rules[0]}")
    
    # Counterfactual insights
    if 'counterfactual' in explanation_results:
        counterfactual_data = explanation_results['counterfactual']
        scenario_desc = counterfactual_data.get('scenario_description', '')
        if scenario_desc:
            insights.append(f"Sensitivity analysis: {scenario_desc}")
    
    return insights[:5]  # Limit to 5 insights


def generate_recommendations(
    explanation_results: Dict[str, Any],
    prediction: float,
    confidence: float
) -> List[str]:
    """Generate actionable recommendations"""
    recommendations = []
    
    # Confidence-based recommendations
    if confidence < 0.7:
        recommendations.append("Consider gathering additional data to improve prediction confidence")
        recommendations.append("Validate results with domain experts before making decisions")
    
    # Feature importance recommendations
    if 'feature_importance' in explanation_results:
        importance_data = explanation_results['feature_importance']
        top_features = importance_data.get('top_features', [])
        if top_features:
            recommendations.append(f"Monitor {top_features[0][0]} closely as it has the highest impact")
    
    # General recommendations
    recommendations.extend([
        "Review model assumptions and validate with current market conditions",
        "Consider ensemble methods for more robust predictions",
        "Implement continuous monitoring of model performance"
    ])
    
    return recommendations[:5]  # Limit to 5 recommendations


def create_explanation_summary(
    explanation_results: Dict[str, Any],
    model_name: str,
    prediction: float,
    confidence: float
) -> str:
    """Create a human-readable explanation summary"""
    summary_parts = []
    
    summary_parts.append(f"The {model_name} model predicts a value of {prediction:.3f} with {confidence:.1%} confidence.")
    
    if 'feature_importance' in explanation_results:
        importance_data = explanation_results['feature_importance']
        top_features = importance_data.get('top_features', [])
        if top_features:
            summary_parts.append(f"The most influential factor is {top_features[0][0]} with an impact of {top_features[0][1]:.3f}.")
    
    if 'decision_path' in explanation_results:
        decision_data = explanation_results['decision_path']
        if decision_data.get('decision_rules'):
            summary_parts.append("The model's decision process follows a clear logical path based on feature contributions.")
    
    if 'counterfactual' in explanation_results:
        counterfactual_data = explanation_results['counterfactual']
        if counterfactual_data.get('change_impact'):
            summary_parts.append("Sensitivity analysis shows which features would most impact the prediction if changed.")
    
    return " ".join(summary_parts)


def create_forecasting_summary(
    explanations: Dict[str, Any],
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
    if "feature_importance" in explanations:
        importance_result = explanations["feature_importance"]
        top_feature = importance_result.get("top_features", [])[0] if importance_result.get("top_features") else None
        if top_feature:
            summary_parts.append(f"Most important factor: {top_feature[0]} (impact: {top_feature[1]:.3f})")
    
    # Add decision path summary
    if "decision_path" in explanations:
        decision_result = explanations["decision_path"]
        if decision_result.get("decision_rules"):
            summary_parts.append(f"Key decision: {decision_result['decision_rules'][0]}")
    
    return ". ".join(summary_parts) if summary_parts else "No explanation summary available"


def generate_forecasting_recommendations(
    explanations: Dict[str, Any]
) -> List[str]:
    """Generate actionable recommendations based on explanations"""
    
    recommendations = []
    
    # Feature importance recommendations
    if "feature_importance" in explanations:
        importance_result = explanations["feature_importance"]
        if importance_result.get("top_features"):
            top_feature = importance_result["top_features"][0]
            recommendations.append(
                f"Monitor {top_feature[0]} closely as it has the highest impact on predictions"
            )
    
    # Counterfactual recommendations
    if "counterfactual" in explanations:
        counterfactual_result = explanations["counterfactual"]
        if counterfactual_result.get("change_impact"):
            most_sensitive = max(counterfactual_result["change_impact"].items(), key=lambda x: x[1])
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

