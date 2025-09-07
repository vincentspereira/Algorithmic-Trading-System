"""Data Processor for Analytics Module
Handles data cleaning, feature engineering, and preprocessing for analytics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass, field


@dataclass
class DataQualityReport:
    """Report on data quality metrics."""
    total_records: int
    valid_records: int
    outliers_removed: int
    missing_values_filled: int
    data_quality_score: float
    processing_time_ms: float


@dataclass
class FeatureDescription:
    """Description of engineered features."""
    name: str
    description: str
    importance: float
    data_type: str


class DataProcessor:
    """Processes raw market data for analytics purposes."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the data processor with configuration.
        
        Args:
            config: Configuration dictionary with processing parameters
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Extract configuration parameters
        self.data_sources = config.get('data_sources', [])
        self.processing_frequency = config.get('processing_frequency', '1min')
        self.data_quality_checks = config.get('data_quality_checks', True)
        self.outlier_detection = config.get('outlier_detection', True)
        self.missing_data_handling = config.get('missing_data_handling', 'interpolation')
        
    def clean_data(self, raw_data: pd.DataFrame) -> Dict[str, Any]:
        """Clean raw market data by removing outliers and handling missing values.
        
        Args:
            raw_data: Raw market data DataFrame
            
        Returns:
            Dictionary containing cleaned data and quality report
        """
        start_time = datetime.now()
        
        # Make a copy to avoid modifying original data
        cleaned_data = raw_data.copy()
        
        # Handle missing values
        missing_values_filled = 0
        if self.missing_data_handling == 'interpolation':
            numeric_columns = cleaned_data.select_dtypes(include=[np.number]).columns
            cleaned_data[numeric_columns] = cleaned_data[numeric_columns].interpolate()
            missing_values_filled = cleaned_data.isnull().sum().sum()
        elif self.missing_data_handling == 'forward_fill':
            cleaned_data = cleaned_data.fillna(method='ffill')
            missing_values_filled = cleaned_data.isnull().sum().sum()
        
        # Detect and remove outliers
        outlier_indices = []
        if self.outlier_detection:
            outlier_indices = self._detect_outliers(cleaned_data)
            # Remove outliers
            if outlier_indices:
                cleaned_data = cleaned_data.drop(cleaned_data.index[outlier_indices])
        
        # Calculate data quality metrics
        total_records = len(raw_data)
        valid_records = len(cleaned_data)
        outliers_removed = len(outlier_indices)
        
        # Calculate data quality score (0-1, higher is better)
        data_quality_score = valid_records / total_records if total_records > 0 else 0.0
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        quality_report = DataQualityReport(
            total_records=total_records,
            valid_records=valid_records,
            outliers_removed=outliers_removed,
            missing_values_filled=missing_values_filled,
            data_quality_score=data_quality_score,
            processing_time_ms=processing_time
        )
        
        return {
            'cleaned_data': cleaned_data,
            'quality_report': quality_report
        }
    
    def _detect_outliers(self, data: pd.DataFrame) -> List[int]:
        """Detect outliers using isolation forest method.
        
        Args:
            data: DataFrame to analyze for outliers
            
        Returns:
            List of indices where outliers were detected
        """
        try:
            # For simplicity, we'll use a basic statistical approach
            # In a real implementation, we might use more sophisticated methods
            outlier_indices = []
            
            # Check numeric columns for outliers using Z-score
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for column in numeric_columns:
                # Calculate Z-scores
                z_scores = np.abs((data[column] - data[column].mean()) / data[column].std())
                # Identify outliers (Z-score > 3)
                column_outliers = data[z_scores > 3].index.tolist()
                outlier_indices.extend(column_outliers)
            
            # Remove duplicates and sort
            outlier_indices = sorted(list(set(outlier_indices)))
            
            return outlier_indices
            
        except Exception as e:
            self.logger.error(f"Error detecting outliers: {e}")
            return []
    
    def engineer_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Engineer features from cleaned market data.
        
        Args:
            data: Cleaned market data DataFrame
            
        Returns:
            Dictionary containing engineered features and metadata
        """
        try:
            # Calculate basic features
            features = pd.DataFrame()
            features['timestamp'] = data['timestamp'] if 'timestamp' in data.columns else pd.Series()
            
            # Calculate returns if price data is available
            if 'bid' in data.columns and 'ask' in data.columns:
                mid_price = (data['bid'] + data['ask']) / 2
                features['returns'] = mid_price.pct_change().fillna(0)
                features['mid_price'] = mid_price
                
            # Calculate volatility (rolling standard deviation)
            if 'returns' in features.columns:
                features['volatility'] = features['returns'].rolling(window=20, min_periods=1).std().fillna(0)
            
            # Calculate simple moving average if mid_price is available
            if 'mid_price' in features.columns:
                features['sma_20'] = features['mid_price'].rolling(window=20, min_periods=1).mean()
            
            # Calculate RSI if price data is available
            if 'mid_price' in features.columns:
                delta = features['mid_price'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                features['rsi'] = 100 - (100 / (1 + rs))
                features['rsi'] = features['rsi'].fillna(50)  # Default to 50 for RSI
            
            # Calculate volume features if volume data is available
            if 'volume' in data.columns:
                features['volume'] = data['volume']
                features['volume_sma'] = data['volume'].rolling(window=20, min_periods=1).mean()
            
            # Create feature descriptions
            feature_descriptions = {}
            
            if 'returns' in features.columns:
                feature_descriptions['returns'] = FeatureDescription(
                    name='returns',
                    description='Log returns calculated from mid prices',
                    importance=0.25,
                    data_type='float'
                )
            
            if 'volatility' in features.columns:
                feature_descriptions['volatility'] = FeatureDescription(
                    name='volatility',
                    description='Rolling 20-period volatility',
                    importance=0.20,
                    data_type='float'
                )
            
            if 'rsi' in features.columns:
                feature_descriptions['rsi'] = FeatureDescription(
                    name='rsi',
                    description='Relative Strength Index (14 periods)',
                    importance=0.15,
                    data_type='float'
                )
            
            if 'sma_20' in features.columns:
                feature_descriptions['sma_20'] = FeatureDescription(
                    name='sma_20',
                    description='20-period Simple Moving Average',
                    importance=0.12,
                    data_type='float'
                )
            
            if 'volume' in features.columns:
                feature_descriptions['volume'] = FeatureDescription(
                    name='volume',
                    description='Trading volume',
                    importance=0.10,
                    data_type='float'
                )
            
            if 'volume_sma' in features.columns:
                feature_descriptions['volume_sma'] = FeatureDescription(
                    name='volume_sma',
                    description='20-period volume moving average',
                    importance=0.08,
                    data_type='float'
                )
            
            # Calculate feature importance (simplified)
            feature_importance = {desc.name: desc.importance for desc in feature_descriptions.values()}
            
            # Normalize feature importance to sum to 1.0
            total_importance = sum(feature_importance.values())
            if total_importance > 0:
                feature_importance = {k: v/total_importance for k, v in feature_importance.items()}
            
            return {
                'features': features,
                'feature_descriptions': feature_descriptions,
                'feature_importance': feature_importance
            }
            
        except Exception as e:
            self.logger.error(f"Error engineering features: {e}")
            return {
                'features': pd.DataFrame(),
                'feature_descriptions': {},
                'feature_importance': {}
            }