"""
Analytics Module
Comprehensive market analytics, data processing, and visualization tools
"""

# Import existing analytics components
from .liquidity_detection import (
    LiquidityDetectionEngine,
    LiquidityType,
    LiquidityTier,
    VenueType,
    LiquiditySignal,
    IcebergOrderSignal,
    DarkPoolActivity,
    VenueLiquidityScore
)

from .order_book_analytics import (
    OrderBookAnalyticsEngine,
    OrderBookSnapshot,
    OrderBookLevel,
    OrderBookSide,
    MarketDepthAnalysis,
    OrderBookImbalance
)

# Import new analytics components
from .data_processor import DataProcessor, DataQualityReport, FeatureDescription
from .metrics_calculator import MetricsCalculator, PerformanceMetrics, RiskMetrics
from .report_generator import ReportGenerator, ReportConfig, ReportSection
from .dashboard_manager import DashboardManager, DashboardConfig, DashboardWidget, AlertRule
from .data_visualization import DataVisualization, ChartConfig, VisualizationData

# Note: market_maker_analysis.py has encoding issues, skipping for now
# Note: cross_asset_analytics.py has encoding issues, skipping for now

__all__ = [
    # Liquidity Detection
    'LiquidityDetectionEngine',
    'LiquidityType',
    'LiquidityTier',
    'VenueType',
    'LiquiditySignal',
    'IcebergOrderSignal',
    'DarkPoolActivity',
    'VenueLiquidityScore',
    
    # Order Book Analytics
    'OrderBookAnalyticsEngine',
    'OrderBookSnapshot',
    'OrderBookLevel',
    'OrderBookSide',
    'MarketDepthAnalysis',
    'OrderBookImbalance',
    
    # Data Processing
    'DataProcessor',
    'DataQualityReport',
    'FeatureDescription',
    
    # Metrics Calculation
    'MetricsCalculator',
    'PerformanceMetrics',
    'RiskMetrics',
    
    # Report Generation
    'ReportGenerator',
    'ReportConfig',
    'ReportSection',
    
    # Dashboard Management
    'DashboardManager',
    'DashboardConfig',
    'DashboardWidget',
    'AlertRule',
    
    # Data Visualization
    'DataVisualization',
    'ChartConfig',
    'VisualizationData',
    
    # Market Maker Analysis - temporarily disabled due to encoding issues
    # 'MarketMakerAnalysisEngine',
    # 'MarketMakerMetrics',
    # 'MarketMakingStrategy',
    # 'LiquidityProvisionMetrics',
    
    # Cross Asset Analytics - temporarily disabled due to encoding issues
    # 'CrossAssetCorrelationAnalyzer',
    # 'ArbitrageDetector',
    # 'CorrelationResult',
    # 'ArbitrageOpportunity',
    # 'SpreadOpportunity',
    # 'RiskAttribution'
]