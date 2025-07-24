"""
Pydantic models for features endpoints

This module contains all feature engineering-related data models used throughout the API.
These models define the structure for feature requests, feature sets, technical indicators,
and responses from the feature engineering system.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AggregationPeriod(str, Enum):
    """
    Available aggregation periods for feature calculation
    
    Defines the time periods over which features can be aggregated.
    """
    DAILY = "daily"
    HOURLY = "hourly"
    MINUTE_5 = "5min"
    MINUTE_15 = "15min"
    MINUTE_30 = "30min"


class FeatureType(str, Enum):
    """
    Available feature types
    
    Enumeration of all supported feature types that can be calculated.
    """
    TECHNICAL_INDICATORS = "technical_indicators"
    PRICE_FEATURES = "price_features"
    VOLUME_FEATURES = "volume_features"
    VOLATILITY_FEATURES = "volatility_features"
    MOMENTUM_FEATURES = "momentum_features"


class FeatureRequest(BaseModel):
    """
    Feature calculation request model
    
    Defines the parameters required to calculate features for a given asset,
    including the time period, aggregation, and specific features to compute.
    """
    symbol: str = Field(
        ...,
        description="Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)",
        min_length=1,
        max_length=10,
        example="AAPL"
    )
    start_date: datetime = Field(
        ...,
        description="Start date for feature calculation in ISO 8601 format",
        example="2023-01-01T00:00:00Z"
    )
    end_date: datetime = Field(
        ...,
        description="End date for feature calculation in ISO 8601 format",
        example="2023-12-31T23:59:59Z"
    )
    aggregation: AggregationPeriod = Field(
        default=AggregationPeriod.DAILY,
        description="Time aggregation period for feature calculation",
        example="daily"
    )
    feature_types: Optional[List[FeatureType]] = Field(
        default=None,
        description="Specific feature types to calculate (if None, all types are calculated)",
        example=["technical_indicators", "price_features"]
    )
    indicators: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Specific technical indicators to calculate with their parameters",
        example={
            "sma": {"periods": [10, 20, 50]},
            "rsi": {"period": 14},
            "macd": {"fast": 12, "slow": 26, "signal": 9}
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2023-12-31T23:59:59Z",
                "aggregation": "daily",
                "feature_types": ["technical_indicators", "price_features"],
                "indicators": {
                    "sma": {"periods": [10, 20, 50]},
                    "rsi": {"period": 14}
                }
            }
        }


class FeatureSet(BaseModel):
    """
    Feature set model
    
    Contains a named set of calculated features with their values.
    Each feature set represents a category of features (e.g., technical indicators).
    """
    name: str = Field(
        ...,
        description="Name of the feature set (e.g., 'technical_indicators', 'price_features')",
        example="technical_indicators"
    )
    description: Optional[str] = Field(
        None,
        description="Description of what this feature set contains",
        example="Technical analysis indicators including moving averages, RSI, and MACD"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Dictionary containing the calculated feature values",
        example={
            "sma_10": [150.25, 151.30, 152.15],
            "sma_20": [148.75, 149.80, 150.90],
            "rsi_14": [65.2, 68.5, 72.1]
        }
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata about the feature calculations",
        example={
            "calculation_time": "2024-01-15T10:30:00Z",
            "data_points": 252,
            "missing_values": 0
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "technical_indicators",
                "description": "Technical analysis indicators including moving averages, RSI, and MACD",
                "data": {
                    "sma_10": [150.25, 151.30, 152.15],
                    "sma_20": [148.75, 149.80, 150.90],
                    "rsi_14": [65.2, 68.5, 72.1]
                },
                "metadata": {
                    "calculation_time": "2024-01-15T10:30:00Z",
                    "data_points": 252,
                    "missing_values": 0
                }
            }
        }


class FeaturesResponse(BaseModel):
    """
    Complete features response model
    
    Contains the complete results from a feature calculation request,
    including all calculated feature sets and metadata.
    """
    symbol: str = Field(
        ...,
        description="Stock ticker symbol that was analyzed",
        example="AAPL"
    )
    start_date: datetime = Field(
        ...,
        description="Start date of the analysis period",
        example="2023-01-01T00:00:00Z"
    )
    end_date: datetime = Field(
        ...,
        description="End date of the analysis period",
        example="2023-12-31T23:59:59Z"
    )
    aggregation: str = Field(
        ...,
        description="Time aggregation period used for calculations",
        example="daily"
    )
    features: List[FeatureSet] = Field(
        ...,
        description="List of calculated feature sets"
    )
    summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Summary statistics and metadata about the feature calculation",
        example={
            "total_features": 25,
            "calculation_time_seconds": 2.5,
            "data_quality_score": 0.98,
            "missing_data_percentage": 0.02
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "start_date": "2023-01-01T00:00:00Z",
                "end_date": "2023-12-31T23:59:59Z",
                "aggregation": "daily",
                "features": [
                    {
                        "name": "technical_indicators",
                        "description": "Technical analysis indicators",
                        "data": {
                            "sma_10": [150.25, 151.30, 152.15],
                            "rsi_14": [65.2, 68.5, 72.1]
                        }
                    }
                ],
                "summary": {
                    "total_features": 25,
                    "calculation_time_seconds": 2.5,
                    "data_quality_score": 0.98
                }
            }
        }


class FeaturesError(BaseModel):
    """
    Features error response model
    
    Contains error information when a feature calculation operation fails,
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
        example="2024-01-15T10:30:00Z"
    )
    error: str = Field(
        ...,
        description="Primary error message describing what went wrong",
        example="Invalid symbol: XYZ not found in data provider"
    )
    details: Optional[str] = Field(
        None,
        description="Additional error details and context",
        example="The symbol 'XYZ' is not available in our market data feed"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Parameters that caused the error",
        example={
            "symbol": "XYZ",
            "start_date": "2023-01-01T00:00:00Z",
            "end_date": "2023-12-31T23:59:59Z"
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "timestamp": "2024-01-15T10:30:00Z",
                "error": "Invalid symbol: XYZ not found in data provider",
                "details": "The symbol 'XYZ' is not available in our market data feed",
                "parameters": {
                    "symbol": "XYZ",
                    "start_date": "2023-01-01T00:00:00Z",
                    "end_date": "2023-12-31T23:59:59Z"
                }
            }
        }