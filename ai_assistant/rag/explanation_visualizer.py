"""
Explanation Visualizer for AI Assistant - Phase 3
SHAP visualization components and interactive HTML report generation

This module provides:
1. SHAP plot generation (waterfall, force, summary plots)
2. Interactive HTML reports for explanations
3. Export capabilities in various formats (PNG, SVG, HTML, PDF)
4. Custom visualization themes for financial domain
5. Dashboard-style explanation summaries
6. Integration with web interfaces and notebooks

All visualizations are optimized for financial domain understanding
and provide clear, actionable insights for decision-making.
"""

import os
import json
import logging
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import io

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from plotly.offline import plot as plotly_plot

# SHAP visualization imports
import shap
from shap.plots import waterfall, force, summary, bar, heatmap, partial_dependence

from .utils.explanation_utils import generate_insights, generate_recommendations, create_explanation_summary

# Additional visualization libraries
from wordcloud import WordCloud
import networkx as nx
from PIL import Image, ImageDraw, ImageFont

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set plotting backends
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")
pio.renderers.default = "browser"


class VisualizationType(Enum):
    """Types of visualizations supported"""
    WATERFALL = "waterfall"
    FORCE_PLOT = "force_plot"
    SUMMARY_PLOT = "summary_plot"
    BAR_PLOT = "bar_plot"
    HEATMAP = "heatmap"
    PARTIAL_DEPENDENCE = "partial_dependence"
    FEATURE_IMPORTANCE = "feature_importance"
    DECISION_PATH = "decision_path"
    COUNTERFACTUAL = "counterfactual"
    DASHBOARD = "dashboard"


class ExportFormat(Enum):
    """Export formats supported"""
    PNG = "png"
    SVG = "svg"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    INTERACTIVE_HTML = "interactive_html"


class ColorTheme(Enum):
    """Color themes for visualizations"""
    FINANCIAL = "financial"
    CORPORATE = "corporate"
    ACADEMIC = "academic"
    DARK = "dark"
    LIGHT = "light"
    COLORBLIND = "colorblind"


@dataclass
class VisualizationConfig:
    """Configuration for visualizations"""
    theme: ColorTheme = ColorTheme.FINANCIAL
    figure_size: Tuple[int, int] = (12, 8)
    dpi: int = 300
    font_size: int = 12
    title_font_size: int = 16
    show_values: bool = True
    show_confidence: bool = True
    max_features: int = 20
    interactive: bool = True
    export_format: ExportFormat = ExportFormat.HTML


