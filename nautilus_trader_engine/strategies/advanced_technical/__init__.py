"""Advanced Technical Strategies Module

This module implements sophisticated technical analysis strategies including:
- Gann Theory (angles, squares, time cycles)
- Fibonacci analysis (retracements, extensions, time zones)
- Elliott Wave analysis
- Harmonic patterns
- Advanced geometric patterns

Key Features:
- Mathematical precision in pattern recognition
- Multi-timeframe analysis
- Dynamic support/resistance levels
- Time-based projections
- Advanced entry/exit algorithms

Architecture:
Follows the 5-Pillar Architecture with specialized mathematical engines,
pattern recognition systems, and integrated risk management.
"""

# Core components
from .gann_strategies import (
    GannStrategy, GannAngleStrategy, GannSquareStrategy,
    GannTimeStrategy, GannFanStrategy, GannGridStrategy,
    GannAngle, GannLevel, GannTimeProjection,
    calculate_gann_angles, calculate_gann_square,
    find_gann_support_resistance
)

from .fibonacci_strategies import (
    FibonacciStrategy, FibonacciRetracementStrategy,
    FibonacciExtensionStrategy, FibonacciTimeStrategy,
    FibonacciLevel, FibonacciProjection, FibonacciCluster,
    calculate_fibonacci_levels, calculate_fibonacci_extensions,
    find_fibonacci_clusters
)

from .elliott_wave import (
    ElliottWaveStrategy, WaveAnalyzer, WavePattern,
    WaveType, WaveDegree, WaveCount,
    identify_wave_patterns, calculate_wave_projections
)

from .harmonic_patterns import (
    HarmonicPatternStrategy, PatternRecognizer,
    HarmonicPattern, PatternType, PatternValidation,
    detect_harmonic_patterns, validate_pattern_ratios
)

from .geometric_analysis import (
    GeometricPatternType, TrendDirection, PatternStatus, BreakoutDirection,
    GeometricPoint, TrendLine, GeometricPattern,
    GeometricAnalyzer, GeometricAnalysisStrategy,
    TrianglePatternStrategy, SupportResistanceStrategy,
    TriangleStrategy, SRStrategy, GeometricStrategy,
    find_support_resistance_levels, identify_triangle_pattern, find_trend_lines,
    TrendChannel, PriceGeometry, AngleAnalysis,
    calculate_trend_channels, analyze_price_geometry
)

# Utility functions
from .technical_utils import (
    calculate_pivot_points, find_swing_points,
    calculate_price_projections, validate_technical_levels,
    TechnicalLevel, SwingPoint, PivotPoint
)

__all__ = [
    # Gann Analysis
    'GannStrategy',
    'GannAngleStrategy',
    'GannSquareStrategy',
    'GannTimeStrategy',
    'GannFanStrategy',
    'GannGridStrategy',
    'GannAngle',
    'GannLevel',
    'GannTimeProjection',
    'calculate_gann_angles',
    'calculate_gann_square',
    'find_gann_support_resistance',
    
    # Fibonacci Analysis
    'FibonacciStrategy',
    'FibonacciRetracementStrategy',
    'FibonacciExtensionStrategy',
    'FibonacciTimeStrategy',
    'FibonacciLevel',
    'FibonacciProjection',
    'FibonacciCluster',
    'calculate_fibonacci_levels',
    'calculate_fibonacci_extensions',
    'find_fibonacci_clusters',
    
    # Elliott Wave Analysis
    'ElliottWaveStrategy',
    'WaveAnalyzer',
    'WavePattern',
    'WaveType',
    'WaveDegree',
    'WaveCount',
    'identify_wave_patterns',
    'calculate_wave_projections',
    
    # Harmonic Patterns
    'HarmonicPatternStrategy',
    'PatternRecognizer',
    'HarmonicPattern',
    'PatternType',
    'PatternValidation',
    'detect_harmonic_patterns',
    'validate_pattern_ratios',
    
    # Geometric Analysis
    'GeometricPatternType',
    'TrendDirection',
    'PatternStatus',
    'BreakoutDirection',
    'GeometricPoint',
    'TrendLine',
    'GeometricPattern',
    'GeometricAnalyzer',
    'GeometricAnalysisStrategy',
    'TrianglePatternStrategy',
    'SupportResistanceStrategy',
    'TriangleStrategy',
    'SRStrategy',
    'GeometricStrategy',
    'find_support_resistance_levels',
    'identify_triangle_pattern',
    'find_trend_lines',
    'TrendChannel',
    'PriceGeometry',
    'AngleAnalysis',
    'calculate_trend_channels',
    'analyze_price_geometry',
    
    # Technical Utilities
    'calculate_pivot_points',
    'find_swing_points',
    'calculate_price_projections',
    'validate_technical_levels',
    'TechnicalLevel',
    'SwingPoint',
    'PivotPoint'
]

# Module metadata
__version__ = "1.0.0"
__author__ = "Algorithmic Trading System"
__description__ = "Advanced Technical Analysis Strategies"

# Default configuration
DEFAULT_CONFIG = {
    'gann': {
        'angle_tolerance': 2.0,  # degrees
        'time_tolerance': 0.1,   # fraction
        'price_tolerance': 0.005, # fraction
        'min_swing_size': 0.02   # minimum swing size
    },
    'fibonacci': {
        'retracement_levels': [0.236, 0.382, 0.5, 0.618, 0.786],
        'extension_levels': [1.272, 1.414, 1.618, 2.0, 2.618],
        'cluster_tolerance': 0.01,  # price clustering tolerance
        'time_ratios': [0.618, 1.0, 1.618, 2.618]  # time-based ratios
    },
    'elliott_wave': {
        'wave_tolerance': 0.1,
        'fibonacci_validation': True,
        'min_wave_size': 0.01,
        'max_wave_count': 5
    },
    'harmonic_patterns': {
        'ratio_tolerance': 0.05,
        'pattern_completion_zone': 0.02,
        'min_pattern_size': 0.03,
        'validation_strict': True
    }
}