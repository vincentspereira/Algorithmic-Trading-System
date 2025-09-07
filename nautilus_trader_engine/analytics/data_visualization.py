"""Data Visualization for Analytics Module
Provides charting and visualization capabilities for trading analytics.
"""

import pandas as pd
import numpy as np

# Handle optional dependencies
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    plt = None
    MATPLOTLIB_AVAILABLE = False

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    sns = None
    SEABORN_AVAILABLE = False
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import logging
import io
import base64
from dataclasses import dataclass, field


@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    chart_type: str = "line"  # line, bar, scatter, heatmap, histogram
    width: int = 10
    height: int = 6
    theme: str = "default"  # default, dark, light
    show_grid: bool = True
    show_legend: bool = True
    color_palette: str = "viridis"


@dataclass
class VisualizationData:
    """Data structure for visualization."""
    data: Union[pd.DataFrame, Dict[str, Any], List[Any]]
    x_column: Optional[str] = None
    y_column: Optional[str] = None
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    config: ChartConfig = field(default_factory=ChartConfig)


class DataVisualization:
    """Provides data visualization capabilities for trading analytics."""
    
    def __init__(self):
        """Initialize the data visualization component."""
        self.logger = logging.getLogger(__name__)
        if MATPLOTLIB_AVAILABLE:
            self._setup_themes()
        else:
            self.logger.warning("Matplotlib not available, visualization features will be limited")
    
    def _setup_themes(self):
        """Set up visualization themes."""
        if MATPLOTLIB_AVAILABLE and SEABORN_AVAILABLE:
            # Configure default theme
            plt.style.use('default')
            sns.set_theme()
        elif MATPLOTLIB_AVAILABLE:
            plt.style.use('default')
    
    def create_chart(self, viz_data: VisualizationData) -> str:
        """Create a chart and return as base64 encoded image.
        
        Args:
            viz_data: VisualizationData object with chart parameters
            
        Returns:
            Base64 encoded image string
        """
        if not MATPLOTLIB_AVAILABLE:
            self.logger.warning("Matplotlib not available, cannot create chart")
            return ""
        
        try:
            # Set up the figure
            plt.figure(figsize=(viz_data.config.width, viz_data.config.height))
            
            # Apply theme
            if viz_data.config.theme == "dark":
                plt.style.use('dark_background')
            elif viz_data.config.theme == "light":
                plt.style.use('default')
            
            # Create chart based on type
            if viz_data.config.chart_type == "line":
                chart_result = self._create_line_chart(viz_data)
            elif viz_data.config.chart_type == "bar":
                chart_result = self._create_bar_chart(viz_data)
            elif viz_data.config.chart_type == "scatter":
                chart_result = self._create_scatter_chart(viz_data)
            elif viz_data.config.chart_type == "heatmap":
                chart_result = self._create_heatmap(viz_data)
            elif viz_data.config.chart_type == "histogram":
                chart_result = self._create_histogram(viz_data)
            else:
                # Default to line chart
                chart_result = self._create_line_chart(viz_data)
            
            # Add labels and title
            if viz_data.title:
                plt.title(viz_data.title)
            if viz_data.xlabel:
                plt.xlabel(viz_data.xlabel)
            if viz_data.ylabel:
                plt.ylabel(viz_data.ylabel)
            
            # Add grid if requested
            if viz_data.config.show_grid:
                plt.grid(True, alpha=0.3)
            
            # Add legend if requested
            if viz_data.config.show_legend:
                plt.legend()
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', bbox_inches='tight', dpi=300)
            buffer.seek(0)
            
            # Convert to base64
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            # Clean up
            plt.close()
            
            return image_base64
            
        except Exception as e:
            self.logger.error(f"Error creating chart: {e}")
            try:
                plt.close()
            except:
                pass
            return ""
    
    def _create_line_chart(self, viz_data: VisualizationData) -> bool:
        """Create a line chart.
        
        Args:
            viz_data: VisualizationData object
            
        Returns:
            True if successful
        """
        if not MATPLOTLIB_AVAILABLE:
            return False
            
        try:
            if isinstance(viz_data.data, pd.DataFrame):
                if viz_data.x_column and viz_data.y_column:
                    plt.plot(viz_data.data[viz_data.x_column], 
                            viz_data.data[viz_data.y_column], 
                            label=viz_data.y_column)
                else:
                    # Plot all numeric columns
                    numeric_columns = viz_data.data.select_dtypes(include=[np.number]).columns
                    for column in numeric_columns:
                        plt.plot(viz_data.data.index, 
                                viz_data.data[column], 
                                label=column)
            else:
                # Handle dictionary or list data
                if isinstance(viz_data.data, dict):
                    for key, values in viz_data.data.items():
                        plt.plot(values, label=key)
                elif isinstance(viz_data.data, list):
                    plt.plot(viz_data.data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating line chart: {e}")
            return False
    
    def _create_bar_chart(self, viz_data: VisualizationData) -> bool:
        """Create a bar chart.
        
        Args:
            viz_data: VisualizationData object
            
        Returns:
            True if successful
        """
        if not MATPLOTLIB_AVAILABLE:
            return False
            
        try:
            if isinstance(viz_data.data, pd.DataFrame):
                if viz_data.x_column and viz_data.y_column:
                    plt.bar(viz_data.data[viz_data.x_column], 
                           viz_data.data[viz_data.y_column], 
                           label=viz_data.y_column)
                else:
                    # Plot all numeric columns
                    numeric_columns = viz_data.data.select_dtypes(include=[np.number]).columns
                    for column in numeric_columns:
                        plt.bar(range(len(viz_data.data)), 
                               viz_data.data[column], 
                               label=column,
                               alpha=0.7)
            else:
                # Handle dictionary or list data
                if isinstance(viz_data.data, dict):
                    plt.bar(list(viz_data.data.keys()), 
                           list(viz_data.data.values()))
                elif isinstance(viz_data.data, list):
                    plt.bar(range(len(viz_data.data)), 
                           viz_data.data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating bar chart: {e}")
            return False
    
    def _create_scatter_chart(self, viz_data: VisualizationData) -> bool:
        """Create a scatter chart.
        
        Args:
            viz_data: VisualizationData object
            
        Returns:
            True if successful
        """
        if not MATPLOTLIB_AVAILABLE:
            return False
            
        try:
            if isinstance(viz_data.data, pd.DataFrame):
                if viz_data.x_column and viz_data.y_column:
                    plt.scatter(viz_data.data[viz_data.x_column], 
                               viz_data.data[viz_data.y_column], 
                               label=viz_data.y_column,
                               alpha=0.7)
                else:
                    # Need both x and y columns for scatter plot
                    self.logger.warning("Scatter plot requires both x_column and y_column")
                    return False
            else:
                # Handle dictionary or list data
                self.logger.warning("Scatter plot requires DataFrame with x_column and y_column")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating scatter chart: {e}")
            return False
    
    def _create_heatmap(self, viz_data: VisualizationData) -> bool:
        """Create a heatmap.
        
        Args:
            viz_data: VisualizationData object
            
        Returns:
            True if successful
        """
        if not MATPLOTLIB_AVAILABLE or not SEABORN_AVAILABLE:
            return False
            
        try:
            if isinstance(viz_data.data, pd.DataFrame):
                # Create correlation matrix if not already provided
                if viz_data.x_column is None and viz_data.y_column is None:
                    # Use correlation matrix
                    corr_matrix = viz_data.data.corr()
                    sns.heatmap(corr_matrix, annot=True, cmap=viz_data.config.color_palette)
                else:
                    # Use provided data
                    sns.heatmap(viz_data.data, annot=True, cmap=viz_data.config.color_palette)
            else:
                # Handle dictionary or list data
                self.logger.warning("Heatmap requires DataFrame data")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating heatmap: {e}")
            return False
    
    def _create_histogram(self, viz_data: VisualizationData) -> bool:
        """Create a histogram.
        
        Args:
            viz_data: VisualizationData object
            
        Returns:
            True if successful
        """
        if not MATPLOTLIB_AVAILABLE:
            return False
            
        try:
            if isinstance(viz_data.data, pd.DataFrame):
                if viz_data.y_column:
                    plt.hist(viz_data.data[viz_data.y_column], 
                            bins=30, 
                            alpha=0.7,
                            label=viz_data.y_column)
                else:
                    # Plot histograms for all numeric columns
                    numeric_columns = viz_data.data.select_dtypes(include=[np.number]).columns
                    for i, column in enumerate(numeric_columns):
                        plt.hist(viz_data.data[column], 
                                bins=30, 
                                alpha=0.7,
                                label=column)
            else:
                # Handle dictionary or list data
                if isinstance(viz_data.data, dict):
                    for key, values in viz_data.data.items():
                        plt.hist(values, bins=30, alpha=0.7, label=key)
                elif isinstance(viz_data.data, list):
                    plt.hist(viz_data.data, bins=30, alpha=0.7)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating histogram: {e}")
            return False