class ExplanationVisualizer:
    """
    Comprehensive visualization service for model explanations
    
    Features:
    - Multiple SHAP visualization types
    - Interactive HTML reports
    - Custom financial domain themes
    - Export in multiple formats
    - Dashboard-style summaries
    """
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        """
        Initialize explanation visualizer
        
        Args:
            config: Visualization configuration
        """
        self.config = config or VisualizationConfig()
        self.color_schemes = self._load_color_schemes()
        self.templates = self._load_html_templates()
        
        # Set up matplotlib and seaborn styles
        self._setup_plotting_style()
        
        logger.info("Explanation Visualizer initialized")
    
    def _load_color_schemes(self) -> Dict[ColorTheme, Dict[str, Any]]:
        """Load color schemes for different themes"""
        return {
            ColorTheme.FINANCIAL: {
                "positive": "#2E8B57",  # Sea Green
                "negative": "#DC143C",  # Crimson
                "neutral": "#708090",   # Slate Gray
                "background": "#F8F8FF", # Ghost White
                "text": "#2F4F4F",      # Dark Slate Gray
                "accent": "#4169E1",    # Royal Blue
                "palette": ["#2E8B22", "#DC143C", "#4169E1", "#FF8C00", "#9370DB"]
            },
            ColorTheme.CORPORATE: {
                "positive": "#0066CC",  # Corporate Blue
                "negative": "#CC0000",  # Corporate Red
                "neutral": "#666666",   # Gray
                "background": "#FFFFFF", # White
                "text": "#333333",      # Dark Gray
                "accent": "#FF6600",    # Orange
                "palette": ["#0066CC", "#CC0000", "#FF6600", "#00CC66", "#9966CC"]
            },
            ColorTheme.ACADEMIC: {
                "positive": "#1f77b4",  # Blue
                "negative": "#d62728",  # Red
                "neutral": "#7f7f7f",   # Gray
                "background": "#FFFFFF", # White
                "text": "#000000",      # Black
                "accent": "#ff7f0e",    # Orange
                "palette": ["#1f77b4", "#d62728", "#ff7f0e", "#2ca02c", "#9467bd"]
            },
            ColorTheme.DARK: {
                "positive": "#00FF7F",  # Spring Green
                "negative": "#FF6347",  # Tomato
                "neutral": "#C0C0C0",   # Silver
                "background": "#2F2F2F", # Dark Gray
                "text": "#FFFFFF",      # White
                "accent": "#00BFFF",    # Deep Sky Blue
                "palette": ["#00FF7F", "#FF6347", "#00BFFF", "#FFD700", "#DA70D6"]
            },
            ColorTheme.LIGHT: {
                "positive": "#228B22",  # Forest Green
                "negative": "#B22222",  # Fire Brick
                "neutral": "#808080",   # Gray
                "background": "#FAFAFA", # Very Light Gray
                "text": "#333333",      # Dark Gray
                "accent": "#4682B4",    # Steel Blue
                "palette": ["#228B22", "#B22222", "#4682B4", "#FF8C00", "#8A2BE2"]
            },
            ColorTheme.COLORBLIND: {
                "positive": "#0173B2",  # Blue
                "negative": "#DE8F05",  # Orange
                "neutral": "#949494",   # Gray
                "background": "#FFFFFF", # White
                "text": "#000000",      # Black
                "accent": "#CC78BC",    # Pink
                "palette": ["#0173B2", "#DE8F05", "#CC78BC", "#029E73", "#D55E00"]
            }
        }
    
    def _load_html_templates(self) -> Dict[str, str]:
        """Load HTML templates for reports"""
        return {
            "base": """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title}</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: {background_color};
                        color: {text_color};
                        line-height: 1.6;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    .header {
                        text-align: center;
                        margin-bottom: 30px;
                        border-bottom: 2px solid {accent_color};
                        padding-bottom: 20px;
                    }
                    .section {
                        margin: 30px 0;
                        padding: 20px;
                        border-left: 4px solid {accent_color};
                        background-color: #f9f9f9;
                    }
                    .visualization {
                        text-align: center;
                        margin: 20px 0;
                    }
                    .metrics {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin: 20px 0;
                    }
                    .metric-card {
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        text-align: center;
                    }
                    .metric-value {
                        font-size: 2em;
                        font-weight: bold;
                        color: {accent_color};
                    }
                    .footer {
                        text-align: center;
                        margin-top: 40px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                        color: #666;
                    }
                </style>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            </head>
            <body>
                <div class="container">
                    {content}
                </div>
            </body>
            </html>
            ",
            
            "dashboard": """
            <div class="header">
                <h1>{title}</h1>
                <p>{subtitle}</p>
                <p><strong>Generated:</strong> {timestamp}</p>
            </div>
            
            <div class="metrics">
                {metrics_cards}
            </div>
            
            <div class="section">
                <h2>Model Explanation Summary</h2>
                <p>{summary}</p>
            </div>
            
            {visualizations}
            
            <div class="section">
                <h2>Key Insights</h2>
                <ul>
                    {insights}
                </ul>
            </div>
            
            <div class="section">
                <h2>Recommendations</h2>
                <ul>
                    {recommendations}
                </ul>
            </div>
            
            <div class="footer">
                <p>Generated by Vincent S. Pereira Explainability Service</p>
                <p>Model: {model_name} | Confidence: {confidence:.2f}</p>
            </div>
            "
        }
    
    def _setup_plotting_style(self):
        """Set up matplotlib and seaborn plotting styles"""
        colors = self.color_schemes[self.config.theme]
        
        # Set matplotlib parameters
        plt.rcParams.update({
            'figure.figsize': self.config.figure_size,
            'figure.dpi': self.config.dpi,
            'font.size': self.config.font_size,
            'axes.titlesize': self.config.title_font_size,
            'axes.labelsize': self.config.font_size,
            'xtick.labelsize': self.config.font_size - 2,
            'ytick.labelsize': self.config.font_size - 2,
            'legend.fontsize': self.config.font_size - 2,
            'figure.facecolor': colors['background'],
            'axes.facecolor': colors['background'],
            'text.color': colors['text'],
            'axes.labelcolor': colors['text'],
            'xtick.color': colors['text'],
            'ytick.color': colors['text']
        })
        
        # Set seaborn style
        sns.set_palette(colors['palette'])
    
    def create_waterfall_plot(
        self,
        shap_values: np.ndarray,
        feature_names: List[str],
        base_value: float,
        prediction: float,
        title: str = "Feature Contributions",
        max_display: Optional[int] = None
    ) -> go.Figure:
        """
        Create waterfall plot showing feature contributions
        
        Args:
            shap_values: SHAP values for features
            feature_names: Names of features
            base_value: Base prediction value
            prediction: Final prediction
            title: Plot title
            max_display: Maximum features to display
            
        Returns:
            Plotly figure object
        """
        try:
            colors = self.color_schemes[self.config.theme]
            
            # Limit features if specified
            if max_display and len(shap_values) > max_display:
                # Sort by absolute SHAP values and take top features
                indices = np.argsort(np.abs(shap_values))[-max_display:]
                shap_values = shap_values[indices]
                feature_names = [feature_names[i] for i in indices]
            
            # Prepare data for waterfall plot
            x_labels = ['Base'] + feature_names + ['Prediction']
            y_values = [base_value] + list(shap_values) + [prediction]
            
            # Calculate cumulative values for positioning
            cumulative = [base_value]
            for shap_val in shap_values:
                cumulative.append(cumulative[-1] + shap_val)
            cumulative.append(prediction)
            
            # Create waterfall chart
            fig = go.Figure()
            
            # Add base value
            fig.add_trace(go.Bar(
                x=['Base'],
                y=[base_value],
                name='Base Value',
                marker_color=colors['neutral'],
                text=[f'{base_value:.3f}'],
                textposition='auto'
            ))
            
            # Add feature contributions
            for i, (feature, shap_val) in enumerate(zip(feature_names, shap_values)):
                color = colors['positive'] if shap_val > 0 else colors['negative']
                
                fig.add_trace(go.Bar(
                    x=[feature],
                    y=[abs(shap_val)],
                    base=[cumulative[i] if shap_val > 0 else cumulative[i+1]],
                    name=f'{feature} ({shap_val:+.3f})',
                    marker_color=color,
                    text=[f'{shap_val:+.3f}'],
                    textposition='auto',
                    showlegend=False
                ))
            
            # Add final prediction
            fig.add_trace(go.Bar(
                x=['Prediction'],
                y=[prediction],
                name='Final Prediction',
                marker_color=colors['accent'],
                text=[f'{prediction:.3f}'],
                textposition='auto'
            ))
            
            # Update layout
            fig.update_layout(
                title=title,
                xaxis_title='Features',
                yaxis_title='Contribution',
                template='plotly_white',
                font=dict(size=self.config.font_size),
                showlegend=True,
                height=600,
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating waterfall plot: {e}")
            return self._create_error_plot(f"Error creating waterfall plot: {str(e)}")
    
    def create_feature_importance_plot(
        self,
        importance_scores: Dict[str, float],
        title: str = "Feature Importance",
        max_features: Optional[int] = None
    ) -> go.Figure:
        """
        Create feature importance bar plot
        
        Args:
            importance_scores: Dictionary of feature importance scores
            title: Plot title
            max_features: Maximum features to display
            
        Returns:
            Plotly figure object
        """
        try:
            colors = self.color_schemes[self.config.theme]
            
            # Sort features by importance
            sorted_features = sorted(importance_scores.items(), key=lambda x: abs(x[1]), reverse=True)
            
            if max_features:
                sorted_features = sorted_features[:max_features]
            
            features, scores = zip(*sorted_features)
            
            # Create color list based on positive/negative values
            bar_colors = [colors['positive'] if score > 0 else colors['negative'] for score in scores]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=list(scores),
                    y=list(features),
                    orientation='h',
                    marker_color=bar_colors,
                    text=[f'{score:.3f}' for score in scores],
                    textposition='auto'
                )
            ])
            
            fig.update_layout(
                title=title,
                xaxis_title='Importance Score',
                yaxis_title='Features',
                template='plotly_white',
                font=dict(size=self.config.font_size),
                height=max(400, len(features) * 30),
                margin=dict(l=150, r=50, t=80, b=50)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating feature importance plot: {e}")
            return self._create_error_plot(f"Error creating feature importance plot: {str(e)}")
    
    def create_decision_path_plot(
        self,
        decision_nodes: List[Dict[str, Any]],
        title: str = "Decision Path"
    ) -> go.Figure:
        """
        Create decision path visualization
        
        Args:
            decision_nodes: List of decision nodes
            title: Plot title
            
        Returns:
            Plotly figure object
        """
        try:
            colors = self.color_schemes[self.config.theme]
            
            # Extract data from decision nodes
            steps = [node['step'] for node in decision_nodes]
            features = [node['feature'] for node in decision_nodes]
            contributions = [node['contribution'] for node in decision_nodes]
            cumulative = [node['cumulative_prediction'] for node in decision_nodes]
            
            # Create subplot with secondary y-axis
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # Add contribution bars
            fig.add_trace(
                go.Bar(
                    x=features,
                    y=contributions,
                    name='Contribution',
                    marker_color=[colors['positive'] if c > 0 else colors['negative'] for c in contributions],
                    text=[f'{c:+.3f}' for c in contributions],
                    textposition='auto'
                ),
                secondary_y=False
            )
            
            # Add cumulative prediction line
            fig.add_trace(
                go.Scatter(
                    x=features,
                    y=cumulative,
                    mode='lines+markers',
                    name='Cumulative Prediction',
                    line=dict(color=colors['accent'], width=3),
                    marker=dict(size=8)
                ),
                secondary_y=True
            )
            
            # Update layout
            fig.update_layout(
                title=title,
                template='plotly_white',
                font=dict(size=self.config.font_size),
                height=600,
                margin=dict(l=50, r=50, t=80, b=100)
            )
            
            # Update y-axes titles
            fig.update_yaxes(title_text="Feature Contribution", secondary_y=False)
            fig.update_yaxes(title_text="Cumulative Prediction", secondary_y=True)
            fig.update_xaxes(title_text="Decision Steps", tickangle=45)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating decision path plot: {e}")
            return self._create_error_plot(f"Error creating decision path plot: {str(e)}")
    
    def create_counterfactual_plot(
        self,
        original_prediction: float,
        counterfactual_prediction: float,
        feature_changes: Dict[str, Dict[str, float]],
        title: str = "Counterfactual Analysis"
    ) -> go.Figure:
        """
        Create counterfactual analysis visualization
        
        Args:
            original_prediction: Original prediction value
            counterfactual_prediction: Counterfactual prediction value
            feature_changes: Dictionary of feature changes
            title: Plot title
            
        Returns:
            Plotly figure object
        """
        try:
            colors = self.color_schemes[self.config.theme]
            
            # Prepare data
            features = list(feature_changes.keys())
            original_values = [feature_changes[f]['original_value'] for f in features]
            modified_values = [feature_changes[f]['modified_value'] for f in features]
            changes = [modified_values[i] - original_values[i] for i in range(len(features))]
            
            # Create subplot
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Feature Changes', 'Prediction Comparison'),
                vertical_spacing=0.15
            )
            
            # Feature changes plot
            fig.add_trace(
                go.Bar(
                    x=features,
                    y=changes,
                    name='Feature Change',
                    marker_color=[colors['positive'] if c > 0 else colors['negative'] for c in changes],
                    text=[f'{c:+.3f}' for c in changes],
                    textposition='auto'
                ),
                row=1, col=1
            )
            
            # Prediction comparison
            fig.add_trace(
                go.Bar(
                    x=['Original', 'Counterfactual'],
                    y=[original_prediction, counterfactual_prediction],
                    name='Predictions',
                    marker_color=[colors['neutral'], colors['accent']],
                    text=[f'{original_prediction:.3f}', f'{counterfactual_prediction:.3f}'],
                    textposition='auto'
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                title=title,
                template='plotly_white',
                font=dict(size=self.config.font_size),
                height=800,
                showlegend=False,
                margin=dict(l=50, r=50, t=100, b=50)
            )
            
            # Update x-axes
            fig.update_xaxes(title_text="Features", row=1, col=1, tickangle=45)
            fig.update_xaxes(title_text="Scenario", row=2, col=1)
            
            # Update y-axes
            fig.update_yaxes(title_text="Change in Value", row=1, col=1)
            fig.update_yaxes(title_text="Prediction Value", row=2, col=1)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating counterfactual plot: {e}")
            return self._create_error_plot(f"Error creating counterfactual plot: {str(e)}")
    
    def create_summary_dashboard(
        self,
        explanation_results: Dict[str, Any],
        model_name: str,
        prediction: float,
        confidence: float
    ) -> str:
        """
        Create comprehensive HTML dashboard
        
        Args:
            explanation_results: Dictionary of explanation results
            model_name: Name of the model
            prediction: Model prediction
            confidence: Prediction confidence
            
        Returns:
            HTML string for dashboard
        """
        try:
            colors = self.color_schemes[self.config.theme]
            
            # Generate visualizations
            visualizations_html = ""
            
            # Feature importance plot
            if 'feature_importance' in explanation_results:
                importance_data = explanation_results['feature_importance']
                fig = self.create_feature_importance_plot(
                    importance_data.get('importance_scores', {}),
                    "Feature Importance Analysis"
                )
                plot_html = pio.to_html(fig, include_plotlyjs=False, div_id="importance_plot")
                visualizations_html += f'<div class="section"><h2>Feature Importance</h2><div class="visualization">{plot_html}</div></div>'
            
            # Decision path plot
            if 'decision_path' in explanation_results:
                decision_data = explanation_results['decision_path']
                fig = self.create_decision_path_plot(
                    decision_data.get('decision_nodes', []),
                    "Decision Path Analysis"
                )
                plot_html = pio.to_html(fig, include_plotlyjs=False, div_id="decision_plot")
                visualizations_html += f'<div class="section"><h2>Decision Path</h2><div class="visualization">{plot_html}</div></div>'
            
            # Counterfactual plot
            if 'counterfactual' in explanation_results:
                counterfactual_data = explanation_results['counterfactual']
                fig = self.create_counterfactual_plot(
                    counterfactual_data.get('original_prediction', 0),
                    counterfactual_data.get('counterfactual_prediction', 0),
                    counterfactual_data.get('feature_changes', {}),
                    "Counterfactual Analysis"
                )
                plot_html = pio.to_html(fig, include_plotlyjs=False, div_id="counterfactual_plot")
                visualizations_html += f'<div class="section"><h2>What-If Analysis</h2><div class="visualization">{plot_html}</div></div>'
            
            # Create metrics cards
            metrics_cards = f"""
            <div class="metric-card">
                <div class="metric-value">{prediction:.3f}</div>
                <div>Prediction</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{confidence:.1%}</div>
                <div>Confidence</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(explanation_results)}</div>
                <div>Explanations</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{model_name}</div>
                <div>Model</div>
            </div>
            """
            
            # Generate insights
            insights = generate_insights(explanation_results, prediction, confidence)
            insights_html = "".join([f"<li>{insight}</li>" for insight in insights])
            
            # Generate recommendations
            recommendations = generate_recommendations(explanation_results, prediction, confidence)
            recommendations_html = "".join([f"<li>{rec}</li>" for rec in recommendations])
            
            # Create summary
            summary = create_explanation_summary(explanation_results, model_name, prediction, confidence)
            
            # Fill dashboard template
            dashboard_content = self.templates['dashboard'].format(
                title="Model Explanation Dashboard",
                subtitle=f"Comprehensive analysis for {model_name}",
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                metrics_cards=metrics_cards,
                summary=summary,
                visualizations=visualizations_html,
                insights=insights_html,
                recommendations=recommendations_html,
                model_name=model_name,
                confidence=confidence
            )
            
            # Fill base template
            html_content = self.templates['base'].format(
                title="Model Explanation Dashboard",
                background_color=colors['background'],
                text_color=colors['text'],
                accent_color=colors['accent'],
                content=dashboard_content
            )
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error creating summary dashboard: {e}")
            return f"<html><body><h1>Error creating dashboard: {str(e)}</h1></body></html>"
    
    
    def _create_error_plot(self, error_message: str) -> go.Figure:
        """
        Create error plot when visualization fails
        """
        fig = go.Figure()
        
        fig.add_annotation(
            text=f"Error: {error_message}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="red")
        )
        
        fig.update_layout(
            title="Visualization Error",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            template='plotly_white',
            height=400
        )
        
        return fig
    
    def export_visualization(
        self,
        figure: go.Figure,
        output_path: str,
        format: ExportFormat = ExportFormat.HTML,
        width: int = 1200,
        height: int = 800
    ):
        """
        Export visualization to file
        
        Args:
            figure: Plotly figure to export
            output_path: Path to save the file
            format: Export format
            width: Image width (for image formats)
            height: Image height (for image formats)
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if format == ExportFormat.HTML:
                pio.write_html(figure, output_path, include_plotlyjs=True)
            elif format == ExportFormat.PNG:
                pio.write_image(figure, output_path, format='png', width=width, height=height)
            elif format == ExportFormat.SVG:
                pio.write_image(figure, output_path, format='svg', width=width, height=height)
            elif format == ExportFormat.PDF:
                pio.write_image(figure, output_path, format='pdf', width=width, height=height)
            elif format == ExportFormat.JSON:
                with open(output_path, 'w') as f:
                    json.dump(figure.to_dict(), f, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.info(f"Visualization exported to {output_path} in {format.value} format")
            
        except Exception as e:
            logger.error(f"Error exporting visualization: {e}")
            raise
    
    def export_dashboard(
        self,
        html_content: str,
        output_path: str
    ):
        """
        Export HTML dashboard to file
        
        Args:
            html_content: HTML content to export
            output_path: Path to save the HTML file
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Dashboard exported to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting dashboard: {e}")
            raise
    
    def create_batch_visualizations(
        self,
        explanation_results_list: List[Dict[str, Any]],
        output_dir: str,
        format: ExportFormat = ExportFormat.HTML
    ) -> List[str]:
        """
        Create visualizations for multiple explanation results
        
        Args:
            explanation_results_list: List of explanation results
            output_dir: Directory to save visualizations
            format: Export format
            
        Returns:
            List of output file paths
        """
        output_paths = []
        
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            for i, explanation_results in enumerate(explanation_results_list):
                # Create dashboard for each result
                model_name = explanation_results.get('model_name', f'Model_{i}')
                prediction = explanation_results.get('prediction', 0.0)
                confidence = explanation_results.get('confidence', 0.0)
                
                dashboard_html = self.create_summary_dashboard(
                    explanation_results,
                    model_name,
                    prediction,
                    confidence
                )
                
                # Save dashboard
                output_path = os.path.join(output_dir, f'explanation_dashboard_{i}.html')
                self.export_dashboard(dashboard_html, output_path)
                output_paths.append(output_path)
            
            logger.info(f"Created {len(output_paths)} batch visualizations in {output_dir}")
            return output_paths
            
        except Exception as e:
            logger.error(f"Error creating batch visualizations: {e}")
            return []
    
    def update_theme(self, theme: ColorTheme):
        """Update visualization theme"""
        self.config.theme = theme
        self._setup_plotting_style()
        logger.info(f"Updated visualization theme to {theme.value}")
    
    def get_available_themes(self) -> List[str]:
        """Get list of available color themes"""
        return [theme.value for theme in ColorTheme]
    
    def get_theme_preview(self) -> Dict[str, str]:
        """Get color preview for a theme"""
        return self.color_schemes[self.config.theme]


# Factory function for easy initialization
def create_explanation_visualizer(config: Optional[VisualizationConfig] = None) -> ExplanationVisualizer:
    """
    Factory function to create explanation visualizer
    
    Args:
        config: Visualization configuration
        
    Returns:
        ExplanationVisualizer instance
    """
    return ExplanationVisualizer(config)


# Utility functions for quick visualizations
def quick_feature_importance_plot(
    importance_scores: Dict[str, float],
    title: str = "Feature Importance",
    theme: ColorTheme = ColorTheme.FINANCIAL
) -> go.Figure:
    """
    Quick feature importance plot
    
    Args:
        importance_scores: Dictionary of feature importance scores
        title: Plot title
        theme: Color theme
        
    Returns:
        Plotly figure
    """
    config = VisualizationConfig(theme=theme)
    visualizer = ExplanationVisualizer(config)
    return visualizer.create_feature_importance_plot(importance_scores, title)


def quick_waterfall_plot(
    shap_values: np.ndarray,
    feature_names: List[str],
    base_value: float,
    prediction: float,
    title: str = "Feature Contributions",
    theme: ColorTheme = ColorTheme.FINANCIAL
) -> go.Figure:
    """
    Quick waterfall plot
    
    Args:
        shap_values: SHAP values
        feature_names: Feature names
        base_value: Base prediction value
        prediction: Final prediction
        title: Plot title
        theme: Color theme
        
    Returns:
        Plotly figure
    """
    config = VisualizationConfig(theme=theme)
    visualizer = ExplanationVisualizer(config)
    return visualizer.create_waterfall_plot(shap_values, feature_names, base_value, prediction, title)


def quick_dashboard(
    explanation_results: Dict[str, Any],
    model_name: str,
    prediction: float,
    confidence: float,
    theme: ColorTheme = ColorTheme.FINANCIAL
) -> str:
    """
    Quick dashboard creation
    
    Args:
        explanation_results: Explanation results
        model_name: Model name
        prediction: Prediction value
        confidence: Confidence score
        theme: Color theme
        
    Returns:
        HTML dashboard string
    """
    config = VisualizationConfig(theme=theme)
    visualizer = ExplanationVisualizer(config)
    return visualizer.create_summary_dashboard(explanation_results, model_name, prediction, confidence)


# Export main classes and functions
__all__ = [
    "ExplanationVisualizer",
    "VisualizationConfig",
    "VisualizationType",
    "ExportFormat",
    "ColorTheme",
    "create_explanation_visualizer",
    "quick_feature_importance_plot",
    "quick_waterfall_plot",
    "quick_dashboard"
]
